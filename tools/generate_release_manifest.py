"""Generate a CTEC Architecture Release Manifest (.xlsx), matching exactly the
reader contract in scripts/verify_architecture_release.py, using only the
Python standard library.

Reusable across releases: every release-specific value (version, title,
artifact inventory) is an explicit input, not hardcoded. An existing released
manifest is used as a read-only layout/style template -- its non-data parts
([Content_Types].xml, _rels/.rels, xl/workbook.xml,
xl/_rels/workbook.xml.rels, xl/styles.xml, xl/theme/theme1.xml,
xl/sharedStrings.xml) are copied byte-for-byte; only xl/worksheets/sheet1.xml
is regenerated. The template is opened read-only and never written to.

Determinism: given the same template and inputs, output is byte-identical --
stable row ordering (sorted by relative path), stable XML attribute/element
ordering (built from fixed string templates, not dict iteration), fixed ZIP
entry timestamps (1980-01-01, the DOS epoch), fixed ZIP part order, no
current-time metadata, no random identifiers, no machine-specific paths (all
paths are resolved relative to the repository root).

No macros, formulas, external links, hidden sheets, or remote resources are
ever written -- every artifact cell is a plain literal string
(`t="str"` with the text directly in `<x:v>`), matching the same encoding the
verifier's reader expects and every prior manifest already uses.
"""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = REPOSITORY_ROOT / "architecture/released/v1.7/RELEASE-MANIFEST-v1.7.xlsx"

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
FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
TEMPLATE_PASSTHROUGH_PARTS = (
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/styles.xml",
    "xl/theme/theme1.xml",
    "xl/sharedStrings.xml",
)
XML_NAMESPACE = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
TITLE_STYLE = "2"
SUBTITLE_STYLE = "4"
HEADER_STYLE = "7"
DATA_ROW_STYLE = "11"


class ManifestGenerationError(Exception):
    """Raised for any condition that must abort manifest generation."""


@dataclass(frozen=True, slots=True)
class ManifestArtifact:
    relative_path: str
    identifier: str
    title: str
    version: str
    status: str
    current: str
    authority: str
    superseded_document: str
    approval_reference: str

    def __post_init__(self) -> None:
        required = {
            "Relative Path": self.relative_path,
            "Document Identifier": self.identifier,
            "Document Title": self.title,
            "Semantic Version": self.version,
            "Status": self.status,
            "Current": self.current,
            "Authority": self.authority,
            "Approval Reference": self.approval_reference,
        }
        missing = [name for name, value in required.items() if not value or not value.strip()]
        if missing:
            raise ManifestGenerationError(
                f"artifact {self.relative_path or '<empty>'!r} missing required column(s): "
                f"{', '.join(missing)}"
            )
        if self.status not in ALLOWED_STATUSES:
            raise ManifestGenerationError(
                f"artifact {self.relative_path!r} has invalid status {self.status!r}"
            )
        if (self.status, self.current, self.authority) not in VALID_GOVERNANCE:
            raise ManifestGenerationError(
                f"artifact {self.relative_path!r} has invalid governance combination "
                f"{self.status} + {self.current} + {self.authority}"
            )


def _column_letter(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _literal_cell(column: int, row: int, style: str, value: str) -> str:
    ref = f"{_column_letter(column)}{row}"
    return f'<x:c r="{ref}" s="{style}" t="str"><x:v>{escape(value)}</x:v></x:c>'


def _empty_cell(column: int, row: int, style: str) -> str:
    ref = f"{_column_letter(column)}{row}"
    return f'<x:c r="{ref}" s="{style}" />'


def _title_row(row: int, text: str, style: str) -> str:
    cells = [_literal_cell(0, row, style, text)]
    cells.extend(_empty_cell(col, row, style) for col in range(1, len(HEADERS)))
    return f'<x:row r="{row}">' + "".join(cells) + "</x:row>"


def _data_row(row: int, values: tuple[str, ...], style: str) -> str:
    cells = [_literal_cell(col, row, style, value) for col, value in enumerate(values)]
    return f'<x:row r="{row}">' + "".join(cells) + "</x:row>"


def _build_sheet_xml(
    title: str,
    subtitle_lines: tuple[str, str, str],
    artifacts: tuple[ManifestArtifact, ...],
    checksums: dict[str, str],
) -> str:
    rows = [
        _title_row(1, title, TITLE_STYLE),
        _title_row(2, subtitle_lines[0], SUBTITLE_STYLE),
        _title_row(3, subtitle_lines[1], SUBTITLE_STYLE),
        _title_row(4, subtitle_lines[2], SUBTITLE_STYLE),
        _data_row(5, HEADERS, HEADER_STYLE),
    ]
    for offset, artifact in enumerate(artifacts):
        rows.append(
            _data_row(
                6 + offset,
                (
                    artifact.relative_path,
                    artifact.identifier,
                    artifact.title,
                    artifact.version,
                    artifact.status,
                    artifact.current,
                    artifact.authority,
                    checksums[artifact.relative_path],
                    artifact.superseded_document,
                    artifact.approval_reference,
                ),
                DATA_ROW_STYLE,
            )
        )
    sheet_data = "<x:sheetData>" + "".join(rows) + "</x:sheetData>"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<x:worksheet xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<x:sheetViews><x:sheetView showGridLines="0" workbookViewId="0" /></x:sheetViews>'
        '<x:sheetFormatPr defaultRowHeight="15" />'
        f"{sheet_data}"
        "</x:worksheet>"
    )


def _validate_template(template_path: Path) -> None:
    if not template_path.is_file():
        raise ManifestGenerationError(f"template manifest not found: {template_path}")
    try:
        with zipfile.ZipFile(template_path) as archive:
            names = set(archive.namelist())
            for part in (*TEMPLATE_PASSTHROUGH_PARTS, "xl/worksheets/sheet1.xml"):
                if part not in names:
                    raise ManifestGenerationError(f"template manifest is missing expected part: {part}")
            root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    except zipfile.BadZipFile as error:
        raise ManifestGenerationError(f"template manifest is not a valid zip/xlsx: {error}") from error

    header_cells = []
    for row in root.findall(".//x:sheetData/x:row", XML_NAMESPACE):
        if row.attrib.get("r") == "5":
            for cell in row.findall("x:c", XML_NAMESPACE):
                value = cell.find("x:v", XML_NAMESPACE)
                header_cells.append(value.text if value is not None else "")
            break
    if tuple(header_cells) != HEADERS:
        raise ManifestGenerationError(
            f"template manifest row 5 does not match the governed header schema: {header_cells}"
        )


def _validate_artifacts(
    artifacts: tuple[ManifestArtifact, ...], *, release_version: str, repository_root: Path
) -> None:
    if not artifacts:
        raise ManifestGenerationError("at least one artifact is required")

    seen_paths: set[str] = set()
    expected_dir = (repository_root / "architecture" / "released" / release_version).resolve()
    for artifact in artifacts:
        if artifact.relative_path in seen_paths:
            raise ManifestGenerationError(f"duplicate artifact path: {artifact.relative_path}")
        seen_paths.add(artifact.relative_path)

        relative = Path(artifact.relative_path)
        if relative.is_absolute():
            raise ManifestGenerationError(
                f"artifact path must be repository-relative, not absolute: {artifact.relative_path}"
            )
        resolved = (repository_root / relative).resolve()
        if repository_root not in resolved.parents and resolved != repository_root:
            raise ManifestGenerationError(f"artifact path escapes the repository: {artifact.relative_path}")
        if resolved.parent != expected_dir:
            raise ManifestGenerationError(
                f"artifact {artifact.relative_path!r} does not belong to baseline directory "
                f"architecture/released/{release_version}/"
            )
        if not resolved.is_file():
            raise ManifestGenerationError(f"missing artifact: {artifact.relative_path}")


def generate(
    *,
    template_path: Path,
    output_path: Path,
    release_version: str,
    title: str,
    subtitle_lines: tuple[str, str, str],
    artifacts: tuple[ManifestArtifact, ...],
    repository_root: Path = REPOSITORY_ROOT,
) -> Path:
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if output_path.exists():
        raise ManifestGenerationError(
            f"refusing to overwrite existing manifest: {output_path}. "
            "A deliberate regeneration must use a distinct output path and compare the "
            "generated bytes with the governed artifact."
        )
    if tmp_path.exists():
        raise ManifestGenerationError(
            f"refusing to overwrite or delete an existing temp file not proven to belong to "
            f"this invocation: {tmp_path}"
        )

    _validate_template(template_path)
    _validate_artifacts(artifacts, release_version=release_version, repository_root=repository_root)

    checksums = {
        artifact.relative_path: hashlib.sha256(
            (repository_root / artifact.relative_path).read_bytes()
        ).hexdigest()
        for artifact in artifacts
    }

    ordered = tuple(sorted(artifacts, key=lambda item: item.relative_path))
    sheet_xml = _build_sheet_xml(title, subtitle_lines, ordered, checksums)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(template_path) as template_zip:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as out_zip:
            for part in TEMPLATE_PASSTHROUGH_PARTS:
                info = zipfile.ZipInfo(part, date_time=FIXED_DATE_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 0
                out_zip.writestr(info, template_zip.read(part))
            sheet_info = zipfile.ZipInfo("xl/worksheets/sheet1.xml", date_time=FIXED_DATE_TIME)
            sheet_info.compress_type = zipfile.ZIP_DEFLATED
            sheet_info.create_system = 0
            out_zip.writestr(sheet_info, sheet_xml)

    try:
        with zipfile.ZipFile(tmp_path) as reloaded:
            if set(reloaded.namelist()) != {*TEMPLATE_PASSTHROUGH_PARTS, "xl/worksheets/sheet1.xml"}:
                raise ManifestGenerationError("generated manifest has unexpected zip parts")
            ElementTree.fromstring(reloaded.read("xl/worksheets/sheet1.xml"))
    except (zipfile.BadZipFile, ElementTree.ParseError) as error:
        tmp_path.unlink(missing_ok=True)
        raise ManifestGenerationError(f"generated manifest failed validation: {error}") from error
    except ManifestGenerationError:
        tmp_path.unlink(missing_ok=True)
        raise

    tmp_path.replace(output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(
        "This tool is invoked as a library (see generate()) by release-specific "
        "scripts, since artifact inventories are release-specific data, not CLI "
        "flags. There is no generic CLI entry point.",
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
