"""Request/response models for the Gate V Governed Agent Resolution API
(CDD-037 §18-§19). The request payload carries no `tenant_id` and no
`requested_by` -- both are derived exclusively from the authenticated
`TrustedPrincipal` (CDD-037 §11)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResolveObservationBody(BaseModel):
    observation_text: str = Field(min_length=1, max_length=500)
    priority_score: int = Field(ge=0, le=100)


class ResolutionResponse(BaseModel):
    resolution_id: UUID
    agent_id: str
    outcome: str
    approval_id: UUID | None
    resolved_on: datetime


class ResolutionDetailResponse(ResolutionResponse):
    tenant_id: str
    requested_by: str
    observation_text: str
    priority_score: int
