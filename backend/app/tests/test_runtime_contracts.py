from dataclasses import fields
from typing import cast
from uuid import uuid4

from app.runtime.contracts import (
    CognitiveEngineInvocationPort,
    ExecutionObservationPort,
    InvocationRequest,
    InvocationStatus,
)
from app.runtime.engine import CognitiveEngineRuntime
from app.runtime.orchestration import (
    CapabilityStepInput,
    CapabilityStepOutput,
    CapabilityStepPorts,
)


class PassthroughStep:
    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        return CapabilityStepOutput(
            step_input.protocol_version,
            step_input.correlation_identifier,
            step_input.request_identifier,
            step_input.session_identifier,
            step_input.execution_identifier,
            step_input.opaque_payload,
        )


def make_runtime() -> CognitiveEngineRuntime:
    step = PassthroughStep()
    return CognitiveEngineRuntime(CapabilityStepPorts(step, step, step, step, step, step))


def test_invocation_request_contains_only_governed_fields() -> None:
    assert {field.name for field in fields(InvocationRequest)} == {
        "protocol_version",
        "correlation_identifier",
        "request_identifier",
        "session_identifier",
        "request_classification",
        "opaque_payload",
    }


def test_runtime_satisfies_only_the_two_authorized_external_ports() -> None:
    runtime = make_runtime()
    invocation_port = cast(CognitiveEngineInvocationPort, runtime)
    observation_port = cast(ExecutionObservationPort, runtime)
    request = InvocationRequest("1.0", uuid4(), uuid4(), uuid4(), "opaque", b"payload")

    response = invocation_port.invoke(request)

    assert response.status is InvocationStatus.ACCEPTED
    assert response.execution_identifier is not None
    assert observation_port.get_execution(response.execution_identifier) is not None
