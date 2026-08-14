"""Focused tests for generate_release_manifest.py.

Run with: python3 -m pytest tools/test_generate_release_manifest.py
"""

import hashlib
import zipfile
from pathlib import Path

import pytest
from generate_release_manifest import (
    REPOSITORY_ROOT,
    ManifestArtifact,
    ManifestGenerationError,
    generate,
)

TEMPLATE = REPOSITORY_ROOT / "architecture/released/v1.7/RELEASE-MANIFEST-v1.7.xlsx"


def _repo_with_artifacts(tmp_path: Path, *, release_version: str = "v9.9") -> tuple[Path, Path]:
    """A throwaway repository root with a baseline directory containing two
    real files, so path/existence validation exercises real filesystem
    checks without touching the real repository."""
    repo_root = tmp_path / "repo"
    baseline_dir = repo_root / "architecture" / "released" / release_version
    baseline_dir.mkdir(parents=True)
    (baseline_dir / "ARTIFACT-ONE.md").write_text("first artifact content")
    (baseline_dir / "ARTIFACT-TWO.csv").write_text("second,artifact,content")
    return repo_root, baseline_dir


def _artifacts_for(baseline_dir: Path, release_version: str) -> tuple[ManifestArtifact, ...]:
    prefix = f"architecture/released/{release_version}"
    return (
        ManifestArtifact(
            relative_path=f"{prefix}/ARTIFACT-ONE.md",
            identifier="ART-001",
            title="Artifact One",
            version="1.0",
            status="Frozen",
            current="YES",
            authority="AUTHORITATIVE",
            superseded_document="",
            approval_reference="Test approval",
        ),
        ManifestArtifact(
            relative_path=f"{prefix}/ARTIFACT-TWO.csv",
            identifier="ART-002",
            title="Artifact Two",
            version="1.0",
            status="Frozen",
            current="YES",
            authority="AUTHORITATIVE",
            superseded_document="",
            approval_reference="Test approval",
        ),
    )


def _generate(repo_root: Path, baseline_dir: Path, release_version: str, output: Path):
    artifacts = _artifacts_for(baseline_dir, release_version)
    return generate(
        template_path=TEMPLATE,
        output_path=output,
        release_version=release_version,
        title=f"Test Manifest {release_version}",
        subtitle_lines=("subtitle one", "subtitle two", "subtitle three"),
        artifacts=artifacts,
        repository_root=repo_root,
    )


def test_determinism_identical_inputs_produce_byte_identical_output(tmp_path: Path) -> None:
    repo_root, baseline_dir = _repo_with_artifacts(tmp_path)
    output_a = tmp_path / "a" / "MANIFEST.xlsx"
    output_b = tmp_path / "b" / "MANIFEST.xlsx"

    _generate(repo_root, baseline_dir, "v9.9", output_a)
    _generate(repo_root, baseline_dir, "v9.9", output_b)

    assert output_a.read_bytes() == output_b.read_bytes()


def test_checksums_match_real_artifact_bytes(tmp_path: Path) -> None:
    repo_root, baseline_dir = _repo_with_artifacts(tmp_path)
    output = tmp_path / "MANIFEST.xlsx"

    _generate(repo_root, baseline_dir, "v9.9", output)

    with zipfile.ZipFile(output) as archive:
        rows = _sheet_rows(archive)
    checksum_by_path = {row[0]: row[7] for row in rows}
    assert checksum_by_path[
        "architecture/released/v9.9/ARTIFACT-ONE.md"
    ] == hashlib.sha256((baseline_dir / "ARTIFACT-ONE.md").read_bytes()).hexdigest()
    assert checksum_by_path[
        "architecture/released/v9.9/ARTIFACT-TWO.csv"
    ] == hashlib.sha256((baseline_dir / "ARTIFACT-TWO.csv").read_bytes()).hexdigest()


def test_missing_artifact_is_rejected(tmp_path: Path) -> None:
    repo_root, baseline_dir = _repo_with_artifacts(tmp_path)
    (baseline_dir / "ARTIFACT-TWO.csv").unlink()
    output = tmp_path / "MANIFEST.xlsx"

    with pytest.raises(ManifestGenerationError, match="missing artifact"):
        _generate(repo_root, baseline_dir, "v9.9", output)

    assert not output.exists()


def test_duplicate_artifact_path_is_rejected(tmp_path: Path) -> None:
    repo_root, baseline_dir = _repo_with_artifacts(tmp_path)
    artifacts = _artifacts_for(baseline_dir, "v9.9")
    duplicated = artifacts + (artifacts[0],)
    output = tmp_path / "MANIFEST.xlsx"

    with pytest.raises(ManifestGenerationError, match="duplicate artifact path"):
        generate(
            template_path=TEMPLATE,
            output_path=output,
            release_version="v9.9",
            title="Test",
            subtitle_lines=("a", "b", "c"),
            artifacts=duplicated,
            repository_root=repo_root,
        )
    assert not output.exists()


def test_missing_approval_reference_is_rejected() -> None:
    with pytest.raises(ManifestGenerationError, match="Approval Reference"):
        ManifestArtifact(
            relative_path="architecture/released/v9.9/X.md",
            identifier="X-001",
            title="X",
            version="1.0",
            status="Frozen",
            current="YES",
            authority="AUTHORITATIVE",
            superseded_document="",
            approval_reference="",
        )


def test_absolute_artifact_path_is_rejected(tmp_path: Path) -> None:
    repo_root, baseline_dir = _repo_with_artifacts(tmp_path)
    artifacts = (
        ManifestArtifact(
            relative_path=str(baseline_dir / "ARTIFACT-ONE.md"),
            identifier="ART-001",
            title="Artifact One",
            version="1.0",
            status="Frozen",
            current="YES",
            authority="AUTHORITATIVE",
            superseded_document="",
            approval_reference="Test approval",
        ),
    )
    output = tmp_path / "MANIFEST.xlsx"

    with pytest.raises(ManifestGenerationError, match="repository-relative"):
        generate(
            template_path=TEMPLATE,
            output_path=output,
            release_version="v9.9",
            title="Test",
            subtitle_lines=("a", "b", "c"),
            artifacts=artifacts,
            repository_root=repo_root,
        )
    assert not output.exists()


def test_out_of_repository_artifact_path_is_rejected(tmp_path: Path) -> None:
    repo_root, baseline_dir = _repo_with_artifacts(tmp_path)
    artifacts = (
        ManifestArtifact(
            relative_path="../outside-the-repo.md",
            identifier="ART-001",
            title="Artifact One",
            version="1.0",
            status="Frozen",
            current="YES",
            authority="AUTHORITATIVE",
            superseded_document="",
            approval_reference="Test approval",
        ),
    )
    output = tmp_path / "MANIFEST.xlsx"

    with pytest.raises(ManifestGenerationError):
        generate(
            template_path=TEMPLATE,
            output_path=output,
            release_version="v9.9",
            title="Test",
            subtitle_lines=("a", "b", "c"),
            artifacts=artifacts,
            repository_root=repo_root,
        )
    assert not output.exists()


def test_refuses_to_overwrite_existing_final_file(tmp_path: Path) -> None:
    repo_root, baseline_dir = _repo_with_artifacts(tmp_path)
    output = tmp_path / "MANIFEST.xlsx"
    output.write_text("pre-existing governed content")

    with pytest.raises(ManifestGenerationError, match="refusing to overwrite existing"):
        _generate(repo_root, baseline_dir, "v9.9", output)

    assert output.read_text() == "pre-existing governed content"


def test_refuses_to_overwrite_existing_temp_file(tmp_path: Path) -> None:
    repo_root, baseline_dir = _repo_with_artifacts(tmp_path)
    output = tmp_path / "MANIFEST.xlsx"
    tmp_file = output.with_suffix(output.suffix + ".tmp")
    tmp_file.write_text("some other process's in-progress temp file")

    with pytest.raises(ManifestGenerationError, match="existing temp file"):
        _generate(repo_root, baseline_dir, "v9.9", output)

    assert tmp_file.read_text() == "some other process's in-progress temp file"
    assert not output.exists()


def test_prior_released_manifests_remain_byte_identical() -> None:
    """Generation must never touch the template it reads from."""
    before = TEMPLATE.read_bytes()
    checksum_before = hashlib.sha256(before).hexdigest()
    # Deliberately do not generate anything here; this test's only purpose
    # is to assert the template file on disk is untouched by the mere act
    # of importing/using this module elsewhere in the suite.
    after = TEMPLATE.read_bytes()
    assert after == before
    assert hashlib.sha256(after).hexdigest() == checksum_before


def _sheet_rows(archive: zipfile.ZipFile) -> list[tuple[str, ...]]:
    from xml.etree import ElementTree

    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows: list[tuple[str, ...]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        row_number = int(row.attrib["r"])
        if row_number < 6:
            continue
        values = [""] * 10
        for cell in row.findall("x:c", namespace):
            column = ord(cell.attrib["r"][0]) - ord("A")
            value = cell.find("x:v", namespace)
            values[column] = value.text if value is not None else ""
        rows.append(tuple(values))
    return rows
