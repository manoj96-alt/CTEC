"""Verify CTEC Architecture Release Manifests without third-party dependencies."""

from __future__ import annotations

import hashlib
import csv
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = REPOSITORY_ROOT / "architecture" / "released"
ARCHITECTURE_REGISTRY = REPOSITORY_ROOT / "architecture" / "INDEX.md"
DEPENDENCY_MATRIX = RELEASE_ROOT / "v1.8" / "DEPENDENCY-MATRIX-v1.8.csv"
BASELINES = ("v1.0", "v1.1", "v1.2", "v1.3", "v1.4", "v1.5", "v1.6", "v1.7", "v1.8")
HEADERS = (
    "Relative Path",
    "Document Identifier",
    "Document Title",
    "Semantic Version",
    "Status",
    "Current",
    "Authority",
    "SHA-256 Checksum",
    "Superseded Document",
    "Approval Reference",
)
ALLOWED_STATUSES = {"Development", "Frozen", "Superseded", "Historical"}
VALID_GOVERNANCE = {
    ("Frozen", "YES", "AUTHORITATIVE"),
    ("Development", "NO", "NON-AUTHORITATIVE"),
    ("Superseded", "NO", "NON-AUTHORITATIVE"),
    ("Historical", "NO", "NON-AUTHORITATIVE"),
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
XML_NAMESPACE = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _registry_rows() -> list[tuple[str, dict[str, str]]]:
    rows: list[tuple[str, dict[str, str]]] = []
    section = ""
    headers: list[str] = []
    for line in ARCHITECTURE_REGISTRY.read_text().splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            headers = []
            continue
        if not line.startswith("|"):
            continue
        cells = [value.strip() for value in line[1:-1].split("|")]
        if all(re.fullmatch(r":?-+:?", value) for value in cells):
            continue
        if not headers:
            headers = cells
            continue
        if len(cells) == len(headers):
            rows.append((section, dict(zip(headers, cells, strict=True))))
    return rows


def _registry_release_entries() -> dict[str, str]:
    entries: dict[str, str] = {}
    governance_rows = 0
    current_by_identifier: dict[str, int] = {}
    for section, row in _registry_rows():
        status_raw = row.get("Status", "")
        current = row.get("Current", "")
        authority = row.get("Authority", "")
        if status_raw and (current or authority):
            name = row.get("Document") or row.get("Artifact") or row.get("Review Artifact") or row.get("Registry Version")
            if not name or not current or not authority:
                raise ValueError(f"registry entry in {section!r} is missing Status, Current, or Authority")
            status = status_raw.title()
            if status not in ALLOWED_STATUSES or (status, current, authority) not in VALID_GOVERNANCE:
                raise ValueError(
                    f"registry artifact {name!r} has invalid governance combination "
                    f"{status_raw} + {current} + {authority}"
                )
            governance_rows += 1
        location_value = row.get("Location", "")
        location = re.search(r"\]\((released/v1\.\d+/[^)]+)\)", location_value)
        if location is None:
            continue
        name = row.get("Document") or row.get("Artifact") or row.get("Review Artifact")
        status = status_raw.title()
        if status == "Superseded" and not row.get("Superseded By", "").strip(" —"):
            raise ValueError(f"superseded registry artifact {name!r} has no replacement")
        if section.startswith("Authoritative artifacts"):
            identifier = _registry_identifier(name)
            current_by_identifier[identifier] = current_by_identifier.get(identifier, 0) + 1
        entries[location.group(1).replace("%20", " ")] = status
    duplicates = sorted(identifier for identifier, count in current_by_identifier.items() if count != 1)
    if duplicates:
        raise ValueError(f"registry does not contain exactly one current authority for: {', '.join(duplicates)}")
    print(f"Registry governance verified: {governance_rows} entries; zero invalid combinations")
    return entries


def _registry_identifier(name: str) -> str:
    match = re.match(r"([A-Z]+-\d{3}|CDD Template|Enterprise Constitution|ECOM Physical Data Model)", name)
    return match.group(1) if match else name


def _registry_artifacts() -> tuple[dict[str, tuple[str, str, str]], dict[str, set[str]]]:
    current: dict[str, tuple[str, str, str]] = {}
    superseded: dict[str, set[str]] = {}
    for section, row in _registry_rows():
        location = re.search(r"\]\((released/v1\.\d+/[^)]+)\)", row.get("Location", ""))
        if location is None:
            continue
        name = row.get("Document") or row.get("Artifact") or row.get("Review Artifact") or ""
        identifier = _registry_identifier(name)
        if section.startswith("Authoritative artifacts"):
            current[identifier] = (row["Version"], row["Status"], location.group(1).replace("%20", " "))
        elif section.startswith("Historical baseline"):
            superseded.setdefault(identifier, set()).add(row["Version"])
    return current, superseded


def _docx_blocks(path: Path) -> list[str]:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    blocks: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        blocks.append("".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)))
    # A dependency identifier and version are frequently stored in adjacent
    # Word table cells. Preserve each row as an additional searchable block so
    # stale references cannot evade validation merely because XML separates
    # the identifier and version into different paragraphs.
    for row in root.findall(".//w:tr", namespace):
        cells = [
            "".join(node.text or "" for node in cell.findall(".//w:t", namespace)).strip()
            for cell in row.findall("./w:tc", namespace)
        ]
        blocks.append(" | ".join(value for value in cells if value))
    return blocks


def _artifact_blocks(path: Path) -> list[str]:
    if path.suffix.lower() == ".docx":
        return _docx_blocks(path)
    if path.suffix.lower() in {".md", ".csv", ".sql"}:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    return []


def verify_dependencies() -> int:
    current, superseded = _registry_artifacts()
    if not DEPENDENCY_MATRIX.is_file():
        raise ValueError("missing governed Architecture Dependency Matrix")

    with DEPENDENCY_MATRIX.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = {
        "Dependent Identifier",
        "Dependent Version",
        "Dependency Identifier",
        "Dependency Version",
        "Dependency Status",
        "Relationship",
        "Semantic Compatibility",
        "Approval Reference",
    }
    if not rows or set(rows[0]) != required:
        raise ValueError("Architecture Dependency Matrix schema is invalid or empty")

    for number, row in enumerate(rows, start=2):
        missing = [name for name in required if not row.get(name, "").strip()]
        if missing:
            raise ValueError(f"dependency matrix row {number} missing {', '.join(sorted(missing))}")
        dependent = row["Dependent Identifier"]
        dependency = row["Dependency Identifier"]
        if dependent not in current:
            raise ValueError(f"dependency matrix row {number}: dependent {dependent!r} is not current")
        if dependency not in current:
            raise ValueError(f"dependency matrix row {number}: dependency {dependency!r} is not current")
        dependent_version, dependent_status, _ = current[dependent]
        dependency_version, dependency_status, _ = current[dependency]
        if row["Dependent Version"] != dependent_version:
            raise ValueError(f"dependency matrix row {number}: {dependent} version mismatch")
        if row["Dependency Version"] != dependency_version:
            raise ValueError(f"dependency matrix row {number}: {dependency} version mismatch")
        if dependent_status != "FROZEN" or dependency_status != "FROZEN" or row["Dependency Status"] != "FROZEN":
            raise ValueError(f"dependency matrix row {number}: dependency authority is not Frozen")
        if row["Semantic Compatibility"] != "Compatible":
            raise ValueError(f"dependency matrix row {number}: semantic compatibility is not approved")

    stale_findings: list[str] = []
    for identifier, (version, status, relative) in current.items():
        if status != "FROZEN":
            continue
        path = REPOSITORY_ROOT / "architecture" / relative
        blocks = _artifact_blocks(path)
        joined = "\n".join(blocks)
        if path.suffix.lower() == ".docx" and not re.search(
            rf"Version\s*:?[\s|]*{re.escape(version)}(?![\d.])", joined, re.IGNORECASE
        ):
            stale_findings.append(f"{identifier}: document metadata does not contain Registry version {version}")
        for referenced_identifier, versions in superseded.items():
            if referenced_identifier == identifier:
                continue
            for old_version in versions:
                pattern = re.compile(
                    rf"\b{re.escape(referenced_identifier)}\s+(?:v|Version\s*){re.escape(old_version)}\b",
                    re.IGNORECASE,
                )
                for block in blocks:
                    if pattern.search(block) and not re.search(
                        r"\b(historical|superseded|resolved by|revision history)\b",
                        block,
                        re.IGNORECASE,
                    ):
                        stale_findings.append(
                            f"{identifier}: stale dependency reference {referenced_identifier} {old_version}: {block[:160]}"
                        )
    if stale_findings:
        raise ValueError("authoritative dependency scan failed; " + "; ".join(stale_findings))

    print(f"Dependency reconciliation verified: {len(rows)} approved relationships")
    return len(rows)


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
            if value is not None and value.text is not None:
                values[column] = value.text
            else:
                inline = cell.find("x:is/x:t", XML_NAMESPACE)
                values[column] = (
                    inline.text if inline is not None and inline.text is not None else ""
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
        relative, identifier, title, version, status, current, authority, expected, _, approval = row
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
        if (status, current, authority) not in VALID_GOVERNANCE:
            raise ValueError(
                f"{baseline}: row {row_number} has invalid governance combination "
                f"{status} + {current} + {authority}"
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
        registry_entries = _registry_release_entries()
        total = sum(verify_baseline(baseline) for baseline in BASELINES)
        verify_dependencies()
        if not registry_entries:
            raise ValueError("Architecture Registry contains no governed release entries")
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        print(f"Architecture release verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Architecture release verification passed: {total} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
