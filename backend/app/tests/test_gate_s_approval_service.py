"""Focused Gate S (CDD-036) test suite for `GateSApprovalService`, using a
fake in-memory repository (no live database required -- concurrency itself
is proven separately in `test_gate_s_approval_postgres.py`, which requires
real row-level locking)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.gate_s_approval_service import GateSApprovalError, GateSApprovalService
from app.domain.gate_s.approval import ACTION_ID, ApprovalStatus, GateSApprovalRequest
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditEvent

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, GateSApprovalRequest] = {}
        self.notes: list[dict[str, object]] = []

    def create(self, request: GateSApprovalRequest) -> None:
        self._store[request.approval_id] = request

    def get_by_id(self, approval_id: UUID) -> GateSApprovalRequest | None:
        return self._store.get(approval_id)

    def get_for_update(self, approval_id: UUID) -> GateSApprovalRequest | None:
        return self._store.get(approval_id)

    def update_decision(self, request: GateSApprovalRequest) -> None:
        self._store[request.approval_id] = request

    def insert_governed_note_and_consume(
        self,
        *,
        request: GateSApprovalRequest,
        governed_note_id: UUID,
        execution_id: UUID,
        created_by: str,
        now: datetime,
    ) -> None:
        self.notes.append(
            {
                "governed_note_id": governed_note_id,
                "tenant_id": request.tenant_id,
                "approval_id": request.approval_id,
                "note_text": request.note_text,
                "created_by": created_by,
                "created_at": now,
            }
        )
        current = self._store[request.approval_id]
        self._store[request.approval_id] = GateSApprovalRequest(
            approval_id=current.approval_id,
            tenant_id=current.tenant_id,
            action_id=current.action_id,
            note_text=current.note_text,
            action_input_digest=current.action_input_digest,
            requested_by=current.requested_by,
            requested_on=current.requested_on,
            status=current.status,
            decided_by=current.decided_by,
            decided_on=current.decided_on,
            rejection_reason=current.rejection_reason,
            consumed_on=now,
            consumed_execution_id=execution_id,
        )


class FakeAuditRepository:
    def __init__(self) -> None:
        self.events: list[ApiSecurityAuditEvent] = []

    def append(self, event: ApiSecurityAuditEvent) -> UUID:
        self.events.append(event)
        return uuid4()


def make_principal(
    *, principal_id: str, scopes: tuple[str, ...], tenant_id: str = "tenant-a"
) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id=principal_id,
        tenant_id=tenant_id,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def make_service() -> tuple[GateSApprovalService, FakeRepository, FakeAuditRepository]:
    repository = FakeRepository()
    audit = FakeAuditRepository()
    return GateSApprovalService(repository=repository, audit_repository=audit), repository, audit


REQUESTER = make_principal(principal_id="alice", scopes=())
APPROVER = make_principal(principal_id="bob", scopes=())


def test_request_creates_pending_with_correct_tenant_and_digest() -> None:
    service, repository, audit = make_service()
    principal = make_principal(
        principal_id="alice", scopes=("governed-approval:request",), tenant_id="tenant-a"
    )

    request = service.request(principal=principal, note_text="hello")

    assert request.status == ApprovalStatus.PENDING
    assert request.tenant_id == "tenant-a"
    assert request.requested_by == "alice"
    assert request.action_id == ACTION_ID
    assert repository.get_by_id(request.approval_id) is not None
    assert len(audit.events) == 1
    assert audit.events[0].diagnostic_code == "REQUESTED"


def test_self_approval_is_prohibited() -> None:
    service, _repository, _audit = make_service()
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))
    request = service.request(principal=requester, note_text="hello")
    self_approver = make_principal(principal_id="alice", scopes=("governed-approval:decide",))

    with pytest.raises(GateSApprovalError) as exc:
        service.approve(principal=self_approver, approval_id=request.approval_id)
    assert exc.value.code == "APPROVAL_SELF_APPROVAL_PROHIBITED"


def test_cross_tenant_decision_fails_with_tenant_mismatch() -> None:
    service, _repository, _audit = make_service()
    requester = make_principal(
        principal_id="alice", scopes=("governed-approval:request",), tenant_id="tenant-a"
    )
    request = service.request(principal=requester, note_text="hello")
    other_tenant_approver = make_principal(
        principal_id="bob", scopes=("governed-approval:decide",), tenant_id="tenant-b"
    )

    with pytest.raises(GateSApprovalError) as exc:
        service.approve(principal=other_tenant_approver, approval_id=request.approval_id)
    assert exc.value.code == "APPROVAL_TENANT_MISMATCH"


def test_approve_transitions_pending_to_approved_exactly_once() -> None:
    service, _repository, audit = make_service()
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))
    approver = make_principal(principal_id="bob", scopes=("governed-approval:decide",))
    request = service.request(principal=requester, note_text="hello")

    approved = service.approve(principal=approver, approval_id=request.approval_id)
    assert approved.status == ApprovalStatus.APPROVED
    assert approved.decided_by == "bob"

    with pytest.raises(GateSApprovalError) as exc:
        service.approve(principal=approver, approval_id=request.approval_id)
    assert exc.value.code == "APPROVAL_NOT_PENDING"
    assert any(event.diagnostic_code == "APPROVED" for event in audit.events)


def test_reject_transitions_pending_to_rejected_with_reason() -> None:
    service, _repository, _audit = make_service()
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))
    approver = make_principal(principal_id="bob", scopes=("governed-approval:decide",))
    request = service.request(principal=requester, note_text="hello")

    rejected = service.reject(
        principal=approver, approval_id=request.approval_id, rejection_reason="not needed"
    )
    assert rejected.status == ApprovalStatus.REJECTED
    assert rejected.rejection_reason == "not needed"


def test_execute_on_pending_request_fails_closed() -> None:
    service, repository, _audit = make_service()
    requester = make_principal(
        principal_id="alice", scopes=("governed-approval:request",), tenant_id="tenant-a"
    )
    request = service.request(principal=requester, note_text="hello")

    with pytest.raises(GateSApprovalError) as exc:
        service.execute(principal=requester, approval_id=request.approval_id, note_text="hello")
    assert exc.value.code == "APPROVAL_NOT_PENDING"
    assert repository.notes == []


def test_execute_on_rejected_request_fails_closed() -> None:
    service, repository, _audit = make_service()
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))
    approver = make_principal(principal_id="bob", scopes=("governed-approval:decide",))
    request = service.request(principal=requester, note_text="hello")
    service.reject(principal=approver, approval_id=request.approval_id, rejection_reason=None)

    with pytest.raises(GateSApprovalError) as exc:
        service.execute(principal=requester, approval_id=request.approval_id, note_text="hello")
    assert exc.value.code == "APPROVAL_REJECTED"
    assert repository.notes == []


def test_execute_on_approved_matching_action_writes_note_and_consumes() -> None:
    service, repository, audit = make_service()
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))
    approver = make_principal(principal_id="bob", scopes=("governed-approval:decide",))
    request = service.request(principal=requester, note_text="hello")
    service.approve(principal=approver, approval_id=request.approval_id)

    governed_note_id = service.execute(
        principal=requester, approval_id=request.approval_id, note_text="hello"
    )

    assert governed_note_id is not None
    assert len(repository.notes) == 1
    assert repository.notes[0]["note_text"] == "hello"
    consumed = repository.get_by_id(request.approval_id)
    assert consumed is not None
    assert consumed.consumed_on is not None
    assert any(event.diagnostic_code == "EXECUTED" for event in audit.events)


def test_execute_with_mutated_note_text_fails_action_mismatch() -> None:
    service, repository, _audit = make_service()
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))
    approver = make_principal(principal_id="bob", scopes=("governed-approval:decide",))
    request = service.request(principal=requester, note_text="hello")
    service.approve(principal=approver, approval_id=request.approval_id)

    with pytest.raises(GateSApprovalError) as exc:
        service.execute(principal=requester, approval_id=request.approval_id, note_text="mutated")
    assert exc.value.code == "APPROVAL_ACTION_MISMATCH"
    assert repository.notes == []


def test_second_execute_on_consumed_approval_fails_closed() -> None:
    service, repository, _audit = make_service()
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))
    approver = make_principal(principal_id="bob", scopes=("governed-approval:decide",))
    request = service.request(principal=requester, note_text="hello")
    service.approve(principal=approver, approval_id=request.approval_id)
    service.execute(principal=requester, approval_id=request.approval_id, note_text="hello")

    with pytest.raises(GateSApprovalError) as exc:
        service.execute(principal=requester, approval_id=request.approval_id, note_text="hello")
    assert exc.value.code == "APPROVAL_ALREADY_CONSUMED"
    assert len(repository.notes) == 1


def test_audit_records_requester_approver_decision_execution_and_correlation() -> None:
    service, _repository, audit = make_service()
    requester = make_principal(
        principal_id="alice", scopes=("governed-approval:request",), tenant_id="tenant-a"
    )
    approver = make_principal(
        principal_id="bob", scopes=("governed-approval:decide",), tenant_id="tenant-a"
    )
    request = service.request(principal=requester, note_text="hello")
    service.approve(principal=approver, approval_id=request.approval_id)
    governed_note_id = service.execute(
        principal=requester, approval_id=request.approval_id, note_text="hello"
    )

    request_event = next(e for e in audit.events if e.diagnostic_code == "REQUESTED")
    assert request_event.principal_reference == "alice"
    assert request_event.tenant_id == "tenant-a"

    decide_event = next(e for e in audit.events if e.diagnostic_code == "APPROVED")
    assert decide_event.principal_reference == "bob"

    execute_event = next(e for e in audit.events if e.diagnostic_code == "EXECUTED")
    assert execute_event.execution_id is not None
    assert execute_event.correlation_id is not None
    assert governed_note_id is not None


def test_raw_note_text_never_enters_audit() -> None:
    service, _repository, audit = make_service()
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))
    approver = make_principal(principal_id="bob", scopes=("governed-approval:decide",))
    secret = "unique-marker-payload-should-never-be-audited"
    request = service.request(principal=requester, note_text=secret)
    service.approve(principal=approver, approval_id=request.approval_id)
    service.execute(principal=requester, approval_id=request.approval_id, note_text=secret)

    for event in audit.events:
        for value in (
            event.operation,
            event.diagnostic_code,
            event.evidence_resource_reference,
            event.authorization_decision_reference,
        ):
            assert secret not in str(value)


def test_provenance_recording_failure_prevents_success_result() -> None:
    class RaisingAuditRepository:
        def append(self, event: ApiSecurityAuditEvent) -> UUID:
            raise RuntimeError("durable provenance write failed")

    repository = FakeRepository()
    service = GateSApprovalService(repository=repository, audit_repository=RaisingAuditRepository())
    requester = make_principal(principal_id="alice", scopes=("governed-approval:request",))

    with pytest.raises(RuntimeError):
        service.request(principal=requester, note_text="hello")
