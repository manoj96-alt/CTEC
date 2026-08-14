import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from uuid import UUID, uuid4

from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EnterpriseEntityResolutionRecord,
    ResolutionCandidate,
    ResolutionOutcome,
)


@dataclass(frozen=True, slots=True)
class ResolutionPolicy:
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
            raise ValueError("Resolution thresholds must be between 0 and 1")
        if self.resolved_threshold < self.possible_threshold:
            raise ValueError("Resolved threshold must be at least the possible threshold")
        if self.high_confidence_threshold < self.medium_confidence_threshold:
            raise ValueError("High confidence threshold must be at least the medium threshold")


class EntityResolutionEngine:
    """Deterministic implementation of ERM-001 candidate discovery and evaluation."""

    def __init__(self, policy: ResolutionPolicy) -> None:
        self.policy = policy

    @staticmethod
    def normalize(value: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())

    def discover_candidates(
        self, source_names: tuple[str, ...], enterprise_entities: tuple[tuple[UUID, str], ...]
    ) -> tuple[ResolutionCandidate, ...]:
        normalized_sources = tuple(self.normalize(value) for value in source_names)
        candidates: list[ResolutionCandidate] = []
        for entity_id, entity_name in enterprise_entities:
            normalized_entity = self.normalize(entity_name)
            score = max(
                SequenceMatcher(None, source_name, normalized_entity).ratio()
                for source_name in normalized_sources
            )
            reason = (
                "Normalized name exact match"
                if score == 1
                else "Normalized name similarity evaluation"
            )
            if score >= self.policy.possible_threshold:
                candidates.append(ResolutionCandidate(entity_id, score, (reason,)))
        return tuple(
            sorted(
                candidates, key=lambda item: (-item.internal_score, str(item.enterprise_entity_id))
            )
        )

    def resolve(
        self,
        *,
        tenant_id: str,
        supporting_source_object_ids: tuple[UUID, ...],
        candidates: tuple[ResolutionCandidate, ...],
        produced_at: datetime,
        override_entity_id: UUID | None = None,
    ) -> EnterpriseEntityResolutionRecord:
        best = candidates[0] if candidates else None
        if override_entity_id is not None:
            entity_id = override_entity_id
            outcome = ResolutionOutcome.RESOLVED
            score = 1.0
            reasons: tuple[str, ...] = ("Authorized human override",)
        elif best is None:
            entity_id = None
            outcome = ResolutionOutcome.UNRESOLVED
            score = 0.0
            reasons = ("No candidate satisfied the configured discovery threshold",)
        else:
            entity_id = best.enterprise_entity_id
            score = best.internal_score
            reasons = best.reasons
            outcome = (
                ResolutionOutcome.RESOLVED
                if score >= self.policy.resolved_threshold
                else ResolutionOutcome.POSSIBLE
            )
        confidence = (
            BusinessConfidence.HIGH
            if score >= self.policy.high_confidence_threshold
            else (
                BusinessConfidence.MEDIUM
                if score >= self.policy.medium_confidence_threshold
                else BusinessConfidence.LOW
            )
        )
        narrative = f"{outcome.value} using policy {self.policy.version}: {'; '.join(reasons)}."
        return EnterpriseEntityResolutionRecord(
            record_id=uuid4(),
            tenant_id=tenant_id,
            enterprise_entity_id=entity_id,
            supporting_source_object_ids=supporting_source_object_ids,
            outcome=outcome,
            business_confidence=confidence,
            structured_reasons=reasons,
            narrative_explanation=narrative,
            produced_at=produced_at,
            policy_version=self.policy.version,
        )
