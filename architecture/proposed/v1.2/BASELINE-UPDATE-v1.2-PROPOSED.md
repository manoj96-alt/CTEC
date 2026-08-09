# Architecture Baseline v1.2 — Proposed Amendment Release

Status: DEVELOPMENT / NO / NON-AUTHORITATIVE

This proposed baseline carries only the approved Closure Gate 1A amendment scope. All unchanged Baseline v1.1 authorities remain unchanged and must be included by exact checksum in the final cumulative release manifest.

The proposed baseline adds RFC-014 v1.1, CIM-001 v1.1, CVR-001 v1.0, and the CDD-010 companion clarification; supersedes only ASM-001 v2.2, EOM-001 v1.2, EIC-001 v1.2, GRM-001 v1.2, and DRM-001 v1.2 with their reviewed clarification versions.

It adds two canonical vocabulary values and no canonical structures:

- `SUPPLIER_RISK_CONDITION`
- `HAS_ACTIVE_RISK_CONDITION`

No production code, tests, APIs, persistence, UI, deployment configuration, or capability integration is included. CDD-010 remains implemented exactly as published; the companion clarification authorizes only a future separately governed control-metadata extension.

Publication requires explicit release approval, final cumulative manifest generation, Registry application, consistency/drift/readiness reports, and an atomic commit.
