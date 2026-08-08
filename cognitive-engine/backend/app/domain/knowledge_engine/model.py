from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException


class KnowledgeOutcome(StrEnum):
    INSTITUTIONALIZED = "Institutionalized"
    CANDIDATE = "Candidate"
    REJECTED = "Rejected"


class KnowledgeConfidence(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True, slots=True)
class AcceptanceEvidence:
    evidence_id: UUID
    assertion_record_id: UUID
    acceptance_authority: str
    policy_reference: str
    policy_version: str
    acceptance_timestamp: datetime

    def __post_init__(self) -> None:
        values = (self.acceptance_authority, self.policy_reference, self.policy_version)
        if any(not value.strip() for value in values):
            raise ValidationException(
                "Acceptance authority, policy reference, and policy version are required"
            )
        if self.acceptance_timestamp.tzinfo is None:
            raise ValidationException("Acceptance timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class KnowledgeEvaluationRecord:
    record_id: UUID
    assertion_record_id: UUID
    outcome: KnowledgeOutcome
    structured_reasons: tuple[str, ...]
    narrative_explanation: str
    acceptance_evidence_id: UUID | None
    rejection_explanation: str | None
    knowledge_confidence: KnowledgeConfidence
    policy_version: str
    effective_from: datetime
    produced_at: datetime

    def __post_init__(self) -> None:
        if not self.structured_reasons or not all(x.strip() for x in self.structured_reasons):
            raise ValidationException("Structured evaluation reasons are required")
        if not self.narrative_explanation.strip():
            raise ValidationException("Narrative evaluation explanation is required")
        if not self.policy_version.strip():
            raise ValidationException("Policy version is required")
        if self.effective_from.tzinfo is None or self.produced_at.tzinfo is None:
            raise ValidationException("Knowledge timestamps must be timezone-aware")
        if (
            self.outcome is KnowledgeOutcome.INSTITUTIONALIZED
            and self.acceptance_evidence_id is None
        ):
            raise ValidationException("Institutionalized outcome requires Acceptance Evidence")
        if self.outcome is KnowledgeOutcome.REJECTED and (
            self.rejection_explanation is None or not self.rejection_explanation.strip()
        ):
            raise ValidationException("Rejected outcome requires Rejection Explanation")

    @property
    def establishes_institutional_knowledge(self) -> bool:
        return self.outcome is KnowledgeOutcome.INSTITUTIONALIZED
