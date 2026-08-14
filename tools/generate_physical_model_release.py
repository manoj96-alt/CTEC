"""Generate ECOM Physical Data Model v1.6 from the authoritative v1.5 predecessor.

Increment 3A-0 / RFC-015 tenant-foundation architecture release. Two independent,
explicitly authorized changes relative to v1.5:

1. Tenant ownership: tenant_id is added to enterprise_entities, source_systems,
   and source_objects, with tenant-scoped uniqueness replacing the prior global
   uniqueness on their business-key names, and source_objects' source_system_id
   foreign key becoming tenant-qualified. No other canonical table, column, or
   constraint changes.

2. Bounded-extension layout normalization (non-semantic): v1.5 inherited a
   duplicated representation of its six CDD-012 runtime-persistence tables (one
   verbose copy positioned before its own boundary comment, one compact copy
   after it) and positioned its CDD-013 api_security_audit_events table outside
   that boundary entirely. This script verifies both copies of every CDD-012
   table are column-for-column semantically equivalent, then emits exactly one
   copy of each of the seven bounded non-canonical extension tables, once, after
   a single explicit boundary marker. No runtime or audit schema, type, default,
   constraint, or index semantics are altered.

Scope note: the content edits below (which tables gain tenant_id, which
duplicated tables get deduplicated) are specific to this one governed release,
matching the specific, one-time nature of a physical-model version bump. The
structural mechanics (temp-file-then-move, fail-closed assertions, dedicated
validation pass) follow the same reusable pattern this repository already uses
for architecture-release tooling (see tools/build_persistence_traceability.py),
so a future release can extend this script rather than starting over.

I/O contract:
- Reads (read-only): the predecessor SQL file and, for this release, the frozen
  v1.3 file used to prove the predecessor's canonical block is unmodified.
- Writes: only a single temporary file next to the intended output. The
  temporary file is moved to the final governed path only after every assertion
  in this script has passed; on any failure the script exits non-zero and the
  temporary file is removed, leaving no partial or final release artifact.
- Never touches any other file. Never invokes a subprocess, opens a socket, or
  connects to a database. All paths are resolved relative to the repository
  root (this file's grandparent directory), never hardcoded to a machine.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_V13 = REPOSITORY_ROOT / "architecture/released/v1.1/ECOM_Physical_Data_Model_v1_3.sql"
DEFAULT_V15 = REPOSITORY_ROOT / "architecture/released/v1.4/ECOM_Physical_Data_Model_v1_5.sql"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql"

BOUNDARY = "-- ---------- BOUNDED NON-CANONICAL EXTENSIONS (CDD-012, CDD-013) ----------"

RUNTIME_TABLES = (
    "runtime_executions",
    "runtime_stages",
    "runtime_handoffs",
    "runtime_artifact_references",
    "runtime_results",
    "runtime_recovery_attempts",
)
CANONICAL_TABLE_COUNT = 32
CANONICAL_COLUMN_COUNT = 373
BOUNDED_EXTENSION_TABLE_COUNT = 7


class ReleaseGenerationError(Exception):
    """Raised for any condition that must abort generation without writing output."""


def _extract_create_table(sql: str, table: str, start_from: int = 0) -> tuple[str, int, int]:
    pattern = re.compile(rf"CREATE TABLE {re.escape(table)} \((.*?)\n\);\n", re.DOTALL)
    match = pattern.search(sql, start_from)
    if not match:
        raise ReleaseGenerationError(f"could not find CREATE TABLE {table} from offset {start_from}")
    return match.group(0), match.start(), match.end()


def _normalize_column_defs(body: str) -> list[str]:
    """Column-def-level normalization: collapse whitespace, split on
    top-level commas (respecting parens), so a verbose multi-line rendering
    and a compact one-line rendering of the same columns compare equal."""
    flat = re.sub(r"\s+", " ", body).strip()
    parts: list[str] = []
    depth = 0
    current = ""
    for char in flat:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def _verify_canonical_block_unchanged(v15: str, v13: str) -> str:
    """Locate v1.5's embedded canonical block (header + 32 tables + FK/
    uniqueness/CHECK/index sections) and assert it is byte-identical to the
    frozen v1.3 release, from the shared header marker onward. (v1.5's copy
    of the single decorative separator line that precedes the header marker
    in v1.3 was dropped when v1.5 was assembled -- confirmed by inspection --
    so comparison intentionally starts at the marker itself, which is where
    the actual schema-relevant content begins; a fresh separator line is
    prepended when reconstructing the canonical text below.)"""
    canon_start_marker = "-- ECOM Physical Data Model -- PostgreSQL 15+ DDL -- v1.3"
    marker_idx_v15 = v15.index(canon_start_marker)
    marker_idx_v13 = v13.index(canon_start_marker)
    if v13.count(canon_start_marker) != 1 or v15.count(canon_start_marker) != 1:
        raise ReleaseGenerationError("canonical header marker must appear exactly once in each source file")

    join_table_end_marker = (
        "CREATE TABLE institutional_relationship_assertions (\n"
        "    institutional_relationship_id UUID NOT NULL "
        "REFERENCES institutional_relationships(institutional_relationship_id),\n"
        "    assertion_id UUID NOT NULL REFERENCES assertions(assertion_id),\n"
        "    PRIMARY KEY (institutional_relationship_id, assertion_id)\n"
        ");\n"
    )
    join_end_v15 = v15.index(join_table_end_marker) + len(join_table_end_marker)
    join_end_v13 = v13.index(join_table_end_marker) + len(join_table_end_marker)
    head_v15 = v15[marker_idx_v15:join_end_v15]
    head_v13 = v13[marker_idx_v13:join_end_v13]

    fk_marker = "-- ---------- Foreign key constraints ----------"
    fk_start_v15 = v15.index(fk_marker)
    fk_start_v13 = v13.index(fk_marker)
    old_boundary_marker = "-- ---------- CDD-012 BOUNDED NON-CANONICAL RUNTIME PERSISTENCE ----------"
    if v15.count(old_boundary_marker) != 1:
        raise ReleaseGenerationError(
            f"expected exactly one legacy boundary marker in v1.5, found {v15.count(old_boundary_marker)}"
        )
    old_boundary_idx = v15.index(old_boundary_marker)
    # v13 (no marker follows it) ends immediately after its final comment
    # line with no trailing newline; v15 has the same final content but with
    # trailing blank-line spacing before the (untrustworthy) old marker.
    # That is whitespace-only padding, not a content difference, so both
    # tails are compared with trailing whitespace stripped.
    tail_v15 = v15[fk_start_v15:old_boundary_idx].rstrip()
    tail_v13 = v13[fk_start_v13:].rstrip()

    if head_v15 != head_v13:
        for i, (a, b) in enumerate(zip(head_v15, head_v13)):
            if a != b:
                raise ReleaseGenerationError(
                    "v1.5's embedded canonical header/table content is not identical to v1.3 "
                    f"from the shared header marker onward.\nFirst difference at char {i}\n"
                    f"v1.5 side: {head_v15[max(0, i - 80):i + 80]!r}\n"
                    f"v1.3 side: {head_v13[max(0, i - 80):i + 80]!r}"
                )
        raise ReleaseGenerationError(
            f"v1.5 canonical head length {len(head_v15)} != v1.3 head length {len(head_v13)}"
        )
    if tail_v15 != tail_v13:
        for i, (a, b) in enumerate(zip(tail_v15, tail_v13)):
            if a != b:
                raise ReleaseGenerationError(
                    "v1.5's embedded canonical FK/uniqueness/CHECK/index content is not "
                    f"identical to v1.3.\nFirst difference at char {i}\n"
                    f"v1.5 side: {tail_v15[max(0, i - 80):i + 80]!r}\n"
                    f"v1.3 side: {tail_v13[max(0, i - 80):i + 80]!r}"
                )
        raise ReleaseGenerationError(
            f"v1.5 canonical tail length {len(tail_v15)} != v1.3 tail length {len(tail_v13)}"
        )

    combined = "-- ============================================================\n" + head_v15 + tail_v15
    return combined, old_boundary_idx, join_end_v15


def _verify_runtime_table_duplication_is_semantic_noop(
    v15: str, join_end: int, old_boundary_idx: int, old_boundary_marker_len: int
) -> None:
    first_copies: dict[str, str] = {}
    cursor = join_end
    for table in RUNTIME_TABLES:
        block, _start, end = _extract_create_table(v15, table, cursor)
        first_copies[table] = block
        cursor = end

    second_copies: dict[str, str] = {}
    cursor = old_boundary_idx + old_boundary_marker_len
    for table in RUNTIME_TABLES:
        block, _start, end = _extract_create_table(v15, table, cursor)
        second_copies[table] = block
        cursor = end

    mismatches = []
    for table in RUNTIME_TABLES:
        body1 = re.search(r"\((.*)\)", first_copies[table], re.DOTALL).group(1)
        body2 = re.search(r"\((.*)\)", second_copies[table], re.DOTALL).group(1)
        cols1 = _normalize_column_defs(body1)
        cols2 = _normalize_column_defs(body2)
        if cols1 != cols2:
            mismatches.append((table, cols1, cols2))

    if mismatches:
        detail = "\n".join(
            f"  {table}:\n    copy 1: {c1}\n    copy 2: {c2}" for table, c1, c2 in mismatches
        )
        raise ReleaseGenerationError(
            "duplicated CDD-012 runtime table definitions are not semantically "
            f"equivalent; refusing to deduplicate silently:\n{detail}"
        )


def _apply_tenant_ownership_changes(canon: str) -> str:
    old_header = (
        "-- ============================================================\n"
        "-- ECOM Physical Data Model -- PostgreSQL 15+ DDL -- v1.3\n"
        "-- Generated directly from EAD-001 v1.3 (Enterprise Attribute Dictionary)\n"
        "-- ============================================================"
    )
    new_header = (
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
    if canon.count(old_header) != 1:
        raise ReleaseGenerationError("canonical header pattern not found exactly once")
    canon = canon.replace(old_header, new_header)

    column_changes = [
        (
            "CREATE TABLE enterprise_entities (\n"
            "    enterprise_entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    enterprise_entity_name VARCHAR(200) NOT NULL UNIQUE,",
            "CREATE TABLE enterprise_entities (\n"
            "    enterprise_entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    tenant_id VARCHAR(200) NOT NULL,\n"
            "    enterprise_entity_name VARCHAR(200) NOT NULL,",
        ),
        (
            "CREATE TABLE source_systems (\n"
            "    source_system_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    source_system_name VARCHAR(200) NOT NULL UNIQUE,",
            "CREATE TABLE source_systems (\n"
            "    source_system_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    tenant_id VARCHAR(200) NOT NULL,\n"
            "    source_system_name VARCHAR(200) NOT NULL,",
        ),
        (
            "CREATE TABLE source_objects (\n"
            "    source_object_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    source_object_name VARCHAR(200) NOT NULL UNIQUE,",
            "CREATE TABLE source_objects (\n"
            "    source_object_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    tenant_id VARCHAR(200) NOT NULL,\n"
            "    source_object_name VARCHAR(200) NOT NULL,",
        ),
    ]
    for old, new in column_changes:
        if canon.count(old) != 1:
            raise ReleaseGenerationError(f"expected exactly one occurrence of pattern:\n{old}")
        canon = canon.replace(old, new)

    old_fk = (
        "ALTER TABLE source_objects ADD CONSTRAINT fk_source_objects_source_system_id "
        "FOREIGN KEY (source_system_id) REFERENCES source_systems(source_system_id);"
    )
    new_fk = (
        "ALTER TABLE source_objects ADD CONSTRAINT fk_source_objects_source_system_id "
        "FOREIGN KEY (tenant_id,source_system_id) REFERENCES source_systems(tenant_id,source_system_id);"
    )
    if canon.count(old_fk) != 1:
        raise ReleaseGenerationError("expected exactly one occurrence of the source_objects FK line")
    canon = canon.replace(old_fk, new_fk)

    old_uniq = (
        "-- ---------- Composite uniqueness constraints ----------\n"
        "ALTER TABLE business_domains ADD CONSTRAINT "
        "uq_business_domains_enterprise_id_domain_name UNIQUE (enterprise_id,domain_name);"
    )
    new_uniq = (
        old_uniq + "\n"
        "ALTER TABLE enterprise_entities ADD CONSTRAINT uq_enterprise_entities_tenant_name "
        "UNIQUE (tenant_id,enterprise_entity_name);\n"
        "ALTER TABLE enterprise_entities ADD CONSTRAINT uq_enterprise_entities_tenant_pk "
        "UNIQUE (tenant_id,enterprise_entity_id);\n"
        "ALTER TABLE source_systems ADD CONSTRAINT uq_source_systems_tenant_name "
        "UNIQUE (tenant_id,source_system_name);\n"
        "ALTER TABLE source_systems ADD CONSTRAINT uq_source_systems_tenant_pk "
        "UNIQUE (tenant_id,source_system_id);\n"
        "ALTER TABLE source_objects ADD CONSTRAINT uq_source_objects_tenant_name "
        "UNIQUE (tenant_id,source_object_name);\n"
        "ALTER TABLE source_objects ADD CONSTRAINT uq_source_objects_tenant_pk "
        "UNIQUE (tenant_id,source_object_id);"
    )
    if canon.count(old_uniq) != 1:
        raise ReleaseGenerationError("expected exactly one occurrence of the composite-uniqueness anchor")
    canon = canon.replace(old_uniq, new_uniq)

    old_idx_anchor = "CREATE INDEX idx_enterprises_enterprise_name ON enterprises(enterprise_name);"
    new_idx_anchor = (
        "CREATE INDEX idx_enterprise_entities_tenant_id ON enterprise_entities(tenant_id);\n"
        "CREATE INDEX idx_source_systems_tenant_id ON source_systems(tenant_id);\n"
        "CREATE INDEX idx_source_objects_tenant_id ON source_objects(tenant_id);\n"
        + old_idx_anchor
    )
    if canon.count(old_idx_anchor) != 1:
        raise ReleaseGenerationError("expected exactly one occurrence of the indexes-section anchor")
    canon = canon.replace(old_idx_anchor, new_idx_anchor, 1)
    return canon


def _extract_bounded_extension_content(v15: str, old_boundary_idx: int, old_boundary_marker: str) -> str:
    audit_comment_marker = "-- CDD-013 bounded non-canonical application-security record"
    audit_start = v15.index(audit_comment_marker)
    _audit_block, _audit_start2, audit_table_end = _extract_create_table(
        v15, "api_security_audit_events", 0
    )
    audit_tail_end = v15.index(
        "-- ============================================================", audit_table_end
    )
    audit_block = v15[audit_start:audit_tail_end].rstrip("\n") + "\n"

    runtime_block = v15[old_boundary_idx + len(old_boundary_marker):].lstrip("\n")
    return audit_block.rstrip("\n") + "\n\n" + runtime_block.rstrip("\n") + "\n"


def _physical_tables(sql: str) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for table, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", sql, re.DOTALL):
        tables[table] = {
            match.group(1)
            for line in body.splitlines()
            if (match := re.match(r"\s*(\w+)\s+(?:UUID|VARCHAR|TIMESTAMPTZ|INTEGER|BOOLEAN|BIGINT|BYTEA|\w+_t)", line))
        }
    return tables


def _validate_v16_structure(v16: str) -> None:
    if v16.count(BOUNDARY) != 1:
        raise ReleaseGenerationError(f"expected exactly one boundary marker, found {v16.count(BOUNDARY)}")
    boundary_idx = v16.index(BOUNDARY)

    canonical_text = v16[:boundary_idx]
    extension_text = v16[boundary_idx:]

    canonical_tables = _physical_tables(canonical_text)
    extension_tables = _physical_tables(extension_text)
    all_tables = _physical_tables(v16)

    if len(all_tables) != len(canonical_tables) + len(extension_tables):
        raise ReleaseGenerationError(
            "a table name appears on both sides of the boundary marker: "
            f"{set(canonical_tables) & set(extension_tables)}"
        )
    if len(all_tables) != 39:
        raise ReleaseGenerationError(f"expected 39 total CREATE TABLE statements, found {len(all_tables)}")

    total_create_table_statements = len(re.findall(r"CREATE TABLE \w+ \(", v16))
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
    if set(extension_tables) != {"api_security_audit_events", *RUNTIME_TABLES}:
        raise ReleaseGenerationError(
            f"unexpected bounded-extension table set: {set(extension_tables)}"
        )
    if "enterprise_entities" not in canonical_tables or "tenant_id" not in canonical_tables["enterprise_entities"]:
        raise ReleaseGenerationError("enterprise_entities is missing tenant_id in the canonical section")
    if "source_systems" not in canonical_tables or "tenant_id" not in canonical_tables["source_systems"]:
        raise ReleaseGenerationError("source_systems is missing tenant_id in the canonical section")
    if "source_objects" not in canonical_tables or "tenant_id" not in canonical_tables["source_objects"]:
        raise ReleaseGenerationError("source_objects is missing tenant_id in the canonical section")


def generate(v13_path: Path, v15_path: Path, output_path: Path) -> Path:
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if output_path.exists():
        raise ReleaseGenerationError(
            f"refusing to overwrite existing release file: {output_path}. "
            "A deliberate regeneration must use a distinct --output path and compare "
            "the generated bytes with the governed artifact; this tool never overwrites "
            "a file that already exists."
        )
    if tmp_path.exists():
        raise ReleaseGenerationError(
            f"refusing to overwrite or delete an existing temp file not proven to belong "
            f"to this invocation: {tmp_path}. Remove or rename it manually before retrying."
        )

    v13 = v13_path.read_text()
    v15 = v15_path.read_text()

    canonical_combined, old_boundary_idx, join_end = _verify_canonical_block_unchanged(v15, v13)
    old_boundary_marker = "-- ---------- CDD-012 BOUNDED NON-CANONICAL RUNTIME PERSISTENCE ----------"
    _verify_runtime_table_duplication_is_semantic_noop(
        v15, join_end, old_boundary_idx, len(old_boundary_marker)
    )

    canon = _apply_tenant_ownership_changes(canonical_combined)
    extensions = _extract_bounded_extension_content(v15, old_boundary_idx, old_boundary_marker)

    v16 = canon.rstrip("\n") + "\n\n" + BOUNDARY + "\n\n" + extensions

    _validate_v16_structure(v16)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(v16)
    try:
        # Re-read and re-validate the file actually on disk, not just the
        # in-memory string, before it becomes the governed artifact.
        _validate_v16_structure(tmp_path.read_text())
    except ReleaseGenerationError:
        tmp_path.unlink(missing_ok=True)
        raise
    tmp_path.replace(output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v13", type=Path, default=DEFAULT_V13)
    parser.add_argument("--v15", type=Path, default=DEFAULT_V15)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        output_path = generate(args.v13, args.v15, args.output)
    except ReleaseGenerationError as error:
        print(f"Physical model release generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
