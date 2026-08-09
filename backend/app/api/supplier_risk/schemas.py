"""Versioned external contracts; trusted control metadata is intentionally absent."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.integration.contracts import RiskSeverity


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceObservationRequest(ClosedModel):
    observation_id: UUID
    source_system_reference: UUID
    source_record_reference: str = Field(min_length=1, max_length=1000)
    subject_type: str = Field(min_length=1, max_length=200)
    subject_id: UUID
    observation_type: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=1000)
    severity: RiskSeverity
    observed_at: datetime
    received_at: datetime
    evidence_reference: str = Field(min_length=1, max_length=1000)
    schema_version: Literal["1.0"] = "1.0"
    conflicting: bool = False


class SupplierEligibilityRequest(ClosedModel):
    supplier_entity_id: UUID
    qualified: bool
    approved: bool
    contractually_eligible: bool
    usable_capacity: bool
    operationally_ready: bool


class AcceptanceEvidenceRequest(ClosedModel):
    evidence_id: UUID
    authority: str = Field(min_length=1, max_length=1000)
    policy_reference: str = Field(min_length=1, max_length=1000)
    policy_version: str = Field(min_length=1, max_length=100)
    accepted_at: datetime


class SupplierRiskAssessmentRequest(ClosedModel):
    supplier_names: list[str] = Field(min_length=1, max_length=100)
    source_object_ids: list[UUID] = Field(min_length=1, max_length=100)
    enterprise_candidates: list[tuple[UUID, str]] = Field(max_length=100)
    semantic_terms: list[str] = Field(max_length=100)
    semantic_candidates: list[tuple[UUID, str]] = Field(max_length=100)
    context_id: UUID
    material_id: UUID
    facility_or_region_id: UUID
    effective_at: datetime
    observations: list[SourceObservationRequest] = Field(min_length=1, max_length=100)
    supplier_eligibility: list[SupplierEligibilityRequest] = Field(max_length=100)
    identity_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    semantic_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    assertion_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    knowledge_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    decision_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    governance_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    identity_policy_version: str = Field(min_length=1, max_length=100)
    semantic_policy_version: str = Field(min_length=1, max_length=100)
    assertion_policy_version: str = Field(min_length=1, max_length=100)
    knowledge_policy_version: str = Field(min_length=1, max_length=100)
    decision_policy_reference: str = Field(min_length=1, max_length=1000)
    decision_policy_version: str = Field(min_length=1, max_length=100)
    decision_policy_rule: str = Field(min_length=1, max_length=1000)
    governance_policy_reference: str = Field(min_length=1, max_length=1000)
    governance_policy_version: str = Field(min_length=1, max_length=100)
    acceptance_evidence: AcceptanceEvidenceRequest | None = None
    governance_conditions: list[str] = Field(default_factory=list, max_length=100)
    verified_conditions: list[str] = Field(default_factory=list, max_length=100)
    exceptional_policy_condition: bool = False

    @field_validator(
        "supplier_names", "semantic_terms", "governance_conditions", "verified_conditions"
    )
    @classmethod
    def bounded_strings(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 1000 for value in values):
            raise ValueError("values must be non-empty and at most 1000 characters")
        return values


class SupplierRiskSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_identifier: UUID
    correlation_identifier: UUID
    session_identifier: UUID
    supplier_risk: SupplierRiskAssessmentRequest


class RetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_identifier: UUID
    correlation_identifier: UUID
    reason: str = Field(min_length=3, max_length=1000)
    expected_revision: int | None = Field(default=None, ge=0)


class ReplayRequest(RetryRequest):
    replay_option_reference: UUID | None = None
    expected_revision: int | None = Field(default=None, ge=0)


class SubmissionResponse(BaseModel):
    execution_identifier: UUID
    logical_execution_identifier: UUID
    correlation_identifier: UUID
    state: str


class ExecutionResponse(BaseModel):
    execution_identifier: UUID
    logical_execution_identifier: UUID
    correlation_identifier: UUID
    state: str
    admitted_at: str | None
    completed_at: str | None
    result_code: str | None
    recommendation: str | None
    actionable: bool
    produced_record_references: list[UUID]
    terminal: bool = False
    terminal_classification: str | None = None
    safe_diagnostic_code: str | None = None
    retry_eligible: bool = False
    replay_eligible: bool = False


class AttemptResponse(BaseModel):
    execution_identifier: UUID
    logical_execution_identifier: UUID
    state: str
    admitted_at: datetime
    completed_at: datetime | None
    revision: int


class AttemptListResponse(BaseModel):
    items: list[AttemptResponse]
    next_cursor: str | None = None


class StageResponse(BaseModel):
    stage_identifier: UUID
    stage_name: Literal["ERM", "SRM", "ASM", "KRM", "DRM", "GRM"]
    stage_ordinal: int = Field(ge=0, le=5)
    status: str
    started_at: datetime
    completed_at: datetime | None
    safe_failure_code: str | None
    produced_record_references: list[UUID]


class StageListResponse(BaseModel):
    items: list[StageResponse]


class GovernedResultResponse(BaseModel):
    execution_identifier: UUID
    governance_standing: str | None
    recommendation: str | None
    actionable: bool
    completed_at: datetime
    produced_record_references: list[UUID]
    terminal_classification: str
    safe_diagnostic_code: str | None = None
    conditions: list[str] = Field(default_factory=list)
    verified_conditions: list[str] = Field(default_factory=list)
    safe_business_explanation: str | None = None
    evidence_references: list[str] = Field(default_factory=list)
    provenance_references: list[str] = Field(default_factory=list)
    policy_reference: str | None = None
    policy_version: str | None = None
    policy_rule: str | None = None
    decision_reference: UUID | None = None
    contract_version: Literal["PAS-001-v1.1"] = "PAS-001-v1.1"


class ExecutionSummaryResponse(BaseModel):
    logical_execution_identifier: UUID
    current_execution_identifier: UUID
    subject_summary: str
    submitted_at: datetime
    execution_status: str
    current_or_terminal_stage: str | None
    terminal_classification: str | None
    retry_eligible: bool
    replay_eligible: bool
    last_updated_at: datetime
    revision: int


class ExecutionListResponse(BaseModel):
    items: list[ExecutionSummaryResponse]
    next_cursor: str | None = None


class RetryEligibilityResponse(BaseModel):
    eligible: bool
    governing_attempt_identifier: UUID
    reason_code: str
    safe_constraint: str | None = None
    revision: int
    action: str | None = None


class ReplayOptionResponse(BaseModel):
    option_reference: UUID
    source_attempt_identifier: UUID
    stage_label: str
    checkpoint_at: datetime
    eligible: bool
    reason_code: str
    revision: int


class ReplayOptionsResponse(BaseModel):
    items: list[ReplayOptionResponse]


class ErrorResponse(BaseModel):
    code: str
    message: str
    correlation_id: UUID
    retryable: bool = False
