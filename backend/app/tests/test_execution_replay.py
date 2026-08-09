from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.base import Base
from app.integration.contracts import AuthorityContext
from app.runtime.execution_state import ExecutionState
from app.runtime.persistence.contracts import RECOVERY_ROLE, RECOVERY_SCOPE, ReplayAuthorization
from app.runtime.persistence.repository import SqlAlchemyExecutionStore
from app.tests.test_durable_execution_store import FakeHandoffProtector, request


def test_replay_preserves_explicit_authorization_evidence() -> None:
    value = ReplayAuthorization(
        "operator",
        "tenant",
        (RECOVERY_ROLE,),
        (RECOVERY_SCOPE,),
        "authorization-1",
        "database restart",
        uuid4(),
        datetime.now(UTC),
    )
    value.validate("tenant")
    assert value.authorization_reference == "authorization-1" and value.reason == "database restart"


def test_recovery_attempt_requires_authority_and_links_attempts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    durable = SqlAlchemyExecutionStore(
        sessionmaker(engine, expire_on_commit=False), FakeHandoffProtector()
    )
    original = durable.admit(request(), b"original").execution_identifier
    assert original is not None
    durable.advance(original, ExecutionState.EXECUTING)
    durable.checkpoint(
        original,
        stage_name="ERM",
        stage_ordinal=0,
        input_payload=b"payload",
        output_payload=b"resolved",
        artifact_references=(),
        completed_at=datetime.now(UTC),
    )
    durable.advance(original, ExecutionState.FAILED)
    now = datetime.now(UTC)
    correlation = uuid4()
    request_id = uuid4()
    authorization = ReplayAuthorization(
        "operator",
        "tenant",
        (RECOVERY_ROLE,),
        (RECOVERY_SCOPE,),
        "authorization-2",
        "recover from verified checkpoint",
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
        "authorization-2",
        "gateway",
        request_id,
        correlation,
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )
    replay = durable.prepare_replay(original, authorization, authority)
    assert replay.execution_identifier != original
    assert replay.logical_execution_identifier == original
