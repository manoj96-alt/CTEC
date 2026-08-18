"""Gate F tenant isolation tests (CDD-015 §16 item 7, §19, §35): every Gate
F evaluation operates under one trusted tenant context. Cross-tenant
supplier/material/candidate/assertion access is rejected or excluded --
tenant authority is verified at every step, never trusted from client
input.
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
from app.infrastructure.persistence.decision_repository import DecisionEvaluationRepositoryImpl
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


def _tenant(label: str) -> str:
    return f"gate-f-{label}-{uuid4()}"


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


def test_cross_tenant_supplier_is_inaccessible(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_a = _tenant("a")
    tenant_b = _tenant("b")
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        supplier_a = _entity(
            session, tenant_id=tenant_a, name=f"SUP-{uuid4()}", type_name="Supplier"
        )
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    with pytest.raises(ValidationException):
        service.evaluate(
            _principal(tenant_b),
            SupplyChainImpactEvaluateRequest(supplier_entity_id=supplier_a),
        )


def test_cross_tenant_material_is_excluded_from_traversal(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_a = _tenant("a")
    tenant_b = _tenant("b")
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        supplier_a = _entity(
            session, tenant_id=tenant_a, name=f"SUP-{uuid4()}", type_name="Supplier"
        )
        material_b = _entity(
            session, tenant_id=tenant_b, name=f"MAT-{uuid4()}", type_name="Material"
        )
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_a), SupplyChainImpactEvaluateRequest(supplier_entity_id=supplier_a)
    )
    assert material_b not in {m.material_entity_id for m in result.impact.materials}


def test_cross_tenant_alternate_supplier_is_excluded_from_candidate_discovery(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_a = _tenant("a")
    tenant_b = _tenant("b")
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        supplier_a = _entity(
            session, tenant_id=tenant_a, name=f"SUP-{uuid4()}", type_name="Supplier"
        )
        material_a = _entity(
            session, tenant_id=tenant_a, name=f"MAT-{uuid4()}", type_name="Material"
        )
        _relate(
            session, tenant_id=tenant_a, type_name="supplies", from_id=supplier_a, to_id=material_a
        )
        # An Alternate Supplier entity that exists only in tenant_b.
        _entity(session, tenant_id=tenant_b, name=f"ALT-{uuid4()}", type_name="Alternate Supplier")
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_a), SupplyChainImpactEvaluateRequest(supplier_entity_id=supplier_a)
    )

    # tenant_a has zero governed Alternate Supplier entities of its own ->
    # zero-alternate semantics apply, not a leak of tenant_b's candidate.
    material_result = result.materials[0]
    assert material_result.candidates[0].alternate_supplier_entity_id is None


def test_cross_tenant_severity_assertion_is_not_read(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_a = _tenant("a")
    tenant_b = _tenant("b")
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        source_system_b = _seed_source_system(session, tenant_b)

        supplier_a = _entity(
            session, tenant_id=tenant_a, name=f"SUP-{uuid4()}", type_name="Supplier"
        )
        material_a = _entity(
            session, tenant_id=tenant_a, name=f"MAT-{uuid4()}", type_name="Material"
        )
        region_a = _entity(session, tenant_id=tenant_a, name=f"REG-{uuid4()}", type_name="Region")
        risk_event_a = _entity(
            session, tenant_id=tenant_a, name=f"RISK-{uuid4()}", type_name="Risk Event"
        )
        _relate(
            session, tenant_id=tenant_a, type_name="supplies", from_id=supplier_a, to_id=material_a
        )
        _relate(
            session, tenant_id=tenant_a, type_name="locatedIn", from_id=supplier_a, to_id=region_a
        )
        _relate(
            session, tenant_id=tenant_a, type_name="exposedTo", from_id=region_a, to_id=risk_event_a
        )
        # No severity assertion for tenant_a's Risk Event -- only a
        # same-named entity in tenant_b's data would have one, but the
        # traversal itself never crosses tenant_a's graph.
        risk_event_b = _entity(
            session, tenant_id=tenant_b, name=f"RISK-{uuid4()}", type_name="Risk Event"
        )
        _assert_literal(
            session,
            subject_entity_id=risk_event_b,
            predicate="severity",
            object_value="Severe",
            source_system_id=source_system_b,
        )
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_a), SupplyChainImpactEvaluateRequest(supplier_entity_id=supplier_a)
    )

    assert result.materials[0].high_severity_disruption is None


def test_decision_evaluation_group_tenant_scoping_holds_end_to_end(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_a = _tenant("a")
    tenant_b = _tenant("b")
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        supplier_a = _entity(
            session, tenant_id=tenant_a, name=f"SUP-{uuid4()}", type_name="Supplier"
        )
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_a), SupplyChainImpactEvaluateRequest(supplier_entity_id=supplier_a)
    )

    with factory() as session:
        repository = DecisionEvaluationRepositoryImpl(session)
        assert repository.group_by_id(result.decision_evaluation_id, tenant_id=tenant_a) is not None
        assert repository.group_by_id(result.decision_evaluation_id, tenant_id=tenant_b) is None
