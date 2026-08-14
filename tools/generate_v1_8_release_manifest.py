"""Generate architecture/released/v1.8/RELEASE-MANIFEST-v1.8.xlsx.

Increment 3A-0 / RFC-015 tenant-foundation architecture release. This is the
concrete, reviewable artifact inventory for baseline v1.8 -- the release-
specific input to the reusable tools/generate_release_manifest.py generator.
"""

from __future__ import annotations

import sys

from generate_release_manifest import (
    REPOSITORY_ROOT,
    ManifestArtifact,
    ManifestGenerationError,
    generate,
)

RELEASE_VERSION = "v1.8"
APPROVAL_REFERENCE = "Product Owner authorization Increment 3A-0 (RFC-015)"
TEMPLATE = REPOSITORY_ROOT / "architecture/released/v1.7/RELEASE-MANIFEST-v1.7.xlsx"
OUTPUT = REPOSITORY_ROOT / "architecture/released/v1.8/RELEASE-MANIFEST-v1.8.xlsx"

ARTIFACTS = (
    ManifestArtifact(
        relative_path="architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql",
        identifier="ECOM Physical Data Model",
        title="ECOM Physical Data Model",
        version="1.6",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="ECOM Physical Data Model v1.5",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path=(
            "architecture/released/v1.8/"
            "RFC-015_Tenant_Ownership_Physical_Model_Authorization_v1.0_FROZEN.md"
        ),
        identifier="RFC-015",
        title="Tenant Ownership Physical Model Authorization",
        version="1.0",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.8/DEPENDENCY-MATRIX-v1.8.csv",
        identifier="DEPENDENCY-MATRIX",
        title="Architecture Dependency Matrix",
        version="1.8",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="Architecture Dependency Matrix v1.7",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.8/ARCHITECTURE-CONSISTENCY-REPORT-v1.9_FROZEN.md",
        identifier="ACR-001",
        title="Architecture Consistency Report",
        version="1.9",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="ACR-001 v1.8",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.8/README.md",
        identifier="RELEASE-README",
        title="Architecture Release v1.8",
        version="1.8",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="Release README v1.7",
        approval_reference=APPROVAL_REFERENCE,
    ),
)


def main() -> int:
    try:
        output_path = generate(
            template_path=TEMPLATE,
            output_path=OUTPUT,
            release_version=RELEASE_VERSION,
            title="CTEC Architecture Release Manifest v1.8",
            subtitle_lines=(
                "Tenant-foundation architecture release (Increment 3A-0, RFC-015)",
                "Effective 2026-08-14 · Status FROZEN",
                "Checksums cover every released artifact except this manifest.",
            ),
            artifacts=ARTIFACTS,
        )
    except ManifestGenerationError as error:
        print(f"v1.8 manifest generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
