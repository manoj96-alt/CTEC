"""Unit-level proof of migration 0012_ir_tenant_ownership's
_resolve_pre_existing_row_tenants() defensive guard against an
institutional_relationships row whose from_entity_id/to_entity_id does not
resolve to any enterprise_entities row (RFC-016 §5a "Case D").

Uses an isolated in-memory SQLite database rather than the shared
PostgreSQL integration database, for the same reason
test_entity_resolution_steward_provenance_guard.py does: migration 0011's
own schema already enforces a plain foreign key on both
from_entity_id/to_entity_id, so this state cannot be constructed against a
real, unbypassed PostgreSQL database at all -- there is no real row to seed
the Postgres integration suite with. SQLite does not enforce foreign keys
unless a session explicitly opts in (never done here), so it can hold the
row shape this defensive guard exists for, entirely in isolation, with zero
risk to -- and zero interaction with -- any shared fixture.

Cases A, B, C, E, and F are proven against real, unbypassed PostgreSQL in
test_institutional_relationship_tenant_migration_postgres.py.
"""

import uuid
from importlib import import_module

from sqlalchemy import Engine, create_engine, text

migration = import_module(
    "app.infrastructure.persistence.migrations.versions"
    ".0012_institutional_relationship_tenant_ownership"
)


def _isolated_engine() -> Engine:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE enterprise_entities ("
                "enterprise_entity_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE institutional_relationships ("
                "institutional_relationship_id TEXT PRIMARY KEY, "
                "from_entity_id TEXT NOT NULL, to_entity_id TEXT NOT NULL)"
            )
        )
    return engine


def test_migration_module_identity() -> None:
    assert migration.revision == "0012_ir_tenant_ownership"
    assert migration.down_revision == "0011_erm_tenant_and_evidence"


def test_unresolvable_from_entity_id_fails_closed_with_no_tenant_guessed() -> None:
    engine = _isolated_engine()
    tenant_id = f"tenant-{uuid.uuid4()}"
    row_id = uuid.uuid4()
    to_entity_id = uuid.uuid4()
    missing_from_entity_id = uuid.uuid4()

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO enterprise_entities (enterprise_entity_id, tenant_id) VALUES (:id, :tenant_id)"
            ),
            {"id": str(to_entity_id), "tenant_id": tenant_id},
        )
        # from_entity_id deliberately references no row -- only reachable
        # here, since a real FK would reject this insert outright.
        conn.execute(
            text(
                "INSERT INTO institutional_relationships "
                "(institutional_relationship_id, from_entity_id, to_entity_id) VALUES (:id, :from_id, :to_id)"
            ),
            {"id": str(row_id), "from_id": str(missing_from_entity_id), "to_id": str(to_entity_id)},
        )

    with engine.connect() as conn:
        try:
            migration._resolve_pre_existing_row_tenants(conn)
            raised = False
        except migration.InstitutionalRelationshipTenantResolutionError as exc:
            raised = True
            message = str(exc)

    assert raised
    assert str(row_id) in message
    assert "from_entity_id" in message
    assert "does not resolve" in message
    # No tenant was invented anywhere in the failure message.
    assert tenant_id not in message


def test_unresolvable_to_entity_id_fails_closed() -> None:
    engine = _isolated_engine()
    tenant_id = f"tenant-{uuid.uuid4()}"
    row_id = uuid.uuid4()
    from_entity_id = uuid.uuid4()
    missing_to_entity_id = uuid.uuid4()

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO enterprise_entities (enterprise_entity_id, tenant_id) VALUES (:id, :tenant_id)"
            ),
            {"id": str(from_entity_id), "tenant_id": tenant_id},
        )
        conn.execute(
            text(
                "INSERT INTO institutional_relationships "
                "(institutional_relationship_id, from_entity_id, to_entity_id) VALUES (:id, :from_id, :to_id)"
            ),
            {"id": str(row_id), "from_id": str(from_entity_id), "to_id": str(missing_to_entity_id)},
        )

    with engine.connect() as conn:
        try:
            migration._resolve_pre_existing_row_tenants(conn)
            raised = False
        except migration.InstitutionalRelationshipTenantResolutionError as exc:
            raised = True
            message = str(exc)

    assert raised
    assert "to_entity_id" in message
    assert "does not resolve" in message


def test_empty_table_resolves_to_no_rows() -> None:
    engine = _isolated_engine()
    with engine.connect() as conn:
        resolved = migration._resolve_pre_existing_row_tenants(conn)
    assert resolved == {}


def test_same_tenant_endpoints_resolve_deterministically() -> None:
    engine = _isolated_engine()
    tenant_id = f"tenant-{uuid.uuid4()}"
    row_id = uuid.uuid4()
    from_entity_id = uuid.uuid4()
    to_entity_id = uuid.uuid4()

    with engine.begin() as conn:
        for entity_id in (from_entity_id, to_entity_id):
            conn.execute(
                text(
                    "INSERT INTO enterprise_entities (enterprise_entity_id, tenant_id) VALUES (:id, :tenant_id)"
                ),
                {"id": str(entity_id), "tenant_id": tenant_id},
            )
        conn.execute(
            text(
                "INSERT INTO institutional_relationships "
                "(institutional_relationship_id, from_entity_id, to_entity_id) VALUES (:id, :from_id, :to_id)"
            ),
            {"id": str(row_id), "from_id": str(from_entity_id), "to_id": str(to_entity_id)},
        )

    with engine.connect() as conn:
        resolved = migration._resolve_pre_existing_row_tenants(conn)

    assert resolved == {str(row_id): tenant_id}
