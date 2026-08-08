from datetime import datetime
from uuid import uuid4

from app.domain.decision_engine.model import (
    DecisionConfidence,
    DecisionConfidenceLevel,
    DecisionEvaluationModel,
    DecisionEvaluationRecord,
    DecisionExplanation,
    DecisionRecommendation,
    EvaluationOutcome,
    GoverningPolicyReference,
    PolicyVersion,
    SupportingKnowledgeReference,
)
from app.domain.shared.exceptions import ValidationException


class DecisionRecommendationService:
    def recommend(self, recommendation: str) -> DecisionRecommendation:
        return DecisionRecommendation(recommendation)


class DecisionExplanationService:
    def explain(self, reasons: tuple[str, ...], narrative: str) -> DecisionExplanation:
        return DecisionExplanation(reasons, narrative)


class DecisionConfidenceClassificationService:
    def __init__(self, *, high_threshold: float, medium_threshold: float) -> None:
        if not 0 <= medium_threshold <= high_threshold <= 1:
            raise ValueError("Decision confidence thresholds must satisfy 0 <= medium <= high <= 1")
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def classify(self, score: float) -> DecisionConfidence:
        if not 0 <= score <= 1:
            raise ValueError("Decision confidence score must be between 0 and 1")
        if score >= self.high_threshold:
            return DecisionConfidence(DecisionConfidenceLevel.HIGH)
        if score >= self.medium_threshold:
            return DecisionConfidence(DecisionConfidenceLevel.MEDIUM)
        return DecisionConfidence(DecisionConfidenceLevel.LOW)


class DecisionEvaluationService:
    def evaluate(
        self,
        *,
        knowledge_references: tuple[SupportingKnowledgeReference, ...],
        recommendation: DecisionRecommendation,
        outcome: EvaluationOutcome,
        confidence: DecisionConfidence,
        explanation: DecisionExplanation,
        policy_reference: GoverningPolicyReference,
        policy_version: PolicyVersion,
        policy_satisfied: bool,
        effective_from: datetime,
        produced_timestamp: datetime,
    ) -> DecisionEvaluationRecord:
        if outcome is EvaluationOutcome.RECOMMENDED and not policy_satisfied:
            raise ValidationException("Recommended outcome requires governing policy satisfaction")
        return DecisionEvaluationRecord(
            record_identifier=uuid4(),
            knowledge_references=knowledge_references,
            decision_recommendation=recommendation,
            evaluation_outcome=outcome,
            decision_confidence=confidence,
            decision_explanation=explanation,
            governing_policy_reference=policy_reference,
            policy_version=policy_version,
            effective_from=effective_from,
            produced_timestamp=produced_timestamp,
        )


class DecisionHistoryService:
    def order(
        self, records: tuple[DecisionEvaluationRecord, ...]
    ) -> tuple[DecisionEvaluationRecord, ...]:
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


class CurrentDecisionDeterminationService:
    def determine(
        self, records: tuple[DecisionEvaluationRecord, ...], *, as_of: datetime
    ) -> DecisionEvaluationRecord | None:
        if as_of.tzinfo is None:
            raise ValueError("Currentness timestamp must be timezone-aware")
        eligible = tuple(record for record in records if record.effective_from <= as_of)
        ordered = DecisionHistoryService().order(eligible)
        return ordered[0] if ordered else None


class PolicyTraceabilityService:
    def trace(self, record: DecisionEvaluationRecord) -> tuple[str, str]:
        return (
            record.governing_policy_reference.value,
            record.policy_version.value,
        )


class HumanOverrideService:
    def __init__(self, evaluation_service: DecisionEvaluationService) -> None:
        self.evaluation_service = evaluation_service

    def override(
        self,
        previous: DecisionEvaluationModel,
        *,
        recommendation: DecisionRecommendation,
        outcome: EvaluationOutcome,
        confidence: DecisionConfidence,
        explanation: DecisionExplanation,
        policy_reference: GoverningPolicyReference,
        policy_version: PolicyVersion,
        policy_satisfied: bool,
        effective_from: datetime,
        produced_timestamp: datetime,
    ) -> DecisionEvaluationModel:
        record = self.evaluation_service.evaluate(
            knowledge_references=previous.record.knowledge_references,
            recommendation=recommendation,
            outcome=outcome,
            confidence=confidence,
            explanation=explanation,
            policy_reference=policy_reference,
            policy_version=policy_version,
            policy_satisfied=policy_satisfied,
            effective_from=effective_from,
            produced_timestamp=produced_timestamp,
        )
        return DecisionEvaluationModel(
            record=record,
            business_context_reference=previous.business_context_reference,
            enterprise_constraint_references=previous.enterprise_constraint_references,
        )
