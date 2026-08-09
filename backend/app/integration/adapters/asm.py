from dataclasses import replace

from app.domain.assertion_engine import AssertionOutcome, GovernedEvidence
from app.integration.adapters.erm import _output
from app.integration.contracts import (
    HAS_ACTIVE_RISK_CONDITION_ID,
    SUPPLIER_RISK_CONDITION_ID,
    DiagnosticCode,
    IntegrationEnvelope,
)
from app.integration.dependencies import IntegrationDependencies
from app.runtime.orchestration import CapabilityStepInput, CapabilityStepOutput


class AssertionAdapter:
    def __init__(self, dependencies: IntegrationDependencies) -> None:
        self._dependencies = dependencies

    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        started = self._dependencies.clock()
        envelope = IntegrationEnvelope.from_bytes(step_input.opaque_payload)
        observations = envelope.request.observations
        evidence_complete = bool(observations) and not any(
            item.conflicting for item in observations
        )
        if not evidence_complete:
            return _output(
                step_input,
                replace(
                    envelope.gated(DiagnosticCode.EVIDENCE_INDETERMINATE),
                    capability_timestamps=envelope.capability_timestamps
                    + (("ASM", started, self._dependencies.clock()),),
                ),
            )
        if (
            envelope.enterprise_entity_id is None
            or envelope.references.entity_resolution is None
            or envelope.references.semantic_resolution is None
        ):
            return _output(step_input, envelope.gated(DiagnosticCode.SEMANTICS_NOT_RESOLVED))
        record = self._dependencies.assertion.evaluate(
            subject_entity_id=envelope.enterprise_entity_id,
            predicate_relationship_type_id=HAS_ACTIVE_RISK_CONDITION_ID,
            object_institutional_concept_id=SUPPLIER_RISK_CONDITION_ID,
            context_id=envelope.request.context_id,
            evidence=GovernedEvidence(
                (envelope.references.entity_resolution,),
                (envelope.references.semantic_resolution,),
                envelope.enterprise_entity_id,
            ),
            internal_score=envelope.request.assertion_score,
            produced_at=self._dependencies.clock(),
        )
        self._dependencies.persistence.assertion(record)
        envelope = replace(
            envelope,
            references=replace(envelope.references, assertion=record.record_id),
            capability_timestamps=envelope.capability_timestamps
            + (("ASM", started, self._dependencies.clock()),),
        )
        if record.outcome is not AssertionOutcome.ESTABLISHED:
            envelope = envelope.gated(DiagnosticCode.ASSERTION_NOT_ESTABLISHED)
        return _output(step_input, envelope)
