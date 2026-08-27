# CDD-037 — Governed Agent Resolution — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION (pending V1 publication)
Authority base: 58d1da3f506032b56e5c78b6a15a8fe256c9864c

## 1. Purpose

Enumerates exactly which repository artifacts Gate V v1 implementation may create or modify to
prove the governed agent-resolution capability defined by CDD-037 — and nothing more.

## 2. Governing authorities

CDD-037 remains the sole semantic authority for every decision here. CDD-036 remains the sole
authority for `GateSApprovalService`, reused unmodified by call. CDD-013 remains the sole authority
for `SecurityAuditService`/`ApiSecurityAuditRepository`, reused unmodified.

## 3. Implementation objective

Prove CDD-037's exact deterministic-agent, confused-deputy-safe, Gate-S-composing proposal pipeline
via the smallest file surface consistent with Gate S's own proven layering (domain / model /
repository / service / API / tests), including the exact four-file migration-head regression
correction learned from Gate S's own omission — in the original authorization, not a later
remediation.

## 4. Exact authorized allowlist

| Path | Operation | Purpose |
|---|---|---|
| `backend/app/domain/gate_v/__init__.py` | CREATE | Package marker for the new Gate V domain package. |
| `backend/app/domain/gate_v/agent_resolution.py` | CREATE | `AgentResolutionOutcome` (closed 2-value StrEnum), `GateVAgentResolution` frozen dataclass with `__post_init__` validation, the fixed `AGENT_ID` and `PRIORITY_THRESHOLD` constants (CDD-037 Sec7, Sec14). |
| `backend/app/infrastructure/persistence/models/gate_v_agent_resolution.py` | CREATE | `GateVAgentResolutionORM` (`gate_v_agent_resolutions`), exactly the columns in CDD-037 Sec15. |
| `backend/app/infrastructure/persistence/migrations/versions/0019_gate_v_agent_resolution.py` | CREATE | Alembic migration creating exactly the Sec15 table; `down_revision = "0018_gate_s_approval"`. |
| `backend/app/infrastructure/persistence/gate_v_agent_resolution_repository.py` | CREATE | `GateVAgentResolutionRepository` (Protocol) + implementation: `create()`, `get_by_id()`. The sole authorized construction site for `GateVAgentResolutionORM` (CDD-037 Sec24). |
| `backend/app/application/gate_v_agent_service.py` | CREATE | `GateVApplicationService.resolve()`: the deterministic threshold rule (Sec14), calling `GateSApprovalService.request()` by direct in-process call when `PROPOSED`, recording the resolution and one audit event. Defines its own narrow `AuditRepository` Protocol (not imported from Gate S/Gate R, mirroring their own zero-shared-code precedent). |
| `backend/app/api/gate_v/__init__.py` | CREATE | Package marker for the new Gate V API package. |
| `backend/app/api/gate_v/dependencies.py` | CREATE | FastAPI dependency wiring, reusing `Container.ontology_sessions` (no `dependency_container.py` change), mirroring `app/api/gate_s/dependencies.py` exactly. |
| `backend/app/api/gate_v/schemas.py` | CREATE | Pydantic request/response models for the two Sec18 endpoints, with the exact field bounds in CDD-037 Sec19. |
| `backend/app/api/gate_v/router.py` | CREATE | The exact two endpoints in CDD-037 Sec18, mirroring `app/api/gate_s/router.py`'s `_authorize`/`_authorize_any`/`_record_denied` pattern. |
| `backend/app/tests/test_gate_v_agent_service.py` | CREATE | Fake-repository, non-DB tests: threshold PROPOSED/SUPPRESSED, digest/approval linkage via a fake `GateSApprovalService`-shaped double, audit content, `observation_text` absence from audit. |
| `backend/app/tests/test_gate_v_agent_router.py` | CREATE | HTTP-layer scope/tenant authorization tests, mirroring `test_gate_s_approval_router.py`: both-scopes-required, cross-tenant GET denial, GET accessible via either scope. |
| `backend/app/tests/test_gate_v_agent_postgres.py` | CREATE | Real-Postgres tests: migration schema correctness, resolution row durability, real composition with a real `GateSApprovalService.request()` call producing a genuine `gate_s_approval_requests` row. |
| `backend/app/main.py` | MODIFY | Add one import and one `app.include_router(gate_v_router)` line, mirroring the existing `gate_s_router` registration exactly. |
| `keycloak/ctec-realm.json` | MODIFY | Add exactly one `clientScopes` entry and one `optionalClientScopes` entry: `governed-agent:propose`. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Add the 13 new/changed paths above to `AUTHORIZED_CHANGED_PATHS`; add one new firewall test proving Gate Q/R/S file-import absence and single-write-site enforcement for `GateVAgentResolutionORM` (CDD-037 Sec24). |
| `backend/app/tests/test_decision_engine.py` | MODIFY | Update exactly the migration-head literal: `"0018_gate_s_approval"` → `"0019_gate_v_agent_resolution"`. No other change. |
| `backend/app/tests/test_governance_engine.py` | MODIFY | Update exactly the migration-head literal: `"0018_gate_s_approval"` → `"0019_gate_v_agent_resolution"`. No other change. |
| `backend/app/tests/test_knowledge_engine.py` | MODIFY | Update exactly the migration-head literal: `"0018_gate_s_approval"` → `"0019_gate_v_agent_resolution"`. No other change. |
| `backend/app/tests/test_persistence_integration.py` | MODIFY | Update exactly two literals: migration-head `"0018_gate_s_approval"` → `"0019_gate_v_agent_resolution"`; table-count `63` → `64`. No other change. |

```
AUTHORIZED_NEW    = 13
AUTHORIZED_CHANGE = 7
AUTHORIZED_DELETE = 0
TOTAL IMPLEMENTATION SURFACE = 20
```

No 21st path is authorized. If implementation discovery determines a further new/modified file is
mechanically necessary, implementation MUST STOP and return to the Product Owner.

## 5. Read-only dependencies

Consumed, by call only, entirely unmodified: `app.api.supplier_risk.authentication.TrustedPrincipal`,
`app.application.gate_s_approval_service.GateSApprovalService` (specifically `.request()` only — never
`.approve()`/`.reject()`/`.execute()`), `app.infrastructure.persistence.gate_s_approval_repository.
GateSApprovalRepositoryImpl` (constructed once, passed into `GateSApprovalService`, exactly as Gate S's
own dependency wiring does), `app.infrastructure.persistence.api_security_audit_repository.
{ApiSecurityAuditEvent, ApiSecurityAuditRepository}`, `app.api.supplier_risk.dependencies.{container,
correlation_id, principal}`, `app.core.dependency_container.Container` (existing `ontology_sessions`
and `security_audit` attributes only).

## 6. Explicitly forbidden files/domains (binding)

NOT authorized under any circumstance:
- `backend/app/application/gate_s_approval_service.py` (consumed by call only, never modified)
- `backend/app/infrastructure/persistence/gate_s_approval_repository.py`
- `backend/app/domain/gate_s/**`, `backend/app/api/gate_s/**`
- `backend/app/application/governed_tool_executor.py`
- `backend/app/application/mcp_client.py`
- `backend/app/application/mcp_connector_catalog.py`
- any file under `backend/app/runtime/`
- any file under `backend/app/integration/adapters/`
- `backend/app/core/dependency_container.py`
- any file under `frontend/`
- any migration other than `0019_gate_v_agent_resolution.py`
- any second agent identity or second consequential-action definition
- any agent, planner, or LLM code beyond the deterministic threshold rule in Sec14
- any file governing Simulation, generalized Data Quality, Evidence Fitness, or remediation
- CDD-030, CDD-031, CDD-035, CDD-036, any of CDD-036's companion authorizations, or any other frozen
  governance document

## 7. Route/endpoint authorization (binding, exact)

```
POST /api/v1/governed-agent/resolutions
GET  /api/v1/governed-agent/resolutions/{resolution_id}
```

No other route. No PUT/PATCH/DELETE. No `list`. No execute endpoint.

## 8. Persistence / migration / authentication / Keycloak discipline (binding)

Exactly one migration, exactly one new table (CDD-037 Sec15). Authentication is the existing,
unmodified OIDC/`TrustedPrincipal` mechanism. The sole Keycloak change is exactly the one
`clientScopes`/`optionalClientScopes` addition — no other realm content may change.

## 9. Dependency-container discipline (binding, load-bearing)

`backend/app/core/dependency_container.py` is NOT modified. `backend/app/api/gate_v/dependencies.py`
builds its session/repository/service instances per-request from the existing `Container.
ontology_sessions` sessionmaker, exactly as `app/api/gate_s/dependencies.py` already does.

## 10. Gate S composition discipline (binding, load-bearing)

`GateVApplicationService.resolve()` constructs and calls `GateSApprovalService.request(principal=...,
note_text=...)` directly — the exact same construction pattern used to wire `GateSApprovalService` in
`app/api/gate_s/dependencies.py`. No Gate S file is imported for modification; only its public
`request()` method is called.

## 11. Gate Q firewall (binding, restated)

`mcp_client.py`/`mcp_connector_catalog.py` not imported, called, or modified by any authorized file.

## 12. Gate R firewall (binding, restated)

`governed_tool_executor.py`/`GOVERNED_TOOL_REGISTRY` not imported, called, or modified by any
authorized file.

## 13. Cognitive-runtime firewall (binding, restated)

No file under `backend/app/runtime/` or `backend/app/integration/adapters/` is imported, called,
referenced, or modified by any authorized file.

## 14. Gate T / Gate W / DQ / frontend firewall (binding, restated)

No Gate T file consumed or modified. No production API-management framework. No DQ scoring/rules/
dashboard. No frontend file authorized, referenced, or implied.

## 15. Single-write-site discipline (binding, load-bearing)

`GateVAgentResolutionORM` may be constructed in exactly one location: the repository implementation in
`backend/app/infrastructure/persistence/gate_v_agent_resolution_repository.py`. No test fixture, no
router, no other service may construct it directly. The architecture test enforces this via source
inspection.

## 16. Migration-regression discipline (binding, load-bearing — the exact Gate S lesson)

The four MODIFY rows in Sec4 targeting `test_decision_engine.py`/`test_governance_engine.py`/
`test_knowledge_engine.py`/`test_persistence_integration.py` authorize **exactly** the literal
corrections named — the migration-head string in all four, plus the table-count integer in the last —
and nothing else. No test weakening, deletion, skip, xfail, refactor, or generalized migration-agnostic
mechanism is authorized in any of these four files.

## 17. Test obligations (binding, minimum set)

Per CDD-037 Sec34, distributed across the three new test files exactly as enumerated in Sec4.

## 18. Implementation stop conditions

Implementation MUST STOP and return to the Product Owner if: a 21st file becomes mechanically
necessary; `Container.ontology_sessions` is found unsuitable; `test_runtime_architecture.py`'s
allowlist differs from the state assumed here; any forbidden path (Sec6) is found mechanically
required; a fifth migration-regression file is discovered beyond the four named in Sec4.

## 19. Acceptance criteria

1. Exact 20-file diff: CREATE=13, MODIFY=7, DELETE=0.
2. All 4 CDD-037 Sec23 diagnostic codes present, no more, no fewer.
3. All CDD-037 Sec34 test obligations pass, distributed per Sec4/Sec17.
4. `test_runtime_architecture.py`'s own existing tests (Gate Q/R/S untouched, no seventh
   cognitive-engine stage, exhaustive changed-path allowlist) pass unmodified.
5. The four migration-regression tests pass with the corrected literal values.
6. Full backend regression suite passes with zero unexplained failures.
7. `docker compose config --quiet` passes.
8. CDD-037, this Artifact Authorization, CDD-036 and all its companions, CDD-030, CDD-013 remain
   byte-identical.
9. `keycloak/ctec-realm.json`'s `defaultClientScopes` array remains byte-identical except for this
   diff's own explicit `optionalClientScopes` addition.
10. Exact-head CI passes before merge; post-merge CI passes.

## 20. Implementation PR strategy

One dedicated implementation branch/worktree under `/Users/manojvelayudhannair/Developer/`, from exact
authoritative main. One commit (or the minimum CI-driven fixup commits) containing exactly the 20
authorized files. One PR against main. No merge within this same phase.

## 21. Merge requirements

Exact-head CI green; `mergeable = MERGEABLE`; `mergeStateStatus = CLEAN`; frozen-governance
byte-integrity reconfirmed immediately pre-merge.

## 22. Closure criteria

Gate V v1 may be classified RESOLVED/MERGED/VERIFIED/CLOSED only after: the merge commit is confirmed
as new authoritative main via both git and the GitHub API; the post-merge diff from pre-merge main
contains exactly the 20 authorized files; all Sec19 acceptance criteria are reconfirmed directly from
the merge commit's own content.

## 23. Authorization

This Artifact Authorization is approved for publication alongside CDD-037, reached via Gate V0. Pending
Product Owner review before V1 publication.
