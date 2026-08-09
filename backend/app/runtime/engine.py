"""Single facade for the in-process Cognitive Engine runtime shell."""

from threading import Thread
from uuid import UUID

from app.runtime.contracts import ExecutionSnapshot, InvocationRequest, InvocationResponse
from app.runtime.execution_state import ExecutionState
from app.runtime.execution_store import InMemoryExecutionStore
from app.runtime.invocation import InvocationAdmissionService
from app.runtime.orchestration import (
    CapabilityStepError,
    CapabilityStepInput,
    CapabilityStepPorts,
    RuntimeOrchestrator,
)


class CognitiveEngineRuntime:
    def __init__(self, ports: CapabilityStepPorts) -> None:
        self._store = InMemoryExecutionStore()
        self._admission = InvocationAdmissionService(self._store)
        self._orchestrator = RuntimeOrchestrator(ports)

    def invoke(self, request: InvocationRequest) -> InvocationResponse:
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

    def get_execution(self, execution_identifier: UUID) -> ExecutionSnapshot | None:
        return self._store.get(execution_identifier)

    def _execute(self, request: InvocationRequest, execution_identifier: UUID) -> None:
        self._store.advance(execution_identifier, ExecutionState.EXECUTING)
        step_input = CapabilityStepInput(
            protocol_version=request.protocol_version,
            correlation_identifier=request.correlation_identifier,
            request_identifier=request.request_identifier,
            session_identifier=request.session_identifier,
            execution_identifier=execution_identifier,
            opaque_payload=request.opaque_payload,
        )
        try:
            self._orchestrator.execute(step_input)
        except CapabilityStepError:
            self._store.advance(execution_identifier, ExecutionState.FAILED)
            return
        self._store.advance(execution_identifier, ExecutionState.COMPLETED)
