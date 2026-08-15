"""Full-stack proof for the Entity Resolution Steward API: real FastAPI
router, real application service, real EntityResolutionStore, and a real
disposable PostgreSQL database, all wired together through create_app().

Only authentication is dependency-overridden -- per the established test
pattern (see test_supplier_risk_api_security.py), OIDC token verification
itself is exercised elsewhere; TrustedPrincipal objects are supplied
directly here. The `container` dependency is overridden with a Container
built from *real* components (EntityResolutionStewardApiService,
SecurityAuditService/ApiSecurityAuditRepository) backed by the disposable
database, so security-audit rows are genuinely persisted and can be read
back and verified.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.api.supplier_risk.rate_limit import RateLimiter
from app.application.entity_resolution_steward_api import EntityResolutionStewardApiService
from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_ENTITY_TYPE_ID,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.identity_resolution.evidence import SourceRepresentation
from app.domain.identity_resolution.model import EvidenceType
from app.domain.identity_resolution.policy import conservative_preset
from app.domain.identity_resolution.service import EvidenceResolutionEngine
from app.infrastructure.persistence.api_security_audit_repository import (
    ApiSecurityAuditRepository,
)
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.resolution_policy_store import ResolutionPolicyStore
from app.main import create_app

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CANDIDATE_NAME = "Taiwan Semiconductor Manufacturing Company Limited"
RAW_TAX_ID = "SECRET-TAX-ID-FULLSTACK-0042"


def _tenant(label: str) -> str:
    return f"{label}-{uuid4()}"


def _principal(
    tenant_id: str,
    *,
    scopes: tuple[str, ...] = ("entity-resolution:read", "entity-resolution:decide"),
    principal_id: str = "steward-full-stack",
) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id=principal_id,
        tenant_id=tenant_id,
        scopes=scopes,
        roles=("steward",),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _seed_case(
    session: Session, *, tenant_id: str, with_matching_tax_id: bool = False
) -> tuple[str, UUID, UUID]:
    """Seeds one source system/object pair, a materialized Conservative
    policy, and one evidence-bearing resolution record. Returns
    (understanding_key, record_id, policy_id)."""
    system_id = uuid4()
    session.add(
        SourceSystem(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=f"sys-{uuid4()}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
        )
    )
    session.flush()
    source_id = uuid4()
    session.add(
        SourceObject(
            source_object_id=source_id,
            tenant_id=tenant_id,
            source_object_name=f"obj-{uuid4()}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            source_system_id=system_id,
        )
    )
    session.flush()
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=f"Entity-{uuid4()}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            entity_type_id=BOOTSTRAP_ENTITY_TYPE_ID,
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()

    policy = conservative_preset()
    policy_row = ResolutionPolicyStore(session).materialize(
        tenant_id, policy, preset_kind="Conservative"
    )
    policy_id = policy_row.policy_id

    strong_identifiers = (
        ((EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION, RAW_TAX_ID),)
        if with_matching_tax_id
        else ()
    )
    rep = SourceRepresentation(
        source_object_id=source_id,
        source_system_name="CRM",
        display_name=CANDIDATE_NAME,
        website_domain="tsmc.com",
        country="Taiwan",
        strong_identifiers=strong_identifiers,
    )
    engine = EvidenceResolutionEngine(policy, policy_id=policy_id)
    record = engine.resolve(
        tenant_id=tenant_id,
        supporting_source_object_ids=(source_id,),
        representations=(rep,),
        candidate_name=CANDIDATE_NAME,
        candidate_enterprise_entity_id=entity_id,
        produced_at=NOW,
        candidate_country="Taiwan",
    )
    EntityResolutionStore(session).append(record)
    understanding_key = EntityResolutionStore.understanding_key((source_id,))
    return understanding_key, record.record_id, policy_id


def _real_container(migrated_engine: Engine) -> Container:
    sessions = sessionmaker(migrated_engine)
    return Container(
        Settings(),
        entity_resolution_steward_api=EntityResolutionStewardApiService(sessions),
        security_audit=SecurityAuditService(ApiSecurityAuditRepository(sessions)),
        rate_limiter=RateLimiter(1000),
    )


def _client(migrated_engine: Engine, authenticated: TrustedPrincipal) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: _real_container(migrated_engine)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Authenticated, tenant-scoped case read
# ---------------------------------------------------------------------------


def test_authenticated_tenant_scoped_case_read(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        understanding_key, record_id, _policy_id = _seed_case(session, tenant_id=tenant_id)

    client = _client(migrated_engine, _principal(tenant_id))
    response = client.get(f"/api/v1/entity-resolution/cases/{understanding_key}")

    assert response.status_code == 200
    body = response.json()
    assert body["understanding_key"] == understanding_key
    assert body["record_id"] == str(record_id)
    assert len(body["source_representations"]) == 1


# ---------------------------------------------------------------------------
# Missing scope -> 403
# ---------------------------------------------------------------------------


def test_missing_scope_returns_403(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        understanding_key, _record_id, _policy_id = _seed_case(session, tenant_id=tenant_id)

    client = _client(migrated_engine, _principal(tenant_id, scopes=()))
    response = client.get(f"/api/v1/entity-resolution/cases/{understanding_key}")

    assert response.status_code == 403
    assert response.json()["code"] == "AUTHORIZATION_SCOPE_REQUIRED"


# ---------------------------------------------------------------------------
# Cross-tenant case -> 404, no disclosure
# ---------------------------------------------------------------------------


def test_cross_tenant_case_returns_404_without_disclosure(migrated_engine: Engine) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        understanding_key, _record_id, _policy_id = _seed_case(session, tenant_id=tenant_b)

    client = _client(migrated_engine, _principal(tenant_a))
    response = client.get(f"/api/v1/entity-resolution/cases/{understanding_key}")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "RESOLUTION_CASE_NOT_FOUND"
    # The response never echoes back the tenant that actually owns the case,
    # nor any other case content.
    assert tenant_b not in response.text
    assert "record_id" not in body
    assert "evidence_profile" not in body


# ---------------------------------------------------------------------------
# Successful decision append
# ---------------------------------------------------------------------------


def test_successful_decision_append_through_full_stack(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        understanding_key, record_id, policy_id = _seed_case(
            session, tenant_id=tenant_id, with_matching_tax_id=True
        )

    client = _client(migrated_engine, _principal(tenant_id))
    response = client.post(
        f"/api/v1/entity-resolution/cases/{understanding_key}/decisions",
        json={
            "action": "confirm_match",
            "rationale": "Verified via full-stack integration test.",
            "based_on_record_id": str(record_id),
            "policy_id": str(policy_id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["outcome"] == "Resolved"
    new_record_id = UUID(body["record_id"])
    assert new_record_id != record_id

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        history = store.get_history(tenant_id, understanding_key)
        assert history is not None
        assert history.current_record_identifier == new_record_id
        assert str(record_id) in history.historical_record_references


# ---------------------------------------------------------------------------
# Stale decision -> stable HTTP 409 STALE_RESOLUTION_CASE
# ---------------------------------------------------------------------------


def test_stale_decision_returns_stable_409(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        understanding_key, original_record_id, policy_id = _seed_case(session, tenant_id=tenant_id)

    client = _client(migrated_engine, _principal(tenant_id))

    # First decision succeeds and moves the history pointer.
    first = client.post(
        f"/api/v1/entity-resolution/cases/{understanding_key}/decisions",
        json={
            "action": "mark_unresolved",
            "rationale": "First steward decision.",
            "based_on_record_id": str(original_record_id),
            "policy_id": str(policy_id),
        },
    )
    assert first.status_code == 201

    # A second decision using the now-stale original record id must fail
    # with a stable 409 STALE_RESOLUTION_CASE, and must append nothing.
    second = client.post(
        f"/api/v1/entity-resolution/cases/{understanding_key}/decisions",
        json={
            "action": "mark_unresolved",
            "rationale": "Second steward, unaware the case already moved on.",
            "based_on_record_id": str(original_record_id),
            "policy_id": str(policy_id),
        },
    )
    assert second.status_code == 409
    assert second.json()["code"] == "STALE_RESOLUTION_CASE"

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        history = store.get_history(tenant_id, understanding_key)
        assert history is not None
        assert str(original_record_id) in history.historical_record_references
        # Exactly one successor was appended -- the rejected second attempt
        # appended nothing.
        assert len(history.historical_record_references) == 1


# ---------------------------------------------------------------------------
# Real security-audit persistence (Gap 4)
# ---------------------------------------------------------------------------


def test_real_audit_rows_are_persisted_for_success_and_stale_rejection(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        understanding_key, original_record_id, policy_id = _seed_case(
            session, tenant_id=tenant_id, with_matching_tax_id=True
        )

    client = _client(migrated_engine, _principal(tenant_id))

    success = client.post(
        f"/api/v1/entity-resolution/cases/{understanding_key}/decisions",
        json={
            "action": "confirm_match",
            "rationale": "Verified for audit-persistence proof.",
            "based_on_record_id": str(original_record_id),
            "policy_id": str(policy_id),
        },
    )
    assert success.status_code == 201

    stale = client.post(
        f"/api/v1/entity-resolution/cases/{understanding_key}/decisions",
        json={
            "action": "mark_unresolved",
            "rationale": "Stale attempt for audit-persistence proof.",
            "based_on_record_id": str(original_record_id),
            "policy_id": str(policy_id),
        },
    )
    assert stale.status_code == 409

    sessions = sessionmaker(migrated_engine)
    repository = ApiSecurityAuditRepository(sessions)
    rows = repository.list_for_tenant(tenant_id)
    assert rows

    codes = {row.diagnostic_code for row in rows}
    assert "RESOLUTION_DECISION_ACCEPTED" in codes
    assert "STALE_RESOLUTION_CASE" in codes

    accepted_row = next(r for r in rows if r.diagnostic_code == "RESOLUTION_DECISION_ACCEPTED")
    stale_row = next(r for r in rows if r.diagnostic_code == "STALE_RESOLUTION_CASE")

    for row in (accepted_row, stale_row):
        assert row.tenant_id == tenant_id
        assert row.principal_reference == "steward-full-stack"
        assert row.operation == "DECIDE_RESOLUTION_CASE"
        assert row.endpoint_classification == "ENTITY_RESOLUTION_STEWARD_API_V1"

    assert accepted_row.outcome == "ACCEPTED"
    assert accepted_row.execution_id is not None
    assert stale_row.outcome == "REJECTED"

    # No raw sensitive identifier anywhere in any persisted audit field.
    for row in rows:
        for value in (
            row.operation,
            row.endpoint_classification,
            row.event_category,
            row.outcome,
            row.diagnostic_code,
            row.tenant_id,
            row.principal_reference,
            row.authorization_decision_reference,
            row.evidence_resource_reference,
            row.source_channel,
        ):
            if value is not None:
                assert RAW_TAX_ID not in value
