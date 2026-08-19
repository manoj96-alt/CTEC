"""Gate F cardinality tests (CDD-015 §16, §28 acceptance criterion 3, §35):
the multi-material/multi-candidate case. Per-pair facts via
`institutional_relationship_assertions` do not collide; all
`decision_evaluation_records` for one evaluation reference the same
`decision_evaluations` group; exactly one `governance_evaluation_records`
row exists per group.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

from sqlalchemy import Engine, func, select
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
from app.infrastructure.persistence.decision_repository import DecisionEvaluationRepositoryImpl
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.governance_evaluation import GovernanceEvaluationORM
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.institutional_relationship_assertion import (
    InstitutionalRelationshipAssertions,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.ontology_seed import OntologySeeder

NOW = datetime(2026, 1, 1, tzinfo=UTC)
POLICY = GateFPolicyConfiguration()


def _tenant() -> str:
    return f"gate-f-cardinality-{uuid4()}"


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


def test_multi_material_multi_candidate_cardinality(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        source_system_id = _seed_source_system(session, tenant_id)

        supplier = _entity(
            session, tenant_id=tenant_id, name=f"SUP-{uuid4()}", type_name="Supplier"
        )
        material_1 = _entity(
            session, tenant_id=tenant_id, name=f"MAT1-{uuid4()}", type_name="Material"
        )
        material_2 = _entity(
            session, tenant_id=tenant_id, name=f"MAT2-{uuid4()}", type_name="Material"
        )
        region = _entity(session, tenant_id=tenant_id, name=f"REG-{uuid4()}", type_name="Region")
        risk_event = _entity(
            session, tenant_id=tenant_id, name=f"RISK-{uuid4()}", type_name="Risk Event"
        )
        _relate(
            session, tenant_id=tenant_id, type_name="supplies", from_id=supplier, to_id=material_1
        )
        _relate(
            session, tenant_id=tenant_id, type_name="supplies", from_id=supplier, to_id=material_2
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

        alt_1 = _entity(
            session, tenant_id=tenant_id, name=f"ALT1-{uuid4()}", type_name="Alternate Supplier"
        )
        _assert_literal(
            session,
            subject_entity_id=alt_1,
            predicate="qualification",
            object_value="true",
            source_system_id=source_system_id,
        )
        _assert_literal(
            session,
            subject_entity_id=alt_1,
            predicate="capacity",
            object_value="true",
            source_system_id=source_system_id,
        )
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=supplier)
    )

    # No Revenue Exposure was set up -> revenue materiality is Unknown for
    # both materials, so no decision_evaluation_records are produced (§16
    # item 6 absence precedent), and no governance record is produced.
    assert len(result.materials) == 2
    for material_result in result.materials:
        assert material_result.revenue_materiality is None
        assert material_result.candidates[0].outcome is None
    assert result.governance_standing is None

    with factory() as session:
        repository = DecisionEvaluationRepositoryImpl(session)
        records = repository.records_for_group(result.decision_evaluation_id, tenant_id=tenant_id)
        assert len(records) == 0

        # candidateFor relationships were still created (KRM's job), one
        # per (material, candidate) pair, each with its own attached
        # assertions -- non-colliding.
        relationships = session.scalars(
            select(InstitutionalRelationship).where(
                InstitutionalRelationship.from_entity_id == alt_1,
            )
        ).all()
        assert len(relationships) == 2
        assert {r.to_entity_id for r in relationships} == {material_1, material_2}
        for relationship in relationships:
            attached = session.scalars(
                select(InstitutionalRelationshipAssertions.assertion_id).where(
                    InstitutionalRelationshipAssertions.institutional_relationship_id
                    == relationship.institutional_relationship_id
                )
            ).all()
            assert len(attached) == 2  # qualification + capacity


def test_multi_material_multi_candidate_with_full_evidence_cardinality(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        source_system_id = _seed_source_system(session, tenant_id)

        supplier = _entity(
            session, tenant_id=tenant_id, name=f"SUP-{uuid4()}", type_name="Supplier"
        )
        material_1 = _entity(
            session, tenant_id=tenant_id, name=f"MAT1-{uuid4()}", type_name="Material"
        )
        material_2 = _entity(
            session, tenant_id=tenant_id, name=f"MAT2-{uuid4()}", type_name="Material"
        )
        bom_1 = _entity(session, tenant_id=tenant_id, name=f"BOM1-{uuid4()}", type_name="BOM")
        bom_2 = _entity(session, tenant_id=tenant_id, name=f"BOM2-{uuid4()}", type_name="BOM")
        product_1 = _entity(
            session, tenant_id=tenant_id, name=f"PROD1-{uuid4()}", type_name="Product"
        )
        product_2 = _entity(
            session, tenant_id=tenant_id, name=f"PROD2-{uuid4()}", type_name="Product"
        )
        revenue_1 = _entity(
            session, tenant_id=tenant_id, name=f"REV1-{uuid4()}", type_name="Revenue Exposure"
        )
        revenue_2 = _entity(
            session, tenant_id=tenant_id, name=f"REV2-{uuid4()}", type_name="Revenue Exposure"
        )
        region = _entity(session, tenant_id=tenant_id, name=f"REG-{uuid4()}", type_name="Region")
        risk_event = _entity(
            session, tenant_id=tenant_id, name=f"RISK-{uuid4()}", type_name="Risk Event"
        )

        _relate(
            session, tenant_id=tenant_id, type_name="supplies", from_id=supplier, to_id=material_1
        )
        _relate(
            session, tenant_id=tenant_id, type_name="supplies", from_id=supplier, to_id=material_2
        )
        _relate(session, tenant_id=tenant_id, type_name="usedIn", from_id=material_1, to_id=bom_1)
        _relate(session, tenant_id=tenant_id, type_name="usedIn", from_id=material_2, to_id=bom_2)
        _relate(session, tenant_id=tenant_id, type_name="defines", from_id=bom_1, to_id=product_1)
        _relate(session, tenant_id=tenant_id, type_name="defines", from_id=bom_2, to_id=product_2)
        _relate(
            session,
            tenant_id=tenant_id,
            type_name="generatesRevenue",
            from_id=product_1,
            to_id=revenue_1,
        )
        _relate(
            session,
            tenant_id=tenant_id,
            type_name="generatesRevenue",
            from_id=product_2,
            to_id=revenue_2,
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
        _assert_literal(
            session,
            subject_entity_id=revenue_1,
            predicate="annualRevenueUsd",
            object_value="12000000",
            source_system_id=source_system_id,
        )
        _assert_literal(
            session,
            subject_entity_id=revenue_2,
            predicate="annualRevenueUsd",
            object_value="12000000",
            source_system_id=source_system_id,
        )

        alt_1 = _entity(
            session, tenant_id=tenant_id, name=f"ALT1-{uuid4()}", type_name="Alternate Supplier"
        )
        alt_2 = _entity(
            session, tenant_id=tenant_id, name=f"ALT2-{uuid4()}", type_name="Alternate Supplier"
        )
        for alt in (alt_1, alt_2):
            _assert_literal(
                session,
                subject_entity_id=alt,
                predicate="qualification",
                object_value="true",
                source_system_id=source_system_id,
            )
            _assert_literal(
                session,
                subject_entity_id=alt,
                predicate="capacity",
                object_value="true",
                source_system_id=source_system_id,
            )
        session.commit()

    service = SupplyChainImpactApiService(factory, policy=POLICY)
    result = service.evaluate(
        _principal(tenant_id), SupplyChainImpactEvaluateRequest(supplier_entity_id=supplier)
    )

    # 2 materials x 2 candidates = 4 recommended units.
    all_outcomes = [c.outcome for m in result.materials for c in m.candidates]
    assert len(all_outcomes) == 4
    assert all(outcome == "Recommended" for outcome in all_outcomes)

    with factory() as session:
        repository = DecisionEvaluationRepositoryImpl(session)
        group = repository.group_by_id(result.decision_evaluation_id, tenant_id=tenant_id)
        assert group is not None
        records = repository.records_for_group(result.decision_evaluation_id, tenant_id=tenant_id)
        assert len(records) == 4

        governance_count = session.scalar(
            select(func.count())
            .select_from(GovernanceEvaluationORM)
            .where(
                GovernanceEvaluationORM.governed_record_reference == result.decision_evaluation_id
            )
        )
        assert governance_count == 1
