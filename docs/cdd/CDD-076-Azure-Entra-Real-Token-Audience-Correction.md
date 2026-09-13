# CDD-076 — Azure Entra Real Token Audience Correction

**Status:** FROZEN
**Originating phase:** AZURE-ENTRA-OIDC-R11-R3 (DRG only in this artifact)
**Amends:** nothing frozen in place. Complements CDD-073 (Entra operational correction), CDD-074 (fully-qualified resource-scope correction), and CDD-075 (local-account correction) — all three remain unchanged and each remains proven for its own scope. This artifact addresses a distinct, later-stage real defect discovered only after CDD-075's local account achieved a genuine, successful Microsoft login.
**Scope:** the live Azure Container App backend's `CTEC_OIDC_AUDIENCE` runtime configuration value, and the narrow deployment-guide/IaC-placeholder text that caused it to be set incorrectly. No application source logic, no database, no Key Vault, no app registration, no user flow, no claims-mapping policy, no image rebuild.

---

## 1. Boundaries already closed — reaffirmed, not reopened

**CDD-074 (resource-scope):** the real token's `aud` targets the correct application (`3a880f13-985d-4a71-be05-20f97b9bcfa3`, `noetva-dev-backend-api`), not Microsoft Graph — CDD-074's scope-qualification correction remains proven and is not reopened.

**CDD-075 (local account):** the real login using `noetva-dev-test-2@noetvaexternal.onmicrosoft.com` succeeded end-to-end (Entra sign-in log: `errorCode: 0`). CDD-075 remains proven and is not reopened.

**CDD-073 (claims mapping) — a prior open question is now closed as a side effect of this investigation:** CDD-073 froze the claims-mapping policy but explicitly flagged, at freeze time, that it had never been empirically proven to actually emit `noetva_tenant_id` into a real access token from a real login. The real token decoded in this phase carries `noetva_tenant_id: "noetva-dev-tenant"` — **CDD-073's claims-mapping mechanism is now proven correct end-to-end against a real Microsoft-issued token, for the first time.** This is a confirmatory finding, not a reopening; no correction to CDD-073 is authorized or required.

## 2. Current, distinct blocker

The first protected-capability call after a fully successful real login (`GET /api/v1/oqi/findings`, requiring `oqi:read`) returns `HTTP 401`, body `{"detail":{"code":"AUTH_AUDIENCE_INVALID"}}`. Source-tracing (`backend/app/api/supplier_risk/dependencies.py`, `backend/app/api/oqi/dependencies.py`, `backend/app/api/oqi/router.py`) proves this originates strictly inside `principal()`'s token-validation stage (`OidcJwtVerifier.verify()`), never reaching the separate, later scope-authorization stage (which raises `403`, not `401`) — a structurally distinct, later-stage failure than anything CDD-073/074/075 addressed.

## 3. Real access token — safe evidence (operator-decoded, locally, raw token never disclosed)

```
aud              = 3a880f13-985d-4a71-be05-20f97b9bcfa3
tid              = 8f9e2dee-5a5b-4b33-9044-4d11691899de
iss              = https://8f9e2dee-5a5b-4b33-9044-4d11691899de.ciamlogin.com/8f9e2dee-5a5b-4b33-9044-4d11691899de/v2.0
noetva_tenant_id = noetva-dev-tenant
scp              = (present; includes oqi:read, information-element-context:read, evidence-fitness:read, supply-chain-impact:evaluate)
```

`tid`, `iss`, and `noetva_tenant_id` all match the governed contract exactly. `scp` carries the correctly-formed bare capability names (fully consistent with CDD-074's confirmation that the backend's own authorization call sites compare against bare `scp` values regardless of how the *scope request* was qualified). **`aud` is the sole mismatching claim.**

## 4. Live backend configured expected audience (read-only Azure query)

Container App `noetva-dev-eus2-backend`, plain (non-secret) environment variable:

```
CTEC_OIDC_AUDIENCE = api://3a880f13-985d-4a71-be05-20f97b9bcfa3
```

## 5. Exact live mismatch

```
REAL TOKEN aud (Microsoft-issued)     = 3a880f13-985d-4a71-be05-20f97b9bcfa3
BACKEND CONFIGURED EXPECTED AUDIENCE  = api://3a880f13-985d-4a71-be05-20f97b9bcfa3
```

Not equal, byte-for-byte. `backend/app/api/supplier_risk/authentication.py` passes `audience=self._settings.oidc_audience` directly to `jwt.decode(...)` (PyJWT), which performs exact-match/set-intersection comparison against the token's `aud` claim with no normalization of the `api://` prefix — a mismatched configured value is guaranteed to raise `jwt.InvalidAudienceError`, mapped by the verifier to `AUTH_AUDIENCE_INVALID`. This is the confirmed, complete root cause.

## 6. Backend validator implementation (traced, unchanged, correct)

`backend/app/core/config.py`: `oidc_audience: str = ""` (single configurable string, env `CTEC_OIDC_AUDIENCE`, no default — fails closed if unset). `backend/app/core/dependency_container.py`: constructs `OidcJwtVerifier` only when `oidc_issuer`/`oidc_audience`/`oidc_jwks_url` are all non-empty. `backend/app/api/supplier_risk/authentication.py`: `OidcJwtVerifier.verify()` calls `jwt.decode(token, key, algorithms=..., audience=self._settings.oidc_audience, issuer=self._settings.oidc_issuer, ...)`; `jwt.InvalidAudienceError` → `AuthenticationError("AUTH_AUDIENCE_INVALID")`. This comparison logic is provider-neutral, single-audience, fail-closed, and requires **no change** — the defect is entirely in the *configured value*, not the validation code.

## 7. Microsoft v2.0 access-token `aud` contract (authoritative, fetched directly)

Microsoft Learn, "Access token claims reference" (`access-token-claims-reference`), payload claims table, `aud`:

> *"String, an Application ID URI or GUID. Identifies the intended audience of the token. **In v2.0 tokens, this value is always the client ID of the API.** In v1.0 tokens, it can be the client ID or the resource URI used in the request. The value can depend on how the client requested the token."*

This backend application registration has `api.requestedAccessTokenVersion: 2` (frozen by CDD-073, required for the `acceptMappedClaims` claims-mapping mechanism CDD-073/074/075 all depend on) — under v2.0, `aud` is documented as **always** the bare client ID GUID, never the App ID URI, regardless of how the authorization request was qualified. The real token's `aud` (`3a880f13-985d-4a71-be05-20f97b9bcfa3`) matches this documented contract exactly.

## 8. App ID URI relationship (clarified, not conflated)

`identifierUris: ["api://3a880f13-985d-4a71-be05-20f97b9bcfa3"]` (fresh Graph read, backend app object `1cbed9d5-bd79-4e68-b73c-d9eb5ddaa58c`) is the **Application ID URI** — used to *qualify authorization-request scopes* (`api://3a880f13-985d-4a71-be05-20f97b9bcfa3/oqi:read`, CDD-074's correction) and to *route the claims-mapping policy onto the access token rather than only the ID token* (CDD-073, §Step 22.2). It plays no role in, and is never echoed into, the v2.0 `aud` claim for this application. CDD-074's frontend `NEXT_PUBLIC_OIDC_API_RESOURCE_URI` build-time value remains correct and unchanged — it governs the *scope-request resource prefix*, a wholly separate mechanism from *token audience validation*, per the governing prompt's explicit critical distinction.

## 9. Scope-prefix relationship (clarified, not conflated)

The bare `scp` values in the real token (`oqi:read`, etc.) confirm, independently, that the fully-qualified scope *request* (`api://.../oqi:read`) and the token's resulting `aud`/`scp` claims are governed by separate Microsoft rules: the App ID URI prefix steers *which resource* is targeted during authorization (already proven correct by CDD-074's resourceId evidence), while `aud` is fixed by the v2.0 token-issuance rule in §7 regardless of that prefix.

## 10. Root cause

**Deployment-guide + IaC-placeholder-text defect (classification C + B combined; zero application-source defect).** Specifically:

- `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`, Step 21.3 ("Register the backend (API) app") instructs the operator to save only `BACKEND_API_APPLICATION_ID_URI` from the app registration's "Expose an API" page — it never separately names or instructs saving the bare Application (client) ID GUID as the value that later feeds backend audience configuration.
- `infra/azure/environments/dev/main.parameters.json`, `oidcAudience` parameter placeholder text reads literally `"REPLACE_WITH_API_APPLICATION_ID_URI"` — directly steering the operator, who is following the guide's own naming, to paste the URI form.
- `infra/azure/modules/resources.bicep` line 41, `@description('OIDC audience (API application ID URI)')` — the IaC parameter's own description reinforces the same incorrect assumption at the module level.

The operator correctly followed the guide and the IaC's own naming; the naming itself encoded a wrong assumption about Microsoft's v2.0 `aud` semantics. No application source file, test, or validation script encodes this wrong assumption — `backend/app/tests/test_oidc_authentication.py` tests only generic single-string audience matching (`aud: "ctec"` / `"other"` → `AUTH_AUDIENCE_INVALID`), asserting nothing about GUID-vs-URI form, and required no change.

## 11. Defect classification

Deployment-documentation + infrastructure-as-code placeholder/description text (configuration-value guidance), not application logic, not Entra configuration, not a new authentication-boundary defect.

## 12. Local Keycloak audience contract — preserved, unaffected

CI (`.github/workflows/ci.yml:54`) and local Docker Compose (`docker-compose.yml:83`) both configure `CTEC_OIDC_AUDIENCE: ctec-supplier-risk-api` — an arbitrary bare string wholly independent of any Entra GUID/URI question, matched against whatever `aud` Keycloak's own realm configuration issues. The backend already treats `oidc_audience` as one free-form, per-environment-configured string with no provider-specific parsing or normalization — this is precisely the "configuration over provider-detection" mechanism the governing prompt required to already exist, and it does; **no source change of any kind is required to preserve Keycloak.**

## 13. Options evaluated

**Option A — SELECTED.** Correct only the live Azure runtime `CTEC_OIDC_AUDIENCE` value (URI form → bare GUID form) plus the three narrow documentation/placeholder-text artifacts that caused it, leaving `OidcJwtVerifier`'s comparison semantics, `Settings`, and every other environment (Keycloac local/CI) untouched.

**Option B — rejected.** Changing backend validator semantics (e.g., accepting either GUID or URI form) would accept two audiences for no governed reason, is unsupported by any real requirement (Microsoft's v2.0 contract is unconditional per §7), and directly violates the governing prompt's explicit security requirement against "accepting both client-ID and App-ID-URI without governed necessity."

**Option C — rejected.** Changing Entra/application configuration (e.g., reverting to v1.0 tokens to obtain URI-form `aud`) is not viable: v1.0 tokens are incompatible with the `acceptMappedClaims`/claims-mapping mechanism CDD-073 governed and this phase just empirically proved works correctly (§1) — reverting would reopen a closed, proven boundary to chase a value Microsoft's v2.0 contract will never emit for this registration type regardless.

**Option D — not applicable.** No smaller correction exists: the mismatch is a single configured string value plus its three textual sources.

## 14. Selected correction architecture

Option A. Matches Microsoft's documented v2.0 token semantics exactly (§7); preserves Keycloak (§12) with zero source change; preserves fail-closed validation (`OidcJwtVerifier` is untouched — still rejects any non-matching audience); requires exactly one configured audience string (unchanged mechanism, corrected value only); accepts no additional audience values; does not weaken issuer/audience validation in any way; is fully reproducible from an empty Azure environment once the corrected guide/placeholder text is followed.

## 15. Security invariants (unchanged, reaffirmed)

Audience validation remains fail-closed: `OidcJwtVerifier.verify()` continues to reject any token whose `aud` does not exactly equal the single configured `CTEC_OIDC_AUDIENCE` value, with no fallback, no multi-audience acceptance, no warning-only mode, and no provider auto-detection. Only the configured *value* changes; the *mechanism* does not.

## 16. Exact Azure runtime mutation authorized for R11-R3-I

Container App: `noetva-dev-eus2-backend`, resource group `rg-noetva-dev`.
Environment variable: `CTEC_OIDC_AUDIENCE`.
Old value: `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`.
New value: `3a880f13-985d-4a71-be05-20f97b9bcfa3`.
This is a plain (non-secret) template environment-variable change. The Container App is confirmed (`activeRevisionsMode: Single`, live read) to be in single-revision mode — this change will provision a new revision automatically, replacing the active one; this is standard, expected platform behavior for a template change, not a rebuild.

**Preserved, unmutated by this change:** backend image digest `sha256:3c7e46ac8751faaeb687a3c3bc11a85ff34a52ec9798375be9b2fa69e4a5f6bc` (confirmed live, unchanged); every other environment variable (`CTEC_ENVIRONMENT`, `CTEC_LOG_LEVEL`, `CTEC_CORS_ORIGINS`, `CTEC_OIDC_ISSUER`, `CTEC_OIDC_JWKS_URL`, `CTEC_OIDC_SCOPE_CLAIM`, `CTEC_OIDC_TENANT_CLAIM`, `CTEC_RUNTIME_HANDOFF_KEY_ID`); both Key Vault secret references (`ctec-database-url`, `ctec-runtime-handoff-key`); managed identity; networking; ingress; CORS; `minReplicas: 0`/`maxReplicas: 1` lifecycle; database configuration. No Entra mutation. No frontend change or redeploy. No image rebuild.

## 17. Exact repository artifact authorization for R11-R3-I

- **MODIFY** `infra/azure/modules/resources.bicep` — correct the `oidcAudience` parameter's `@description` from `'OIDC audience'` / `(API application ID URI)` framing to accurately state the v2.0 client-ID-GUID contract (comment/description only; the parameter name, type, and every consuming line are unchanged).
- **MODIFY** `infra/azure/environments/dev/main.parameters.json` — rename the `oidcAudience` placeholder text only (e.g. from `REPLACE_WITH_API_APPLICATION_ID_URI` to a name unambiguously describing the required bare client-ID-GUID form); the file carries no real secret or tenant-specific value today (confirmed: still template placeholder text on the open PR branch) and this remains true after the rename.
- **MODIFY** `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`, Step 21.3 — add the previously-missing instruction to also save the backend app's bare Application (client) ID GUID under its own named worksheet value, and state explicitly (citing this CDD and Microsoft's documented v2.0 `aud` contract) that this GUID, not the Application ID URI, is what feeds `CTEC_OIDC_AUDIENCE`/`oidcAudience`.

**Explicitly out of scope, deferred, not touched by R11-R3-I:** `infra/azure/environments/{demo,staging,prod}/main.parameters.json` carry the identical latent placeholder-text defect (confirmed, read-only) but are not yet deployed against any real Entra application in this program — correcting them is deferred to whichever future phase first deploys to those environments, consistent with this program's established narrow-fix precedent (CDD-074, CDD-075). No global runbook hardening is authorized here.

## 18. CREATE/MODIFY/DELETE ceiling

**This DRG phase (R11-R3-G):** CREATE = 1 (`docs/cdd/CDD-076-Azure-Entra-Real-Token-Audience-Correction.md`). MODIFY = 0. DELETE = 0.

**Authorized for the next phase (R11-R3-I), not exceeded here:** CREATE = 0. MODIFY = 3 (`infra/azure/modules/resources.bicep`, `infra/azure/environments/dev/main.parameters.json`, `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`). DELETE = 0. Plus exactly one live Azure Container App environment-variable mutation (§16). No other file, and no other Azure/Entra/database/Key Vault/Cloudflare/GitHub-settings mutation, is authorized.

## 19. Post-correction VM plan (frozen for R11-R3-I)

1. Apply the single authorized `CTEC_OIDC_AUDIENCE` env-var mutation (§16); confirm new revision `Healthy`; confirm backend image digest unchanged; confirm `/health` still real `200`.
2. Using the existing authenticated frontend session if the access token remains unexpired; otherwise a controlled, explicitly-flagged re-authentication (not assumed).
3. `GET /api/v1/oqi/findings` → expect the request to pass audience validation (no `AUTH_AUDIENCE_INVALID`) and proceed to scope authorization.
4. Expect `200` (or a truthful application-level result) for `oqi:read`.
5. Continue the three remaining paused protected-capability tests: `information-element-context:read`, `evidence-fitness:read`, `supply-chain-impact:evaluate`.
6. Confirm at least one authenticated call reaches the real PostgreSQL-backed path (not merely the token-validation boundary).
7. Negative security tests: confirm a token whose `aud` is deliberately wrong (e.g., the *old* misconfigured value, or an unrelated audience) is still rejected with `AUTH_AUDIENCE_INVALID` — fail-closed behavior must be demonstrated as preserved, not merely assumed.

## 20. Wrong-audience negative preservation

The corrected configuration must continue to reject any token whose `aud` does not exactly equal `3a880f13-985d-4a71-be05-20f97b9bcfa3` — including, notably, a token that (hypothetically) carried the old `api://3a880f13-985d-4a71-be05-20f97b9bcfa3` form. This is required verification content for R11-R3-I's VM, not merely a passive expectation.

## 21. R11-R2 disposition

R11-R2-I-VM's own scope (creating and verifying the replacement CIAM local account) is confirmed successful and is not reopened by this artifact. However, R11-R2-I-VM's full authenticated-backend verification sequence cannot reach PASS, because this independent, later-stage audience defect blocks every protected-capability test. **R11-R2-I-VM formally remains OPEN, pending R11-R3-I's correction and the completion of the post-correction VM plan in §19** — its history is not rewritten; its local-account implementation work stands as complete and correct.

## 22. STOP conditions — evaluated

Real token `aud` was safely established (§3) — not triggered. Live backend expected audience was established via read-only Azure query (§4) — not triggered. Microsoft documentation was unambiguous and directly on point (§7) — no material conflict, not triggered. The selected correction does not weaken audience validation in any way (§15) — not triggered. No governed reason arose to accept multiple audiences (§13, Option B rejected) — not triggered. No Entra application mutation is required by this correction — not triggered. The authorized source correction (§17) is strictly narrower than or equal to the defect's own footprint (three text/placeholder edits, zero logic changes) — not triggered. No additional independent authentication defect was discovered beyond this single audience mismatch — not triggered.

**No STOP condition is triggered. This governance artifact is authorized to freeze.**
