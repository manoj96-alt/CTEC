"""Gate F DRM (CDD-015 §11, remediated per the merged Gate F Governed Impact
Decision Policy Clarification and Remediation Report, PR #69): the governed
four-condition binary policy.

    Condition 1: high-severity disruption
    Condition 2: single-source exposure
    Condition 3: annual revenue exposure > $10,000,000
    Condition 4: qualified alternate with sufficient capacity

All four positively True -> RECOMMENDED. Any one positively False ->
REJECTED (AND-logic short-circuit, independent of the others' status).
Otherwise (no condition positively False, at least one Unknown) -> no
`decision_evaluation_records` row is produced for that unit (CDD-015 §16
item 6's existing absence precedent, extended to "cannot be autonomously
decided" -- never a fabricated REJECTED).

DRM does not approve the action (§12: that boundary belongs to GRM,
`gate_f/grm.py`). Persists via the new public
`DecisionEvaluationRepositoryImpl.append_group_member` contract -- never
`_to_orm` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.decision_engine import (
    DecisionConfidence,
    DecisionConfidenceLevel,
    DecisionEvaluationGroupReference,
    DecisionEvaluationModel,
    DecisionExplanation,
    DecisionRecommendation,
    EvaluationOutcome,
    GoverningPolicyReference,
    PolicyVersion,
    SupportingKnowledgeReference,
)
from app.domain.decision_engine.configuration import GateFPolicyConfiguration
from app.domain.decision_engine.service import DecisionEvaluationService
from app.infrastructure.persistence.decision_repository import (
    DecisionEvaluationRepositoryImpl,
    DecisionPersistenceModel,
)
from app.integration.adapters.gate_f.krm import CandidateEvidence, GovernedFact


class GateFOutcomeReason(StrEnum):
    """Gate F's own recommendation vocabulary (binary only -- CDD-015 does
    not authorize a three-tier policy; see the merged clarification's
    Amendment K)."""

    RECOMMENDED = "Recommended: all four governed conditions are satisfied"
    REJECTED_NOT_HIGH_SEVERITY = "Rejected: disruption is not high-severity"
    REJECTED_NOT_SINGLE_SOURCED = "Rejected: material is not single-sourced"
    REJECTED_NOT_MATERIAL = "Rejected: revenue exposure does not exceed the materiality threshold"
    REJECTED_NOT_QUALIFIED = "Rejected: candidate is not qualified"
    REJECTED_INSUFFICIENT_CAPACITY = "Rejected: candidate capacity is insufficient"
    REJECTED_NO_VIABLE_ALTERNATE = "Rejected: no viable alternate was found"


@dataclass(frozen=True, slots=True)
class DrmUnit:
    """One (Material, Alternate Supplier) governed decision unit, evaluated
    against the four-condition policy."""

    material_entity_id: UUID
    alternate_supplier_entity_id: UUID | None
    high_severity_disruption: GovernedFact
    single_source_exposure: GovernedFact
    revenue_materiality: GovernedFact
    candidate: CandidateEvidence | None


@dataclass(frozen=True, slots=True)
class GateFDecisionResult:
    record_identifier: UUID
    material_entity_id: UUID
    alternate_supplier_entity_id: UUID | None
    outcome: EvaluationOutcome
    reason: GateFOutcomeReason


class GateFDecisionAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def evaluate(
        self,
        *,
        decision_evaluation_id: UUID,
        unit: DrmUnit,
        policy: GateFPolicyConfiguration,
        now: datetime,
    ) -> GateFDecisionResult | None:
        """Returns `None` (no record) when the policy cannot be
        autonomously decided (an Unknown condition, with none positively
        False) -- never fabricates RECOMMENDED or REJECTED."""
        outcome, reason = self._classify(unit)
        if outcome is None or reason is None:
            return None

        knowledge_references = self._knowledge_references(unit)
        policy_satisfied = outcome is EvaluationOutcome.RECOMMENDED

        record = DecisionEvaluationService().evaluate(
            knowledge_references=knowledge_references,
            recommendation=DecisionRecommendation(reason.value),
            outcome=outcome,
            confidence=DecisionConfidence(DecisionConfidenceLevel.HIGH),
            explanation=DecisionExplanation(
                (reason.value,), "Gate F governed four-condition mitigation policy (CDD-015 §11)."
            ),
            policy_reference=GoverningPolicyReference(policy.policy_reference),
            policy_version=PolicyVersion(policy.policy_version),
            policy_satisfied=policy_satisfied,
            effective_from=now,
            produced_timestamp=now,
        )
        model = DecisionEvaluationModel(
            record=record,
            decision_evaluation_id=DecisionEvaluationGroupReference(decision_evaluation_id),
        )
        DecisionEvaluationRepositoryImpl(self._session).append_group_member(
            DecisionPersistenceModel(model, policy_satisfied)
        )

        return GateFDecisionResult(
            record_identifier=record.record_identifier,
            material_entity_id=unit.material_entity_id,
            alternate_supplier_entity_id=unit.alternate_supplier_entity_id,
            outcome=outcome,
            reason=reason,
        )

    @staticmethod
    def _classify(
        unit: DrmUnit,
    ) -> tuple[EvaluationOutcome, GateFOutcomeReason] | tuple[None, None]:
        qualified = unit.candidate.qualified if unit.candidate is not None else GovernedFact(None)
        capacity = (
            unit.candidate.capacity_sufficient if unit.candidate is not None else GovernedFact(None)
        )
        no_viable_alternate = unit.candidate is None

        # Any positively-False condition is sufficient for REJECTED,
        # regardless of the other conditions' status (AND-logic
        # short-circuit; merged clarification Amendment L).
        if unit.high_severity_disruption.value is False:
            return EvaluationOutcome.REJECTED, GateFOutcomeReason.REJECTED_NOT_HIGH_SEVERITY
        if unit.single_source_exposure.value is False:
            return EvaluationOutcome.REJECTED, GateFOutcomeReason.REJECTED_NOT_SINGLE_SOURCED
        if unit.revenue_materiality.value is False:
            return EvaluationOutcome.REJECTED, GateFOutcomeReason.REJECTED_NOT_MATERIAL
        if no_viable_alternate:
            # Successful discovery returning zero candidates is a known
            # False for condition 4 (merged clarification Amendment M),
            # not Unknown.
            return EvaluationOutcome.REJECTED, GateFOutcomeReason.REJECTED_NO_VIABLE_ALTERNATE
        if qualified.value is False:
            return EvaluationOutcome.REJECTED, GateFOutcomeReason.REJECTED_NOT_QUALIFIED
        if capacity.value is False:
            return EvaluationOutcome.REJECTED, GateFOutcomeReason.REJECTED_INSUFFICIENT_CAPACITY

        # All four positively True.
        if (
            unit.high_severity_disruption.value is True
            and unit.single_source_exposure.value is True
            and unit.revenue_materiality.value is True
            and qualified.value is True
            and capacity.value is True
        ):
            return EvaluationOutcome.RECOMMENDED, GateFOutcomeReason.RECOMMENDED

        # No condition is positively False, but at least one is Unknown:
        # cannot be autonomously decided.
        return None, None

    @staticmethod
    def _knowledge_references(unit: DrmUnit) -> tuple[SupportingKnowledgeReference, ...]:
        assertion_ids: list[UUID] = []
        for fact in (
            unit.high_severity_disruption,
            unit.single_source_exposure,
            unit.revenue_materiality,
        ):
            if fact.assertion_id is not None:
                assertion_ids.append(fact.assertion_id)
        if unit.candidate is not None:
            assertion_ids.extend(unit.candidate.assertion_ids)
            assertion_ids.append(unit.candidate.institutional_relationship_id)
        if not assertion_ids:
            assertion_ids.append(unit.material_entity_id)
        return tuple(SupportingKnowledgeReference(value) for value in assertion_ids)
