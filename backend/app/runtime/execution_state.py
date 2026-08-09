"""ESM-compliant process-local execution states and transitions."""

from dataclasses import dataclass
from enum import StrEnum


class ExecutionState(StrEnum):
    ACCEPTED = "Accepted"
    EXECUTING = "Executing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class InvalidExecutionTransition(ValueError):
    """Raised when a transition is not authorized by ESM-001."""


@dataclass(frozen=True, slots=True)
class ExecutionTransition:
    previous_state: ExecutionState | None
    current_state: ExecutionState


_VALID_TRANSITIONS: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.ACCEPTED: frozenset({ExecutionState.EXECUTING}),
    ExecutionState.EXECUTING: frozenset({ExecutionState.COMPLETED, ExecutionState.FAILED}),
    ExecutionState.COMPLETED: frozenset(),
    ExecutionState.FAILED: frozenset(),
}


def initial_transition() -> ExecutionTransition:
    return ExecutionTransition(previous_state=None, current_state=ExecutionState.ACCEPTED)


def transition(current_state: ExecutionState, target_state: ExecutionState) -> ExecutionTransition:
    if target_state not in _VALID_TRANSITIONS[current_state]:
        raise InvalidExecutionTransition(
            f"Execution cannot transition from {current_state.value} to {target_state.value}"
        )
    return ExecutionTransition(previous_state=current_state, current_state=target_state)
