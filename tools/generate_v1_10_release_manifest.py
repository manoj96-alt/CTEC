"""Generate architecture/released/v1.10/RELEASE-MANIFEST-v1.10.xlsx.

Gate E / PAD-002 architecture release. This is the concrete, reviewable
artifact inventory for baseline v1.10 -- the release-specific input to the
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

RELEASE_VERSION = "v1.10"
APPROVAL_REFERENCE = "Product Owner authorization Gate E (PAD-002)"
TEMPLATE = REPOSITORY_ROOT / "architecture/released/v1.9/RELEASE-MANIFEST-v1.9.xlsx"
OUTPUT = REPOSITORY_ROOT / "architecture/released/v1.10/RELEASE-MANIFEST-v1.10.xlsx"

ARTIFACTS = (
    ManifestArtifact(
        relative_path=(
            "architecture/released/v1.10/"
            "PAD-002-Local-Development-Identity-Provider-and-Demo-Persona-Authorization-Boundary_v1.0_FROZEN.md"
        ),
        identifier="Local Development Identity Provider and Demo Persona Authorization Boundary (PAD-002)",
        title="Local Development Identity Provider and Demo Persona Authorization Boundary",
        version="1.0",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.10/DEPENDENCY-MATRIX-v1.10.csv",
        identifier="DEPENDENCY-MATRIX",
        title="Architecture Dependency Matrix",
        version="1.10",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="Architecture Dependency Matrix v1.9",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.10/ARCHITECTURE-CONSISTENCY-REPORT-v1.11_FROZEN.md",
        identifier="ACR-001",
        title="Architecture Consistency Report",
        version="1.11",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="ACR-001 v1.10",
        approval_reference=APPROVAL_REFERENCE,
    ),
    ManifestArtifact(
        relative_path="architecture/released/v1.10/README.md",
        identifier="RELEASE-README",
        title="Architecture Release v1.10",
        version="1.10",
        status="Frozen",
        current="YES",
        authority="AUTHORITATIVE",
        superseded_document="Release README v1.9",
        approval_reference=APPROVAL_REFERENCE,
    ),
)


def main() -> int:
    try:
        output_path = generate(
            template_path=TEMPLATE,
            output_path=OUTPUT,
            release_version=RELEASE_VERSION,
            title="CTEC Architecture Release Manifest v1.10",
            subtitle_lines=(
                "Gate E architecture release (PAD-002)",
                "Effective 2026-08-16 · Status FROZEN",
                "Checksums cover every released artifact except this manifest.",
            ),
            artifacts=ARTIFACTS,
        )
    except ManifestGenerationError as error:
        print(f"v1.10 manifest generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
