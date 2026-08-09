from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Event, Lock
from time import monotonic, sleep
from uuid import uuid4

from app.integration.contracts import AuthorityContext
from app.runtime.contracts import (
    IDEMPOTENCY_CONFLICT_REASON,
    InvocationRejectionCategory,
    InvocationRequest,
    InvocationStatus,
)
from app.runtime.engine import CognitiveEngineRuntime
from app.runtime.execution_state import ExecutionState
from app.runtime.orchestration import (
    CapabilityStepError,
    CapabilityStepInput,
    CapabilityStepOutput,
    CapabilityStepPorts,
)


class CountingStep:
    def __init__(self, entered: Event | None = None, release: Event | None = None) -> None:
        self._entered = entered
        self._release = release
        self._lock = Lock()
        self.call_count = 0

    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        with self._lock:
            self.call_count += 1
        if self._entered is not None:
            self._entered.set()
        if self._release is not None:
            self._release.wait(timeout=2)
        return CapabilityStepOutput(
            step_input.protocol_version,
            step_input.correlation_identifier,
            step_input.request_identifier,
            step_input.session_identifier,
            step_input.execution_identifier,
            step_input.opaque_payload,
        )


class FailingStep:
    def execute(self, step_input: CapabilityStepInput) -> CapabilityStepOutput:
        raise CapabilityStepError("opaque failure")


def request(payload: bytes = b"payload") -> InvocationRequest:
    return InvocationRequest("1.0", uuid4(), uuid4(), uuid4(), "opaque", payload)


def runtime_with(step: object) -> CognitiveEngineRuntime:
    return CognitiveEngineRuntime(CapabilityStepPorts(*([step] * 6)))  # type: ignore[arg-type]


def wait_for_state(
    runtime: CognitiveEngineRuntime,
    execution_identifier: object,
    state: ExecutionState,
) -> None:
    deadline = monotonic() + 2
    while monotonic() < deadline:
        snapshot = runtime.get_execution(execution_identifier)  # type: ignore[arg-type]
        if snapshot is not None and snapshot.state is state:
            return
        sleep(0.005)
    raise AssertionError(f"Execution did not reach {state.value}")


def test_invalid_invocation_is_rejected_without_execution_identifier() -> None:
    runtime = runtime_with(CountingStep())

    response = runtime.invoke(replace(request(), protocol_version=" "))

    assert response.status is InvocationStatus.REJECTED
    assert response.rejection_category is InvocationRejectionCategory.INVALID_INVOCATION
    assert response.execution_identifier is None
    assert response.execution_reference is None


def test_new_protocol_rejects_missing_malformed_and_conflicting_authority() -> None:
    runtime = runtime_with(CountingStep())
    missing = runtime.invoke(replace(request(), protocol_version="2.0"))
    assert missing.status is InvocationStatus.REJECTED
    now = datetime.now(UTC)
    value = request()
    authority = AuthorityContext(
        "principal",
        "Service",
        "enterprise",
        ("role",),
        ("scope",),
        "AUTHORIZED",
        "authz",
        "gateway",
        value.request_identifier,
        value.correlation_identifier,
        now - timedelta(seconds=1),
        now + timedelta(minutes=1),
    )
    accepted_request = replace(
        value, protocol_version="2.0", authority_context=authority, control_metadata_version="1.0"
    )
    accepted = runtime.invoke(accepted_request)
    assert accepted.status is InvocationStatus.ACCEPTED
    conflict = runtime.invoke(
        replace(accepted_request, authority_context=replace(authority, roles=("other",)))
    )
    assert conflict.status is InvocationStatus.REJECTED
    unsupported = runtime.invoke(replace(request(), protocol_version="99"))
    assert unsupported.status is InvocationStatus.REJECTED


def test_concurrent_identical_admission_creates_one_execution() -> None:
    entered, release = Event(), Event()
    step = CountingStep(entered, release)
    runtime = runtime_with(step)
    invocation = request()

    with ThreadPoolExecutor(max_workers=12) as pool:
        responses = list(pool.map(lambda _: runtime.invoke(invocation), range(12)))
    assert entered.wait(timeout=1)

    identifiers = {response.execution_identifier for response in responses}
    assert len(identifiers) == 1
    assert None not in identifiers
    assert all(response.status is InvocationStatus.ACCEPTED for response in responses)
    assert step.call_count == 1
    release.set()


def test_active_and_terminal_replay_return_existing_execution_without_work() -> None:
    entered, release = Event(), Event()
    step = CountingStep(entered, release)
    runtime = runtime_with(step)
    invocation = request()

    first = runtime.invoke(invocation)
    assert entered.wait(timeout=1)
    active = runtime.invoke(invocation)
    assert active.execution_identifier == first.execution_identifier
    assert active.execution_state in {ExecutionState.ACCEPTED, ExecutionState.EXECUTING}
    assert step.call_count == 1

    release.set()
    assert first.execution_identifier is not None
    wait_for_state(runtime, first.execution_identifier, ExecutionState.COMPLETED)
    terminal = runtime.invoke(invocation)
    assert terminal.execution_identifier == first.execution_identifier
    assert terminal.execution_state is ExecutionState.COMPLETED
    assert step.call_count == 6


def test_conflicting_replay_is_rejected_and_starts_no_work() -> None:
    entered, release = Event(), Event()
    step = CountingStep(entered, release)
    runtime = runtime_with(step)
    original = request()
    first = runtime.invoke(original)
    assert entered.wait(timeout=1)

    conflict = runtime.invoke(replace(original, opaque_payload=b"different"))

    assert conflict.status is InvocationStatus.REJECTED
    assert conflict.rejection_category is InvocationRejectionCategory.INVOCATION_REJECTION
    assert conflict.rejection_reason == IDEMPOTENCY_CONFLICT_REASON
    assert conflict.execution_identifier is None
    assert first.execution_identifier is not None
    assert step.call_count == 1
    release.set()


def test_failed_replay_starts_no_work_and_retry_needs_new_request_identifier() -> None:
    runtime = runtime_with(FailingStep())
    original = request()
    first = runtime.invoke(original)
    assert first.execution_identifier is not None
    wait_for_state(runtime, first.execution_identifier, ExecutionState.FAILED)

    replay = runtime.invoke(original)
    retry = runtime.invoke(replace(original, request_identifier=uuid4()))

    assert replay.execution_identifier == first.execution_identifier
    assert replay.execution_state is ExecutionState.FAILED
    assert retry.execution_identifier is not None
    assert retry.execution_identifier != first.execution_identifier
