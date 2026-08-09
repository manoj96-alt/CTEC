"""Trusted-boundary authorization and AuthorityContext construction."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import HTTPException

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.integration.contracts import AuthorityContext


def require_scope(principal: TrustedPrincipal, scope: str) -> None:
    if scope not in principal.scopes:
        raise HTTPException(403, detail={"code": "AUTHORIZATION_SCOPE_REQUIRED"})


def authority_context(
    principal: TrustedPrincipal, *, request_id: UUID, correlation_id: UUID
) -> AuthorityContext:
    now = datetime.now(UTC)
    if principal.issued_at >= principal.expires_at or now >= principal.expires_at:
        raise PermissionError("AUTHORITY_CONTEXT_EXPIRED")
    return AuthorityContext(
        principal_id=principal.principal_id,
        principal_type="AuthenticatedPrincipal",
        organization_id=principal.tenant_id,
        roles=principal.roles or ("authenticated",),
        scopes=principal.scopes,
        authorization_decision="AUTHORIZED",
        authorization_reference=f"api-authz:{uuid5(NAMESPACE_URL, f'{principal.issuer}:{principal.principal_id}:{request_id}')}",
        trust_source=principal.issuer,
        request_id=request_id,
        correlation_id=correlation_id,
        issued_at=principal.issued_at,
        expires_at=principal.expires_at,
    )
