"""Verify CTEC Architecture Release Manifests without third-party dependencies."""

from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = REPOSITORY_ROOT / "architecture" / "released"
ARCHITECTURE_REGISTRY = REPOSITORY_ROOT / "architecture" / "INDEX.md"
BASELINES = ("v1.0", "v1.1")
HEADERS = (
    "Relative Path",
    "Document Identifier",
    "Document Title",
    "Semantic Version",
    "Status",
    "SHA-256 Checksum",
    "Superseded Document",
    "Approval Reference",
)
ALLOWED_STATUSES = {"Development", "Frozen", "Superseded", "Historical"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
XML_NAMESPACE = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _cell_column(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    value = 0
    for character in letters:
        value = value * 26 + ord(character.upper()) - ord("A") + 1
    return value - 1


def _manifest_rows(manifest: Path) -> list[tuple[str, ...]]:
    with zipfile.ZipFile(manifest) as archive:
        root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[tuple[str, ...]] = []
    for row in root.findall(".//x:sheetData/x:row", XML_NAMESPACE):
        row_number = int(row.attrib["r"])
        if row_number < 5:
            continue
        values = [""] * len(HEADERS)
        for cell in row.findall("x:c", XML_NAMESPACE):
            column = _cell_column(cell.attrib["r"])
            if column >= len(values):
                continue
            value = cell.find("x:v", XML_NAMESPACE)
            values[column] = (
                value.text if value is not None and value.text is not None else ""
            )
        rows.append(tuple(values))
    return rows


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_baseline(baseline: str) -> int:
    directory = RELEASE_ROOT / baseline
    manifest = directory / f"RELEASE-MANIFEST-{baseline}.xlsx"
    if not manifest.is_file():
        raise ValueError(f"{baseline}: missing {manifest.relative_to(REPOSITORY_ROOT)}")

    registry_line = next(
        (
            line
            for line in ARCHITECTURE_REGISTRY.read_text().splitlines()
            if line.startswith(f"| {baseline} |") and manifest.name in line
        ),
        "",
    )
    registered_checksum = re.search(r"`([0-9a-f]{64})`", registry_line)
    if registered_checksum is None:
        raise ValueError(
            f"{baseline}: manifest checksum is not pinned in architecture/INDEX.md"
        )
    actual_manifest_checksum = _checksum(manifest)
    if actual_manifest_checksum != registered_checksum.group(1):
        raise ValueError(
            f"{baseline}: manifest checksum mismatch: expected "
            f"{registered_checksum.group(1)}, got {actual_manifest_checksum}"
        )

    rows = _manifest_rows(manifest)
    if not rows or rows[0] != HEADERS:
        raise ValueError(
            f"{baseline}: manifest headers do not match the governed schema"
        )

    records = rows[1:]
    recorded_paths: set[Path] = set()
    for row_number, row in enumerate(records, start=6):
        relative, identifier, title, version, status, expected, _, approval = row
        missing = [
            name
            for name, value in zip(HEADERS, row, strict=True)
            if name != "Superseded Document" and not value
        ]
        if missing:
            raise ValueError(
                f"{baseline}: row {row_number} missing {', '.join(missing)}"
            )
        if status not in ALLOWED_STATUSES:
            raise ValueError(
                f"{baseline}: row {row_number} has invalid status {status!r}"
            )
        if not SHA256_PATTERN.fullmatch(expected):
            raise ValueError(f"{baseline}: row {row_number} has invalid SHA-256")
        if not identifier or not title or not version or not approval:
            raise ValueError(
                f"{baseline}: row {row_number} has incomplete governance metadata"
            )

        artifact = (REPOSITORY_ROOT / relative).resolve()
        if REPOSITORY_ROOT not in artifact.parents:
            raise ValueError(f"{baseline}: row {row_number} escapes the repository")
        if artifact.parent != directory.resolve():
            raise ValueError(
                f"{baseline}: row {row_number} belongs to another baseline"
            )
        if artifact == manifest.resolve():
            raise ValueError(
                f"{baseline}: manifest must not contain a self-checksum row"
            )
        if artifact in recorded_paths:
            raise ValueError(f"{baseline}: duplicate artifact {relative}")
        if not artifact.is_file():
            raise ValueError(f"{baseline}: missing artifact {relative}")
        actual = _checksum(artifact)
        if actual != expected:
            raise ValueError(
                f"{baseline}: checksum mismatch for {relative}: expected {expected}, got {actual}"
            )
        recorded_paths.add(artifact)

    actual_paths = {
        item.resolve()
        for item in directory.iterdir()
        if item.is_file() and item.resolve() != manifest.resolve()
    }
    omitted = actual_paths - recorded_paths
    unexpected = recorded_paths - actual_paths
    if omitted or unexpected:
        details = [
            *(
                f"unregistered: {path.relative_to(REPOSITORY_ROOT)}"
                for path in sorted(omitted)
            ),
            *(
                f"missing: {path.relative_to(REPOSITORY_ROOT)}"
                for path in sorted(unexpected)
            ),
        ]
        raise ValueError(
            f"{baseline}: manifest coverage mismatch; " + "; ".join(details)
        )

    print(f"{baseline}: verified {len(records)} artifacts")
    return len(records)


def main() -> int:
    try:
        total = sum(verify_baseline(baseline) for baseline in BASELINES)
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        print(f"Architecture release verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Architecture release verification passed: {total} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
