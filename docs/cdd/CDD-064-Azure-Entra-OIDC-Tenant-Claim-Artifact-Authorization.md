# CDD-064 — Azure Entra OIDC Tenant-Claim Artifact Authorization

**Status:** FROZEN
**Originating phase:** AZURE-DEV-ENTRA-TENANT-CLAIM-R1 (DRG → I → VM-PREDEPLOY → VM-RUNTIME)
**Scope:** A single, narrow Azure/Entra compatibility configuration — which JWT claim name carries the Noetva business-tenant identifier on Azure, versus local/Docker/Keycloak. No authentication redesign. No change to authorization semantics, scope-claim handling (CDD-063/R2), issuer/audience/JWKS validation, or any R1(scope-length) scope literal.

---

## 1. Authoritative baseline at freeze

Main SHA: `e0188319236bd96711331538a6efacc2d0d4fb40` (independently re-verified against `origin/main` and GitHub `main`). R2 (CDD-063, `oidcScopeClaim`/`scp`) is merged and present at this commit; its Stage 2 (real-Entra operational proof) remains pending and is untouched by this artifact. This document does not reopen, reference for modification, or depend on any R2 or R1(scope-length) governed value.

## 2. Real-Azure blocker this artifact resolves

During live Azure DEV / Entra External ID configuration, attempting to add an outgoing claim literally named `tenant_id` in **Enterprise applications → noetva-dev-backend-api → (OIDC-based Sign-on) Attributes & Claims → Add/Manage claim** produces the Microsoft Entra portal validation error **"This claim type is restricted"**, and the claim is not saved. This is genuine, reproducible Microsoft Entra platform behavior — not a defect in Noetva's own configuration.

## 3. Root cause (Microsoft-documented, independently verified)

`tenant_id` is a **permanent member of the Microsoft Entra JWT restricted claim set** (Microsoft Learn, "Claims customization" reference, JSON Web Token restricted claim set table), alongside `tid`, `oid`, `sub`, `aud`, `iss`, `scp`, `roles`, and others. Per that same reference: *"Names and URIs of claims in the restricted claim set can't be used for the claim type elements."* Unlike a narrow subset of the separately-listed **SAML** restricted claims (e.g. `windowsaccountname`, `primarysid`, legacy `upn`/`role`), which the same page states *"are restricted by default, but aren't restricted if you have a custom signing key,"* **no such override exists for the general JWT restricted claim set** that `tenant_id` belongs to. A custom Entra signing key would not unlock the literal name `tenant_id` as an outgoing JWT claim. This restriction is:
- **Not** External-ID-specific — it is a platform-wide Entra ID claims-customization restriction that applies identically to any Enterprise Application's Attributes & Claims / claims-mapping-policy configuration, regardless of tenant type (workforce or External ID/CIAM).
- **Not** limited to unqualified names by coincidence of Noetva's choice — `tenant_id` is explicitly enumerated in Microsoft's fixed restricted-name list, so no unqualified spelling of that exact string will ever be accepted as a custom outgoing claim name.
- Independent of, and unrelated to, R2's `scp`/`scope` correction — `scp` and `scope` are also both restricted-set members for *unqualified custom mapping* in general, but R2 never attempted to remap them; R2 only reconfigured which *already-standard, provider-emitted* claim (`scp` vs `scope`) the backend reads. This artifact is a different kind of correction: `tenant_id` is not a standard Entra-emitted claim at all (§4) and must be manufactured as a **custom** claim, which is exactly the scenario the restricted-claim-set rule blocks for the bare name.

## 4. Microsoft-supported claim architecture (documented, not invented)

Microsoft Learn's "Customize app JSON Web Token (JWT) claims" reference (Attributes & Claims → "Add application-specific claims") states: *"Enter the name of the claims. The value doesn't strictly need to follow a URI pattern. If you need a URI pattern, you can put that in the Namespace field."* This is the documented, portal-native escape hatch for exactly the error reproduced in §2: supplying a **Namespace** produces a compound outgoing claim identifier distinct from the bare restricted string `tenant_id`, which is therefore no longer a literal match against the restricted-claim-set check.

**Frozen mechanism:** the outgoing claim is configured with:
- **Name:** `tenant_id`
- **Namespace:** `https://noetva.ai/claims`
- **Source:** Attribute → Directory schema extension → the existing `tenant_id` custom user attribute (§6)

**Not frozen as a literal string in Bicep by this artifact:** the exact resulting compound claim key that Entra emits into the token (whether it joins as `<namespace>/<name>`, `<namespace>tenant_id`, or another concatenation) is a portal-rendered value that must be read back from the Attributes & Claims "Review"/overview screen (or a real decoded token) before it is written into any environment parameter file. R1-I must capture this exact string with evidence (screenshot or decoded-token excerpt) and treat it as the authoritative value — never assume the join format sight-unseen. Until then, the environment parameter files carry an explicit placeholder (§8).

## 5. Directory attribute vs. outgoing claim name (separated, as required)

These are two independent things and must not be conflated:
- **Directory attribute name:** `tenant_id` — the custom user attribute / directory schema extension. **Unchanged by this artifact.** The user's real-Azure evidence states this attribute may already exist; **do not delete or mutate it.** It remains admin-controlled, set via **Users → (user) → custom attribute section**, never via self-service sign-up collection (§9).
- **Outgoing JWT claim name:** must change from the restricted bare `tenant_id` to the namespaced form in §4. This is a claims-mapping configuration change only — it does not touch, rename, or migrate the underlying directory attribute.

## 6. Access-token mapping architecture (proven, not assumed)

Per Microsoft's claims-mapping-policy model (Microsoft Learn, "Claims customization," Claim schema `Source` table: `user | application | resource | audience | company`), a claims customization is configured **on the resource application's own service principal**, and the resulting policy governs tokens **issued for that application as the audience** — i.e., access tokens minted with that application as the resource, not the ID token issued to a different client application. The real-Azure evidence already reflects the correct target: the operator configured Attributes & Claims on **`noetva-dev-backend-api`'s own Enterprise Application entry** (the resource/API service principal whose Application ID URI, `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`, is the backend's own audience) — **not** on `noetva-dev-frontend`'s entry. This is the architecturally correct target for the claim to land in the ACCESS token the frontend sends to the backend, not merely the ID token. R1-I must still empirically confirm this by decoding a real access token (Stage 2, §14) — this artifact freezes the correct *mechanism*, not yet the empirical proof.

## 7. Frozen backend configuration decision — no parser change authorized

`backend/app/core/config.py`: `oidc_tenant_claim: str = "tenant_id"`, plain string, no format constraint. `backend/app/api/supplier_risk/authentication.py`, `_principal()`: `tenant = claims.get(self._settings.oidc_tenant_claim)` — an unconditional flat-dict `.get()` by whatever string names the configured claim. A decoded JWT's claims are a flat JSON object; a claim key containing `/`, `:`, or any other character (e.g. `https://noetva.ai/claims/tenant_id`) is retrieved identically to any other string key — **no nested/URI-aware traversal exists or is required.** Therefore: **no modification to `backend/app/core/config.py` or `backend/app/api/supplier_risk/authentication.py` is authorized under this artifact.** The correction is a configuration-value change only, exactly analogous to R2's `oidcScopeClaim`/`CTEC_OIDC_SCOPE_CLAIM` pattern.

## 8. Frozen Azure Bicep and environment-parameter change

**`infra/azure/main.bicep`** — add, adjacent to the existing `oidcScopeClaim` parameter:
```bicep
@description('OAuth tenant-claim name the backend trusts for the Noetva business-tenant identifier (Entra External ID: a namespaced custom claim, since the bare name "tenant_id" is a Microsoft-reserved JWT claim; local Keycloak: tenant_id).')
param oidcTenantClaim string
```
and forward it into the `resources.bicep` module call, alongside `oidcScopeClaim: oidcScopeClaim`:
```bicep
oidcTenantClaim: oidcTenantClaim
```

**`infra/azure/resources.bicep`** — matching parameter declaration (same description, no default), and one new `backendEnvVars` entry adjacent to the existing `CTEC_OIDC_SCOPE_CLAIM` entry:
```bicep
{ name: 'CTEC_OIDC_TENANT_CLAIM', value: oidcTenantClaim }
```
No secret reference. No Key Vault entry. No runtime fallback logic.

**Environment parameter files** — authorize exactly these four files, each receiving exactly one new key:
```json
"oidcTenantClaim": { "value": "REPLACE_WITH_ENTRA_TENANT_CLAIM_NAME" }
```
- `infra/azure/environments/dev/main.parameters.json`
- `infra/azure/environments/staging/main.parameters.json`
- `infra/azure/environments/demo/main.parameters.json`
- `infra/azure/environments/prod/main.parameters.json`

**Rationale for a placeholder here (unlike R2's concrete `"scp"`):** `scp` was Microsoft's own fixed, universal, provider-level convention — deterministic and knowable without touching any specific tenant. The exact namespaced tenant-claim string is not: it depends on the literal Namespace text an operator enters and how the real Entra portal/token renders the concatenation (§4). Freezing a concrete literal here, sight-unseen, would risk silently shipping a wrong value with no fail-safe (a wrong tenant-claim name fails exactly like a missing one — closed, per §7 — so the risk is operational breakage, not a security hole, but it is still not evidence-based and is therefore not authorized). R1-I must replace this placeholder with the real, portal-confirmed string (§4) and capture that evidence in its report, following the same discipline already used for `REPLACE_WITH_ENTRA_EXTERNAL_ID_ISSUER_URL` and its siblings in these same four files.

## 9. Tenant-isolation security analysis (binding invariant, re-affirmed)

**A public/signup user MUST NOT be able to select, edit, forge, or self-assert the authorization-relevant Noetva business-tenant identifier.** This artifact changes nothing about that boundary:
- The directory attribute (`tenant_id`, §5) remains admin-set post-creation via **Users → (user) → custom attribute section** in the Entra portal — never exposed as a collected field in the `noetva-dev-signup-signin` self-service user flow's attribute-collection step.
- The namespace/claim-name change (§4) is a claims-*emission* configuration, not a claims-*collection* configuration — it does not create any new avenue for a signup user to influence the value.
- The backend's fail-closed behavior (§7, unchanged) still rejects any token with a missing, empty, non-string, or list-valued tenant claim, regardless of which literal claim name is configured.
- **Explicitly re-confirmed:** creating this custom directory attribute (already done, per real-Azure evidence) remains **required** for the tenant claim to exist at all; exposing it to self-service sign-up collection would be **security-dangerous** and is explicitly **not** authorized by this or any prior artifact.

## 10. Manifest-setting re-evaluation (independently assessed, not carried over blindly)

- **`acceptMappedClaims: true`** — **required and correct** for this scenario. Microsoft Learn ("Customize app JSON Web Token (JWT) claims," "Update the application manifest") states this property is needed for a single-tenant app to use claims mapping without a custom signing key, and that the token audience must be either the application GUID or a verified tenant domain (else Entra returns `AADSTS501461`). Noetva's backend Application ID URI, `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`, is in the **application-GUID** form — it satisfies this rule directly. This assumes the backend app registration is single-tenant (the ordinary default; R1-I must confirm this directly rather than assume it, since a multi-tenant registration would instead require a custom signing key per the same documentation).
- **`isFallbackPublicClient: true`** — **not evidenced as required for this scenario and not authorized to be reintroduced by this artifact.** This manifest property governs public-client/ROPC-style flow fallback behavior; it appears nowhere in Microsoft's claims-mapping documentation and nothing else in this repository (no ROPC flow, no public-client token acquisition path) depends on it. The prior deployment guide's inclusion of this flag appears to be an unjustified carry-over from an unrelated tutorial. **Flagged for removal** from the corrected guide (§11) unless a separate, evidenced requirement for it is identified — this artifact does not authorize adding it to the Bicep/App-registration configuration it governs, and the documentation correction must stop recommending it for this purpose.

## 11. Frozen documentation contract

Authorize modification only to `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`:
- **Part 22** rewritten to reflect: the bare `tenant_id` outgoing-claim attempt is rejected by Entra with "This claim type is restricted" (§2/§3); the corrected Step 22.2 uses the Namespace field (§4) with the directory attribute unchanged (§5); explicit instruction to capture and record the real resulting claim string before deployment (§4/§8); the `acceptMappedClaims` requirement re-justified (§10) and `isFallbackPublicClient` removed from the instructed manifest edit (§10); Part 22.4's negative-test table extended with the tenant-claim-specific fail-closed cases already governed in §12.
- **Part 32**'s backend environment-variable inventory line extended with `CTEC_OIDC_TENANT_CLAIM`, alongside the existing `CTEC_OIDC_SCOPE_CLAIM` line added by R2, with truthful text stating the value is the real, portal-confirmed namespaced claim string, not `tenant_id` literally.
- **Part 34**'s end-to-end verification updated to decode the real access token and confirm the *actual configured* claim key (not a hardcoded assumption of `tenant_id`) carries the expected tenant value.

No other section of the Guide may be modified under this artifact.

## 12. Frozen test contract

Authorize modification only to `backend/app/tests/test_oidc_authentication.py`. Extend the existing `_verifier()` helper (already extended once, by R2, with `oidc_scope_claim`) with an additional keyword parameter `oidc_tenant_claim: str = "tenant_id"` (default-preserving; forwarded into the `Settings(...)` construction), and add exactly these new test functions (no existing test may be altered):

1. **Namespaced claim accepted.** `oidc_tenant_claim="https://noetva.ai/claims/tenant_id"`; token carries that exact key with value `"noetva-dev-tenant"` (and no bare `tenant_id` key). Assert `principal.tenant_id == "noetva-dev-tenant"`.
2. **No fallback to bare `tenant_id`.** Same namespaced configuration; token carries only the bare `tenant_id` key (Entra's blocked/legacy shape), omitting the namespaced key entirely. Assert `AuthenticationError` with code `AUTH_TENANT_MISSING_OR_AMBIGUOUS`.
3. **`tid` never substitutes.** Namespaced configuration; token carries a standard `tid` claim (Entra's real directory-tenant GUID) but omits the configured namespaced claim. Assert the same fail-closed code — proving Entra's `tid` can never silently become Noetva's business tenant.
4. **Both present, only the configured claim is trusted.** Namespaced configuration; token carries both `tid` (directory GUID) and the namespaced business-tenant claim (different values). Assert `principal.tenant_id` equals only the namespaced claim's value, never `tid`'s.
5. **Ambiguous/list-valued namespaced claim fails closed.** Namespaced configuration; the namespaced key's value is a list (e.g. `["a", "b"]`). Assert `AUTH_TENANT_MISSING_OR_AMBIGUOUS`.
6. **Local/Keycloak default unaffected.** The existing, unmodified `test_valid_signed_token_derives_minimum_trusted_principal` (default `oidc_tenant_claim="tenant_id"`, bare `tenant_id` claim) must continue to pass unchanged — re-run, not rewritten.
7. **R2 `scp` behavior unaffected.** The existing R2 tests (`test_configured_scp_claim_is_extracted_in_entra_delegated_shape`, `test_configured_scp_claim_does_not_fall_back_to_scope`) must continue to pass unchanged — re-run, not rewritten.

Do not modify production authentication source to make any of these pass — if any fails against current source, that is a STOP-worthy discrepancy for R1-I to report.

## 13. Exact implementation authorization ceiling

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

**Explicitly prohibited** under this artifact (any of the following requires a STOP and a new governance correction, never silent expansion): `backend/app/core/config.py`; `backend/app/api/supplier_risk/authentication.py`; `docker-compose.yml`; `keycloak/ctec-realm.json`; any `frontend/*` path; any `.github/workflows/*` path; any R1(scope-length) or R2(scope-claim) governed value or artifact; any database schema/migration file.

## 14. GitHub variable/secret decision

**No new GitHub Actions variable. No new GitHub Actions secret. No new Key Vault entry.** The namespaced tenant-claim string is non-secret configuration naming material (it identifies a claim *shape*, not a credential), following exactly the mechanism `oidcScopeClaim` already established: a governed Azure environment parameter file entry, read directly by the operator-run `az deployment` command.

## 15. Security invariants (binding, all 15)

1. Exactly one authoritative tenant-claim name per runtime.
2. Local/Keycloak default remains bare `tenant_id`.
3. Azure/Entra uses a namespaced custom claim, never the bare restricted name.
4. No fallback from the namespaced claim to bare `tenant_id`.
5. No fallback from bare `tenant_id` to the namespaced claim.
6. No dual-claim union.
7. `tid` (Entra directory GUID) never substitutes for the Noetva business-tenant claim.
8. Missing configured claim → `AUTH_TENANT_MISSING_OR_AMBIGUOUS` → fails closed.
9. Malformed/list-valued configured claim → `AUTH_TENANT_MISSING_OR_AMBIGUOUS` → fails closed.
10. The directory attribute remains admin-controlled, never self-service-collected at sign-up.
11. Issuer, audience, JWKS, and signature validation unchanged.
12. R2's `scp`/`scope` configuration and parser unchanged.
13. R1(scope-length)'s `evidence-fitness:read` literal unchanged.
14. Endpoint-level authorization logic (`_authorize()`) unchanged.
15. Human authority boundaries (recommendation ≠ authorization; remediation ≠ resolution) unchanged.

## 16. R2 Stage 2 interaction

This artifact does not perform, complete, or substitute for R2's Stage 2 (real-Entra `scp` operational proof, CDD-063 §14). Both R2 Stage 2 and this artifact's own Stage 2 (§17) must eventually be satisfied by inspecting the **same** real, deployed backend and the **same** real, decoded access token — they are not sequential dependencies of each other, but they will likely be verified together in one real-Azure execution pass since both require the same live token.

## 17. Two-stage verification model (binding, mirrors CDD-063 §14)

### Stage 1 — Pre-deployment source certification
1. Exact authorized diff (exactly the 8 paths in §13).
2. Bicep syntax/build validation on `main.bicep` and `resources.bicep`.
3. All four environment parameter files parse and contain the `oidcTenantClaim` placeholder key.
4. `resources.bicep` genuinely emits `CTEC_OIDC_TENANT_CLAIM` from the parameter.
5–11. All seven tests in §12 pass.
12. Full backend regression passes.
13. `black`/`isort`/`ruff`/`mypy` clean.
14. Frontend regression unaffected (no frontend file in the diff).
15. Local Keycloak/Docker regression unaffected (default untouched, live-login re-confirmed).
16. GitHub CI green on the exact candidate.
17. R1(scope-length) and R2(scope-claim) non-regression re-confirmed.
18. No unauthorized path in the diff.
19. This artifact re-verified byte-identical by SHA-256 at every subsequent phase boundary.

**Stage 1 success authorizes merging the source correction only. It does not authorize declaring the Entra tenant-claim integration operationally proven, and it does not authorize writing a concrete final value into the environment parameter files beyond the placeholder in §8 unless the real portal-confirmed string is already in hand with evidence.**

### Stage 2 — Post-deployment real-Entra certification
Requires, in the real, deployed Noetva Azure DEV environment, with the backend running `CTEC_OIDC_TENANT_CLAIM=<real confirmed namespaced claim>`:
1. A real user completes real Entra Authorization Code + PKCE authentication.
2. The real access token (aud = `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`) is decoded.
3. The exact configured namespaced claim is present in that access token (not merely the ID token).
4. Its value equals the chosen DEV business-tenant identifier (e.g. `noetva-dev-tenant`).
5. The token's `tid` is confirmed to equal Entra's directory GUID (`8f9e2dee-5a5b-4b33-9044-4d11691899de`) and is confirmed **not** to be what the backend uses as the tenant.
6. The running backend Container App's environment genuinely has both `CTEC_OIDC_SCOPE_CLAIM=scp` (R2) and `CTEC_OIDC_TENANT_CLAIM=<real value>` present.
7. An authenticated request with the correct tenant claim succeeds and is scoped to the correct Noetva tenant's data.
8. A token missing the tenant claim, or carrying a tenant value with no corresponding Noetva DB tenant row, is genuinely rejected.
9. Tenant isolation (cross-tenant nondisclosure) is genuinely observed against two distinct real tenant values.

**Only Stage 2 success may declare this correction operationally CLOSED.**

## 18. Exact allowed terminology

After Stage 1 passes and the source correction is merged, the only permitted conclusion is:

> **PASS + SOURCE MERGED — TENANT-CLAIM OPERATIONAL VERIFICATION PENDING AZURE EXECUTION**

**This correction may never be declared "CLOSED" until Stage 2 succeeds.**

## 19. Frozen phase sequence

```
R1-G (this document, AZURE-DEV-ENTRA-TENANT-CLAIM-R1-DRG)
→ R1-I            (implement exactly the 8 authorized paths; Stage 1 verification; open PR, do not merge unless separately authorized)
→ R1-VM-PREDEPLOY (adversarially re-verify Stage 1; merge)
→ [Azure/Entra External ID execution — capture the real Namespace/claim string, complete Steps 22.1-22.4, deploy]
→ R1-VM-RUNTIME    (Stage 2 — the only phase permitted to declare this correction operationally CLOSED)
```

---

*This document authorizes governance only. It does not implement, deploy, or verify anything itself.*
