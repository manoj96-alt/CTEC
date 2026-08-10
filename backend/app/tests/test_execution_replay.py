from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.base import Base
from app.integration.contracts import AuthorityContext
from app.runtime.execution_state import ExecutionState
from app.runtime.persistence.contracts import RECOVERY_ROLE, RECOVERY_SCOPE, ReplayAuthorization
from app.runtime.persistence.models import RuntimeExecutionORM, RuntimeRecoveryAttemptORM
from app.runtime.persistence.repository import SqlAlchemyExecutionStore
from app.runtime.recovery import STAGES
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


def test_current_server_issued_grm_checkpoint_replays_grm_once() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    durable = SqlAlchemyExecutionStore(sessions, FakeHandoffProtector())
    original_request = request(b"admitted")
    original = durable.admit(original_request, b"original").execution_identifier
    assert original is not None
    durable.advance(original, ExecutionState.EXECUTING)

    input_payload = original_request.opaque_payload
    for ordinal, stage_name in enumerate(STAGES):
        output_payload = f"{stage_name}-output".encode()
        durable.checkpoint(
            original,
            stage_name=stage_name,
            stage_ordinal=ordinal,
            input_payload=input_payload,
            output_payload=output_payload,
            artifact_references=(),
            completed_at=datetime.now(UTC),
        )
        input_payload = output_payload
    durable.advance(original, ExecutionState.COMPLETED)

    issued = durable.replay_options(original, "tenant")
    assert len(issued) == 1
    assert issued[0].stage_name == "GRM"
    assert issued[0].eligible

    now = datetime.now(UTC)
    correlation = uuid4()
    request_id = uuid4()
    authorization = ReplayAuthorization(
        "operator",
        "tenant",
        (RECOVERY_ROLE,),
        (RECOVERY_SCOPE,),
        "authorization-grm",
        "re-evaluate governance from the verified checkpoint",
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
        "authorization-grm",
        "trusted-api",
        request_id,
        correlation,
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )

    first = durable.prepare_replay(original, authorization, authority)
    duplicate = durable.prepare_replay(original, authorization, authority)

    assert first.execution_identifier == duplicate.execution_identifier
    assert first.recovery_identifier == duplicate.recovery_identifier
    assert first.resume_stage_ordinal == len(STAGES) - 1
    assert first.opaque_payload == b"DRM-output"
    durable.checkpoint(
        first.execution_identifier,
        stage_name="GRM",
        stage_ordinal=len(STAGES) - 1,
        input_payload=first.opaque_payload,
        output_payload=b"GRM-replayed-output",
        artifact_references=(),
        completed_at=datetime.now(UTC),
    )
    with sessions() as session:
        assert session.query(RuntimeRecoveryAttemptORM).count() == 1
        assert session.query(RuntimeExecutionORM).count() == 2
        original_row = session.get(RuntimeExecutionORM, original)
        assert original_row is not None
        assert original_row.state == ExecutionState.COMPLETED.value
