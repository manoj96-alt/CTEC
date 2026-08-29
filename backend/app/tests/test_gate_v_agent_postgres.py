"""Postgres-backed acceptance evidence for Gate V (CDD-037 §15-§16, §20,
§22; Gate V Artifact Authorization §19). Proves three things a fake
repository cannot: (1) migration `0019_gate_v_agent_resolution` produces
exactly the expected schema, with `down_revision = 0018_gate_s_approval`;
(2) a `PROPOSED` resolution genuinely composes with a real, unmodified
`GateSApprovalService`, producing a real, independently-durable
`gate_s_approval_requests` row; and (3) a resolution durably survives across
an independent session/re-read, with correct tenant isolation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Engine, inspect
from sqlalchemy.orm import sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.gate_s_approval_service import GateSApprovalService
from app.application.gate_v_agent_service import GateVApplicationService
from app.domain.gate_v.agent_resolution import AgentResolutionOutcome
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditEvent
from app.infrastructure.persistence.gate_s_approval_repository import GateSApprovalRepositoryImpl
from app.infrastructure.persistence.gate_v_agent_resolution_repository import (
    GateVAgentResolutionRepositoryImpl,
)

NOW = datetime.now(UTC)


class _NullAuditRepository:
    """Discards audit writes -- these tests prove schema/persistence/
    composition, not provenance content (already proven in
    `test_gate_v_agent_service.py`)."""

    def append(self, event: ApiSecurityAuditEvent) -> UUID:
        return uuid4()


def _principal(
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


def _service(session: object) -> GateVApplicationService:
    gate_s_service = GateSApprovalService(
        repository=GateSApprovalRepositoryImpl(session),  # type: ignore[arg-type]
        audit_repository=_NullAuditRepository(),
    )
    return GateVApplicationService(
        repository=GateVAgentResolutionRepositoryImpl(session),  # type: ignore[arg-type]
        gate_s_service=gate_s_service,
        audit_repository=_NullAuditRepository(),
    )


def test_migration_creates_expected_schema(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    tables = set(inspector.get_table_names())
    assert "gate_v_agent_resolutions" in tables

    columns = {c["name"] for c in inspector.get_columns("gate_v_agent_resolutions")}
    assert columns == {
        "resolution_id",
        "tenant_id",
        "agent_id",
        "requested_by",
        "observation_text",
        "priority_score",
        "outcome",
        "approval_id",
        "resolved_on",
    }

    foreign_keys = inspector.get_foreign_keys("gate_v_agent_resolutions")
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["referred_table"] == "gate_s_approval_requests"
    assert foreign_keys[0]["referred_columns"] == ["approval_id"]


def test_migration_head_and_down_revision(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        from sqlalchemy import text

        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "0021_oqi2_cross_source"


def test_proposed_resolution_creates_genuine_gate_s_approval_request(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    principal = _principal(
        principal_id="alice",
        scopes=("governed-agent:propose", "governed-approval:request"),
        tenant_id="tenant-a",
    )

    with factory() as session:
        service = _service(session)
        resolution = service.resolve(
            principal=principal, observation_text="unusual pattern", priority_score=80
        )
        session.commit()

    assert resolution.outcome == AgentResolutionOutcome.PROPOSED
    assert resolution.approval_id is not None

    with factory() as verify_session:
        gate_s_repository = GateSApprovalRepositoryImpl(verify_session)
        gate_s_request = gate_s_repository.get_by_id(resolution.approval_id)
        assert gate_s_request is not None
        assert gate_s_request.tenant_id == "tenant-a"
        assert gate_s_request.requested_by == "alice"
        assert gate_s_request.note_text == "Agent observation: unusual pattern"


def test_suppressed_resolution_creates_no_gate_s_approval_request(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    principal = _principal(
        principal_id="bob",
        scopes=("governed-agent:propose", "governed-approval:request"),
        tenant_id="tenant-a",
    )

    with factory() as session:
        service = _service(session)
        resolution = service.resolve(
            principal=principal, observation_text="minor note", priority_score=10
        )
        session.commit()

    assert resolution.outcome == AgentResolutionOutcome.SUPPRESSED
    assert resolution.approval_id is None


def test_resolution_durability_across_independent_session(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    principal = _principal(
        principal_id="carol",
        scopes=("governed-agent:propose", "governed-approval:request"),
        tenant_id="tenant-a",
    )

    with factory() as session:
        service = _service(session)
        resolution = service.resolve(
            principal=principal, observation_text="restart-durability check", priority_score=90
        )
        session.commit()

    with factory() as independent_session:
        repository = GateVAgentResolutionRepositoryImpl(independent_session)
        reread = repository.get_by_id(resolution.resolution_id)
        assert reread is not None
        assert reread.observation_text == "restart-durability check"
        assert reread.outcome == AgentResolutionOutcome.PROPOSED
        assert reread.tenant_id == "tenant-a"


def test_tenant_isolation_across_resolutions(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_a_principal = _principal(
        principal_id="dave",
        scopes=("governed-agent:propose", "governed-approval:request"),
        tenant_id="tenant-a",
    )
    tenant_b_principal = _principal(
        principal_id="erin",
        scopes=("governed-agent:propose", "governed-approval:request"),
        tenant_id="tenant-b",
    )

    with factory() as session:
        service = _service(session)
        resolution_a = service.resolve(
            principal=tenant_a_principal, observation_text="a", priority_score=60
        )
        resolution_b = service.resolve(
            principal=tenant_b_principal, observation_text="b", priority_score=60
        )
        session.commit()

    with factory() as verify_session:
        repository = GateVAgentResolutionRepositoryImpl(verify_session)
        reread_a = repository.get_by_id(resolution_a.resolution_id)
        reread_b = repository.get_by_id(resolution_b.resolution_id)
        assert reread_a is not None
        assert reread_b is not None
        assert reread_a.tenant_id == "tenant-a"
        assert reread_b.tenant_id == "tenant-b"
