from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.api_security_audit_repository import (
    ApiSecurityAuditEvent,
    ApiSecurityAuditRepository,
)
from app.infrastructure.persistence.base import Base


def _repository() -> ApiSecurityAuditRepository:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return ApiSecurityAuditRepository(sessionmaker(engine, expire_on_commit=False))


def test_audit_append_is_minimal_and_seven_year_retained() -> None:
    repository = _repository()
    event_id = repository.append(
        ApiSecurityAuditEvent(
            operation="AUTHENTICATE",
            endpoint_classification="SUPPLIER_RISK_API_V1",
            event_category="AUTHENTICATION",
            outcome="REJECTED",
            diagnostic_code="AUTH_TOKEN_UNVERIFIABLE",
            correlation_id=uuid4(),
        )
    )
    rows = repository.list_for_tenant("unknown")
    assert event_id and rows == ()


def test_legal_hold_is_recorded_as_new_immutable_evidence() -> None:
    repository = _repository()
    original = repository.append(
        ApiSecurityAuditEvent(
            operation="SUBMIT",
            endpoint_classification="SUPPLIER_RISK_API_V1",
            event_category="ADMISSION",
            outcome="ACCEPTED",
            diagnostic_code="OK",
            correlation_id=uuid4(),
            tenant_id="tenant-a",
            event_timestamp=datetime.now(UTC),
        )
    )
    hold = repository.record_legal_hold(original, "case-1", enabled=True)
    rows = repository.list_for_tenant("tenant-a")
    assert hold != original and len(rows) == 2
    assert rows[0].event_category == "LEGAL_HOLD_APPLIED"
