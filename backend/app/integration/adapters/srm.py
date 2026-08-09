from dataclasses import replace

from app.domain.semantic_resolution import ResolutionOutcome
from app.integration.adapters.erm import _output
from app.integration.contracts import DiagnosticCode, IntegrationEnvelope
from app.integration.dependencies import IntegrationDependencies
from app.runtime.orchestration import CapabilityStepInput, CapabilityStepOutput


class SemanticResolutionAdapter:
    def __init__(self, dependencies: IntegrationDependencies) -> None:
        self._dependencies = dependencies

    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        started = self._dependencies.clock()
        envelope = IntegrationEnvelope.from_bytes(step_input.opaque_payload)
        if envelope.enterprise_entity_id is None or envelope.references.entity_resolution is None:
            return _output(step_input, envelope.gated(DiagnosticCode.IDENTITY_NOT_RESOLVED))
        request = envelope.request
        candidates = self._dependencies.semantic_resolution.discover_candidates(
            request.semantic_terms, request.semantic_candidates
        )
        record = self._dependencies.semantic_resolution.resolve(
            enterprise_entity_id=envelope.enterprise_entity_id,
            context_id=request.context_id,
            supporting_entity_resolution_record_ids=(envelope.references.entity_resolution,),
            supporting_source_object_ids=request.source_object_ids,
            candidates=candidates,
            produced_at=self._dependencies.clock(),
        )
        self._dependencies.persistence.semantic_resolution(record)
        envelope = replace(
            envelope,
            references=replace(envelope.references, semantic_resolution=record.record_id),
            institutional_concept_id=record.semantic_interpretation_id,
            capability_timestamps=envelope.capability_timestamps
            + (("SRM", started, self._dependencies.clock()),),
        )
        if record.outcome is not ResolutionOutcome.RESOLVED:
            envelope = envelope.gated(DiagnosticCode.SEMANTICS_NOT_RESOLVED)
        return _output(step_input, envelope)
