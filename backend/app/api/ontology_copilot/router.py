"""Ask CTEC v1 route (Gate D, Priority 6).

Reuses the Supplier Risk API's authentication (OIDC bearer token ->
TrustedPrincipal), scope authorization, rate limiting, and security-audit
infrastructure exactly -- there is no separate mechanism here. Tenant
identity always comes from TrustedPrincipal.tenant_id (verified, trusted
boundary); it is never accepted from the request body.

Logically read-only: POST is used only because the question is a request
payload, not because this endpoint creates or mutates any record. No
ontology, enterprise-identity, institutional-relationship, governance,
decision, assertion, or knowledge record is ever written by this router.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.ontology_copilot.dependencies import ontology_copilot_api_service
from app.api.ontology_copilot.schemas import (
    AskRequest,
    AskResponse,
    EvidenceStepResponse,
    ResolvedEntityResponse,
)
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.ontology_copilot_api import AskResult, OntologyCopilotApiService
from app.core.dependency_container import Container

router = APIRouter(prefix="/api/v1/ontology-copilot", tags=["ontology-copilot"])

_ENDPOINT_CLASSIFICATION = "ONTOLOGY_COPILOT_API_V1"


def _to_response(result: AskResult) -> AskResponse:
    return AskResponse(
        status=result.status.value,
        intent=result.intent.value if result.intent is not None else None,
        answer=result.answer,
        resolved_entity=(
            ResolvedEntityResponse(
                entity_id=result.resolved_entity.entity_id,
                entity_name=result.resolved_entity.entity_name,
                entity_type_name=result.resolved_entity.entity_type_name,
            )
            if result.resolved_entity is not None
            else None
        ),
        result_names=list(result.result_names),
        evidence=[
            [
                EvidenceStepResponse(
                    step=step.step,
                    entity_id=step.entity_id,
                    entity_name=step.entity_name,
                    entity_type_name=step.entity_type_name,
                    relationship_name=step.relationship_name,
                )
                for step in path
            ]
            for path in result.evidence
        ],
        reason=result.reason,
    )


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[OntologyCopilotApiService, Depends(ontology_copilot_api_service)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
) -> AskResponse:
    _authorize(authenticated, "ontology-copilot:ask", dependencies, correlation)
    _rate_limit(authenticated, dependencies)

    result = service.ask(authenticated, body.question)

    _audit(
        dependencies,
        authenticated,
        correlation,
        operation="ASK_ONTOLOGY_QUESTION",
        category="PROTECTED_DISCLOSURE",
        outcome=result.status.value.upper(),
        code=f"ONTOLOGY_COPILOT_{result.status.value.upper()}",
    )
    return _to_response(result)


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
