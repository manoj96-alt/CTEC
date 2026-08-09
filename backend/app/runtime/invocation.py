"""Invocation validation and process-local admission."""

from dataclasses import dataclass
from hashlib import sha256

from app.runtime.contracts import (
    InvocationRejectionCategory,
    InvocationRequest,
    InvocationResponse,
    InvocationStatus,
)
from app.runtime.execution_store import ExecutionStore


@dataclass(frozen=True, slots=True)
class InvocationAdmission:
    response: InvocationResponse
    starts_execution: bool


class InvocationAdmissionService:
    def __init__(self, store: ExecutionStore) -> None:
        self._store = store

    def admit(self, request: InvocationRequest) -> InvocationAdmission:
        rejection = self._validate(request)
        if rejection is not None:
            return InvocationAdmission(rejection, starts_execution=False)

        fingerprint = sha256(request.opaque_payload).digest()
        admission = self._store.admit(request, fingerprint)
        if admission.is_conflict:
            return InvocationAdmission(
                InvocationResponse(
                    status=InvocationStatus.REJECTED,
                    rejection_category=InvocationRejectionCategory.INVOCATION_REJECTION,
                    rejection_reason="Idempotency Conflict",
                ),
                starts_execution=False,
            )

        if admission.execution_identifier is None:
            raise RuntimeError("A non-conflicting admission must identify an execution")
        snapshot = self._store.get(admission.execution_identifier)
        if snapshot is None:
            raise RuntimeError("An admitted execution must have process-local state")
        return InvocationAdmission(
            InvocationResponse(
                status=InvocationStatus.ACCEPTED,
                execution_identifier=snapshot.execution_identifier,
                execution_reference=snapshot.execution_reference,
                execution_state=snapshot.state,
            ),
            starts_execution=admission.is_new,
        )

    @staticmethod
    def _validate(request: InvocationRequest) -> InvocationResponse | None:
        if not request.protocol_version.strip() or not request.request_classification.strip():
            return InvocationResponse(
                status=InvocationStatus.REJECTED,
                rejection_category=InvocationRejectionCategory.INVALID_INVOCATION,
                rejection_reason="Required invocation field is empty",
            )
        if not isinstance(request.opaque_payload, bytes):
            return InvocationResponse(
                status=InvocationStatus.REJECTED,
                rejection_category=InvocationRejectionCategory.VALIDATION_FAILURE,
                rejection_reason="Opaque payload must be bytes",
            )
        return None
