"""Gate O -- Governed Blueprint Information-Element Context-as-a-Service
routes (CDD-029; Gate O Artifact Authorization v1.0). Reuses Gate E's
authentication (OIDC bearer token -> TrustedPrincipal) and the exact
scope-authorization pattern of `app.api.entity_resolution.router` /
`app.api.ontology_modeling.router` -- there is no separate mechanism here.
One endpoint; no PUT/PATCH/DELETE; no write of any kind. Authorization is
enforced before the service is even constructed, so an under-scoped or
unauthenticated caller never reaches Blueprint resolution, Gate I, H4, or
Gate N (CDD-029 §10, §14)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.information_element_context.dependencies import (
    information_element_context_service,
)
from app.api.information_element_context.schemas import ResolveRequest, ResolveResponse
from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.information_element_context_resolution import (
    InformationElementContextResolutionApplicationService,
    InformationElementContextResolutionResult,
    InformationElementContextResolutionStatus,
)
from app.core.dependency_container import Container

router = APIRouter(
    prefix="/api/v1/information-element-context", tags=["information-element-context"]
)

_ENDPOINT_CLASSIFICATION = "INFORMATION_ELEMENT_CONTEXT_API_V1"

# Frozen HTTP mapping (CDD-029 §15, O3-D8/O6-D13 -- not reopened here).
_FAILURE_HTTP_STATUS: dict[InformationElementContextResolutionStatus, int] = {
    InformationElementContextResolutionStatus.BLUEPRINT_NOT_FOUND: 404,
    InformationElementContextResolutionStatus.INFORMATION_ELEMENT_NOT_FOUND: 404,
    InformationElementContextResolutionStatus.INFORMATION_ELEMENT_NAME_AMBIGUOUS: 422,
    InformationElementContextResolutionStatus.UPSTREAM_INTEGRITY_FAILURE: 500,
}


@router.post("/resolve", response_model=ResolveResponse)
def resolve(
    body: ResolveRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[
        InformationElementContextResolutionApplicationService,
        Depends(information_element_context_service),
    ],
) -> ResolveResponse:
    _authorize(authenticated, "information-element-context:read", dependencies, correlation)
    result = service.resolve(
        principal=authenticated,
        blueprint_name=body.blueprint_name,
        information_element_name=body.information_element_name,
    )
    if result.status is not InformationElementContextResolutionStatus.RESOLVED:
        raise HTTPException(
            _FAILURE_HTTP_STATUS[result.status], detail={"code": result.status.value}
        )
    return _to_response(result)


def _to_response(result: InformationElementContextResolutionResult) -> ResolveResponse:
    # Structural invariant: status is RESOLVED here, so every field below was
    # populated by InformationElementContextResolutionApplicationService.resolve().
    assert result.blueprint_id is not None
    assert result.blueprint_version_number is not None
    assert result.information_element_requirement_id is not None
    assert result.information_element_name is not None
    assert result.obligation is not None
    assert result.coverage_status is not None
    return ResolveResponse(
        blueprint_id=result.blueprint_id,
        blueprint_version_number=result.blueprint_version_number,
        information_element_requirement_id=result.information_element_requirement_id,
        information_element_name=result.information_element_name,
        obligation=result.obligation.value,
        coverage_status=result.coverage_status.value,
        evidence_availability_status=(
            result.evidence_availability_status.value
            if result.evidence_availability_status is not None
            else None
        ),
    )


def _authorize(
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
