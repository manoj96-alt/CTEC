from dataclasses import replace

from app.domain.governance_engine import (
    GovernanceEvaluationModel,
    GovernanceExplanation,
    GovernanceOutcome,
    GovernedRecordReference,
    GoverningPolicyReference,
    PolicyVersion,
)
from app.integration.adapters.erm import _output
from app.integration.contracts import (
    DiagnosticCode,
    GovernanceStanding,
    IntegrationEnvelope,
    SourcingRecommendation,
)
from app.integration.dependencies import IntegrationDependencies
from app.integration.supplier_risk_policy import SupplierRiskPolicy
from app.runtime.orchestration import CapabilityStepInput, CapabilityStepOutput


class GovernanceAdapter:
    def __init__(self, dependencies: IntegrationDependencies, policy: SupplierRiskPolicy) -> None:
        self._dependencies = dependencies
        self._policy = policy

    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        started = self._dependencies.clock()
        envelope = IntegrationEnvelope.from_bytes(step_input.opaque_payload)
        decision_id = envelope.references.decision_evaluation
        if decision_id is None or envelope.recommendation is None:
            return _output(step_input, envelope.gated(DiagnosticCode.DECISION_NOT_VALID))
        request = envelope.request
        requires_review = (
            envelope.recommendation is SourcingRecommendation.ESCALATE_FOR_HUMAN_REVIEW
            or request.exceptional_policy_condition
        )
        compliant = request.governance_score >= 0.65 and not requires_review
        outcome = (
            GovernanceOutcome.REQUIRES_REVIEW
            if requires_review
            else GovernanceOutcome.COMPLIANT if compliant else GovernanceOutcome.NON_COMPLIANT
        )
        record = self._dependencies.governance.evaluate(
            governed_record_reference=GovernedRecordReference(decision_id),
            governed_record_type="Decision Evaluation",
            outcome=outcome,
            confidence=self._dependencies.governance_confidence.classify(request.governance_score),
            explanation=GovernanceExplanation(
                ("Governed sourcing recommendation evaluated",),
                "Governance standing derived without executing the recommendation.",
            ),
            policy_reference=GoverningPolicyReference(request.governance_policy_reference),
            policy_version=PolicyVersion(request.governance_policy_version),
            exception_authorization_reference=None,
            policy_satisfied=compliant,
            human_review_required=requires_review,
            effective_from=request.effective_at,
            produced_timestamp=self._dependencies.clock(),
        )
        model = GovernanceEvaluationModel(record)
        self._dependencies.persistence.governance(model)
        standing, verified = self._policy.standing(
            compliant=compliant,
            requires_review=requires_review,
            conditions=request.governance_conditions,
            verified=request.verified_conditions,
        )
        envelope = replace(
            envelope,
            references=replace(envelope.references, governance_evaluation=record.record_identifier),
            governance_standing=standing,
            conditions_verified=verified,
            recommendation=(
                envelope.recommendation
                if standing
                in {GovernanceStanding.APPROVED, GovernanceStanding.CONDITIONALLY_APPROVED}
                else SourcingRecommendation.NO_AUTOMATED_RECOMMENDATION
            ),
            capability_timestamps=envelope.capability_timestamps
            + (("GRM", started, self._dependencies.clock()),),
        )
        if not standing.actionable and not (
            standing is GovernanceStanding.CONDITIONALLY_APPROVED and verified
        ):
            envelope = envelope.gated(DiagnosticCode.GOVERNANCE_NON_ACTIONABLE, standing=standing)
        return _output(step_input, envelope)
