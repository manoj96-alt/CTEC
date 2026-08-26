"""Request/response models for the Governed Evidence Fitness Exposure API
(CDD-034 §8-§9; CDD-034 Artifact Authorization v1.0 §6). A locally-defined
closed model, not imported from any other API package's schemas, to avoid
any coupling across capability firewalls (CDD-034 §14)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResolveRequest(ClosedModel):
    blueprint_name: str = Field(min_length=1)
    information_element_name: str = Field(min_length=1)


class ResolveResponse(BaseModel):
    information_element_requirement_id: UUID
    source_field_id: UUID | None
    fitness_status: Literal["FIT", "STALE", "CONFLICTING"] | None
    evaluated_at: datetime
