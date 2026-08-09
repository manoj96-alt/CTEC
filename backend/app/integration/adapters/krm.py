from dataclasses import replace

from app.domain.knowledge_engine import AcceptanceEvidence, KnowledgeOutcome
from app.integration.adapters.erm import _output
from app.integration.contracts import DiagnosticCode, IntegrationEnvelope
from app.integration.dependencies import IntegrationDependencies
from app.runtime.orchestration import CapabilityStepInput, CapabilityStepOutput


class KnowledgeAdapter:
    def __init__(self, dependencies: IntegrationDependencies) -> None:
        self._dependencies = dependencies

    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        started = self._dependencies.clock()
        envelope = IntegrationEnvelope.from_bytes(step_input.opaque_payload)
        assertion_id = envelope.references.assertion
        supplied = envelope.request.acceptance_evidence
        if assertion_id is None or supplied is None:
            return _output(
                step_input, envelope.gated(DiagnosticCode.KNOWLEDGE_NOT_INSTITUTIONALIZED)
            )
        evidence = AcceptanceEvidence(
            supplied.evidence_id,
            assertion_id,
            supplied.authority,
            supplied.policy_reference,
            supplied.policy_version,
            supplied.accepted_at,
        )
        record = self._dependencies.knowledge.evaluate(
            assertion_record_id=assertion_id,
            outcome=KnowledgeOutcome.INSTITUTIONALIZED,
            confidence_score=envelope.request.knowledge_score,
            structured_reasons=("Governed acceptance evidence validated",),
            narrative_explanation="Institutional acceptance demonstrated for supplier risk.",
            effective_from=envelope.request.effective_at,
            produced_at=self._dependencies.clock(),
            acceptance_evidence=evidence,
        )
        self._dependencies.persistence.knowledge(record)
        envelope = replace(
            envelope,
            references=replace(envelope.references, knowledge_evaluation=record.record_id),
            capability_timestamps=envelope.capability_timestamps
            + (("KRM", started, self._dependencies.clock()),),
        )
        if record.outcome is not KnowledgeOutcome.INSTITUTIONALIZED:
            envelope = envelope.gated(DiagnosticCode.KNOWLEDGE_NOT_INSTITUTIONALIZED)
        return _output(step_input, envelope)
