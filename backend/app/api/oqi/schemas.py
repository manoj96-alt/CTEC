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

from pydantic import BaseModel


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
