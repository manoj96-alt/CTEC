"""Focused tests for generate_ead_release.py.

Run with: python3 -m pytest tools/test_generate_ead_release.py
"""

import json
from pathlib import Path

import pytest
from generate_ead_release import EadGenerationError, generate

SOURCE_ROWS = [
    {"row": 1, "Entity": "Enterprise", "Attribute Name": "enterprise_id"},
    {"row": 2, "Entity": "Enterprise Entity", "Attribute Name": "enterprise_entity_id"},
    {"row": 3, "Entity": "Source System", "Attribute Name": "source_system_id"},
    {"row": 4, "Entity": "Source Object", "Attribute Name": "source_object_id"},
]
NEW_ATTRIBUTE_ROWS = (
    ("Enterprise Entity", "Operational"),
    ("Source System", "Integration"),
    ("Source Object", "Integration"),
)


def _write_source(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "EAD-source.json"
    path.write_text(json.dumps(rows))
    return path


def test_successful_generation_produces_expected_row_count(tmp_path: Path) -> None:
    source = _write_source(tmp_path, SOURCE_ROWS)
    output = tmp_path / "EAD-output.json"

    result_path = generate(
        source, output, expected_source_rows=len(SOURCE_ROWS), new_attribute_rows=NEW_ATTRIBUTE_ROWS
    )

    assert result_path == output
    rows = json.loads(output.read_text())
    assert len(rows) == len(SOURCE_ROWS) + len(NEW_ATTRIBUTE_ROWS)
    tenant_id_pairs = {
        (r["Entity"], r["Attribute Name"]) for r in rows if r["Attribute Name"] == "tenant_id"
    }
    assert tenant_id_pairs == {(entity, "tenant_id") for entity, _ in NEW_ATTRIBUTE_ROWS}
    assert not output.with_suffix(output.suffix + ".tmp").exists()
    # source untouched
    assert json.loads(source.read_text()) == SOURCE_ROWS


def test_missing_source_entity_is_rejected(tmp_path: Path) -> None:
    rows = [r for r in SOURCE_ROWS if r["Entity"] != "Source Object"]
    source = _write_source(tmp_path, rows)
    output = tmp_path / "EAD-output.json"

    with pytest.raises(EadGenerationError, match="not found in source EAD dictionary"):
        generate(source, output, expected_source_rows=len(rows), new_attribute_rows=NEW_ATTRIBUTE_ROWS)

    assert not output.exists()
    assert not output.with_suffix(output.suffix + ".tmp").exists()


def test_duplicate_entity_attribute_pair_is_rejected(tmp_path: Path) -> None:
    rows = [*SOURCE_ROWS, {"row": 5, "Entity": "Enterprise Entity", "Attribute Name": "tenant_id"}]
    source = _write_source(tmp_path, rows)
    output = tmp_path / "EAD-output.json"

    with pytest.raises(EadGenerationError, match="already exists in source EAD dictionary"):
        generate(source, output, expected_source_rows=len(rows), new_attribute_rows=NEW_ATTRIBUTE_ROWS)

    assert not output.exists()
    assert not output.with_suffix(output.suffix + ".tmp").exists()


def test_refuses_to_overwrite_existing_final_file(tmp_path: Path) -> None:
    source = _write_source(tmp_path, SOURCE_ROWS)
    output = tmp_path / "EAD-output.json"
    output.write_text("pre-existing governed content")

    with pytest.raises(EadGenerationError, match="refusing to overwrite existing"):
        generate(source, output, expected_source_rows=len(SOURCE_ROWS), new_attribute_rows=NEW_ATTRIBUTE_ROWS)

    assert output.read_text() == "pre-existing governed content"


def test_refuses_to_overwrite_existing_temp_file(tmp_path: Path) -> None:
    source = _write_source(tmp_path, SOURCE_ROWS)
    output = tmp_path / "EAD-output.json"
    tmp_file = output.with_suffix(output.suffix + ".tmp")
    tmp_file.write_text("some other process's in-progress temp file")

    with pytest.raises(EadGenerationError, match="existing temp file"):
        generate(source, output, expected_source_rows=len(SOURCE_ROWS), new_attribute_rows=NEW_ATTRIBUTE_ROWS)

    assert tmp_file.read_text() == "some other process's in-progress temp file"
    assert not output.exists()


def test_malformed_source_json_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "EAD-source.json"
    source.write_text("{not valid json")
    output = tmp_path / "EAD-output.json"

    with pytest.raises(EadGenerationError, match="not valid JSON"):
        generate(source, output, expected_source_rows=len(SOURCE_ROWS), new_attribute_rows=NEW_ATTRIBUTE_ROWS)

    assert not output.exists()
    assert not output.with_suffix(output.suffix + ".tmp").exists()


def test_identical_inputs_produce_byte_identical_output(tmp_path: Path) -> None:
    source = _write_source(tmp_path, SOURCE_ROWS)
    output_a = tmp_path / "a" / "EAD-output.json"
    output_b = tmp_path / "b" / "EAD-output.json"

    generate(source, output_a, expected_source_rows=len(SOURCE_ROWS), new_attribute_rows=NEW_ATTRIBUTE_ROWS)
    generate(source, output_b, expected_source_rows=len(SOURCE_ROWS), new_attribute_rows=NEW_ATTRIBUTE_ROWS)

    assert output_a.read_bytes() == output_b.read_bytes()
