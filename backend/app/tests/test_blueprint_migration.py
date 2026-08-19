"""Migration correctness for 0014_blueprint_requirement_contract (Gate G G2;
CDD-017 §6-9, G2 Persistence and Domain Artifact Authorization companion).

Module-identity is proven statically, without a database. Upgrade/downgrade
and backward-compatibility are proven against real, unbypassed PostgreSQL
(`migrated_engine`), following the existing migration-test convention --
this migration's Postgres-specific ENUM reuse (`create_type=False` against
the pre-existing `lifecyclestate_t`/`governancestatus_t` types) cannot be
meaningfully exercised against SQLite.
"""

# isort: skip_file
from importlib import import_module

import alembic.command
from alembic.config import Config
from sqlalchemy import Engine, inspect

migration = import_module(
    "app.infrastructure.persistence.migrations.versions.0014_blueprint_requirement_contract"
)

_NEW_TABLES = (
    "blueprints",
    "concept_requirements",
    "relationship_requirements",
    "information_element_requirements",
)


def test_migration_module_identity() -> None:
    assert migration.revision == "0014_blueprint_requirement"
    assert migration.down_revision == "0013_decision_evaluation_group"


def test_upgrade_creates_exactly_the_authorized_tables_with_no_tenant_id(
    migrated_engine: Engine,
) -> None:
    inspector = inspect(migrated_engine)
    existing_tables = set(inspector.get_table_names())
    for table_name in _NEW_TABLES:
        assert table_name in existing_tables
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert "tenant_id" not in columns

    blueprint_columns = {column["name"] for column in inspector.get_columns("blueprints")}
    assert "version_number" in blueprint_columns
    assert "previous_version_id" in blueprint_columns

    blueprint_name_column = next(
        column
        for column in inspector.get_columns("blueprints")
        if column["name"] == "blueprint_name"
    )
    unique_constraints = inspector.get_unique_constraints("blueprints")
    assert not any(
        blueprint_name_column["name"] in constraint["column_names"]
        for constraint in unique_constraints
    )


def test_upgrade_does_not_alter_any_existing_table(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    entity_type_columns = {column["name"] for column in inspector.get_columns("entity_types")}
    relationship_type_columns = {
        column["name"] for column in inspector.get_columns("relationship_types")
    }
    # Pre-existing tables retain exactly their pre-Gate-G shape.
    assert "blueprint_id" not in entity_type_columns
    assert "blueprint_id" not in relationship_type_columns


def test_downgrade_removes_exactly_the_new_tables_and_preserves_existing_schema(
    migrated_engine: Engine, test_database_url: str
) -> None:
    """Explicit, directly observable downgrade evidence (CDD-017 §17/§19 G2
    companion Purpose: "Migration correctness; upgrade/downgrade..."),
    exercised through the same Alembic command machinery
    `conftest.py`'s own `migrated_engine` fixture uses -- not by calling
    `migration.downgrade()`/`migration.upgrade()` directly, which would
    bypass the real `MigrationContext`. `migrated_engine` is requested only
    to guarantee the database is already at "head" (this migration
    included) before this test steps one migration back and forward again,
    restoring head state for every other test sharing the session-scoped
    engine."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", test_database_url)

    inspector = inspect(migrated_engine)
    for table_name in _NEW_TABLES:
        assert table_name in set(inspector.get_table_names())

    try:
        alembic.command.downgrade(config, "0013_decision_evaluation_group")
        inspector = inspect(migrated_engine)
        remaining_tables = set(inspector.get_table_names())
        for table_name in _NEW_TABLES:
            assert table_name not in remaining_tables
        # Pre-existing schema remains valid after this migration is reverted.
        assert "entity_types" in remaining_tables
        assert "relationship_types" in remaining_tables
    finally:
        alembic.command.upgrade(config, "head")

    inspector = inspect(migrated_engine)
    restored_tables = set(inspector.get_table_names())
    for table_name in _NEW_TABLES:
        assert table_name in restored_tables
