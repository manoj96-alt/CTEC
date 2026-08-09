# CDD-013 — API Contract Clarification Allowlist

Version: 1.0
Status: AUTHORIZED
Authority base: `9d2ab3042f22e69b9d41d01fd0905cbb7cd73ec7`

Only these governance paths may be created or modified for the bounded clarification release:

- `architecture/INDEX.md`
- `architecture/released/v1.6/**`
- `scripts/verify_architecture_release.py` — baseline-list and current dependency-matrix pointer only.
- `docs/cdd/CDD-013-API-CONTRACT-CLARIFICATION-ALLOWLIST.md`
- `docs/cdd/CDD-013-Business-Facing-API-Contract-Clarification-and-Remediation-Report.md`
- `docs/cdd/CDD-013-API-CONTRACT-IMPLEMENTATION-ALLOWLIST.md`
- `docs/cdd/BSP-001-BROWSER-SECURITY-GOVERNANCE-ALLOWLIST.md`
- `docs/cdd/CDD-014-FRONTEND-IMPLEMENTATION-ALLOWLIST.md`
- the fourteen existing `docs/cdd/CDD-014-*.md` preimplementation artifacts, reference updates only.

No production, test, persistence, migration, dependency, UI, or deployment path is authorized by
this allowlist. All unlisted paths are READ-ONLY.
