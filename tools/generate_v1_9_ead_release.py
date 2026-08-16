"""Generate EAD-001-v1.7.json for Gate D1 / RFC-016: appends one new
`tenant_id` attribute row for the already-present `Institutional Relationship`
entity, so tools/build_persistence_traceability.py has an EAD trace for the
tenant_id column added to institutional_relationships by
tools/generate_v1_9_physical_model_release.py.

Thin release-specific wrapper around the reusable
tools/generate_ead_release.generate() -- no new I/O-contract logic here; see
that module's docstring for the temp-file/overwrite-guard/validation contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

from generate_ead_release import REPOSITORY_ROOT, EadGenerationError, generate

DEFAULT_SOURCE = REPOSITORY_ROOT / "docs/persistence/traceability/EAD-001-v1.6.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "docs/persistence/traceability/EAD-001-v1.7.json"
EXPECTED_SOURCE_ROWS = 365
NEW_ATTRIBUTE_ROWS = (("Institutional Relationship", "Operational"),)
CONSTITUTIONAL_MEANING = (
    "Gate D1 / RFC-016: opaque tenant ownership identifier sourced from the "
    "trusted authority boundary, establishing customer-boundary isolation for "
    "this instance-data table"
)


def main() -> int:
    try:
        output_path = generate(
            DEFAULT_SOURCE,
            DEFAULT_OUTPUT,
            expected_source_rows=EXPECTED_SOURCE_ROWS,
            new_attribute_rows=NEW_ATTRIBUTE_ROWS,
            constitutional_meaning=CONSTITUTIONAL_MEANING,
        )
    except EadGenerationError as error:
        print(f"v1.7 EAD release generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(REPOSITORY_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
