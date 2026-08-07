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
class CandidateSemanticInterpretation:
    institutional_concept_id: UUID
    business_confidence: BusinessConfidence
    structured_reasons: tuple[str, ...]
    narrative_explanation: str
    internal_score: float

    def __post_init__(self) -> None:
        if not 0 <= self.internal_score <= 1:
            raise ValidationException("Internal candidate score must be between 0 and 1")
        if not self.structured_reasons or not self.narrative_explanation.strip():
            raise ValidationException("Candidate explanations are required")


@dataclass(frozen=True, slots=True)
class SemanticResolutionRecord:
    record_id: UUID
    enterprise_entity_id: UUID
    context_id: UUID
    semantic_interpretation_id: UUID | None
    candidate_interpretations: tuple[CandidateSemanticInterpretation, ...]
    supporting_entity_resolution_record_ids: tuple[UUID, ...]
    supporting_source_object_ids: tuple[UUID, ...]
    outcome: ResolutionOutcome
    business_confidence: BusinessConfidence
    structured_reasons: tuple[str, ...]
    narrative_explanation: str
    policy_version: str
    produced_at: datetime

    def __post_init__(self) -> None:
        if (
            not self.supporting_entity_resolution_record_ids
            or not self.supporting_source_object_ids
        ):
            raise ValidationException("At least one EERR and one Source Object are required")
        if self.outcome is ResolutionOutcome.RESOLVED:
            if self.semantic_interpretation_id is None or self.candidate_interpretations:
                raise ValidationException("Resolved records require exactly one interpretation")
        elif self.outcome is ResolutionOutcome.POSSIBLE:
            if self.semantic_interpretation_id is not None or not self.candidate_interpretations:
                raise ValidationException("Possible records require candidate interpretations")
        elif self.semantic_interpretation_id is not None or self.candidate_interpretations:
            raise ValidationException("Unresolved records cannot contain interpretations")
        if not self.structured_reasons or not self.narrative_explanation.strip():
            raise ValidationException("Semantic explanation is required")
        if not self.policy_version.strip() or self.produced_at.tzinfo is None:
            raise ValidationException("Policy version and timezone-aware timestamp are required")
