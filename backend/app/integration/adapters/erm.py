from dataclasses import replace

from app.domain.identity_resolution import ResolutionOutcome
from app.integration.contracts import DiagnosticCode, IntegrationEnvelope
from app.integration.dependencies import IntegrationDependencies
from app.runtime.orchestration import CapabilityStepError, CapabilityStepInput, CapabilityStepOutput


class EntityResolutionAdapter:
    def __init__(self, dependencies: IntegrationDependencies) -> None:
        self._dependencies = dependencies

    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        started = self._dependencies.clock()
        # Fail closed: an entity-resolution record can never be persisted
        # without a trusted tenant. The runtime already rejects admission
        # when AuthorityContext is missing (see engine.py's control-metadata
        # check), but this adapter does not rely on that alone.
        organization_id = (
            step_input.authority_context.organization_id
            if step_input.authority_context is not None
            else None
        )
        if not organization_id:
            raise CapabilityStepError(
                "Entity resolution requires a trusted AuthorityContext with organization_id"
            )
        envelope = IntegrationEnvelope.from_bytes(step_input.opaque_payload)
        request = envelope.request
        candidates = self._dependencies.entity_resolution.discover_candidates(
            request.supplier_names, request.enterprise_candidates
        )
        record = self._dependencies.entity_resolution.resolve(
            tenant_id=organization_id,
            supporting_source_object_ids=request.source_object_ids,
            candidates=candidates,
            produced_at=self._dependencies.clock(),
        )
        self._dependencies.persistence.entity_resolution(record)
        references = replace(envelope.references, entity_resolution=record.record_id)
        envelope = replace(
            envelope,
            references=references,
            enterprise_entity_id=record.enterprise_entity_id,
            capability_timestamps=envelope.capability_timestamps
            + (("ERM", started, self._dependencies.clock()),),
        )
        if record.outcome is not ResolutionOutcome.RESOLVED:
            envelope = envelope.gated(DiagnosticCode.IDENTITY_NOT_RESOLVED)
        return _output(step_input, envelope)


def _output(step_input: CapabilityStepInput, envelope: IntegrationEnvelope) -> CapabilityStepOutput:
    references = tuple(
        value
        for value in (
            envelope.references.entity_resolution,
            envelope.references.semantic_resolution,
            envelope.references.assertion,
            envelope.references.knowledge_evaluation,
            envelope.references.decision_evaluation,
            envelope.references.governance_evaluation,
        )
        if value is not None
    )
    return CapabilityStepOutput(
        step_input.protocol_version,
        step_input.correlation_identifier,
        step_input.request_identifier,
        step_input.session_identifier,
        step_input.execution_identifier,
        envelope.to_bytes(),
        business_gated=envelope.gate_outcome.value == "BUSINESS_GATED",
        produced_record_references=references,
        result_code=envelope.diagnostic_code.value if envelope.diagnostic_code else None,
        result_value=(
            envelope.governance_standing.value
            if envelope.governance_standing
            else envelope.recommendation.value if envelope.recommendation else None
        ),
        actionable=(
            envelope.governance_standing is not None
            and (
                envelope.governance_standing.actionable
                or (
                    envelope.governance_standing.value == "CONDITIONALLY_APPROVED"
                    and envelope.conditions_verified
                )
            )
        ),
    )
