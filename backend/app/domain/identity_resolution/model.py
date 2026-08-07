from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException


class ResolutionOutcome(StrEnum):
    RESOLVED = "Resolved"
    POSSIBLE = "Possible Resolution"
    UNRESOLVED = "Unresolved"


class BusinessConfidence(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True, slots=True)
class ResolutionCandidate:
    enterprise_entity_id: UUID
    internal_score: float
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.internal_score <= 1:
            raise ValidationException("Internal candidate score must be between 0 and 1")
        if not self.reasons:
            raise ValidationException("Candidate evaluation requires at least one reason")


@dataclass(frozen=True, slots=True)
class EnterpriseEntityResolutionRecord:
    record_id: UUID
    enterprise_entity_id: UUID | None
    supporting_source_object_ids: tuple[UUID, ...]
    outcome: ResolutionOutcome
    business_confidence: BusinessConfidence
    structured_reasons: tuple[str, ...]
    narrative_explanation: str
    produced_at: datetime
    policy_version: str

    def __post_init__(self) -> None:
        if not self.supporting_source_object_ids:
            raise ValidationException("At least one supporting Source Object is required")
        if len(set(self.supporting_source_object_ids)) != len(self.supporting_source_object_ids):
            raise ValidationException("Supporting Source Objects must be unique")
        if self.outcome is ResolutionOutcome.UNRESOLVED and self.enterprise_entity_id is not None:
            raise ValidationException("Unresolved records cannot reference an Enterprise Entity")
        if self.outcome is not ResolutionOutcome.UNRESOLVED and self.enterprise_entity_id is None:
            raise ValidationException("Resolved outcomes require an Enterprise Entity reference")
        if not self.structured_reasons or not self.narrative_explanation.strip():
            raise ValidationException("Structured reasons and narrative explanation are required")
        if self.produced_at.tzinfo is None:
            raise ValidationException("Produced timestamp must include a timezone")
        if not self.policy_version.strip():
            raise ValidationException("Resolution Policy Version is required")
