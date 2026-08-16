import hashlib
import json
import re
from pathlib import Path

from app.infrastructure.persistence.metadata import canonical_metadata

MIGRATIONS = Path("app/infrastructure/persistence/migrations")

# The frozen v1.1 release of the original v1.3 physical model. Immutable
# forever: this is what migration 0001's embedded canonical_v1_3.sql
# actually executed, and it must never be repointed regardless of later
# physical-model releases.
FROZEN_V1_3_PHYSICAL_MODEL = Path("../architecture/released/v1.1/ECOM_Physical_Data_Model_v1_3.sql")
CANONICAL_MIGRATION = MIGRATIONS / "canonical_v1_3.sql"

# The current authoritative physical model (Gate D1 / RFC-016). Its
# canonical section (before CANONICAL_BOUNDARY_MARKER) is the ORM's current
# 32-table/374-column authority; its bounded-extension section (after the
# marker) governs the seven CDD-012/CDD-013 extension tables separately.
CURRENT_PHYSICAL_MODEL = Path("../architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql")
CANONICAL_BOUNDARY_MARKER = (
    "-- ---------- BOUNDED NON-CANONICAL EXTENSIONS (CDD-012, CDD-013) ----------"
)
TRACEABILITY = Path("../docs/persistence/traceability/PERSISTENCE-TRACEABILITY-v1.7.json")

CANONICAL_TABLE_COUNT = 32
CANONICAL_COLUMN_COUNT = 374
BOUNDED_EXTENSION_TABLE_COUNT = 7


def _physical_tables(sql: str) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for table, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", sql, re.DOTALL):
        tables[table] = {
            match.group(1)
            for line in body.splitlines()
            if (match := re.match(r"\s*(\w+)\s+(?:UUID|VARCHAR|TIMESTAMPTZ|INTEGER|\w+_t)", line))
        }
    return tables


def _canonical_and_bounded_sections(sql: str) -> tuple[str, str]:
    """Split the current physical model at its explicit boundary marker.
    Fails closed (no silent ignore list) if the marker is missing, duplicated,
    or if any table ends up on the wrong side of it."""
    occurrences = sql.count(CANONICAL_BOUNDARY_MARKER)
    if occurrences != 1:
        raise AssertionError(
            f"expected exactly one canonical/bounded-extension boundary marker, found {occurrences}"
        )
    boundary_idx = sql.index(CANONICAL_BOUNDARY_MARKER)
    canonical_sql = sql[:boundary_idx]
    bounded_sql = sql[boundary_idx:]

    canonical_tables = _physical_tables(canonical_sql)
    bounded_tables = _physical_tables(bounded_sql)
    overlap = set(canonical_tables) & set(bounded_tables)
    if overlap:
        raise AssertionError(f"tables appear on both sides of the boundary marker: {overlap}")
    if len(canonical_tables) != CANONICAL_TABLE_COUNT:
        raise AssertionError(
            f"expected {CANONICAL_TABLE_COUNT} canonical tables before the marker, "
            f"found {len(canonical_tables)}: {sorted(canonical_tables)}"
        )
    if len(bounded_tables) != BOUNDED_EXTENSION_TABLE_COUNT:
        raise AssertionError(
            f"expected {BOUNDED_EXTENSION_TABLE_COUNT} bounded-extension tables after the "
            f"marker, found {len(bounded_tables)}: {sorted(bounded_tables)}"
        )
    total_create_table_statements = len(re.findall(r"CREATE TABLE \w+ \(", sql))
    if total_create_table_statements != CANONICAL_TABLE_COUNT + BOUNDED_EXTENSION_TABLE_COUNT:
        raise AssertionError(
            f"expected {CANONICAL_TABLE_COUNT + BOUNDED_EXTENSION_TABLE_COUNT} total CREATE TABLE "
            f"statements, found {total_create_table_statements} (duplicate table definitions present)"
        )
    return canonical_sql, bounded_sql


def test_orm_tables_and_columns_match_frozen_physical_model() -> None:
    canonical_sql, _bounded_sql = _canonical_and_bounded_sections(
        CURRENT_PHYSICAL_MODEL.read_text()
    )
    expected = _physical_tables(canonical_sql)
    actual = {
        table_name: {column.name for column in table.columns}
        for table_name, table in canonical_metadata.tables.items()
        if table_name in expected
    }
    assert actual == expected
    assert len(actual) == CANONICAL_TABLE_COUNT
    assert sum(len(columns) for columns in actual.values()) == CANONICAL_COLUMN_COUNT


def test_indexes_match_frozen_physical_model() -> None:
    canonical_sql, _bounded_sql = _canonical_and_bounded_sections(
        CURRENT_PHYSICAL_MODEL.read_text()
    )
    expected = set(re.findall(r"CREATE INDEX (\w+) ON", canonical_sql))
    actual = {
        index.name
        for table_name, table in canonical_metadata.tables.items()
        if table_name in _physical_tables(canonical_sql)
        for index in table.indexes
        if index.name is not None
    }
    assert actual == expected


def test_traceability_covers_every_physical_column() -> None:
    manifest = json.loads(TRACEABILITY.read_text())
    assert (
        manifest["schema_source"] == "architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql"
    )
    canonical_sql, _bounded_sql = _canonical_and_bounded_sections(
        CURRENT_PHYSICAL_MODEL.read_text()
    )
    assert (
        manifest["schema_sha256"] == hashlib.sha256(CURRENT_PHYSICAL_MODEL.read_bytes()).hexdigest()
    )
    assert manifest["tables"] == CANONICAL_TABLE_COUNT
    assert manifest["columns"] == CANONICAL_COLUMN_COUNT
    assert manifest["missing_ead_traces"] == []
    traced = {(item["table"], item["column"]) for item in manifest["column_traceability"]}
    expected = {
        (table_name, column.name)
        for table_name, table in canonical_metadata.tables.items()
        if table_name in _physical_tables(canonical_sql)
        for column in table.columns
    }
    assert traced == expected


def test_canonical_migration_matches_frozen_physical_model_byte_for_byte() -> None:
    assert CANONICAL_MIGRATION.read_bytes() == FROZEN_V1_3_PHYSICAL_MODEL.read_bytes()
