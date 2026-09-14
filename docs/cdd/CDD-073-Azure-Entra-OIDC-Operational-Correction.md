# CDD-073 — Azure Entra OIDC Operational Correction

**Status:** FROZEN
**Originating phase:** AZURE-ENTRA-OIDC-OPERATIONAL-R11 (DRG only in this artifact)
**Amends:** nothing frozen in place. Complements CDD-063/064/065/066 (mechanism/scope design, unchanged) and CDD-067–072 (Azure infrastructure/database, closed per §1). Does not reopen any of them. Resolves the final operational gap between the already-designed OIDC architecture and the now-healthy, database-complete Azure DEV environment.

**Scope:** Entra External ID app-registration read-back, SPA redirect/logout URI configuration, the noetva_tenant_id claims-mapping-policy (found genuinely absent, not merely unverified), a Pass-2 frontend rebuild, an application-tier CORS/image redeploy, and the real authenticated verification sequence. No database, no Bicep-module redesign, no new Key Vault secret.

---

## 1. Database foundation — closed boundary, reaffirmed

Re-confirmed unchanged, not reopened: PostgreSQL `Ready`/`Disabled`; canonical DSN `postgresql+psycopg://`, psycopg v3; migration execution #4 (`noetva-dev-eus2-migrate-93xhj1t`) `Succeeded`; Alembic head `0046_oqi5_remediation_tenancy`; both seeders succeeded; backend `DB_HEALTHY: True` as `noetva_app` (`CAN_CREATE_SCHEMA_OBJECTS: False`); `backendMinReplicas` restored to `0`; backend/frontend `/health` both `200`.

## 2. Authoritative baseline

Main SHA `09acfeb77a258ff8a83a48a8fc4105279456f50a` — matches. PRs #213–#223 all re-derived live — OPEN, `mergedAt: null`. R9 introduced the last source change (`3444d35989c37eee3f57e6b98e65b3103284159b`); R10 introduced zero. CDD-063 (`9849e1ee135eede9fdba9bfa10fdd4cf0b8c5fd2dec3d9ec223d778cb2d0ca7c`), CDD-065 (`0ebd2dd032a174267e9954a4a2aa5a109351475317a427e7e30b1d605807c2a0`), CDD-066 (`80e78f3b799a67c42b86773a1713dae5cae033829ae13793d5fc80159aa8a49a`), CDD-067–072 — all re-hashed from `origin/main`/their exact commits — byte-identical.

## 3. Tenant-bootstrap reclassification (traced to source, not assumed)

`noetva-dev-tenant` is not a row in a dedicated tenant table. The backend's authentication layer (`backend/app/api/supplier_risk/authentication.py`) extracts the tenant identity **directly from the validated access token's `noetva_tenant_id` claim** (`tenant = claims.get(settings.oidc_tenant_claim)`) and fails closed (`AUTH_TENANT_MISSING_OR_AMBIGUOUS`) if it is missing or empty — there is no lookup against a stored tenant registry anywhere in this path. **Truthful establishment criterion:** `noetva-dev-tenant` is "operationally established" the moment a real, validated access token carrying `noetva_tenant_id: "noetva-dev-tenant"` is accepted by the backend and used to scope a real request/row — there is no separate creation step, and none is invented here (matching R10's own conclusion that no dedicated seeder exists, now fully explained).

## 4. Two/three tenant concepts, kept distinct (reaffirmed)

Entra External tenant `8f9e2dee-5a5b-4b33-9044-4d11691899de`, workforce/subscription tenant `f111b68a-49a0-4fca-b249-cb774d866c18`, and the Noetva business tenant `noetva-dev-tenant` (a bare string claim value) are three structurally distinct identifiers, confirmed never conflated anywhere in source (`backend/app/api/supplier_risk/authentication.py` reads `tid` nowhere as a business-tenant source).

## 5. Frontend app registration (live, read-only, re-derived)

`noetva-dev-frontend`, object `ed5926b9-13c3-4f0c-84bc-cec512c7a814`, appId `ee9c1b49-9a28-4293-a312-83743abee1f5`, tenant `8f9e2dee-...` — all confirmed. `signInAudience: AzureADMyOrg`. `isFallbackPublicClient`: unset (`null`) — correct, not mutated. `spa.redirectUris: []`, `web.redirectUris: []`, `publicClient.redirectUris: []` — **all currently empty**, confirming no redirect URI is configured yet (expected — this is R11-I's work). `web.implicitGrantSettings`: both `enableAccessTokenIssuance`/`enableIdTokenIssuance` **false** — implicit flow correctly disabled. No client secret exists on a SPA/public-client registration of this kind (public clients don't hold secrets). `requiredResourceAccess` declares all 11 backend delegated scopes plus Graph `User.Read` (`e1fe6dd8-ba31-4d61-89e7-88639da4683d`) — matches expected exactly.

## 6. Backend app registration (live, read-only, re-derived)

`noetva-dev-backend-api`, object `1cbed9d5-bd79-4e68-b73c-d9eb5ddaa58c`, appId `3a880f13-985d-4a71-be05-20f97b9bcfa3`, `identifierUris: ["api://3a880f13-985d-4a71-be05-20f97b9bcfa3"]` — matches. `api.acceptMappedClaims: True` — **already set**, no mutation needed. `api.requestedAccessTokenVersion: 2`. `api.preAuthorizedApplications: []` — empty (see §17).

## 7. Real Azure FQDNs (freshly re-derived, not assumed)

Backend: `noetva-dev-eus2-backend.politeglacier-6315242f.eastus2.azurecontainerapps.io`. Frontend: `noetva-dev-eus2-frontend.politeglacier-6315242f.eastus2.azurecontainerapps.io`. Both re-read live from the Container Apps ingress configuration, matching the previously reported values exactly.

## 8. Exact SPA redirect URI (traced to source, not assumed)

`frontend/lib/auth/browser-session.ts` constructs `new UserManager({ redirect_uri: config.redirectUri, ... })`; the route that consumes the resulting callback is `frontend/app/auth/callback/page.tsx` (Next.js App Router file-based routing → `/auth/callback`, no trailing slash, no case variants). **Frozen exact value:**

```
https://noetva-dev-eus2-frontend.politeglacier-6315242f.eastus2.azurecontainerapps.io/auth/callback
```

## 9. Exact post-logout URI (traced to source, not assumed)

The same `UserManager` construction sets `post_logout_redirect_uri: config.postLogoutRedirectUri`, sourced verbatim from `NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI` with no path suffix (the deployment guide's own Part 27 example already uses the bare origin). **Frozen exact value:**

```
https://noetva-dev-eus2-frontend.politeglacier-6315242f.eastus2.azurecontainerapps.io
```

## 10. Frontend OIDC build/runtime contract (fully classified)

| Value | Classification | Source |
|---|---|---|
| `NEXT_PUBLIC_OIDC_AUTHORITY` | BUILD-TIME, CLIENT-EXPOSED | Dockerfile `ARG`/`ENV`, inlined by Next.js at `next build` |
| `NEXT_PUBLIC_OIDC_CLIENT_ID` | BUILD-TIME, CLIENT-EXPOSED | same |
| `NEXT_PUBLIC_OIDC_REDIRECT_URI` | BUILD-TIME, CLIENT-EXPOSED | same |
| `NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI` | BUILD-TIME, CLIENT-EXPOSED | same |
| `NEXT_PUBLIC_CTEC_API_ORIGIN` | BUILD-TIME, CLIENT-EXPOSED | same |
| `NEXT_PUBLIC_OIDC_SCOPE` | BUILD-TIME, CLIENT-EXPOSED (has an in-source default, §14) | same |

**None of these are RUNTIME or SERVER-ONLY** — `frontend/app/health/route.ts` aside (which reads nothing), the frontend Container App's own `envVars` array is `[]` (confirmed live and in `resources.bicep`) — there is no server-side environment variable mechanism for these values at all. **Container App environment variables cannot change a value Next.js has already inlined at build time** — this is a hard constraint, not a design choice to reconsider.

## 11. Pass-2 frontend rebuild decision: REQUIRED

The currently deployed frontend image (`sha256:0d82d2ad...`, built in R8-I as the governed Pass-1 image) was built with `NEXT_PUBLIC_OIDC_REDIRECT_URI`, `NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI`, and `NEXT_PUBLIC_CTEC_API_ORIGIN` all at their Dockerfile empty-string/localhost defaults. `frontend/lib/auth/config.ts`'s own `browserAuthConfig()` throws `"Browser authentication configuration is incomplete"` whenever any of `authority`/`clientId`/`redirectUri`/`postLogoutRedirectUri`/`apiOrigin` is falsy — **the current image cannot perform real sign-in or real API calls**; it is definitively insufficient for this phase's objective. A Pass-2 rebuild is required.

## 12. Exact Pass-2 build inputs (frozen)

```
NEXT_PUBLIC_OIDC_AUTHORITY=https://8f9e2dee-5a5b-4b33-9044-4d11691899de.ciamlogin.com/8f9e2dee-5a5b-4b33-9044-4d11691899de/v2.0
NEXT_PUBLIC_OIDC_CLIENT_ID=ee9c1b49-9a28-4293-a312-83743abee1f5
NEXT_PUBLIC_OIDC_REDIRECT_URI=https://noetva-dev-eus2-frontend.politeglacier-6315242f.eastus2.azurecontainerapps.io/auth/callback
NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI=https://noetva-dev-eus2-frontend.politeglacier-6315242f.eastus2.azurecontainerapps.io
NEXT_PUBLIC_CTEC_API_ORIGIN=https://noetva-dev-eus2-backend.politeglacier-6315242f.eastus2.azurecontainerapps.io
```

`NEXT_PUBLIC_OIDC_SCOPE` is left unset, exactly as in Pass 1 — `config.ts`'s own in-source default (§14) already matches CDD-066's governed contract; not re-typed, to avoid a transcription risk. Build target: `linux/amd64` (explicit, via `docker buildx build --platform linux/amd64`, the same mechanism already proven in every prior image build this arc). Push to `noetvadeveus2acr`, resolve the immutable manifest-list digest, independently verify its child manifest is `Architecture: amd64, Os: linux` via `az acr manifest list-metadata` before use. Backend image is **not** rebuilt — no backend source or dependency changed.

## 13. OIDC authority / discovery (live-verified)

`GET https://8f9e2dee-5a5b-4b33-9044-4d11691899de.ciamlogin.com/8f9e2dee-5a5b-4b33-9044-4d11691899de/v2.0/.well-known/openid-configuration` returns a real, working document: `issuer` matches the already-configured `oidcIssuer`; `jwks_uri` matches the already-configured `oidcJwksUrl`; `authorization_endpoint`/`token_endpoint`/`end_session_endpoint` all resolve under the same tenant-level path. **No user-flow/policy-specific authority suffix is required** — Entra External ID (CIAM), unlike classic B2C, associates the user flow with the *application* (§16), not with a policy-suffixed authority URL; the plain tenant authority is sufficient and is what the frontend/backend already use.

## 14. Frontend runtime 10-scope contract (re-derived from source, unchanged)

`frontend/lib/auth/config.ts`'s in-source default: `"openid profile supplier-risk:read entity-resolution:read ontology-copilot:ask ontology-modeling:read oqi-remediation:authorize oqi-remediation:report-execution oqi:read information-element-context:read evidence-fitness:read supply-chain-impact:evaluate"`. Classified: `openid`/`profile` are standard OIDC scopes (not among, and not counted in, the 10 backend capability scopes); the remaining 10 are exactly CDD-066's governed set, including all four of `oqi:read`/`information-element-context:read`/`evidence-fitness:read`/`supply-chain-impact:evaluate`, excluding `supply-chain-impact:read` and the retired `information-element-evidence-fitness:read`. `offline_access` and `User.Read` are **not** present in this runtime request string (the app registration's `requiredResourceAccess`, §5, is a separate, broader design-time declaration — not what's requested at sign-in). Unchanged by this artifact.

## 15. Backend's 11 exposed scopes and frontend permission state (live-verified)

All 11 scopes on `noetva-dev-backend-api`'s `oauth2PermissionScopes` confirmed `isEnabled: true`, `type: "Admin"` (admin-consent-required): `supplier-risk:read`, `entity-resolution:read`, `ontology-copilot:ask`, `ontology-modeling:read`, `oqi-remediation:authorize`, `oqi-remediation:report-execution`, `oqi:read`, `information-element-context:read`, `supply-chain-impact:read`, `supply-chain-impact:evaluate`, `evidence-fitness:read`. A real, existing `oauth2PermissionGrant` (`consentType: AllPrincipals`, tenant-wide) already covers the frontend service principal (`41a636b7-ce58-4069-96da-f4a4948fc9ae`) for **all 11** of these scopes plus Graph `User.Read` — confirmed live, not assumed. This is distinct from, and already broader than, the 10-scope runtime request (§14) — the grant existing is what allows the frontend to actually request a subset of these scopes without a fresh consent prompt.

## 16. User flow (live-verified)

`noetva-dev-signup-signin` (id `f93c2f3b-412a-49db-b9d0-43dcc665f567`), type `externalUsersSelfServiceSignUpEventsFlow`, `conditions.applications.includeApplications` = `[{appId: "ee9c1b49-..."}]` (the frontend) — confirmed associated. `onAuthenticationMethodLoadStart.identityProviders` = `[{id: "EmailPassword-OAUTH", displayName: "Email with password"}]` — matches. `isSignUpAllowed: true`.

## 17. Signup tenant-safety (proven, not assumed)

The user flow's `onAttributeCollection.attributeCollectionPage` and its `attributes` array contain **exactly four** entries: `email`, `displayName`, `givenName`, `surname` — no `tenant_id`/`noetva_tenant_id` attribute is defined in this user flow at all. A public self-service sign-up **cannot** collect or self-assert a business tenant value — the attribute doesn't exist in the flow's schema, not merely "hidden" or "not required."

## 18. DEV test user (live-verified)

`dev-test@noetvaexternal.onmicrosoft.com`, display name "Noetva DEV Test User", object `c1d19303-0b45-4db9-b7d6-9ecaa0e41297` — confirmed. Real, live-read value of `extension_4795a02ed0cc42929fe9a98d42d08300_tenant_id`: `"noetva-dev-tenant"` — confirmed present and correct, read via Graph, not printed as part of any broader dump.

## 19. Directory tenant attribute (live-verified, full provenance traced)

The extension property genuinely exists: `name: "extension_4795a02ed0cc42929fe9a98d42d08300_tenant_id"`, `dataType: String`, `targetObjects: ["User"]`, registered against application `2df03fbc-e98a-420a-b1bd-5c923c74c609` (`appId` `4795a02e-d0cc-4292-9fe9-a98d42d08300`, display name **"b2c-extensions-app. Do not modify. Used by AADB2C for storing user data."**) — confirmed by deriving that appId directly from the extension name's embedded prefix and independently reading the app object and its `extensionProperties`, never guessed.

## 20. Existing outgoing claim-mapping state: **NOT PRESENT — real, material finding, contrary to assumption**

Three independent Graph checks — `GET /policies/claimsMappingPolicies` (tenant-wide, all `claimsMappingPolicy` objects), `GET /servicePrincipals/{backend-sp}/claimsMappingPolicies` (policies assigned to the backend's own Enterprise Application), and `GET /applications/{backend-app}?$select=optionalClaims` (both v1.0 and beta) — **all return empty/null**. **No claims-mapping-policy currently exists anywhere in this tenant.** This contradicts the assumption (carried from CDD-064/065's own text, which itself explicitly disclosed the empirical proof was still pending as of those artifacts' freeze) that this was "existing" and merely needed re-verification. CDD-064/065's **mechanism design is not reopened or changed** — the correct, governed mechanism (an Attributes & Claims-equivalent `claimsMappingPolicy` on the backend's service principal, `ExtensionID` = `extension_4795a02ed0cc42929fe9a98d42d08300_tenant_id`, `JWTClaimType` = `noetva_tenant_id`) remains exactly as CDD-064/065 froze it — it simply does not yet exist as a live object and must be created by R11-I.

## 21. `acceptMappedClaims` current/required state

Already `true` on the backend application object (§6) — **no mutation required for this specific flag.** Per Microsoft Learn (already cited in CDD-064 and re-confirmed here), this is required precisely because the backend is single-tenant (`signInAudience: AzureADMyOrg`, confirmed) with an application-GUID-form Application ID URI (`api://3a880f13-...`, confirmed) — exactly the case that avoids `AADSTS501461` without a custom signing key.

## 22. Custom signing key: NOT required

Investigated directly, not ignored: the "custom signing key" requirement Microsoft's portal warns about applies when a resource application is **multi-tenant** or when its Application ID URI is **not** in application-GUID or verified-domain form. `noetva-dev-backend-api` is `AzureADMyOrg` (single-tenant) with an application-GUID-form URI — the exact combination CDD-064's own cited Microsoft Learn guidance identifies as **not** requiring a custom signing key. No signing key is created or required by this artifact.

## 23. Authorized Client Applications: NOT required

`preAuthorizedApplications` is empty (§6), but a real, tenant-wide `AllPrincipals` `oauth2PermissionGrant` already covers the frontend for all 11 backend scopes plus `User.Read` (§15) — the practical effect `preAuthorizedApplications` would otherwise provide (skipping a consent prompt) is already achieved through the existing grant. Adding the frontend to `preAuthorizedApplications` would be redundant, not required, and is **not authorized** by this artifact.

## 24. Backend runtime OIDC contract (traced to source, unchanged)

`backend/app/api/supplier_risk/authentication.py`: `jwt.decode(token, ..., audience=settings.oidc_audience, issuer=settings.oidc_issuer)` — PyJWT enforces exact `aud`/`iss` match, raising `AUTH_AUDIENCE_INVALID`/`AUTH_ISSUER_INVALID` on mismatch. `tenant = claims.get(settings.oidc_tenant_claim)` with `oidc_tenant_claim` deployed as `noetva_tenant_id` — raises `AUTH_TENANT_MISSING_OR_AMBIGUOUS` if absent/blank (no fallback, no default acceptance of `tenant_id`). `scopes = _claim_values(claims.get(settings.oidc_scope_claim))` with `oidc_scope_claim` deployed as `scp` — no legacy `scope` claim is consulted in Azure. Subject: `AUTH_PRINCIPAL_MISSING` if absent/blank.

## 25. Real access-token contract (frozen)

A successful DEV-user access token must carry: `aud = api://3a880f13-985d-4a71-be05-20f97b9bcfa3`; `scp` containing (space-delimited) at least the scopes requested at sign-in (a subset of the 10, §14); `noetva_tenant_id = "noetva-dev-tenant"`; `tid = 8f9e2dee-5a5b-4b33-9044-4d11691899de` (confirmed, per source in §24, never consulted as the business tenant); plus the standard `iss`, `sub`/`oid`, `exp`, `iat`/`nbf` claims, useful for validation but not separately gating. No legacy `scope` claim is required or consulted.

## 26. Protected API verification plan (frozen, endpoints from source, not invented)

Exercise, at minimum, the four capabilities CDD-066 corrected: `oqi:read`, `information-element-context:read`, `evidence-fitness:read`, `supply-chain-impact:evaluate` — via their real frontend-invoked backend routes (`frontend/lib/oqi/api-client.ts`, `frontend/lib/context/api-client.ts`, `frontend/lib/evidence-fitness/api-client.ts`, `frontend/lib/supply-chain-impact/api-client.ts`, already read in this arc), using a real token obtained via §27. Each call must succeed with the real token and be independently confirmed to fail (401/403) without it, per §28.

## 27. Real DEV-user login mechanism (frozen, not left ambiguous)

Authorization Code + PKCE is inherently an interactive, browser-mediated flow — it cannot be reduced to a single non-interactive CLI call. R11-I must obtain a real token by one of, in preference order: (a) a scripted browser automation (e.g., Playwright) driving the real `noetva-dev-signup-signin` flow end-to-end as the real DEV test user, capturing the resulting token via the SPA's own token store — the most faithful reproduction of a real user's path; (b) if the tenant/app registration is confirmed (at implementation time, not assumed here) to support a device-code or another Microsoft-documented non-interactive grant safe for a public client test account, use that instead. **ROPC (resource-owner password) is not selected or authorized here** — it is deprecated guidance for public-client/CIAM scenarios and was not confirmed enabled; R11-I must not silently fall back to it. If neither (a) nor (b) can be completed safely and non-interactively, R11-I must ask the operator to complete one manual interactive login and hand back the resulting token through a secret-safe mechanism (never pasted into a report or command history) — this is an honest deferral, not a guessed mechanism.

## 28. Fail-closed negative tests (frozen, source-level proven; real-provider proof separately required)

**Source-level (already provable from `backend/app/api/supplier_risk/authentication.py`, likely already covered by `backend/app/tests/test_oidc_authentication.py`):** missing/invalid issuer → `AUTH_ISSUER_INVALID`; wrong audience → `AUTH_AUDIENCE_INVALID`; missing/blank tenant claim → `AUTH_TENANT_MISSING_OR_AMBIGUOUS`; missing/blank subject → `AUTH_PRINCIPAL_MISSING`; any other malformed/unverifiable token → `AUTH_TOKEN_UNVERIFIABLE`. **Real-provider proof (R11-I/VM):** (1) call a protected route with no `Authorization` header → expect `401`; (2) call with a real token lacking a required scope → expect `403`; (3) present the real token to a route requiring a *different* audience, if one exists, or synthesize the negative case from the source-level proof if no such route exists — do not weaken or reconfigure any real setting merely to manufacture a negative token. These two levels are tracked and reported distinctly, never conflated.

## 29. Token confidentiality (frozen handling rules)

Never print, log, commit, or include a complete access token (header/payload/signature) in any command output, report, or file. Decode claims only via a local, ephemeral, secret-safe tool invocation (e.g., a short Python snippet run and discarded, never writing the token to a file that persists); report only claim **names and their expected-safe values** (e.g., `tid` value, `noetva_tenant_id` value, presence/absence of a scope) — never the raw token string, never the signature. Treat the access token exactly as any other credential handled elsewhere in this arc.

## 30. Entra/Azure tenant-context discipline (frozen, operational)

Entra External ID discovery/configuration operates against tenant `8f9e2dee-5a5b-4b33-9044-4d11691899de` (`az account get-access-token --tenant 8f9e2dee-... --resource https://graph.microsoft.com`, or an equivalent explicit-tenant Graph call) — confirmed this session requires interactive MFA the first time; the operator completed this once, out of band. Every Azure resource-affecting operation (Bicep deploy, ACR push, Container App/Job read or mutation) **must** run against subscription `2aca2d95-0ac5-4dd6-b081-3822ee294a70` / workforce tenant `f111b68a-...` — re-confirmed via `az account show` immediately before this artifact's own Azure-adjacent actions, and required identically before every R11-I Azure step. Never rely on implicit context.

## 31. Exact configuration/verification order (frozen, corrected from the candidate sequence)

1. Build the Pass-2 frontend image (§12); push; resolve/verify digest.
2. Configure the SPA redirect URI (§8) and logout URL (§9) on the frontend application object (Graph `PATCH`, since this session has no portal/browser access — functionally identical to the portal action).
3. Create the `noetva_tenant_id` claims-mapping-policy (§20) and assign it to the backend's service principal (Graph `POST /policies/claimsMappingPolicies` + assign — a documented, technically-equivalent alternative to the portal UI, necessary given no browser access; not a reopening of CDD-064/065's mechanism design).
4. Application-tier redeploy: new frontend digest, `corsOrigins` updated to include the real frontend origin (currently `[]` — §12's rebuilt frontend needs the backend to actually accept its cross-origin calls) — `what-if` first.
5. Verify frontend/backend health post-redeploy (both `/health` → `200`).
6. Obtain a real token via §27.
7. Verify token claims via §25 (secret-safe, §29).
8. Exercise protected APIs via §26.
9. Perform negative tests via §28.
10. Verify `noetva-dev-tenant` operational establishment per §3's criterion (the successful §8 calls **are** this proof — no separate step).

(User-flow association, frontend permissions, and Authorized-Client-Application status are already correct — §16/§15/§23 — verified, not reconfigured, and do not appear as separate steps above.)

## 32. Source-change requirement

**Zero.** Every item in this artifact is an Entra configuration action, an Azure image build/redeploy using already-existing, already-parameterized Bicep inputs (`frontendImageReference`, `corsOrigins` — both pre-existing parameters, no new one introduced), or a verification action. No Bicep module, application source, dependency, or documentation file requires modification.

## 33. Exact Entra mutation authorization (enumerated, not blanket)

R11-I **is** authorized to: set `spa.redirectUris` on the frontend application to exactly the URI in §8; set `web.logoutUrl` to exactly the URI in §9; create one `claimsMappingPolicy` (`ExtensionID` = `extension_4795a02ed0cc42929fe9a98d42d08300_tenant_id`, `JWTClaimType` = `noetva_tenant_id`, source `user`) and assign it to service principal `db9828d6-4020-4f4e-a086-fb75120e9b96`. R11-I is **not** authorized to: change `acceptMappedClaims` (already correct); create a custom signing key (§22, not required); add `preAuthorizedApplications` (§23, not required); modify the user flow, its attribute collection, or its identity provider (§16/§17, already correct); modify DEV-user attributes beyond what's already set (§18); modify API permissions, scopes, or consent (§15, already correct); modify `isFallbackPublicClient` or enable implicit grant.

## 34. Exact Azure mutation authorization

R11-I **is** authorized to: build and push exactly one new frontend image (§12), no backend rebuild; perform exactly one application-tier `what-if` + redeploy updating `frontendImageReference` and `corsOrigins` only (all other parameters unchanged from the last known-good deployment); perform read-only verification calls (health checks, `az containerapp exec`-based or HTTP-based protected-API exercises). R11-I is **not** authorized to: create any new Key Vault secret/version; change any DSN; modify `backendMinReplicas` beyond a bounded, restored verification window if one proves necessary (mirroring CDD-072's own pattern) — and if used, it must be restored to `0` and confirmed, exactly as before; touch Cloudflare/DNS; touch GitHub settings; merge any PR; delete any Azure resource.

## 35. Database/lifecycle preservation

No migration, schema change, database role change, DSN change, or Key Vault database-secret change. `backendMinReplicas` returns to `0` at the end of R11-I exactly as it did at the end of R10.

## 36. Real OIDC VM standard (frozen, restated precisely)

PASS requires the complete real chain: a real DEV-user login via §27's mechanism → Authorization Code + PKCE → a real access token satisfying §25 exactly → backend acceptance (via §24's real validation code, not a stub) → all four §26 capabilities succeeding → the two-tier §28 negative proof → confirmation that tenant isolation (already enforced at the database level by the very Alembic migrations that just ran, §1) is not bypassed. Portal/API settings *looking* correct is explicitly insufficient.

## 37. STOP conditions (all evaluated during this DRG; none triggered)

- The redirect URI **was** derived exactly, from source (§8) — not triggered.
- The frontend build contract is **not** ambiguous — fully classified (§10) — not triggered.
- The claim mapping does **not** require unsupported/insecure configuration — the governed mechanism (§20) is unchanged, standard, and Microsoft-documented — not triggered.
- The custom-signing-key question **was** resolved safely: not required (§22) — not triggered.
- Public signup **cannot** self-assert the business tenant — proven structurally absent from the flow schema (§17) — not triggered.
- The frontend does **not** require a client secret (public client/SPA, confirmed, §5) — not triggered.
- Implicit grant is **not** required — confirmed disabled and not reopened (§5) — not triggered.
- `isFallbackPublicClient=true` does **not** appear necessary — confirmed unset, unchanged (§5/§33) — not triggered.
- The backend requires `scp`, **never** legacy `scope`, confirmed from source (§24) — not triggered.
- The tenant claim **can** be emitted safely via the unchanged, governed mechanism (§20/§33) — not triggered.
- The business tenant is **not** conflated with Entra `tid` anywhere in source (§4/§24) — not triggered.
- The exact 10-scope request **is** preserved unchanged (§14) — not triggered.
- Protected-endpoint mapping is **not** ambiguous — real routes identified from source (§26) — not triggered.
- Real token verification does **not** require weakening authorization anywhere (§28's real-provider tests are additive, not configuration changes) — not triggered.
- Database/security architecture does **not** need reopening (§1, closed) — not triggered.
- Source changes **are** bounded — zero (§32) — not triggered.

No STOP condition fired. This correction is safe to freeze and hand to an implementation phase.

---

**Freeze evidence index:** every Entra fact in this artifact (app registrations, service principals, claims-mapping-policy absence, extension property, DEV user, user flow, discovery endpoint) was independently read live via Microsoft Graph against tenant `8f9e2dee-5a5b-4b33-9044-4d11691899de` (interactive MFA completed by the operator for this session), never assumed from a prior artifact's text alone. Every frontend/backend source claim was independently re-read from the real repository files this session. No secret or token value was printed at any point.
