"""SQLAlchemy mappings for the six governed runtime records."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import Base


class RuntimeExecutionORM(Base):
    __tablename__ = "runtime_executions"
    __table_args__ = (UniqueConstraint("tenant_id", "protocol_version", "request_id"),)
    execution_id: Mapped[UUID] = mapped_column(primary_key=True)
    logical_execution_id: Mapped[UUID]
    tenant_id: Mapped[str] = mapped_column(String(200))
    protocol_version: Mapped[str] = mapped_column(String(32))
    integration_contract_version: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[UUID]
    correlation_id: Mapped[UUID]
    session_id: Mapped[UUID]
    request_classification: Mapped[str] = mapped_column(String(100))
    payload_fingerprint: Mapped[bytes] = mapped_column(LargeBinary)
    control_fingerprint: Mapped[bytes] = mapped_column(LargeBinary)
    state: Mapped[str] = mapped_column(String(32))
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(BigInteger, default=0)
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuntimeStageORM(Base):
    __tablename__ = "runtime_stages"
    __table_args__ = (UniqueConstraint("execution_id", "stage_ordinal"),)
    stage_id: Mapped[UUID] = mapped_column(primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("runtime_executions.execution_id"))
    stage_name: Mapped[str] = mapped_column(String(16))
    stage_ordinal: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_handoff_id: Mapped[UUID | None]
    output_handoff_id: Mapped[UUID | None]
    safe_failure_code: Mapped[str | None] = mapped_column(String(100))
    revision: Mapped[int] = mapped_column(BigInteger, default=0)


class RuntimeHandoffORM(Base):
    __tablename__ = "runtime_handoffs"
    handoff_id: Mapped[UUID] = mapped_column(primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("runtime_executions.execution_id"))
    source_stage: Mapped[str | None] = mapped_column(String(16))
    target_stage: Mapped[str | None] = mapped_column(String(16))
    contract_version: Mapped[str] = mapped_column(String(32))
    protected_payload: Mapped[bytes] = mapped_column(LargeBinary)
    content_hash: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RuntimeArtifactReferenceORM(Base):
    __tablename__ = "runtime_artifact_references"
    __table_args__ = (UniqueConstraint("execution_id", "artifact_role", "artifact_id"),)
    artifact_reference_id: Mapped[UUID] = mapped_column(primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("runtime_executions.execution_id"))
    stage_id: Mapped[UUID | None] = mapped_column(ForeignKey("runtime_stages.stage_id"))
    artifact_role: Mapped[str] = mapped_column(String(40))
    artifact_id: Mapped[UUID]
    source_capability: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RuntimeResultORM(Base):
    __tablename__ = "runtime_results"
    result_id: Mapped[UUID] = mapped_column(primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("runtime_executions.execution_id"), unique=True
    )
    terminal_capability: Mapped[str | None] = mapped_column(String(16))
    disposition: Mapped[str] = mapped_column(String(40))
    result_code: Mapped[str | None] = mapped_column(String(100))
    result_value: Mapped[str | None] = mapped_column(String(200))
    actionable: Mapped[bool] = mapped_column(Boolean)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RuntimeRecoveryAttemptORM(Base):
    __tablename__ = "runtime_recovery_attempts"
    recovery_id: Mapped[UUID] = mapped_column(primary_key=True)
    logical_execution_id: Mapped[UUID]
    original_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("runtime_executions.execution_id")
    )
    replay_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("runtime_executions.execution_id"), unique=True
    )
    checkpoint_stage_id: Mapped[UUID | None] = mapped_column(ForeignKey("runtime_stages.stage_id"))
    tenant_id: Mapped[str] = mapped_column(String(200))
    replay_principal_id: Mapped[str] = mapped_column(String(200))
    original_authorization_reference: Mapped[str] = mapped_column(String(200))
    replay_authorization_reference: Mapped[str] = mapped_column(String(200))
    replay_reason: Mapped[str] = mapped_column(String(1000))
    correlation_id: Mapped[UUID]
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
