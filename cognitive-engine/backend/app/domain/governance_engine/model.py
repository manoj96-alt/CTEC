from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException


def _required(value: str, label: str) -> str:
    if not value.strip():
        raise ValidationException(f"{label} is required")
    return value


class GovernanceOutcome(StrEnum):
    COMPLIANT = "Compliant"
    NON_COMPLIANT = "Non-Compliant"
    EXCEPTION_GRANTED = "Exception Granted"
    REQUIRES_REVIEW = "Requires Review"


class GovernanceConfidenceLevel(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True, slots=True)
class GovernedRecordReference:
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
class GovernanceExplanation:
    structured_reasons: tuple[str, ...]
    narrative: str

    def __post_init__(self) -> None:
        if not self.structured_reasons or not all(
            reason.strip() for reason in self.structured_reasons
        ):
            raise ValidationException("Governance Explanation requires structured reasons")
        _required(self.narrative, "Governance Explanation narrative")


@dataclass(frozen=True, slots=True)
class GovernanceConfidence:
    level: GovernanceConfidenceLevel


@dataclass(frozen=True, slots=True)
class ExceptionAuthorizationReference:
    value: UUID


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationRecord:
    record_identifier: UUID
    governed_record_reference: GovernedRecordReference
    governed_record_type: str
    governance_outcome: GovernanceOutcome
    governance_confidence: GovernanceConfidence
    governance_explanation: GovernanceExplanation
    governing_policy_reference: GoverningPolicyReference
    policy_version: PolicyVersion
    exception_authorization_reference: ExceptionAuthorizationReference | None
    effective_from: datetime
    produced_timestamp: datetime

    def __post_init__(self) -> None:
        _required(self.governed_record_type, "Governed Record Type")
        if self.effective_from.tzinfo is None or self.produced_timestamp.tzinfo is None:
            raise ValidationException("Governance timestamps must be timezone-aware")
        has_exception = self.exception_authorization_reference is not None
        if self.governance_outcome is GovernanceOutcome.EXCEPTION_GRANTED and not has_exception:
            raise ValidationException(
                "Exception Granted requires an Exception Authorization Reference"
            )
        if self.governance_outcome is not GovernanceOutcome.EXCEPTION_GRANTED and has_exception:
            raise ValidationException(
                "Exception Authorization Reference is allowed only for Exception Granted"
            )


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationModel:
    record: GovernanceEvaluationRecord
