"""Application boundary over the existing runtime and durable execution store."""

import json
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.schemas import (
    AttemptListResponse,
    AttemptResponse,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionSummaryResponse,
    GovernedResultResponse,
    ReplayOptionResponse,
    ReplayOptionsResponse,
    ReplayRequest,
    RetryEligibilityResponse,
    RetryRequest,
    StageListResponse,
    StageResponse,
    SubmissionResponse,
    SupplierRiskSubmission,
)
from app.api.supplier_risk.security import authority_context
from app.integration.contracts import AuthorityContext
from app.runtime.contracts import InvocationRequest, InvocationStatus
from app.runtime.engine import CognitiveEngineRuntime
from app.runtime.execution_state import ExecutionState
from app.runtime.persistence.contracts import (
    AttemptProjection,
    ExecutionSummaryProjection,
    ReplayAuthorization,
    ReplayOptionProjection,
    ResultProjection,
    RetryAuthorization,
    StageProjection,
)
from app.runtime.recovery import ValidatedRecoveryInvocation


class ExecutionApiStore(Protocol):
    def list_executions(
        self, tenant_id: str, *, offset: int, limit: int, state: str | None = None
    ) -> tuple[ExecutionSummaryProjection, ...]: ...

    def list_attempts(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> tuple[AttemptProjection, ...]: ...

    def list_stages(
        self, logical_execution_id: UUID, execution_id: UUID, tenant_id: str
    ) -> tuple[StageProjection, ...]: ...

    def get_result_for_logical(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> ResultProjection | None: ...

    def replay_options(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> tuple[ReplayOptionProjection, ...]: ...

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
        supplier_risk = request.supplier_risk.model_dump(mode="json")
        client_payload = json.dumps(
            request.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()

        def admitted_payload(admitted_at: datetime) -> bytes:
            admitted_request = json.loads(json.dumps(supplier_risk))
            received_at = admitted_at.astimezone(UTC).isoformat()
            for observation in admitted_request["observations"]:
                observation["received_at"] = received_at
            return _envelope_bytes(admitted_request)

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
            opaque_payload=client_payload,
            authority_context=control,
            control_metadata_version="1.0",
            admitted_payload_builder=admitted_payload,
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
        terminal = snapshot.state in {ExecutionState.COMPLETED, ExecutionState.FAILED}
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
            terminal=terminal,
            terminal_classification=_classification(snapshot.state.value, snapshot.result_code),
            safe_diagnostic_code=(
                snapshot.result_code
                if snapshot.result_code
                and snapshot.result_code
                not in {"APPROVED", "CONDITIONALLY_APPROVED", "REJECTED", "INDETERMINATE"}
                else None
            ),
            retry_eligible=snapshot.state is ExecutionState.FAILED,
            replay_eligible=terminal,
        )

    def executions(
        self,
        principal: TrustedPrincipal,
        *,
        offset: int,
        limit: int,
        state: str | None,
    ) -> ExecutionListResponse:
        if self._store is None:
            raise RuntimeError("DURABLE_QUERY_UNAVAILABLE")
        values = self._store.list_executions(
            principal.tenant_id, offset=offset, limit=limit + 1, state=state
        )
        selected = values[:limit]
        return ExecutionListResponse(
            items=[
                ExecutionSummaryResponse(
                    logical_execution_identifier=value.logical_execution_id,
                    current_execution_identifier=value.current_execution_id,
                    subject_summary=value.subject_summary,
                    submitted_at=value.submitted_at,
                    execution_status=value.state,
                    current_or_terminal_stage=value.current_stage,
                    terminal_classification=value.terminal_classification,
                    retry_eligible=value.retry_eligible,
                    replay_eligible=value.replay_eligible,
                    last_updated_at=value.last_updated_at,
                    revision=value.revision,
                )
                for value in selected
            ],
            next_cursor=str(offset + limit) if len(values) > limit else None,
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
            terminal_classification=value.terminal_classification,
            safe_diagnostic_code=value.diagnostic_code,
            conditions=list(value.conditions),
            verified_conditions=list(value.verified_conditions),
            evidence_references=list(value.evidence_references),
            provenance_references=list(value.provenance_references),
            policy_reference=value.policy_reference,
            policy_version=value.policy_version,
            policy_rule=value.policy_rule,
            decision_reference=value.decision_reference,
        )

    def retry_eligibility(
        self, logical_execution_id: UUID, principal: TrustedPrincipal
    ) -> RetryEligibilityResponse | None:
        if self._store is None:
            raise RuntimeError("DURABLE_RECOVERY_UNAVAILABLE")
        attempts = self._store.list_attempts(logical_execution_id, principal.tenant_id)
        if not attempts:
            return None
        current = attempts[-1]
        eligible = current.state == ExecutionState.FAILED.value
        return RetryEligibilityResponse(
            eligible=eligible,
            governing_attempt_identifier=current.execution_id,
            reason_code="RETRY_ELIGIBLE" if eligible else "ATTEMPT_NOT_FAILED",
            safe_constraint=None if eligible else "Only a failed current attempt may be retried.",
            revision=current.revision,
            action=(
                f"/api/v1/supplier-risk/executions/{logical_execution_id}/retry"
                if eligible
                else None
            ),
        )

    def replay_options(
        self, logical_execution_id: UUID, principal: TrustedPrincipal
    ) -> ReplayOptionsResponse | None:
        if self._store is None:
            raise RuntimeError("DURABLE_RECOVERY_UNAVAILABLE")
        attempts = self._store.list_attempts(logical_execution_id, principal.tenant_id)
        if not attempts:
            return None
        return ReplayOptionsResponse(
            items=[
                ReplayOptionResponse(
                    option_reference=value.option_reference,
                    source_attempt_identifier=value.source_execution_id,
                    stage_label=value.stage_name,
                    checkpoint_at=value.checkpoint_at,
                    eligible=value.eligible,
                    reason_code=value.reason_code,
                    revision=value.revision,
                )
                for value in self._store.replay_options(logical_execution_id, principal.tenant_id)
            ]
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
        if request.expected_revision is not None and request.expected_revision != original.revision:
            raise ValueError("RETRY_ELIGIBILITY_STALE")
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
        original = attempts[-1]
        options = self._store.replay_options(logical_execution_id, principal.tenant_id)
        if not any(
            (
                request.replay_option_reference is None
                or option.option_reference == request.replay_option_reference
            )
            and option.source_execution_id == original.execution_id
            and (request.expected_revision is None or option.revision == request.expected_revision)
            and option.eligible
            for option in options
        ):
            raise ValueError("REPLAY_OPTION_STALE_OR_INVALID")
        context = authority_context(
            principal,
            request_id=request.request_identifier,
            correlation_id=request.correlation_identifier,
        )
        recovery = self._store.prepare_replay(
            original.execution_id,
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


def _classification(state: str, code: str | None) -> str | None:
    if state not in {ExecutionState.COMPLETED.value, ExecutionState.FAILED.value}:
        return "IN_PROGRESS"
    if state == ExecutionState.FAILED.value:
        return "TECHNICAL_FAILURE"
    if code in {"APPROVED", "CONDITIONALLY_APPROVED", "REJECTED", "INDETERMINATE"}:
        return code
    if code in {"EVIDENCE_INDETERMINATE", "IDENTITY_NOT_RESOLVED", "SEMANTICS_NOT_RESOLVED"}:
        return "INDETERMINATE"
    return "BUSINESS_GATED"
