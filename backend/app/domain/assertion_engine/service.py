from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.assertion_engine.model import (
    AssertionOutcome,
    AssertionRecord,
    BusinessConfidence,
    GovernedEvidence,
)


@dataclass(frozen=True, slots=True)
class AssertionPolicy:
    version: str
    established_threshold: float = 0.9
    candidate_threshold: float = 0.65
    high_confidence_threshold: float = 0.9
    medium_confidence_threshold: float = 0.65

    def __post_init__(self) -> None:
        values = (
            self.established_threshold,
            self.candidate_threshold,
            self.high_confidence_threshold,
            self.medium_confidence_threshold,
        )
        if any(not 0 <= value <= 1 for value in values):
            raise ValueError("Assertion thresholds must be between 0 and 1")
        if self.established_threshold < self.candidate_threshold:
            raise ValueError("Established threshold must be at least candidate threshold")


class AssertionEngine:
    """ASM-001 v2.1 evaluation; cannot operate without governed EER and SR evidence."""

    def __init__(self, policy: AssertionPolicy) -> None:
        self.policy = policy

    def _confidence(self, score: float) -> BusinessConfidence:
        if score >= self.policy.high_confidence_threshold:
            return BusinessConfidence.HIGH
        if score >= self.policy.medium_confidence_threshold:
            return BusinessConfidence.MEDIUM
        return BusinessConfidence.LOW

    def evaluate(
        self,
        *,
        subject_entity_id: UUID,
        predicate_relationship_type_id: UUID,
        object_institutional_concept_id: UUID,
        context_id: UUID,
        evidence: GovernedEvidence,
        internal_score: float,
        produced_at: datetime,
        override_outcome: AssertionOutcome | None = None,
        override_confidence: BusinessConfidence | None = None,
    ) -> AssertionRecord:
        if not 0 <= internal_score <= 1:
            raise ValueError("Internal assertion score must be between 0 and 1")
        if override_outcome is not None or override_confidence is not None:
            outcome = override_outcome or self._outcome(internal_score)
            confidence = override_confidence or self._confidence(internal_score)
            reasons = ("Authorized human override",)
        else:
            outcome = self._outcome(internal_score)
            confidence = self._confidence(internal_score)
            reasons = ("Governed proposition evaluated against configured business policy",)
        return AssertionRecord(
            uuid4(),
            subject_entity_id,
            predicate_relationship_type_id,
            object_institutional_concept_id,
            context_id,
            outcome,
            confidence,
            evidence,
            reasons,
            f"{outcome.value} using policy {self.policy.version}: {'; '.join(reasons)}.",
            self.policy.version,
            produced_at,
        )

    def _outcome(self, score: float) -> AssertionOutcome:
        if score >= self.policy.established_threshold:
            return AssertionOutcome.ESTABLISHED
        if score >= self.policy.candidate_threshold:
            return AssertionOutcome.CANDIDATE
        return AssertionOutcome.REJECTED
