# CDD-035 — Governed Tool Execution — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION (pending R3 publication)
Authority base: 606bc8545d8b7d2d051bb22d76e0f2390d574b53

## 1. Purpose

Enumerates exactly which repository artifacts Gate R v1 implementation (R4) may create or modify to
prove the governed tool-execution boundary defined by CDD-035 -- and nothing more. This document alone
does not authorize implementation; a separate, subsequent Product Owner implementation authorization
remains required.

## 2. Governing authorities

CDD-035 (this document's parent) remains the sole semantic authority for every architectural decision
enumerated here. CDD-013 remains the sole authority for `SecurityAuditService`/`ApiSecurityAuditRepository`
semantics, reused unmodified. CDD-030, CDD-010, and CDD-012 remain FROZEN and untouched -- this
authorization does not permit any file governed by them to change.

## 3. Implementation objective

Prove CDD-035's exact governed pipeline (tool resolution -> authorization -> eligibility -> input
validation -> execution-identity generation -> controlled invocation -> result normalization -> durable
provenance) for exactly one deterministic, local, read-only tool, via the smallest possible file surface,
without creating a domain package, an API surface, or any adapter/plugin abstraction.

## 4. Authorized implementation slices (binding)

Exactly one new application-layer module containing the tool registration, input/output contracts, the
deterministic tool implementation, the result/status types, and the `GovernedToolExecutor` pipeline
itself -- deliberately not split across a separate `domain/` package, since the capability is small enough
that doing so would violate the "prefer fewer files" discipline without any architectural benefit. Exactly
one new test file. Two narrow, additive modifications to existing, already-authorized-for-change files
(the Keycloak realm and the runtime-architecture allowlist).

## 5. Exact authorized allowlist

| Path | Operation | Purpose | Prohibited changes |
|---|---|---|---|
| `backend/app/application/governed_tool_executor.py` | CREATE | Tool registration tuple, input/output dataclasses, `GovernedToolExecutionStatus` enum, `GovernedToolExecutionResult` dataclass, the `gate-r-text-digest` tool function, and the `GovernedToolExecutor` class implementing CDD-035 Sec5's exact pipeline. | No import of `mcp_client`, `mcp_connector_catalog`, any `backend/app/runtime/*`, or any `backend/app/integration/adapters/*` module. No second tool. No API/router/schema code. No new persistence model. |
| `backend/app/tests/test_governed_tool_executor.py` | CREATE | Tests per CDD-035 Sec40. | No modification of any other test file. No weakened or skipped assertion. |
| `keycloak/ctec-realm.json` | MODIFY | Add exactly the one `clientScopes` block and `optionalClientScopes` entry in CDD-035 Sec12. | No modification to `defaultClientScopes`. No modification to any other existing scope, client, user, role, or group. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Add exactly the two new paths above (`governed_tool_executor.py`, `test_governed_tool_executor.py`) to the existing `AUTHORIZED_CHANGED_PATHS` set. | No modification to any other entry in the set. No modification to any other test in the file. |

```
AUTHORIZED_NEW    = 2
AUTHORIZED_CHANGE = 2
AUTHORIZED_DELETE = 0
TOTAL IMPLEMENTATION SURFACE = 4
```

No sixth file is authorized. If implementation discovery determines a fifth new/modified file is
mechanically required, implementation MUST STOP and return to the Product Owner rather than silently
widening this surface.

## 6. Read-only dependencies

The following existing files are consumed, by call only, entirely unmodified: `app.api.supplier_risk.
authentication.TrustedPrincipal`, `app.api.supplier_risk.audit.SecurityAuditService`, `app.infrastructure.
persistence.api_security_audit_repository.{ApiSecurityAuditEvent, ApiSecurityAuditRepository}`, and
`app.core.dependency_container.Container` (for accessing the existing `security_audit` service, mirroring
every other application-layer/router's own dependency-access pattern).

## 7. Explicitly forbidden files/domains (binding)

NOT authorized under any circumstance:
- `backend/app/application/mcp_client.py`
- `backend/app/application/mcp_connector_catalog.py`
- any file under `backend/app/runtime/`
- any file under `backend/app/integration/adapters/`
- any file under `backend/app/api/`
- any file under `frontend/`
- any file under `migrations/` or `alembic/`
- any new persistence ORM model or repository
- any new execution/audit table
- any OpenAI, Azure OpenAI, or Anthropic SDK/config file
- any production MCP server integration
- any agent, planner, or LLM code
- any human-approval code
- any dynamic plugin-registration mechanism
- any file governing Simulation, generalized Data Quality, Evidence Fitness, or remediation
- CDD-030, its Artifact Authorization, CDD-010, CDD-012, or any other frozen governance document

## 8. Route/endpoint authorization (binding)

None. Gate R v1 has no API of any kind (CDD-035 Sec33).

## 9. Consumed-API/collaborator authorization (binding)

None external. Gate R v1 has no outbound dependency on any other Gate's API, service, or capability
beyond the read-only dependencies in Sec6.

## 10. Backend/API expansion discipline (binding)

No `backend/app/main.py` change of any kind -- there is no router to register.

## 11. Persistence / migration / authentication / Keycloak discipline (binding)

No migration. No new ORM model. Authentication is the existing, unmodified OIDC/`TrustedPrincipal`
mechanism. The sole Keycloak change is exactly the one `clientScopes`/`optionalClientScopes` addition in
Sec5 -- no other realm content may change.

## 12. Eligibility/status closure boundary (binding)

The `GovernedToolExecutionStatus` enum implemented in `governed_tool_executor.py` must contain exactly the
six values frozen in CDD-035 Sec20 -- no additional value, no removed value.

## 13. Audit-field boundary (binding)

The `SecurityAuditService.record(...)` call site(s) in `governed_tool_executor.py` must use exactly the
field mapping frozen in CDD-035 Sec22 -- no additional field, no substituted field, no raw payload
argument.

## 14. Gate Q firewall (binding, restated)

`mcp_client.py` and `mcp_connector_catalog.py` are not imported, called, referenced, or modified by any
authorized file.

## 15. Cognitive-runtime firewall (binding, restated)

No file under `backend/app/runtime/` or `backend/app/integration/adapters/` is imported, called,
referenced, or modified by any authorized file.

## 16. Gate S / Gate V / MCP / generalized-DQ firewall (binding, restated)

No approval workflow, no durable human-approval state, no agent execution, no LLM invocation, no MCP
invocation of any kind, and no generalized Data Quality component, route, or persisted record is
authorized, referenced, or implied by this document.

## 17. Test obligations (binding, minimum set)

`test_governed_tool_executor.py` must prove, at minimum: (A) successful execution with a valid principal
and valid input returns `EXECUTED` with the exact output contract; (B) missing `tool-execution:execute`
returns `AUTHORIZATION_SCOPE_REQUIRED` with zero tool invocations; (C) an unknown `tool_id` returns
`UNKNOWN_TOOL` with zero tool invocations; (D) empty text and text exceeding 1024 characters both return
`INVALID_INPUT` with zero tool invocations; (E) exactly one audit-service call occurs per executor call,
for every one of the above paths, asserted via a test double/spy; (F) the audit call's arguments never
contain the raw `text` or raw `digest_hex` value; (G) `tenant_id`/`principal_reference` passed to the
audit call originate only from the test's constructed `TrustedPrincipal`; (H) two calls with identical
input produce identical `digest_hex` output (determinism); (I) `execution_id` is `None` for each of the
four denial paths and a real UUID for the success path.

## 18. Implementation stop conditions

Implementation MUST STOP and return to the Product Owner if: a fifth file becomes mechanically necessary;
`test_runtime_architecture.py`'s allowlist is found to already differ from the state assumed by this
document at implementation time; the existing `SecurityAuditService.record(...)` signature has changed
since this document's freeze; or any forbidden path (Sec7) is found to be mechanically required.

## 19. Acceptance criteria

1. Exact 4-file diff: CREATE=2, MODIFY=2, DELETE=0.
2. All 6 status values present, no more, no fewer.
3. All 9 test obligations (Sec17) pass.
4. `test_runtime_architecture.py`'s own existing tests (Gate Q untouched, no seventh cognitive-engine
   stage, exhaustive changed-path allowlist) pass unmodified.
5. Full backend regression suite passes.
6. `docker compose config --quiet` passes.
7. `scripts/verify_architecture_release.py` passes.
8. CDD-035, this Artifact Authorization, CDD-030, CDD-013, CDD-010, and CDD-012 remain byte-identical.
9. `keycloak/ctec-realm.json`'s `defaultClientScopes` array remains byte-identical (unchanged membership
   and order) except for the diff's own explicit `optionalClientScopes` addition.
10. Exact-head CI passes before merge; post-merge CI passes.

## 20. Implementation PR strategy

One dedicated implementation branch/worktree from exact authoritative main (never reusing another gate's
worktree). One commit containing exactly the 4 authorized files. One PR against main. No merge within the
same phase as implementation -- a separate exact-head merge authorization remains required (Gate R5).

## 21. Merge requirements

Exact-head CI green (backend/frontend/containers); `mergeable = MERGEABLE`; `mergeStateStatus = CLEAN`;
frozen-governance byte-integrity reconfirmed immediately pre-merge.

## 22. Closure criteria

Gate R v1 may be classified RESOLVED/MERGED/VERIFIED/CLOSED only after: the merge commit is confirmed as
new authoritative main via both git and the GitHub API; the post-merge diff from pre-merge main contains
exactly the 4 authorized files; all Sec19 acceptance criteria are reconfirmed directly from the merge
commit's own content (not the pre-merge working tree).

## 23. Authorization

This Artifact Authorization is approved for publication alongside CDD-035, reached via Gate R0 (discovery)
-> R1 (architecture decision) -> this R2 drafting turn. Pending Product Owner review before R3 publication.
