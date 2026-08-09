from importlib import import_module


def test_migration_lineage() -> None:
    migration = import_module(
        "app.infrastructure.persistence.migrations.versions.0008_durable_execution"
    )
    assert migration.revision == "0008_durable_execution"
    assert migration.down_revision == "0007_governance_eval"
