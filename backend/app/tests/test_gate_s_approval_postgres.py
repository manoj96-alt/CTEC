"""Postgres-backed acceptance evidence for Gate S (CDD-036 §19-§20, §35-§36;
Gate S Artifact Authorization §17). Proves two things a fake repository
cannot: (1) migration `0018_gate_s_approval` produces exactly the expected
schema, and (2) the `SELECT ... FOR UPDATE` row lock genuinely serializes
two concurrent decisions/executions against the same approval row -- the
concrete guarantee CDD-036 §20 claims."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.gate_s_approval_service import GateSApprovalError, GateSApprovalService
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditEvent
from app.infrastructure.persistence.gate_s_approval_repository import GateSApprovalRepositoryImpl
from app.infrastructure.persistence.models.gate_s_approval import GateSGovernedNoteORM

NOW = datetime.now(UTC)


class _NullAuditRepository:
    """Discards audit writes -- these tests prove row-lock concurrency, not
    provenance content (already proven in `test_gate_s_approval_service.py`)."""

    def append(self, event: ApiSecurityAuditEvent) -> UUID:
        return uuid4()


def _principal(*, principal_id: str, scopes: tuple[str, ...]) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id=principal_id,
        tenant_id="tenant-a",
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def test_migration_creates_expected_schema(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    tables = set(inspector.get_table_names())
    assert "gate_s_approval_requests" in tables
    assert "gate_s_governed_notes" in tables

    approval_columns = {c["name"] for c in inspector.get_columns("gate_s_approval_requests")}
    assert approval_columns == {
        "approval_id",
        "tenant_id",
        "action_id",
        "note_text",
        "action_input_digest",
        "requested_by",
        "requested_on",
        "status",
        "decided_by",
        "decided_on",
        "rejection_reason",
        "consumed_on",
        "consumed_execution_id",
    }

    note_columns = {c["name"] for c in inspector.get_columns("gate_s_governed_notes")}
    assert note_columns == {
        "governed_note_id",
        "tenant_id",
        "approval_id",
        "note_text",
        "created_by",
        "created_at",
    }


def test_concurrent_decide_race_has_exactly_one_winner(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    requester = _principal(principal_id="alice", scopes=("governed-approval:request",))
    approver_1 = _principal(principal_id="bob", scopes=("governed-approval:decide",))
    approver_2 = _principal(principal_id="carol", scopes=("governed-approval:decide",))

    with factory() as setup_session:
        setup_service = GateSApprovalService(
            repository=GateSApprovalRepositoryImpl(setup_session),
            audit_repository=_NullAuditRepository(),
        )
        request = setup_service.request(principal=requester, note_text="race-decide")
        setup_session.commit()

    # Thread A acquires the row lock (via approve()) and signals `lock_held`
    # before sleeping-then-committing. Thread B waits for that signal before
    # attempting its own approve() -- at which point its SELECT ... FOR
    # UPDATE genuinely blocks at the database level until A commits. Using a
    # single barrier for both "lock acquired" and "safe to commit" would
    # deadlock: B cannot reach a shared barrier while stuck inside a blocked
    # SQL call, and A would then wait forever for B to arrive.
    lock_held = threading.Event()
    outcomes: dict[str, str] = {}

    def _decide_first(session: Session, principal: TrustedPrincipal, label: str) -> None:
        service = GateSApprovalService(
            repository=GateSApprovalRepositoryImpl(session),
            audit_repository=_NullAuditRepository(),
        )
        service.approve(principal=principal, approval_id=request.approval_id)
        lock_held.set()
        time.sleep(0.3)
        session.commit()
        outcomes[label] = "APPROVED"

    def _decide_second(session: Session, principal: TrustedPrincipal, label: str) -> None:
        assert lock_held.wait(timeout=5)
        service = GateSApprovalService(
            repository=GateSApprovalRepositoryImpl(session),
            audit_repository=_NullAuditRepository(),
        )
        try:
            service.approve(principal=principal, approval_id=request.approval_id)
            session.commit()
            outcomes[label] = "APPROVED"
        except GateSApprovalError as exc:
            session.rollback()
            outcomes[label] = exc.code

    session_a = factory()
    session_b = factory()
    thread_a = threading.Thread(target=_decide_first, args=(session_a, approver_1, "a"))
    thread_b = threading.Thread(target=_decide_second, args=(session_b, approver_2, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    values = sorted(outcomes.values())
    assert values == ["APPROVAL_NOT_PENDING", "APPROVED"]


def test_concurrent_execute_race_writes_exactly_one_note(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    requester = _principal(principal_id="dave", scopes=("governed-approval:request",))
    approver = _principal(principal_id="erin", scopes=("governed-approval:decide",))

    with factory() as setup_session:
        setup_service = GateSApprovalService(
            repository=GateSApprovalRepositoryImpl(setup_session),
            audit_repository=_NullAuditRepository(),
        )
        request = setup_service.request(principal=requester, note_text="race-execute")
        setup_session.commit()
    with factory() as approve_session:
        approve_service = GateSApprovalService(
            repository=GateSApprovalRepositoryImpl(approve_session),
            audit_repository=_NullAuditRepository(),
        )
        approve_service.approve(principal=approver, approval_id=request.approval_id)
        approve_session.commit()

    # See test_concurrent_decide_race_has_exactly_one_winner for why a
    # single shared barrier would deadlock here.
    lock_held = threading.Event()
    outcomes: dict[str, str] = {}

    def _execute_first(session: Session, label: str) -> None:
        service = GateSApprovalService(
            repository=GateSApprovalRepositoryImpl(session),
            audit_repository=_NullAuditRepository(),
        )
        service.execute(
            principal=requester, approval_id=request.approval_id, note_text="race-execute"
        )
        lock_held.set()
        time.sleep(0.3)
        session.commit()
        outcomes[label] = "EXECUTED"

    def _execute_second(session: Session, label: str) -> None:
        assert lock_held.wait(timeout=5)
        service = GateSApprovalService(
            repository=GateSApprovalRepositoryImpl(session),
            audit_repository=_NullAuditRepository(),
        )
        try:
            service.execute(
                principal=requester, approval_id=request.approval_id, note_text="race-execute"
            )
            session.commit()
            outcomes[label] = "EXECUTED"
        except GateSApprovalError as exc:
            session.rollback()
            outcomes[label] = exc.code

    session_a = factory()
    session_b = factory()
    thread_a = threading.Thread(target=_execute_first, args=(session_a, "a"))
    thread_b = threading.Thread(target=_execute_second, args=(session_b, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    values = sorted(outcomes.values())
    assert values == ["APPROVAL_ALREADY_CONSUMED", "EXECUTED"]

    with factory() as verify_session:
        notes = (
            verify_session.execute(
                select(GateSGovernedNoteORM).where(
                    GateSGovernedNoteORM.approval_id == request.approval_id
                )
            )
            .scalars()
            .all()
        )
        assert len(notes) == 1
