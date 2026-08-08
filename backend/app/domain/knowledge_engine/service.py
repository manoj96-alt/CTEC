from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.knowledge_engine.model import (
    AcceptanceEvidence,
    KnowledgeConfidence,
    KnowledgeEvaluationRecord,
    KnowledgeOutcome,
)
from app.domain.shared.exceptions import ValidationException


@dataclass(frozen=True, slots=True)
class KnowledgePolicy:
    version: str
    authorized_acceptance_authorities: frozenset[str]
    high_confidence_threshold: float = 0.9
    medium_confidence_threshold: float = 0.65

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("Knowledge policy version is required")
        if any(not authority.strip() for authority in self.authorized_acceptance_authorities):
            raise ValueError("Authorized acceptance authorities cannot contain blank values")
        thresholds = (self.high_confidence_threshold, self.medium_confidence_threshold)
        if any(not 0 <= value <= 1 for value in thresholds):
            raise ValueError("Knowledge confidence thresholds must be between 0 and 1")
        if self.high_confidence_threshold < self.medium_confidence_threshold:
            raise ValueError("High confidence threshold must be at least medium threshold")


class AcceptanceEvidenceValidator:
    """Validates the AEM-001 contract without producing governance approval."""

    def __init__(self, authorized_authorities: frozenset[str]) -> None:
        self.authorized_authorities = authorized_authorities

    def validate(
        self,
        evidence: AcceptanceEvidence,
        *,
        assertion_record_id: UUID,
        policy_version: str,
    ) -> None:
        if evidence.assertion_record_id != assertion_record_id:
            raise ValidationException("Acceptance Evidence must reference the same Assertion")
        if evidence.acceptance_authority not in self.authorized_authorities:
            raise ValidationException("Acceptance Evidence authority is not authorized")
        if evidence.policy_version != policy_version:
            raise ValidationException("Acceptance Evidence policy version does not match")


class KnowledgeEngine:
    """KRM-001 v1.3 evaluation over an existing Assertion and AEM-001 v1.1 evidence."""

    def __init__(self, policy: KnowledgePolicy) -> None:
        self.policy = policy
        self._evidence_validator = AcceptanceEvidenceValidator(
            policy.authorized_acceptance_authorities
        )

    def classify_confidence(self, score: float) -> KnowledgeConfidence:
        if not 0 <= score <= 1:
            raise ValueError("Knowledge confidence score must be between 0 and 1")
        if score >= self.policy.high_confidence_threshold:
            return KnowledgeConfidence.HIGH
        if score >= self.policy.medium_confidence_threshold:
            return KnowledgeConfidence.MEDIUM
        return KnowledgeConfidence.LOW

    def evaluate(
        self,
        *,
        assertion_record_id: UUID,
        outcome: KnowledgeOutcome,
        confidence_score: float,
        structured_reasons: tuple[str, ...],
        narrative_explanation: str,
        effective_from: datetime,
        produced_at: datetime,
        acceptance_evidence: AcceptanceEvidence | None = None,
        rejection_explanation: str | None = None,
    ) -> KnowledgeEvaluationRecord:
        if outcome is KnowledgeOutcome.INSTITUTIONALIZED:
            if acceptance_evidence is None:
                raise ValidationException("Institutionalized outcome requires Acceptance Evidence")
            self._evidence_validator.validate(
                acceptance_evidence,
                assertion_record_id=assertion_record_id,
                policy_version=self.policy.version,
            )
        return KnowledgeEvaluationRecord(
            record_id=uuid4(),
            assertion_record_id=assertion_record_id,
            outcome=outcome,
            structured_reasons=structured_reasons,
            narrative_explanation=narrative_explanation,
            acceptance_evidence_id=(
                acceptance_evidence.evidence_id if acceptance_evidence is not None else None
            ),
            rejection_explanation=rejection_explanation,
            knowledge_confidence=self.classify_confidence(confidence_score),
            policy_version=self.policy.version,
            effective_from=effective_from,
            produced_at=produced_at,
        )

    def override(
        self,
        previous: KnowledgeEvaluationRecord,
        *,
        outcome: KnowledgeOutcome,
        confidence_score: float,
        structured_reasons: tuple[str, ...],
        narrative_explanation: str,
        effective_from: datetime,
        produced_at: datetime,
        acceptance_evidence: AcceptanceEvidence | None = None,
        rejection_explanation: str | None = None,
    ) -> KnowledgeEvaluationRecord:
        reasons = ("Authorized human override", *structured_reasons)
        return self.evaluate(
            assertion_record_id=previous.assertion_record_id,
            outcome=outcome,
            confidence_score=confidence_score,
            structured_reasons=reasons,
            narrative_explanation=narrative_explanation,
            effective_from=effective_from,
            produced_at=produced_at,
            acceptance_evidence=acceptance_evidence,
            rejection_explanation=rejection_explanation,
        )
