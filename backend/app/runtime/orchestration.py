"""Deterministic orchestration over six injected opaque capability-step ports."""

from dataclasses import dataclass, replace
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CapabilityStepInput:
    protocol_version: str
    correlation_identifier: UUID
    request_identifier: UUID
    session_identifier: UUID
    execution_identifier: UUID
    opaque_payload: bytes


@dataclass(frozen=True, slots=True)
class CapabilityStepOutput:
    protocol_version: str
    correlation_identifier: UUID
    request_identifier: UUID
    session_identifier: UUID
    execution_identifier: UUID
    opaque_payload: bytes


class CapabilityStepError(RuntimeError):
    """Signals an opaque capability-step failure to the runtime shell."""


class CapabilityStepPort(Protocol):
    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput: ...


@dataclass(frozen=True, slots=True)
class CapabilityStepPorts:
    erm: CapabilityStepPort
    srm: CapabilityStepPort
    asm: CapabilityStepPort
    krm: CapabilityStepPort
    drm: CapabilityStepPort
    grm: CapabilityStepPort

    def ordered(self) -> tuple[CapabilityStepPort, ...]:
        return (self.erm, self.srm, self.asm, self.krm, self.drm, self.grm)


class RuntimeOrchestrator:
    def __init__(self, ports: CapabilityStepPorts) -> None:
        self._ports = ports

    def execute(self, initial_input: CapabilityStepInput) -> CapabilityStepOutput:
        current_input = initial_input
        output: CapabilityStepOutput | None = None
        for port in self._ports.ordered():
            output = port.execute(current_input)
            self._validate_metadata(current_input, output)
            current_input = replace(current_input, opaque_payload=output.opaque_payload)

        if output is None:
            raise RuntimeError("The governed runtime sequence must contain six steps")
        return output

    @staticmethod
    def _validate_metadata(
        step_input: CapabilityStepInput, step_output: CapabilityStepOutput
    ) -> None:
        expected = (
            step_input.protocol_version,
            step_input.correlation_identifier,
            step_input.request_identifier,
            step_input.session_identifier,
            step_input.execution_identifier,
        )
        actual = (
            step_output.protocol_version,
            step_output.correlation_identifier,
            step_output.request_identifier,
            step_output.session_identifier,
            step_output.execution_identifier,
        )
        if actual != expected:
            raise CapabilityStepError("Capability step changed governed runtime metadata")
