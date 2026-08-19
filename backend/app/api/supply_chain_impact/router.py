"""Gate F Supply Chain Impact API v1 routes (CDD-015 §16, §21, §32; PAD-003
§2a-§4a). Reuses Gate E's authentication (OIDC bearer token ->
TrustedPrincipal), scope authorization, and security-audit infrastructure
exactly, following the `api/entity_resolution/router.py` precedent -- there
is no separate mechanism here. Tenant identity always comes from
TrustedPrincipal.tenant_id (verified, trusted boundary); it is never
accepted from a request body, query, or path parameter.

Two independent, non-compositional scopes (PAD-003 §4a):
`supply-chain-impact:read` (retrieve an already-persisted evaluation) and
`supply-chain-impact:evaluate` (initiate a new governed evaluation). An
evaluate call's response may include that call's own freshly-created
result without separately holding `:read` (PAD-003 §3a/§4a's own-result
carve-out) -- this router does not check `:read` on the evaluate route,
and does not check `:evaluate` on the read route.

The evaluate route stays thin: it delegates the entire governed
computation to the already-implemented, already-governed
`SupplyChainImpactApiService` (CDD-015 §33) -- no ontology traversal, KRM,
DRM, or GRM logic is reproduced here. The read route performs a
tenant-scoped lookup through the existing PUBLIC
`DecisionEvaluationRepositoryImpl`/`GovernanceEvaluationRepositoryImpl`
read contracts only -- it never calls a private `_to_orm`/`_to_domain`
conversion directly from outside those repositories, and it never re-runs
the F-I2 evaluation: a read returns exactly the persisted, decision-time
result (CDD-015 §20)."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.api.supply_chain_impact import schemas
from app.api.supply_chain_impact.dependencies import (
    supply_chain_impact_api_service,
    supply_chain_impact_sessions,
)
from app.api.supply_chain_impact.schemas import (
    CandidateOutcomeResponse,
    DecisionEvaluationRecordResponse,
    GovernanceEvaluationRecordResponse,
    ImpactedEntityResponse,
    ImpactedMaterialResponse,
    ImpactSummaryResponse,
    MaterialEvaluationResultResponse,
    SupplyChainImpactEvaluateResponse,
    SupplyChainImpactReadResponse,
)
from app.application import supply_chain_impact_api as gate_f_service
from app.core.dependency_container import Container
from app.domain.decision_engine.configuration import (
    GATE_F_POLICY_REFERENCE,
    GATE_F_POLICY_VERSION,
)
from app.domain.governance_engine import GovernanceOutcome
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.decision_repository import DecisionEvaluationRepositoryImpl
from app.infrastructure.persistence.governance_repository import GovernanceEvaluationRepositoryImpl

router = APIRouter(prefix="/api/v1/supply-chain-impact", tags=["supply-chain-impact"])

_ENDPOINT_CLASSIFICATION = "SUPPLY_CHAIN_IMPACT_API_V1"


@router.post(
    "/evaluations",
    response_model=SupplyChainImpactEvaluateResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate(
    body: schemas.SupplyChainImpactEvaluateRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    service: Annotated[
        gate_f_service.SupplyChainImpactApiService, Depends(supply_chain_impact_api_service)
    ],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
) -> SupplyChainImpactEvaluateResponse:
    _authorize(authenticated, "supply-chain-impact:evaluate", dependencies, correlation)
    _rate_limit(authenticated, dependencies)
    audit = _required_audit(dependencies)
    audit.record(
        operation="EVALUATE_SUPPLY_CHAIN_IMPACT",
        category="GOVERNED_EVALUATION",
        outcome="AUTHORIZED",
        code="EVALUATION_AUTHORIZED",
        correlation_id=correlation,
        principal=authenticated,
        endpoint_classification=_ENDPOINT_CLASSIFICATION,
    )
    try:
        result = service.evaluate(
            authenticated,
            gate_f_service.SupplyChainImpactEvaluateRequest(
                supplier_entity_id=body.supplier_entity_id
            ),
        )
    except ValidationException as exc:
        audit.record(
            operation="EVALUATE_SUPPLY_CHAIN_IMPACT",
            category="GOVERNED_EVALUATION",
            outcome="REJECTED",
            code="SUPPLY_CHAIN_IMPACT_TARGET_NOT_FOUND",
            correlation_id=correlation,
            principal=authenticated,
            endpoint_classification=_ENDPOINT_CLASSIFICATION,
        )
        raise HTTPException(404, detail={"code": "SUPPLY_CHAIN_IMPACT_TARGET_NOT_FOUND"}) from exc
    audit.record(
        operation="EVALUATE_SUPPLY_CHAIN_IMPACT",
        category="GOVERNED_EVALUATION",
        outcome="ACCEPTED",
        code="EVALUATION_ACCEPTED",
        correlation_id=correlation,
        principal=authenticated,
        execution_id=result.decision_evaluation_id,
        endpoint_classification=_ENDPOINT_CLASSIFICATION,
    )
    return SupplyChainImpactEvaluateResponse(
        decision_evaluation_id=result.decision_evaluation_id,
        impact=ImpactSummaryResponse(
            supplier_entity_id=result.impact.supplier_entity_id,
            supplier_name=result.impact.supplier_name,
            materials=[
                ImpactedMaterialResponse(
                    material_entity_id=material.material_entity_id,
                    material_name=material.material_name,
                )
                for material in result.impact.materials
            ],
            products=[
                ImpactedEntityResponse(entity_id=item.entity_id, entity_name=item.entity_name)
                for item in result.impact.products
            ],
            facilities=[
                ImpactedEntityResponse(entity_id=item.entity_id, entity_name=item.entity_name)
                for item in result.impact.facilities
            ],
            revenue_exposures=[
                ImpactedEntityResponse(entity_id=item.entity_id, entity_name=item.entity_name)
                for item in result.impact.revenue_exposures
            ],
        ),
        materials=[
            MaterialEvaluationResultResponse(
                material_entity_id=material.material_entity_id,
                high_severity_disruption=material.high_severity_disruption,
                single_source_exposure=material.single_source_exposure,
                revenue_materiality=material.revenue_materiality,
                candidates=[
                    CandidateOutcomeResponse(
                        alternate_supplier_entity_id=candidate.alternate_supplier_entity_id,
                        outcome=candidate.outcome,
                        reason=candidate.reason,
                        decision_record_identifier=candidate.decision_record_identifier,
                    )
                    for candidate in material.candidates
                ],
            )
            for material in result.materials
        ],
        governance_standing=result.governance_standing,
        governance_record_identifier=result.governance_record_identifier,
        policy_reference=GATE_F_POLICY_REFERENCE,
        policy_version=GATE_F_POLICY_VERSION,
    )


@router.get(
    "/evaluations/{decision_evaluation_id}",
    response_model=SupplyChainImpactReadResponse,
)
def get_evaluation(
    decision_evaluation_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    sessions: Annotated["sessionmaker[Session]", Depends(supply_chain_impact_sessions)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
) -> SupplyChainImpactReadResponse:
    _authorize(authenticated, "supply-chain-impact:read", dependencies, correlation)
    _rate_limit(authenticated, dependencies)
    with sessions() as session:
        decision_repository = DecisionEvaluationRepositoryImpl(session)
        group = decision_repository.group_by_id(
            decision_evaluation_id, tenant_id=authenticated.tenant_id
        )
        if group is None:
            # Tenant-scoped lookup never distinguishes "does not exist"
            # from "belongs to another tenant" -- a cross-tenant read must
            # not leak existence (CDD-015 §19, §25).
            raise HTTPException(404, detail={"code": "SUPPLY_CHAIN_IMPACT_EVALUATION_NOT_FOUND"})
        records = decision_repository.records_for_group(
            decision_evaluation_id, tenant_id=authenticated.tenant_id
        )
        governance_projection = GovernanceEvaluationRepositoryImpl(session).current(
            decision_evaluation_id, GATE_F_POLICY_REFERENCE, as_of=datetime.now(UTC)
        )
    _audit_disclosure(dependencies, authenticated, correlation, decision_evaluation_id)
    governance_record = governance_projection.record
    return SupplyChainImpactReadResponse(
        decision_evaluation_id=group.decision_evaluation_id,
        created_at=group.created_at.isoformat(),
        records=[
            DecisionEvaluationRecordResponse(
                record_identifier=record.record_identifier,
                outcome=record.evaluation_outcome.value,
                recommendation=record.decision_recommendation.value,
                confidence=record.decision_confidence.level.value,
                structured_reasons=list(record.decision_explanation.structured_reasons),
                narrative=record.decision_explanation.narrative,
                knowledge_references=[item.value for item in record.knowledge_references],
                policy_reference=record.governing_policy_reference.value,
                policy_version=record.policy_version.value,
                effective_from=record.effective_from.isoformat(),
                produced_timestamp=record.produced_timestamp.isoformat(),
            )
            for record in records
        ],
        governance=(
            GovernanceEvaluationRecordResponse(
                record_identifier=governance_record.record_identifier,
                governance_outcome=governance_record.governance_outcome.value,
                human_approval_required=(
                    governance_record.governance_outcome is GovernanceOutcome.REQUIRES_REVIEW
                ),
                policy_reference=governance_record.governing_policy_reference.value,
                policy_version=governance_record.policy_version.value,
                effective_from=governance_record.effective_from.isoformat(),
                produced_timestamp=governance_record.produced_timestamp.isoformat(),
            )
            if governance_record is not None
            else None
        ),
    )


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


def _audit_disclosure(
    dependencies: Container,
    authenticated: TrustedPrincipal,
    correlation: UUID,
    decision_evaluation_id: UUID,
) -> None:
    _required_audit(dependencies).record(
        operation="READ_SUPPLY_CHAIN_IMPACT_EVALUATION",
        category="PROTECTED_DISCLOSURE",
        outcome="PERMITTED",
        code="SUPPLY_CHAIN_IMPACT_EVALUATION_READ",
        correlation_id=correlation,
        principal=authenticated,
        execution_id=decision_evaluation_id,
        endpoint_classification=_ENDPOINT_CLASSIFICATION,
    )


def _rate_limit(authenticated: TrustedPrincipal, dependencies: Container) -> None:
    if dependencies.rate_limiter and not dependencies.rate_limiter.admit(authenticated.tenant_id):
        raise HTTPException(429, detail={"code": "RATE_LIMITED"})
