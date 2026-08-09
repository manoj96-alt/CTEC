"""Supplier-risk v1 command and observation routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import api_service, container, principal
from app.api.supplier_risk.schemas import (
    AttemptListResponse,
    ExecutionListResponse,
    ExecutionResponse,
    GovernedResultResponse,
    ReplayOptionsResponse,
    ReplayRequest,
    RetryEligibilityResponse,
    RetryRequest,
    StageListResponse,
    SubmissionResponse,
    SupplierRiskSubmission,
)
from app.application.supplier_risk_api import SupplierRiskApiService
from app.core.dependency_container import Container

router = APIRouter(prefix="/api/v1/supplier-risk", tags=["supplier-risk"])


@router.get("/executions", response_model=ExecutionListResponse)
def list_executions(
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    execution_status: Annotated[str | None, Query(alias="status")] = None,
) -> ExecutionListResponse:
    _authorize(authenticated, "supplier-risk:read", dependencies, UUID(int=0))
    _rate_limit(authenticated, dependencies)
    if execution_status not in {None, "Accepted", "Executing", "Completed", "Failed"}:
        raise HTTPException(400, detail={"code": "INVALID_EXECUTION_STATUS_FILTER"})
    try:
        offset = int(cursor or "0")
        if offset < 0:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(400, detail={"code": "INVALID_CURSOR"}) from exc
    result = service.executions(authenticated, offset=offset, limit=limit, state=execution_status)
    _audit_disclosure(dependencies, authenticated, UUID(int=0), "EXECUTION_QUEUE_READ")
    return result


@router.post(
    "/assessments", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED
)
def submit_assessment(
    body: SupplierRiskSubmission,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
) -> SubmissionResponse:
    if idempotency_key != str(body.request_identifier):
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_CONFLICT"})
    _authorize(
        authenticated,
        "supplier-risk:submit",
        dependencies,
        body.correlation_identifier,
    )
    content_length = int(request.headers.get("content-length", "0") or 0)
    if content_length > dependencies.settings.supplier_risk_payload_limit_bytes:
        raise HTTPException(413, detail={"code": "PAYLOAD_TOO_LARGE"})
    if dependencies.rate_limiter and not dependencies.rate_limiter.admit(authenticated.tenant_id):
        raise HTTPException(429, detail={"code": "RATE_LIMITED"})
    if dependencies.security_audit is None:
        raise HTTPException(503, detail={"code": "AUDIT_UNAVAILABLE"})
    dependencies.security_audit.record(
        operation="SUBMIT_ASSESSMENT",
        category="ADMISSION",
        outcome="AUTHORIZED",
        code="ASSESSMENT_AUTHORIZED",
        correlation_id=body.correlation_identifier,
        principal=authenticated,
    )
    result = service.submit(body, authenticated)
    dependencies.security_audit.record(
        operation="SUBMIT_ASSESSMENT",
        category="ADMISSION",
        outcome="ACCEPTED",
        code="ASSESSMENT_ACCEPTED",
        correlation_id=body.correlation_identifier,
        principal=authenticated,
        execution_id=result.execution_identifier,
    )
    return result


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(
    execution_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
) -> ExecutionResponse:
    _authorize(authenticated, "supplier-risk:read", dependencies, execution_id)
    result = service.get(execution_id, authenticated)
    if result is None:
        raise HTTPException(404, detail={"code": "RESOURCE_NOT_FOUND"})
    _required_audit(dependencies).record(
        operation="READ_EXECUTION",
        category="PROTECTED_DISCLOSURE",
        outcome="PERMITTED",
        code="EXECUTION_READ",
        correlation_id=result.correlation_identifier,
        principal=authenticated,
        execution_id=execution_id,
    )
    return result


@router.get("/executions/{logical_execution_id}/attempts", response_model=AttemptListResponse)
def list_attempts(
    logical_execution_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AttemptListResponse:
    _authorize(authenticated, "supplier-risk:read", dependencies, logical_execution_id)
    try:
        offset = int(cursor or "0")
        if offset < 0:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(400, detail={"code": "INVALID_CURSOR"}) from exc
    result = service.attempts(logical_execution_id, authenticated, offset=offset, limit=limit)
    if result is None:
        raise HTTPException(404, detail={"code": "RESOURCE_NOT_FOUND"})
    _audit_disclosure(dependencies, authenticated, logical_execution_id, "ATTEMPTS_READ")
    return result


@router.get(
    "/executions/{logical_execution_id}/attempts/{execution_id}/stages",
    response_model=StageListResponse,
)
def list_stages(
    logical_execution_id: UUID,
    execution_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
) -> StageListResponse:
    _authorize(authenticated, "supplier-risk:read", dependencies, logical_execution_id)
    result = service.stages(logical_execution_id, execution_id, authenticated)
    if result is None:
        raise HTTPException(404, detail={"code": "RESOURCE_NOT_FOUND"})
    _audit_disclosure(dependencies, authenticated, logical_execution_id, "STAGES_READ")
    return result


@router.get("/executions/{logical_execution_id}/result", response_model=GovernedResultResponse)
def get_result(
    logical_execution_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
) -> GovernedResultResponse | Response:
    _authorize(authenticated, "supplier-risk:read", dependencies, logical_execution_id)
    result = service.result(logical_execution_id, authenticated)
    if result is not None:
        _audit_disclosure(dependencies, authenticated, logical_execution_id, "RESULT_READ")
        return result
    if service.get(logical_execution_id, authenticated) is None:
        raise HTTPException(404, detail={"code": "RESOURCE_NOT_FOUND"})
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.get(
    "/executions/{logical_execution_id}/retry-eligibility",
    response_model=RetryEligibilityResponse,
)
def get_retry_eligibility(
    logical_execution_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
) -> RetryEligibilityResponse:
    _authorize(authenticated, "supplier-risk:retry", dependencies, logical_execution_id)
    result = service.retry_eligibility(logical_execution_id, authenticated)
    if result is None:
        raise HTTPException(404, detail={"code": "RESOURCE_NOT_FOUND"})
    _audit_disclosure(dependencies, authenticated, logical_execution_id, "RETRY_ELIGIBILITY_READ")
    return result


@router.get(
    "/executions/{logical_execution_id}/replay-options",
    response_model=ReplayOptionsResponse,
)
def get_replay_options(
    logical_execution_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
) -> ReplayOptionsResponse:
    _authorize(authenticated, "supplier-risk:replay", dependencies, logical_execution_id)
    if "EXECUTION_RECOVERY_OPERATOR" not in authenticated.roles:
        raise HTTPException(403, detail={"code": "RECOVERY_ROLE_REQUIRED"})
    result = service.replay_options(logical_execution_id, authenticated)
    if result is None:
        raise HTTPException(404, detail={"code": "RESOURCE_NOT_FOUND"})
    _audit_disclosure(dependencies, authenticated, logical_execution_id, "REPLAY_OPTIONS_READ")
    return result


@router.post(
    "/executions/{logical_execution_id}/retry",
    response_model=SubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_execution(
    logical_execution_id: UUID,
    body: RetryRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
) -> SubmissionResponse:
    _authorize(
        authenticated,
        "supplier-risk:retry",
        dependencies,
        body.correlation_identifier,
    )
    if idempotency_key != str(body.request_identifier):
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_CONFLICT"})
    audit = _required_audit(dependencies)
    audit.record(
        operation="RETRY_EXECUTION",
        category="RECOVERY",
        outcome="AUTHORIZED",
        code="RETRY_AUTHORIZED",
        correlation_id=body.correlation_identifier,
        principal=authenticated,
    )
    try:
        result = service.retry(logical_execution_id, body, authenticated)
    except LookupError as exc:
        raise HTTPException(404, detail={"code": "RESOURCE_NOT_FOUND"}) from exc
    except ValueError as exc:
        raise HTTPException(409, detail={"code": str(exc)}) from exc
    audit.record(
        operation="RETRY_EXECUTION",
        category="RECOVERY",
        outcome="ACCEPTED",
        code="RETRY_ACCEPTED",
        correlation_id=body.correlation_identifier,
        principal=authenticated,
        execution_id=result.execution_identifier,
    )
    return result


@router.post(
    "/executions/{logical_execution_id}/replay",
    response_model=SubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def replay_execution(
    logical_execution_id: UUID,
    body: ReplayRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[SupplierRiskApiService, Depends(api_service)],
    dependencies: Annotated[Container, Depends(container)],
) -> SubmissionResponse:
    _authorize(
        authenticated,
        "supplier-risk:replay",
        dependencies,
        body.correlation_identifier,
    )
    if "EXECUTION_RECOVERY_OPERATOR" not in authenticated.roles:
        _required_audit(dependencies).record(
            operation="REPLAY_EXECUTION",
            category="AUTHORIZATION",
            outcome="DENIED",
            code="RECOVERY_ROLE_REQUIRED",
            correlation_id=body.correlation_identifier,
            principal=authenticated,
        )
        raise HTTPException(403, detail={"code": "RECOVERY_ROLE_REQUIRED"})
    if idempotency_key != str(body.request_identifier):
        raise HTTPException(409, detail={"code": "IDEMPOTENCY_KEY_CONFLICT"})
    audit = _required_audit(dependencies)
    audit.record(
        operation="REPLAY_EXECUTION",
        category="PRIVILEGED_RECOVERY",
        outcome="AUTHORIZED",
        code="REPLAY_AUTHORIZED",
        correlation_id=body.correlation_identifier,
        principal=authenticated,
    )
    try:
        result = service.replay(logical_execution_id, body, authenticated)
    except LookupError as exc:
        raise HTTPException(404, detail={"code": "RESOURCE_NOT_FOUND"}) from exc
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise HTTPException(409, detail={"code": "REPLAY_REJECTED"}) from exc
    audit.record(
        operation="REPLAY_EXECUTION",
        category="PRIVILEGED_RECOVERY",
        outcome="ACCEPTED",
        code="REPLAY_ACCEPTED",
        correlation_id=body.correlation_identifier,
        principal=authenticated,
        execution_id=result.execution_identifier,
    )
    return result


def _required_audit(dependencies: Container) -> SecurityAuditService:
    if dependencies.security_audit is None:
        raise HTTPException(503, detail={"code": "AUDIT_UNAVAILABLE"})
    return dependencies.security_audit


def _authorize(
    authenticated: TrustedPrincipal,
    scope: str,
    dependencies: Container,
    correlation_id: UUID,
) -> None:
    if scope in authenticated.scopes:
        return
    _required_audit(dependencies).record(
        operation="AUTHORIZE_API_OPERATION",
        category="AUTHORIZATION",
        outcome="DENIED",
        code="AUTHORIZATION_SCOPE_REQUIRED",
        correlation_id=correlation_id,
        principal=authenticated,
    )
    raise HTTPException(403, detail={"code": "AUTHORIZATION_SCOPE_REQUIRED"})


def _audit_disclosure(
    dependencies: Container,
    authenticated: TrustedPrincipal,
    logical_execution_id: UUID,
    code: str,
) -> None:
    _required_audit(dependencies).record(
        operation="READ_EXECUTION_RESOURCE",
        category="PROTECTED_DISCLOSURE",
        outcome="PERMITTED",
        code=code,
        correlation_id=logical_execution_id,
        principal=authenticated,
        execution_id=logical_execution_id,
    )


def _rate_limit(authenticated: TrustedPrincipal, dependencies: Container) -> None:
    if dependencies.rate_limiter and not dependencies.rate_limiter.admit(authenticated.tenant_id):
        raise HTTPException(429, detail={"code": "RATE_LIMITED"})
