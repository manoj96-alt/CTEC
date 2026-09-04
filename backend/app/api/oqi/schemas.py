"""CDD-045 §23 -- Pydantic response models for every OQI7-I1 read/action
contract. Every enum field is serialized as its exact governed string value
(no downgrade, no boolean/None substitution for a domain state -- CDD-045
§78-79 discipline carried into the API boundary). No `trust_score`,
`reliability_score`, `confidence_score`, `business_impact_score`,
`criticality_score`, or `quality_health_score` field exists anywhere in this
file (CDD-045 §8)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CommandCenterResponse(BaseModel):
    reliance_supported_count: int
    reliance_at_risk_count: int
    reliance_unknown_count: int
    critical_dependencies_at_risk_count: int
    open_findings_count: int
    active_agent_investigations_count: int
    pending_human_authorizations_count: int


class FindingSummary(BaseModel):
    finding_id: UUID
    finding_family: str
    condition_label: str
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    affected_entity_id: UUID | None
    affected_entity_type: str | None
    highest_criticality: str | None
    reliance_state: str | None


class FindingListResponse(BaseModel):
    items: tuple[FindingSummary, ...]
    next_cursor: str | None


class FindingDetailResponse(BaseModel):
    finding_id: UUID
    finding_family: str
    condition_label: str
    status: str
    state_revision: int
    first_seen_at: datetime
    last_seen_at: datetime


class EvidenceParticipant(BaseModel):
    source_system: str
    observed_value: str | None
    is_missing: bool
    is_authoritative: bool
    is_conflicting: bool


class EvidenceCandidate(BaseModel):
    candidate_id: UUID
    proposed_value: str
    supporting_participant_count: int
    status: str = "CANDIDATE_NOT_TRUTH"


class EvidenceResponse(BaseModel):
    participants: tuple[EvidenceParticipant, ...]
    candidate: EvidenceCandidate | None


class OntologyImpactPathSegment(BaseModel):
    relationship_instance_id: UUID
    path_ordinal: int
    direction: str


class OntologyImpactResponse(BaseModel):
    outcome: str
    direct_entity_id: UUID | None
    direct_entity_type: str | None
    propagated_path: tuple[OntologyImpactPathSegment, ...] | None


class BusinessImpactDependency(BaseModel):
    business_process_name: str
    criticality: str | None
    business_dependency_version: int


class BusinessImpactResponse(BaseModel):
    outcome: str
    dependencies: tuple[BusinessImpactDependency, ...]


class RelianceHistoryEntry(BaseModel):
    state: str
    evaluated_at: datetime


class RelianceResponse(BaseModel):
    state: str
    reason_codes: tuple[str, ...]
    contributing_finding_ids: tuple[UUID, ...]
    history: tuple[RelianceHistoryEntry, ...]


class SpecialistAssessmentView(BaseModel):
    role_id: str
    result_state: str
    assessment_text: str | None
    referenced_candidate_id: UUID | None


class AgentRecommendationView(BaseModel):
    recommendation_type: str
    candidate_id: UUID | None
    rationale: str
    basis: str


class AgentInvestigationResponse(BaseModel):
    specialists: tuple[SpecialistAssessmentView, ...]
    recommendation: AgentRecommendationView | None


class RemediationCandidateView(BaseModel):
    candidate_id: UUID
    proposed_value: str
    status: str = "CANDIDATE_NOT_TRUTH"


class RemediationAuthorizationView(BaseModel):
    authorization_id: UUID
    principal: str
    decided_on: datetime | None
    instruction: str
    authorized_against_state_revision: int
    is_stale: bool
    status: str


class RemediationExternalExecutionView(BaseModel):
    reported_at: datetime


class RemediationResponse(BaseModel):
    case_status: str | None
    candidate: RemediationCandidateView | None
    recommendation: AgentRecommendationView | None
    authorization: RemediationAuthorizationView | None
    external_execution: RemediationExternalExecutionView | None


class DecideAuthorizationRequest(BaseModel):
    approve: bool
    decided_by: str
    rejection_reason: str | None = None


class ReportExecutionRequest(BaseModel):
    pass


class RemediationCaseActionResponse(BaseModel):
    case_status: str


# ---------------------------------------------------------------------
# CDD-048 §26, §29 -- OQI-H2 Reference Evidence configuration, human
# verification, and conflict-listing contracts. Minimal, additive; no
# broad Reference Evidence CRUD surface.
# ---------------------------------------------------------------------


class AssertGovernedReferenceDatasetRequest(BaseModel):
    """CDD-048 OQI-H2-I-R1 §8: carries no actor-identity field of any kind
    -- `created_by` is populated exclusively from the authenticated
    principal at the router boundary (`TrustedPrincipal.principal_id`),
    never accepted from the caller."""

    ontology_element_type: str
    ontology_element_id: UUID
    source_field_id: UUID
    asserted_value: str
    dataset_name: str
    dataset_version: str
    entry_key: str


class RecordHumanVerifiedEvidenceRequest(BaseModel):
    """CDD-048 OQI-H2-I-R1 §8: carries no actor-identity field of any kind
    -- `verifying_actor_id`/`created_by` are populated exclusively from the
    authenticated principal at the router boundary
    (`TrustedPrincipal.principal_id`), never accepted from the caller. An
    authenticated Bob can never cause "Alice" to be persisted as the
    verifying actor, because no code path reads an actor identity from
    anywhere other than the verified JWT subject."""

    ontology_element_type: str
    ontology_element_id: UUID
    source_field_id: UUID
    asserted_value: str
    verification_rationale: str


class ReferenceEvidenceAssertionResponse(BaseModel):
    assertion_id: UUID
    ontology_element_type: str
    ontology_element_id: UUID
    source_field_id: UUID
    form: str
    asserted_value: str
    status: str
    version_number: int
    created_by: str
    created_on: datetime


class ReferenceEvidenceConflictResponse(BaseModel):
    conflict_id: UUID
    ontology_element_type: str
    ontology_element_id: UUID
    source_field_id: UUID
    conflicting_assertion_ids: tuple[UUID, ...]
    status: str
    first_detected_at: datetime
    last_observed_at: datetime


class ReferenceEvidenceConflictListResponse(BaseModel):
    items: tuple[ReferenceEvidenceConflictResponse, ...]


class EvaluateRequest(BaseModel):
    """CDD-056 §8: no `tenant_id` field exists on this contract at all --
    tenant authority is sourced exclusively from the authenticated
    `TrustedPrincipal`, never from request-body content. `extra="forbid"`
    ensures an injected body `tenant_id` (or any other unknown field) is
    rejected with HTTP 422, never silently ignored."""

    model_config = ConfigDict(extra="forbid")

    correlation_id: UUID | None = None
    information_element_requirement_id: UUID
    source_record_reference: str
    business_process_id: UUID
    business_process_version: int


class DimensionResultView(BaseModel):
    dimension: str
    status: str
    finding_id: UUID | None = None
    outcome: str | None = None


class OntologyImpactResultView(BaseModel):
    status: str
    outcome: str | None = None


class BusinessImpactResultView(BaseModel):
    dependency_id: UUID
    status: str
    outcome: str | None = None


class RelianceResultView(BaseModel):
    status: str
    state: str | None = None


class EvaluateResponse(BaseModel):
    """CDD-056 §9: transport acceptance (`HTTP 202`) is distinct from
    domain/quality outcome -- a response containing only NOT_EVALUABLE
    dimension entries is a fully successful orchestration run."""

    correlation_id: UUID | None
    evaluated_at: datetime
    dimensions: tuple[DimensionResultView, ...]
    ontology_impact: OntologyImpactResultView
    business_impact: tuple[BusinessImpactResultView, ...]
    reliance: RelianceResultView
