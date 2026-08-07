from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException


class AssertionOutcome(StrEnum):
    ESTABLISHED = "Established"
    CANDIDATE = "Candidate"
    REJECTED = "Rejected"


class BusinessConfidence(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True, slots=True)
class GovernedEvidence:
    enterprise_entity_resolution_record_ids: tuple[UUID, ...]
    semantic_resolution_record_ids: tuple[UUID, ...]
    enterprise_entity_id: UUID

    def __post_init__(self) -> None:
        if not self.enterprise_entity_resolution_record_ids:
            raise ValidationException(
                "At least one Enterprise Entity Resolution Record is required"
            )
        if not self.semantic_resolution_record_ids:
            raise ValidationException("At least one Semantic Resolution Record is required")


@dataclass(frozen=True, slots=True)
class AssertionRecord:
    record_id: UUID
    subject_entity_id: UUID
    predicate_relationship_type_id: UUID
    object_institutional_concept_id: UUID
    context_id: UUID
    outcome: AssertionOutcome
    business_confidence: BusinessConfidence
    evidence: GovernedEvidence
    structured_reasons: tuple[str, ...]
    narrative_explanation: str
    policy_version: str
    produced_at: datetime

    def __post_init__(self) -> None:
        if self.evidence.enterprise_entity_id != self.subject_entity_id:
            raise ValidationException("All governed evidence must reference the Assertion Subject")
        if not self.structured_reasons or not self.narrative_explanation.strip():
            raise ValidationException("Assertion explanation is required")
        if not self.policy_version.strip() or self.produced_at.tzinfo is None:
            raise ValidationException("Policy version and timezone-aware timestamp are required")
