"""Application boundary over the existing runtime and durable execution store."""

import json
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.schemas import (
    AttemptListResponse,
    AttemptResponse,
    ExecutionResponse,
    GovernedResultResponse,
    ReplayRequest,
    RetryRequest,
    StageListResponse,
    StageResponse,
    SubmissionResponse,
    SupplierRiskSubmission,
)
from app.api.supplier_risk.security import authority_context
from app.integration.contracts import AuthorityContext, IntegrationEnvelope
from app.runtime.contracts import InvocationRequest, InvocationStatus
from app.runtime.engine import CognitiveEngineRuntime
from app.runtime.execution_state import ExecutionState
from app.runtime.persistence.contracts import (
    AttemptProjection,
    ReplayAuthorization,
    ResultProjection,
    RetryAuthorization,
    StageProjection,
)
from app.runtime.recovery import ValidatedRecoveryInvocation


class ExecutionApiStore(Protocol):
    def list_attempts(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> tuple[AttemptProjection, ...]: ...

    def list_stages(
        self, logical_execution_id: UUID, execution_id: UUID, tenant_id: str
    ) -> tuple[StageProjection, ...]: ...

    def get_result_for_logical(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> ResultProjection | None: ...

    def prepare_retry(
        self,
        original_execution_id: UUID,
        authorization: RetryAuthorization,
        authority_context: AuthorityContext,
    ) -> ValidatedRecoveryInvocation: ...

    def prepare_replay(
        self,
        original_execution_id: UUID,
        authorization: ReplayAuthorization,
        authority_context: AuthorityContext,
    ) -> ValidatedRecoveryInvocation: ...


class SupplierRiskApiService:
    def __init__(
        self,
        runtime: CognitiveEngineRuntime,
        store: ExecutionApiStore | None = None,
    ) -> None:
        self._runtime = runtime
        self._store = store

    def submit(
        self, request: SupplierRiskSubmission, principal: TrustedPrincipal
    ) -> SubmissionResponse:
        envelope = IntegrationEnvelope.from_bytes(_envelope_bytes(request.supplier_risk))
        control = authority_context(
            principal,
            request_id=request.request_identifier,
            correlation_id=request.correlation_identifier,
        )
        invocation = InvocationRequest(
            protocol_version="2.0",
            correlation_identifier=request.correlation_identifier,
            request_identifier=request.request_identifier,
            session_identifier=request.session_identifier,
            request_classification="supplier-risk",
            opaque_payload=envelope.to_bytes(),
            authority_context=control,
            control_metadata_version="1.0",
        )
        result = self._runtime.invoke(invocation)
        if result.status is not InvocationStatus.ACCEPTED or result.execution_identifier is None:
            raise RuntimeError(result.rejection_reason or "INVOCATION_REJECTED")
        return SubmissionResponse(
            execution_identifier=result.execution_identifier,
            logical_execution_identifier=result.execution_reference or result.execution_identifier,
            correlation_identifier=request.correlation_identifier,
            state=str(result.execution_state or "Accepted"),
        )

    def get(self, execution_id: UUID, principal: TrustedPrincipal) -> ExecutionResponse | None:
        if self._store is not None:
            attempts = self._store.list_attempts(execution_id, principal.tenant_id)
            if not attempts:
                return None
            attempt_id = attempts[-1].execution_id
        else:
            attempt_id = execution_id
        snapshot = self._runtime.get_execution(attempt_id)
        if snapshot is None:
            return None
        return ExecutionResponse(
            execution_identifier=snapshot.execution_identifier,
            logical_execution_identifier=snapshot.execution_reference,
            correlation_identifier=snapshot.correlation_identifier,
            state=snapshot.state.value,
            admitted_at=snapshot.admitted_at.isoformat() if snapshot.admitted_at else None,
            completed_at=snapshot.completed_at.isoformat() if snapshot.completed_at else None,
            result_code=snapshot.result_code,
            recommendation=snapshot.result_value,
            actionable=snapshot.actionable,
            produced_record_references=list(snapshot.produced_record_references),
        )

    def attempts(
        self, logical_execution_id: UUID, principal: TrustedPrincipal, *, offset: int, limit: int
    ) -> AttemptListResponse | None:
        if self._store is None:
            return None
        values = self._store.list_attempts(logical_execution_id, principal.tenant_id)
        if not values:
            return None
        selected = values[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(values) else None
        return AttemptListResponse(
            items=[
                AttemptResponse(
                    execution_identifier=value.execution_id,
                    logical_execution_identifier=value.logical_execution_id,
                    state=value.state,
                    admitted_at=value.admitted_at,
                    completed_at=value.terminal_at,
                    revision=value.revision,
                )
                for value in selected
            ],
            next_cursor=next_cursor,
        )

    def stages(
        self, logical_execution_id: UUID, execution_id: UUID, principal: TrustedPrincipal
    ) -> StageListResponse | None:
        if self._store is None:
            return None
        values = self._store.list_stages(logical_execution_id, execution_id, principal.tenant_id)
        if not values:
            return None
        return StageListResponse(
            items=[
                StageResponse(
                    stage_identifier=value.stage_id,
                    stage_name=value.stage_name,
                    stage_ordinal=value.stage_ordinal,
                    status=value.status,
                    started_at=value.started_at,
                    completed_at=value.completed_at,
                    safe_failure_code=value.safe_failure_code,
                    produced_record_references=list(value.produced_record_references),
                )
                for value in values
            ]
        )

    def result(
        self, logical_execution_id: UUID, principal: TrustedPrincipal
    ) -> GovernedResultResponse | None:
        if self._store is None:
            return None
        value = self._store.get_result_for_logical(logical_execution_id, principal.tenant_id)
        if value is None:
            return None
        return GovernedResultResponse(
            execution_identifier=value.execution_id,
            governance_standing=value.result_code,
            recommendation=value.result_value,
            actionable=value.actionable,
            completed_at=value.completed_at,
            produced_record_references=list(value.produced_record_references),
        )

    def retry(
        self, logical_execution_id: UUID, request: RetryRequest, principal: TrustedPrincipal
    ) -> SubmissionResponse:
        if self._store is None:
            raise RuntimeError("DURABLE_RECOVERY_UNAVAILABLE")
        attempts = self._store.list_attempts(logical_execution_id, principal.tenant_id)
        if not attempts:
            raise LookupError("RESOURCE_NOT_FOUND")
        original = attempts[-1]
        if original.state != "Failed":
            raise ValueError("RETRY_NOT_ELIGIBLE")
        context = authority_context(
            principal,
            request_id=request.request_identifier,
            correlation_id=request.correlation_identifier,
        )
        recovery = self._store.prepare_retry(
            original.execution_id,
            RetryAuthorization(
                principal.principal_id,
                principal.tenant_id,
                principal.scopes,
                context.authorization_reference,
                request.reason,
                request.correlation_identifier,
                datetime.now(UTC),
            ),
            context,
        )
        return self._resume(recovery)

    def replay(
        self, logical_execution_id: UUID, request: ReplayRequest, principal: TrustedPrincipal
    ) -> SubmissionResponse:
        if self._store is None:
            raise RuntimeError("DURABLE_RECOVERY_UNAVAILABLE")
        attempts = self._store.list_attempts(logical_execution_id, principal.tenant_id)
        if not attempts:
            raise LookupError("RESOURCE_NOT_FOUND")
        context = authority_context(
            principal,
            request_id=request.request_identifier,
            correlation_id=request.correlation_identifier,
        )
        recovery = self._store.prepare_replay(
            attempts[-1].execution_id,
            ReplayAuthorization(
                principal.principal_id,
                principal.tenant_id,
                principal.roles,
                principal.scopes,
                context.authorization_reference,
                request.reason,
                request.correlation_identifier,
                datetime.now(UTC),
            ),
            context,
        )
        return self._resume(recovery)

    def _resume(self, recovery: ValidatedRecoveryInvocation) -> SubmissionResponse:
        existing = self._runtime.get_execution(recovery.execution_identifier)
        if existing is None:
            raise RuntimeError("RECOVERY_ADMISSION_FAILED")
        if existing.state is ExecutionState.ACCEPTED:
            response = self._runtime.resume(recovery)
            if response.execution_identifier is None:
                raise RuntimeError("RECOVERY_ADMISSION_FAILED")
        return SubmissionResponse(
            execution_identifier=recovery.execution_identifier,
            logical_execution_identifier=recovery.logical_execution_identifier,
            correlation_identifier=recovery.correlation_identifier,
            state=existing.state.value,
        )


def _envelope_bytes(payload: dict[str, object]) -> bytes:
    raw = {
        "request": payload,
        "references": {
            name: None
            for name in (
                "entity_resolution",
                "semantic_resolution",
                "assertion",
                "knowledge_evaluation",
                "decision_evaluation",
                "governance_evaluation",
            )
        },
        "enterprise_entity_id": None,
        "institutional_concept_id": None,
        "sourcing_status": None,
        "recommendation": None,
        "governance_standing": None,
        "conditions_verified": False,
        "gate_outcome": "CONTINUE",
        "diagnostic_code": None,
        "policy_traceability": None,
        "capability_timestamps": [],
    }
    return json.dumps(raw, separators=(",", ":")).encode()
