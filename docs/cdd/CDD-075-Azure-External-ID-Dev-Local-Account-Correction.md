# CDD-075 — Azure External ID DEV Local-Account Correction

**Status:** FROZEN
**Originating phase:** AZURE-ENTRA-OIDC-R11-R2 (DRG only in this artifact)
**Amends:** nothing frozen in place. Complements CDD-073/074 (both unchanged, both already real-Azure verified for their own scope) by correcting a distinct, later-stage real authentication defect discovered immediately after CDD-074's own successful real-Azure verification. Does not reopen CDD-073's redirect/claims-mapping/app-registration work or CDD-074's scope-qualification work.

**Scope:** the DEV test identity used to exercise real Entra External ID login, and one narrow deployment-guide correction to its creation instructions. No application source, no Bicep, no database, no Key Vault, no app registration, no user flow, no claims-mapping policy.

---

## 1. Boundary already closed — reaffirmed, not reopened

Fresh, independent Entra sign-in log query (read-only, tenant `8f9e2dee-...`) confirms: the six newest events for `dev-test@noetvaexternal.onmicrosoft.com` via `noetva-dev-frontend`, spanning `2026-09-13T01:59:13Z`–`02:26:42Z`, all show `resourceId: 3a880f13-985d-4a71-be05-20f97b9bcfa3`, `resourceDisplayName: "noetva-dev-backend-api"` — **never** the Microsoft Graph GUID. `AADSTS650053` does not appear in any of them. **CDD-074's resource-scope correction is proven closed and is not reopened by this artifact.**

## 2. Current, distinct blocker

All six events show `errorCode: 50126`, `failureReason: "Error validating credentials due to invalid username or password."` This occurs at the credential-validation stage, strictly later in the protocol than the resource-scope negotiation CDD-074 fixed — a structurally different failure boundary, not a recurrence.

## 3. Pass-3 preservation (reconfirmed, not touched)

Frontend: `provisioningState: Succeeded`, digest `sha256:b4d52a9e96721ddd00cac62977f7d88ced3b17360a1b583b2ed7e1c32fa031d4` (the exact Pass-3 digest), revision `Healthy`. Backend: digest unchanged (`sha256:3c7e46ac...`), `backendMinReplicas: 0`, `Healthy`. Both `/health` return real `200`. No redeploy performed or required by this DRG.

## 4. Existing DEV user object (fresh, read-only, safe fields only)

`id: c1d19303-0b45-4db9-b7d6-9ecaa0e41297`, `accountEnabled: true`, `userType: Member`, `userPrincipalName: dev-test@noetvaexternal.onmicrosoft.com`, `mail: null`, `otherMails: []`, `creationType: null`, `extension_...tenant_id: "noetva-dev-tenant"` (correct, unchanged). **`identities` contains exactly one entry:** `{signInType: "userPrincipalName", issuer: "noetvaexternal.onmicrosoft.com", issuerAssignedId: "dev-test@noetvaexternal.onmicrosoft.com"}`. No password value was retrieved or inspected.

## 5. Microsoft External ID local-account contract (authoritative, fetched directly)

Microsoft Learn, "Identity providers for external tenants" (`concept-authentication-methods-customers`): *"Email sign-up is enabled by default in your local account identity provider settings. With the email option, users can sign up and sign in with their email address and a password... Sign-up: Users are prompted for an email address, which is verified at sign-up with a one-time passcode."* Microsoft Graph API reference, "Create User" (`user-post-users`), **Example 3 — "Create a customer account in external tenants"** (the example explicitly labeled for exactly this product/scenario, external tenants/CIAM):

```json
{
    "displayName": "Test User",
    "identities": [
        { "signInType": "emailAddress", "issuer": "contoso.onmicrosoft.com", "issuerAssignedId": "adelev@adatum.com" }
    ],
    "mail": "adelev@adatum.com",
    "passwordProfile": { "password": "passwordValue", "forceChangePasswordNextSignIn": true },
    "passwordPolicies": "DisablePasswordExpiration"
}
```

with the note *"For local account identities, password expirations must be disabled."* The response's own `userPrincipalName` is Microsoft-generated (`<random-guid>@<tenant>.onmicrosoft.com`), **never** the sign-in email — confirming UPN and local-account sign-in identifier are two independent concepts for this account type. **`signInType: emailAddress` is confirmed required** — it is the sole documented shape this identity-provider's "Create User" example produces, and is structurally distinct from `signInType: userPrincipalName` (the shape a normal Entra admin-center "Users → New user" flow produces, per Example 1 of the same reference, which has no `identities` array at all and relies on the ordinary workforce `userPrincipalName` property).

## 6. Exact identity discrepancy

The existing DEV user has **only** the workforce-shaped identity (§4); it has **zero** `emailAddress`-signInType identity. The `EmailPassword-OAUTH` provider validates credentials against a local-account identity record of exactly that shape (§5) — which does not exist on this object. Every password attempt is therefore checked against a record that doesn't exist for that provider, producing `AADSTS50126` regardless of the actual password value.

## 7. Deployment-guide root cause (confirmed, narrow)

`docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`, **Step 22.3 — "Create your first DEV test user..."**, current text: *"Where: External ID tenant → Users → New user."* This is the ordinary Entra admin-center workforce-user creation path — it does not produce a CIAM local-account identity (§5). **This is a real, narrow deployment-guide defect**, independent of any source or Bicep code, and is the exact instruction that produced the malformed live object in §4.

## 8. Existing-user repair feasibility

No Microsoft documentation found (across the "Create User" reference, its update/`PATCH` counterpart's own scope, or the External ID authentication-methods concept page) describes or supports *retrofitting* a `signInType: emailAddress` identity onto an already-existing `Member`/UPN-only user via `PATCH /users/{id}`. Every Microsoft-documented example that produces a working local-account identity does so **at creation time** (`POST /users`). Attempting an undocumented `PATCH` to inject a new `identities` array onto an existing directory object — one already carrying live app-registration/claims-mapping expectations tied to its Object ID — is exactly the kind of unsupported, ambiguous operation this DRG's own STOP conditions flag ("Microsoft documentation contradicts the current root cause," "correcting the account requires weakening authentication"). **Existing-user repair is rejected as unsupported/ambiguous, not selected.**

## 9. Replacement-account feasibility

Microsoft Graph's own "Create User" reference **Example 3** is written for exactly this scenario (external-tenant customer/local account) and is fully deterministic and repeatable: a single `POST /users` call with an explicit `identities` array, `mail`, `passwordProfile`, and `passwordPolicies: DisablePasswordExpiration`. This is the documented, supported, minimal-risk path.

## 10. Email identity decision

The new local account's `issuerAssignedId`/`mail` will be a **new**, distinct address under the tenant's own default `noetvaexternal.onmicrosoft.com` domain (e.g. `noetva-dev-test-2@noetvaexternal.onmicrosoft.com` — exact literal value frozen at implementation time from this pattern, distinct from the retired account's address to avoid any ambiguity between the two objects) — **not** a real, routable company or founder mailbox (explicitly rejected per this DRG's own instruction, and unnecessary: Microsoft's own Example 3 shows `issuerAssignedId` need not match the issuer's own domain, and password-based sign-in requires no inbox access). **Disclosed limitation, not hidden:** this address is not a deliverable mailbox; Microsoft's self-service "forgot password" email-OTP flow will not function for it. This is acceptable for a DEV-only test identity whose password is established and, if ever needed, reset by an administrator via Graph (§11) — never via the self-service email link.

## 11. Password lifecycle decision

`passwordPolicies: "DisablePasswordExpiration"` is set at creation — **required**, per Microsoft's own explicit documentation note (§5), to avoid recreating the `AADSTS50055` (password-expired) condition this arc already hit once on the malformed account. `forceChangePasswordNextSignIn: true` is set, matching Microsoft's own CIAM-specific Example 3 value exactly (a documentation note earlier in the same reference, attached to a *different*, B2C-migration-labeled example, states the opposite — this discrepancy is disclosed, not silently resolved by guessing; Example 3's own value is followed because it is the example explicitly written for this exact external-tenant/CIAM scenario). The operator will complete one interactive password-set step on first real sign-in, exactly the same class of safe, already-proven interactive flow used earlier in this arc for the password-expiry condition. **No password value is ever placed in source, CDD text, shell history, logs, or any report** — the initial value is chosen and entered by the operator directly into the Graph/portal creation call at implementation time, never told to or handled by this session.

## 12. Business tenant extension preservation

The new account's `extension_4795a02ed0cc42929fe9a98d42d08300_tenant_id` (the exact, unchanged directory extension, §19/CDD-064) is set to `noetva-dev-tenant` at creation time, identically to the retired account — this is a plain custom-extension property write, entirely independent of the `identities` array, and requires no claims-mapping-policy change (the policy already targets this extension by its `ExtensionID`, not by user Object ID).

## 13. Object-ID dependency analysis

Exhaustive repository search (`c1d19303-0b45-4db9-b7d6-9ecaa0e41297`) across all source, test, Bicep, JSON, and YAML files: **zero matches**. The only place this Object ID appears anywhere in the repository is one informational line in CDD-073's already-frozen, unmodified text (§4 of that artifact) — a historical record, not a live dependency. **No hidden Object-ID dependency exists.** The replacement account's new, different Object ID introduces no risk.

## 14. Old malformed user disposition

**Not deleted or disabled by this artifact.** Per this DRG's own explicit preference for staged, non-destructive sequencing: the replacement account is created and fully verified (real login → token → protected APIs) **first**; only after that succeeds does a future, separately-authorized step disable (not delete) the old malformed account, and only if explicitly re-confirmed necessary at that time — deletion is never required merely for authentication success, and this artifact does not authorize it.

## 15. User-flow preservation

`noetva-dev-signup-signin` re-confirmed live and unchanged: `EmailPassword-OAUTH` ("Email with password"), associated with the frontend application, attribute-collection schema unchanged (`email`/`displayName`/`givenName`/`surname` only — no tenant attribute, confirmed absent, matching CDD-073's own prior finding). **No user-flow mutation required or authorized.**

## 16. Application preservation

Frontend/backend app registrations, redirect URI, logout URI, exposed scopes, permissions, consent, claims-mapping policy (`NoetvaTenantClaimMapping`, exactly one, still assigned), `acceptMappedClaims`, `requestedAccessTokenVersion` — all re-confirmed live and unchanged by this DRG's own investigation and the immediately preceding R11-R1 work. **None require any change; none are touched by this artifact.**

## 17. Source-change requirement

**Zero.** This is an Entra directory-object and one narrow documentation-text correction only.

## 18. Deployment-guide correction (narrow, bounded)

`docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`, Step 22.3 only: replace the instruction to use the ordinary "Users → New user" admin-center flow with the Microsoft-documented Graph `POST /users` local-account creation call (§5/§9's exact shape), explicitly noting `passwordPolicies: DisablePasswordExpiration` and the `emailAddress` `signInType` requirement. **This is the only documentation edit authorized** — no broader Zero-to-Deployment runbook hardening, per the user's own explicit instruction that such hardening is deferred until after full deployment/authentication closure.

## 19. Selected correction architecture: REPLACEMENT CIAM LOCAL ACCOUNT

Justified directly against every required criterion: **Microsoft supportability** — Example 3 is an official, current, scenario-matched reference; **repeatability** — a single deterministic `POST /users` call, reproducible for every future environment; **security** — no weakening, no broadened authority, no credential exposed to this session; **identity correctness** — produces exactly the documented local-account shape the configured user flow expects; **password lifecycle** — explicit, documented, disclosed (`DisablePasswordExpiration` + one interactive first-login password set); **business-tenant claim preservation** — the extension is a plain property, copied identically; **operator simplicity** — one Graph call plus one interactive password-set step, no ambiguous retrofit; **deployment-guide reproducibility** — directly fixes the exact instruction that caused this, so the next environment's DEV user is created correctly the first time; **risk of hidden state** — none found (§13); **least mutation** — smaller and more certain than attempting an undocumented, unsupported existing-object mutation (§8).

## 20. Exact live Entra mutation authorization (enumerated, not blanket)

R11-R2-I **is** authorized to: **(1)** create exactly one new user via `POST /users` with the Example-3 shape — `displayName` (e.g. "Noetva DEV Test User 2"), `identities: [{signInType: "emailAddress", issuer: "noetvaexternal.onmicrosoft.com", issuerAssignedId: <new address, §10>}]`, `mail: <same address>`, `passwordProfile: {password: <operator-chosen, never told to this session>, forceChangePasswordNextSignIn: true}`, `passwordPolicies: "DisablePasswordExpiration"`; **(2)** set `extension_4795a02ed0cc42929fe9a98d42d08300_tenant_id: "noetva-dev-tenant"` on that same new user (in the same or an immediately following call). R11-R2-I is **not** authorized to: modify the existing malformed DEV user in any way; disable or delete any user (deferred, §14); modify the user flow, any app registration, any permission/consent, or the claims-mapping policy.

## 21. Exact repository artifact ceiling

| # | Path | Change |
|---|---|---|
| 1 | `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` | MODIFY — Step 22.3 only, per §18 |

```
CREATE = 0
MODIFY = 1
DELETE = 0
TOTAL  = 1
```

## 22. Real-Azure VM plan (frozen, not executed in this DRG)

Create the replacement local account (§20) → confirm `extension_...tenant_id` populated → read back its `identities`/`mail`/`accountEnabled` shape (safe fields only) → operator performs exactly one real browser login as the new identity, completing the forced first-login password set → confirm `resourceId` is still the Noetva backend (not Graph) → authorization code issued → PKCE token exchange → real access token → `tid`/`aud`/`iss`/`scp`/`noetva_tenant_id` all correct (per CDD-073 §25's already-frozen contract) → backend accepts the token → the four CDD-066/CDD-073 protected capabilities exercised → at least one authenticated, real-PostgreSQL-backed path proven → the full negative-test suite (401/403/wrong-audience/wrong-tenant/wrong-issuer, per CDD-073 §28) → **only after all of the above succeed**, a separate, explicit decision on the old malformed account's disposition (disable, not delete, if still authorized at that time).

## 23. STOP conditions (all evaluated during this DRG; none triggered)

- `signInType=emailAddress` **is** actually required — confirmed by Microsoft's own documented example being the sole supported shape for this identity provider (§5) — not triggered.
- Microsoft documentation does **not** contradict the root cause — it directly corroborates it (§5) — not triggered.
- The existing user **cannot** authenticate correctly without correction (six consecutive real `AADSTS50126` failures) — not triggered.
- Correcting the account does **not** require weakening authentication (§16, unaffected) — not triggered.
- Correcting the account does **not** require changing application auth architecture (§16) — not triggered.
- The business tenant claim **is** preserved (§12) — not triggered.
- The replacement user introduces **no** unresolved Object-ID dependency (§13, exhaustively searched) — not triggered.
- User-flow mutation is **not** materially necessary (§15) — not triggered.
- Source change beyond documentation is **not** materially necessary (§17) — not triggered.
- No other independent material defect was discovered during this DRG.

No STOP condition fired. This correction is safe to freeze and hand to an implementation phase.

---

**Freeze evidence index:** the sign-in log evidence (§1/§2) and the DEV user's current identity shape (§4) were freshly re-queried this DRG, not reused from the prior investigation's cached output; the Microsoft identity-platform local-account contract (§5) was fetched directly from two live Microsoft Learn/Graph reference pages, quoted verbatim, including the exact CIAM-specific "Create a customer account in external tenants" example; the Object-ID dependency search (§13) was a fresh, exhaustive repository grep, not assumed.
