# CDD-034 — Artifact Authorization: Azure Entra Scope-Length R1-G-R1 Amendment

**Status:** FROZEN
**Amends (additively, does not edit):** `CDD-034-Artifact-Authorization-Azure-Entra-Scope-Length-R1-Correction.md` (SHA-256 `10fe34455623806da8c8c97831ce1c681ce1b2470e0cc6060d218a505741e598`, unchanged, preserved byte-identical)
**Originating phase:** AZURE-DEV-EXTERNAL-ID-SCOPE-R1-G-R1
**Trigger:** AZURE-DEV-EXTERNAL-ID-SCOPE-R1-VM adversarially discovered three closure defects in the original R1 correction's frozen verification contract (§18) — two clauses that cannot be literally satisfied, and one CI-required formatting check the implementation candidate fails. This document corrects the *contract*, not the *decision*. The functional scope migration (`information-element-evidence-fitness:read` → `evidence-fitness:read`) is unchanged and not reopened.

---

## 0. Independent reproduction of the three VM findings (this phase's own verification, before writing any rule)

**§18.1 (OLD-literal inventory) — reproduced.** Repository-wide search of the R1-I candidate (`6846150c643eae9dfb74afcbdc2ad3850e4656cb`) for `information-element-evidence-fitness:read` returns exactly 7 locations: the 5 §16-listed historical CDD artifacts (compliant), `backend/app/tests/test_information_element_evidence_fitness_router.py`'s `_RETIRED_SCOPE` constant (a live, non-historical file), and the original R1 correction governance document itself (not one of its own §16-listed five). Confirmed zero occurrences anywhere in production authorization code, Keycloak granting configuration, frontend product source, or Azure runtime configuration.

**§18.11 (empirical OLD-only session) — reproduced impossible.** A live request to the running Keycloak instance for `scope=openid profile information-element-evidence-fitness:read` returns an immediate `302` with `error=invalid_scope&error_description=Invalid+scopes...` — Keycloak refuses to issue any token for this request at all. Separately, a manually constructed `TrustedPrincipal(scopes=("information-element-evidence-fitness:read",))` posted against the real router via `TestClient` returns `403 AUTHORIZATION_SCOPE_REQUIRED` with zero downstream service calls. Both reproduced independently; they are not equivalent proofs (one is IdP-level, one is backend-level), and neither can be read as satisfying "a session holding only the OLD scope does not authorize Evidence Fitness" as literally worded, since no such session can be constructed at all.

**CI Black failure — reproduced.** `black --check --diff backend/app/api/information_element_evidence_fitness/router.py` fails: Black's canonical formatter collapses the now-shorter `_authorize(\n    authenticated, "evidence-fitness:read", dependencies, correlation\n)` (a line-wrap sized for the retired 41-character literal) onto a single line, since `_authorize(authenticated, "evidence-fitness:read", dependencies, correlation)` now fits within Black's line-length limit. `isort --check-only .`, `ruff check .`, and `mypy app` all pass clean. Confirmed zero semantic change in the required diff.

**Router-test individual-invocation failure — root-caused.** `backend/app/tests/conftest.py` defines `migrated_engine` as a **session-scoped fixture, requested explicitly by test functions, not `autouse`**. `test_information_element_evidence_fitness_resolution_postgres.py` and `test_information_element_evidence_fitness_resolution.py` both request it directly (`def test_x(migrated_engine: Engine) -> None`); `test_information_element_evidence_fitness_router.py` never does. Pytest session-scoped fixtures are established once per process and persist for every test collected in that same process — so when the three files are invoked together in one `pytest` command (one process, one session), the migration runs once (triggered by either of the first two files) and the resulting schema is available to the router file's `test_missing_bearer_token_rejects_before_service_disclosure` test too. Invoked as three fully separate `pytest <file>` processes, no process running the router file alone ever triggers migration, and that one test fails on `relation "api_security_audit_events" does not exist`. **This is a real, pre-existing characteristic of the test suite's fixture architecture — not a defect introduced by, or specific to, the scope-literal migration**, and it is not a source defect: the repository's own established test-invocation convention (`Makefile`'s `test` target: `cd backend && pytest`, and the CI `backend` job: a single `pytest` invocation over the whole suite) already runs all tests in one process, exactly the invocation under which this passes. **Disposition: B — the original R1 contract's phrasing ("run individually") was imprecise about invocation scope, not the test source.** No test-fixture or production path is authorized or required for this item.

---

## 1. Amendment #1 — corrected OLD-literal inventory rule (replaces original §18.1)

The original R1 correction's §18.1 ("may remain **only** inside the five historical artifacts listed in §16") is superseded, for verification purposes, by the following rule. **The five §16 historical artifacts remain unchanged and unedited; this rule only enlarges the set of locations where the OLD literal's continued presence is expected and compliant:**

> The OLD literal (`information-element-evidence-fitness:read`) may remain **only** in:
> 1. The five historical CDD artifacts originally listed in §16 of the R1 correction (`CDD-029-...`, `CDD-031-...`, `CDD-034-Evidence-Fitness-Frontend-Exposure-Authorization.md`, `CDD-034-Governed-Evidence-Fitness-Exposure-Artifact-Authorization.md`, `CDD-034-Governed-Evidence-Fitness-Exposure.md`).
> 2. The original R1 correction governance artifact (`CDD-034-Artifact-Authorization-Azure-Entra-Scope-Length-R1-Correction.md`) and this additive R1-G-R1 amendment artifact itself, solely because both documents must discuss the retired literal to document the migration and its verification.
> 3. Exactly one rejection-only constant in `backend/app/tests/test_information_element_evidence_fitness_router.py` (the existing `_RETIRED_SCOPE = "information-element-evidence-fitness:read"`), whose only referenced use is constructing a principal to prove the retired literal does **not** authorize the endpoint.
>
> **Explicitly, and without exception:**
> - OLD must not appear in production authorization code (`backend/app/api/information_element_evidence_fitness/router.py` or anywhere else `_authorize`/`authorize` is called).
> - OLD must not appear as a Keycloak granting scope (`keycloak/ctec-realm.json`'s `clientScopes[].name` or any `defaultClientScopes`/`optionalClientScopes` entry).
> - OLD must not appear in any Azure granting/runtime configuration (`infra/azure/**`).
> - OLD must never be accepted through a compatibility branch, fallback, alias, or normalization step in any authorization check.
> - No occurrence beyond the three categories above is authorized. Repository search remains a required proof at implementation-verification time.

## 2. Amendment #2 — executable two-layer OLD-scope adversarial proof (replaces original §18.11)

The original §18.11 ("a session holding only the OLD scope does not authorize Evidence Fitness — empirically demonstrated") is superseded by the following two-part proof, **both parts required, neither substituting for the other**:

> **PROOF A — Live identity-provider retirement.** Using the real Keycloak authorization endpoint against a running instance built from the candidate's `keycloak/ctec-realm.json`, submit an authorization request whose `scope` parameter includes the literal `information-element-evidence-fitness:read`. Require Keycloak to refuse token issuance outright — an `invalid_scope` error (or Keycloak's then-current equivalent rejection signal) returned before any login form or token is produced. This proves the retired permission cannot be obtained through the configured identity provider at all; no authenticated OLD-only token needs to be (or can be) manufactured, because the IdP correctly never issues one.
>
> **PROOF B — Backend defense-in-depth.** Independently of Proof A, construct a `TrustedPrincipal` carrying only `information-element-evidence-fitness:read` in its `scopes` tuple (via `_principal(scopes=(_RETIRED_SCOPE,))` in `test_information_element_evidence_fitness_router.py`) and invoke `POST /api/v1/information-element-evidence-fitness/resolve` through the real router. Require `403 AUTHORIZATION_SCOPE_REQUIRED` and zero downstream `service.calls`.
>
> Together, these prove: the IdP will not issue the retired scope, **and** the backend would independently reject it even if some future or misconfigured caller ever managed to present it in a synthetic/adversarial token. Neither proof alone is sufficient; both are required and must be independently reproducible at verification time.

## 3. Amendment #3 — Black-formatting-only correction

Authorizes exactly the minimum formatting change required by authoritative CI, and nothing else:

> `backend/app/api/information_element_evidence_fitness/router.py`: apply Black's canonical formatting to the `_authorize(...)` call inside `resolve()` — collapsing it from its current three-line wrapped form to Black's required single-line form. **Semantic effect: none.** The scope-literal argument remains exactly `"evidence-fitness:read"`; the endpoint, authorization behavior, tenant behavior, and every other line in the file are unchanged. No other formatting, refactor, or cleanup in this file or any other production file is authorized.

## 4. Router-test isolation — no correction authorized (Disposition B, per §0 above)

No test-fixture, conftest, or production path is authorized or required. The original R1 verification contract's item 6 ("the three modified test files, run individually... pass") is corrected, for verification purposes, to the exact executable invocation below (§6 of this document), which is the repository's own already-established convention (a single `pytest` process covering all relevant files), not a new mechanism.

## 5. Corrected implementation authorization ceiling

```
MODIFY = 1
CREATE = 0
DELETE = 0
```

| Path | Action | Reason |
|---|---|---|
| `backend/app/api/information_element_evidence_fitness/router.py` | MODIFY | Black-canonical reformatting of the `_authorize(...)` call only (Amendment #3). No other file is authorized: `keycloak/ctec-realm.json`, `frontend/**`, `infra/azure/**`, `.github/workflows/**`, dependency files, database schema, endpoint schemas, and tenant-boundary implementation are explicitly **not** reopened — none of the three VM defects requires touching them. |

## 6. Refrozen, executable verification contract (binding on the next implementation-completion and VM phases)

1. Exact candidate ancestry: `main → R1-G (b1ed927...) → R1-I-R1 implementation commit`, single-parent linear chain.
2. This amendment's own SHA-256, and the original R1 correction's SHA-256 (`10fe34455623806da8c8c97831ce1c681ce1b2470e0cc6060d218a505741e598`), both independently verified, the latter byte-identical/unedited.
3. `len("evidence-fitness:read") == 21`; `21 < 40`.
4. Repository-wide search for `information-element-evidence-fitness:read` returns occurrences **only** in the three categories of Amendment #1 §1 above — no other location.
5. NEW scope (`evidence-fitness:read`) accepted by the protected endpoint (200).
6. Missing scope rejected (`403 AUTHORIZATION_SCOPE_REQUIRED`).
7. Proof B (synthetic OLD-only `TrustedPrincipal`) rejected with `403 AUTHORIZATION_SCOPE_REQUIRED`, zero downstream service calls.
8. Proof A (real Keycloak authorization request for the OLD literal) rejected at the IdP as `invalid_scope` or equivalent, before any token is issued.
9. Protected endpoint unchanged: `POST /api/v1/information-element-evidence-fitness/resolve`.
10. Tenant boundary unchanged (sourced from `TrustedPrincipal.tenant_id`, untouched by any authorized path).
11. Keycloak NEW-scope parity: `clientScopes[].name` and `ctec-frontend.defaultClientScopes[]` both read `evidence-fitness:read`.
12. OLD literal absent from Keycloak's granting configuration (both locations above).
13. Targeted Evidence Fitness tests pass: run `pytest backend/app/tests/test_information_element_evidence_fitness_resolution_postgres.py backend/app/tests/test_information_element_evidence_fitness_resolution.py backend/app/tests/test_information_element_evidence_fitness_router.py` **as one combined invocation** (one process, one session) — the repository's own established convention — and confirm every individual test in the `-v` output passes, including `test_missing_bearer_token_rejects_before_service_disclosure`. Running any of these three files as a fully separate, isolated process is not required and is not expected to independently establish schema state for tests that do not request `migrated_engine`.
14. Full backend regression (`pytest`, whole suite) passes with 0 failures.
15. Authoritative CI-equivalent gates pass: `black --check .`, `isort --check-only .`, `ruff check .`, `mypy app` — all clean, zero reformatting required anywhere.
16. Frontend `format:check`, `lint`, `typecheck`, `build`, and full test suite pass from a clean, committed candidate.
17. Fresh, isolated Docker rebuild/runtime smoke: all services healthy, `keycloak-bootstrap` exits 0, no material log errors.
18. Real authenticated NEW-scope token (via live Keycloak PKCE login) independently decoded and confirmed to carry `evidence-fitness:read`.
19. That authenticated request to `POST /api/v1/information-element-evidence-fitness/resolve` returns 200.
20. An unauthenticated request to the same endpoint returns 401.
21. Exact-path diff verification: the implementation diff against this amendment's governance head contains **exactly** the one authorized path (§5 above) — no CREATE, no DELETE, no additional MODIFY.
22. PR-required CI checks (`backend`, `frontend`, `containers`) all green on the exact candidate SHA.
23. No Azure deployment occurs before R1 (as amended) closes.
24. `CTEC_OIDC_SCOPE_CLAIM`/`scp` (the separate R2 item) is not implemented, referenced, or touched by this correction.
25. No path outside §5's single authorized file is modified.
26. Governance and implementation branches remain clean (`git status --porcelain` empty) at every checkpoint.

## 7. R2 separation (explicit, unchanged)

The Microsoft Entra delegated-permission claim name (`scope` vs `scp`, i.e. `CTEC_OIDC_SCOPE_CLAIM`) remains a wholly separate, unresolved, unimplemented item, reserved for its own R2 correction after this R1 (as amended) closes. This document authorizes no work toward it.

---

*This amendment is additive only. It does not edit, supersede in place, or invalidate the original R1 correction's scope decision (§§1–17 of `CDD-034-Artifact-Authorization-Azure-Entra-Scope-Length-R1-Correction.md`), which remains frozen and byte-identical. It replaces only the two literally-unsatisfiable verification clauses (§18.1, §18.11) and the one CI-blocking gap (Black formatting) discovered by AZURE-DEV-EXTERNAL-ID-SCOPE-R1-VM, and clarifies the intended invocation scope of the router-test verification item.*
