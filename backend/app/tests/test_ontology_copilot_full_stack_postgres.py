"""Full-stack proof for the Ask CTEC API (Gate D): real FastAPI router, real
application service, real InstitutionalRelationshipStore, and a real
disposable PostgreSQL database, all wired together through create_app().

Only authentication is dependency-overridden -- per the established test
pattern (see test_entity_resolution_steward_full_stack_postgres.py); the
`container` dependency is overridden with a Container built from *real*
components backed by the disposable database, so the whole round trip --
HTTP request -> auth -> scope check -> application service -> real SQL
query -> real audit row -> HTTP response -- is genuinely exercised.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.api.supplier_risk.rate_limit import RateLimiter
from app.application.ontology_copilot_api import OntologyCopilotApiService
from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_DEMO_TENANT_ID,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.core.config import Settings
from app.core.dependency_container import Container
from app.infrastructure.persistence.api_security_audit_repository import (
    ApiSecurityAuditRepository,
)
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    DemoFieldValueEvidenceSeeder,
)
from app.infrastructure.persistence.models.api_security_audit import ApiSecurityAuditEventORM
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.main import create_app

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _tenant(label: str) -> str:
    return f"{label}-{uuid4()}"


def _principal(
    tenant_id: str, *, scopes: tuple[str, ...] = ("ontology-copilot:ask",)
) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-full-stack",
        tenant_id=tenant_id,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _real_container(migrated_engine: Engine) -> Container:
    sessions = sessionmaker(migrated_engine)
    return Container(
        Settings(),
        ontology_copilot_api=OntologyCopilotApiService(sessions),
        security_audit=SecurityAuditService(ApiSecurityAuditRepository(sessions)),
        rate_limiter=RateLimiter(1000),
    )


def _client(migrated_engine: Engine, authenticated: TrustedPrincipal) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: _real_container(migrated_engine)
    return TestClient(app)


def _seed_supply_chain(session: Session, *, tenant_id: str, supplier_name: str) -> None:
    OntologySeeder(session).load()
    session.flush()
    entity_types: dict[str, UUID] = {
        name: entity_type_id
        for name, entity_type_id in session.execute(
            select(EntityType.entity_type_name, EntityType.entity_type_id).where(
                EntityType.entity_type_name.in_(("Supplier", "Material", "BOM", "Product"))
            )
        ).all()
    }
    relationship_types: dict[str, UUID] = {
        name: relationship_type_id
        for name, relationship_type_id in session.execute(
            select(
                RelationshipType.relationship_type_name, RelationshipType.relationship_type_id
            ).where(RelationshipType.relationship_type_name.in_(("supplies", "usedIn", "defines")))
        ).all()
    }

    def entity(name: str, type_name: str) -> UUID:
        entity_id = uuid4()
        session.add(
            EnterpriseEntity(
                enterprise_entity_id=entity_id,
                tenant_id=tenant_id,
                enterprise_entity_name=name,
                lifecycle_state="Active",
                effective_from=NOW,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
                entity_type_id=entity_types[type_name],
                business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
            )
        )
        session.flush()
        return entity_id

    def relate(name: str, type_name: str, from_id: UUID, to_id: UUID) -> None:
        session.add(
            InstitutionalRelationship(
                institutional_relationship_id=uuid4(),
                tenant_id=tenant_id,
                institutional_relationship_name=name,
                lifecycle_state="Active",
                effective_from=NOW,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
                relationship_type_id=relationship_types[type_name],
                from_entity_id=from_id,
                to_entity_id=to_id,
            )
        )
        session.flush()

    supplier_id = entity(supplier_name, "Supplier")
    material_id = entity(f"Material for {supplier_name}", "Material")
    bom_id = entity(f"BOM for {supplier_name}", "BOM")
    product_id = entity(f"Product for {supplier_name}", "Product")
    relate(f"{supplier_name}-supplies", "supplies", supplier_id, material_id)
    relate(f"{supplier_name}-usedIn", "usedIn", material_id, bom_id)
    relate(f"{supplier_name}-defines", "defines", bom_id, product_id)


def test_successful_ask_through_the_full_stack(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant")
    supplier_name = f"FullStack-Supplier-{uuid4()}"
    with Session(migrated_engine) as session, session.begin():
        _seed_supply_chain(session, tenant_id=tenant_id, supplier_name=supplier_name)

    client = _client(migrated_engine, _principal(tenant_id))
    response = client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": f"Which products depend on {supplier_name}?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["result_names"] == [f"Product for {supplier_name}"]
    assert body["resolved_entity"]["entity_name"] == supplier_name
    assert len(body["evidence"]) == 1
    relationship_names = [
        step["relationship_name"] for step in body["evidence"][0] if step["relationship_name"]
    ]
    assert relationship_names == ["supplies", "usedIn", "defines"]


def test_missing_scope_returns_403(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant")
    client = _client(migrated_engine, _principal(tenant_id, scopes=()))
    response = client.post("/api/v1/ontology-copilot/ask", json={"question": "x"})
    assert response.status_code == 403
    assert response.json()["code"] == "AUTHORIZATION_SCOPE_REQUIRED"


def test_missing_bearer_token_returns_401(migrated_engine: Engine) -> None:
    del migrated_engine
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/ontology-copilot/ask", json={"question": "x"})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_MISSING"


def test_real_audit_row_is_persisted_for_a_successful_ask(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant")
    supplier_name = f"Audit-Supplier-{uuid4()}"
    with Session(migrated_engine) as session, session.begin():
        _seed_supply_chain(session, tenant_id=tenant_id, supplier_name=supplier_name)

    client = _client(migrated_engine, _principal(tenant_id))
    response = client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": f"Which products depend on {supplier_name}?"},
    )
    assert response.status_code == 200

    with Session(migrated_engine) as session:
        rows = (
            session.execute(
                select(ApiSecurityAuditEventORM).where(
                    ApiSecurityAuditEventORM.operation == "ASK_ONTOLOGY_QUESTION",
                    ApiSecurityAuditEventORM.tenant_id == tenant_id,
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1
    assert rows[0].outcome == "ANSWERED"
    # The raw question/supplier text is never persisted in the audit row.
    for column in ("operation", "outcome", "diagnostic_code", "tenant_id", "principal_reference"):
        value = str(getattr(rows[0], column))
        assert supplier_name not in value


def test_full_stack_ask_is_read_only(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant")
    supplier_name = f"ReadOnlyFullStack-{uuid4()}"
    with Session(migrated_engine) as session, session.begin():
        _seed_supply_chain(session, tenant_id=tenant_id, supplier_name=supplier_name)

    def _counts(session: Session) -> tuple[int, int]:
        return (
            session.execute(select(func.count()).select_from(EnterpriseEntity)).scalar_one(),
            session.execute(
                select(func.count()).select_from(InstitutionalRelationship)
            ).scalar_one(),
        )

    with Session(migrated_engine) as session:
        before = _counts(session)

    client = _client(migrated_engine, _principal(tenant_id))
    client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": f"Which products depend on {supplier_name}?"},
    )
    client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": "Which products depend on Nobody?"},
    )

    with Session(migrated_engine) as session:
        after = _counts(session)

    assert before == after


# ---------------------------------------------------------------------------
# Gate P (CDD-025): one bounded full-stack acceptance scenario. This does
# not re-prove the full acceptance matrix (already proven in
# test_ontology_copilot_api_postgres.py) -- it proves the real HTTP round
# trip: request -> auth -> scope check -> application service -> real
# Blueprint/Gate I/H4/Gate N chain -> HTTP response.
# ---------------------------------------------------------------------------


def test_successful_gate_p_ask_through_the_full_stack(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        DemoFieldValueEvidenceSeeder(session).seed()

    client = _client(migrated_engine, _principal(BOOTSTRAP_DEMO_TENANT_ID))
    response = client.post(
        "/api/v1/ontology-copilot/ask",
        json={
            "question": (
                f"What is the evidence status of Supplier Legal Name in {CANONICAL_BLUEPRINT_NAME}?"
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    explanation = body["context_explanation"]
    assert explanation is not None
    assert explanation["status"] == "answered"
    assert explanation["coverage_status"] == "MAPPED"
    assert explanation["evidence_availability_status"] == "EVIDENCE_PRESENT"
    assert "Supplier Legal Name" in body["answer"]

    # Existing Gate D supplier-question full-stack behavior remains unaffected,
    # asked through the same client/principal as the Gate P question above.
    supplier_name = f"GateP-Coexist-Supplier-{uuid4()}"
    with Session(migrated_engine) as session, session.begin():
        _seed_supply_chain(session, tenant_id=BOOTSTRAP_DEMO_TENANT_ID, supplier_name=supplier_name)
    supplier_response = client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": f"Which products depend on {supplier_name}?"},
    )
    assert supplier_response.status_code == 200
    assert supplier_response.json()["status"] == "answered"
    assert supplier_response.json()["context_explanation"] is None
