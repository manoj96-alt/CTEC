from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.integration.contracts import AuthorityContext
from app.runtime.engine import CognitiveEngineRuntime
from app.runtime.orchestration import (
    CapabilityStepInput,
    CapabilityStepOutput,
    CapabilityStepPorts,
    RuntimeOrchestrator,
)
from app.runtime.recovery import ValidatedRecoveryInvocation


class RecordingStep:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def execute(self, value: CapabilityStepInput) -> CapabilityStepOutput:
        self.calls.append(self.name)
        return CapabilityStepOutput(
            value.protocol_version,
            value.correlation_identifier,
            value.request_identifier,
            value.session_identifier,
            value.execution_identifier,
            value.opaque_payload + self.name.encode(),
        )


def runtime(calls: list[str]) -> RuntimeOrchestrator:
    steps = [RecordingStep(name, calls) for name in ("ERM", "SRM", "ASM", "KRM", "DRM", "GRM")]
    return RuntimeOrchestrator(CapabilityStepPorts(*steps))


def input_value() -> CapabilityStepInput:
    return CapabilityStepInput(
        "2.0", uuid4(), uuid4(), uuid4(), uuid4(), b"checkpoint", admitted_at=datetime.now(UTC)
    )


@pytest.mark.parametrize("ordinal", range(6))
def test_resume_invokes_only_selected_and_downstream_stages(ordinal: int) -> None:
    names = ["ERM", "SRM", "ASM", "KRM", "DRM", "GRM"]
    calls: list[str] = []
    runtime(calls).execute_from(input_value(), ordinal)
    assert calls == names[ordinal:]


def test_invalid_resume_stage_fails_closed() -> None:
    with pytest.raises(ValueError, match="Resume stage"):
        runtime([]).execute_from(input_value(), 6)


def test_runtime_rejects_caller_constructed_recovery_invocation() -> None:
    now = datetime.now(UTC)
    request_id = uuid4()
    correlation = uuid4()
    authority = AuthorityContext(
        "operator",
        "Service",
        "tenant",
        ("EXECUTION_RECOVERY_OPERATOR",),
        ("execution:replay",),
        "AUTHORIZED",
        "auth-ref",
        "trusted-boundary",
        request_id,
        correlation,
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )
    calls: list[str] = []
    forged = ValidatedRecoveryInvocation(
        uuid4(),
        uuid4(),
        "2.0",
        correlation,
        request_id,
        uuid4(),
        "supplier-risk",
        b"payload",
        authority,
        now,
        1,
        uuid4(),
        object(),
    )
    with pytest.raises(PermissionError, match="not validated"):
        CognitiveEngineRuntime(runtime(calls)._ports).resume(forged)
    assert calls == []
