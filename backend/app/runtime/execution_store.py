"""Thread-safe, non-durable execution and idempotency state."""

from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Protocol
from uuid import UUID, uuid4

from app.runtime.contracts import ExecutionSnapshot, InvocationRequest
from app.runtime.execution_state import ExecutionState, initial_transition, transition


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    execution_identifier: UUID | None
    is_new: bool
    is_conflict: bool


class ExecutionStore(Protocol):
    def admit(self, request: InvocationRequest, payload_fingerprint: bytes) -> AdmissionResult: ...
    def get(self, execution_identifier: UUID) -> ExecutionSnapshot | None: ...
    def advance(self, execution_identifier: UUID, target_state: ExecutionState) -> None: ...
    def checkpoint(
        self,
        execution_identifier: UUID,
        *,
        stage_name: str,
        stage_ordinal: int,
        input_payload: bytes,
        output_payload: bytes,
        artifact_references: tuple[UUID, ...],
        completed_at: datetime,
    ) -> None: ...
    def record_result(
        self,
        execution_identifier: UUID,
        *,
        result_code: str | None,
        result_value: str | None,
        actionable: bool,
        completed_at: datetime,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class _Admission:
    payload_fingerprint: bytes
    execution_identifier: UUID


class InMemoryExecutionStore:
    """Owns process-local snapshots and atomic first admission."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._admissions: dict[tuple[str, UUID], _Admission] = {}
        self._snapshots: dict[UUID, ExecutionSnapshot] = {}

    def admit(self, request: InvocationRequest, payload_fingerprint: bytes) -> AdmissionResult:
        key = (request.protocol_version, request.request_identifier)
        with self._lock:
            existing = self._admissions.get(key)
            if existing is not None:
                if existing.payload_fingerprint != payload_fingerprint:
                    return AdmissionResult(None, is_new=False, is_conflict=True)
                return AdmissionResult(
                    existing.execution_identifier, is_new=False, is_conflict=False
                )

            execution_identifier = uuid4()
            execution_reference = uuid4()
            self._admissions[key] = _Admission(payload_fingerprint, execution_identifier)
            self._snapshots[execution_identifier] = ExecutionSnapshot(
                execution_identifier=execution_identifier,
                execution_reference=execution_reference,
                protocol_version=request.protocol_version,
                correlation_identifier=request.correlation_identifier,
                request_identifier=request.request_identifier,
                session_identifier=request.session_identifier,
                state=ExecutionState.ACCEPTED,
                transition_history=(initial_transition(),),
            )
            return AdmissionResult(execution_identifier, is_new=True, is_conflict=False)

    def get(self, execution_identifier: UUID) -> ExecutionSnapshot | None:
        with self._lock:
            return self._snapshots.get(execution_identifier)

    def advance(self, execution_identifier: UUID, target_state: ExecutionState) -> None:
        with self._lock:
            current = self._snapshots[execution_identifier]
            next_transition = transition(current.state, target_state)
            self._snapshots[execution_identifier] = ExecutionSnapshot(
                execution_identifier=current.execution_identifier,
                execution_reference=current.execution_reference,
                protocol_version=current.protocol_version,
                correlation_identifier=current.correlation_identifier,
                request_identifier=current.request_identifier,
                session_identifier=current.session_identifier,
                state=target_state,
                transition_history=current.transition_history + (next_transition,),
            )

    def checkpoint(
        self,
        execution_identifier: UUID,
        *,
        stage_name: str,
        stage_ordinal: int,
        input_payload: bytes,
        output_payload: bytes,
        artifact_references: tuple[UUID, ...],
        completed_at: datetime,
    ) -> None:
        """Process-local compatibility implementation; CDD-010 remains unchanged."""

    def record_result(
        self,
        execution_identifier: UUID,
        *,
        result_code: str | None,
        result_value: str | None,
        actionable: bool,
        completed_at: datetime,
    ) -> None:
        """Process-local results remain owned by the runtime overlay."""
