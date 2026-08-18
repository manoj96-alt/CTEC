"""Generate architecture/released/v1.11/RELEASE-MANIFEST-v1.11.xlsx.

Gate F / RFC-017 / PAD-003 architecture release. This is the concrete,
reviewable artifact inventory for baseline v1.11 -- the release-specific
input to the reusable tools/generate_release_manifest.py generator.
"""

from __future__ import annotations

import sys

from generate_release_manifest import (
    REPOSITORY_ROOT,
    ManifestArtifact,
    ManifestGenerationError,
    generate,
)

RELEASE_VERSION = "v1.11"
APPROVAL_REFERENCE = "Product Owner authorization Gate F (RFC-017 / PAD-003 / CDD-015)"
TEMPLATE = REPOSITORY_ROOT / "architecture/released/v1.10/RELEASE-MANIFEST-v1.10.xlsx"
OUTPUT = REPOSITORY_ROOT / "architecture/released/v1.11/RELEASE-MANIFEST-v1.11.xlsx"

ARTIFACTS = (
    ManifestArtifact(
        relative_path=(
            "architecture/released/v1.11/"
            "RFC-017-Gate-F-Supply-Chain-Semantic-Vocabulary-Authorization_v1.0_FROZEN.md"
        ),
        identifier="RFC-017",
        title="Gate F Supply Chain Semantic Vocabulary Authorization",
        version="1.0",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path=(
            "architecture/released/v1.11/"
            "PAD-003-Gate-F-Impact-Mitigation-Access-Boundary_v1.0_FROZEN.md"
        ),
        identifier="Gate F Impact and Mitigation Access Boundary (PAD-003)",
        title="Gate F Impact and Mitigation Access Boundary",
        version="1.0",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.11/DEPENDENCY-MATRIX-v1.11.csv",
        identifier="DEPENDENCY-MATRIX",
        title="Architecture Dependency Matrix",
        version="1.11",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="Architecture Dependency Matrix v1.10",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.11/ARCHITECTURE-CONSISTENCY-REPORT-v1.12_FROZEN.md",
        identifier="ACR-001",
        title="Architecture Consistency Report",
        version="1.12",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="ACR-001 v1.11",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.11/README.md",
        identifier="RELEASE-README",
        title="Architecture Release v1.11",
        version="1.11",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="Release README v1.10",
        approval_reference=APPROVAL_REFERENCE,
    ),
)


def main() -> int:
    try:
        output_path = generate(
            template_path=TEMPLATE,
            output_path=OUTPUT,
            release_version=RELEASE_VERSION,
            title="CTEC Architecture Release Manifest v1.11",
            subtitle_lines=(
                "Gate F architecture release (RFC-017 / PAD-003 / CDD-015)",
                "Effective 2026-08-18 · Status FROZEN",
                "Checksums cover every released artifact except this manifest.",
            ),
            artifacts=ARTIFACTS,
        )
    except ManifestGenerationError as error:
        print(f"v1.11 manifest generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
