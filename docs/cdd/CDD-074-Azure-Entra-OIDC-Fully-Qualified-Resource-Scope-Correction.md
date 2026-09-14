# CDD-074 — Azure Entra OIDC Fully-Qualified Resource-Scope Correction

**Status:** FROZEN
**Originating phase:** AZURE-ENTRA-OIDC-R11-R1 (DRG only in this artifact)
**Amends:** nothing frozen in place. Complements CDD-063/065/066 (scope-contract design, unchanged) and CDD-073 (Entra operational correction, unchanged — its redirect URI, claims-mapping policy, `acceptMappedClaims`, and Pass-2 build inputs all remain exactly as implemented and verified). Resolves a new, real, Azure-Entra-only authentication defect discovered during CDD-073's own first real login attempt.

**Scope:** the frontend's OIDC scope-string construction (`frontend/lib/auth/config.ts`), its build-time wiring (`frontend/Dockerfile`, `docker-compose.yml`), its test coverage, and one deployment-guide/static-check correction. No Entra mutation, no Azure infrastructure mutation, no backend change, no database change.

---

## 1. Real failure evidence (independently reproduced this DRG)

Fresh, read-only query of Entra's own `auditLogs/signIns` (tenant `8f9e2dee-...`, explicit tenant context) reproduces the exact defect: the newest real sign-in attempt by `dev-test@noetvaexternal.onmicrosoft.com` via `noetva-dev-frontend` shows `errorCode: 650053`, `resourceId: 00000003-0000-0000-c000-000000000000` (the literal, well-known Microsoft Graph resource GUID), `failureReason` template *"The application '{name}' asked for scope '{scope}' that doesn't exist on the resource '{resource}'."* No authorization code was issued; the token endpoint was never reached. The earlier, separate `AADSTS50055` (password-expired) condition is confirmed fully resolved and absent from this and all more recent events — the two failures are distinct and not conflated.

## 2. Microsoft identity-platform contract (authoritative, fetched directly, not from memory)

Microsoft Learn, "Scopes and permissions in the Microsoft identity platform" (`scopes-oidc`), verbatim: *"In requests to the authorization, token or consent endpoints for the Microsoft identity platform, if the resource identifier is omitted in the scope parameter, the resource is assumed to be Microsoft Graph. For example, `scope=User.Read` is equivalent to `https://graph.microsoft.com/User.Read`."* Microsoft Learn, "Microsoft identity platform and OAuth 2.0 authorization code flow" (`v2-oauth2-auth-code-flow`), independently confirms every worked example in the entire document uses a fully qualified scope (`https://graph.microsoft.com/mail.read`, `api://contoso.com/api/UseResource`) — never a bare permission name — for exactly this reason.

## 3. Root cause, fully proven

`frontend/lib/auth/config.ts`'s in-source default scope string requests the ten Noetva backend capability scopes as **bare** values (`supplier-risk:read`, `oqi:read`, etc.), with no resource-URI prefix. Per §2, Entra therefore resolves every one of them against Microsoft Graph — which has no permission named `oqi:read` — producing `AADSTS650053` before any code/token is ever issued. This is the exact, sole cause; no other configuration is implicated (redirect URI, claims-mapping policy, `acceptMappedClaims`, DEV-user tenant attribute, and deployed Pass-2 digest were all independently re-verified unchanged and correct during this DRG's investigation).

## 4. Local Keycloak behavior (unaffected, must remain so)

`keycloak/ctec-realm.json` defines these same ten capabilities as bare client-scope names (`"name": "supplier-risk:read"`, `"name": "oqi:read"`, etc.) — Keycloak has no equivalent resource-prefix requirement and already works correctly with bare names today. Any correction must not alter this local contract or its existing, passing tests.

## 5. Backend App ID URI and exposed scopes (live-verified)

`noetva-dev-backend-api`, `identifierUris: ["api://3a880f13-985d-4a71-be05-20f97b9bcfa3"]` — confirmed live. All 11 `oauth2PermissionScopes` confirmed `isEnabled: true`, `type: Admin`, values unchanged from CDD-073's read-back. Per Microsoft's own convention (§2's `.default` section, and every worked example), the fully-qualified wire-format identifier for each is `api://3a880f13-985d-4a71-be05-20f97b9bcfa3/<scope-value>` — e.g. `api://3a880f13-985d-4a71-be05-20f97b9bcfa3/oqi:read`.

## 6. Frontend permissions/consent impact: NONE

`noetva-dev-frontend`'s `requiredResourceAccess` (design-time permission declaration) and the existing tenant-wide `AllPrincipals` `oauth2PermissionGrant` (covering all 11 scopes + Graph `User.Read`) are both keyed by permission **ID** (a GUID), not by wire-format scope string — confirmed live, re-read, unchanged. Qualifying the *runtime request string* does not touch either object; no permission or consent mutation is required or authorized by this artifact. (Separately corroborated: Microsoft's own "Preauthorization" guidance notes customer-facing External ID apps typically need it precisely so users outside the org aren't blocked by a consent prompt — the existing `AllPrincipals` grant already serves this exact purpose here, unaffected.)

## 7. Expected access-token `scp` behavior — critical compatibility boundary, proven

Microsoft's own sample/tutorial guidance for validating a custom API's tokens checks the `scp` claim for the **bare scope value** (e.g. `access_as_user`), never the full `api://.../` string — the resource qualifier is carried by the token's `aud` claim, not repeated inside `scp`. This is independently confirmed against this repository's own backend: every real authorization call site (`backend/app/api/oqi/router.py:186` — `authorize(authenticated, "oqi:read", ...)`; `backend/app/api/supplier_risk/router.py` — `_authorize(authenticated, "supplier-risk:read", ...)`; `backend/app/api/supplier_risk/security.py:13` — `if scope not in principal.scopes`; and identical patterns in `information_element_context`, `information_element_evidence_fitness`, `supply_chain_impact`, `gate_s`, `gate_v`, `ontology_modeling`) compares against the **bare** scope name, with zero exceptions found across the codebase. **The backend's authorization contract already expects exactly what Entra will actually deliver** — requesting a fully-qualified scope changes nothing about what ends up in `scp`.

## 8. Backend change requirement: NONE

Proven, not assumed, by §7's exhaustive source trace: `CTEC_OIDC_SCOPE_CLAIM=scp` remains correct and unchanged; every scope-comparison call site already expects bare values. No backend source, dependency, or Azure runtime configuration change is required or authorized.

## 9. Tenant-claim and claims-policy preservation

Out of scope, untouched, and re-confirmed live and unchanged during this DRG: `NoetvaTenantClaimMapping` remains exactly one policy, still assigned to the backend service principal, definition unchanged; `acceptMappedClaims: True` unchanged; DEV user's `extension_...tenant_id` value `"noetva-dev-tenant"` unchanged. This correction is scope-wire-format only and does not interact with tenant-claim mapping in any way.

## 10. Architecture options evaluated

- **Option A — provider-specific scope qualification hardcoded in application logic (e.g. detect Entra by authority-string pattern-matching):** rejected — fragile (string-sniffing a URL to infer provider identity), untruthful (the code shouldn't need to "guess" which provider it's talking to), and harder to test than an explicit configuration value.
- **Option B — a single new build-time resource-identifier value that the existing scope-construction logic uses to qualify only the ten capability scopes, leaving `openid`/`profile` untouched:** **SELECTED.**
- **Option C — a fully pre-assembled build-time scope string supplied by environment (reusing the existing `NEXT_PUBLIC_OIDC_SCOPE` override verbatim, with the Azure guide simply typing out all ten pre-qualified scopes):** rejected as the *sole* mechanism — it would require manually duplicating the ten-name list a second time (in the deployment guide/CI), exactly the drift risk this DRG was explicitly told to avoid; `NEXT_PUBLIC_OIDC_SCOPE` itself remains fully available as an escape hatch, untouched, for any future operator who genuinely needs to override the whole string.
- **Option D — another smaller architecture:** none found smaller than B while satisfying single-source-of-truth.

## 11. Selected architecture (Option B, precise)

Introduce exactly one new, optional, client-exposed build-time value: **`NEXT_PUBLIC_OIDC_API_RESOURCE_URI`** — the backend's own Application ID URI (`api://3a880f13-985d-4a71-be05-20f97b9bcfa3`, itself public, non-secret configuration, not a credential). `frontend/lib/auth/config.ts` is refactored to hold the ten backend capability-scope names as a single canonical list (unchanged names/order/membership from the current literal), and to construct the default scope string as `openid profile` + each capability name **prefixed with `${NEXT_PUBLIC_OIDC_API_RESOURCE_URI}/`** *only if that value is set*, else left bare exactly as today. `NEXT_PUBLIC_OIDC_SCOPE`'s existing full-override behavior is entirely unchanged and untouched by this refactor.

## 12. Fail-closed configuration semantics

`NEXT_PUBLIC_OIDC_API_RESOURCE_URI` is **optional locally** (unset in `docker-compose.yml`/CI, preserving the exact current bare-scope Keycloak behavior byte-for-byte) and **required operationally for every real Azure/Entra build** — enforced not by a runtime application-level throw (there is no reliable way for client code to know at build time whether "unset" means "correctly local" or "mistakenly omitted for Azure"; forcing a hard runtime error would risk breaking the already-working local/test path) but by an explicit, real-Azure-verified static check (§17) mirroring CDD-071's own precedent, plus the deployment guide's own corrected instructions. Its absence for a real Azure build reproduces exactly this DRG's own diagnosed, loud, non-silent failure (`AADSTS650053`, no code issued) — never a silent fallback to Microsoft Graph being accepted by the backend (the backend's own `aud` check would independently reject a Graph-audience token outright, per CDD-073 §24's unchanged validation code). No secret of any kind is placed in this configuration value.

## 13. Standard OIDC scopes, kept separate

`openid` and `profile` are never prefixed — confirmed Microsoft's OIDC scopes are inherently provider-hosted, not resource-specific, and prefixing them would be both incorrect and unnecessary. `offline_access` is confirmed **not** currently requested anywhere in the frontend's scope string (absent from the existing literal) and is not introduced by this artifact. Graph `User.Read` is confirmed **not** requested at runtime either (absent from the scope string; its presence in `requiredResourceAccess`, §6, is a separate design-time declaration, not a runtime request) — not added by this artifact.

## 14. Exact ten-scope semantic contract (preserved, re-verified unchanged)

`supplier-risk:read`, `entity-resolution:read`, `ontology-copilot:ask`, `ontology-modeling:read`, `oqi-remediation:authorize`, `oqi-remediation:report-execution`, `oqi:read`, `information-element-context:read`, `evidence-fitness:read`, `supply-chain-impact:evaluate`. `supply-chain-impact:read` remains excluded (no live frontend caller — unchanged finding). The retired `information-element-evidence-fitness:read` remains absent. This artifact changes **only** the wire-format each is transmitted in for Entra; the set itself is untouched.

## 15. Exact source path authorization (ceiling)

| # | Path | Change | Reason |
|---|---|---|---|
| 1 | `frontend/lib/auth/config.ts` | MODIFY | Refactor to a single canonical capability-scope list; add resource-URI-conditional qualification; `NEXT_PUBLIC_OIDC_SCOPE` override behavior unchanged |
| 2 | `frontend/Dockerfile` | MODIFY | Add `ARG`/`ENV NEXT_PUBLIC_OIDC_API_RESOURCE_URI=""`, matching the exact existing pattern for every sibling `NEXT_PUBLIC_OIDC_*` value |
| 3 | `docker-compose.yml` | MODIFY | Add the matching optional passthrough entry (`${NEXT_PUBLIC_OIDC_API_RESOURCE_URI:-}`), consistent with every sibling entry; remains unset for local/CI |
| 4 | `frontend/tests/browser-session.test.ts` | MODIFY | Add tests proving: (a) unset value preserves today's exact bare-scope default byte-for-byte (regression guard for Keycloak), (b) a set value qualifies exactly the ten capability scopes and leaves `openid`/`profile` bare, (c) `NEXT_PUBLIC_OIDC_SCOPE`'s override still short-circuits both paths unchanged |
| 5 | `infra/azure/validation/static_architecture_checks.py` | MODIFY | Add one structural regression check (mirroring the CDD-071 precedent) asserting the deployment guide's frontend build example includes `NEXT_PUBLIC_OIDC_API_RESOURCE_URI` set to the real, governed backend App ID URI |
| 6 | `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` | MODIFY | Correct Part 27's frontend build example to include the new build arg with its real value and a short explanation of why it's required for Azure/Entra but not local Keycloak |
| 7 | `infra/azure/README.md` | MODIFY | Record this defect/correction in "Known residual risks," matching the CDD-069/070/071 precedent of documenting real-Azure-discovered-and-closed items |

```
CREATE = 0
MODIFY = 7
DELETE = 0
TOTAL  = 7
```

No backend path, no Bicep module, no Key Vault, no dependency file, no other frontend UX path is authorized.

## 16. Exact tests frozen

1. Local Keycloak scope-contract regression: existing test at `frontend/tests/browser-session.test.ts:266` ("canonical default scope is exactly the least-privilege live-capability set...") must continue to pass **unmodified in its assertions**, proving `NEXT_PUBLIC_OIDC_API_RESOURCE_URI` unset reproduces today's exact bare-scope string.
2. New: with `NEXT_PUBLIC_OIDC_API_RESOURCE_URI` set to a test value (e.g. `api://test-resource`), the resulting `config.scope` contains `openid profile` unprefixed, followed by all ten capability names each prefixed exactly `api://test-resource/<name>`, in a fully deterministic, parseable form (split on space, assert exact token set — not substring matching).
3. Standard OIDC scopes (`openid`, `profile`) remain unqualified in both the set and unset case.
4. All ten backend capabilities remain present (qualified or bare, depending on the case) — none dropped, none renamed.
5. `supply-chain-impact:read` remains absent in both cases.
6. The retired `information-element-evidence-fitness:read` remains absent in both cases.
7. `NEXT_PUBLIC_OIDC_SCOPE`'s existing full-override test (`frontend/tests/browser-session.test.ts:316`) continues to pass unmodified, proving the override still fully replaces the computed default regardless of `NEXT_PUBLIC_OIDC_API_RESOURCE_URI`.
8. Static: the deployment-guide regression check (§15 item 5) fails if Part 27's frontend build example lacks `NEXT_PUBLIC_OIDC_API_RESOURCE_URI` set to the real backend App ID URI — verified (at authorship time) to actually fail against the guide's current, uncorrected text, then pass once corrected, mirroring the CDD-071 pattern of proving the check is non-vacuous.
9. No legacy `scope` claim fallback is introduced anywhere (unaffected, backend unchanged — confirmed by not touching backend source at all).
10. Existing tenant-claim behavior/tests remain unaffected (unaffected, out of scope, not touched).
11. No client secret introduced (this correction touches only public, client-exposed configuration).
12. Authorization Code + PKCE architecture unchanged (unaffected, `browser-session.ts` not touched by this artifact).

## 17. Pass-2 image disposition and corrected-image requirement

The existing Pass-2 digest (`sha256:ba069cda25ad9b37db2ef98fa216b37ece5f845ab65ee6f322314c2affa95734`) correctly implements every part of CDD-073 — it is not "generally broken," is not deleted, and its tag/digest is not overwritten. It is operationally unable to complete a real Entra login solely because of this newly discovered scope-wire-format defect. Implementation of this artifact produces a **new, distinct immutable digest** (Pass-3, in effect, though CDD-074 does not require renaming the build-arg naming convention) built from the corrected source, `linux/amd64`, pushed to the same ACR — the prior digest remains a valid historical artifact, not deleted or reused.

## 18. Real-Azure implementation/VM plan (frozen, not executed in this DRG)

Source correction → frontend unit tests (§16 items 1–7) → frontend production build (`next build`, proving no build-time error) → new `linux/amd64` image → immutable ACR digest, independently verified → application-tier `what-if` (frontend-image-only logical change, all else unchanged) → real deployment → healthy revision confirmed → real DEV-user browser login (Authorization Code + PKCE, same mechanism as before) → authorization code issued this time → PKCE token exchange → real access token → `aud` correct → `tid` correct → `scp` containing the requested bare capability names (per §7) → `noetva_tenant_id` correct → backend acceptance → the four CDD-066 protected capabilities → authenticated real-PostgreSQL-backed path → negative tests (401/403/wrong-audience/wrong-tenant/wrong-issuer, exactly as CDD-073 already froze). Not executed here.

## 19. Azure/database/lifecycle preservation (reconfirmed, not mutated this DRG)

Re-confirmed, read-only, unchanged: `backendMinReplicas: 0`; backend/frontend both healthy; PostgreSQL `Ready`/`Disabled` private; current backend digest (`sha256:3c7e46ac...`) and current (pre-correction) frontend digest (`sha256:ba069cda...`) both unchanged; CORS configuration unchanged (`["https://noetva-dev-eus2-frontend...azurecontainerapps.io"]`). No migration, schema change, tenant bootstrap, DSN change, role change, or secret rotation performed or required by this artifact.

## 20. STOP conditions (all evaluated during this DRG; none triggered)

- `AADSTS650053` **was** independently reproduced from existing Entra sign-in evidence (§1) — not triggered.
- `resourceId` **does** resolve to the literal Microsoft Graph GUID (§1) — not triggered.
- Microsoft documentation **corroborates**, does not contradict, the proposed root cause (§2) — not triggered.
- The backend App ID URI **matches** the governed value exactly (§5) — not triggered.
- Scope exposure **does not** differ from the expected 11 (§5) — not triggered.
- The frontend semantic scope list **does not** differ from CDD-066 (§14) — not triggered.
- The fix does **not** require changing backend authorization semantics — proven unnecessary by exhaustive source trace (§7/§8) — not triggered.
- The fix does **not** require weakening PKCE/authentication, a client secret, implicit grant, or Entra permission broadening (§6/§9, all untouched) — not triggered.
- The fix does **not** require any database/security architecture change (§19) — not triggered.
- The artifact ceiling **is** bounded (§15 — 7 paths, all MODIFY, zero new resource type, zero dependency) — not triggered.
- No other independent material defect was discovered during this DRG's investigation.

No STOP condition fired. This correction is safe to freeze and hand to an implementation phase.

---

**Freeze evidence index:** the `AADSTS650053`/`resourceId` evidence was independently re-queried live from Entra's own `auditLogs/signIns` this DRG (not reused from the prior investigation's cached output); the Microsoft identity-platform scope-resolution rule was fetched directly from two live Microsoft Learn pages, quoted verbatim; the backend's bare-scope authorization contract was independently re-traced across every real call site in `backend/app/api/`, not assumed; the local Keycloak realm's bare-scope definitions were independently re-read from `keycloak/ctec-realm.json`; the existing frontend permission/consent state was independently re-queried live via Microsoft Graph, unchanged from CDD-073.
