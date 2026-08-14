"""Focused tests for generate_physical_model_release.py: overwrite-safety
refusals (using placeholder v13/v15 paths, since those checks run before any
input file is read) and the canonical-block anchor (using the real
architecture files, since that is a regression test for a real anchor bug
found while building this tool: an earlier implementation located the
canonical header by walking back a fixed number of newlines from the header
marker, which mis-anchored against v1.5's actual byte layout -- see the
CDD-013 audit block sitting immediately before the marker with no blank-line
separator of its own).

Run with: python3 -m pytest tools/test_generate_physical_model_release.py
"""

import re
from pathlib import Path

import pytest
from generate_physical_model_release import (
    DEFAULT_V13,
    DEFAULT_V15,
    RUNTIME_TABLES,
    ReleaseGenerationError,
    _verify_canonical_block_unchanged,
    generate,
)

CANONICAL_TABLE_NAMES = (
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
)


def test_refuses_to_overwrite_existing_final_release_file(tmp_path: Path) -> None:
    output_path = tmp_path / "ECOM_Physical_Data_Model_v1_6.sql"
    output_path.write_text("pre-existing governed content")

    with pytest.raises(ReleaseGenerationError, match="refusing to overwrite existing release file"):
        generate(tmp_path / "nonexistent-v13.sql", tmp_path / "nonexistent-v15.sql", output_path)

    assert output_path.read_text() == "pre-existing governed content"
    assert not (tmp_path / "ECOM_Physical_Data_Model_v1_6.sql.tmp").exists()


def test_refuses_to_overwrite_or_delete_existing_temp_file(tmp_path: Path) -> None:
    output_path = tmp_path / "ECOM_Physical_Data_Model_v1_6.sql"
    tmp_file = tmp_path / "ECOM_Physical_Data_Model_v1_6.sql.tmp"
    tmp_file.write_text("some other process's in-progress temp file")

    with pytest.raises(ReleaseGenerationError, match="existing temp file"):
        generate(tmp_path / "nonexistent-v13.sql", tmp_path / "nonexistent-v15.sql", output_path)

    assert tmp_file.read_text() == "some other process's in-progress temp file"
    assert not output_path.exists()


def test_canonical_block_anchor_regression_against_real_v13_v15() -> None:
    """Regression test for the exact failure hit during development: the
    anchor must locate v1.5's embedded canonical block correctly (it
    previously mis-anchored into the middle of the CDD-013 audit block)."""
    v13 = DEFAULT_V13.read_text()
    v15 = DEFAULT_V15.read_text()

    combined, old_boundary_idx, join_end_v15 = _verify_canonical_block_unchanged(v15, v13)

    assert combined.startswith(
        "-- ============================================================\n"
        "-- ECOM Physical Data Model -- PostgreSQL 15+ DDL -- v1.3"
    )
    assert "api_security_audit_events" not in combined
    for table in CANONICAL_TABLE_NAMES:
        assert re.search(rf"CREATE TABLE {table} \(", combined), f"missing canonical table {table}"
    assert len(re.findall(r"CREATE TABLE \w+ \(", combined)) == 32
    for table in RUNTIME_TABLES:
        assert table not in combined, f"{table} leaked into the canonical block"

    assert 0 < join_end_v15 < old_boundary_idx < len(v15)


def test_canonical_block_anchor_does_not_depend_on_fixed_line_positions() -> None:
    """Prove the anchor is content-anchored (via .index() on marker text),
    not position-anchored: shifting every line before the canonical marker
    must not change the extracted canonical content at all."""
    v13 = DEFAULT_V13.read_text()
    v15 = DEFAULT_V15.read_text()

    baseline_combined, _baseline_boundary, _baseline_join = _verify_canonical_block_unchanged(v15, v13)

    marker = "-- ECOM Physical Data Model -- PostgreSQL 15+ DDL -- v1.3"
    marker_idx = v15.index(marker)
    shifted_v15 = (
        v15[:marker_idx]
        + "-- an extra unrelated comment line inserted purely to shift line numbers\n\n\n"
        + v15[marker_idx:]
    )
    assert shifted_v15.count("\n", 0, shifted_v15.index(marker)) != v15.count(
        "\n", 0, v15.index(marker)
    ), "test setup must actually change the line number of the marker"

    shifted_combined, _shifted_boundary, _shifted_join = _verify_canonical_block_unchanged(
        shifted_v15, v13
    )
    assert shifted_combined == baseline_combined


def test_no_stray_temp_file_survives_in_the_release_directory() -> None:
    """A .tmp file should never linger here: a successful run moves it to
    the final path, and a failed run deletes it (see the refusal tests
    above). This holds permanently, unlike checking that the final release
    file itself doesn't exist yet, which was only ever true before the real
    v1.6 artifact was first generated."""
    release_dir = Path(__file__).resolve().parents[1] / "architecture" / "released" / "v1.8"
    tmp_path_ = release_dir / "ECOM_Physical_Data_Model_v1_6.sql.tmp"
    assert not tmp_path_.exists(), "a prior attempt left a temp file behind"
