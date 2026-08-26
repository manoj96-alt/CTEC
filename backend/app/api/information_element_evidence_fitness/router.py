"""Governed Evidence Fitness Exposure routes (CDD-034; CDD-031 Evidence
Fitness Exposure Clarification and Remediation Report; CDD-034 Artifact
Authorization v1.0). Reuses Gate E's authentication (OIDC bearer token ->
TrustedPrincipal) and the exact scope-authorization pattern of
`app.api.information_element_context.router` -- there is no separate
mechanism here. One endpoint; no PUT/PATCH/DELETE; no write of any kind.
Authorization is enforced before the service is even constructed, so an
under-scoped or unauthenticated caller never reaches Blueprint resolution,
Gate I, H4, or Gate T (CDD-034 §13, §16)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.information_element_evidence_fitness.dependencies import (
    information_element_evidence_fitness_service,
)
from app.api.information_element_evidence_fitness.schemas import ResolveRequest, ResolveResponse
from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.information_element_evidence_fitness_resolution import (
    InformationElementEvidenceFitnessResolutionApplicationService,
    InformationElementEvidenceFitnessResolutionResult,
    InformationElementEvidenceFitnessResolutionStatus,
)
from app.core.dependency_container import Container

router = APIRouter(
    prefix="/api/v1/information-element-evidence-fitness",
    tags=["information-element-evidence-fitness"],
)

_ENDPOINT_CLASSIFICATION = "INFORMATION_ELEMENT_EVIDENCE_FITNESS_API_V1"

# Frozen HTTP mapping (CDD-034 §18 -- not reopened here).
_FAILURE_HTTP_STATUS: dict[InformationElementEvidenceFitnessResolutionStatus, int] = {
    InformationElementEvidenceFitnessResolutionStatus.BLUEPRINT_NOT_FOUND: 404,
    InformationElementEvidenceFitnessResolutionStatus.INFORMATION_ELEMENT_NOT_FOUND: 404,
    InformationElementEvidenceFitnessResolutionStatus.INFORMATION_ELEMENT_NAME_AMBIGUOUS: 422,
    InformationElementEvidenceFitnessResolutionStatus.UPSTREAM_INTEGRITY_FAILURE: 500,
}


@router.post("/resolve", response_model=ResolveResponse)
def resolve(
    body: ResolveRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[
        InformationElementEvidenceFitnessResolutionApplicationService,
        Depends(information_element_evidence_fitness_service),
    ],
) -> ResolveResponse:
    _authorize(
        authenticated, "information-element-evidence-fitness:read", dependencies, correlation
    )
    result = service.resolve(
        principal=authenticated,
        blueprint_name=body.blueprint_name,
        information_element_name=body.information_element_name,
    )
    if result.status is not InformationElementEvidenceFitnessResolutionStatus.RESOLVED:
        raise HTTPException(
            _FAILURE_HTTP_STATUS[result.status], detail={"code": result.status.value}
        )
    return _to_response(result)


def _to_response(
    result: InformationElementEvidenceFitnessResolutionResult,
) -> ResolveResponse:
    # Structural invariant: status is RESOLVED here, so both of these were
    # populated by InformationElementEvidenceFitnessResolutionApplicationService
    # .resolve() -- source_field_id and fitness_status remain independently
    # nullable per CDD-034 §11.
    assert result.information_element_requirement_id is not None
    assert result.evaluated_at is not None
    return ResolveResponse(
        information_element_requirement_id=result.information_element_requirement_id,
        source_field_id=result.source_field_id,
        fitness_status=(result.fitness_status.value if result.fitness_status is not None else None),
        evaluated_at=result.evaluated_at,
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
