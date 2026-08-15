"""Response/request models for the Entity Resolution Steward API
(Increment 3A Gate C). Every field here comes from an already-persisted
column -- see app/application/entity_resolution_steward_api.py -- and
evidence values are exactly Gate B's already-fingerprinted/normalized
EvidenceItem contents; no raw sensitive identifier is ever read or
serialized here.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceItemResponse(BaseModel):
    evidence_type: str
    compared_attributes: list[str]
    normalized_values: list[str]
    classification: str
    contribution: float
    explanation: str
    provenance: str


class EvidenceProfileResponse(BaseModel):
    items: list[EvidenceItemResponse]


class SourceRepresentationSummary(BaseModel):
    """Persisted provenance for one supporting source object: only what is
    actually stored (source object/system display names), not the
    multi-attribute SourceRepresentation used to compute evidence -- that is
    never persisted (see evidence.py's module docstring); the full,
    per-category comparison is in evidence_profile instead."""

    source_object_id: UUID
    source_object_name: str
    source_system_id: UUID
    source_system_name: str


class PriorDecisionSummary(BaseModel):
    record_id: UUID
    outcome: str
    business_confidence: str
    produced_at: str
    actor_id: str | None
    decision_rationale: str | None


class CaseSummaryResponse(BaseModel):
    understanding_key: str
    record_id: UUID
    outcome: str
    business_confidence: str
    policy_version: str
    produced_at: str
    supporting_source_object_count: int
    candidate_enterprise_entity_id: UUID | None
    candidate_enterprise_entity_name: str | None


class CaseListResponse(BaseModel):
    items: list[CaseSummaryResponse]


class CaseDetailResponse(BaseModel):
    understanding_key: str
    record_id: UUID
    outcome: str
    business_confidence: str
    structured_reasons: list[str]
    narrative_explanation: str
    produced_at: str
    policy_id: UUID | None
    policy_name: str | None
    policy_version: str
    evidence_profile: EvidenceProfileResponse | None
    candidate_enterprise_entity_id: UUID | None
    candidate_enterprise_entity_name: str | None
    source_representations: list[SourceRepresentationSummary]
    actor_id: str | None
    decision_rationale: str | None
    prior_decision_count: int
    previous_decision: PriorDecisionSummary | None


class PolicySummaryResponse(BaseModel):
    policy_id: UUID
    policy_name: str
    policy_version: str
    preset_kind: str
    resolved_threshold: float
    possible_threshold: float
    high_confidence_threshold: float
    medium_confidence_threshold: float
    min_corroborating_attributes: int
    country_conflict_severity: str
    parent_subsidiary_conflict_severity: str


class PolicyListResponse(BaseModel):
    items: list[PolicySummaryResponse]


class PreviewResponse(BaseModel):
    policy_id: UUID
    policy_name: str
    policy_version: str
    outcome: str
    business_confidence: str
    score: float
    would_change_outcome: bool
    structured_reasons: list[str]


class DecisionRequest(BaseModel):
    action: str
    rationale: str = Field(min_length=1, max_length=2000)
    based_on_record_id: UUID
    policy_id: UUID


class DecisionResponse(BaseModel):
    record_id: UUID
    understanding_key: str
    outcome: str
    business_confidence: str
    produced_at: str
    policy_id: UUID | None
    policy_version: str
    narrative_explanation: str
    structured_reasons: list[str]
