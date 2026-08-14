"""Generate a new Enterprise Attribute Dictionary (EAD) release by appending
new attribute rows to an existing, frozen EAD JSON file.

Built for Increment 3A-0 / RFC-015: EAD-001-v1.3.json's 362 rows plus three
new tenant_id attribute rows (Enterprise Entity, Source System, Source
Object), producing EAD-001-v1.6.json (365 rows) so
tools/build_persistence_traceability.py has an EAD trace for the tenant_id
columns added to the physical model by
tools/generate_physical_model_release.py.

I/O contract, matching tools/generate_physical_model_release.py:
- Reads the source EAD JSON read-only; never writes to it.
- Writes only a temporary file first (<output>.tmp), re-reads and re-validates
  it from disk, and only then renames it to the final output path.
- Refuses to run at all if either the final output path or the temp path
  already exists -- never overwrites or deletes a file it did not just create
  itself in this invocation.
- On any validation failure, removes only its own temp file and leaves no
  final artifact.
- All default paths are resolved relative to this file's location (the
  repository's tools/ directory), never hardcoded to a machine.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPOSITORY_ROOT / "docs/persistence/traceability/EAD-001-v1.3.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "docs/persistence/traceability/EAD-001-v1.6.json"
DEFAULT_EXPECTED_SOURCE_ROWS = 362

# Increment 3A-0 / RFC-015: tenant_id was added to these three canonical
# tables in ECOM Physical Data Model v1.6 (see
# tools/generate_physical_model_release.py); each needs a matching EAD trace.
DEFAULT_NEW_ATTRIBUTE_ROWS: tuple[tuple[str, str], ...] = (
    ("Enterprise Entity", "Operational"),
    ("Source System", "Integration"),
    ("Source Object", "Integration"),
)
DEFAULT_ATTRIBUTE_NAME = "tenant_id"
DEFAULT_CONSTITUTIONAL_MEANING = (
    "Increment 3A-0 / RFC-015: opaque tenant ownership identifier sourced "
    "from the trusted authority boundary, establishing customer-boundary "
    "isolation for this instance-data table"
)


class EadGenerationError(Exception):
    """Raised for any condition that must abort generation without writing output."""


def _build_row(entity: str, package: str, row_number: int, attribute_name: str) -> dict[str, Any]:
    return {
        "row": row_number,
        "Entity": entity,
        "Attribute Name": attribute_name,
        "Business Name": "Tenant ID",
        "Description": "Customer/tenant ownership boundary",
        "Data Type": "STRING",
        "Length": "200",
        "Mandatory": True,
        "Nullable": False,
        "PK": None,
        "AK": None,
        "FK": None,
        "FK Entity": None,
        "Attribute Category": "Governance",
        "Base Profile": "Custom",
        "Enumeration": None,
        "Default": None,
        "Immutable": "Yes",
        "Derived": "No",
        "Searchable": "Yes",
        "Indexed": "Yes",
        "Relationship Entity": None,
        "Relationship Attribute": None,
        "Constitutional Meaning": DEFAULT_CONSTITUTIONAL_MEANING,
        "Entity Package": package,
    }


def _validate_rows(rows: list[dict[str, Any]]) -> None:
    pairs = [(r.get("Entity"), r.get("Attribute Name")) for r in rows]
    if len(pairs) != len(set(pairs)):
        seen: set[tuple[Any, Any]] = set()
        dupes: set[tuple[Any, Any]] = set()
        for pair in pairs:
            if pair in seen:
                dupes.add(pair)
            seen.add(pair)
        raise EadGenerationError(f"(Entity, Attribute Name) pairs are not unique: {dupes}")


def generate(
    source_path: Path,
    output_path: Path,
    *,
    expected_source_rows: int = DEFAULT_EXPECTED_SOURCE_ROWS,
    new_attribute_rows: tuple[tuple[str, str], ...] = DEFAULT_NEW_ATTRIBUTE_ROWS,
    attribute_name: str = DEFAULT_ATTRIBUTE_NAME,
) -> Path:
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if output_path.exists():
        raise EadGenerationError(
            f"refusing to overwrite existing EAD release file: {output_path}. "
            "A deliberate regeneration must use a distinct --output path."
        )
    if tmp_path.exists():
        raise EadGenerationError(
            f"refusing to overwrite or delete an existing temp file not proven to belong "
            f"to this invocation: {tmp_path}. Remove or rename it manually before retrying."
        )

    try:
        data = json.loads(source_path.read_text())
    except json.JSONDecodeError as error:
        raise EadGenerationError(f"source EAD file is not valid JSON: {source_path}: {error}") from error
    if not isinstance(data, list):
        raise EadGenerationError(f"source EAD file must contain a JSON array of rows: {source_path}")

    if len(data) != expected_source_rows:
        raise EadGenerationError(
            f"expected source EAD file to contain {expected_source_rows} rows, found {len(data)}"
        )

    existing_pairs = {(r.get("Entity"), r.get("Attribute Name")) for r in data}
    entities_present = {r.get("Entity") for r in data}

    for entity, _package in new_attribute_rows:
        if entity not in entities_present:
            raise EadGenerationError(f"entity {entity!r} not found in source EAD dictionary")
        if (entity, attribute_name) in existing_pairs:
            raise EadGenerationError(
                f"({entity!r}, {attribute_name!r}) already exists in source EAD dictionary"
            )

    row_numbers = [r["row"] for r in data if isinstance(r.get("row"), int)]
    if not row_numbers:
        raise EadGenerationError("source EAD file has no integer 'row' values to continue numbering from")
    next_row_number = max(row_numbers) + 1
    new_rows = [
        _build_row(entity, package, next_row_number + i, attribute_name)
        for i, (entity, package) in enumerate(new_attribute_rows)
    ]

    combined = data + new_rows
    _validate_rows(combined)
    expected_total = expected_source_rows + len(new_attribute_rows)
    if len(combined) != expected_total:
        raise EadGenerationError(f"expected {expected_total} total rows, got {len(combined)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json.dumps(combined, indent=2) + "\n")

    try:
        reloaded = json.loads(tmp_path.read_text())
        if len(reloaded) != expected_total:
            raise EadGenerationError(f"temp file has {len(reloaded)} rows, expected {expected_total}")
        _validate_rows(reloaded)
        reloaded_pairs = {(r.get("Entity"), r.get("Attribute Name")) for r in reloaded}
        for entity, _package in new_attribute_rows:
            if (entity, attribute_name) not in reloaded_pairs:
                raise EadGenerationError(f"temp file missing ({entity!r}, {attribute_name!r})")
    except (EadGenerationError, json.JSONDecodeError) as error:
        tmp_path.unlink(missing_ok=True)
        raise EadGenerationError(f"temp-file validation failed: {error}") from error

    tmp_path.replace(output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-source-rows", type=int, default=DEFAULT_EXPECTED_SOURCE_ROWS)
    args = parser.parse_args()
    try:
        output_path = generate(
            args.source, args.output, expected_source_rows=args.expected_source_rows
        )
    except EadGenerationError as error:
        print(f"EAD release generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
