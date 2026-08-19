"""Gate F Supply Chain Impact API security tests (CDD-015 §16, §21, §25,
§28, §35; PAD-003 §2a-§4a). Follows `test_supplier_risk_api_security.py`'s
and `test_ontology_copilot_router.py`'s established two-layer pattern:
fast, DB-free tests through FastAPI dependency overrides for the
authentication/authorization/injection trust boundary (no fake service call
happens until authorization has already succeeded), plus a real-Postgres,
full-stack section (mirroring `test_ontology_copilot_full_stack_postgres.py`)
proving the genuine round trip -- HTTP request -> auth -> scope check ->
real SupplyChainImpactApiService -> real persisted state -> HTTP response.

`supply-chain-impact:read` and `supply-chain-impact:evaluate` are
independent, non-compositional scopes (PAD-003 §4a): holding one never
authorizes the other's operation, except that an evaluate call's own
response may include its own freshly-created result.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.api.supplier_risk.rate_limit import RateLimiter
from app.api.supply_chain_impact.dependencies import (
    supply_chain_impact_api_service,
    supply_chain_impact_sessions,
)
from app.application.supply_chain_impact_api import (
    ImpactSummary,
    SupplyChainImpactApiService,
    SupplyChainImpactEvaluateRequest,
    SupplyChainImpactEvaluationResult,
)
from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.core.config import Settings
from app.core.dependency_container import Container
from app.infrastructure.persistence.api_security_audit_repository import (
    ApiSecurityAuditRepository,
)
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.main import create_app

NOW = datetime(2026, 1, 1, tzinfo=UTC)
EVALUATIONS_PATH = "/api/v1/supply-chain-impact/evaluations"


class Audit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, **values: object) -> UUID:
        self.events.append(values)
        return uuid4()


def _principal(*, tenant_id: str = "tenant-a", scopes: tuple[str, ...] = ()) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="analyst-jane",
        tenant_id=tenant_id,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


# --------------------------------------------------------------------------
# Fast, DB-free authentication/authorization/injection boundary tests
# --------------------------------------------------------------------------


@dataclass
class FakeSupplyChainImpactApiService:
    calls: list[tuple[TrustedPrincipal, SupplyChainImpactEvaluateRequest]] = field(
        default_factory=list
    )
    result: SupplyChainImpactEvaluationResult | None = None

    def evaluate(
        self, principal: TrustedPrincipal, request: SupplyChainImpactEvaluateRequest
    ) -> SupplyChainImpactEvaluationResult:
        self.calls.append((principal, request))
        assert self.result is not None
        return self.result


def _fake_result(decision_evaluation_id: UUID, tenant_id: str) -> SupplyChainImpactEvaluationResult:
    return SupplyChainImpactEvaluationResult(
        decision_evaluation_id=decision_evaluation_id,
        tenant_id=tenant_id,
        impact=ImpactSummary(
            supplier_entity_id=uuid4(),
            supplier_name="SUP-1",
            materials=(),
            products=(),
            facilities=(),
            revenue_exposures=(),
        ),
        materials=(),
        governance_standing=None,
        governance_record_identifier=None,
    )


def _fake_container(
    *, audit: Audit | None = None, rate_limiter: RateLimiter | None = None
) -> Container:
    return Container(
        Settings(),
        security_audit=audit or Audit(),  # type: ignore[arg-type]
        rate_limiter=rate_limiter or RateLimiter(1000),
    )


def _fake_client(
    app_container: Container,
    service: FakeSupplyChainImpactApiService,
    authenticated: TrustedPrincipal,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: app_container
    app.dependency_overrides[supply_chain_impact_api_service] = lambda: service
    # The read route's session dependency is resolved before the route body
    # runs its own _authorize() check (ordinary FastAPI dependency
    # resolution order, identical to how api_service/steward_api_service
    # already behave elsewhere in this codebase) -- override it directly so
    # authorization-boundary tests exercise _authorize() itself rather than
    # failing earlier on an unconfigured session factory the fake container
    # never needs to actually open.
    app.dependency_overrides[supply_chain_impact_sessions] = lambda: None
    return TestClient(app)


def test_missing_token_denied_on_evaluate() -> None:
    with TestClient(create_app()) as client:
        response = client.post(EVALUATIONS_PATH, json={"supplier_entity_id": str(uuid4())})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_TOKEN_MISSING"


def test_missing_token_denied_on_read() -> None:
    with TestClient(create_app()) as client:
        response = client.get(f"{EVALUATIONS_PATH}/{uuid4()}")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_TOKEN_MISSING"


def test_missing_evaluate_scope_denied() -> None:
    service = FakeSupplyChainImpactApiService()
    client = _fake_client(
        _fake_container(),
        service,
        _principal(scopes=("supply-chain-impact:read",)),
    )
    response = client.post(EVALUATIONS_PATH, json={"supplier_entity_id": str(uuid4())})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_missing_read_scope_denied() -> None:
    client = _fake_client(
        _fake_container(),
        FakeSupplyChainImpactApiService(),
        _principal(scopes=("supply-chain-impact:evaluate",)),
    )
    response = client.get(f"{EVALUATIONS_PATH}/{uuid4()}")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"


def test_no_scope_principal_denied_both_operations() -> None:
    client = _fake_client(
        _fake_container(), FakeSupplyChainImpactApiService(), _principal(scopes=())
    )
    read_response = client.get(f"{EVALUATIONS_PATH}/{uuid4()}")
    evaluate_response = client.post(EVALUATIONS_PATH, json={"supplier_entity_id": str(uuid4())})
    assert read_response.status_code == 403
    assert evaluate_response.status_code == 403


def test_evaluate_authorized_reaches_service_with_trusted_principal() -> None:
    decision_evaluation_id = uuid4()
    service = FakeSupplyChainImpactApiService(
        result=_fake_result(decision_evaluation_id, "tenant-a")
    )
    authenticated = _principal(tenant_id="tenant-a", scopes=("supply-chain-impact:evaluate",))
    client = _fake_client(_fake_container(), service, authenticated)
    supplier_entity_id = uuid4()
    response = client.post(EVALUATIONS_PATH, json={"supplier_entity_id": str(supplier_entity_id)})
    assert response.status_code == 201
    assert response.json()["decision_evaluation_id"] == str(decision_evaluation_id)
    assert len(service.calls) == 1
    called_principal, called_request = service.calls[0]
    assert called_principal is authenticated
    assert called_request.supplier_entity_id == supplier_entity_id


def test_evaluate_requires_supplier_entity_id() -> None:
    client = _fake_client(
        _fake_container(),
        FakeSupplyChainImpactApiService(),
        _principal(scopes=("supply-chain-impact:evaluate",)),
    )
    response = client.post(EVALUATIONS_PATH, json={})
    assert response.status_code == 422


def test_evaluate_rejects_authority_bearing_fields() -> None:
    """The evaluate request schema uses extra="forbid" (ClosedModel):
    submitting any field beyond supplier_entity_id is a 422 validation
    error, never silently accepted or trusted (CDD-015 §25, §19; PAD-003
    §8) -- covers every governed fact/tenant/outcome field the caller must
    never be authoritative for."""
    client = _fake_client(
        _fake_container(),
        FakeSupplyChainImpactApiService(),
        _principal(scopes=("supply-chain-impact:evaluate",)),
    )
    base = {"supplier_entity_id": str(uuid4())}
    injected_fields = (
        "tenant_id",
        "high_severity",
        "single_source",
        "annual_revenue_exposure",
        "materiality",
        "qualified",
        "capacity_sufficient",
        "lead_time_days",
        "candidate_cost",
        "recommendation",
        "governance_outcome",
    )
    for field_name in injected_fields:
        response = client.post(EVALUATIONS_PATH, json={**base, field_name: "malicious-value"})
        assert response.status_code == 422, f"{field_name} was not rejected"


def test_openapi_schema_evaluate_request_has_only_supplier_entity_id() -> None:
    app = create_app()
    schema = app.openapi()
    body_schema = schema["components"]["schemas"]["SupplyChainImpactEvaluateRequest"]
    assert set(body_schema["properties"]) == {"supplier_entity_id"}
    assert body_schema.get("additionalProperties") is False


# --------------------------------------------------------------------------
# Real-Postgres full-stack tests
# --------------------------------------------------------------------------


def _tenant(label: str) -> str:
    return f"gate-f-api-{label}-{uuid4()}"


def _entity_type_id(session: Session, name: str) -> UUID:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return value


def _relationship_type_id(session: Session, name: str) -> UUID:
    value = session.scalar(
        select(RelationshipType.relationship_type_id).where(
            RelationshipType.relationship_type_name == name
        )
    )
    assert value is not None
    return value


def _entity(session: Session, *, tenant_id: str, name: str, type_name: str) -> UUID:
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            effective_to=None,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            modified_by=None,
            modified_on=None,
            version_number=1,
            previous_version_id=None,
            entity_type_id=_entity_type_id(session, type_name),
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _relate(
    session: Session, *, tenant_id: str, type_name: str, from_id: UUID, to_id: UUID
) -> UUID:
    relationship_id = uuid4()
    session.add(
        InstitutionalRelationship(
            institutional_relationship_id=relationship_id,
            tenant_id=tenant_id,
            institutional_relationship_name=f"{type_name}:{relationship_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            effective_to=None,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            modified_by=None,
            modified_on=None,
            version_number=1,
            previous_version_id=None,
            relationship_type_id=_relationship_type_id(session, type_name),
            from_entity_id=from_id,
            to_entity_id=to_id,
            superseded_by_id=None,
        )
    )
    session.flush()
    return relationship_id


def _seed_source_system(session: Session, tenant_id: str) -> UUID:
    identifier = uuid5(BOOTSTRAP_SEED_NAMESPACE, f"gate-f-api-test-seed-source:{tenant_id}")
    if session.get(SourceSystem, identifier) is None:
        session.add(
            SourceSystem(
                source_system_id=identifier,
                tenant_id=tenant_id,
                source_system_name=f"Gate F API Test Seed Source ({tenant_id})",
                lifecycle_state="Active",
                effective_from=NOW,
                effective_to=None,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
                modified_by=None,
                modified_on=None,
                version_number=1,
                previous_version_id=None,
            )
        )
        session.flush()
    return identifier


def _assert_literal(
    session: Session,
    *,
    subject_entity_id: UUID,
    predicate: str,
    object_value: str,
    source_system_id: UUID,
) -> UUID:
    assertion_id = uuid4()
    session.add(
        Assertion(
            assertion_id=assertion_id,
            assertion_name=f"gate-f-api-test:{assertion_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            effective_to=None,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            modified_by=None,
            modified_on=None,
            version_number=1,
            previous_version_id=None,
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            object_value=object_value,
            object_entity_id=None,
            source_system_id=source_system_id,
            source_object_id=None,
            asserted_on=NOW,
            prior_assertion_id=None,
            knowledge_id=None,
            assertion_type="Institutional",
            relationship_type_id=None,
        )
    )
    session.flush()
    return assertion_id


def _build_scenario(
    session: Session,
    tenant_id: str,
    *,
    severity: str | None = "Severe",
    revenue_usd: str | None = "12000000",
    with_alternate: bool = True,
    alternate_qualified: str | None = "true",
    alternate_capacity: str | None = "true",
) -> dict[str, UUID]:
    source_system_id = _seed_source_system(session, tenant_id)
    supplier = _entity(session, tenant_id=tenant_id, name=f"SUP-{uuid4()}", type_name="Supplier")
    material = _entity(session, tenant_id=tenant_id, name=f"MAT-{uuid4()}", type_name="Material")
    bom = _entity(session, tenant_id=tenant_id, name=f"BOM-{uuid4()}", type_name="BOM")
    product = _entity(session, tenant_id=tenant_id, name=f"PROD-{uuid4()}", type_name="Product")
    revenue = _entity(
        session, tenant_id=tenant_id, name=f"REV-{uuid4()}", type_name="Revenue Exposure"
    )
    region = _entity(session, tenant_id=tenant_id, name=f"REG-{uuid4()}", type_name="Region")
    risk_event = _entity(
        session, tenant_id=tenant_id, name=f"RISK-{uuid4()}", type_name="Risk Event"
    )

    _relate(session, tenant_id=tenant_id, type_name="supplies", from_id=supplier, to_id=material)
    _relate(session, tenant_id=tenant_id, type_name="usedIn", from_id=material, to_id=bom)
    _relate(session, tenant_id=tenant_id, type_name="defines", from_id=bom, to_id=product)
    _relate(
        session, tenant_id=tenant_id, type_name="generatesRevenue", from_id=product, to_id=revenue
    )
    _relate(session, tenant_id=tenant_id, type_name="locatedIn", from_id=supplier, to_id=region)
    _relate(session, tenant_id=tenant_id, type_name="exposedTo", from_id=region, to_id=risk_event)

    if severity is not None:
        _assert_literal(
            session,
            subject_entity_id=risk_event,
            predicate="severity",
            object_value=severity,
            source_system_id=source_system_id,
        )
    if revenue_usd is not None:
        _assert_literal(
            session,
            subject_entity_id=revenue,
            predicate="annualRevenueUsd",
            object_value=revenue_usd,
            source_system_id=source_system_id,
        )

    result = {"supplier": supplier, "material": material, "risk_event": risk_event}
    if with_alternate:
        alternate_supplier = _entity(
            session, tenant_id=tenant_id, name=f"ALT-{uuid4()}", type_name="Alternate Supplier"
        )
        if alternate_qualified is not None:
            _assert_literal(
                session,
                subject_entity_id=alternate_supplier,
                predicate="qualification",
                object_value=alternate_qualified,
                source_system_id=source_system_id,
            )
        if alternate_capacity is not None:
            _assert_literal(
                session,
                subject_entity_id=alternate_supplier,
                predicate="capacity",
                object_value=alternate_capacity,
                source_system_id=source_system_id,
            )
        result["alternate_supplier"] = alternate_supplier

    session.commit()
    return result


def _real_container(migrated_engine: Engine) -> Container:
    sessions = sessionmaker(migrated_engine)
    return Container(
        Settings(),
        supply_chain_impact_api=SupplyChainImpactApiService(sessions),
        security_audit=SecurityAuditService(ApiSecurityAuditRepository(sessions)),
        rate_limiter=RateLimiter(1000),
        ontology_sessions=sessions,
    )


def _real_client(migrated_engine: Engine, authenticated: TrustedPrincipal) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: _real_container(migrated_engine)
    return TestClient(app)


def test_evaluate_and_read_round_trip_recommended(migrated_engine: Engine) -> None:
    tenant_id = _tenant("recommended")
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        scenario = _build_scenario(session, tenant_id)

    authenticated = _principal(
        tenant_id=tenant_id,
        scopes=("supply-chain-impact:read", "supply-chain-impact:evaluate"),
    )
    client = _real_client(migrated_engine, authenticated)

    evaluate_response = client.post(
        EVALUATIONS_PATH, json={"supplier_entity_id": str(scenario["supplier"])}
    )
    assert evaluate_response.status_code == 201
    evaluate_body = evaluate_response.json()
    assert evaluate_body["governance_standing"] == "HUMAN_APPROVAL_REQUIRED"
    assert evaluate_body["policy_reference"] == "CDD-015-Gate-F-Mitigation-Policy"
    assert evaluate_body["policy_version"] == "2.0"
    [material] = evaluate_body["materials"]
    [candidate] = material["candidates"]
    assert candidate["outcome"] == "Recommended"
    decision_evaluation_id = evaluate_body["decision_evaluation_id"]

    read_response = client.get(f"{EVALUATIONS_PATH}/{decision_evaluation_id}")
    assert read_response.status_code == 200
    read_body = read_response.json()
    assert read_body["decision_evaluation_id"] == decision_evaluation_id
    [record] = read_body["records"]
    assert record["outcome"] == "Recommended"
    assert record["policy_reference"] == "CDD-015-Gate-F-Mitigation-Policy"
    assert record["policy_version"] == "2.0"
    assert read_body["governance"]["human_approval_required"] is True
    assert read_body["governance"]["governance_outcome"] == "Requires Review"


def test_evaluate_missing_severity_evidence_stays_unknown_not_rejected(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("unknown-severity")
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        scenario = _build_scenario(session, tenant_id, severity=None)

    authenticated = _principal(tenant_id=tenant_id, scopes=("supply-chain-impact:evaluate",))
    client = _real_client(migrated_engine, authenticated)
    response = client.post(EVALUATIONS_PATH, json={"supplier_entity_id": str(scenario["supplier"])})
    assert response.status_code == 201
    body = response.json()
    [material] = body["materials"]
    assert material["high_severity_disruption"] is None
    [candidate] = material["candidates"]
    assert candidate["outcome"] is None
    assert candidate["reason"] is None
    assert candidate["decision_record_identifier"] is None


def test_evaluate_zero_alternates_is_known_rejected(migrated_engine: Engine) -> None:
    tenant_id = _tenant("zero-alt")
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        scenario = _build_scenario(session, tenant_id, with_alternate=False)

    authenticated = _principal(tenant_id=tenant_id, scopes=("supply-chain-impact:evaluate",))
    client = _real_client(migrated_engine, authenticated)
    response = client.post(EVALUATIONS_PATH, json={"supplier_entity_id": str(scenario["supplier"])})
    assert response.status_code == 201
    [material] = response.json()["materials"]
    [candidate] = material["candidates"]
    assert candidate["outcome"] == "Rejected"
    assert candidate["alternate_supplier_entity_id"] is None


def test_evaluate_cross_tenant_supplier_not_found(migrated_engine: Engine) -> None:
    owner_tenant = _tenant("owner")
    other_tenant = _tenant("other")
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        scenario = _build_scenario(session, owner_tenant)

    authenticated = _principal(tenant_id=other_tenant, scopes=("supply-chain-impact:evaluate",))
    client = _real_client(migrated_engine, authenticated)
    response = client.post(EVALUATIONS_PATH, json={"supplier_entity_id": str(scenario["supplier"])})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SUPPLY_CHAIN_IMPACT_TARGET_NOT_FOUND"


def test_read_unknown_evaluation_id_not_found(migrated_engine: Engine) -> None:
    authenticated = _principal(tenant_id=_tenant("reader"), scopes=("supply-chain-impact:read",))
    client = _real_client(migrated_engine, authenticated)
    response = client.get(f"{EVALUATIONS_PATH}/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SUPPLY_CHAIN_IMPACT_EVALUATION_NOT_FOUND"


def test_read_cross_tenant_evaluation_not_found(migrated_engine: Engine) -> None:
    owner_tenant = _tenant("owner-read")
    other_tenant = _tenant("other-read")
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        scenario = _build_scenario(session, owner_tenant)

    owner_client = _real_client(
        migrated_engine,
        _principal(tenant_id=owner_tenant, scopes=("supply-chain-impact:evaluate",)),
    )
    evaluate_response = owner_client.post(
        EVALUATIONS_PATH, json={"supplier_entity_id": str(scenario["supplier"])}
    )
    decision_evaluation_id = evaluate_response.json()["decision_evaluation_id"]

    other_client = _real_client(
        migrated_engine, _principal(tenant_id=other_tenant, scopes=("supply-chain-impact:read",))
    )
    response = other_client.get(f"{EVALUATIONS_PATH}/{decision_evaluation_id}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SUPPLY_CHAIN_IMPACT_EVALUATION_NOT_FOUND"


def test_read_does_not_rerun_evaluation(migrated_engine: Engine) -> None:
    """A later change to underlying governed facts must not silently
    change a historical read result (CDD-015 §20)."""
    tenant_id = _tenant("historical")
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        scenario = _build_scenario(session, tenant_id)

    authenticated = _principal(
        tenant_id=tenant_id,
        scopes=("supply-chain-impact:read", "supply-chain-impact:evaluate"),
    )
    client = _real_client(migrated_engine, authenticated)
    evaluate_response = client.post(
        EVALUATIONS_PATH, json={"supplier_entity_id": str(scenario["supplier"])}
    )
    decision_evaluation_id = evaluate_response.json()["decision_evaluation_id"]
    first_read = client.get(f"{EVALUATIONS_PATH}/{decision_evaluation_id}").json()

    with factory() as session:
        source_system_id = _seed_source_system(session, tenant_id)
        _assert_literal(
            session,
            subject_entity_id=scenario["risk_event"],
            predicate="severity",
            object_value="Low",
            source_system_id=source_system_id,
        )
        session.commit()

    second_read = client.get(f"{EVALUATIONS_PATH}/{decision_evaluation_id}").json()
    assert second_read["records"] == first_read["records"]


# --------------------------------------------------------------------------
# Keycloak configuration
# --------------------------------------------------------------------------


def test_keycloak_demo_persona_has_both_gate_f_scopes() -> None:
    import json
    from pathlib import Path

    realm = json.loads((Path(__file__).parents[3] / "keycloak" / "ctec-realm.json").read_text())
    default_scopes = realm["clients"][0]["defaultClientScopes"]
    assert "supply-chain-impact:read" in default_scopes
    assert "supply-chain-impact:evaluate" in default_scopes
    scope_names = {block["name"] for block in realm["clientScopes"]}
    assert {"supply-chain-impact:read", "supply-chain-impact:evaluate"} <= scope_names


def test_keycloak_unrelated_scope_assignments_unchanged() -> None:
    import json
    from pathlib import Path

    realm = json.loads((Path(__file__).parents[3] / "keycloak" / "ctec-realm.json").read_text())
    client = realm["clients"][0]
    assert set(client["optionalClientScopes"]) == {
        "supplier-risk:submit",
        "supplier-risk:retry",
        "supplier-risk:replay",
        "entity-resolution:decide",
    }
    assert "entity-resolution:decide" not in client["defaultClientScopes"]
