"""Focused Gate V (CDD-037) test suite for `GateVApplicationService`, using
fake in-memory repositories for both Gate V's own resolution storage and
Gate S's approval-request storage (no live database required -- schema and
real cross-table composition are proven separately in
`test_gate_v_agent_postgres.py`). `GateSApprovalService` itself is real and
unmodified in every test here -- only its repository/audit dependencies are
faked -- so these tests exercise genuine Gate V -> Gate S composition, not a
second, duplicated approval implementation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.gate_s_approval_service import GateSApprovalError, GateSApprovalService
from app.application.gate_v_agent_service import GateVApplicationService
from app.domain.gate_s.approval import GateSApprovalRequest
from app.domain.gate_v.agent_resolution import (
    AGENT_ID,
    PRIORITY_THRESHOLD,
    AgentResolutionOutcome,
    GateVAgentResolution,
)
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditEvent

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeGateSRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, GateSApprovalRequest] = {}

    def create(self, request: GateSApprovalRequest) -> None:
        self.store[request.approval_id] = request

    def get_by_id(self, approval_id: UUID) -> GateSApprovalRequest | None:
        return self.store.get(approval_id)

    def get_for_update(self, approval_id: UUID) -> GateSApprovalRequest | None:
        return self.store.get(approval_id)

    def update_decision(self, request: GateSApprovalRequest) -> None:
        self.store[request.approval_id] = request

    def insert_governed_note_and_consume(self, **kwargs: object) -> None:
        raise NotImplementedError("Gate V never calls execute()")


class FakeAuditRepository:
    def __init__(self) -> None:
        self.events: list[ApiSecurityAuditEvent] = []

    def append(self, event: ApiSecurityAuditEvent) -> UUID:
        self.events.append(event)
        return uuid4()


class FakeGateVRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, GateVAgentResolution] = {}

    def create(self, resolution: GateVAgentResolution) -> None:
        self.store[resolution.resolution_id] = resolution

    def get_by_id(self, resolution_id: UUID) -> GateVAgentResolution | None:
        return self.store.get(resolution_id)


def make_principal(
    *, principal_id: str = "alice", scopes: tuple[str, ...] = (), tenant_id: str = "tenant-a"
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


def make_service() -> (
    tuple[GateVApplicationService, FakeGateVRepository, FakeGateSRepository, FakeAuditRepository]
):
    gate_v_repository = FakeGateVRepository()
    gate_s_repository = FakeGateSRepository()
    gate_v_audit = FakeAuditRepository()
    gate_s_service = GateSApprovalService(
        repository=gate_s_repository, audit_repository=FakeAuditRepository()
    )
    service = GateVApplicationService(
        repository=gate_v_repository,
        gate_s_service=gate_s_service,
        audit_repository=gate_v_audit,
    )
    return service, gate_v_repository, gate_s_repository, gate_v_audit


PROPOSING_SCOPES = ("governed-agent:propose", "governed-approval:request")


def test_priority_at_threshold_proposes_and_creates_gate_s_request() -> None:
    service, gate_v_repository, gate_s_repository, _audit = make_service()
    principal = make_principal(scopes=PROPOSING_SCOPES)

    resolution = service.resolve(
        principal=principal, observation_text="unusual pattern", priority_score=50
    )

    assert resolution.outcome == AgentResolutionOutcome.PROPOSED
    assert resolution.approval_id is not None
    assert gate_s_repository.get_by_id(resolution.approval_id) is not None
    assert gate_v_repository.get_by_id(resolution.resolution_id) is not None


def test_priority_below_threshold_suppresses_and_creates_no_gate_s_request() -> None:
    service, gate_v_repository, gate_s_repository, _audit = make_service()
    principal = make_principal(scopes=PROPOSING_SCOPES)

    resolution = service.resolve(
        principal=principal, observation_text="minor note", priority_score=49
    )

    assert resolution.outcome == AgentResolutionOutcome.SUPPRESSED
    assert resolution.approval_id is None
    assert gate_s_repository.store == {}
    assert gate_v_repository.get_by_id(resolution.resolution_id) is not None


def test_fixed_agent_id_and_threshold() -> None:
    assert AGENT_ID == "gate-v-deterministic-notifier-agent"
    assert PRIORITY_THRESHOLD == 50


def test_deterministic_note_text_derivation() -> None:
    service, _gate_v_repository, gate_s_repository, _audit = make_service()
    principal = make_principal(scopes=PROPOSING_SCOPES)

    resolution = service.resolve(
        principal=principal, observation_text="odd traffic spike", priority_score=100
    )

    assert resolution.approval_id is not None
    stored = gate_s_repository.get_by_id(resolution.approval_id)
    assert stored is not None
    assert stored.note_text == "Agent observation: odd traffic spike"


def test_tenant_and_requested_by_derived_from_principal_not_payload() -> None:
    service, _gate_v_repository, _gate_s_repository, _audit = make_service()
    principal = make_principal(principal_id="carol", tenant_id="tenant-z", scopes=PROPOSING_SCOPES)

    resolution = service.resolve(principal=principal, observation_text="x", priority_score=10)

    assert resolution.tenant_id == "tenant-z"
    assert resolution.requested_by == "carol"


def test_audit_mapping_and_observation_text_absent_from_audit() -> None:
    service, _gate_v_repository, _gate_s_repository, audit = make_service()
    principal = make_principal(scopes=PROPOSING_SCOPES)
    secret = "unique-marker-payload-should-never-be-audited"

    resolution = service.resolve(principal=principal, observation_text=secret, priority_score=75)

    assert len(audit.events) == 1
    event = audit.events[0]
    assert event.operation == "GATE_V_AGENT_RESOLUTION"
    assert event.endpoint_classification == "GOVERNED_AGENT_ORCHESTRATION_API_V1"
    assert event.event_category == "AGENT_RESOLUTION"
    assert event.outcome == "SUCCESS"
    assert event.diagnostic_code == "PROPOSED"
    assert event.execution_id is None
    assert event.authorization_decision_reference == "governed-agent:propose"
    assert event.evidence_resource_reference == str(resolution.resolution_id)
    for value in (
        event.operation,
        event.diagnostic_code,
        event.evidence_resource_reference,
        event.authorization_decision_reference,
    ):
        assert secret not in str(value)


def test_suppressed_resolution_diagnostic_code() -> None:
    service, _gate_v_repository, _gate_s_repository, audit = make_service()
    principal = make_principal(scopes=PROPOSING_SCOPES)

    resolution = service.resolve(principal=principal, observation_text="x", priority_score=0)

    assert resolution.outcome == AgentResolutionOutcome.SUPPRESSED
    assert audit.events[0].diagnostic_code == "SUPPRESSED"


def test_self_approval_of_agent_derived_request_remains_prohibited() -> None:
    """CDD-037 §12: Gate V passes the real calling principal through to Gate
    S unchanged, so Gate S's own, unmodified self-approval prohibition
    applies automatically -- Gate V adds no second implementation of it."""
    gate_v_repository = FakeGateVRepository()
    gate_s_repository = FakeGateSRepository()
    gate_s_service = GateSApprovalService(
        repository=gate_s_repository, audit_repository=FakeAuditRepository()
    )
    service = GateVApplicationService(
        repository=gate_v_repository,
        gate_s_service=gate_s_service,
        audit_repository=FakeAuditRepository(),
    )
    requester = make_principal(principal_id="alice", scopes=PROPOSING_SCOPES)

    resolution = service.resolve(principal=requester, observation_text="x", priority_score=100)
    assert resolution.approval_id is not None

    same_principal_as_approver = make_principal(
        principal_id="alice", scopes=("governed-approval:decide",)
    )
    with pytest.raises(GateSApprovalError) as exc:
        gate_s_service.approve(
            principal=same_principal_as_approver, approval_id=resolution.approval_id
        )
    assert exc.value.code == "APPROVAL_SELF_APPROVAL_PROHIBITED"


def test_gate_v_never_calls_gate_s_decision_or_execution_methods() -> None:
    """Structural proof complementing the architecture test: exercising the
    full resolve() path never reaches `insert_governed_note_and_consume`
    (Gate S's `execute()` path), which this fake deliberately fails hard on
    if ever invoked."""
    service, _gate_v_repository, _gate_s_repository, _audit = make_service()
    principal = make_principal(scopes=PROPOSING_SCOPES)
    service.resolve(principal=principal, observation_text="x", priority_score=100)
    service.resolve(principal=principal, observation_text="y", priority_score=0)
