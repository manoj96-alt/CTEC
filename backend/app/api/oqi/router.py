"""CDD-045 §22-§23 -- `/api/v1/oqi` product-serving read routes plus the two
thin remediation-action HTTP wrappers. Tenant context comes exclusively
from `TrustedPrincipal.tenant_id` (never a client-supplied parameter,
CDD-045 §22/§59). Every read route requires `oqi:read`; the two action
routes each require their own narrow scope, mirroring Gate S's
`governed-approval:decide`/`request` two-scope pattern -- neither scope
ever implies the other."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.oqi.dependencies import authorize
from app.api.oqi.schemas import (
    AgentInvestigationResponse,
    AgentRecommendationView,
    BusinessImpactDependency,
    BusinessImpactResponse,
    CommandCenterResponse,
    DecideAuthorizationRequest,
    EvidenceCandidate,
    EvidenceParticipant,
    EvidenceResponse,
    FindingDetailResponse,
    FindingListResponse,
    FindingSummary,
    OntologyImpactPathSegment,
    OntologyImpactResponse,
    RelianceHistoryEntry,
    RelianceResponse,
    RemediationAuthorizationView,
    RemediationCandidateView,
    RemediationCaseActionResponse,
    RemediationExternalExecutionView,
    RemediationResponse,
    ReportExecutionRequest,
    SpecialistAssessmentView,
)
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.oqi_product_experience_service import (
    OqiProductExperienceService,
)
from app.application.oqi_remediation_service import OqiRemediationError
from app.core.dependency_container import Container

router = APIRouter(prefix="/api/v1/oqi", tags=["oqi"])

_ENDPOINT_CLASSIFICATION = "OQI_API_V1"

_REMEDIATION_ERROR_HTTP_STATUS: dict[str, int] = {
    "REMEDIATION_FINDING_NOT_FOUND": 404,
    "REMEDIATION_TENANT_MISMATCH": 404,
    "REMEDIATION_SELF_APPROVAL_PROHIBITED": 403,
    "REMEDIATION_AUTHORIZATION_NOT_PENDING": 409,
    "REMEDIATION_AUTHORIZATION_ALREADY_CONSUMED": 409,
    "REMEDIATION_ACTION_MISMATCH": 409,
}


def oqi_session(value: Annotated[Container, Depends(container)]) -> Iterator[Session]:
    if value.ontology_sessions is None:
        raise HTTPException(503, detail={"code": "OQI_SERVICE_UNAVAILABLE"})
    session = value.ontology_sessions()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def oqi_service(
    session: Annotated[Session, Depends(oqi_session)],
) -> OqiProductExperienceService:
    return OqiProductExperienceService(session)


def _require_read(
    authenticated: TrustedPrincipal, dependencies: Container, correlation: UUID
) -> None:
    authorize(authenticated, "oqi:read", dependencies, correlation)


def _recommendation_view(row: object | None) -> AgentRecommendationView | None:
    if row is None:
        return None
    return AgentRecommendationView(
        recommendation_type=row.recommendation_type,  # type: ignore[attr-defined]
        candidate_id=row.candidate_id,  # type: ignore[attr-defined]
        rationale=row.rationale,  # type: ignore[attr-defined]
        basis=row.basis,  # type: ignore[attr-defined]
    )


@router.get("/command-center", response_model=CommandCenterResponse)
def get_command_center(
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> CommandCenterResponse:
    _require_read(authenticated, dependencies, correlation)
    row = service.get_command_center(tenant_id=authenticated.tenant_id)
    return CommandCenterResponse(
        reliance_supported_count=row.reliance_supported_count,
        reliance_at_risk_count=row.reliance_at_risk_count,
        reliance_unknown_count=row.reliance_unknown_count,
        critical_dependencies_at_risk_count=row.critical_dependencies_at_risk_count,
        open_findings_count=row.open_findings_count,
        active_agent_investigations_count=row.active_agent_investigations_count,
        pending_human_authorizations_count=row.pending_human_authorizations_count,
    )


@router.get("/findings", response_model=FindingListResponse)
def list_findings(
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
    family: str | None = Query(default=None),
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> FindingListResponse:
    _require_read(authenticated, dependencies, correlation)
    rows, next_cursor = service.list_findings(
        tenant_id=authenticated.tenant_id,
        family=family,
        status=status,
        limit=limit,
        cursor=cursor,
    )
    items = tuple(
        FindingSummary(
            finding_id=row.finding.finding_id,
            finding_family=row.finding.family.value,
            condition_label=row.finding.condition_label,
            status=row.finding.status,
            first_seen_at=row.finding.first_seen_at,
            last_seen_at=row.finding.last_seen_at,
            affected_entity_id=row.affected_entity_id,
            affected_entity_type=row.affected_entity_type,
            highest_criticality=(
                row.highest_criticality.value if row.highest_criticality is not None else None
            ),
            reliance_state=row.reliance_state.value if row.reliance_state is not None else None,
        )
        for row in rows
    )
    return FindingListResponse(items=items, next_cursor=next_cursor)


@router.get("/findings/{finding_id}", response_model=FindingDetailResponse)
def get_finding_detail(
    finding_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> FindingDetailResponse:
    _require_read(authenticated, dependencies, correlation)
    row = service.get_finding_detail(tenant_id=authenticated.tenant_id, finding_id=finding_id)
    if row is None:
        raise HTTPException(404, detail={"code": "OQI_FINDING_NOT_FOUND"})
    return FindingDetailResponse(
        finding_id=row.finding_id,
        finding_family=row.family.value,
        condition_label=row.condition_label,
        status=row.status,
        state_revision=row.state_revision,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
    )


@router.get("/findings/{finding_id}/evidence", response_model=EvidenceResponse)
def get_evidence(
    finding_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> EvidenceResponse:
    _require_read(authenticated, dependencies, correlation)
    bundle = service.get_evidence(tenant_id=authenticated.tenant_id, finding_id=finding_id)
    if bundle is None:
        raise HTTPException(404, detail={"code": "OQI_FINDING_NOT_FOUND"})
    candidate = (
        EvidenceCandidate(
            candidate_id=bundle.candidate.candidate_id,
            proposed_value=bundle.candidate.proposed_value,
            supporting_participant_count=bundle.candidate.supporting_participant_count,
        )
        if bundle.candidate is not None
        else None
    )
    participants = tuple(
        EvidenceParticipant(
            source_system=p.source_system,
            observed_value=p.observed_value,
            is_missing=p.is_missing,
            is_authoritative=p.is_authoritative,
            is_conflicting=p.is_conflicting,
        )
        for p in bundle.participants
    )
    return EvidenceResponse(participants=participants, candidate=candidate)


@router.get("/findings/{finding_id}/ontology-impact", response_model=OntologyImpactResponse)
def get_ontology_impact(
    finding_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> OntologyImpactResponse:
    _require_read(authenticated, dependencies, correlation)
    row = service.get_ontology_impact(tenant_id=authenticated.tenant_id, finding_id=finding_id)
    if row is None:
        raise HTTPException(404, detail={"code": "OQI_FINDING_NOT_FOUND"})
    propagated_path = (
        tuple(
            OntologyImpactPathSegment(
                relationship_instance_id=segment.relationship_instance_id,
                path_ordinal=segment.path_ordinal,
                direction=segment.direction,
            )
            for segment in row.propagated_path
        )
        if row.propagated_path is not None
        else None
    )
    return OntologyImpactResponse(
        outcome=row.outcome.value,
        direct_entity_id=row.direct_entity_id,
        direct_entity_type=row.direct_entity_type.value if row.direct_entity_type else None,
        propagated_path=propagated_path,
    )


@router.get("/findings/{finding_id}/business-impact", response_model=BusinessImpactResponse)
def get_business_impact(
    finding_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> BusinessImpactResponse:
    _require_read(authenticated, dependencies, correlation)
    row = service.get_business_impact(tenant_id=authenticated.tenant_id, finding_id=finding_id)
    if row is None:
        raise HTTPException(404, detail={"code": "OQI_FINDING_NOT_FOUND"})
    dependencies_view = tuple(
        BusinessImpactDependency(
            business_process_name=d.business_process_name,
            criticality=d.criticality.value if d.criticality is not None else None,
            business_dependency_version=d.business_dependency_version,
        )
        for d in row.dependencies
    )
    return BusinessImpactResponse(outcome=row.outcome.value, dependencies=dependencies_view)


@router.get("/findings/{finding_id}/reliance", response_model=RelianceResponse)
def get_reliance(
    finding_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> RelianceResponse:
    _require_read(authenticated, dependencies, correlation)
    row = service.get_reliance(tenant_id=authenticated.tenant_id, finding_id=finding_id)
    if row is None:
        raise HTTPException(404, detail={"code": "OQI_FINDING_NOT_FOUND"})
    return RelianceResponse(
        state=row.state.value,
        reason_codes=tuple(row.reason_codes),
        contributing_finding_ids=row.contributing_finding_ids,
        history=tuple(
            RelianceHistoryEntry(state=h.state.value, evaluated_at=h.evaluated_at)
            for h in row.history
        ),
    )


@router.get("/findings/{finding_id}/agent-investigation", response_model=AgentInvestigationResponse)
def get_agent_investigation(
    finding_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> AgentInvestigationResponse:
    _require_read(authenticated, dependencies, correlation)
    row = service.get_agent_investigation(tenant_id=authenticated.tenant_id, finding_id=finding_id)
    if row is None:
        raise HTTPException(404, detail={"code": "OQI_FINDING_NOT_FOUND"})
    specialists = tuple(
        SpecialistAssessmentView(
            role_id=s.role_id,
            result_state=s.result_state,
            assessment_text=s.assessment_text,
            referenced_candidate_id=s.referenced_candidate_id,
        )
        for s in row.specialists
    )
    return AgentInvestigationResponse(
        specialists=specialists, recommendation=_recommendation_view(row.recommendation)
    )


@router.get("/findings/{finding_id}/remediation", response_model=RemediationResponse)
def get_remediation(
    finding_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> RemediationResponse:
    _require_read(authenticated, dependencies, correlation)
    row = service.get_remediation(tenant_id=authenticated.tenant_id, finding_id=finding_id)
    if row is None:
        raise HTTPException(404, detail={"code": "OQI_FINDING_NOT_FOUND"})
    candidate = (
        RemediationCandidateView(
            candidate_id=row.candidate.candidate_id, proposed_value=row.candidate.proposed_value
        )
        if row.candidate is not None
        else None
    )
    authorization = (
        RemediationAuthorizationView(
            authorization_id=row.authorization.authorization_id,
            principal=row.authorization.principal,
            decided_on=row.authorization.decided_on,
            instruction=row.authorization.instruction,
            authorized_against_state_revision=row.authorization.authorized_against_state_revision,
            is_stale=row.authorization.is_stale,
            status=row.authorization.status,
        )
        if row.authorization is not None
        else None
    )
    external_execution = (
        RemediationExternalExecutionView(reported_at=row.external_execution.reported_at)
        if row.external_execution is not None
        else None
    )
    return RemediationResponse(
        case_status=row.case_status,
        candidate=candidate,
        recommendation=_recommendation_view(row.recommendation),
        authorization=authorization,
        external_execution=external_execution,
    )


@router.post(
    "/remediation/authorizations/{authorization_id}/decide",
    response_model=RemediationCaseActionResponse,
)
def decide_authorization(
    authorization_id: UUID,
    body: DecideAuthorizationRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> RemediationCaseActionResponse:
    authorize(authenticated, "oqi-remediation:authorize", dependencies, correlation)
    try:
        status_value = service.decide_authorization(
            tenant_id=authenticated.tenant_id,
            authorization_id=authorization_id,
            approve=body.approve,
            decided_by=body.decided_by,
            rejection_reason=body.rejection_reason,
        )
    except OqiRemediationError as exc:
        raise HTTPException(
            _REMEDIATION_ERROR_HTTP_STATUS.get(exc.code, 409), detail={"code": exc.code}
        ) from exc
    return RemediationCaseActionResponse(case_status=status_value)


@router.post(
    "/remediation/authorizations/{authorization_id}/report-execution",
    response_model=RemediationCaseActionResponse,
)
def report_execution(
    authorization_id: UUID,
    body: ReportExecutionRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiProductExperienceService, Depends(oqi_service)],
) -> RemediationCaseActionResponse:
    authorize(authenticated, "oqi-remediation:report-execution", dependencies, correlation)
    _ = body
    try:
        status_value = service.report_execution(
            tenant_id=authenticated.tenant_id, authorization_id=authorization_id
        )
    except OqiRemediationError as exc:
        raise HTTPException(
            _REMEDIATION_ERROR_HTTP_STATUS.get(exc.code, 409), detail={"code": exc.code}
        ) from exc
    return RemediationCaseActionResponse(case_status=status_value)
