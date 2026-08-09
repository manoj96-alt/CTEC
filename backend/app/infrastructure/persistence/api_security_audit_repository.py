"""Isolated append-only repository for CDD-013 security audit evidence."""

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.persistence.models.api_security_audit import ApiSecurityAuditEventORM


@dataclass(frozen=True, slots=True)
class ApiSecurityAuditEvent:
    operation: str
    endpoint_classification: str
    event_category: str
    outcome: str
    diagnostic_code: str
    correlation_id: UUID
    tenant_id: str | None = None
    principal_reference: str | None = None
    execution_id: UUID | None = None
    attempt_id: UUID | None = None
    authorization_decision_reference: str | None = None
    evidence_resource_reference: str | None = None
    source_channel: str | None = None
    audit_event_id: UUID | None = None
    event_timestamp: datetime | None = None
    retention_until: datetime | None = None
    legal_hold: bool = False
    legal_hold_reference: str | None = None


class ApiSecurityAuditRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def append(self, event: ApiSecurityAuditEvent) -> UUID:
        now = event.event_timestamp or datetime.now(UTC)
        event_id = event.audit_event_id or uuid4()
        retention = event.retention_until or now + timedelta(days=365 * 7 + 2)
        values = replace(
            event, audit_event_id=event_id, event_timestamp=now, retention_until=retention
        )
        digest = sha256(repr(values).encode()).digest()
        session = self._sessions()
        try:
            session.add(
                ApiSecurityAuditEventORM(
                    **asdict(values), integrity_version=1, integrity_digest=digest, created_at=now
                )
            )
            session.commit()
            return event_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_for_tenant(
        self, tenant_id: str, *, limit: int = 100
    ) -> tuple[ApiSecurityAuditEventORM, ...]:
        session = self._sessions()
        try:
            return tuple(
                session.scalars(
                    select(ApiSecurityAuditEventORM)
                    .where(ApiSecurityAuditEventORM.tenant_id == tenant_id)
                    .order_by(ApiSecurityAuditEventORM.event_timestamp.desc())
                    .limit(limit)
                )
            )
        finally:
            session.close()

    def record_legal_hold(self, event_id: UUID, reference: str, *, enabled: bool) -> UUID:
        session = self._sessions()
        try:
            target = session.get(ApiSecurityAuditEventORM, event_id)
            if target is None:
                raise KeyError(event_id)
            return self.append(
                ApiSecurityAuditEvent(
                    operation="LEGAL_HOLD",
                    endpoint_classification="SECURITY_AUDIT_GOVERNANCE",
                    event_category="LEGAL_HOLD_APPLIED" if enabled else "LEGAL_HOLD_RELEASED",
                    outcome="RECORDED",
                    diagnostic_code="LEGAL_HOLD_CHANGED",
                    correlation_id=target.correlation_id,
                    tenant_id=target.tenant_id,
                    evidence_resource_reference=str(event_id),
                    legal_hold=enabled,
                    legal_hold_reference=reference,
                )
            )
        finally:
            session.close()

    def dispose_expired(self, *, tenant_id: str, now: datetime) -> int:
        session = self._sessions()
        try:
            holds = tuple(
                session.scalars(
                    select(ApiSecurityAuditEventORM)
                    .where(
                        ApiSecurityAuditEventORM.tenant_id == tenant_id,
                        ApiSecurityAuditEventORM.operation == "LEGAL_HOLD",
                    )
                    .order_by(ApiSecurityAuditEventORM.event_timestamp)
                )
            )
            active: dict[str, bool] = {}
            for hold in holds:
                if hold.evidence_resource_reference:
                    active[hold.evidence_resource_reference] = hold.legal_hold
            protected = tuple(UUID(value) for value, enabled in active.items() if enabled)
            session.execute(text("SET LOCAL ctec.audit_disposition = 'authorized'"))
            criteria = [
                ApiSecurityAuditEventORM.tenant_id == tenant_id,
                ApiSecurityAuditEventORM.retention_until < now,
                ApiSecurityAuditEventORM.legal_hold.is_(False),
            ]
            if protected:
                criteria.append(ApiSecurityAuditEventORM.audit_event_id.not_in(protected))
            result = session.execute(delete(ApiSecurityAuditEventORM).where(*criteria))
            session.commit()
            return int(getattr(result, "rowcount", 0) or 0)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
