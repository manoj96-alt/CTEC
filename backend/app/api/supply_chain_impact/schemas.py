"""Request/response models for the Gate F Supply Chain Impact API
(CDD-015 §16, §21, §32). Every response field comes from an already
governed/persisted value -- app/application/supply_chain_impact_api.py
for the evaluate operation, and the public
DecisionEvaluationRepositoryImpl/GovernanceEvaluationRepositoryImpl read
contracts for the read operation. No field accepts an approval,
rejection, or execution instruction (CDD-015 §25); no field accepts a
client-supplied tenant_id (CDD-015 §19, PAD-003 §8); no field is
authoritative for a governed business fact (candidate qualification,
capacity, lead time, cost, disruption severity, sourcing concentration,
recommendation, or governance outcome) -- the evaluate request identifies
only the evaluation target (CDD-015 §25; merged Governed Impact Decision
Policy Clarification and Remediation Report, Amendment R).

`structured_reasons`/`narrative`/`confidence`/`evidence` on the evaluate
response (F-I4, merged CDD-015 Deterministic Demo Data and
Read-Projection Clarification and Remediation Report, Items B-C) are
read-only projections of state the same evaluate call already persisted
-- never a second evaluation, never new business logic."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SupplyChainImpactEvaluateRequest(ClosedModel):
    """The evaluation target only. Rejects any other field -- in
    particular no tenant_id, high_severity, single_source,
    annual_revenue_exposure, qualified, capacity_sufficient,
    lead_time_days, candidate_cost, recommendation, or governance_outcome
    field exists on this model; an unrecognized field is a 422 validation
    error, never silently accepted."""

    supplier_entity_id: UUID


class ImpactedEntityResponse(BaseModel):
    entity_id: UUID
    entity_name: str


class ImpactedMaterialResponse(BaseModel):
    material_entity_id: UUID
    material_name: str


class ImpactSummaryResponse(BaseModel):
    supplier_entity_id: UUID
    supplier_name: str
    materials: list[ImpactedMaterialResponse]
    products: list[ImpactedEntityResponse]
    facilities: list[ImpactedEntityResponse]
    revenue_exposures: list[ImpactedEntityResponse]


class EvidenceItemResponse(BaseModel):
    """One governed literal assertion backing a condition or a candidate
    fact -- a read-only projection of an already-persisted `assertions`
    row (predicate/value/source/timestamp), never a new derivation
    (CDD-015 Deterministic Demo Data and Read-Projection Clarification,
    Item C)."""

    source_system_name: str
    predicate: str
    value: str
    asserted_on: str


class CandidateOutcomeResponse(BaseModel):
    alternate_supplier_entity_id: UUID | None
    outcome: str | None
    reason: str | None
    decision_record_identifier: UUID | None
    structured_reasons: list[str]
    narrative: str | None
    confidence: str | None
    evidence: list[EvidenceItemResponse]


class MaterialEvaluationResultResponse(BaseModel):
    material_entity_id: UUID
    high_severity_disruption: bool | None
    single_source_exposure: bool | None
    revenue_materiality: bool | None
    candidates: list[CandidateOutcomeResponse]


class SupplyChainImpactEvaluateResponse(BaseModel):
    """The freshly-created result of the evaluate call that produced it --
    not general retrieval access to other, previously-existing Decision
    Evaluations (PAD-003 §3a/§4a's own-result carve-out)."""

    decision_evaluation_id: UUID
    impact: ImpactSummaryResponse
    materials: list[MaterialEvaluationResultResponse]
    governance_standing: str | None
    governance_record_identifier: UUID | None
    policy_reference: str
    policy_version: str


class DecisionEvaluationRecordResponse(BaseModel):
    record_identifier: UUID
    outcome: str
    recommendation: str
    confidence: str
    structured_reasons: list[str]
    narrative: str
    knowledge_references: list[UUID]
    evidence: list[EvidenceItemResponse]
    policy_reference: str
    policy_version: str
    effective_from: str
    produced_timestamp: str


class GovernanceEvaluationRecordResponse(BaseModel):
    record_identifier: UUID
    governance_outcome: str
    human_approval_required: bool
    policy_reference: str
    policy_version: str
    effective_from: str
    produced_timestamp: str


class SupplyChainImpactReadResponse(BaseModel):
    """The persisted, decision-time result of a previously-created Gate F
    evaluation -- what CTEC decided then, not what CTEC would decide now
    (CDD-015 §20; no re-evaluation is performed to service a read)."""

    decision_evaluation_id: UUID
    created_at: str
    records: list[DecisionEvaluationRecordResponse]
    governance: GovernanceEvaluationRecordResponse | None
