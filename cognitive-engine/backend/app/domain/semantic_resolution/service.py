import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from uuid import UUID, uuid4

from app.domain.semantic_resolution.model import (
    BusinessConfidence,
    CandidateSemanticInterpretation,
    ResolutionOutcome,
    SemanticResolutionRecord,
)


@dataclass(frozen=True, slots=True)
class SemanticResolutionPolicy:
    version: str
    resolved_threshold: float = 0.9
    possible_threshold: float = 0.65
    high_confidence_threshold: float = 0.9
    medium_confidence_threshold: float = 0.65

    def __post_init__(self) -> None:
        values = (
            self.resolved_threshold,
            self.possible_threshold,
            self.high_confidence_threshold,
            self.medium_confidence_threshold,
        )
        if any(not 0 <= value <= 1 for value in values):
            raise ValueError("Semantic thresholds must be between 0 and 1")
        if self.resolved_threshold < self.possible_threshold:
            raise ValueError("Resolved threshold must be at least possible threshold")


class SemanticResolutionEngine:
    """Deterministic SRM-001 v2.1 semantic candidate evaluation."""

    def __init__(self, policy: SemanticResolutionPolicy) -> None:
        self.policy = policy

    @staticmethod
    def normalize(value: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())

    def _confidence(self, score: float) -> BusinessConfidence:
        if score >= self.policy.high_confidence_threshold:
            return BusinessConfidence.HIGH
        if score >= self.policy.medium_confidence_threshold:
            return BusinessConfidence.MEDIUM
        return BusinessConfidence.LOW

    def discover_candidates(
        self, terms: tuple[str, ...], concepts: tuple[tuple[UUID, str], ...]
    ) -> tuple[CandidateSemanticInterpretation, ...]:
        normalized_terms = tuple(self.normalize(term) for term in terms)
        candidates = []
        for concept_id, concept_name in concepts:
            score = max(
                SequenceMatcher(None, term, self.normalize(concept_name)).ratio()
                for term in normalized_terms
            )
            if score >= self.policy.possible_threshold:
                reasons = ("Governed vocabulary name evaluation",)
                candidates.append(
                    CandidateSemanticInterpretation(
                        concept_id,
                        self._confidence(score),
                        reasons,
                        f"Candidate evaluated using policy {self.policy.version}.",
                        score,
                    )
                )
        return tuple(
            sorted(
                candidates,
                key=lambda item: (-item.internal_score, str(item.institutional_concept_id)),
            )
        )

    def resolve(
        self,
        *,
        enterprise_entity_id: UUID,
        context_id: UUID,
        supporting_entity_resolution_record_ids: tuple[UUID, ...],
        supporting_source_object_ids: tuple[UUID, ...],
        candidates: tuple[CandidateSemanticInterpretation, ...],
        produced_at: datetime,
        override_concept_id: UUID | None = None,
    ) -> SemanticResolutionRecord:
        best = candidates[0] if candidates else None
        concept_id: UUID | None
        possible: tuple[CandidateSemanticInterpretation, ...]
        reasons: tuple[str, ...]
        if override_concept_id is not None:
            outcome, concept_id, possible, score = (
                ResolutionOutcome.RESOLVED,
                override_concept_id,
                (),
                1.0,
            )
            reasons = ("Authorized human override",)
        elif best is None:
            outcome, concept_id, possible, score = ResolutionOutcome.UNRESOLVED, None, (), 0.0
            reasons = ("No governed concept satisfied the configured threshold",)
        elif best.internal_score >= self.policy.resolved_threshold:
            outcome, concept_id, possible, score = (
                ResolutionOutcome.RESOLVED,
                best.institutional_concept_id,
                (),
                best.internal_score,
            )
            reasons = best.structured_reasons
        else:
            outcome, concept_id, possible, score = (
                ResolutionOutcome.POSSIBLE,
                None,
                candidates,
                best.internal_score,
            )
            reasons = ("One or more candidate semantic interpretations require confirmation",)
        return SemanticResolutionRecord(
            uuid4(),
            enterprise_entity_id,
            context_id,
            concept_id,
            possible,
            supporting_entity_resolution_record_ids,
            supporting_source_object_ids,
            outcome,
            self._confidence(score),
            reasons,
            f"{outcome.value} using policy {self.policy.version}: {'; '.join(reasons)}.",
            self.policy.version,
            produced_at,
        )
