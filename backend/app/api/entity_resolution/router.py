"""Entity Resolution Steward v1 routes (Increment 3A Gate C).

Reuses the Supplier Risk API's authentication (OIDC bearer token ->
TrustedPrincipal), scope authorization, rate limiting, and security-audit
infrastructure exactly -- there is no separate mechanism here. Tenant
identity always comes from TrustedPrincipal.tenant_id (verified, trusted
boundary); it is never accepted from a request body or query parameter.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.entity_resolution.dependencies import steward_api_service
from app.api.entity_resolution.schemas import (
    CaseDetailResponse,
    CaseListResponse,
    DecisionRequest,
    DecisionResponse,
    PolicyListResponse,
    PreviewResponse,
)
from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.entity_resolution_steward_api import (
    QUEUE_OUTCOMES,
    CaseNotFoundError,
    EntityResolutionStewardApiService,
    IncompleteSourceProvenanceError,
    NoEvidenceProfileError,
    PolicyNotFoundError,
)
from app.core.dependency_container import Container
from app.domain.identity_resolution.service import OverrideNotPermittedError
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.entity_resolution_store import StaleResolutionCaseError

router = APIRouter(prefix="/api/v1/entity-resolution", tags=["entity-resolution"])

_ENDPOINT_CLASSIFICATION = "ENTITY_RESOLUTION_STEWARD_API_V1"


@router.get("/cases", response_model=CaseListResponse)
def list_cases(
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[EntityResolutionStewardApiService, Depends(steward_api_service)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    outcome: Annotated[str | None, Query()] = None,
) -> CaseListResponse:
    _authorize(authenticated, "entity-resolution:read", dependencies, correlation)
    _rate_limit(authenticated, dependencies)
    outcomes = QUEUE_OUTCOMES
    if outcome is not None:
        if outcome not in QUEUE_OUTCOMES:
            raise HTTPException(400, detail={"code": "INVALID_OUTCOME_FILTER"})
        outcomes = (outcome,)
    result = service.list_cases(authenticated, outcomes=outcomes)
    _audit(
        dependencies,
        authenticated,
        correlation,
        operation="LIST_RESOLUTION_CASES",
        category="PROTECTED_DISCLOSURE",
        outcome="PERMITTED",
        code="RESOLUTION_CASE_QUEUE_READ",
    )
    return result


@router.get("/cases/{understanding_key}", response_model=CaseDetailResponse)
def get_case(
    understanding_key: str,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[EntityResolutionStewardApiService, Depends(steward_api_service)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
) -> CaseDetailResponse:
    _authorize(authenticated, "entity-resolution:read", dependencies, correlation)
    _rate_limit(authenticated, dependencies)
    try:
        result = service.get_case(authenticated, understanding_key)
    except IncompleteSourceProvenanceError as exc:
        raise HTTPException(500, detail={"code": "SOURCE_PROVENANCE_INCOMPLETE"}) from exc
    if result is None:
        raise HTTPException(404, detail={"code": "RESOLUTION_CASE_NOT_FOUND"})
    _audit(
        dependencies,
        authenticated,
        correlation,
        operation="READ_RESOLUTION_CASE",
        category="PROTECTED_DISCLOSURE",
        outcome="PERMITTED",
        code="RESOLUTION_CASE_READ",
    )
    return result


@router.get("/policies", response_model=PolicyListResponse)
def list_policies(
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[EntityResolutionStewardApiService, Depends(steward_api_service)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
) -> PolicyListResponse:
    _authorize(authenticated, "entity-resolution:read", dependencies, correlation)
    _rate_limit(authenticated, dependencies)
    result = service.list_policies(authenticated)
    _audit(
        dependencies,
        authenticated,
        correlation,
        operation="LIST_RESOLUTION_POLICIES",
        category="PROTECTED_DISCLOSURE",
        outcome="PERMITTED",
        code="RESOLUTION_POLICY_LIST_READ",
    )
    return result


@router.post("/cases/{understanding_key}/preview", response_model=PreviewResponse)
def preview_policy(
    understanding_key: str,
    policy_id: Annotated[UUID, Query()],
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[EntityResolutionStewardApiService, Depends(steward_api_service)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
) -> PreviewResponse:
    """Read-only: evaluates Gate B's deterministic decide() against the
    case's already-computed evidence profile and a candidate policy. Never
    appends or mutates anything."""
    _authorize(authenticated, "entity-resolution:read", dependencies, correlation)
    _rate_limit(authenticated, dependencies)
    try:
        result = service.preview(authenticated, understanding_key, policy_id)
    except CaseNotFoundError as exc:
        raise HTTPException(404, detail={"code": "RESOLUTION_CASE_NOT_FOUND"}) from exc
    except PolicyNotFoundError as exc:
        raise HTTPException(404, detail={"code": "RESOLUTION_POLICY_NOT_FOUND"}) from exc
    except NoEvidenceProfileError as exc:
        raise HTTPException(422, detail={"code": "NO_EVIDENCE_PROFILE_TO_PREVIEW"}) from exc
    _audit(
        dependencies,
        authenticated,
        correlation,
        operation="PREVIEW_RESOLUTION_POLICY",
        category="PROTECTED_DISCLOSURE",
        outcome="PERMITTED",
        code="RESOLUTION_POLICY_PREVIEW_READ",
    )
    return result


@router.post(
    "/cases/{understanding_key}/decisions",
    response_model=DecisionResponse,
    status_code=201,
)
def decide_case(
    understanding_key: str,
    body: DecisionRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[EntityResolutionStewardApiService, Depends(steward_api_service)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
) -> DecisionResponse:
    _authorize(authenticated, "entity-resolution:decide", dependencies, correlation)
    _rate_limit(authenticated, dependencies)
    audit = _required_audit(dependencies)
    audit.record(
        operation="DECIDE_RESOLUTION_CASE",
        category="STEWARD_DECISION",
        outcome="AUTHORIZED",
        code="RESOLUTION_DECISION_AUTHORIZED",
        correlation_id=correlation,
        principal=authenticated,
        endpoint_classification=_ENDPOINT_CLASSIFICATION,
    )
    try:
        result = service.decide_case(authenticated, understanding_key, body)
    except CaseNotFoundError as exc:
        raise HTTPException(404, detail={"code": "RESOLUTION_CASE_NOT_FOUND"}) from exc
    except PolicyNotFoundError as exc:
        raise HTTPException(404, detail={"code": "RESOLUTION_POLICY_NOT_FOUND"}) from exc
    except NoEvidenceProfileError as exc:
        raise HTTPException(422, detail={"code": "NO_EVIDENCE_PROFILE_TO_DECIDE"}) from exc
    except StaleResolutionCaseError as exc:
        audit.record(
            operation="DECIDE_RESOLUTION_CASE",
            category="STEWARD_DECISION",
            outcome="REJECTED",
            code="STALE_RESOLUTION_CASE",
            correlation_id=correlation,
            principal=authenticated,
            endpoint_classification=_ENDPOINT_CLASSIFICATION,
        )
        raise HTTPException(409, detail={"code": "STALE_RESOLUTION_CASE"}) from exc
    except OverrideNotPermittedError as exc:
        audit.record(
            operation="DECIDE_RESOLUTION_CASE",
            category="STEWARD_DECISION",
            outcome="REJECTED",
            code="OVERRIDE_NOT_PERMITTED",
            correlation_id=correlation,
            principal=authenticated,
            endpoint_classification=_ENDPOINT_CLASSIFICATION,
        )
        raise HTTPException(422, detail={"code": "OVERRIDE_NOT_PERMITTED"}) from exc
    except ValidationException as exc:
        audit.record(
            operation="DECIDE_RESOLUTION_CASE",
            category="STEWARD_DECISION",
            outcome="REJECTED",
            code="DECISION_NOT_PERMITTED",
            correlation_id=correlation,
            principal=authenticated,
            endpoint_classification=_ENDPOINT_CLASSIFICATION,
        )
        raise HTTPException(422, detail={"code": "DECISION_NOT_PERMITTED"}) from exc
    audit.record(
        operation="DECIDE_RESOLUTION_CASE",
        category="STEWARD_DECISION",
        outcome="ACCEPTED",
        code="RESOLUTION_DECISION_ACCEPTED",
        correlation_id=correlation,
        principal=authenticated,
        execution_id=result.record_id,
        endpoint_classification=_ENDPOINT_CLASSIFICATION,
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
    correlation: UUID,
) -> None:
    if scope in authenticated.scopes:
        return
    audit = dependencies.security_audit
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
    raise HTTPException(403, detail={"code": "AUTHORIZATION_SCOPE_REQUIRED"})


def _audit(
    dependencies: Container,
    authenticated: TrustedPrincipal,
    correlation: UUID,
    *,
    operation: str,
    category: str,
    outcome: str,
    code: str,
) -> None:
    if dependencies.security_audit is None:
        return
    dependencies.security_audit.record(
        operation=operation,
        category=category,
        outcome=outcome,
        code=code,
        correlation_id=correlation,
        principal=authenticated,
        endpoint_classification=_ENDPOINT_CLASSIFICATION,
    )


def _rate_limit(authenticated: TrustedPrincipal, dependencies: Container) -> None:
    if dependencies.rate_limiter and not dependencies.rate_limiter.admit(authenticated.tenant_id):
        raise HTTPException(429, detail={"code": "RATE_LIMITED"})
