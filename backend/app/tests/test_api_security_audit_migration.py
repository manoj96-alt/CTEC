from importlib import import_module
from pathlib import Path


def test_migration_lineage_and_append_only_controls() -> None:
    migration = import_module(
        "app.infrastructure.persistence.migrations.versions.0009_api_security_audit"
    )
    assert migration.revision == "0009_api_security_audit"
    assert migration.down_revision == "0008_durable_execution"
    assert migration.__file__ is not None
    text = Path(migration.__file__).read_text()
    assert "api_security_audit_immutable" in text
    assert "ctec.audit_disposition" in text
