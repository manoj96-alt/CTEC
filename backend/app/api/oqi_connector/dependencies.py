"""CDD-059 SS41/SS42 -- scope-authorization/audit dependency for
`/api/v1/oqi/connectors`. Reuses `app.api.oqi.dependencies.authorize`
directly (per the Artifact Authorization row 11) rather than duplicating
its scope-denial/audit logic -- the only new element is this module's own
successful-outcome audit helper, mirroring CDD-058's `_record_success`
precedent exactly. New scopes: `oqi-connector:read`,
`oqi-connector:configure`, `oqi-connector:run` -- narrow, mirroring the
existing `resource:action` convention; no scope ever implies another."""

from __future__ import annotations

from uuid import UUID

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.core.dependency_container import Container

_ENDPOINT_CLASSIFICATION = "OQI_CONNECTOR_API_V1"


def record_success(
    dependencies: Container,
    correlation: UUID,
    authenticated: TrustedPrincipal,
    *,
    operation: str,
    code: str,
) -> None:
    """CDD-059 SS42: successful-outcome audit recording, reusing the
    pre-existing `SecurityAuditService` exactly as CDD-058's own
    `_record_success` already established -- no new observability
    infrastructure. Never called with credential material as `code`."""
    audit = dependencies.security_audit
    if audit is not None:
        audit.record(
            operation=operation,
            category="ADMISSION" if operation.startswith("CONNECTOR_RUN") else "AUTHORIZATION",
            outcome="SUCCESS",
            code=code,
            correlation_id=correlation,
            principal=authenticated,
            endpoint_classification=_ENDPOINT_CLASSIFICATION,
        )
