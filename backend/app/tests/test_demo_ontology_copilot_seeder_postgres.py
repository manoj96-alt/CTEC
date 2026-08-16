"""Real-PostgreSQL proof that the demo Ask CTEC seeder (Gate D) persists a
genuine, tenant-scoped, three-hop supply chain via institutional_relationships,
and is idempotent."""

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.infrastructure.persistence.demo_ontology_copilot_seeder import (
    SUPPLIER_NAME,
    DemoOntologyCopilotSeeder,
)
from app.infrastructure.persistence.institutional_relationship_store import (
    InstitutionalRelationshipStore,
)
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)


def test_seed_creates_a_real_two_product_supply_chain(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        summary = DemoOntologyCopilotSeeder(session).seed()

    assert summary.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
    assert summary.supplier.created is True
    assert len(summary.products) == 2
    assert summary.relationships_created == 6

    with Session(migrated_engine) as session:
        store = InstitutionalRelationshipStore(session)
        matches = store.find_enterprise_entities_by_name(BOOTSTRAP_DEMO_TENANT_ID, SUPPLIER_NAME)
    assert len(matches) == 1
    assert matches[0].entity_name == SUPPLIER_NAME
    assert matches[0].entity_type_name == "Supplier"


def test_seed_is_idempotent(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        DemoOntologyCopilotSeeder(session).seed()

    with Session(migrated_engine) as session:
        entity_count_before = session.execute(
            select(func.count())
            .select_from(EnterpriseEntity)
            .where(EnterpriseEntity.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        ).scalar_one()
        relationship_count_before = session.execute(
            select(func.count())
            .select_from(InstitutionalRelationship)
            .where(InstitutionalRelationship.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        ).scalar_one()

    with Session(migrated_engine) as session, session.begin():
        summary = DemoOntologyCopilotSeeder(session).seed()

    assert summary.supplier.created is False
    assert all(product.created is False for product in summary.products)
    assert summary.relationships_created == 0

    with Session(migrated_engine) as session:
        entity_count_after = session.execute(
            select(func.count())
            .select_from(EnterpriseEntity)
            .where(EnterpriseEntity.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        ).scalar_one()
        relationship_count_after = session.execute(
            select(func.count())
            .select_from(InstitutionalRelationship)
            .where(InstitutionalRelationship.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        ).scalar_one()

    assert entity_count_after == entity_count_before
    assert relationship_count_after == relationship_count_before
