"""Request/response models for the Gate S Governed Human Approval API
(CDD-036 §27). Every response field comes from an already-persisted
`GateSApprovalRequest`."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RequestApprovalBody(BaseModel):
    note_text: str = Field(min_length=1, max_length=500)


class RejectBody(BaseModel):
    rejection_reason: str | None = Field(default=None, max_length=1000)


class ExecuteBody(BaseModel):
    note_text: str = Field(min_length=1, max_length=500)


class ApprovalResponse(BaseModel):
    approval_id: UUID
    tenant_id: str
    action_id: str
    note_text: str
    status: str
    requested_by: str
    requested_on: datetime
    decided_by: str | None
    decided_on: datetime | None
    rejection_reason: str | None
    consumed_on: datetime | None
    consumed_execution_id: UUID | None


class ExecuteResponse(BaseModel):
    governed_note_id: UUID
