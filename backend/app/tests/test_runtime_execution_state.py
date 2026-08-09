from uuid import uuid4

import pytest

from app.runtime.contracts import InvocationRequest
from app.runtime.execution_state import (
    ExecutionState,
    InvalidExecutionTransition,
    transition,
)
from app.runtime.execution_store import InMemoryExecutionStore


def test_only_esm_transitions_are_valid() -> None:
    assert transition(ExecutionState.ACCEPTED, ExecutionState.EXECUTING).current_state is (
        ExecutionState.EXECUTING
    )
    assert transition(ExecutionState.EXECUTING, ExecutionState.COMPLETED).current_state is (
        ExecutionState.COMPLETED
    )
    assert transition(ExecutionState.EXECUTING, ExecutionState.FAILED).current_state is (
        ExecutionState.FAILED
    )

    for terminal in (ExecutionState.COMPLETED, ExecutionState.FAILED):
        with pytest.raises(InvalidExecutionTransition):
            transition(terminal, ExecutionState.EXECUTING)


def test_store_replaces_snapshot_and_preserves_immutable_history() -> None:
    store = InMemoryExecutionStore()
    request = InvocationRequest("1.0", uuid4(), uuid4(), uuid4(), "opaque", b"payload")
    admission = store.admit(request, b"fingerprint")
    assert admission.execution_identifier is not None
    accepted = store.get(admission.execution_identifier)
    assert accepted is not None

    store.advance(admission.execution_identifier, ExecutionState.EXECUTING)
    store.advance(admission.execution_identifier, ExecutionState.COMPLETED)
    completed = store.get(admission.execution_identifier)

    assert accepted.state is ExecutionState.ACCEPTED
    assert len(accepted.transition_history) == 1
    assert completed is not None
    assert completed.state is ExecutionState.COMPLETED
    assert tuple(item.current_state for item in completed.transition_history) == (
        ExecutionState.ACCEPTED,
        ExecutionState.EXECUTING,
        ExecutionState.COMPLETED,
    )
    with pytest.raises(InvalidExecutionTransition):
        store.advance(admission.execution_identifier, ExecutionState.EXECUTING)
