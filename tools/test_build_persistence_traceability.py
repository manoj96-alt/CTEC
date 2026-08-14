"""Focused tests for build_persistence_traceability.py's canonical boundary
support (Increment 3A-0 / RFC-015) and overwrite-safety.

Run with: python3 -m pytest tools/test_build_persistence_traceability.py
"""

import hashlib
import json
from pathlib import Path

import pytest
from build_persistence_traceability import TraceabilityBuildError, build, write_manifest_with_overwrite_guard

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REAL_V16_SQL = REPOSITORY_ROOT / "architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql"
REAL_EAD_V16 = REPOSITORY_ROOT / "docs/persistence/traceability/EAD-001-v1.6.json"
REAL_BOUNDARY_MARKER = "-- ---------- BOUNDED NON-CANONICAL EXTENSIONS (CDD-012, CDD-013) ----------"
REAL_CANONICAL_TABLES = frozenset(
    {
        "enterprises",
        "enterprise_types",
        "countries",
        "business_domains",
        "institutional_concepts",
        "relationship_types",
        "entity_types",
        "enterprise_entities",
        "evidences",
        "assertions",
        "institutional_relationships",
        "knowledges",
        "reasons",
        "reason_graphs",
        "decision_objectives",
        "occasions",
        "pattern_of_relevances",
        "decisions",
        "decision_states",
        "institutional_actions",
        "outcomes",
        "experiences",
        "governances",
        "accountable_owners",
        "source_systems",
        "source_objects",
        "institutional_acts",
        "contexts",
        "reason_decision_objectives",
        "reason_evidence",
        "assertion_evidence",
        "institutional_relationship_assertions",
    }
)
REAL_BOUNDED_TABLES = frozenset(
    {
        "api_security_audit_events",
        "runtime_executions",
        "runtime_stages",
        "runtime_handoffs",
        "runtime_artifact_references",
        "runtime_results",
        "runtime_recovery_attempts",
    }
)

SYNTHETIC_MARKER = "-- ---------- BOUNDARY ----------"
SYNTHETIC_SQL = f"""\
-- ========== Widget ==========
CREATE TABLE widgets (
    widget_id UUID PRIMARY KEY,
    widget_name VARCHAR(200) NOT NULL
);

-- ========== Gadget ==========
CREATE TABLE gadgets (
    gadget_id UUID PRIMARY KEY,
    gadget_name VARCHAR(200) NOT NULL
);

{SYNTHETIC_MARKER}
CREATE TABLE bounded_widgets (
    bounded_widget_id UUID PRIMARY KEY,
    bounded_widget_name VARCHAR(200) NOT NULL
);
"""
SYNTHETIC_EAD_ROWS = [
    {"row": 1, "Entity": "Widget", "Attribute Name": "widget_id"},
    {"row": 2, "Entity": "Widget", "Attribute Name": "widget_name"},
    {"row": 3, "Entity": "Gadget", "Attribute Name": "gadget_id"},
    {"row": 4, "Entity": "Gadget", "Attribute Name": "gadget_name"},
]


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content)
    return path


def _write_json(tmp_path: Path, name: str, data) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return path


# ---------------------------------------------------------------------------
# Real v1.6 file: items 1, 2, 3, 4, 9
# ---------------------------------------------------------------------------


def test_v16_boundary_marker_found_exactly_once() -> None:
    sql = REAL_V16_SQL.read_text()
    assert sql.count(REAL_BOUNDARY_MARKER) == 1


def test_v16_traces_only_the_32_canonical_tables_before_the_marker() -> None:
    manifest = build(
        REAL_V16_SQL,
        REAL_EAD_V16,
        boundary_marker=REAL_BOUNDARY_MARKER,
        expected_canonical_table_names=REAL_CANONICAL_TABLES,
        expected_bounded_table_names=REAL_BOUNDED_TABLES,
    )
    assert manifest["tables"] == 32
    traced_tables = {item["table"] for item in manifest["column_traceability"]}
    assert traced_tables == REAL_CANONICAL_TABLES


def test_v16_traces_all_373_canonical_columns() -> None:
    manifest = build(
        REAL_V16_SQL,
        REAL_EAD_V16,
        boundary_marker=REAL_BOUNDARY_MARKER,
        expected_canonical_table_names=REAL_CANONICAL_TABLES,
        expected_bounded_table_names=REAL_BOUNDED_TABLES,
    )
    assert manifest["columns"] == 373
    assert manifest["missing_ead_traces"] == []


def test_v16_excludes_bounded_extension_tables() -> None:
    manifest = build(
        REAL_V16_SQL,
        REAL_EAD_V16,
        boundary_marker=REAL_BOUNDARY_MARKER,
        expected_canonical_table_names=REAL_CANONICAL_TABLES,
        expected_bounded_table_names=REAL_BOUNDED_TABLES,
    )
    traced_tables = {item["table"] for item in manifest["column_traceability"]}
    assert traced_tables.isdisjoint(REAL_BOUNDED_TABLES)


def test_v16_schema_source_label_and_sha256_cover_complete_file() -> None:
    schema_source_label = "architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql"
    manifest = build(
        REAL_V16_SQL,
        REAL_EAD_V16,
        boundary_marker=REAL_BOUNDARY_MARKER,
        schema_source_label=schema_source_label,
        expected_canonical_table_names=REAL_CANONICAL_TABLES,
        expected_bounded_table_names=REAL_BOUNDED_TABLES,
    )
    assert manifest["schema_source"] == schema_source_label
    assert manifest["schema_sha256"] == hashlib.sha256(REAL_V16_SQL.read_bytes()).hexdigest()
    # Sanity: the complete-file hash must differ from a hash of only the
    # canonical slice, proving this is genuinely the whole file, not the slice.
    canonical_only = REAL_V16_SQL.read_text()[: REAL_V16_SQL.read_text().index(REAL_BOUNDARY_MARKER)]
    assert manifest["schema_sha256"] != hashlib.sha256(canonical_only.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Synthetic fixtures: items 5, 6, 7, 8, 10, 11, 12
# ---------------------------------------------------------------------------


def test_missing_boundary_marker_fails_closed(tmp_path: Path) -> None:
    sql_path = _write(tmp_path, "model.sql", SYNTHETIC_SQL.replace(SYNTHETIC_MARKER, "-- no marker here"))
    ead_path = _write_json(tmp_path, "ead.json", SYNTHETIC_EAD_ROWS)

    with pytest.raises(TraceabilityBuildError, match="expected exactly one boundary marker"):
        build(sql_path, ead_path, boundary_marker=SYNTHETIC_MARKER)


def test_duplicate_boundary_marker_fails_closed(tmp_path: Path) -> None:
    doubled = SYNTHETIC_SQL + f"\n{SYNTHETIC_MARKER}\n"
    sql_path = _write(tmp_path, "model.sql", doubled)
    ead_path = _write_json(tmp_path, "ead.json", SYNTHETIC_EAD_ROWS)

    with pytest.raises(TraceabilityBuildError, match="expected exactly one boundary marker"):
        build(sql_path, ead_path, boundary_marker=SYNTHETIC_MARKER)


def test_bounded_table_before_marker_fails_closed(tmp_path: Path) -> None:
    # Move bounded_widgets ahead of the marker: now three tables precede it.
    misplaced = f"""\
-- ========== Widget ==========
CREATE TABLE widgets (
    widget_id UUID PRIMARY KEY,
    widget_name VARCHAR(200) NOT NULL
);

CREATE TABLE bounded_widgets (
    bounded_widget_id UUID PRIMARY KEY,
    bounded_widget_name VARCHAR(200) NOT NULL
);

{SYNTHETIC_MARKER}
CREATE TABLE gadgets (
    gadget_id UUID PRIMARY KEY,
    gadget_name VARCHAR(200) NOT NULL
);
"""
    sql_path = _write(tmp_path, "model.sql", misplaced)
    ead_path = _write_json(tmp_path, "ead.json", SYNTHETIC_EAD_ROWS)

    with pytest.raises(TraceabilityBuildError, match="does not match expectation"):
        build(
            sql_path,
            ead_path,
            boundary_marker=SYNTHETIC_MARKER,
            expected_canonical_table_names=frozenset({"widgets", "gadgets"}),
            expected_bounded_table_names=frozenset({"bounded_widgets"}),
        )


def test_canonical_table_after_marker_fails_closed(tmp_path: Path) -> None:
    # Same misplacement, viewed from the other side: gadgets ends up bounded.
    misplaced = f"""\
-- ========== Widget ==========
CREATE TABLE widgets (
    widget_id UUID PRIMARY KEY,
    widget_name VARCHAR(200) NOT NULL
);

{SYNTHETIC_MARKER}
CREATE TABLE bounded_widgets (
    bounded_widget_id UUID PRIMARY KEY,
    bounded_widget_name VARCHAR(200) NOT NULL
);

CREATE TABLE gadgets (
    gadget_id UUID PRIMARY KEY,
    gadget_name VARCHAR(200) NOT NULL
);
"""
    sql_path = _write(tmp_path, "model.sql", misplaced)
    ead_path = _write_json(tmp_path, "ead.json", SYNTHETIC_EAD_ROWS)

    with pytest.raises(TraceabilityBuildError, match="does not match expectation"):
        build(
            sql_path,
            ead_path,
            boundary_marker=SYNTHETIC_MARKER,
            expected_canonical_table_names=frozenset({"widgets", "gadgets"}),
            expected_bounded_table_names=frozenset({"bounded_widgets"}),
        )


def test_v13_style_invocation_without_boundary_marker_is_backward_compatible(tmp_path: Path) -> None:
    """The original contract: no marker at all means the whole file is
    canonical, exactly as build() behaved before this increment."""
    no_marker_sql = (
        "-- ========== Widget ==========\n"
        "CREATE TABLE widgets (\n"
        "    widget_id UUID PRIMARY KEY,\n"
        "    widget_name VARCHAR(200) NOT NULL\n"
        ");\n"
    )
    sql_path = _write(tmp_path, "model.sql", no_marker_sql)
    ead_path = _write_json(tmp_path, "ead.json", SYNTHETIC_EAD_ROWS)

    manifest = build(sql_path, ead_path)  # no boundary_marker argument at all

    assert manifest["tables"] == 1
    assert manifest["columns"] == 2
    assert manifest["missing_ead_traces"] == []
    assert manifest["schema_sha256"] == hashlib.sha256(no_marker_sql.encode()).hexdigest()


def test_missing_ead_entries_are_reported_in_manifest(tmp_path: Path) -> None:
    incomplete_ead = [row for row in SYNTHETIC_EAD_ROWS if row["Attribute Name"] != "gadget_name"]
    sql_path = _write(tmp_path, "model.sql", SYNTHETIC_SQL)
    ead_path = _write_json(tmp_path, "ead.json", incomplete_ead)

    manifest = build(sql_path, ead_path, boundary_marker=SYNTHETIC_MARKER)

    assert manifest["missing_ead_traces"] == ["gadgets.gadget_name -> EAD Gadget.gadget_name"]


def test_write_manifest_refuses_to_overwrite_existing_final_file(tmp_path: Path) -> None:
    output = tmp_path / "traceability.json"
    output.write_text("pre-existing governed content")

    with pytest.raises(TraceabilityBuildError, match="refusing to overwrite existing"):
        write_manifest_with_overwrite_guard({"some": "manifest"}, output)

    assert output.read_text() == "pre-existing governed content"


def test_write_manifest_refuses_to_overwrite_existing_temp_file(tmp_path: Path) -> None:
    output = tmp_path / "traceability.json"
    tmp_file = output.with_suffix(output.suffix + ".tmp")
    tmp_file.write_text("some other process's in-progress temp file")

    with pytest.raises(TraceabilityBuildError, match="existing temp file"):
        write_manifest_with_overwrite_guard({"some": "manifest"}, output)

    assert tmp_file.read_text() == "some other process's in-progress temp file"
    assert not output.exists()
