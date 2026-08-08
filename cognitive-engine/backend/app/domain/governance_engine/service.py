from datetime import datetime
from uuid import uuid4

from app.domain.governance_engine.model import (
    ExceptionAuthorizationReference,
    GovernanceConfidence,
    GovernanceConfidenceLevel,
    GovernanceEvaluationModel,
    GovernanceEvaluationRecord,
    GovernanceExplanation,
    GovernanceOutcome,
    GovernedRecordReference,
    GoverningPolicyReference,
    PolicyVersion,
)
from app.domain.shared.exceptions import ValidationException


class GovernanceExplanationService:
    def explain(self, reasons: tuple[str, ...], narrative: str) -> GovernanceExplanation:
        return GovernanceExplanation(reasons, narrative)


class GovernanceConfidenceClassificationService:
    def __init__(self, *, high_threshold: float, medium_threshold: float) -> None:
        if not 0 <= medium_threshold <= high_threshold <= 1:
            raise ValueError(
                "Governance confidence thresholds must satisfy 0 <= medium <= high <= 1"
            )
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def classify(self, score: float) -> GovernanceConfidence:
        if not 0 <= score <= 1:
            raise ValueError("Governance confidence score must be between 0 and 1")
        if score >= self.high_threshold:
            return GovernanceConfidence(GovernanceConfidenceLevel.HIGH)
        if score >= self.medium_threshold:
            return GovernanceConfidence(GovernanceConfidenceLevel.MEDIUM)
        return GovernanceConfidence(GovernanceConfidenceLevel.LOW)


class GovernanceEvaluationService:
    def evaluate(
        self,
        *,
        governed_record_reference: GovernedRecordReference,
        governed_record_type: str,
        outcome: GovernanceOutcome,
        confidence: GovernanceConfidence,
        explanation: GovernanceExplanation,
        policy_reference: GoverningPolicyReference,
        policy_version: PolicyVersion,
        exception_authorization_reference: ExceptionAuthorizationReference | None,
        policy_satisfied: bool,
        human_review_required: bool,
        effective_from: datetime,
        produced_timestamp: datetime,
    ) -> GovernanceEvaluationRecord:
        if outcome is GovernanceOutcome.COMPLIANT and not policy_satisfied:
            raise ValidationException("Compliant outcome requires policy satisfaction")
        if (
            outcome in {GovernanceOutcome.NON_COMPLIANT, GovernanceOutcome.EXCEPTION_GRANTED}
            and policy_satisfied
        ):
            raise ValidationException(f"{outcome.value} outcome requires a policy violation")
        if outcome is GovernanceOutcome.REQUIRES_REVIEW and not human_review_required:
            raise ValidationException("Requires Review outcome requires human governance review")
        return GovernanceEvaluationRecord(
            record_identifier=uuid4(),
            governed_record_reference=governed_record_reference,
            governed_record_type=governed_record_type,
            governance_outcome=outcome,
            governance_confidence=confidence,
            governance_explanation=explanation,
            governing_policy_reference=policy_reference,
            policy_version=policy_version,
            exception_authorization_reference=exception_authorization_reference,
            effective_from=effective_from,
            produced_timestamp=produced_timestamp,
        )


class GovernanceHistoryService:
    def order(
        self, records: tuple[GovernanceEvaluationRecord, ...]
    ) -> tuple[GovernanceEvaluationRecord, ...]:
        return tuple(
            sorted(
                records,
                key=lambda record: (
                    record.effective_from,
                    record.produced_timestamp,
                    record.record_identifier,
                ),
                reverse=True,
            )
        )


class CurrentGovernanceDeterminationService:
    def determine(
        self, records: tuple[GovernanceEvaluationRecord, ...], *, as_of: datetime
    ) -> GovernanceEvaluationRecord | None:
        if as_of.tzinfo is None:
            raise ValueError("Currentness timestamp must be timezone-aware")
        eligible = tuple(record for record in records if record.effective_from <= as_of)
        ordered = GovernanceHistoryService().order(eligible)
        return ordered[0] if ordered else None


class GovernanceAttestationService:
    def derive(self, record: GovernanceEvaluationRecord) -> GovernanceOutcome:
        return record.governance_outcome


class PolicyTraceabilityService:
    def trace(self, record: GovernanceEvaluationRecord) -> tuple[str, str]:
        return record.governing_policy_reference.value, record.policy_version.value


class HumanOverrideService:
    def __init__(self, evaluation_service: GovernanceEvaluationService) -> None:
        self.evaluation_service = evaluation_service

    def override(
        self,
        previous: GovernanceEvaluationModel,
        *,
        outcome: GovernanceOutcome,
        confidence: GovernanceConfidence,
        explanation: GovernanceExplanation,
        policy_version: PolicyVersion,
        exception_authorization_reference: ExceptionAuthorizationReference | None,
        policy_satisfied: bool,
        human_review_required: bool,
        effective_from: datetime,
        produced_timestamp: datetime,
    ) -> GovernanceEvaluationModel:
        record = self.evaluation_service.evaluate(
            governed_record_reference=previous.record.governed_record_reference,
            governed_record_type=previous.record.governed_record_type,
            outcome=outcome,
            confidence=confidence,
            explanation=explanation,
            policy_reference=previous.record.governing_policy_reference,
            policy_version=policy_version,
            exception_authorization_reference=exception_authorization_reference,
            policy_satisfied=policy_satisfied,
            human_review_required=human_review_required,
            effective_from=effective_from,
            produced_timestamp=produced_timestamp,
        )
        return GovernanceEvaluationModel(record)
