"""Gate S -- Governed Human Approval application service (CDD-036 §5, §7,
§12-§13, §16-§22). `GateSApprovalService.execute()` is the sole code path
in the entire codebase that constructs a `GateSGovernedNoteORM` row
(CDD-036 §22) -- it is entirely independent of `GovernedToolExecutor`/
`GOVERNED_TOOL_REGISTRY` (Gate R): no import, no call, no shared code
(CDD-036 §21, §29). Scope authorization (`governed-approval:request`/
`governed-approval:decide`) is enforced by the router, exactly mirroring
`app.api.ontology_modeling.router`'s `_authorize` pattern -- this module
enforces only the business invariants (tenant match, self-approval,
status/digest/consumption checks) that no scope check could express."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.domain.gate_s.approval import (
    ACTION_ID,
    ApprovalStatus,
    GateSApprovalRequest,
    compute_action_digest,
)
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditEvent
from app.infrastructure.persistence.gate_s_approval_repository import GateSApprovalRepository

_ENDPOINT_CLASSIFICATION = "GOVERNED_HUMAN_APPROVAL_API_V1"


class GateSApprovalError(Exception):
    """Carries one of CDD-036 §23's nine closed diagnostic codes. The
    router maps each to a stable HTTP status; no raw internal exception
    ever escapes past this boundary."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AuditRepository(Protocol):
    """Structural type satisfied by the existing, unmodified
    `ApiSecurityAuditRepository` -- kept narrow, and deliberately not
    imported from `governed_tool_executor.py` (CDD-036 §21, §29: Gate S
    shares no code with Gate R)."""

    def append(self, event: ApiSecurityAuditEvent) -> UUID: ...


class GateSApprovalService:
    def __init__(
        self, *, repository: GateSApprovalRepository, audit_repository: AuditRepository
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository

    def request(
        self,
        *,
        principal: TrustedPrincipal,
        note_text: str,
        now: datetime | None = None,
    ) -> GateSApprovalRequest:
        moment = now if now is not None else datetime.now(UTC)
        digest = compute_action_digest(action_id=ACTION_ID, note_text=note_text)
        request = GateSApprovalRequest(
            approval_id=uuid4(),
            tenant_id=principal.tenant_id,
            action_id=ACTION_ID,
            note_text=note_text,
            action_input_digest=digest,
            requested_by=principal.principal_id,
            requested_on=moment,
            status=ApprovalStatus.PENDING,
        )
        self._repository.create(request)
        self._record(
            operation="GATE_S_REQUEST_APPROVAL",
            outcome="SUCCESS",
            diagnostic_code="REQUESTED",
            principal=principal,
            approval_id=request.approval_id,
            execution_id=None,
        )
        return request

    def approve(
        self,
        *,
        principal: TrustedPrincipal,
        approval_id: UUID,
        now: datetime | None = None,
    ) -> GateSApprovalRequest:
        return self._decide(
            principal=principal,
            approval_id=approval_id,
            new_status=ApprovalStatus.APPROVED,
            rejection_reason=None,
            now=now,
        )

    def reject(
        self,
        *,
        principal: TrustedPrincipal,
        approval_id: UUID,
        rejection_reason: str | None,
        now: datetime | None = None,
    ) -> GateSApprovalRequest:
        return self._decide(
            principal=principal,
            approval_id=approval_id,
            new_status=ApprovalStatus.REJECTED,
            rejection_reason=rejection_reason,
            now=now,
        )

    def _decide(
        self,
        *,
        principal: TrustedPrincipal,
        approval_id: UUID,
        new_status: ApprovalStatus,
        rejection_reason: str | None,
        now: datetime | None,
    ) -> GateSApprovalRequest:
        moment = now if now is not None else datetime.now(UTC)
        request = self._repository.get_for_update(approval_id)
        if request is None:
            self._record(
                operation="GATE_S_DECIDE_APPROVAL",
                outcome="DENIED",
                diagnostic_code="APPROVAL_REQUEST_NOT_FOUND",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_REQUEST_NOT_FOUND")
        if request.tenant_id != principal.tenant_id:
            self._record(
                operation="GATE_S_DECIDE_APPROVAL",
                outcome="DENIED",
                diagnostic_code="APPROVAL_TENANT_MISMATCH",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_TENANT_MISMATCH")
        if principal.principal_id == request.requested_by:
            self._record(
                operation="GATE_S_DECIDE_APPROVAL",
                outcome="DENIED",
                diagnostic_code="APPROVAL_SELF_APPROVAL_PROHIBITED",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_SELF_APPROVAL_PROHIBITED")
        if request.status is not ApprovalStatus.PENDING:
            self._record(
                operation="GATE_S_DECIDE_APPROVAL",
                outcome="DENIED",
                diagnostic_code="APPROVAL_NOT_PENDING",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_NOT_PENDING")

        decided = GateSApprovalRequest(
            approval_id=request.approval_id,
            tenant_id=request.tenant_id,
            action_id=request.action_id,
            note_text=request.note_text,
            action_input_digest=request.action_input_digest,
            requested_by=request.requested_by,
            requested_on=request.requested_on,
            status=new_status,
            decided_by=principal.principal_id,
            decided_on=moment,
            rejection_reason=rejection_reason,
            consumed_on=request.consumed_on,
            consumed_execution_id=request.consumed_execution_id,
        )
        self._repository.update_decision(decided)
        self._record(
            operation="GATE_S_DECIDE_APPROVAL",
            outcome="SUCCESS",
            diagnostic_code=new_status.value.upper(),
            principal=principal,
            approval_id=approval_id,
            execution_id=None,
        )
        return decided

    def execute(
        self,
        *,
        principal: TrustedPrincipal,
        approval_id: UUID,
        note_text: str,
        now: datetime | None = None,
    ) -> UUID:
        """Returns the `governed_note_id` of the durably-written note.
        CDD-036 §17-§18, §20-§22: tenant/status/digest/consumption are all
        re-checked under a row lock, in the same transaction as the write,
        immediately before any provenance is recorded."""
        moment = now if now is not None else datetime.now(UTC)
        request = self._repository.get_for_update(approval_id)
        if request is None:
            self._record(
                operation="GATE_S_EXECUTE_APPROVED_ACTION",
                outcome="DENIED",
                diagnostic_code="APPROVAL_REQUEST_NOT_FOUND",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_REQUEST_NOT_FOUND")
        if request.tenant_id != principal.tenant_id:
            self._record(
                operation="GATE_S_EXECUTE_APPROVED_ACTION",
                outcome="DENIED",
                diagnostic_code="APPROVAL_TENANT_MISMATCH",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_TENANT_MISMATCH")
        if request.status is ApprovalStatus.REJECTED:
            self._record(
                operation="GATE_S_EXECUTE_APPROVED_ACTION",
                outcome="DENIED",
                diagnostic_code="APPROVAL_REJECTED",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_REJECTED")
        if request.status is not ApprovalStatus.APPROVED:
            self._record(
                operation="GATE_S_EXECUTE_APPROVED_ACTION",
                outcome="DENIED",
                diagnostic_code="APPROVAL_NOT_PENDING",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_NOT_PENDING")
        if request.consumed_on is not None:
            self._record(
                operation="GATE_S_EXECUTE_APPROVED_ACTION",
                outcome="DENIED",
                diagnostic_code="APPROVAL_ALREADY_CONSUMED",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_ALREADY_CONSUMED")
        recomputed_digest = compute_action_digest(action_id=request.action_id, note_text=note_text)
        if recomputed_digest != request.action_input_digest:
            self._record(
                operation="GATE_S_EXECUTE_APPROVED_ACTION",
                outcome="DENIED",
                diagnostic_code="APPROVAL_ACTION_MISMATCH",
                principal=principal,
                approval_id=approval_id,
                execution_id=None,
            )
            raise GateSApprovalError("APPROVAL_ACTION_MISMATCH")

        governed_note_id = uuid4()
        execution_id = uuid4()
        self._repository.insert_governed_note_and_consume(
            request=request,
            governed_note_id=governed_note_id,
            execution_id=execution_id,
            created_by=principal.principal_id,
            now=moment,
        )

        # Fail-closed on audit failure (mirrors CDD-035 Sec21): if this
        # raises, it propagates out of execute() -- the caller never
        # receives a success result for an execution whose provenance was
        # not durably recorded.
        self._record(
            operation="GATE_S_EXECUTE_APPROVED_ACTION",
            outcome="SUCCESS",
            diagnostic_code="EXECUTED",
            principal=principal,
            approval_id=approval_id,
            execution_id=execution_id,
        )
        return governed_note_id

    def _record(
        self,
        *,
        operation: str,
        outcome: str,
        diagnostic_code: str,
        principal: TrustedPrincipal,
        approval_id: UUID,
        execution_id: UUID | None,
    ) -> None:
        """CDD-036 §24-§26 -- the exact, frozen audit-field mapping. Raw
        `note_text` never appears here."""
        self._audit_repository.append(
            ApiSecurityAuditEvent(
                operation=operation,
                endpoint_classification=_ENDPOINT_CLASSIFICATION,
                event_category="HUMAN_APPROVAL",
                outcome=outcome,
                diagnostic_code=diagnostic_code,
                correlation_id=uuid4(),
                tenant_id=principal.tenant_id,
                principal_reference=principal.principal_id,
                execution_id=execution_id,
                attempt_id=None,
                authorization_decision_reference=(
                    "governed-approval:decide"
                    if operation == "GATE_S_DECIDE_APPROVAL"
                    else "governed-approval:request"
                ),
                evidence_resource_reference=str(approval_id),
                source_channel="HTTP_API",
            )
        )
