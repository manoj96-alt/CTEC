"""Generate architecture/released/v1.9/RELEASE-MANIFEST-v1.9.xlsx.

Gate D1 / RFC-016 architecture release. This is the concrete, reviewable
artifact inventory for baseline v1.9 -- the release-specific input to the
reusable tools/generate_release_manifest.py generator.
"""

from __future__ import annotations

import sys

from generate_release_manifest import (
    REPOSITORY_ROOT,
    ManifestArtifact,
    ManifestGenerationError,
    generate,
)

RELEASE_VERSION = "v1.9"
APPROVAL_REFERENCE = "Product Owner authorization Gate D0/D1 (RFC-016)"
TEMPLATE = REPOSITORY_ROOT / "architecture/released/v1.8/RELEASE-MANIFEST-v1.8.xlsx"
OUTPUT = REPOSITORY_ROOT / "architecture/released/v1.9/RELEASE-MANIFEST-v1.9.xlsx"

ARTIFACTS = (
    ManifestArtifact(
        relative_path="architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql",
        identifier="ECOM Physical Data Model",
        title="ECOM Physical Data Model",
        version="1.7",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="ECOM Physical Data Model v1.6",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path=(
            "architecture/released/v1.9/"
            "RFC-016_Institutional_Relationship_Canonical_Authorization_and_Tenant_Ownership_v1.0_FROZEN.md"
        ),
        identifier="RFC-016",
        title="Institutional Relationship Canonical Authorization and Tenant Ownership",
        version="1.0",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path=(
            "architecture/released/v1.9/"
            "PAD-001-Product-Internal-Deterministic-Capability-Boundary-Clarification-v1.0_FROZEN.md"
        ),
        identifier="PAD-001 Product-Internal Deterministic Capability Boundary Clarification",
        title="Product-Internal Deterministic Capability Boundary Clarification",
        version="1.0",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.9/DEPENDENCY-MATRIX-v1.9.csv",
        identifier="DEPENDENCY-MATRIX",
        title="Architecture Dependency Matrix",
        version="1.9",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="Architecture Dependency Matrix v1.8",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.9/ARCHITECTURE-CONSISTENCY-REPORT-v1.10_FROZEN.md",
        identifier="ACR-001",
        title="Architecture Consistency Report",
        version="1.10",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="ACR-001 v1.9",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.9/README.md",
        identifier="RELEASE-README",
        title="Architecture Release v1.9",
        version="1.9",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="Release README v1.8",
        approval_reference=APPROVAL_REFERENCE,
    ),
)


def main() -> int:
    try:
        output_path = generate(
            template_path=TEMPLATE,
            output_path=OUTPUT,
            release_version=RELEASE_VERSION,
            title="CTEC Architecture Release Manifest v1.9",
            subtitle_lines=(
                "Gate D1 architecture release (RFC-016 / PAD-001 Clarification)",
                "Effective 2026-08-16 · Status FROZEN",
                "Checksums cover every released artifact except this manifest.",
            ),
            artifacts=ARTIFACTS,
        )
    except ManifestGenerationError as error:
        print(f"v1.9 manifest generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
