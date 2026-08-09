from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.base import Base
from app.integration.contracts import AuthorityContext
from app.runtime.contracts import InvocationRequest
from app.runtime.execution_state import ExecutionState
from app.runtime.persistence.contracts import ProtectionContext
from app.runtime.persistence.models import (
    RuntimeArtifactReferenceORM,
    RuntimeHandoffORM,
    RuntimeResultORM,
    RuntimeStageORM,
)
from app.runtime.persistence.repository import SqlAlchemyExecutionStore


class FakeHandoffProtector:
    def protect(self, plaintext: bytes, context: ProtectionContext) -> bytes:
        return b"protected:" + plaintext

    def recover(self, protected: bytes, context: ProtectionContext) -> bytes:
        if not protected.startswith(b"protected:"):
            raise ValueError("invalid protected test payload")
        return protected.removeprefix(b"protected:")


def store() -> SqlAlchemyExecutionStore:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SqlAlchemyExecutionStore(
        sessionmaker(engine, expire_on_commit=False), FakeHandoffProtector()
    )


def request(payload: bytes = b"payload") -> InvocationRequest:
    now = datetime.now(UTC)
    request_id = uuid4()
    correlation = uuid4()
    authority = AuthorityContext(
        "principal",
        "Service",
        "tenant",
        ("role",),
        ("scope",),
        "AUTHORIZED",
        "auth-ref",
        "gateway",
        request_id,
        correlation,
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )
    return InvocationRequest(
        "2.0", correlation, request_id, uuid4(), "supplier-risk", payload, authority, "1.0"
    )


def test_atomic_admission_duplicate_conflict_and_terminal_retention() -> None:
    durable = store()
    value = request()
    first = durable.admit(value, b"hash")
    assert first.is_new and first.execution_identifier
    duplicate = durable.admit(value, b"hash")
    assert not duplicate.is_new and not duplicate.is_conflict
    conflict = durable.admit(value, b"different")
    assert conflict.is_conflict
    durable.advance(first.execution_identifier, ExecutionState.EXECUTING)
    durable.advance(first.execution_identifier, ExecutionState.COMPLETED)
    durable.apply_terminal_retention(first.execution_identifier)
    snapshot = durable.get(first.execution_identifier)
    assert snapshot and snapshot.state is ExecutionState.COMPLETED


def test_checkpoint_result_and_references_are_durable() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    durable = SqlAlchemyExecutionStore(sessions, FakeHandoffProtector())
    value = request()
    admitted = durable.admit(value, b"hash")
    assert admitted.execution_identifier is not None
    record_id = uuid4()
    completed_at = datetime.now(UTC)
    durable.checkpoint(
        admitted.execution_identifier,
        stage_name="ERM",
        stage_ordinal=0,
        input_payload=b"payload",
        output_payload=b"output",
        artifact_references=(record_id,),
        completed_at=completed_at,
    )
    durable.record_result(
        admitted.execution_identifier,
        result_code="APPROVED",
        result_value="CONTINUE_MONITORING",
        actionable=True,
        completed_at=completed_at,
    )
    with sessions() as session:
        assert session.query(RuntimeStageORM).count() == 1
        assert session.query(RuntimeHandoffORM).count() == 2
        assert all(
            row.protected_payload.startswith(b"protected:")
            for row in session.query(RuntimeHandoffORM).all()
        )
        assert session.query(RuntimeArtifactReferenceORM).one().artifact_id == record_id
        assert session.query(RuntimeResultORM).one().actionable is True
