"""Allowlisted audit-event construction without payload or credential capture."""

from uuid import UUID

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.infrastructure.persistence.api_security_audit_repository import (
    ApiSecurityAuditEvent,
    ApiSecurityAuditRepository,
)


class SecurityAuditService:
    def __init__(self, repository: ApiSecurityAuditRepository) -> None:
        self._repository = repository

    def record(
        self,
        *,
        operation: str,
        category: str,
        outcome: str,
        code: str,
        correlation_id: UUID,
        principal: TrustedPrincipal | None = None,
        execution_id: UUID | None = None,
        authorization_reference: str | None = None,
    ) -> UUID:
        return self._repository.append(
            ApiSecurityAuditEvent(
                operation=operation,
                endpoint_classification="SUPPLIER_RISK_API_V1",
                event_category=category,
                outcome=outcome,
                diagnostic_code=code,
                correlation_id=correlation_id,
                tenant_id=principal.tenant_id if principal else None,
                principal_reference=principal.principal_id if principal else None,
                execution_id=execution_id,
                attempt_id=execution_id,
                authorization_decision_reference=authorization_reference,
                source_channel="HTTP_API",
            )
        )
