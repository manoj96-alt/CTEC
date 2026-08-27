"""Gate V -- Governed Agent Resolution routes (CDD-037 §18-§19; Gate V
Artifact Authorization §7). Reuses Gate E's authentication (OIDC bearer
token -> TrustedPrincipal) and the exact scope-authorization pattern of
`app.api.gate_s.router`. Two endpoints; no PUT/PATCH/DELETE, no list, no
execute route. `POST` requires BOTH `governed-agent:propose` AND
`governed-approval:request` (CDD-037 §9-§10: neither scope alone can cause
Gate V to manufacture a Gate S approval request -- zero privilege
amplification over calling Gate S directly). `GET` requires EITHER
`governed-agent:propose` OR `governed-approval:decide`."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.gate_v.dependencies import (
    gate_v_agent_resolution_repository,
    gate_v_agent_service,
)
from app.api.gate_v.schemas import (
    ResolutionDetailResponse,
    ResolutionResponse,
    ResolveObservationBody,
)
from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.gate_v_agent_service import GateVApplicationService
from app.core.dependency_container import Container
from app.domain.gate_v.agent_resolution import GateVAgentResolution
from app.infrastructure.persistence.gate_v_agent_resolution_repository import (
    GateVAgentResolutionRepository,
)

router = APIRouter(prefix="/api/v1/governed-agent", tags=["governed-agent"])

_ENDPOINT_CLASSIFICATION = "GOVERNED_AGENT_ORCHESTRATION_API_V1"


@router.post("/resolutions", response_model=ResolutionResponse)
def create_resolution(
    body: ResolveObservationBody,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[GateVApplicationService, Depends(gate_v_agent_service)],
) -> ResolutionResponse:
    if "governed-agent:propose" not in authenticated.scopes:
        _record_denied(dependencies, correlation, authenticated, "AGENT_PROPOSE_AUTHORITY_REQUIRED")
        raise HTTPException(403, detail={"code": "AGENT_PROPOSE_AUTHORITY_REQUIRED"})
    if "governed-approval:request" not in authenticated.scopes:
        _record_denied(dependencies, correlation, authenticated, "REQUEST_AUTHORITY_REQUIRED")
        raise HTTPException(403, detail={"code": "REQUEST_AUTHORITY_REQUIRED"})

    resolution = service.resolve(
        principal=authenticated,
        observation_text=body.observation_text,
        priority_score=body.priority_score,
    )
    return _to_response(resolution)


@router.get("/resolutions/{resolution_id}", response_model=ResolutionDetailResponse)
def get_resolution(
    resolution_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    repository: Annotated[
        GateVAgentResolutionRepository, Depends(gate_v_agent_resolution_repository)
    ],
) -> ResolutionDetailResponse:
    if not any(
        scope in authenticated.scopes
        for scope in ("governed-agent:propose", "governed-approval:decide")
    ):
        _record_denied(dependencies, correlation, authenticated, "AUTHORIZATION_SCOPE_REQUIRED")
        raise HTTPException(403, detail={"code": "AUTHORIZATION_SCOPE_REQUIRED"})

    resolution = repository.get_by_id(resolution_id)
    if resolution is None:
        raise HTTPException(404, detail={"code": "RESOLUTION_NOT_FOUND"})
    if resolution.tenant_id != authenticated.tenant_id:
        raise HTTPException(403, detail={"code": "RESOLUTION_TENANT_MISMATCH"})
    return _to_detail_response(resolution)


def _to_response(resolution: GateVAgentResolution) -> ResolutionResponse:
    return ResolutionResponse(
        resolution_id=resolution.resolution_id,
        agent_id=resolution.agent_id,
        outcome=resolution.outcome.value,
        approval_id=resolution.approval_id,
        resolved_on=resolution.resolved_on,
    )


def _to_detail_response(resolution: GateVAgentResolution) -> ResolutionDetailResponse:
    return ResolutionDetailResponse(
        resolution_id=resolution.resolution_id,
        agent_id=resolution.agent_id,
        outcome=resolution.outcome.value,
        approval_id=resolution.approval_id,
        resolved_on=resolution.resolved_on,
        tenant_id=resolution.tenant_id,
        requested_by=resolution.requested_by,
        observation_text=resolution.observation_text,
        priority_score=resolution.priority_score,
    )


def _record_denied(
    dependencies: Container,
    correlation: UUID,
    authenticated: TrustedPrincipal,
    code: str,
) -> None:
    audit: SecurityAuditService | None = dependencies.security_audit
    if audit is not None:
        audit.record(
            operation="AUTHORIZE_API_OPERATION",
            category="AUTHORIZATION",
            outcome="DENIED",
            code=code,
            correlation_id=correlation,
            principal=authenticated,
            endpoint_classification=_ENDPOINT_CLASSIFICATION,
        )
