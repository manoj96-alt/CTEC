from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.bootstrap import (
    BOOTSTRAP_ENTITY_TYPE,
    BOOTSTRAP_STATUS,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    BOOTSTRAP_SYSTEM_NAME,
    SEED_TIMESTAMP,
    SEED_VERSION,
)
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.session import create_session_factory


def test_frozen_bootstrap_constants() -> None:
    assert BOOTSTRAP_SYSTEM_ENTITY_ID == UUID("00000000-0000-0000-0000-000000000001")
    assert BOOTSTRAP_SYSTEM_NAME == "ECOM Bootstrap System"
    assert BOOTSTRAP_ENTITY_TYPE == "System Actor"
    assert BOOTSTRAP_STATUS == "Active"
    assert SEED_TIMESTAMP == datetime(2026, 1, 1, tzinfo=UTC)
    assert SEED_VERSION == "EDT-001-V3"


def test_initial_migration_creates_exactly_one_bootstrap_entity(
    migrated_engine: object,
) -> None:
    factory = create_session_factory(migrated_engine)  # type: ignore[arg-type]
    with factory() as session:
        entities = session.scalars(
            select(EnterpriseEntity).where(
                EnterpriseEntity.enterprise_entity_id == BOOTSTRAP_SYSTEM_ENTITY_ID
            )
        ).all()
    assert len(entities) == 1
    assert entities[0].enterprise_entity_name == BOOTSTRAP_SYSTEM_NAME
    assert entities[0].created_by == BOOTSTRAP_SYSTEM_ENTITY_ID
