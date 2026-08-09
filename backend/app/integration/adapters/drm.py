from dataclasses import replace

from app.domain.decision_engine import (
    BusinessContextReference,
    DecisionEvaluationModel,
    DecisionExplanation,
    DecisionRecommendation,
    EvaluationOutcome,
    GoverningPolicyReference,
    PolicyVersion,
    SupportingKnowledgeReference,
)
from app.integration.adapters.erm import _output
from app.integration.contracts import (
    DiagnosticCode,
    IntegrationEnvelope,
    PolicyTraceability,
    RiskSeverity,
    SourcingRecommendation,
    SourcingStatus,
)
from app.integration.dependencies import IntegrationDependencies
from app.integration.supplier_risk_policy import SupplierRiskPolicy
from app.runtime.orchestration import CapabilityStepInput, CapabilityStepOutput


class DecisionAdapter:
    def __init__(self, dependencies: IntegrationDependencies, policy: SupplierRiskPolicy) -> None:
        self._dependencies = dependencies
        self._policy = policy

    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        started = self._dependencies.clock()
        envelope = IntegrationEnvelope.from_bytes(step_input.opaque_payload)
        knowledge_id = envelope.references.knowledge_evaluation
        if knowledge_id is None:
            return _output(
                step_input, envelope.gated(DiagnosticCode.KNOWLEDGE_NOT_INSTITUTIONALIZED)
            )
        request = envelope.request
        complete = (
            bool(request.supplier_eligibility)
            and bool(request.observations)
            and not any(item.conflicting for item in request.observations)
        )
        sourcing = self._policy.sourcing_status(
            request.supplier_eligibility, evidence_complete=complete
        )
        severity = max((item.severity for item in request.observations), default=RiskSeverity.LOW)
        recommendation = self._policy.recommend(
            severity,
            sourcing,
            request.supplier_eligibility,
            exceptional=request.exceptional_policy_condition,
        )
        if sourcing is SourcingStatus.NO_QUALIFIED_SOURCE:
            recommendation = SourcingRecommendation.NO_AUTOMATED_RECOMMENDATION
        valid = recommendation is not SourcingRecommendation.NO_AUTOMATED_RECOMMENDATION
        trace = PolicyTraceability(
            request.decision_policy_reference,
            request.decision_policy_version,
            request.decision_policy_rule,
            (f"risk_severity={severity.value}", f"sourcing_status={sourcing.value}"),
            recommendation.value,
            tuple(item.evidence_reference for item in request.observations),
        )
        record = self._dependencies.decision.evaluate(
            knowledge_references=(SupportingKnowledgeReference(knowledge_id),),
            recommendation=DecisionRecommendation(recommendation.value),
            outcome=EvaluationOutcome.RECOMMENDED if valid else EvaluationOutcome.REJECTED,
            confidence=self._dependencies.decision_confidence.classify(request.decision_score),
            explanation=DecisionExplanation(
                (
                    f"policy={trace.policy_identifier}@{trace.policy_version}",
                    f"rule={trace.evaluated_rule}",
                    *trace.relevant_inputs,
                    *(f"evidence={item}" for item in trace.supporting_evidence_references),
                ),
                "Supplier-risk recommendation evaluated against the governed bounded policy.",
            ),
            policy_reference=GoverningPolicyReference(request.decision_policy_reference),
            policy_version=PolicyVersion(request.decision_policy_version),
            policy_satisfied=valid,
            effective_from=request.effective_at,
            produced_timestamp=self._dependencies.clock(),
        )
        model = DecisionEvaluationModel(record, BusinessContextReference(request.context_id))
        self._dependencies.persistence.decision(model, policy_satisfied=valid)
        envelope = replace(
            envelope,
            references=replace(envelope.references, decision_evaluation=record.record_identifier),
            sourcing_status=sourcing,
            recommendation=recommendation,
            policy_traceability=trace,
            capability_timestamps=envelope.capability_timestamps
            + (("DRM", started, self._dependencies.clock()),),
        )
        if not valid:
            envelope = envelope.gated(DiagnosticCode.DECISION_NOT_VALID)
        return _output(step_input, envelope)
