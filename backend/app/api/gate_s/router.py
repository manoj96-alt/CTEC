"""Gate S -- Governed Human Approval routes (CDD-036 §27; Gate S Artifact
Authorization §7). Reuses Gate E's authentication (OIDC bearer token ->
TrustedPrincipal) and the exact scope-authorization pattern of
`app.api.ontology_modeling.router` -- there is no separate mechanism here.
Five endpoints; no PUT/PATCH/DELETE, no list. `approve`/`reject` require
`governed-approval:decide` independently of `governed-approval:request`;
`request`/`execute` require `governed-approval:request` independently of
`governed-approval:decide` -- neither scope ever implies the other."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.gate_s.dependencies import gate_s_approval_repository, gate_s_approval_service
from app.api.gate_s.schemas import (
    ApprovalResponse,
    ExecuteBody,
    ExecuteResponse,
    RejectBody,
    RequestApprovalBody,
)
from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.gate_s_approval_service import GateSApprovalError, GateSApprovalService
from app.core.dependency_container import Container
from app.domain.gate_s.approval import GateSApprovalRequest
from app.infrastructure.persistence.gate_s_approval_repository import GateSApprovalRepository

router = APIRouter(prefix="/api/v1/governed-approval", tags=["governed-approval"])

_ENDPOINT_CLASSIFICATION = "GOVERNED_HUMAN_APPROVAL_API_V1"

_ERROR_STATUS: dict[str, int] = {
    "APPROVAL_REQUEST_NOT_FOUND": 404,
    "APPROVAL_TENANT_MISMATCH": 403,
    "APPROVAL_SELF_APPROVAL_PROHIBITED": 403,
    "APPROVAL_NOT_PENDING": 409,
    "APPROVAL_REJECTED": 409,
    "APPROVAL_ACTION_MISMATCH": 409,
    "APPROVAL_ALREADY_CONSUMED": 409,
}


@router.post("/requests", response_model=ApprovalResponse)
def create_request(
    body: RequestApprovalBody,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[GateSApprovalService, Depends(gate_s_approval_service)],
) -> ApprovalResponse:
    _authorize(authenticated, "governed-approval:request", dependencies, correlation)
    request = service.request(principal=authenticated, note_text=body.note_text)
    return _to_response(request)


@router.get("/requests/{approval_id}", response_model=ApprovalResponse)
def get_request(
    approval_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    repository: Annotated[GateSApprovalRepository, Depends(gate_s_approval_repository)],
) -> ApprovalResponse:
    _authorize_any(
        authenticated,
        ("governed-approval:request", "governed-approval:decide"),
        dependencies,
        correlation,
    )
    request = repository.get_by_id(approval_id)
    if request is None:
        raise HTTPException(404, detail={"code": "APPROVAL_REQUEST_NOT_FOUND"})
    if request.tenant_id != authenticated.tenant_id:
        raise HTTPException(403, detail={"code": "APPROVAL_TENANT_MISMATCH"})
    return _to_response(request)


@router.post("/requests/{approval_id}/approve", response_model=ApprovalResponse)
def approve_request(
    approval_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[GateSApprovalService, Depends(gate_s_approval_service)],
) -> ApprovalResponse:
    _authorize(authenticated, "governed-approval:decide", dependencies, correlation)
    try:
        approved = service.approve(principal=authenticated, approval_id=approval_id)
    except GateSApprovalError as exc:
        raise HTTPException(_ERROR_STATUS[exc.code], detail={"code": exc.code}) from exc
    return _to_response(approved)


@router.post("/requests/{approval_id}/reject", response_model=ApprovalResponse)
def reject_request(
    approval_id: UUID,
    body: RejectBody,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[GateSApprovalService, Depends(gate_s_approval_service)],
) -> ApprovalResponse:
    _authorize(authenticated, "governed-approval:decide", dependencies, correlation)
    try:
        rejected = service.reject(
            principal=authenticated,
            approval_id=approval_id,
            rejection_reason=body.rejection_reason,
        )
    except GateSApprovalError as exc:
        raise HTTPException(_ERROR_STATUS[exc.code], detail={"code": exc.code}) from exc
    return _to_response(rejected)


@router.post("/requests/{approval_id}/execute", response_model=ExecuteResponse)
def execute_request(
    approval_id: UUID,
    body: ExecuteBody,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[GateSApprovalService, Depends(gate_s_approval_service)],
) -> ExecuteResponse:
    _authorize(authenticated, "governed-approval:request", dependencies, correlation)
    try:
        governed_note_id = service.execute(
            principal=authenticated, approval_id=approval_id, note_text=body.note_text
        )
    except GateSApprovalError as exc:
        raise HTTPException(_ERROR_STATUS[exc.code], detail={"code": exc.code}) from exc
    return ExecuteResponse(governed_note_id=governed_note_id)


def _to_response(request: GateSApprovalRequest) -> ApprovalResponse:
    return ApprovalResponse(
        approval_id=request.approval_id,
        tenant_id=request.tenant_id,
        action_id=request.action_id,
        note_text=request.note_text,
        status=request.status.value,
        requested_by=request.requested_by,
        requested_on=request.requested_on,
        decided_by=request.decided_by,
        decided_on=request.decided_on,
        rejection_reason=request.rejection_reason,
        consumed_on=request.consumed_on,
        consumed_execution_id=request.consumed_execution_id,
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


def _authorize_any(
    authenticated: TrustedPrincipal,
    scopes: tuple[str, ...],
    dependencies: Container,
    correlation: UUID,
) -> None:
    if any(scope in authenticated.scopes for scope in scopes):
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
