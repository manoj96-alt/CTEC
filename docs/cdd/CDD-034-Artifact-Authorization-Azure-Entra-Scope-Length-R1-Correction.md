# CDD-034 — Artifact Authorization: Azure Entra Scope-Length R1 Correction

**Status:** FROZEN
**Corrects/extends:** `CDD-034-Governed-Evidence-Fitness-Exposure.md`, `CDD-034-Governed-Evidence-Fitness-Exposure-Artifact-Authorization.md`, `CDD-034-Evidence-Fitness-Frontend-Exposure-Authorization.md`
**Originating phase:** AZURE-DEV-EXTERNAL-ID-SCOPE-R1 (DRG → G → I → VM)
**Scope of this document:** Literal OAuth scope-name migration only. No authorization broadening. No endpoint, tenant-boundary, or business-logic change.

---

## 1. Empirical Entra incompatibility

During manual Microsoft Entra External ID application-registration configuration for Azure DEV (tenant `Noetva External`, tenant ID `8f9e2dee-5a5b-4b33-9044-4d11691899de`; backend registration `noetva-dev-backend-api`, Application ID URI `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`), Entra's live "Add a scope" UI **rejected** the existing governed scope name because Entra enforces a strict **<40-character limit** on custom delegated API scope names. This is an empirically observed, external platform constraint — not a repository defect and not hypothetical.

## 2. OLD scope

```
information-element-evidence-fitness:read
```

## 3. NEW scope

```
evidence-fitness:read
```

## 4. Exact character counts

| | Literal | Length |
|---|---|---|
| OLD | `information-element-evidence-fitness:read` | **41** |
| NEW | `evidence-fitness:read` | **21** |

`21 < 40` — independently re-verified in this document's own governing phase via `len("evidence-fitness:read") == 21`.

## 5. Reason for selecting `evidence-fitness:read`

Three candidates were evaluated against the empirical constraint and against Noetva's existing naming ontology:

| Candidate | Chars | Verdict |
|---|---|---|
| `evidence-fitness:read` | 21 | **Selected.** Matches the capability's own pre-existing colloquial name used everywhere else in the codebase — `frontend/lib/evidence-fitness/`, `frontend/app/quality/evidence-fitness/page.tsx`, and CDD prose ("Gate T evidence-fitness"). The rename brings the OAuth scope literal *into* alignment with an already-established convention, not away from one. Retains `:read` action semantics. Does not collapse into the unrelated `oqi-reference-evidence:*` scope family. |
| `information-evidence-fitness:read` | 33 | Rejected: drops only "element"; matches no existing naming precedent anywhere in the codebase; no material benefit over the selected candidate. |
| `info-element-evidence-fitness:read` | 34 | Rejected: introduces a novel "info" abbreviation used by no other scope, creating inconsistency with the sibling scope `information-element-context:read` (already created in Entra, spelled in full). |

No authorization is broadened, narrowed in meaning, or generalized — this is a pure literal-string migration for one existing, unchanged capability.

## 6. Exact 5-file implementation authorization

| # | Path | Action |
|---|---|---|
| 1 | `backend/app/api/information_element_evidence_fitness/router.py` | MODIFY |
| 2 | `backend/app/tests/test_information_element_evidence_fitness_resolution_postgres.py` | MODIFY |
| 3 | `backend/app/tests/test_information_element_evidence_fitness_resolution.py` | MODIFY |
| 4 | `backend/app/tests/test_information_element_evidence_fitness_router.py` | MODIFY |
| 5 | `keycloak/ctec-realm.json` | MODIFY |

## 7. CREATE/MODIFY/DELETE accounting

```
CREATE = 0
MODIFY = 5
DELETE = 0
TOTAL  = 5
```

No 6th implementation path is authorized under this correction. No frontend product-source file. No `infra/azure/*` Bicep file. No `.github/workflows/*` file. No `infra/azure/environments/*/main.parameters.json` file. No dependency file. No unrelated refactor.

## 8. Exact expected literal-line changes (six lines, five files)

1. `backend/app/api/information_element_evidence_fitness/router.py` — the `_authorize(authenticated, "information-element-evidence-fitness:read", ...)` call site changes its scope-string argument to `"evidence-fitness:read"`.
2. `backend/app/tests/test_information_element_evidence_fitness_resolution_postgres.py` — the `scopes=("information-element-evidence-fitness:read",)` fixture literal changes to `scopes=("evidence-fitness:read",)`.
3. `backend/app/tests/test_information_element_evidence_fitness_resolution.py` — the same fixture-literal change.
4. `backend/app/tests/test_information_element_evidence_fitness_router.py` — the `_SCOPE = "information-element-evidence-fitness:read"` constant changes to `_SCOPE = "evidence-fitness:read"` (one line; every use of `_SCOPE` in that file follows automatically).
5. `keycloak/ctec-realm.json` — the `clientScopes[].name` field (currently `"information-element-evidence-fitness:read"`) changes to `"evidence-fitness:read"`.
6. `keycloak/ctec-realm.json` — the corresponding entry in `ctec-frontend.defaultClientScopes[]` changes from `"information-element-evidence-fitness:read"` to `"evidence-fitness:read"`.

No other line in any of the five files may change.

## 9. Authorization invariant

`backend/app/api/information_element_evidence_fitness/router.py`'s `_authorize()` helper is pure string membership: `if scope in authenticated.scopes: return`, else `403 AUTHORIZATION_SCOPE_REQUIRED`. This proves, by construction:

- **NEW scope present → accepted** (200, resolves normally).
- **OLD scope alone present → rejected** (`"information-element-evidence-fitness:read" != "evidence-fitness:read"` as plain string equality; a token carrying only the retired 41-character literal does not satisfy the new check).
- **Neither scope present → rejected** (`403 AUTHORIZATION_SCOPE_REQUIRED`, unchanged path).
- **No dual-scope compatibility branch is authorized or permitted.** The implementation must not accept both literals during any transition window.

## 10. Tenant isolation unchanged

Tenant-boundary enforcement is sourced exclusively from `TrustedPrincipal.tenant_id` (`backend/app/api/supplier_risk/authentication.py`), constructed independently of and prior to the scope check in `_authorize()`. This document authorizes no change to tenant-boundary logic anywhere.

## 11. Endpoint unchanged

`POST /api/v1/information-element-evidence-fitness/resolve` (route prefix, path, method, request/response schemas, and all `_FAILURE_HTTP_STATUS` mappings) is unchanged. Only the scope-string literal compared inside `_authorize()` changes.

## 12. Business logic unchanged

`InformationElementEvidenceFitnessResolutionApplicationService` and every downstream resolution/evidence-fitness evaluation path are untouched. This correction authorizes a scope-literal rename only.

## 13. Keycloak/Azure parity requirement

The Azure (Entra External ID) and local/Docker (Keycloak) authorization contracts must use the **identical** scope literal — `evidence-fitness:read` — never two different literals for the same capability. `keycloak/ctec-realm.json` is therefore in scope (item 5/6 above), not merely the Azure-side configuration.

## 14. No frontend product-source change

No file under `frontend/` is authorized for modification by this correction. The scope is not currently requested by name in any frontend source file (see item 15).

## 15. Azure frontend runtime scope requirement (deployment-configuration value, not a source change)

At Azure image-build time, the `NEXT_PUBLIC_OIDC_SCOPE` value (consumed by the existing, unmodified `frontend/lib/auth/config.ts` environment-variable-first design) must include:

```
api://3a880f13-985d-4a71-be05-20f97b9bcfa3/evidence-fitness:read
```

among its space-delimited entries. This is a GitHub Actions variable / deployment-time value (Guide Part 20/25), not a repository source edit, and is explicitly **out of scope** for the R1-I implementation commit.

## 16. Historical CDD preservation rule

The following existing artifacts contain the OLD literal as an accurate historical record of what this scope was named when each was written. They are **HISTORICAL — PRESERVE** and **must not be edited** by R1-I or any later phase under this correction's authority:

- `docs/cdd/CDD-029-Information-Element-Context-Keycloak-Scope-Defect-Authorization.md`
- `docs/cdd/CDD-031-Evidence-Fitness-Exposure-Clarification-and-Remediation-Report.md`
- `docs/cdd/CDD-034-Evidence-Fitness-Frontend-Exposure-Authorization.md`
- `docs/cdd/CDD-034-Governed-Evidence-Fitness-Exposure-Artifact-Authorization.md`
- `docs/cdd/CDD-034-Governed-Evidence-Fitness-Exposure.md`

History is not rewritten to make the old scope name disappear. This document is the sole authorized mechanism for recording the migration.

## 17. Explicit exclusion of the scope-claim (`scope` vs `scp`) correction

A separate DRG finding established that `infra/azure/resources.bicep`'s `backendEnvVars` does not wire `CTEC_OIDC_SCOPE_CLAIM` (Azure would use the code default `"scope"`, while Microsoft Entra delegated-permission tokens conventionally expose the claim as `scp`). **This is a distinct compatibility boundary, touching different files (`infra/azure/resources.bicep`, `infra/azure/environments/*/main.parameters.json`) via a different mechanism (a new Bicep parameter/env-var), and is explicitly NOT authorized, implemented, or bundled under this correction.** It is reserved for a separate R2 correction after R1 closes.

## 18. Frozen implementation verification contract (binding on R1-I / R1-VM)

1. **Repository literal search:** after implementation, `information-element-evidence-fitness:read` may remain **only** inside the five historical artifacts listed in §16. No live production, test, configuration, or Keycloak file may retain it.
2. **Authorization:** NEW scope → accepted (200); OLD scope alone → `403 AUTHORIZATION_SCOPE_REQUIRED`; missing scope → `403`.
3. **Protected endpoint unchanged:** `POST /api/v1/information-element-evidence-fitness/resolve`.
4. **Tenant boundary unchanged** (§10).
5. **Keycloak parity:** `clientScopes[].name` and `ctec-frontend.defaultClientScopes[]` both read `evidence-fitness:read`.
6. Relevant targeted Evidence Fitness tests (the three modified test files, run individually) pass.
7. **Full backend regression suite** passes (matches this repository's established governance pattern for any authorization-relevant change).
8. Frontend `format:check`, `lint`, `typecheck`, `build`, and full test suite are run and pass — even though no frontend production source is modified, proving zero unintended impact.
9. Docker image/runtime rebuild and `docker compose up` smoke, confirming Evidence Fitness resolves end-to-end locally with the NEW scope.
10. Local authenticated Evidence Fitness smoke succeeds with the NEW scope granted.
11. A session holding only the OLD scope does **not** authorize Evidence Fitness (empirically demonstrated, not merely asserted).
12. The R1-I candidate diff contains **exactly** the five authorized implementation paths (§6) plus this document's own separately-governed publication path(s) — no 6th or 7th path.
13. **No Azure deployment occurs before R1 closes** (R1-I implements and opens, but does not merge, a PR; Azure execution resumes only in a later phase).
14. Independently re-prove, at implementation time: `len("evidence-fitness:read") == 21` and `21 < 40`.

---

*This document is a narrow, additive governance correction. It does not modify, supersede, or invalidate any other clause of CDD-034's original artifacts beyond the single scope-literal migration authorized above.*
