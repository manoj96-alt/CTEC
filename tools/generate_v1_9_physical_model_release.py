"""Generate ECOM Physical Data Model v1.7 from the authoritative v1.6 predecessor.

Gate D1 / RFC-016: exactly one authorized change relative to v1.6 --
`institutional_relationships` gains tenant ownership, mirroring the mechanism
RFC-015 already applied to `enterprise_entities`, `source_systems`, and
`source_objects`:

- `tenant_id VARCHAR(200) NOT NULL` is added to `institutional_relationships`.
- Its two existing plain foreign keys (`fk_institutional_relationships_from_entity_id`,
  `fk_institutional_relationships_to_entity_id` -- both already present,
  referencing `enterprise_entities(enterprise_entity_id)`) become tenant-qualified
  composite foreign keys, replaced in place under the same constraint names.
- Tenant-scoped uniqueness (`uq_institutional_relationships_tenant_name`,
  `uq_institutional_relationships_tenant_pk`) and a standalone tenant_id index
  are added, matching the exact pattern used for the three RFC-015 tables.

No other canonical table, column, or constraint changes. RFC-016 also
re-authorizes "Institutional Relationship" as a canonical Operational entity;
that is a documentation/registry act (architecture/INDEX.md, EAD-001), not a
physical-model text change, so it has no effect on this script's output.

I/O contract, matching tools/generate_physical_model_release.py:
- Reads the v1.6 predecessor read-only.
- Writes only a temporary file next to the intended output, moved into place
  only after every assertion in this script has passed; on any failure the
  script exits non-zero and the temp file is removed.
- Never touches any other file. Never invokes a subprocess, opens a socket, or
  connects to a database. All paths are resolved relative to the repository
  root.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_V16 = REPOSITORY_ROOT / "architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql"

BOUNDARY = "-- ---------- BOUNDED NON-CANONICAL EXTENSIONS (CDD-012, CDD-013) ----------"
CANONICAL_TABLE_COUNT = 32
CANONICAL_COLUMN_COUNT = 374
BOUNDED_EXTENSION_TABLE_COUNT = 7


class ReleaseGenerationError(Exception):
    """Raised for any condition that must abort generation without writing output."""


def _physical_tables(sql: str) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for table, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", sql, re.DOTALL):
        tables[table] = {
            match.group(1)
            for line in body.splitlines()
            if (match := re.match(r"\s*(\w+)\s+(?:UUID|VARCHAR|TIMESTAMPTZ|INTEGER|BOOLEAN|BIGINT|BYTEA|\w+_t)", line))
        }
    return tables


def _apply_institutional_relationship_tenant_changes(v16: str) -> str:
    old_header = (
        "-- ============================================================\n"
        "-- ECOM Physical Data Model -- PostgreSQL 15+ DDL -- v1.6\n"
        "-- Canonical core derived from ECOM Physical Data Model v1.5\n"
        "-- (architecture/released/v1.4/ECOM_Physical_Data_Model_v1_5.sql), which\n"
        "-- remains frozen and unmodified for historical traceability.\n"
        "--\n"
        "-- Authorized by CTEC Product Owner Manoj Nair on 2026-08-13 for\n"
        "-- Increment 3A-0 (see RFC-015, architecture/released/v1.8/). See\n"
        "-- tools/generate_physical_model_release.py for the two independent,\n"
        "-- explicitly authorized changes this release makes relative to v1.5:\n"
        "-- tenant ownership on three canonical tables, and non-semantic\n"
        "-- bounded-extension layout normalization.\n"
        "-- ============================================================"
    )
    new_header = (
        "-- ============================================================\n"
        "-- ECOM Physical Data Model -- PostgreSQL 15+ DDL -- v1.7\n"
        "-- Canonical core derived from ECOM Physical Data Model v1.6\n"
        "-- (architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql), which\n"
        "-- remains frozen and unmodified for historical traceability.\n"
        "--\n"
        "-- Authorized by CTEC Product Owner Manoj Nair on 2026-08-15 for\n"
        "-- Gate D1 (see RFC-016, architecture/released/v1.9/). See\n"
        "-- tools/generate_v1_9_physical_model_release.py for the single,\n"
        "-- explicitly authorized change this release makes relative to v1.6:\n"
        "-- tenant ownership on institutional_relationships.\n"
        "-- ============================================================"
    )
    if v16.count(old_header) != 1:
        raise ReleaseGenerationError("v1.6 header pattern not found exactly once")
    v17 = v16.replace(old_header, new_header)

    old_table = (
        "CREATE TABLE institutional_relationships (\n"
        "    institutional_relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
        "    institutional_relationship_name VARCHAR(200) NOT NULL UNIQUE,"
    )
    new_table = (
        "CREATE TABLE institutional_relationships (\n"
        "    institutional_relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
        "    tenant_id VARCHAR(200) NOT NULL,\n"
        "    institutional_relationship_name VARCHAR(200) NOT NULL,"
    )
    if v17.count(old_table) != 1:
        raise ReleaseGenerationError("expected exactly one occurrence of the institutional_relationships table header")
    v17 = v17.replace(old_table, new_table)

    old_fks = (
        "ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_from_entity_id "
        "FOREIGN KEY (from_entity_id) REFERENCES enterprise_entities(enterprise_entity_id);\n"
        "ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_to_entity_id "
        "FOREIGN KEY (to_entity_id) REFERENCES enterprise_entities(enterprise_entity_id);"
    )
    new_fks = (
        "ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_from_entity_id "
        "FOREIGN KEY (tenant_id,from_entity_id) REFERENCES enterprise_entities(tenant_id,enterprise_entity_id);\n"
        "ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_to_entity_id "
        "FOREIGN KEY (tenant_id,to_entity_id) REFERENCES enterprise_entities(tenant_id,enterprise_entity_id);"
    )
    if v17.count(old_fks) != 1:
        raise ReleaseGenerationError("expected exactly one occurrence of the two institutional_relationships FK lines, adjacent")
    v17 = v17.replace(old_fks, new_fks)

    old_uniq_anchor = (
        "ALTER TABLE source_objects ADD CONSTRAINT uq_source_objects_tenant_name "
        "UNIQUE (tenant_id,source_object_name);\n"
        "ALTER TABLE source_objects ADD CONSTRAINT uq_source_objects_tenant_pk "
        "UNIQUE (tenant_id,source_object_id);"
    )
    new_uniq = (
        old_uniq_anchor + "\n"
        "ALTER TABLE institutional_relationships ADD CONSTRAINT uq_institutional_relationships_tenant_name "
        "UNIQUE (tenant_id,institutional_relationship_name);\n"
        "ALTER TABLE institutional_relationships ADD CONSTRAINT uq_institutional_relationships_tenant_pk "
        "UNIQUE (tenant_id,institutional_relationship_id);"
    )
    if v17.count(old_uniq_anchor) != 1:
        raise ReleaseGenerationError("expected exactly one occurrence of the composite-uniqueness anchor")
    v17 = v17.replace(old_uniq_anchor, new_uniq)

    old_idx_anchor = "CREATE INDEX idx_source_objects_tenant_id ON source_objects(tenant_id);"
    new_idx_anchor = old_idx_anchor + "\nCREATE INDEX idx_institutional_relationships_tenant_id ON institutional_relationships(tenant_id);"
    if v17.count(old_idx_anchor) != 1:
        raise ReleaseGenerationError("expected exactly one occurrence of the tenant-index anchor")
    v17 = v17.replace(old_idx_anchor, new_idx_anchor, 1)

    return v17


def _validate_v17_structure(v17: str) -> None:
    if v17.count(BOUNDARY) != 1:
        raise ReleaseGenerationError(f"expected exactly one boundary marker, found {v17.count(BOUNDARY)}")
    boundary_idx = v17.index(BOUNDARY)

    canonical_text = v17[:boundary_idx]
    extension_text = v17[boundary_idx:]

    canonical_tables = _physical_tables(canonical_text)
    extension_tables = _physical_tables(extension_text)
    all_tables = _physical_tables(v17)

    if len(all_tables) != len(canonical_tables) + len(extension_tables):
        raise ReleaseGenerationError(
            "a table name appears on both sides of the boundary marker: "
            f"{set(canonical_tables) & set(extension_tables)}"
        )
    if len(all_tables) != 39:
        raise ReleaseGenerationError(f"expected 39 total CREATE TABLE statements, found {len(all_tables)}")

    total_create_table_statements = len(re.findall(r"CREATE TABLE \w+ \(", v17))
    if total_create_table_statements != 39:
        raise ReleaseGenerationError(
            f"expected 39 CREATE TABLE statements in the file, found {total_create_table_statements} "
            "(duplicate table definitions present)"
        )

    if len(canonical_tables) != CANONICAL_TABLE_COUNT:
        raise ReleaseGenerationError(
            f"expected {CANONICAL_TABLE_COUNT} canonical tables before the marker, found {len(canonical_tables)}"
        )
    canonical_columns = sum(len(cols) for cols in canonical_tables.values())
    if canonical_columns != CANONICAL_COLUMN_COUNT:
        raise ReleaseGenerationError(
            f"expected {CANONICAL_COLUMN_COUNT} canonical columns, found {canonical_columns}"
        )
    if len(extension_tables) != BOUNDED_EXTENSION_TABLE_COUNT:
        raise ReleaseGenerationError(
            f"expected {BOUNDED_EXTENSION_TABLE_COUNT} bounded-extension tables after the marker, "
            f"found {len(extension_tables)}"
        )
    if "institutional_relationships" not in canonical_tables or "tenant_id" not in canonical_tables["institutional_relationships"]:
        raise ReleaseGenerationError("institutional_relationships is missing tenant_id in the canonical section")


def generate(v16_path: Path, output_path: Path) -> Path:
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if output_path.exists():
        raise ReleaseGenerationError(
            f"refusing to overwrite existing release file: {output_path}. "
            "A deliberate regeneration must use a distinct --output path."
        )
    if tmp_path.exists():
        raise ReleaseGenerationError(
            f"refusing to overwrite or delete an existing temp file not proven to belong "
            f"to this invocation: {tmp_path}. Remove or rename it manually before retrying."
        )

    v16 = v16_path.read_text()
    v17 = _apply_institutional_relationship_tenant_changes(v16)
    _validate_v17_structure(v17)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(v17)
    try:
        _validate_v17_structure(tmp_path.read_text())
    except ReleaseGenerationError:
        tmp_path.unlink(missing_ok=True)
        raise
    tmp_path.replace(output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v16", type=Path, default=DEFAULT_V16)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        output_path = generate(args.v16, args.output)
    except ReleaseGenerationError as error:
        print(f"Physical model release generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
