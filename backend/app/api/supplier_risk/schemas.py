"""Versioned external contracts; trusted control metadata is intentionally absent."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupplierRiskSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_identifier: UUID
    correlation_identifier: UUID
    session_identifier: UUID
    supplier_risk: dict[str, Any]


class RetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_identifier: UUID
    correlation_identifier: UUID
    reason: str = Field(min_length=3, max_length=1000)


class ReplayRequest(RetryRequest):
    pass


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


class ErrorResponse(BaseModel):
    code: str
    message: str
    correlation_id: UUID
    retryable: bool = False
