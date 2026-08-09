"""Non-canonical immutable API security audit mapping."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import Base


class ApiSecurityAuditEventORM(Base):
    __tablename__ = "api_security_audit_events"

    audit_event_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tenant_id: Mapped[str | None] = mapped_column(String(200))
    principal_reference: Mapped[str | None] = mapped_column(String(200))
    operation: Mapped[str] = mapped_column(String(100))
    endpoint_classification: Mapped[str] = mapped_column(String(100))
    event_category: Mapped[str] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(40))
    diagnostic_code: Mapped[str] = mapped_column(String(100))
    correlation_id: Mapped[UUID]
    execution_id: Mapped[UUID | None]
    attempt_id: Mapped[UUID | None]
    authorization_decision_reference: Mapped[str | None] = mapped_column(String(200))
    evidence_resource_reference: Mapped[str | None] = mapped_column(String(300))
    source_channel: Mapped[str | None] = mapped_column(String(100))
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    legal_hold_reference: Mapped[str | None] = mapped_column(String(200))
    integrity_version: Mapped[int] = mapped_column(Integer, default=1)
    integrity_digest: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
