# CDD-066 — Frontend OIDC Scope Coverage Correction

**Status:** FROZEN
**Originating phase:** AZURE-DEV-FRONTEND-OIDC-SCOPE-COVERAGE (DRG → I → VM)
**Amends:** nothing frozen in place. Extends the single-authority default-scope architecture already frozen by PAD-002 §15 (`architecture/released/v1.10/PAD-002-Local-Development-Identity-Provider-and-Demo-Persona-Authorization-Boundary_v1.0_FROZEN.md`) by correcting the literal value of the one default it governs, in light of live capabilities added after that default was last set. Independent of, and does not reopen, CDD-063/CDD-064/CDD-065 (Azure OIDC claim-name architecture) — this correction touches only which scopes the frontend requests, never how the backend parses `scp`/`noetva_tenant_id`/`tenant_id`.

**Scope:** A single frontend source correction — `frontend/lib/auth/config.ts`'s hard-coded default OIDC scope string is missing four scopes that four already-live, user-accessible frontend capabilities require, and this gap is invisible in local testing (Keycloak masks it) but real in Azure Entra (which does not).

---

## 1. Authoritative baseline at freeze

Main SHA: `f91accd9f0d6b37acde3093a42c6f9a2117249a2` — independently re-verified against `origin/main` and GitHub `main`, unchanged since the immediately preceding preflight.

## 2. Reproduced finding: the frontend under-requests scopes

`frontend/lib/auth/config.ts` (re-read directly): the code-level default (used whenever `NEXT_PUBLIC_OIDC_SCOPE` is unset or empty) is exactly:
```
openid profile supplier-risk:read entity-resolution:read ontology-copilot:ask ontology-modeling:read oqi-remediation:authorize oqi-remediation:report-execution
```
— 6 backend-delegated scopes plus `openid`/`profile`. The backend's `noetva-dev-frontend` Entra app registration exposes, and already has tenant-wide admin consent for, 11 delegated scopes (independently re-confirmed via `oauth2PermissionGrants` in the immediately preceding preflight). Five are never requested by the frontend default: `oqi:read`, `information-element-context:read`, `evidence-fitness:read`, `supply-chain-impact:read`, `supply-chain-impact:evaluate`.

## 3. Root cause

`git log --follow -- frontend/lib/auth/config.ts` shows the default was last touched by the OQI-UX remediation-lifecycle work (which added `oqi-remediation:authorize`/`oqi-remediation:report-execution`). The `oqi:read` dashboard/findings capability, the `information-element-context` lookup capability, the `evidence-fitness` capability, and the `supply-chain-impact` capability were all added as live frontend routes in later, independent work that never revisited this one shared constant. This is a mechanical drift, not a deliberate policy — PAD-002 §15 itself only mandates that `config.ts`'s default be *the* single authoritative source and be least-privilege; it does not freeze its literal contents, which are expected to track live capability as capability grows.

**Why this was invisible locally, real in Azure:** independently confirmed via `keycloak/ctec-realm.json` — every one of the 11 scopes already exists as a Keycloak client scope, and `ctec-frontend`'s `defaultClientScopes` (not `optionalClientScopes`) already lists **all 11** (plus `ctec-identity`). Keycloak grants a client's default scopes to every token issued to it regardless of what the authorization request's `scope` parameter says — so locally, the frontend's narrow literal request has never actually limited what a real token contains, masking the gap completely. Microsoft Entra does not have an equivalent "default scope" concept for delegated permissions: an Entra access token's `scp` claim contains only what was actually requested (among what's consented). Admin consent already covering all 11 (proven in the preceding preflight) does not compensate for this — consent and request are independent axes in Entra's model. This is why the gap is a genuine, live Azure-only defect despite passing all existing local testing.

## 4. Capability-to-scope proof (evidence, not assumption)

For each of the 5 currently-unrequested scopes, independently traced from real frontend source (not inferred):

| Scope | Backend enforcement | Frontend API client | Live caller | Verdict |
|---|---|---|---|---|
| `oqi:read` | `backend/app/api/oqi/router.py` `_require_read()`, gating every `GET` route (command-center, findings, findings/{id}, evidence, ontology-impact, business-impact, reliance, agent-investigation, remediation) | `frontend/lib/oqi/api-client.ts` (`oqiApi`) | `app/quality/findings/[findingId]/page.tsx` calls `.findingDetail`, `.evidence`, `.ontologyImpact`, `.businessImpact`, `.reliance`, `.agentInvestigation`, `.remediation`; `app/quality/findings/page.tsx` and `app/quality/_components/command-center.tsx` also import it | **LIVE — REQUIRED** |
| `information-element-context:read` | `backend/app/api/information_element_context/router.py` line 56, `_authorize(...)` | `frontend/lib/context/api-client.ts` (`contextApi`) | `frontend/app/context/_components/context-lookup.tsx` calls `contextApi.resolve(...)`, rendered on the live `/context` route | **LIVE — REQUIRED** |
| `evidence-fitness:read` | `backend/app/api/information_element_evidence_fitness/router.py` line 57, `_authorize(...)` | `frontend/lib/evidence-fitness/api-client.ts` (`evidenceFitnessApi`) | `frontend/app/quality/evidence-fitness/page.tsx` calls `evidenceFitnessApi.resolve(...)` | **LIVE — REQUIRED** |
| `supply-chain-impact:evaluate` | `backend/app/api/supply_chain_impact/router.py`, `POST /evaluations` requires exactly this scope | `frontend/lib/supply-chain-impact/api-client.ts` (`supplyChainImpactApi.evaluate`) | `frontend/app/supply-chain-impact/page.tsx` calls `supplyChainImpactApi.evaluate(supplierEntityId)` — this is the page's entire reason for existing | **LIVE — REQUIRED** |
| `supply-chain-impact:read` | `backend/app/api/supply_chain_impact/router.py`, `GET /evaluations/{id}` requires exactly this scope | `frontend/lib/supply-chain-impact/api-client.ts` (`supplyChainImpactApi.read`) | Repo-wide search (`grep -rn "supplyChainImpactApi" frontend --include="*.tsx" --include="*.ts"`, excluding test files) shows exactly one live import, and only `.evaluate()` is ever called anywhere in the app — `.read()` is exported but has **zero callers** | **NOT LIVE — CODE EXISTS, NO USER-ACCESSIBLE CALLER** |

The router's own docstring independently corroborates the last row: *"An evaluate call's response may include that call's own freshly-created result without separately holding `:read`"* — by design, the live evaluate flow needs nothing from the read route. `supply-chain-impact:read` is provisioned for a future/API-consumer use case (e.g., revisiting a past evaluation by ID) that does not yet exist in the UI.

**Preserved distinctions, applied:** CODE EXISTS (`supplyChainImpactApi.read`) != USER-ACCESSIBLE CAPABILITY (never called) — proven, not asserted. All four REQUIRED rows are genuinely live, navigable routes with a real, non-test call site, not merely imported-but-unused code.

## 5. Frozen minimum required scope set

**4 of the 5 missing scopes are added; 1 is deliberately excluded.** The corrected default (frozen exactly):
```
openid profile supplier-risk:read entity-resolution:read ontology-copilot:ask ontology-modeling:read oqi-remediation:authorize oqi-remediation:report-execution oqi:read information-element-context:read evidence-fitness:read supply-chain-impact:evaluate
```
10 delegated scopes plus `openid`/`profile`. `supply-chain-impact:read` is **not** added — no over-permissioning for convenience, per this artifact's own mandate.

## 6. Architecture decision (Option A only — not B, not C)

**Frozen: Option A — correct the code-level default in `frontend/lib/auth/config.ts` directly.** No Azure/GitHub-specific scope override is introduced.

**Why B/C are rejected, not merely unnecessary:** PAD-002 §15 (already frozen, released v1.10) is explicit and binding: *"There SHALL be exactly one authoritative source for the default browser OIDC scope request: `frontend/lib/auth/config.ts`'s existing code-level default... An operator MAY set `NEXT_PUBLIC_OIDC_SCOPE` explicitly in their own local `.env` to override the default — this is the one sanctioned override path, not a second competing default."* Wiring a new Azure/GitHub-Actions-specific scope value through the deploy pipeline (Option B), or maintaining both a corrected code default *and* an Azure-specific override (Option C), would recreate exactly the "second competing default" PAD-002 §15 was written to eliminate. Since the corrected default is genuinely environment-independent (every one of the 10 scopes is valid and already provisioned in both Keycloak and Entra — proven in §7), there is no environment-specific reason to diverge, and Option A is not just simplest but the only PAD-002-consistent choice.

**Evaluated against the required criteria:**
- **Least privilege:** satisfied precisely — only the 4 scopes proven required by live capability are added; the 1 proven-unused scope is withheld.
- **Local Keycloak compatibility:** trivially satisfied — see §7; Keycloak already grants all 11 via `defaultClientScopes` regardless of the literal request, so this change is a no-op for what Keycloak actually issues, and only makes the request text match reality.
- **Azure Entra compatibility:** this is the change's entire purpose — Entra grants exactly what's requested among what's consented, and consent already covers the corrected set.
- **Deterministic builds / no environment-specific configuration / no configuration drift:** a single literal in application source, identical across every environment and every build, is maximally deterministic — the opposite of the GitHub-variable path CDD-063/CDD-064/CDD-065 correctly used for genuinely provider-specific claim *names* (which cannot be a single cross-provider literal); scope *content* here is not provider-specific.
- **Fail-closed behavior:** unaffected — this changes what's requested, never how the backend authorizes; a missing/insufficient scope still fails closed exactly as before.
- **Future staging/demo/prod:** identical benefit — none of these environments have any reason to request a narrower or different scope set than DEV, since the same frontend code and the same 11 backend capabilities apply uniformly.
- **No dynamic/incremental scope logic:** not introduced — evidence (§4) shows every live capability's need is already satisfiable by one static, additive scope string; nothing in source suggests per-route/incremental consent is needed or already attempted anywhere.

## 7. Local Keycloak non-regression (proven, not assumed)

Independently queried `keycloak/ctec-realm.json`: all 5 previously-discussed scopes (including the withheld `supply-chain-impact:read`) already exist as `clientScopes` entries, and `ctec-frontend`'s `defaultClientScopes` array already contains all 11 delegated scopes (plus `ctec-identity`, `openid`, `profile`). **No Keycloak realm change is required or authorized by this artifact.** Expanding `config.ts`'s requested-scope text to include the 4 newly-required scopes changes nothing about what a local token actually contains (already granted by default); it only makes the explicit request match what was always silently granted.

## 8. Frozen implementation contract

**`frontend/lib/auth/config.ts`** — replace the default scope string (§2) with the corrected string (§5). No other line in this file changes. No change to `BrowserAuthConfig`'s shape, to the `??`/`||` fallback logic, or to any other config field.

**`frontend/tests/browser-session.test.ts`** — update exactly two existing tests that hard-code the literal old default string as their expected value:
1. `"canonical default scope is exactly the least-privilege demo-persona set plus openid/profile, with no write/decide scope beyond the two frozen OQI remediation capabilities"` — update the `expect(config.scope).toBe(...)` literal to the corrected string (§5); add `expect(config.scope).not.toContain("supply-chain-impact:read")` alongside the existing negative assertions; retitle the test to state three action-shaped scopes are now defaulted (the two frozen OQI remediation capabilities plus `supply-chain-impact:evaluate`, each backing a live user-initiated action its page cannot function without) and that no other write/decide scope (`entity-resolution:decide`, `supplier-risk:submit`/`retry`/`replay`, `ontology-modeling:propose`/`approve`/`publish`) is present — all existing negative assertions in this test are retained unchanged.
2. `"an empty-string NEXT_PUBLIC_OIDC_SCOPE (e.g. an unset Docker build arg passed through) falls back to the canonical default, not an empty scope"` — update its `expect(config.scope).toBe(...)` literal to match.

The third existing scope-related test (`"an explicit non-empty NEXT_PUBLIC_OIDC_SCOPE overrides the canonical default"`) is scope-literal-agnostic and requires no change.

**No other file may change.** No Bicep, no environment parameter file, no GitHub workflow, no `.env.example`, no `docker-compose.yml`, no Keycloak realm file, no backend file, no deployment guide. `NEXT_PUBLIC_OIDC_SCOPE`'s existing pass-through in `docker-compose.yml`/`frontend/Dockerfile`/`azure-deploy.yml`'s (absence of) wiring is unaffected and unauthorized to change here (per §6, no override path is being added).

## 9. Exact implementation authorization ceiling

```
CREATE = 0
MODIFY = 2
DELETE = 0
```

| # | Path |
|---|---|
| 1 | `frontend/lib/auth/config.ts` |
| 2 | `frontend/tests/browser-session.test.ts` |

**Explicitly prohibited** (any of the following requires a STOP and a new governance correction, never silent expansion): any `backend/*` path; any `infra/azure/*` path; `docker-compose.yml`; `keycloak/ctec-realm.json`; `.env.example`; `.github/workflows/*`; `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`; any CDD-063/064/065-governed value; `frontend/Dockerfile`; any redirect-URI-related source (redirect/FQDN configuration is explicitly out of scope for this correction — see §12).

## 10. Frozen test contract (summary; exact edits in §8)

1. Frontend requests the complete governed 10-scope set (§5) by default — proven by the updated literal-string assertion.
2. No required selected scope is omitted — proven by the same assertion (exact string equality, not substring containment, so nothing can be silently dropped).
3. `supply-chain-impact:read` is absent from the default — new explicit negative assertion.
4. Retired invalid scope `information-element-evidence-fitness:read` remains absent — already covered by R1(scope-length)'s existing, unmodified non-regression tests (`keycloak/ctec-realm.json` grep, backend router tests); this artifact does not touch and does not need to re-prove that boundary, since nothing here changes the retired-literal contract.
5. `evidence-fitness:read` is present — proven by the same updated literal-string assertion.
6. "Azure build configuration actually propagates the intended scope value" — **not applicable under the frozen architecture (§6)**: no environment-specific wiring is introduced, so there is nothing environment-specific to propagate-test; the single corrected literal applies identically to every build.
7. Local Keycloak compatibility — proven structurally in §7, no new test required (nothing about Keycloak's grant behavior is being changed or newly relied upon).
8. R1(evidence-fitness)/R2(`scp`/`noetva_tenant_id`) non-regression — unaffected by construction: this artifact touches no backend file, no Bicep file, no environment parameter file, and no claim-name configuration; existing R1/R2 tests are not modified and must continue passing unchanged.
9. No implicit-flow/public-client/client-secret change — unaffected by construction: `config.ts`'s `response_type: "code"` and the absence of any secret are untouched; this artifact edits only the `scope` string.

## 11. Truth-contract preservation (binding)

- CODE EXISTS != USER-ACCESSIBLE CAPABILITY — enforced by excluding `supply-chain-impact:read` despite its client code existing.
- ROUTE EXISTS != PRODUCTION-PROVEN WORKFLOW — this artifact does not claim any of these four capabilities has been proven end-to-end against real Azure; it proves only that real Azure would otherwise reject requests these live UI routes already make locally (masked by Keycloak defaults). Operational proof remains for Stage 2 (§13).
- API-ONLY != UI CAPABILITY — the same evidence standard (a real, non-test call site in `frontend/app/**`) was applied uniformly to all 5 candidates; none was included or excluded by assumption.
- DEFERRED CAPABILITY != PRODUCT CAPABILITY — no deferred/planned capability's scope is added; all 4 additions back capabilities already live and reachable in the current frontend build.

## 12. Redirect-URI separation (binding)

This artifact makes no redirect-URI, hostname, or FQDN-related change of any kind. The callback path (`/auth/callback`) and the Azure frontend FQDN's unknown-until-deployment status (established in the immediately preceding preflight) are unrelated to scope content and are not touched, referenced for modification, or blocked by this correction. Redirect/FQDN configuration remains a wholly separate, later, post-Pass-1 deployment action.

## 13. Two-stage verification model

### Stage 1 — Pre-deployment source certification
1. Exact authorized diff — exactly the 2 paths in §9, no third path.
2. `frontend/lib/auth/config.ts`'s new default string matches §5 exactly (byte-for-byte, including scope ordering, since the tests assert exact equality).
3. Both updated `browser-session.test.ts` tests pass, plus the new `supply-chain-impact:read` negative assertion.
4. Full frontend regression passes (format/lint/typecheck/test).
5. No backend file, Bicep file, environment parameter file, Keycloak realm file, or deployment-guide file appears in the diff.
6. R1/R2 non-regression (backend, Bicep, Keycloak) re-confirmed unaffected — trivially, since no such file is touched.
7. GitHub CI green on the exact candidate.
8. This artifact re-verified byte-identical by SHA-256 at every subsequent phase boundary.

**Stage 1 success authorizes merging the source correction only.**

### Stage 2 — Post-deployment real-Entra certification
Requires, against a real, deployed Azure DEV frontend (after redirect/FQDN configuration is separately completed):
1. A real user completes real Entra Authorization Code + PKCE authentication through the corrected frontend build.
2. The real issued access token's `scp` claim is decoded and shown to contain all 10 delegated scopes from §5 (not merely the prior 6).
3. A real authenticated call to each of the four newly-covered capabilities (`/quality/findings` and its detail sub-panels, `/context`, `/quality/evidence-fitness`, `/supply-chain-impact`) succeeds where it would previously have failed with `403 AUTHORIZATION_SCOPE_REQUIRED`.
4. `supply-chain-impact:read` is confirmed absent from the real token (consistent with §5's deliberate exclusion) and that this causes no live-capability failure.

**Only Stage 2 success may declare this correction operationally CLOSED.** Before that, the only permitted conclusion after a successful source merge is:

> **PASS + SOURCE MERGED — FRONTEND SCOPE COVERAGE OPERATIONAL VERIFICATION PENDING AZURE EXECUTION**

## 14. Security invariants (binding, all 6)

1. Least privilege preserved — exactly the 4 proven-required scopes are added; the 1 proven-unused scope is withheld.
2. No new write/decide/propose/approve/publish scope beyond the three now-legitimate action scopes (the two frozen OQI remediation capabilities, and `supply-chain-impact:evaluate` — each backing a live, user-initiated action its own page cannot function without).
3. No change to backend authorization logic, `oidc_scope_claim`/`oidc_tenant_claim` configuration, or any R1/R2/CDD-063/064/065-governed value.
4. No change to implicit grant, public-client, or client-secret configuration.
5. No redirect URI, hostname, or FQDN change.
6. No Azure/Entra/GitHub mutation of any kind — source-only correction.

---

*This document authorizes governance only. It does not implement, deploy, or verify anything itself.*
