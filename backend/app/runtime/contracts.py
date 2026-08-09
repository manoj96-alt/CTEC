"""Opaque contracts exposed by the in-process Cognitive Engine runtime shell."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.integration.contracts import AuthorityContext
from app.runtime.execution_state import ExecutionState, ExecutionTransition


class InvocationStatus(StrEnum):
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


class InvocationRejectionCategory(StrEnum):
    INVALID_INVOCATION = "Invalid Invocation"
    VALIDATION_FAILURE = "Validation Failure"
    INVOCATION_REJECTION = "Invocation Rejection"


IDEMPOTENCY_CONFLICT_REASON = "Idempotency Conflict"


@dataclass(frozen=True, slots=True)
class InvocationRequest:
    protocol_version: str
    correlation_identifier: UUID
    request_identifier: UUID
    session_identifier: UUID
    request_classification: str
    opaque_payload: bytes
    authority_context: AuthorityContext | None = None
    control_metadata_version: str | None = None
    admitted_payload_builder: Callable[[datetime], bytes] | None = None


@dataclass(frozen=True, slots=True)
class InvocationResponse:
    status: InvocationStatus
    execution_identifier: UUID | None = None
    execution_reference: UUID | None = None
    execution_state: ExecutionState | None = None
    rejection_category: InvocationRejectionCategory | None = None
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionSnapshot:
    execution_identifier: UUID
    execution_reference: UUID
    protocol_version: str
    correlation_identifier: UUID
    request_identifier: UUID
    session_identifier: UUID
    state: ExecutionState
    transition_history: tuple[ExecutionTransition, ...]
    admitted_at: datetime | None = None
    completed_at: datetime | None = None
    produced_record_references: tuple[UUID, ...] = ()
    result_code: str | None = None
    result_value: str | None = None
    actionable: bool = False


class CognitiveEngineInvocationPort(Protocol):
    def invoke(self, request: InvocationRequest) -> InvocationResponse: ...


class ExecutionObservationPort(Protocol):
    def get_execution(self, execution_identifier: UUID) -> ExecutionSnapshot | None: ...
