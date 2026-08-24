"""Request/response models for the Gate O Information-Element Context API
(CDD-029 §11-§12; Gate O Artifact Authorization v1.0 §5). A locally-defined
closed model, not imported from `app.api.ontology_copilot.schemas`, to avoid
any coupling across the Ask CTEC firewall (CDD-029 §19). No `status` field
on the response -- HTTP 200 already signals a valid governed resolution
(CDD-029 §12)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResolveRequest(ClosedModel):
    blueprint_name: str = Field(min_length=1)
    information_element_name: str = Field(min_length=1)


class ResolveResponse(BaseModel):
    blueprint_id: UUID
    blueprint_version_number: int
    information_element_requirement_id: UUID
    information_element_name: str
    obligation: str
    coverage_status: str
    evidence_availability_status: str | None
