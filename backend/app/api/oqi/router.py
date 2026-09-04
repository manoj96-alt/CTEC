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
    AssertGovernedReferenceDatasetRequest,
    BusinessImpactDependency,
    BusinessImpactResponse,
    BusinessImpactResultView,
    CommandCenterResponse,
    DecideAuthorizationRequest,
    DimensionResultView,
    EvaluateRequest,
    EvaluateResponse,
    EvidenceCandidate,
    EvidenceParticipant,
    EvidenceResponse,
    FindingDetailResponse,
    FindingListResponse,
    FindingSummary,
    OntologyImpactPathSegment,
    OntologyImpactResponse,
    OntologyImpactResultView,
    RecordHumanVerifiedEvidenceRequest,
    ReferenceEvidenceAssertionResponse,
    ReferenceEvidenceConflictListResponse,
    ReferenceEvidenceConflictResponse,
    RelianceHistoryEntry,
    RelianceResponse,
    RelianceResultView,
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
from app.application.oqi_evaluation_orchestration_service import (
    OqiEvaluationOrchestrationService,
)
from app.application.oqi_product_experience_service import (
    OqiProductExperienceService,
)
from app.application.oqi_reference_evidence_service import (
    OqiReferenceEvidenceError,
    OqiReferenceEvidenceService,
)
from app.application.oqi_remediation_service import OqiRemediationError
from app.core.dependency_container import Container
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.infrastructure.persistence.oqi_reference_evidence_repository import (
    OqiReferenceEvidenceRepositoryImpl,
)

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


def reference_evidence_service(
    session: Annotated[Session, Depends(oqi_session)],
) -> OqiReferenceEvidenceService:
    return OqiReferenceEvidenceService(repository=OqiReferenceEvidenceRepositoryImpl(session))


def evaluation_orchestration_service(
    session: Annotated[Session, Depends(oqi_session)],
) -> OqiEvaluationOrchestrationService:
    return OqiEvaluationOrchestrationService(session)


_REFERENCE_EVIDENCE_ERROR_HTTP_STATUS: dict[str, int] = {}


def _assertion_view(assertion: object) -> ReferenceEvidenceAssertionResponse:
    return ReferenceEvidenceAssertionResponse(
        assertion_id=assertion.assertion_id,  # type: ignore[attr-defined]
        ontology_element_type=assertion.ontology_element_type.value,  # type: ignore[attr-defined]
        ontology_element_id=assertion.ontology_element_id,  # type: ignore[attr-defined]
        source_field_id=assertion.source_field_id,  # type: ignore[attr-defined]
        form=assertion.form.value,  # type: ignore[attr-defined]
        asserted_value=assertion.asserted_value,  # type: ignore[attr-defined]
        status=assertion.status.value,  # type: ignore[attr-defined]
        version_number=assertion.version_number,  # type: ignore[attr-defined]
        created_by=assertion.created_by,  # type: ignore[attr-defined]
        created_on=assertion.created_on,  # type: ignore[attr-defined]
    )


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


@router.post(
    "/reference-evidence/governed-dataset",
    response_model=ReferenceEvidenceAssertionResponse,
)
def assert_governed_reference_dataset(
    body: AssertGovernedReferenceDatasetRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiReferenceEvidenceService, Depends(reference_evidence_service)],
) -> ReferenceEvidenceAssertionResponse:
    """CDD-048 §10.1, §26: configuration-authority operation --
    `oqi-reference-evidence:configure`. CDD-048 OQI-H2-I-R1 §8:
    `created_by` is populated exclusively from the authenticated principal
    -- never accepted from the request body."""
    authorize(authenticated, "oqi-reference-evidence:configure", dependencies, correlation)
    try:
        assertion = service.assert_governed_reference_dataset(
            tenant_id=authenticated.tenant_id,
            ontology_element_type=OntologyElementType(body.ontology_element_type),
            ontology_element_id=body.ontology_element_id,
            source_field_id=body.source_field_id,
            asserted_value=body.asserted_value,
            dataset_name=body.dataset_name,
            dataset_version=body.dataset_version,
            entry_key=body.entry_key,
            created_by=authenticated.principal_id,
        )
    except OqiReferenceEvidenceError as exc:
        raise HTTPException(409, detail={"code": exc.code}) from exc
    return _assertion_view(assertion)


@router.post(
    "/reference-evidence/human-verified",
    response_model=ReferenceEvidenceAssertionResponse,
)
def record_human_verified_evidence(
    body: RecordHumanVerifiedEvidenceRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[OqiReferenceEvidenceService, Depends(reference_evidence_service)],
) -> ReferenceEvidenceAssertionResponse:
    """CDD-048 §11, §17, §26, PO-03: verification-authority operation --
    `oqi-reference-evidence:verify`, distinct from and never substitutable
    by `oqi-reference-evidence:configure` or any remediation scope.
    CDD-048 OQI-H2-I-R1 §8 (P1 provenance correction): `verifying_actor_id`
    and `created_by` are populated exclusively from the authenticated
    principal's own verified JWT subject -- never from the request body, a
    query parameter, or any header. An authenticated Bob can never cause
    "Alice" to be persisted as the verifying actor."""
    authorize(authenticated, "oqi-reference-evidence:verify", dependencies, correlation)
    try:
        assertion = service.record_human_verified_evidence(
            tenant_id=authenticated.tenant_id,
            ontology_element_type=OntologyElementType(body.ontology_element_type),
            ontology_element_id=body.ontology_element_id,
            source_field_id=body.source_field_id,
            asserted_value=body.asserted_value,
            verifying_actor_id=authenticated.principal_id,
            verification_rationale=body.verification_rationale,
            created_by=authenticated.principal_id,
        )
    except OqiReferenceEvidenceError as exc:
        raise HTTPException(409, detail={"code": exc.code}) from exc
    return _assertion_view(assertion)


@router.get(
    "/reference-evidence/conflicts",
    response_model=ReferenceEvidenceConflictListResponse,
)
def list_reference_evidence_conflicts(
    ontology_element_type: str,
    ontology_element_id: UUID,
    source_field_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    session: Annotated[Session, Depends(oqi_session)],
) -> ReferenceEvidenceConflictListResponse:
    """CDD-048 §16, §29: read-only, gated by the existing `oqi:read` scope
    (mirrors every other OQI read route) -- never labeled as a Quality
    Finding, never implying Noetva chose a value; surfaces only that a
    defensible reference basis is currently absent for this subject."""
    _require_read(authenticated, dependencies, correlation)
    repository = OqiReferenceEvidenceRepositoryImpl(session)
    conflict = repository.find_active_conflict_for_subject(
        tenant_id=authenticated.tenant_id,
        ontology_element_type=OntologyElementType(ontology_element_type),
        ontology_element_id=ontology_element_id,
        source_field_id=source_field_id,
    )
    items = (
        ()
        if conflict is None
        else (
            ReferenceEvidenceConflictResponse(
                conflict_id=conflict.conflict_id,
                ontology_element_type=conflict.ontology_element_type.value,
                ontology_element_id=conflict.ontology_element_id,
                source_field_id=conflict.source_field_id,
                conflicting_assertion_ids=conflict.conflicting_assertion_ids,
                status=conflict.status.value,
                first_detected_at=conflict.first_detected_at,
                last_observed_at=conflict.last_observed_at,
            ),
        )
    )
    return ReferenceEvidenceConflictListResponse(items=items)


@router.post("/evaluate", response_model=EvaluateResponse, status_code=202)
def evaluate(
    body: EvaluateRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[
        OqiEvaluationOrchestrationService, Depends(evaluation_orchestration_service)
    ],
) -> EvaluateResponse:
    """CDD-056 §7-§9: explicit, tenant-scoped production evaluation trigger.
    Tenant authority is sourced exclusively from `authenticated.tenant_id`
    -- `EvaluateRequest` carries no `tenant_id` field at all."""
    authorize(authenticated, "oqi-evaluation:trigger", dependencies, correlation)
    result = service.evaluate(
        tenant_id=authenticated.tenant_id,
        information_element_requirement_id=body.information_element_requirement_id,
        source_record_reference=body.source_record_reference,
        business_process_id=body.business_process_id,
        business_process_version=body.business_process_version,
        correlation_id=body.correlation_id,
    )
    return EvaluateResponse(
        correlation_id=result.correlation_id,
        evaluated_at=result.evaluated_at,
        dimensions=tuple(
            DimensionResultView(
                dimension=d.dimension,
                status=d.status,
                evaluation_id=d.evaluation_id,
                outcome=d.outcome,
            )
            for d in result.dimensions
        ),
        ontology_impact=OntologyImpactResultView(
            status=result.ontology_impact.status, outcome=result.ontology_impact.outcome
        ),
        business_impact=tuple(
            BusinessImpactResultView(
                dependency_id=b.dependency_id, status=b.status, outcome=b.outcome
            )
            for b in result.business_impact
        ),
        reliance=RelianceResultView(status=result.reliance.status, state=result.reliance.state),
    )
