"""Real-PostgreSQL proof of RFC-016 §5a pre-existing-row safety for migration
0012_ir_tenant_ownership, plus the resulting composite-FK tenant isolation.

Cases A, B, C, E, F below are all reachable through the real, unbypassed
schema at migration 0011 (the state immediately before 0012) and are
exercised here directly. Case D (an institutional_relationships row whose
from_entity_id/to_entity_id does not resolve to any enterprise_entities row)
is NOT reachable this way: migration 0011's own schema already enforces a
plain foreign key on both columns, so no such row can ever exist in a real
database. That defensive branch of the migration's resolution logic is
proven in isolation instead, in
test_institutional_relationship_tenant_migration_unit.py, exactly mirroring
the precedent set by test_entity_resolution_steward_provenance_guard.py for
the same kind of FK-protected, structurally-unreachable state.

This module manipulates schema state directly (downgrades to 0011, attempts
the upgrade under controlled pre-conditions) and therefore does NOT use the
shared session-scoped migrated_engine fixture from conftest.py -- doing so
would leave that shared fixture's database in an inconsistent state for
every other test module in the same pytest session. The pre_0012_engine
fixture below guarantees the database is restored to head after every test
in this module, regardless of outcome, so every other test module sees the
schema state it expects.
"""

# isort: skip_file
import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_ENTITY_TYPE_ID,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
PRE_MIGRATION_REVISION = "0011_erm_tenant_and_evidence"


def _tenant(label: str) -> str:
    return f"{label}-{uuid.uuid4()}"


@pytest.fixture()
def pre_0012_engine(test_database_url: str) -> Generator[tuple[Engine, Config], None, None]:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", test_database_url)
    previous = os.environ.get("CTEC_DATABASE_URL")
    os.environ["CTEC_DATABASE_URL"] = test_database_url
    alembic.command.downgrade(config, "base")
    alembic.command.upgrade(config, PRE_MIGRATION_REVISION)
    engine = create_engine(test_database_url)
    try:
        yield engine, config
    finally:
        engine.dispose()
        alembic.command.downgrade(config, "base")
        alembic.command.upgrade(config, "head")
        if previous is None:
            os.environ.pop("CTEC_DATABASE_URL", None)
        else:
            os.environ["CTEC_DATABASE_URL"] = previous


def _insert_relationship_type(conn: Connection, *, name: str) -> uuid.UUID:
    type_id = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO relationship_types
                (relationship_type_id, relationship_type_name, lifecycle_state,
                 effective_from, governance_status, created_by, created_on)
            VALUES
                (:id, :name, 'Active', :now, 'Approved', :created_by, :now)
            """
        ),
        {"id": type_id, "name": name, "now": NOW, "created_by": BOOTSTRAP_SYSTEM_ENTITY_ID},
    )
    return type_id


def _insert_enterprise_entity(conn: Connection, *, tenant_id: str, name: str) -> uuid.UUID:
    entity_id = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO enterprise_entities
                (enterprise_entity_id, tenant_id, enterprise_entity_name, lifecycle_state,
                 effective_from, governance_status, created_by, created_on,
                 entity_type_id, business_domain_id)
            VALUES
                (:id, :tenant_id, :name, 'Active', :now, 'Approved', :created_by, :now,
                 :entity_type_id, :business_domain_id)
            """
        ),
        {
            "id": entity_id,
            "tenant_id": tenant_id,
            "name": name,
            "now": NOW,
            "created_by": BOOTSTRAP_SYSTEM_ENTITY_ID,
            "entity_type_id": BOOTSTRAP_ENTITY_TYPE_ID,
            "business_domain_id": BOOTSTRAP_BUSINESS_DOMAIN_ID,
        },
    )
    return entity_id


def _insert_institutional_relationship(
    conn: Connection,
    *,
    name: str,
    relationship_type_id: uuid.UUID,
    from_entity_id: uuid.UUID,
    to_entity_id: uuid.UUID,
) -> uuid.UUID:
    row_id = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO institutional_relationships
                (institutional_relationship_id, institutional_relationship_name, lifecycle_state,
                 effective_from, governance_status, created_by, created_on,
                 relationship_type_id, from_entity_id, to_entity_id)
            VALUES
                (:id, :name, 'Active', :now, 'Approved', :created_by, :now,
                 :relationship_type_id, :from_entity_id, :to_entity_id)
            """
        ),
        {
            "id": row_id,
            "name": name,
            "now": NOW,
            "created_by": BOOTSTRAP_SYSTEM_ENTITY_ID,
            "relationship_type_id": relationship_type_id,
            "from_entity_id": from_entity_id,
            "to_entity_id": to_entity_id,
        },
    )
    return row_id


def _has_tenant_id_column(engine: Engine) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'institutional_relationships' AND column_name = 'tenant_id'"
            )
        ).first()
    return result is not None


def test_case_a_empty_table_migration_succeeds(pre_0012_engine: tuple[Engine, Config]) -> None:
    engine, config = pre_0012_engine
    assert not _has_tenant_id_column(engine)

    alembic.command.upgrade(config, "head")

    assert _has_tenant_id_column(engine)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM institutional_relationships")).scalar_one()
    assert count == 0


def test_case_b_same_tenant_endpoints_resolve_and_migration_succeeds(
    pre_0012_engine: tuple[Engine, Config],
) -> None:
    engine, config = pre_0012_engine
    tenant_id = _tenant("case-b")

    with engine.begin() as conn:
        relationship_type_id = _insert_relationship_type(conn, name=f"supplies-{uuid.uuid4()}")
        from_entity_id = _insert_enterprise_entity(
            conn, tenant_id=tenant_id, name=f"Supplier-{uuid.uuid4()}"
        )
        to_entity_id = _insert_enterprise_entity(
            conn, tenant_id=tenant_id, name=f"Material-{uuid.uuid4()}"
        )
        row_id = _insert_institutional_relationship(
            conn,
            name=f"rel-{uuid.uuid4()}",
            relationship_type_id=relationship_type_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
        )

    alembic.command.upgrade(config, "head")

    with engine.connect() as conn:
        resolved_tenant = conn.execute(
            text(
                "SELECT tenant_id FROM institutional_relationships "
                "WHERE institutional_relationship_id = :id"
            ),
            {"id": row_id},
        ).scalar_one()
    assert resolved_tenant == tenant_id


def test_case_c_cross_tenant_endpoints_fail_closed_before_any_schema_change(
    pre_0012_engine: tuple[Engine, Config],
) -> None:
    engine, config = pre_0012_engine
    tenant_a = _tenant("case-c-a")
    tenant_b = _tenant("case-c-b")

    with engine.begin() as conn:
        relationship_type_id = _insert_relationship_type(conn, name=f"supplies-{uuid.uuid4()}")
        from_entity_id = _insert_enterprise_entity(
            conn, tenant_id=tenant_a, name=f"Supplier-{uuid.uuid4()}"
        )
        to_entity_id = _insert_enterprise_entity(
            conn, tenant_id=tenant_b, name=f"Material-{uuid.uuid4()}"
        )
        _insert_institutional_relationship(
            conn,
            name=f"rel-{uuid.uuid4()}",
            relationship_type_id=relationship_type_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
        )

    with pytest.raises(Exception, match="resolve different tenants|could not be deterministically"):
        alembic.command.upgrade(config, "head")

    # Fail-closed: no schema change was applied, and the migration did not
    # advance -- confirmed two ways, not just by the raised exception.
    assert not _has_tenant_id_column(engine)
    with engine.connect() as conn:
        current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert current == PRE_MIGRATION_REVISION


def test_case_e_and_f_post_migration_composite_fk_enforces_tenant_isolation(
    pre_0012_engine: tuple[Engine, Config],
) -> None:
    engine, config = pre_0012_engine
    tenant_a = _tenant("case-ef-a")
    tenant_b = _tenant("case-ef-b")

    with engine.begin() as conn:
        relationship_type_id = _insert_relationship_type(conn, name=f"supplies-{uuid.uuid4()}")
        tenant_a_entity_1 = _insert_enterprise_entity(
            conn, tenant_id=tenant_a, name=f"Supplier-{uuid.uuid4()}"
        )
        tenant_a_entity_2 = _insert_enterprise_entity(
            conn, tenant_id=tenant_a, name=f"Material-{uuid.uuid4()}"
        )
        tenant_b_entity = _insert_enterprise_entity(
            conn, tenant_id=tenant_b, name=f"Material-{uuid.uuid4()}"
        )

    alembic.command.upgrade(config, "head")
    assert _has_tenant_id_column(engine)

    # Case E: a row claiming tenant A, whose to_entity_id actually belongs to
    # tenant B -- the composite FK must reject it.
    with engine.connect() as conn, conn.begin(), pytest.raises(IntegrityError):
        conn.execute(
            text(
                """
                INSERT INTO institutional_relationships
                    (institutional_relationship_id, tenant_id, institutional_relationship_name,
                     lifecycle_state, effective_from, governance_status, created_by, created_on,
                     relationship_type_id, from_entity_id, to_entity_id)
                VALUES
                    (:id, :tenant_id, :name, 'Active', :now, 'Approved', :created_by, :now,
                     :relationship_type_id, :from_entity_id, :to_entity_id)
                """
            ),
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_a,
                "name": f"rel-{uuid.uuid4()}",
                "now": NOW,
                "created_by": BOOTSTRAP_SYSTEM_ENTITY_ID,
                "relationship_type_id": relationship_type_id,
                "from_entity_id": tenant_a_entity_1,
                "to_entity_id": tenant_b_entity,
            },
        )

    # Case F: a genuinely same-tenant row is accepted.
    with engine.begin() as conn:
        accepted_id = uuid.uuid4()
        conn.execute(
            text(
                """
                INSERT INTO institutional_relationships
                    (institutional_relationship_id, tenant_id, institutional_relationship_name,
                     lifecycle_state, effective_from, governance_status, created_by, created_on,
                     relationship_type_id, from_entity_id, to_entity_id)
                VALUES
                    (:id, :tenant_id, :name, 'Active', :now, 'Approved', :created_by, :now,
                     :relationship_type_id, :from_entity_id, :to_entity_id)
                """
            ),
            {
                "id": accepted_id,
                "tenant_id": tenant_a,
                "name": f"rel-{uuid.uuid4()}",
                "now": NOW,
                "created_by": BOOTSTRAP_SYSTEM_ENTITY_ID,
                "relationship_type_id": relationship_type_id,
                "from_entity_id": tenant_a_entity_1,
                "to_entity_id": tenant_a_entity_2,
            },
        )
    with engine.connect() as conn:
        count = conn.execute(
            text(
                "SELECT count(*) FROM institutional_relationships WHERE institutional_relationship_id = :id"
            ),
            {"id": accepted_id},
        ).scalar_one()
    assert count == 1
