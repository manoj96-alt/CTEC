import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from uuid import UUID, uuid4

from app.domain.identity_resolution.evidence import (
    ResolutionDecision,
    SourceRepresentation,
    build_evidence_profile,
    decide,
)
from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EnterpriseEntityResolutionRecord,
    EvidenceProfile,
    ResolutionCandidate,
    ResolutionOutcome,
    StewardDecisionAction,
)
from app.domain.identity_resolution.policy import ResolutionPolicyDefinition
from app.domain.shared.exceptions import ValidationException


class OverrideNotPermittedError(ValidationException):
    """Raised when a human override would contradict a non-configurable Gate
    B safety invariant (currently: an unresolved veto conflict). A steward
    can select a candidate only where domain rules permit it; this error is
    the enforcement point that makes BLOCKED_CONFLICT -> RESOLVED
    structurally impossible, regardless of caller intent."""


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


class EvidenceResolutionEngine:
    """Multi-attribute, policy-governed resolution. Additive to
    EntityResolutionEngine (the automated name-only runtime path above,
    unchanged): this engine is the one the future Steward API will call. It
    shares the same domain vocabulary (ResolutionOutcome,
    BusinessConfidence, EnterpriseEntityResolutionRecord, EvidenceProfile)
    rather than inventing a parallel one.
    """

    def __init__(self, policy: ResolutionPolicyDefinition, *, policy_id: UUID) -> None:
        self.policy = policy
        self.policy_id = policy_id

    def evaluate(
        self,
        *,
        representations: tuple[SourceRepresentation, ...],
        candidate_name: str,
        candidate_country: str | None = None,
        candidate_parent_entity_name: str | None = None,
    ) -> ResolutionDecision:
        profile = build_evidence_profile(
            representations=representations,
            candidate_name=candidate_name,
            candidate_country=candidate_country,
            candidate_parent_entity_name=candidate_parent_entity_name,
            policy=self.policy,
        )
        return decide(profile, self.policy)

    def resolve(
        self,
        *,
        tenant_id: str,
        supporting_source_object_ids: tuple[UUID, ...],
        representations: tuple[SourceRepresentation, ...],
        candidate_name: str,
        candidate_enterprise_entity_id: UUID | None,
        produced_at: datetime,
        candidate_country: str | None = None,
        candidate_parent_entity_name: str | None = None,
        override_entity_id: UUID | None = None,
        override_actor_id: str | None = None,
        override_rationale: str | None = None,
    ) -> EnterpriseEntityResolutionRecord:
        if override_entity_id is not None:
            profile = build_evidence_profile(
                representations=representations,
                candidate_name=candidate_name,
                candidate_country=candidate_country,
                candidate_parent_entity_name=candidate_parent_entity_name,
                policy=self.policy,
            )
            # Non-configurable safety invariant: a human override can never
            # turn a veto conflict (BLOCKED_CONFLICT) into RESOLVED. Evaluate
            # the same evidence the automatic engine would see before
            # honoring the override.
            natural_decision = decide(profile, self.policy)
            if natural_decision.outcome is ResolutionOutcome.BLOCKED_CONFLICT:
                raise OverrideNotPermittedError(
                    "Cannot override to Resolved: evidence contains an unresolved veto "
                    f"conflict ({'; '.join(natural_decision.triggered_veto_rules)})"
                )
            return EnterpriseEntityResolutionRecord(
                record_id=uuid4(),
                tenant_id=tenant_id,
                enterprise_entity_id=override_entity_id,
                supporting_source_object_ids=supporting_source_object_ids,
                outcome=ResolutionOutcome.RESOLVED,
                business_confidence=BusinessConfidence.HIGH,
                structured_reasons=("Authorized human override",),
                narrative_explanation=(
                    f"Resolved using policy {self.policy.policy_version}: authorized human override."
                ),
                produced_at=produced_at,
                policy_version=self.policy.policy_version,
                evidence_profile=profile,
                policy_id=self.policy_id,
                actor_id=override_actor_id,
                decision_rationale=override_rationale,
            )

        decision = self.evaluate(
            representations=representations,
            candidate_name=candidate_name,
            candidate_country=candidate_country,
            candidate_parent_entity_name=candidate_parent_entity_name,
        )
        entity_free_outcomes = (ResolutionOutcome.UNRESOLVED, ResolutionOutcome.BLOCKED_CONFLICT)
        if decision.outcome not in entity_free_outcomes and candidate_enterprise_entity_id is None:
            raise ValidationException(
                f"outcome {decision.outcome.value} requires a candidate enterprise entity reference"
            )
        entity_id = (
            None if decision.outcome in entity_free_outcomes else candidate_enterprise_entity_id
        )
        narrative = (
            f"{decision.outcome.value} using policy {self.policy.policy_version} "
            f"(score={decision.score:.2f}): {'; '.join(decision.structured_reasons)}."
        )
        return EnterpriseEntityResolutionRecord(
            record_id=uuid4(),
            tenant_id=tenant_id,
            enterprise_entity_id=entity_id,
            supporting_source_object_ids=supporting_source_object_ids,
            outcome=decision.outcome,
            business_confidence=decision.business_confidence,
            structured_reasons=decision.structured_reasons,
            narrative_explanation=narrative,
            produced_at=produced_at,
            policy_version=self.policy.policy_version,
            evidence_profile=decision.evidence_profile,
            policy_id=self.policy_id,
        )

    def decide_steward_action(
        self,
        *,
        tenant_id: str,
        supporting_source_object_ids: tuple[UUID, ...],
        evidence_profile: EvidenceProfile,
        current_enterprise_entity_id: UUID | None,
        action: StewardDecisionAction,
        actor_id: str,
        decision_rationale: str,
        produced_at: datetime,
    ) -> EnterpriseEntityResolutionRecord:
        """Apply one fixed steward decision to an already-persisted,
        already-computed EvidenceProfile (never raw source representations
        -- those are never persisted; see evidence.py's module docstring).
        decide() is a pure function of (evidence_profile, policy), so the
        veto/score facts it returns here are identical to what the
        automatic engine already established. This is the single place
        confirm/reject/unresolved/block-conflict outcome semantics are
        decided; the API layer must never construct an
        EnterpriseEntityResolutionRecord's outcome itself.
        """
        if not actor_id.strip():
            raise ValidationException("A steward decision requires a non-blank actor id")
        if not decision_rationale.strip():
            raise ValidationException("A steward decision requires a non-blank rationale")

        decision = decide(evidence_profile, self.policy)

        if action is StewardDecisionAction.CONFIRM_MATCH:
            if decision.outcome is ResolutionOutcome.BLOCKED_CONFLICT:
                raise OverrideNotPermittedError(
                    "Cannot confirm a match while evidence contains an unresolved veto "
                    f"conflict ({'; '.join(decision.triggered_veto_rules)})"
                )
            if current_enterprise_entity_id is None:
                raise ValidationException(
                    "confirm_match requires a candidate enterprise entity reference"
                )
            entity_id: UUID | None = current_enterprise_entity_id
            outcome = ResolutionOutcome.RESOLVED
            confidence = BusinessConfidence.HIGH
            reasons: tuple[str, ...] = (
                "Authorized human override: steward confirmed the proposed candidate.",
            )
        elif action is StewardDecisionAction.REJECT_MATCH:
            entity_id = None
            if decision.outcome is ResolutionOutcome.BLOCKED_CONFLICT:
                # A hard veto conflict cannot be rejected away; the evidence
                # itself still blocks automatic or steward resolution.
                outcome = ResolutionOutcome.BLOCKED_CONFLICT
            else:
                outcome = (
                    ResolutionOutcome.POSSIBLE
                    if decision.score >= self.policy.possible_threshold
                    else ResolutionOutcome.UNRESOLVED
                )
            confidence = decision.business_confidence
            reasons = ("Steward rejected the proposed candidate.", *decision.structured_reasons)
        elif action is StewardDecisionAction.MARK_UNRESOLVED:
            entity_id = None
            outcome = ResolutionOutcome.UNRESOLVED
            confidence = BusinessConfidence.LOW
            reasons = ("Steward marked this case unresolved.",)
        elif action is StewardDecisionAction.BLOCK_CONFLICT:
            if decision.outcome is not ResolutionOutcome.BLOCKED_CONFLICT:
                raise ValidationException(
                    "block_conflict requires persisted evidence containing an applicable "
                    "veto/conflict"
                )
            entity_id = None
            outcome = ResolutionOutcome.BLOCKED_CONFLICT
            confidence = BusinessConfidence.LOW
            reasons = decision.triggered_veto_rules or ("Steward blocked this case.",)
        else:
            raise ValidationException(f"Unknown steward decision action: {action}")

        narrative = (
            f"{outcome.value} using policy {self.policy.policy_version} (steward action: "
            f"{action.value}): {'; '.join(reasons)}."
        )
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
            policy_version=self.policy.policy_version,
            evidence_profile=evidence_profile,
            policy_id=self.policy_id,
            actor_id=actor_id,
            decision_rationale=decision_rationale,
        )
