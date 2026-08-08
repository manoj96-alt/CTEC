"""Build and validate governed persistence traceability artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


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


def build(sql_path: Path, ead_path: Path) -> dict[str, Any]:
    sql = sql_path.read_text()
    ead_rows = json.loads(ead_path.read_text())
    tables = parse_tables(sql)
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
                        "physical_model": "ECOM Physical Data Model v1.3",
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
                        "physical_model": "ECOM Physical Data Model v1.3 join table",
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
                    else "Logical Model v1.3 and Physical Model v1.3"
                ),
            }
        )
    return {
        "schema_source": str(sql_path),
        "schema_sha256": hashlib.sha256(sql.encode()).hexdigest(),
        "ead_source": str(ead_path),
        "tables": len(tables),
        "columns": len(columns),
        "foreign_keys": foreign_keys,
        "column_traceability": columns,
        "missing_ead_traces": missing,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sql", type=Path)
    parser.add_argument("ead", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = build(args.sql, args.ead)
    if manifest["missing_ead_traces"]:
        raise SystemExit("Missing EAD traces:\n" + "\n".join(manifest["missing_ead_traces"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
