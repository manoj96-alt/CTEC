# CDD-036 — Governed Human Approval — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION (pending S1 publication)
Authority base: 8fda20f10efc900042f33fc6828c774e99788a13

## 1. Purpose

Enumerates exactly which repository artifacts Gate S v1 implementation (S1) may create or modify
to prove the governed human-approval capability defined by CDD-036 — and nothing more.

## 2. Governing authorities

CDD-036 remains the sole semantic authority for every decision enumerated here. CDD-013 remains
the sole authority for `SecurityAuditService`/`ApiSecurityAuditRepository`, reused unmodified.
CDD-035 and its Artifact Authorization remain FROZEN and untouched — this authorization does not
permit any Gate R file to change.

## 3. Implementation objective

Prove CDD-036's exact tenant-isolated, digest-bound, one-time-consumption, human-approval pipeline
via the smallest file surface consistent with existing repository layering conventions
(domain / persistence model / repository / application service / API), following the exact shape
of Gate M's proposal-governance precedent, without a new dependency-container field, without a
second action type, and without any frontend.

## 4. Exact authorized allowlist

| Path | Operation | Purpose |
|---|---|---|
| `backend/app/domain/gate_s/__init__.py` | CREATE | Package marker for the new Gate S domain package. |
| `backend/app/domain/gate_s/approval.py` | CREATE | `ApprovalStatus` (closed 3-value StrEnum), `GateSApprovalRequest` frozen dataclass with `__post_init__` validation, `compute_action_digest()` (CDD-036 Sec16). |
| `backend/app/infrastructure/persistence/models/gate_s_approval.py` | CREATE | `GateSApprovalRequestORM` (`gate_s_approval_requests`) and `GateSGovernedNoteORM` (`gate_s_governed_notes`), exactly the columns in CDD-036 Sec19. |
| `backend/app/infrastructure/persistence/migrations/versions/0018_gate_s_approval.py` | CREATE | Alembic migration creating exactly the two Sec19 tables; `down_revision = "0017_ontology_change_proposal"`. |
| `backend/app/infrastructure/persistence/gate_s_approval_repository.py` | CREATE | `GateSApprovalRepository` (Protocol or ABC) + implementation: `create()`, `get_for_update(approval_id, tenant_id)` (`SELECT ... FOR UPDATE`), `update_decision()`, `insert_governed_note_and_consume()`. |
| `backend/app/application/gate_s_approval_service.py` | CREATE | `GateSApprovalService`: `request()`, `approve()`, `reject()`, `execute()` — the sole code path constructing `GateSGovernedNoteORM` (CDD-036 Sec21-22). Calls the existing `Container.security_audit`/`SecurityAuditService` for provenance per CDD-036 Sec24, or constructs `ApiSecurityAuditEvent` directly if a field CDD-036 Sec24 requires is not exposed by `SecurityAuditService.record` (mirroring the precedent set in `governed_tool_executor.py`). |
| `backend/app/api/gate_s/__init__.py` | CREATE | Package marker for the new Gate S API package. |
| `backend/app/api/gate_s/dependencies.py` | CREATE | FastAPI dependency wiring, reusing `Container.ontology_sessions` (the existing generic session factory — no `dependency_container.py` change, exactly mirroring `app/api/ontology_modeling/dependencies.py`). |
| `backend/app/api/gate_s/schemas.py` | CREATE | Pydantic request/response models for the five Sec27 endpoints. |
| `backend/app/api/gate_s/router.py` | CREATE | The exact five endpoints in CDD-036 Sec27, mirroring `app/api/ontology_modeling/router.py`'s `_authorize`/`_record_denied` pattern. |
| `backend/app/tests/test_gate_s_approval_service.py` | CREATE | Fake-repository, non-DB tests: request creation, tenant binding, requester identity, authority checks, self-approval, approve/reject transitions, execute-on-pending/rejected denial, successful execute + consumption, digest mismatch, double-consumption, audit content, `note_text` absence from audit. |
| `backend/app/tests/test_gate_s_approval_router.py` | CREATE | HTTP-layer scope/tenant authorization tests, mirroring `test_ontology_modeling_router.py`. |
| `backend/app/tests/test_gate_s_approval_postgres.py` | CREATE | Real-Postgres tests: migration schema correctness, concurrent-decide race, concurrent-execute race. |
| `backend/app/main.py` | MODIFY | Add one import and one `app.include_router(gate_s_router)` line, mirroring the existing `ontology_modeling_router` registration exactly. |
| `keycloak/ctec-realm.json` | MODIFY | Add exactly the two `clientScopes` entries and the two `optionalClientScopes` entries in CDD-036 Sec9. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Add the 13 new/changed paths above to `AUTHORIZED_CHANGED_PATHS`; add one new firewall test proving Gate Q/cognitive-runtime absence and single-write-site bypass-impossibility for `GateSGovernedNoteORM` (CDD-036 Sec22, Sec33). |

```
AUTHORIZED_NEW    = 13
AUTHORIZED_CHANGE = 3
AUTHORIZED_DELETE = 0
TOTAL IMPLEMENTATION SURFACE = 16
```

No seventeenth file is authorized. If implementation discovery determines a further new/modified
file is mechanically necessary, implementation MUST STOP and return to the Product Owner rather
than silently widening this surface.

## 5. Read-only dependencies

Consumed, by call only, entirely unmodified: `app.api.supplier_risk.authentication.TrustedPrincipal`,
`app.api.supplier_risk.audit.SecurityAuditService`, `app.infrastructure.persistence.
api_security_audit_repository.{ApiSecurityAuditEvent, ApiSecurityAuditRepository}`,
`app.api.supplier_risk.dependencies.{container, correlation_id, principal}`,
`app.core.dependency_container.Container` (specifically its existing `ontology_sessions` and
`security_audit` attributes — no new attribute added), `app.domain.shared.exceptions.
ValidationException`.

## 6. Explicitly forbidden files/domains (binding)

NOT authorized under any circumstance:
- `backend/app/application/governed_tool_executor.py`
- `backend/app/tests/test_governed_tool_executor.py`
- `backend/app/application/mcp_client.py`
- `backend/app/application/mcp_connector_catalog.py`
- any file under `backend/app/runtime/`
- any file under `backend/app/integration/adapters/`
- `backend/app/core/dependency_container.py`
- any file under `frontend/`
- any migration other than `0018_gate_s_approval.py`
- any second consequential-action definition
- any agent, planner, or LLM code
- any file governing Simulation, generalized Data Quality, Evidence Fitness, or remediation
- CDD-035, its Artifact Authorization, CDD-013, CDD-028, or any other frozen governance document

## 7. Route/endpoint authorization (binding, exact)

```
POST   /api/v1/governed-approval/requests
GET    /api/v1/governed-approval/requests/{approval_id}
POST   /api/v1/governed-approval/requests/{approval_id}/approve
POST   /api/v1/governed-approval/requests/{approval_id}/reject
POST   /api/v1/governed-approval/requests/{approval_id}/execute
```

No other route. No PUT/PATCH/DELETE. No `list`.

## 8. Persistence / migration / authentication / Keycloak discipline (binding)

Exactly one migration, exactly two new tables (CDD-036 Sec19). Authentication is the existing,
unmodified OIDC/`TrustedPrincipal` mechanism. The sole Keycloak change is exactly the two
`clientScopes`/`optionalClientScopes` additions in Sec4 — no other realm content may change.

## 9. Dependency-container discipline (binding, load-bearing)

`backend/app/core/dependency_container.py` is NOT modified. `backend/app/api/gate_s/dependencies.py`
builds its session and repository/service instances per-request from the existing
`Container.ontology_sessions` sessionmaker, exactly as `app/api/ontology_modeling/dependencies.py`
already does — no new `Container` field is added or read.

## 10. Gate R firewall (binding, restated)

`governed_tool_executor.py` and its test file are not imported, called, referenced, or modified by
any authorized file.

## 11. Gate Q firewall (binding, restated)

`mcp_client.py` and `mcp_connector_catalog.py` are not imported, called, referenced, or modified by
any authorized file.

## 12. Cognitive-runtime firewall (binding, restated)

No file under `backend/app/runtime/` or `backend/app/integration/adapters/` is imported, called,
referenced, or modified by any authorized file.

## 13. Gate V / Gate W firewall (binding, restated)

No agent execution, no LLM invocation, no autonomous decision code, and no frontend file is
authorized, referenced, or implied by this document.

## 14. Single-write-site discipline (binding, load-bearing)

`GateSGovernedNoteORM` may be constructed (via `session.add(...)`) in exactly one location:
`GateSApprovalRepositoryImpl.insert_governed_note_and_consume` in `backend/app/infrastructure/
persistence/gate_s_approval_repository.py`, itself callable only from
`GateSApprovalService.execute()` in `backend/app/application/gate_s_approval_service.py`. No test
fixture, no router, no other service may construct it directly. The architecture test (Sec4's last
row) enforces this via source inspection.

## 15. Test obligations (binding, minimum set)

Per CDD-036 Sec36, distributed across the three new test files exactly as enumerated in this
document's Sec4 table.

## 16. Implementation stop conditions

Implementation MUST STOP and return to the Product Owner if: a seventeenth file becomes
mechanically necessary; `Container.ontology_sessions` is found to be unsuitable for Gate S's
transactional needs; `test_runtime_architecture.py`'s allowlist is found to already differ from
the state assumed here; any forbidden path (Sec6) is found to be mechanically required.

## 17. Acceptance criteria

1. Exact 16-file diff: CREATE=13, MODIFY=3, DELETE=0.
2. All 9 CDD-036 Sec23 diagnostic codes present, no more, no fewer.
3. All CDD-036 Sec36 test obligations pass, distributed per this document's Sec4/Sec15.
4. `test_runtime_architecture.py`'s own existing tests (Gate Q untouched, no seventh
   cognitive-engine stage, exhaustive changed-path allowlist) pass unmodified.
5. Full backend regression suite passes.
6. `docker compose config --quiet` passes.
7. CDD-036, this Artifact Authorization, CDD-035, its Artifact Authorization, CDD-013, and
   CDD-028 remain byte-identical.
8. `keycloak/ctec-realm.json`'s `defaultClientScopes` array remains byte-identical except for
   this diff's own explicit `optionalClientScopes` addition.
9. Exact-head CI passes before merge; post-merge CI passes.

## 18. Implementation PR strategy

One dedicated implementation branch/worktree under `/Users/manojvelayudhannair/Developer/`, from
exact authoritative main (never reusing another gate's worktree). One commit (or the minimum
number of CI-driven fixup commits) containing exactly the 16 authorized files. One PR against
main. No merge within this same phase — a separate exact-head merge authorization (Gate S2)
remains required.

## 19. Merge requirements

Exact-head CI green (backend/frontend/containers); `mergeable = MERGEABLE`; `mergeStateStatus =
CLEAN`; frozen-governance byte-integrity reconfirmed immediately pre-merge.

## 20. Closure criteria

Gate S v1 may be classified RESOLVED/MERGED/VERIFIED/CLOSED only after: the merge commit is
confirmed as new authoritative main via both git and the GitHub API; the post-merge diff from
pre-merge main contains exactly the 16 authorized files; all Sec17 acceptance criteria are
reconfirmed directly from the merge commit's own content.

## 21. Authorization

This Artifact Authorization is approved for publication alongside CDD-036, reached via Gate S0.
Pending Product Owner review before S1 publication.
