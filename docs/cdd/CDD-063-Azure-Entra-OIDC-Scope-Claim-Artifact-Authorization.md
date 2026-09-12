# CDD-063 — Azure Entra OIDC Scope-Claim Artifact Authorization

**Status:** FROZEN
**Originating phase:** AZURE-DEV-EXTERNAL-ID-SCOPE-CLAIM-R2 (DRG → G → I → VM-PREDEPLOY → VM-RUNTIME)
**Scope:** A single, narrow Azure/Entra compatibility configuration — which token claim name the backend trusts for delegated-permission (scope) authorization on Azure, versus local/Docker/Keycloak. No authentication redesign. No change to authorization semantics, tenant binding, issuer/audience/JWKS validation, or any R1 scope literal.

---

## 1. Authoritative baseline at freeze

Main SHA: `ef523fd0f8d10805a7479a6b8886e735f090bc1d`. R1 independently re-verified closed at this commit: production authorization requires exactly `evidence-fitness:read` (`backend/app/api/information_element_evidence_fitness/router.py`); Keycloak's `clientScopes`/`ctec-frontend.defaultClientScopes` both read `evidence-fitness:read`; both R1 governance artifacts present with their frozen hashes (`CDD-034-Artifact-Authorization-Azure-Entra-Scope-Length-R1-Correction.md` = `10fe34455623806da8c8c97831ce1c681ce1b2470e0cc6060d218a505741e598`; `CDD-034-Artifact-Authorization-Azure-Entra-Scope-Length-R1-G-R1-Amendment.md` = `7dc1d712084f876ef96d7cacba4ec02995adc3f9bc9e79463e3651b815f6270d`). This document does not reopen, reference for modification, or depend on any R1 scope literal.

## 2. Revalidated current architecture (re-read directly at freeze, not assumed)

`backend/app/core/config.py`: `oidc_scope_claim: str = "scope"`, bound via `Settings`' `env_prefix="CTEC_"` to `CTEC_OIDC_SCOPE_CLAIM`.

`backend/app/api/supplier_risk/authentication.py`, `OidcJwtVerifier._principal()`:
```python
scopes = _claim_values(claims.get(self._settings.oidc_scope_claim))
```
```python
def _claim_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(sorted(set(value.split())))
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(sorted(set(value)))
    return ()
```
Confirmed: pure name-based lookup by whichever claim `oidc_scope_claim` names; no second claim name is ever consulted; absent, `None`, or any non-string/non-list-of-string value yields `()` (empty scopes, fail-closed through the existing `_authorize()` string-membership check elsewhere in the codebase).

## 3. Frozen provider-specific claim architecture

**Local / Docker / Keycloak:** `CTEC_OIDC_SCOPE_CLAIM` remains unset. Backend default remains `"scope"`. Keycloak continues issuing a space-delimited `scope` claim (empirically observed across many real, live-decoded tokens throughout this engagement). **No change.**

**Azure / Microsoft Entra External ID:** explicitly configure `CTEC_OIDC_SCOPE_CLAIM=scp`.

**Explicitly prohibited, without exception:**
- No automatic provider detection.
- No `scope` ↔ `scp` fallback in either direction.
- No dual-claim union or acceptance of both names.
- No claim aliasing.
- No wildcard scope authorization.
- No compatibility shim of any kind.

Invariant: **exactly one authoritative configured scope claim per runtime environment.**

## 4. Frozen Entra authorization model

Noetva Azure DEV's governed identity flow is Authorization Code + PKCE, frontend `noetva-dev-frontend`, backend API `noetva-dev-backend-api`, **delegated API permissions**. The expected delegated-permission claim is `scp`. Application permissions/app roles (`roles`) are explicitly **not** the model R2 introduces or migrates toward — `roles` remains reserved for whatever it already governs (`oidc_roles_claim`, untouched) and must never substitute for `scp`.

## 5. Frozen parser decision — no production parser change authorized

`_claim_values()` already handles a space-delimited string identically regardless of which claim name it is called with. Microsoft's documented convention for Entra delegated permissions is exactly that shape (`"scp": "scope-a scope-b scope-c"`). **No modification to `backend/app/core/config.py` or `backend/app/api/supplier_risk/authentication.py` is authorized under this artifact.** If future evidence (specifically, Stage 2 real-token inspection, §9 below) reveals a materially different shape, that evidence must trigger a new, separate governance correction — not a silent implementation change.

## 6. Frozen Azure Bicep change

**`infra/azure/main.bicep`** — add, adjacent to the existing `oidcJwksUrl` parameter:
```bicep
@description('OAuth scope-claim name the backend trusts for delegated authorization (Entra External ID: scp; matches Noetva\'s Keycloak default of scope only if explicitly set otherwise).')
param oidcScopeClaim string
```
and forward it into the `resources.bicep` module call, alongside the existing `oidcJwksUrl: oidcJwksUrl` line:
```bicep
oidcScopeClaim: oidcScopeClaim
```

**`infra/azure/resources.bicep`** — add the matching parameter declaration (same description, no default) adjacent to the existing `oidcJwksUrl` parameter, and add exactly one new `backendEnvVars` entry adjacent to the existing `CTEC_OIDC_JWKS_URL` entry:
```bicep
{ name: 'CTEC_OIDC_SCOPE_CLAIM', value: oidcScopeClaim }
```
No secret reference. No Key Vault entry. No runtime fallback logic anywhere in Bicep.

## 7. Frozen environment parameter contract

Authorize exactly these four files, each receiving exactly one new key:
```json
"oidcScopeClaim": { "value": "scp" }
```
- `infra/azure/environments/dev/main.parameters.json`
- `infra/azure/environments/staging/main.parameters.json`
- `infra/azure/environments/demo/main.parameters.json`
- `infra/azure/environments/prod/main.parameters.json`

Rationale: all four already commit unconditionally to Microsoft Entra External ID (each already carries `REPLACE_WITH_ENTRA_EXTERNAL_ID_*` placeholders for `oidcIssuer`/`oidcAudience`/`oidcJwksUrl` — none references Keycloak or any alternate provider). Unlike those three values (genuinely tenant-specific, unknowable until a real Entra tenant exists), `scp` is deterministic, provider-specific, non-secret, and not tenant-specific — the concrete value `"scp"` is used directly; no placeholder is authorized here.

## 8. Frozen focused-test contract

Authorize modification only to `backend/app/tests/test_oidc_authentication.py`. Add exactly two new test functions (no existing test in this file may be altered):

**Test 1 — Entra `scp` extraction.** Construct `Settings(..., oidc_scope_claim="scp")`, build an otherwise-valid signed token whose payload replaces `"scope"` with `"scp": "supplier-risk:read entity-resolution:read"`, verify it, and assert `principal.scopes` contains exactly the expected parsed set (per the existing sorted/deduplicated tuple behavior already exercised by the file's current tests).

**Test 2 — no fallback to `scope`.** Same `oidc_scope_claim="scp"` configuration, but the token retains `"scope": "supplier-risk:read"` and omits `scp` entirely. Assert `principal.scopes == ()`, proving the configured-`scp` verifier never silently reads the `scope` claim instead.

Do not duplicate any endpoint-level authorization test. Do not modify production authentication source to make these tests pass — if either fails against current source, that is a STOP-worthy discrepancy for R2-I to report, not silently work around.

## 9. Frozen documentation contract

Authorize modification only to `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`, Part 32's backend environment-variable inventory line (the one currently listing `CTEC_ENVIRONMENT`, `CTEC_LOG_LEVEL`, `CTEC_CORS_ORIGINS`, `CTEC_OIDC_ISSUER`, `CTEC_OIDC_AUDIENCE`, `CTEC_OIDC_JWKS_URL`, and the Key Vault secret references). Add `CTEC_OIDC_SCOPE_CLAIM` to that enumeration, with truthful text stating Azure sets it to `scp` through the Bicep/environment-parameter configuration frozen above (§6/§7). Do not rewrite any other section of the Guide. Do not add or imply that real Entra-token proof has already occurred — Stage 2 (§11) remains unperformed until real Azure/Entra execution.

## 10. Exact implementation authorization ceiling

```
CREATE = 0
MODIFY = 8
DELETE = 0
```

| # | Path |
|---|---|
| 1 | `infra/azure/main.bicep` |
| 2 | `infra/azure/resources.bicep` |
| 3 | `infra/azure/environments/dev/main.parameters.json` |
| 4 | `infra/azure/environments/staging/main.parameters.json` |
| 5 | `infra/azure/environments/demo/main.parameters.json` |
| 6 | `infra/azure/environments/prod/main.parameters.json` |
| 7 | `backend/app/tests/test_oidc_authentication.py` |
| 8 | `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` |

**Explicitly prohibited** under this artifact (any of the following requires a STOP and a new governance correction, never a silent expansion): `backend/app/core/config.py`; `backend/app/api/supplier_risk/authentication.py`; `docker-compose.yml`; `keycloak/ctec-realm.json`; any `frontend/*` path; any `.github/workflows/*` path; any R1 governance artifact; any R1 scope literal; any database schema/migration file.

## 11. GitHub variable/secret decision

**No new GitHub Actions variable. No new GitHub Actions secret. No new Key Vault entry.** `scp` is public, non-secret OAuth claim-naming material, deterministic across environments once the provider is known to be Entra — it belongs solely in the governed Azure environment parameter files (§7), following the exact same mechanism `oidcIssuer`/`oidcAudience`/`oidcJwksUrl` already use (parameter file, read directly by the operator-run `az deployment` command — confirmed `azure-deploy.yml` contains no Bicep/`az deployment` invocation at all). Introducing a GitHub variable here would be redundant, unjustified configuration surface.

## 12. Security invariants (binding, all 17)

1. Exactly one authoritative scope-claim name per runtime.
2. Local/Keycloak default remains `scope`.
3. Azure/Entra explicitly uses `scp`.
4. No fallback `scope` → `scp`.
5. No fallback `scp` → `scope`.
6. No dual-claim union.
7. No wildcard scope authorization.
8. Missing configured claim → empty scopes → authorization fails closed.
9. Malformed configured claim → empty scopes → authorization fails closed.
10. `roles` does not substitute for `scp`.
11. Issuer validation unchanged.
12. Audience validation unchanged.
13. JWKS validation unchanged.
14. `tenant_id` validation/binding unchanged.
15. Endpoint scope-membership logic (`_authorize()`) unchanged.
16. Human authority boundaries (recommendation ≠ authorization; remediation ≠ resolution) unchanged — R2 touches no code path related to these.
17. R1's scope-name correction (`evidence-fitness:read`) unchanged.

## 13. R1 non-regression

R2 must not reopen R1. Frozen R1 state — OLD `information-element-evidence-fitness:read`, NEW `evidence-fitness:read` — is unaffected by every path in §10; none references either literal. R2-VM (both stages) must independently re-confirm R1's production authorization and Keycloak configuration remain exactly as R1 left them.

## 14. Two-stage verification model (binding, not to be collapsed)

### Stage 1 — Pre-deployment source certification (can complete before any Azure execution)

Require all of:
1. Exact authorized diff (exactly the 8 paths in §10, no more, no less).
2. Bicep syntax/build validation (`az bicep build` or equivalent) on `main.bicep` and `resources.bicep`.
3. All four environment parameter files parse and contain `oidcScopeClaim: "scp"`.
4. `resources.bicep` genuinely emits `CTEC_OIDC_SCOPE_CLAIM` from the parameter (inspect the compiled/rendered template or the module wiring directly).
5. Test 1 (§8) passes.
6. Test 2 (§8) passes.
7. Missing/malformed-claim fail-closed behavior (§2/§12 items 8–9) re-confirmed intact by the existing, unmodified test suite.
8. Full backend regression passes.
9. `black --check .` clean.
10. `isort --check-only .` clean.
11. `ruff check .` clean.
12. `mypy app` clean.
13. Frontend regression unaffected (no frontend file in the diff; run anyway to prove zero impact).
14. Local Keycloak/Docker regression unaffected (default untouched; empirically re-confirm via a live local login still working exactly as before).
15. `docker compose config --quiet` clean.
16. GitHub CI green on the exact candidate.
17. R1 non-regression re-confirmed (§13).
18. No unauthorized path in the diff.
19. Both R1 governance artifacts (and this one) re-verified byte-identical by SHA-256.

**Stage 1 success authorizes merging the source correction. It does NOT authorize declaring the Entra integration operationally proven.**

### Stage 2 — Post-deployment real-Entra certification (cannot be satisfied before real Azure/Entra execution)

Requires, in the real, deployed Noetva Azure DEV environment, after Entra External ID API scopes and frontend authorization are configured and the backend is deployed with `CTEC_OIDC_SCOPE_CLAIM=scp` genuinely present at runtime:
1. A real user completes real Entra Authorization Code + PKCE authentication.
2. The real issued access token is decoded and inspected.
3. That token genuinely contains an `scp` claim.
4. `scp`'s actual representation matches what the parser expects (space-delimited string, per §5 — or, if not, this is itself a Stage-2 finding requiring a new correction, not an assumption to paper over).
5. The required Noetva delegated scopes (including `evidence-fitness:read`, minted via the governed R1 name) genuinely appear in that `scp` value.
6. The running backend Container App's environment genuinely has `CTEC_OIDC_SCOPE_CLAIM=scp` (inspected directly, not assumed from the Bicep source).
7. A real authenticated request to a scope-gated endpoint succeeds.
8. A request missing the required scope is genuinely rejected.
9. Issuer validation is genuinely correct against the real Entra tenant.
10. Audience validation is genuinely correct against the real Application ID URI.
11. `tenant_id` extraction/binding behaves correctly against a real token.
12. No runtime fallback to `scope` occurs (provable only by the absence of any such code path, already frozen in §5, confirmed once more against the real running artifact).
13. R1's `evidence-fitness:read` capability genuinely works end-to-end through a real Entra-issued token once that permission is configured for a real test user.

**Only Stage 2 success may declare R2 operationally CLOSED.**

## 15. Exact allowed terminology

After Stage 1 passes and the source correction is merged, the only permitted conclusion is:

> **PASS + SOURCE MERGED — R2 OPERATIONAL VERIFICATION PENDING AZURE EXECUTION**

**`R2 CLOSED` may never be stated until Stage 2 succeeds.** This distinction exists specifically to prevent "designed/configured" from being represented as "real-runtime verified."

## 16. Frozen phase sequence

```
R2-G (this document)
→ R2-I           (implement exactly the 8 authorized paths; Stage 1 verification; merge source only)
→ R2-VM-PREDEPLOY (adversarially re-verify Stage 1; merge is already done by R2-I per this repository's established pattern, or R2-VM-PREDEPLOY performs the merge if R2-I only opens the PR — to be resolved narrowly by R2-I's own report, not expanded here)
→ [Azure/Entra External ID execution — a separate, already-existing phase family, not authorized or performed by R2]
→ R2-VM-RUNTIME   (Stage 2 — the only phase permitted to declare R2 operationally CLOSED)
```

## 17. Documented-expectation vs. empirically-proven distinction (binding)

**Documented Microsoft expectation (asserted here, not proven):** Entra External ID delegated permissions are exposed via the `scp` claim as a space-delimited string — this is Microsoft's own extensively published convention for the v2.0 token endpoint, distinct from `roles` (application permissions).

**Not yet empirically proven for Noetva:** the exact claim name and shape actually emitted by Noetva's specific Entra External ID tenant (`Noetva External`, `8f9e2dee-5a5b-4b33-9044-4d11691899de`) and its specific `noetva-dev-backend-api` app-registration configuration, for a specific real, issued token. This artifact does not convert the former into the latter. Stage 2 (§14) is the sole mechanism by which that gap may be closed.

---

*This document authorizes governance only. It does not implement, deploy, or verify anything itself.*
