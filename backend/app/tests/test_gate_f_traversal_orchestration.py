"""Gate F traversal-orchestration and governed four-condition policy tests
(CDD-015 §8, §33, §35; remediated per the merged Gate F Governed Impact
Decision Policy Clarification and Remediation Report, PR #69). Tests
create governed state (assertions/relationships) BEFORE calling evaluate()
-- never pass business facts as request fields (Part 23).
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.supply_chain_impact_api import (
    SupplyChainImpactApiService,
    SupplyChainImpactEvaluateRequest,
)
from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.domain.decision_engine.configuration import GateFPolicyConfiguration
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.ontology_seed import OntologySeeder

NOW = datetime(2026, 1, 1, tzinfo=UTC)
POLICY = GateFPolicyConfiguration()


def _tenant() -> str:
    return f"gate-f-tenant-{uuid4()}"


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
    identifier = uuid5(BOOTSTRAP_SEED_NAMESPACE, f"gate-f-test-seed-source:{tenant_id}")
    if session.get(SourceSystem, identifier) is None:
        session.add(
            SourceSystem(
                source_system_id=identifier,
                tenant_id=tenant_id,
                source_system_name=f"Gate F Test Seed Source ({tenant_id})",
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
            assertion_name=f"gate-f-test:{assertion_id}",
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


def _principal(tenant_id: str) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id=f"analyst-{uuid4()}",
        tenant_id=tenant_id,
        scopes=("supply-chain-impact:read", "supply-chain-impact:evaluate"),
        roles=(),
        issuer="test",
        issued_at=NOW,
        expires_at=datetime(2027, 1, 1, tzinfo=UTC),
    )


def _build_scenario(
    session: Session,
    tenant_id: str,
    *,
    severity: str | None = "Severe",
    revenue_usd: str | None = "12000000",
    alternate_qualified: str | None = "true",
    alternate_capacity: str | None = "true",
    alternate_lead_time: str | None = "10",
    alternate_cost: str | None = "5000",
) -> dict[str, UUID]:
    source_system_id = _seed_source_system(session, tenant_id)

    supplier = _entity(session, tenant_id=tenant_id, name=f"SUP-{uuid4()}", type_name="Supplier")
    material = _entity(session, tenant_id=tenant_id, name=f"MAT-{uuid4()}", type_name="Material")
    bom = _entity(session, tenant_id=tenant_id, name=f"BOM-{uuid4()}", type_name="BOM")
    product = _entity(session, tenant_id=tenant_id, name=f"PROD-{uuid4()}", type_name="Product")
    facility = _entity(session, tenant_id=tenant_id, name=f"FAC-{uuid4()}", type_name="Facility")
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
    _relate(session, tenant_id=tenant_id, type_name="assembledAt", from_id=product, to_id=facility)
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
    if alternate_lead_time is not None:
        _assert_literal(
            session,
            subject_entity_id=alternate_supplier,
            predicate="leadTimeDays",
            object_value=alternate_lead_time,
            source_system_id=source_system_id,
        )
    if alternate_cost is not None:
        _assert_literal(
            session,
            subject_entity_id=alternate_supplier,
            predicate="costUsd",
            object_value=alternate_cost,
            source_system_id=source_system_id,
        )

    session.commit()
    return {
        "supplier": supplier,
        "material": material,
        "bom": bom,
        "product": product,
        "facility": facility,
        "revenue": revenue,
        "region": region,
        "risk_event": risk_event,
        "alternate_supplier": alternate_supplier,
    }


def test_traversal_reaches_full_dependency_chain(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        ids = _build_scenario(session, tenant_id)

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=ids["supplier"])
    )

    assert result.impact.supplier_entity_id == ids["supplier"]
    assert {m.material_entity_id for m in result.impact.materials} == {ids["material"]}
    assert {p.entity_id for p in result.impact.products} == {ids["product"]}
    assert {f.entity_id for f in result.impact.facilities} == {ids["facility"]}
    assert {r.entity_id for r in result.impact.revenue_exposures} == {ids["revenue"]}


def test_all_four_conditions_true_yields_recommended(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        ids = _build_scenario(session, tenant_id)

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=ids["supplier"])
    )

    material_result = result.materials[0]
    assert material_result.high_severity_disruption is True
    assert material_result.single_source_exposure is True
    assert material_result.revenue_materiality is True
    assert len(material_result.candidates) == 1
    candidate = material_result.candidates[0]
    assert candidate.outcome == "Recommended"
    assert result.governance_standing == "HUMAN_APPROVAL_REQUIRED"
    assert result.governance_record_identifier is not None


@pytest.mark.parametrize(
    ("severity", "revenue_usd", "qualified", "capacity"),
    [
        ("Moderate", "12000000", "true", "true"),  # not high-severity
        ("Severe", "5000000", "true", "true"),  # not material
        ("Severe", "12000000", "false", "true"),  # not qualified
        ("Severe", "12000000", "true", "false"),  # insufficient capacity
    ],
)
def test_any_known_false_condition_yields_rejected(
    migrated_engine: Engine, severity: str, revenue_usd: str, qualified: str, capacity: str
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        ids = _build_scenario(
            session,
            tenant_id,
            severity=severity,
            revenue_usd=revenue_usd,
            alternate_qualified=qualified,
            alternate_capacity=capacity,
        )

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=ids["supplier"])
    )

    candidate = result.materials[0].candidates[0]
    assert candidate.outcome == "Rejected"
    assert result.governance_standing == "HUMAN_APPROVAL_REQUIRED"


@pytest.mark.parametrize(
    "missing",
    ["severity", "revenue_usd", "qualified", "capacity"],
)
def test_unknown_condition_yields_no_record_not_rejected(
    migrated_engine: Engine, missing: str
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    kwargs: dict[str, str | None] = {
        "severity": "Severe",
        "revenue_usd": "12000000",
        "alternate_qualified": "true",
        "alternate_capacity": "true",
    }
    key = (
        "alternate_qualified"
        if missing == "qualified"
        else ("alternate_capacity" if missing == "capacity" else missing)
    )
    kwargs[key] = None
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        ids = _build_scenario(session, tenant_id, **kwargs)

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=ids["supplier"])
    )

    candidate = result.materials[0].candidates[0]
    assert candidate.outcome is None
    assert candidate.decision_record_identifier is None
    # No decision was recorded anywhere in this evaluation -> no governance record either.
    assert result.governance_standing is None
    assert result.governance_record_identifier is None


@pytest.mark.parametrize(
    ("revenue_usd", "expected_materiality"),
    [
        ("9999999", False),
        ("10000000", False),
        ("10000001", True),
    ],
)
def test_materiality_boundary_semantics(
    migrated_engine: Engine, revenue_usd: str, expected_materiality: bool
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        ids = _build_scenario(session, tenant_id, revenue_usd=revenue_usd)

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=ids["supplier"])
    )

    assert result.materials[0].revenue_materiality is expected_materiality
    if not expected_materiality:
        assert result.materials[0].candidates[0].outcome == "Rejected"


def test_candidate_cost_never_affects_materiality_or_recommendation(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    tenant_id_high = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        low_cost_ids = _build_scenario(session, tenant_id, alternate_cost="100")
        high_cost_ids = _build_scenario(session, tenant_id_high, alternate_cost="50000000")

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    low_cost_result = service.evaluate(
        _principal(tenant_id),
        SupplyChainImpactEvaluateRequest(supplier_entity_id=low_cost_ids["supplier"]),
    )
    high_cost_result = service.evaluate(
        _principal(tenant_id_high),
        SupplyChainImpactEvaluateRequest(supplier_entity_id=high_cost_ids["supplier"]),
    )

    assert low_cost_result.materials[0].revenue_materiality is True
    assert high_cost_result.materials[0].revenue_materiality is True
    assert low_cost_result.materials[0].candidates[0].outcome == "Recommended"
    assert high_cost_result.materials[0].candidates[0].outcome == "Recommended"


@pytest.mark.parametrize("lead_time_days", ["30", "90", "180"])
def test_lead_time_never_independently_changes_recommendation(
    migrated_engine: Engine, lead_time_days: str
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        ids = _build_scenario(session, tenant_id, alternate_lead_time=lead_time_days)

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=ids["supplier"])
    )

    assert result.materials[0].candidates[0].outcome == "Recommended"


def test_zero_alternates_is_known_rejected_not_unknown(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        source_system_id = _seed_source_system(session, tenant_id)
        supplier = _entity(
            session, tenant_id=tenant_id, name=f"SUP-{uuid4()}", type_name="Supplier"
        )
        material = _entity(
            session, tenant_id=tenant_id, name=f"MAT-{uuid4()}", type_name="Material"
        )
        risk_event = _entity(
            session, tenant_id=tenant_id, name=f"RISK-{uuid4()}", type_name="Risk Event"
        )
        region = _entity(session, tenant_id=tenant_id, name=f"REG-{uuid4()}", type_name="Region")
        _relate(
            session, tenant_id=tenant_id, type_name="supplies", from_id=supplier, to_id=material
        )
        _relate(session, tenant_id=tenant_id, type_name="locatedIn", from_id=supplier, to_id=region)
        _relate(
            session, tenant_id=tenant_id, type_name="exposedTo", from_id=region, to_id=risk_event
        )
        _assert_literal(
            session,
            subject_entity_id=risk_event,
            predicate="severity",
            object_value="Severe",
            source_system_id=source_system_id,
        )
        # No Alternate Supplier entity exists in this tenant at all.
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=supplier)
    )

    material_result = result.materials[0]
    assert len(material_result.candidates) == 1
    assert material_result.candidates[0].alternate_supplier_entity_id is None
    assert material_result.candidates[0].outcome == "Rejected"
    assert result.governance_standing == "HUMAN_APPROVAL_REQUIRED"


def test_nonexistent_supplier_fails_closed(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    with pytest.raises(ValidationException):
        service.evaluate(
            _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=uuid4())
        )


def test_request_contract_carries_no_client_authoritative_decision_facts() -> None:
    """Merged clarification Amendment R / Part 21: the request may identify
    only the evaluation target. Structurally proven, not just by
    convention: the request dataclass has exactly one field."""
    import dataclasses

    fields = dataclasses.fields(SupplyChainImpactEvaluateRequest)
    assert {field.name for field in fields} == {"supplier_entity_id"}


def test_no_traversal_result_is_persisted_as_a_new_canonical_artifact() -> None:
    """CDD-015 §28 acceptance criterion 1."""
    import ast
    from pathlib import Path

    source = Path(
        Path(__file__).parents[1] / "application" / "supply_chain_impact_api.py"
    ).read_text()
    tree = ast.parse(source)
    class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    forbidden_suffixes = ("ORM", "Model")
    persistence_looking_classes = {
        name
        for name in class_names
        if any(name.endswith(suffix) for suffix in forbidden_suffixes)
        and name not in {"SupplyChainImpactEvaluationResult", "MaterialEvaluationResult"}
    }
    assert not persistence_looking_classes
