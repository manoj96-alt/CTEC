from dataclasses import replace
from itertools import pairwise
from uuid import uuid4

import pytest

from app.runtime.orchestration import (
    CapabilityStepError,
    CapabilityStepInput,
    CapabilityStepOutput,
    CapabilityStepPorts,
    RuntimeOrchestrator,
)


class RecordingStep:
    def __init__(self, name: str, trace: list[str], suffix: bytes = b"") -> None:
        self.name = name
        self.trace = trace
        self.suffix = suffix
        self.inputs: list[CapabilityStepInput] = []

    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        self.trace.append(self.name)
        self.inputs.append(step_input)
        return CapabilityStepOutput(
            step_input.protocol_version,
            step_input.correlation_identifier,
            step_input.request_identifier,
            step_input.session_identifier,
            step_input.execution_identifier,
            step_input.opaque_payload + self.suffix,
        )


class FailingStep(RecordingStep):
    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        self.trace.append(self.name)
        raise CapabilityStepError("failed")


def initial_input() -> CapabilityStepInput:
    return CapabilityStepInput("1.0", uuid4(), uuid4(), uuid4(), uuid4(), b"opaque")


def test_six_ports_execute_once_in_frozen_order_with_opaque_pass_through() -> None:
    trace: list[str] = []
    names = ("ERM", "SRM", "ASM", "KRM", "DRM", "GRM")
    steps = tuple(RecordingStep(name, trace, name.encode()) for name in names)
    orchestrator = RuntimeOrchestrator(CapabilityStepPorts(*steps))
    original = initial_input()

    result = orchestrator.execute(original)

    assert trace == list(names)
    assert result.opaque_payload == b"opaqueERMSRMASMKRMDRMGRM"
    assert steps[0].inputs[0] == original
    for previous, current in pairwise(steps):
        assert current.inputs[0].opaque_payload == (
            previous.inputs[0].opaque_payload + previous.suffix
        )


def test_failure_is_fail_fast_and_remaining_ports_are_not_called() -> None:
    trace: list[str] = []
    steps = (
        RecordingStep("ERM", trace),
        FailingStep("SRM", trace),
        RecordingStep("ASM", trace),
        RecordingStep("KRM", trace),
        RecordingStep("DRM", trace),
        RecordingStep("GRM", trace),
    )

    with pytest.raises(CapabilityStepError):
        RuntimeOrchestrator(CapabilityStepPorts(*steps)).execute(initial_input())

    assert trace == ["ERM", "SRM"]


def test_step_cannot_change_governed_runtime_metadata() -> None:
    trace: list[str] = []

    class MutatingStep(RecordingStep):
        def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
            output = super().execute(step_input)
            return replace(output, execution_identifier=uuid4())

    good = RecordingStep("good", trace)
    bad = MutatingStep("bad", trace)

    with pytest.raises(CapabilityStepError, match="metadata"):
        RuntimeOrchestrator(CapabilityStepPorts(good, bad, good, good, good, good)).execute(
            initial_input()
        )
