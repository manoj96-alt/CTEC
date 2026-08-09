"""Single facade for the in-process Cognitive Engine runtime shell."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from threading import RLock, Thread
from uuid import UUID

from app.runtime.contracts import (
    ExecutionSnapshot,
    InvocationRejectionCategory,
    InvocationRequest,
    InvocationResponse,
    InvocationStatus,
)
from app.runtime.execution_state import ExecutionState
from app.runtime.execution_store import ExecutionStore, InMemoryExecutionStore
from app.runtime.invocation import InvocationAdmissionService
from app.runtime.orchestration import (
    CapabilityStepError,
    CapabilityStepInput,
    CapabilityStepPorts,
    RuntimeOrchestrator,
)
from app.runtime.recovery import ValidatedRecoveryInvocation


@dataclass(frozen=True, slots=True)
class _ResultOverlay:
    admitted_at: datetime
    completed_at: datetime | None = None
    produced_record_references: tuple[UUID, ...] = ()
    result_code: str | None = None
    result_value: str | None = None
    actionable: bool = False


class CognitiveEngineRuntime:
    def __init__(self, ports: CapabilityStepPorts, store: ExecutionStore | None = None) -> None:
        self._store = store or InMemoryExecutionStore()
        self._admission = InvocationAdmissionService(self._store)
        self._orchestrator = RuntimeOrchestrator(ports, self._store)
        self._result_lock = RLock()
        self._control_fingerprints: dict[tuple[str, UUID], bytes] = {}
        self._result_overlays: dict[UUID, _ResultOverlay] = {}
        self._started_recoveries: set[UUID] = set()

    def invoke(self, request: InvocationRequest) -> InvocationResponse:
        validation = self._validate_control_metadata(request)
        if validation is not None:
            return validation
        key = (request.protocol_version, request.request_identifier)
        control_fingerprint = sha256(
            repr((request.control_metadata_version, request.authority_context)).encode()
        ).digest()
        with self._result_lock:
            existing = self._control_fingerprints.get(key)
            if existing is not None and existing != control_fingerprint:
                return InvocationResponse(
                    status=InvocationStatus.REJECTED,
                    rejection_category=InvocationRejectionCategory.INVOCATION_REJECTION,
                    rejection_reason="Idempotency Conflict",
                )
            self._control_fingerprints.setdefault(key, control_fingerprint)
        admission = self._admission.admit(request)
        response = admission.response
        if admission.starts_execution:
            if response.execution_identifier is None:
                raise RuntimeError("A new admission must identify its execution")
            worker = Thread(
                target=self._execute,
                args=(request, response.execution_identifier),
                daemon=True,
                name=f"ctec-execution-{response.execution_identifier}",
            )
            worker.start()
        return response

    def resume(self, recovery: ValidatedRecoveryInvocation) -> InvocationResponse:
        """Resume a server-validated attempt; ordinary callers cannot select a stage."""
        if not recovery.validated:
            raise PermissionError("Recovery invocation was not validated by the durable boundary")
        with self._result_lock:
            starts_execution = recovery.recovery_identifier not in self._started_recoveries
            if starts_execution:
                self._started_recoveries.add(recovery.recovery_identifier)
        snapshot = self._store.get(recovery.execution_identifier)
        if snapshot is None:
            raise KeyError("Validated recovery execution is unavailable")
        if starts_execution:
            worker = Thread(
                target=self._execute_recovery,
                args=(recovery,),
                daemon=True,
                name=f"ctec-recovery-{recovery.execution_identifier}",
            )
            worker.start()
        return InvocationResponse(
            status=InvocationStatus.ACCEPTED,
            execution_identifier=recovery.execution_identifier,
            execution_reference=recovery.logical_execution_identifier,
            execution_state=snapshot.state,
        )

    def get_execution(self, execution_identifier: UUID) -> ExecutionSnapshot | None:
        snapshot = self._store.get(execution_identifier)
        if snapshot is None:
            return None
        with self._result_lock:
            overlay = self._result_overlays.get(execution_identifier)
        if overlay is None:
            return snapshot
        return replace(
            snapshot,
            admitted_at=overlay.admitted_at,
            completed_at=overlay.completed_at,
            produced_record_references=overlay.produced_record_references,
            result_code=overlay.result_code,
            result_value=overlay.result_value,
            actionable=overlay.actionable,
        )

    def _execute(self, request: InvocationRequest, execution_identifier: UUID) -> None:
        admitted_at = datetime.now(UTC)
        step_input = CapabilityStepInput(
            protocol_version=request.protocol_version,
            correlation_identifier=request.correlation_identifier,
            request_identifier=request.request_identifier,
            session_identifier=request.session_identifier,
            execution_identifier=execution_identifier,
            opaque_payload=request.opaque_payload,
            authority_context=request.authority_context,
            admitted_at=admitted_at,
        )
        self._execute_from(step_input, admitted_at, 0)

    def _execute_recovery(self, recovery: ValidatedRecoveryInvocation) -> None:
        step_input = CapabilityStepInput(
            protocol_version=recovery.protocol_version,
            correlation_identifier=recovery.correlation_identifier,
            request_identifier=recovery.request_identifier,
            session_identifier=recovery.session_identifier,
            execution_identifier=recovery.execution_identifier,
            opaque_payload=recovery.opaque_payload,
            authority_context=recovery.authority_context,
            admitted_at=recovery.admitted_at,
        )
        self._execute_from(step_input, recovery.admitted_at, recovery.resume_stage_ordinal)

    def _execute_from(
        self, step_input: CapabilityStepInput, admitted_at: datetime, start_stage_ordinal: int
    ) -> None:
        execution_identifier = step_input.execution_identifier
        with self._result_lock:
            self._result_overlays[execution_identifier] = _ResultOverlay(admitted_at)
        self._store.advance(execution_identifier, ExecutionState.EXECUTING)
        try:
            result = self._orchestrator.execute_from(step_input, start_stage_ordinal)
        # The runtime boundary must convert every unexpected adapter failure into
        # the governed technical-failure state without leaking implementation data.
        except (CapabilityStepError, Exception):  # noqa: BLE001
            self._store.advance(execution_identifier, ExecutionState.FAILED)
            return
        completed_at = datetime.now(UTC)
        with self._result_lock:
            self._result_overlays[execution_identifier] = _ResultOverlay(
                admitted_at=admitted_at,
                completed_at=completed_at,
                produced_record_references=result.produced_record_references,
                result_code=result.result_code,
                result_value=result.result_value,
                actionable=result.actionable,
            )
        self._store.record_result(
            execution_identifier,
            result_code=result.result_code,
            result_value=result.result_value,
            actionable=result.actionable,
            completed_at=completed_at,
        )
        self._store.advance(execution_identifier, ExecutionState.COMPLETED)

    @staticmethod
    def _validate_control_metadata(request: InvocationRequest) -> InvocationResponse | None:
        if not request.protocol_version.strip():
            return None
        if request.protocol_version == "1.0":
            if (
                request.authority_context is not None
                or request.control_metadata_version is not None
            ):
                return CognitiveEngineRuntime._control_rejection(
                    "Legacy invocation cannot carry trusted control metadata"
                )
            return None
        if request.protocol_version != "2.0":
            return CognitiveEngineRuntime._control_rejection("Unsupported Protocol Version")
        if request.control_metadata_version != "1.0" or request.authority_context is None:
            return CognitiveEngineRuntime._control_rejection(
                "Required AuthorityContext is missing or unsupported"
            )
        try:
            request.authority_context.validate_for(
                request_id=request.request_identifier,
                correlation_id=request.correlation_identifier,
                now=datetime.now(UTC),
            )
        except (ValueError, PermissionError):
            return CognitiveEngineRuntime._control_rejection("AuthorityContext validation failed")
        return None

    @staticmethod
    def _control_rejection(reason: str) -> InvocationResponse:
        return InvocationResponse(
            status=InvocationStatus.REJECTED,
            rejection_category=InvocationRejectionCategory.VALIDATION_FAILURE,
            rejection_reason=reason,
        )
