from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException


def _required(value: str, label: str) -> str:
    if not value.strip():
        raise ValidationException(f"{label} is required")
    return value


class EvaluationOutcome(StrEnum):
    RECOMMENDED = "Recommended"
    CANDIDATE = "Candidate"
    REJECTED = "Rejected"


class DecisionConfidenceLevel(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True, slots=True)
class DecisionRecommendation:
    value: str

    def __post_init__(self) -> None:
        _required(self.value, "Decision Recommendation")


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    structured_reasons: tuple[str, ...]
    narrative: str

    def __post_init__(self) -> None:
        if not self.structured_reasons or not all(
            value.strip() for value in self.structured_reasons
        ):
            raise ValidationException("Decision Explanation requires structured reasons")
        _required(self.narrative, "Decision Explanation narrative")


@dataclass(frozen=True, slots=True)
class SupportingKnowledgeReference:
    value: UUID


@dataclass(frozen=True, slots=True)
class GoverningPolicyReference:
    value: str

    def __post_init__(self) -> None:
        _required(self.value, "Governing Policy Reference")


@dataclass(frozen=True, slots=True)
class PolicyVersion:
    value: str

    def __post_init__(self) -> None:
        _required(self.value, "Policy Version")


@dataclass(frozen=True, slots=True)
class BusinessContextReference:
    value: UUID


@dataclass(frozen=True, slots=True)
class EnterpriseConstraintReference:
    value: str

    def __post_init__(self) -> None:
        _required(self.value, "Enterprise Constraint Reference")


@dataclass(frozen=True, slots=True)
class DecisionConfidence:
    level: DecisionConfidenceLevel


@dataclass(frozen=True, slots=True)
class DecisionEvaluationRecord:
    record_identifier: UUID
    knowledge_references: tuple[SupportingKnowledgeReference, ...]
    decision_recommendation: DecisionRecommendation
    evaluation_outcome: EvaluationOutcome
    decision_confidence: DecisionConfidence
    decision_explanation: DecisionExplanation
    governing_policy_reference: GoverningPolicyReference
    policy_version: PolicyVersion
    effective_from: datetime
    produced_timestamp: datetime

    def __post_init__(self) -> None:
        if not self.knowledge_references:
            raise ValidationException("At least one Institutional Knowledge reference is required")
        if len({item.value for item in self.knowledge_references}) != len(
            self.knowledge_references
        ):
            raise ValidationException("Knowledge References must be unique")
        if self.effective_from.tzinfo is None or self.produced_timestamp.tzinfo is None:
            raise ValidationException("Decision timestamps must be timezone-aware")

    @property
    def establishes_enterprise_decision(self) -> bool:
        return self.evaluation_outcome is EvaluationOutcome.RECOMMENDED


@dataclass(frozen=True, slots=True)
class DecisionEvaluationModel:
    record: DecisionEvaluationRecord
    business_context_reference: BusinessContextReference | None = None
    enterprise_constraint_references: tuple[EnterpriseConstraintReference, ...] = ()
