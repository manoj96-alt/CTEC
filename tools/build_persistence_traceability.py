"""Build and validate governed persistence traceability artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


class TraceabilityBuildError(Exception):
    """Raised for any condition that must abort traceability generation."""


def parse_tables(sql: str) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    for table, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", sql, re.DOTALL):
        columns: list[str] = []
        for raw_line in body.splitlines():
            line = raw_line.strip()
            match = re.match(r"(\w+)\s+(?:UUID|VARCHAR|TIMESTAMPTZ|INTEGER|\w+_t)", line)
            if match:
                columns.append(match.group(1))
        tables[table] = columns
    return tables


def entity_table_map(sql: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for entity, table in re.findall(r"-- ========== (.+?) ==========\s+CREATE TABLE (\w+)", sql):
        if not entity.startswith("Join tables"):
            result[table] = entity
    return result


def build(
    sql_path: Path,
    ead_path: Path,
    *,
    boundary_marker: str | None = None,
    schema_version_label: str = "v1.3",
    schema_source_label: str | None = None,
    expected_canonical_table_names: frozenset[str] | None = None,
    expected_bounded_table_names: frozenset[str] | None = None,
) -> dict[str, Any]:
    """boundary_marker: when given, only the SQL text before it is parsed and
    traced -- this is the canonical/bounded-extension boundary (see
    tools/generate_physical_model_release.py). The six CDD-012 runtime
    tables and one CDD-013 audit table remain governed by their own
    bounded-extension mechanism and are intentionally excluded from this
    canonical traceability artifact, exactly as they always have been (this
    tool has never traced them, even before the boundary marker existed,
    because they were never part of any physical model file it was run
    against). schema_sha256 always covers the complete file, matching the
    original v1.3 behavior (where the whole file was the canonical portion).

    expected_canonical_table_names / expected_bounded_table_names: when
    given, fail closed if the tables actually found on either side of the
    marker do not exactly match -- catches a bounded-extension table
    ending up before the marker (misclassified as canonical) or a canonical
    table ending up after it (silently dropped from traceability), which a
    plain "compare the two column counts" check would not reliably catch.
    """
    full_sql = sql_path.read_text()
    if boundary_marker is not None:
        occurrences = full_sql.count(boundary_marker)
        if occurrences != 1:
            raise TraceabilityBuildError(
                f"expected exactly one boundary marker in {sql_path}, found {occurrences}"
            )
        boundary_idx = full_sql.index(boundary_marker)
        sql = full_sql[:boundary_idx]
        bounded_sql = full_sql[boundary_idx:]
    else:
        sql = full_sql
        bounded_sql = ""

    tables = parse_tables(sql)
    if boundary_marker is not None:
        bounded_tables = parse_tables(bounded_sql)
        overlap = set(tables) & set(bounded_tables)
        if overlap:
            raise TraceabilityBuildError(
                f"tables appear on both sides of the boundary marker: {overlap}"
            )
        if expected_canonical_table_names is not None and set(tables) != expected_canonical_table_names:
            raise TraceabilityBuildError(
                "canonical (pre-marker) table set does not match expectation.\n"
                f"  found: {sorted(tables)}\n  expected: {sorted(expected_canonical_table_names)}"
            )
        if expected_bounded_table_names is not None and set(bounded_tables) != expected_bounded_table_names:
            raise TraceabilityBuildError(
                "bounded-extension (post-marker) table set does not match expectation.\n"
                f"  found: {sorted(bounded_tables)}\n  expected: {sorted(expected_bounded_table_names)}"
            )
    elif expected_canonical_table_names is not None and set(tables) != expected_canonical_table_names:
        raise TraceabilityBuildError(
            "table set does not match expectation.\n"
            f"  found: {sorted(tables)}\n  expected: {sorted(expected_canonical_table_names)}"
        )

    ead_rows = json.loads(ead_path.read_text())
    table_entities = entity_table_map(sql)
    ead_lookup = {
        (row["Entity"], row["Attribute Name"]): row["row"]
        for row in ead_rows
        if row.get("Entity") and row.get("Attribute Name")
    }
    columns: list[dict[str, Any]] = []
    missing: list[str] = []
    for table, table_columns in tables.items():
        entity = table_entities.get(table)
        for column in table_columns:
            if entity:
                ead_row = ead_lookup.get((entity, column))
                if ead_row is None:
                    missing.append(f"{table}.{column} -> EAD {entity}.{column}")
                columns.append(
                    {
                        "table": table,
                        "column": column,
                        "category": "A - EAD attribute",
                        "ead_entity": entity,
                        "ead_attribute": column,
                        "ead_row": ead_row,
                        "physical_model": f"ECOM Physical Data Model {schema_version_label}",
                    }
                )
            else:
                columns.append(
                    {
                        "table": table,
                        "column": column,
                        "category": "B - Physical Model M:N infrastructure",
                        "ead_entity": None,
                        "ead_attribute": None,
                        "ead_row": None,
                        "physical_model": f"ECOM Physical Data Model {schema_version_label} join table",
                    }
                )

    foreign_keys: list[dict[str, str]] = []
    audit_fields = {"created_by", "modified_by", "previous_version_id"}
    fk_records = list(
        re.findall(
            r"ALTER TABLE (\w+) ADD CONSTRAINT (\w+) FOREIGN KEY \((\w+)\) "
            r"REFERENCES (\w+)\((\w+)\);",
            sql,
        )
    )
    for table, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", sql, re.DOTALL):
        for column, target_table, target_column in re.findall(
            r"(\w+) UUID NOT NULL REFERENCES (\w+)\((\w+)\)", body
        ):
            fk_records.append((table, "inline", column, target_table, target_column))
    for table, constraint, column, target_table, target_column in fk_records:
        foreign_keys.append(
            {
                "constraint": constraint,
                "source": f"{table}.{column}",
                "target": f"{target_table}.{target_column}",
                "relationship_authority": (
                    "EAD-001/Physical Model implementation metadata; Logical Model omission approved by ARCH-001"
                    if column in audit_fields
                    else f"Logical Model v1.3 and Physical Model {schema_version_label}"
                ),
            }
        )
    return {
        "schema_source": schema_source_label if schema_source_label is not None else str(sql_path),
        "schema_sha256": hashlib.sha256(full_sql.encode()).hexdigest(),
        "ead_source": str(ead_path),
        "tables": len(tables),
        "columns": len(columns),
        "foreign_keys": foreign_keys,
        "column_traceability": columns,
        "missing_ead_traces": missing,
    }


def write_manifest_with_overwrite_guard(manifest: dict[str, Any], output_path: Path) -> None:
    """Refuses to overwrite an existing final or temp file; writes to a temp
    path first and only renames it into place after a successful write."""
    if output_path.exists():
        raise TraceabilityBuildError(
            f"refusing to overwrite existing traceability file: {output_path}. "
            "A deliberate regeneration must use a distinct output path."
        )
    tmp_output = output_path.with_suffix(output_path.suffix + ".tmp")
    if tmp_output.exists():
        raise TraceabilityBuildError(
            f"refusing to overwrite or delete an existing temp file not proven to belong "
            f"to this invocation: {tmp_output}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_output.write_text(json.dumps(manifest, indent=2) + "\n")
    tmp_output.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sql", type=Path)
    parser.add_argument("ead", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--boundary-marker",
        default=None,
        help="If given, only SQL content before it is traced as canonical.",
    )
    parser.add_argument("--schema-version-label", default="v1.3")
    parser.add_argument("--schema-source-label", default=None)
    parser.add_argument(
        "--expected-canonical-tables",
        default=None,
        help="Comma-separated table names expected before the boundary marker.",
    )
    parser.add_argument(
        "--expected-bounded-tables",
        default=None,
        help="Comma-separated table names expected after the boundary marker.",
    )
    args = parser.parse_args()
    try:
        manifest = build(
            args.sql,
            args.ead,
            boundary_marker=args.boundary_marker,
            schema_version_label=args.schema_version_label,
            schema_source_label=args.schema_source_label,
            expected_canonical_table_names=(
                frozenset(args.expected_canonical_tables.split(","))
                if args.expected_canonical_tables
                else None
            ),
            expected_bounded_table_names=(
                frozenset(args.expected_bounded_tables.split(","))
                if args.expected_bounded_tables
                else None
            ),
        )
        if manifest["missing_ead_traces"]:
            raise TraceabilityBuildError(
                "Missing EAD traces:\n" + "\n".join(manifest["missing_ead_traces"])
            )
        write_manifest_with_overwrite_guard(manifest, args.output)
    except TraceabilityBuildError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
