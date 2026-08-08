import hashlib
import json
import re
from pathlib import Path

from app.infrastructure.persistence.metadata import canonical_metadata

MIGRATIONS = Path("app/infrastructure/persistence/migrations")
PHYSICAL_MODEL = Path("../architecture/released/v1.1/ECOM_Physical_Data_Model_v1_3.sql")
CANONICAL_MIGRATION = MIGRATIONS / "canonical_v1_3.sql"
TRACEABILITY = Path("../docs/persistence/traceability/PERSISTENCE-TRACEABILITY-v1.3.json")


def _physical_tables(sql: str) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for table, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", sql, re.DOTALL):
        tables[table] = {
            match.group(1)
            for line in body.splitlines()
            if (match := re.match(r"\s*(\w+)\s+(?:UUID|VARCHAR|TIMESTAMPTZ|INTEGER|\w+_t)", line))
        }
    return tables


def test_orm_tables_and_columns_match_frozen_physical_model() -> None:
    expected = _physical_tables(PHYSICAL_MODEL.read_text())
    actual = {
        table_name: {column.name for column in table.columns}
        for table_name, table in canonical_metadata.tables.items()
        if table_name in expected
    }
    assert actual == expected
    assert len(actual) == 32
    assert sum(len(columns) for columns in actual.values()) == 370


def test_indexes_match_frozen_physical_model() -> None:
    sql = PHYSICAL_MODEL.read_text()
    expected = set(re.findall(r"CREATE INDEX (\w+) ON", sql))
    actual = {
        index.name
        for table_name, table in canonical_metadata.tables.items()
        if table_name in _physical_tables(sql)
        for index in table.indexes
        if index.name is not None
    }
    assert actual == expected


def test_traceability_covers_every_physical_column() -> None:
    manifest = json.loads(TRACEABILITY.read_text())
    assert manifest["schema_source"] == (
        "architecture/released/v1.1/ECOM_Physical_Data_Model_v1_3.sql"
    )
    assert manifest["schema_sha256"] == hashlib.sha256(PHYSICAL_MODEL.read_bytes()).hexdigest()
    assert manifest["tables"] == 32
    assert manifest["columns"] == 370
    assert manifest["missing_ead_traces"] == []
    traced = {(item["table"], item["column"]) for item in manifest["column_traceability"]}
    expected = {
        (table_name, column.name)
        for table_name, table in canonical_metadata.tables.items()
        if table_name in _physical_tables(PHYSICAL_MODEL.read_text())
        for column in table.columns
    }
    assert traced == expected


def test_canonical_migration_matches_frozen_physical_model_byte_for_byte() -> None:
    assert CANONICAL_MIGRATION.read_bytes() == PHYSICAL_MODEL.read_bytes()
