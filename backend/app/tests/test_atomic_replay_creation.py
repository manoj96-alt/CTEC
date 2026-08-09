from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.persistence.base import Base
from app.integration.contracts import AuthorityContext
from app.runtime.execution_state import ExecutionState
from app.runtime.persistence.contracts import RECOVERY_ROLE, RECOVERY_SCOPE, ReplayAuthorization
from app.runtime.persistence.crypto import AuthenticatedHandoffProtector
from app.runtime.persistence.models import RuntimeExecutionORM, RuntimeRecoveryAttemptORM
from app.runtime.persistence.repository import SqlAlchemyExecutionStore
from app.tests.test_durable_execution_store import request


def test_concurrent_replay_admission_creates_one_linked_attempt() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    store = SqlAlchemyExecutionStore(
        sessions, AuthenticatedHandoffProtector({"test": b"t" * 32}, "test")
    )
    original_request = request(b"original")
    original = store.admit(original_request, b"original-fingerprint").execution_identifier
    assert original is not None
    store.advance(original, ExecutionState.EXECUTING)
    store.checkpoint(
        original,
        stage_name="ERM",
        stage_ordinal=0,
        input_payload=b"original",
        output_payload=b"resolved",
        artifact_references=(),
        completed_at=datetime.now(UTC),
    )
    store.advance(original, ExecutionState.FAILED)

    now = datetime.now(UTC)
    correlation = uuid4()
    request_id = uuid4()
    authorization = ReplayAuthorization(
        "operator",
        "tenant",
        (RECOVERY_ROLE,),
        (RECOVERY_SCOPE,),
        "replay-authorization",
        "resume after technical failure",
        correlation,
        now,
    )
    authority = AuthorityContext(
        "operator",
        "Service",
        "tenant",
        (RECOVERY_ROLE,),
        (RECOVERY_SCOPE,),
        "AUTHORIZED",
        "replay-authorization",
        "trusted-api",
        request_id,
        correlation,
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(
            pool.map(lambda _: store.prepare_replay(original, authorization, authority), range(2))
        )

    assert results[0].execution_identifier == results[1].execution_identifier
    assert results[0].recovery_identifier == results[1].recovery_identifier
    assert results[0].logical_execution_identifier == original
    assert results[0].resume_stage_ordinal == 1
    assert results[0].opaque_payload == b"resolved"
    with sessions() as session:
        assert session.query(RuntimeRecoveryAttemptORM).count() == 1
        assert session.query(RuntimeExecutionORM).count() == 2
        assert session.get(RuntimeExecutionORM, original).state == ExecutionState.FAILED.value
