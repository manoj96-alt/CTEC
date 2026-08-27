# CDD-038 — Governed API Version Declaration — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION (pending W1 publication)
Authority base: cd95f2500abd9bbb2c51b52a33d0a8747730b09c

## 1. Purpose

Enumerates exactly which repository artifacts Gate W v1 implementation may create or modify to
prove the governed API-version-declaration capability defined by CDD-038 — and nothing more.

## 2. Governing authorities

CDD-038 remains the sole semantic authority for every decision here.

## 3. Implementation objective

Prove CDD-038's single read-only endpoint and its route/registry-consistency invariant via the
smallest file surface consistent with the existing `app.api.config`/`app.api.version` precedent —
no domain package, no application service, no persistence, no Keycloak change, no dependency
container change.

## 4. Exact authorized allowlist

| Path | Operation | Purpose |
|---|---|---|
| `backend/app/api/api_versions/router.py` | CREATE | `ApiVersionState` (CDD-038 Sec9), `SupportedApiVersion`, the fixed `SUPPORTED_API_VERSIONS` constant, and the single `GET /versions` route (registered under `/api` via `main.py`), mirroring `app/api/config/router.py`'s exact single-file, no-`__init__.py`, no-authentication convention. |
| `backend/app/tests/test_api_versions.py` | CREATE | Endpoint response/status test; unauthenticated-reachability test; the CDD-038 Sec17 route/registry-consistency invariant test, introspecting the real `create_app()` route table. |
| `backend/app/main.py` | MODIFY | Add one import and one `app.include_router(api_versions_router, prefix=API_PREFIX)` line, mirroring the existing `config_router`/`version_router` registration exactly. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Add the 2 new paths above to `AUTHORIZED_CHANGED_PATHS`. No new firewall/single-write-site test is authorized or required (CDD-038 Sec27: no ORM, no predecessor coupling exists to firewall). |

```
AUTHORIZED_NEW    = 2
AUTHORIZED_CHANGE = 2
AUTHORIZED_DELETE = 0
TOTAL IMPLEMENTATION SURFACE = 4
```

No 5th path is authorized. If implementation discovery determines a further new/modified file is
mechanically necessary, implementation MUST STOP and return to the Product Owner.

## 5. Read-only dependencies

None. The router reads only its own local `SUPPORTED_API_VERSIONS` constant and, in tests, the
real `create_app()` route table (read-only introspection).

## 6. Explicitly forbidden files/domains (binding)

NOT authorized under any circumstance:
- any file under `backend/app/domain/gate_q`, `gate_r`, `gate_s`, `gate_v` or their API/application/
  persistence counterparts
- `backend/app/application/mcp_client.py`, `mcp_connector_catalog.py`, `governed_tool_executor.py`
- `backend/app/application/gate_s_approval_service.py`,
  `backend/app/application/gate_v_agent_service.py`, and their repositories
- any file under `backend/app/runtime/` or `backend/app/integration/adapters/`
- `backend/app/core/dependency_container.py`
- `keycloak/ctec-realm.json`
- any migration file of any kind
- any file under `frontend/`
- any file governing DQ, Simulation, Evidence Fitness, or remediation
- CDD-030, CDD-031, CDD-035, CDD-036, CDD-037, CDD-038, this Artifact Authorization, any of their
  companion authorizations, or any other frozen governance document
- `architecture/INDEX.md`

## 7. Route/endpoint authorization (binding, exact)

```
GET /api/versions
```

No other route. No PUT/POST/PATCH/DELETE. No per-version detail route.

## 8. Persistence / migration / Keycloak discipline (binding)

No migration. No new table. No Keycloak change. No new scope.

## 9. Dependency-container discipline (binding)

`backend/app/core/dependency_container.py` is NOT modified. The router requires no injected
dependency.

## 10. Gate Q/R/S/T/V firewall (binding, restated)

No file under any predecessor gate's domain/application/API/persistence path is imported, called,
referenced, or modified by any authorized file.

## 11. Route/registry consistency test discipline (binding, load-bearing)

The Sec4 test file's consistency invariant must introspect the real `create_app()` route table
(not a hardcoded list of expected paths) so that any future route addition is automatically
checked against the registry without requiring this test's own logic to change.

## 12. Test obligations (binding, minimum set)

Per CDD-038 Sec26, contained entirely within `test_api_versions.py`.

## 13. Implementation stop conditions

Implementation MUST STOP and return to the Product Owner if: a 5th file becomes mechanically
necessary; `app.api.config`/`app.api.version`'s no-dependency pattern is found unsuitable; any
forbidden path (Sec6) is found mechanically required; any authentication/scope requirement is
found necessary for this endpoint.

## 14. Acceptance criteria

1. Exact 4-file diff: CREATE=2, MODIFY=2, DELETE=0.
2. `GET /api/versions` returns exactly `{"versions": [{"version": "v1", "state": "SUPPORTED"}]}`
   with status 200, unauthenticated.
3. The route/registry-consistency invariant passes.
4. `test_runtime_architecture.py`'s own existing tests pass unmodified.
5. Full backend regression suite passes.
6. `docker compose config --quiet` passes.
7. CDD-038, this Artifact Authorization, and every other tracked frozen governance document remain
   byte-identical.
8. `keycloak/ctec-realm.json` remains byte-identical (no change authorized).
9. Exact-head CI passes before merge; post-merge CI passes.

## 15. Implementation PR strategy

One dedicated implementation branch/worktree under `/Users/manojvelayudhannair/Developer/`, from
exact authoritative main. One commit containing exactly the 4 authorized files. One PR against
main. No merge within this same phase.

## 16. Merge requirements

Exact-head CI green; `mergeable = MERGEABLE`; `mergeStateStatus = CLEAN`; frozen-governance
byte-integrity reconfirmed immediately pre-merge.

## 17. Closure criteria

Gate W v1 may be classified RESOLVED/MERGED/VERIFIED/CLOSED only after: the merge commit is
confirmed as new authoritative main via both git and the GitHub API; the post-merge diff from
pre-merge main contains exactly the 4 authorized files; all Sec14 acceptance criteria are
reconfirmed directly from the merge commit's own content.

## 18. Authorization

This Artifact Authorization is approved for publication alongside CDD-038, reached via Gate W0.
Pending Product Owner review before W1 publication.
