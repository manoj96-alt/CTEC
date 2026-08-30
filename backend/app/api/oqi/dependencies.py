"""CDD-045 §22 -- scope-authorization dependency for `/api/v1/oqi`.
Reuses `app.api.supplier_risk.authentication.TrustedPrincipal` and the exact
scope-authorization pattern of `app.api.information_element_context.router`
and `app.api.gate_s.router` -- no new auth mechanism. New scopes:
`oqi:read`, `oqi-remediation:authorize`, `oqi-remediation:report-execution`,
mirroring Gate S's existing `governed-approval:decide`/`request` two-scope
pattern (neither scope ever implies the other)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.core.dependency_container import Container

_ENDPOINT_CLASSIFICATION = "OQI_API_V1"


def authorize(
    authenticated: TrustedPrincipal,
    scope: str,
    dependencies: Container,
    correlation: UUID,
) -> None:
    if scope in authenticated.scopes:
        return
    _record_denied(dependencies, correlation, authenticated)
    raise HTTPException(403, detail={"code": "AUTHORIZATION_SCOPE_REQUIRED"})


def _record_denied(
    dependencies: Container, correlation: UUID, authenticated: TrustedPrincipal
) -> None:
    audit: SecurityAuditService | None = dependencies.security_audit
    if audit is not None:
        audit.record(
            operation="AUTHORIZE_API_OPERATION",
            category="AUTHORIZATION",
            outcome="DENIED",
            code="AUTHORIZATION_SCOPE_REQUIRED",
            correlation_id=correlation,
            principal=authenticated,
            endpoint_classification=_ENDPOINT_CLASSIFICATION,
        )
