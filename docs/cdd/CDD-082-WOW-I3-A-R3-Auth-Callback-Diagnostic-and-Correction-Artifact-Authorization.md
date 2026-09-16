# CDD-082 — WOW-I3-A-R3 Auth Callback Diagnostic and Correction Artifact Authorization

**Status:** FROZEN
**Originating phase:** NOETVA-PRODUCT-EXPERIENCE-WOW-I3-A-R3 (live auth callback failure investigation)
**Amends:** nothing frozen in place. Complements CDD-063/064/065/066/073/074/076 (OIDC mechanism/scope/token design — unchanged, not reopened) and CDD-081 (OQI/Ontology WOW-I3-A scope — unchanged, not touched, not broadened). Does not reopen any of them.

**Scope:** exactly two files, narrowly, for exactly one purpose: capture, safely and non-destructively, the real client-side cause of the live-reproducible "Sign-in failed" callback defect first reported in WOW-I3-A-R1/R2 and now confirmed reproducible in a clean Incognito browser (falsifying the R2 stale-browser-state hypothesis). This is a diagnostic-and-correction authorization for the auth runtime path — the same class of governed exception the WOW-I2 auth correction already established precedent for — never a reopening of CDD-081's OQI/Ontology visual scope.

---

## 1. Why this is authorized outside CDD-081

CDD-081 governs the OQI/Ontology product-experience surface exclusively. The live defect under investigation is in the authentication runtime (`frontend/lib/auth/*`, `frontend/app/auth/callback/page.tsx`), which CDD-081 never touched and never authorized. R2's investigation (re-verified here, not reopened) already proved, with direct live evidence against the real Entra External ID tenant, that: the authorization request (client_id/redirect_uri/scope/PKCE) is valid and accepted; CORS is fully open at the token endpoint for this origin; CSP does not block the token-endpoint fetch; no WOW-I2/I3 commit has ever touched an auth file; `oidc-client-ts` is pinned identically to the last accepted build. The remaining candidate causes are all **client-side runtime behavior** (a possible race between the bootstrap silent-renewal attempt and an explicit interactive sign-in, or duplicate consumption of the one-time OIDC transaction state on the callback page) that cannot be distinguished from config/registration causes by any means available without either browser automation (unavailable in this environment) or safe, narrow, removable instrumentation in the two files below.

## 2. Exact authorized paths

**AUTHORIZED_MODIFY (2):**
1. `frontend/app/auth/callback/page.tsx` — add safe, narrow diagnostic capture (invocation-count / duplicate-consumption detection, and a sanitized, safe rendering of the library's own non-secret error class/code/phase) on the existing failure branch only. No change to the success path's behavior, to `completeSignIn()`'s real logic, or to PKCE/state/nonce validation.
2. `frontend/lib/auth/browser-session.ts` — add exactly one new, read-only, side-effect-free exported diagnostic accessor exposing the *existing* internal `renewalAttempted`/renewal-marker booleans (already present for the code's own bounded-renewal guard) so the callback page can safely report, as a boolean only, whether a bootstrap silent-renewal was attempted this page lifetime. No new authentication behavior, no new redirect, no new state mutation beyond what already exists.

**AUTHORIZED_CREATE (1):**
3. `frontend/tests/auth-callback-diagnostics.test.tsx` — regression coverage proving: (a) the diagnostic never renders a code, token, verifier, nonce, state value, or full query string; (b) the diagnostic correctly classifies the known oidc-client-ts error strings this investigation identified (`No state in response`, `No matching state found in storage`, an `ErrorResponse` with a safe `.error`/`.error_description`, and an unclassified fallback); (c) the invocation-count / duplicate-consumption signal behaves correctly across a simulated re-invocation; (d) the existing silent-vs-explicit failure distinction (already governed, CDD-045-companion AUTH-UX-G) is unchanged.

**FORBIDDEN (explicit, unchanged from every prior WOW phase):** any file under `frontend/app/quality/`, `frontend/app/ontology/`, `frontend/app/ontology-studio/`, `frontend/app/supply-chain-impact/`, `frontend/app/overview/`, `frontend/app/_components/home/`, `frontend/app/page.tsx`, any backend file, `frontend/components/design-system/status-indicator.tsx`, `frontend/components/design-system/empty-state.tsx`, `frontend/tests/gate-x-*.test.tsx` (unless independently verified necessary — not expected here), Entra/CIAM app-registration configuration (no change authorized unless direct proof requires it — none found so far), any Docker/build-argument change beyond what R1 already froze.

CREATE=1, MODIFY=2, DELETE=0, TOTAL=3.

## 3. Security constraints (binding, not advisory)

The diagnostic MUST NEVER render, log, or persist: an authorization code, access token, ID token, refresh token, full JWT, PKCE `code_verifier`, `nonce` value, `state` value, cookies, session contents, user PII, the full callback URL or query string, or any request header carrying credentials. Permitted diagnostic content is limited to: a sanitized exception class/name; the library's own non-secret error code/message (verified, at implementation time, to never itself embed a code/token/verifier — `oidc-client-ts`'s `ErrorResponse.error`/`error_description` fields are standard OAuth protocol strings by specification, never token material); a boolean invocation/duplicate-consumption signal; a boolean silent-renewal-attempted signal; a coarse phase marker string (`AUTH_CALLBACK_STATE_LOOKUP` / `AUTH_CALLBACK_TOKEN_EXCHANGE` / `AUTH_CALLBACK_UNKNOWN`). The instrumentation must be trivially removable (isolated to the failure branch only, no new persistent storage keys beyond one small SHA-256-hashed, non-reversible marker used only to detect duplicate consumption of the same callback URL — never the raw code/state themselves).

## 4. What this authorization does NOT permit

Disabling PKCE; disabling state/nonce validation; weakening token validation; bypassing callback validation; faking a user/session; storing tokens insecurely; globally disabling silent renewal without direct proof that is the correct fix; broad authentication rewrite; backend authorization changes; CORS broadening; Entra/CIAM registration changes (unless a later round's direct evidence proves one is required, which would need its own further amendment); arbitrary sleep/timeout race "fixes." If direct evidence from this instrumentation proves a specific, narrow correction (e.g., mutual exclusion between bootstrap silent renewal and an explicit interactive sign-in, or preventing duplicate consumption of the one-time transaction on the callback page), that correction is authorized under the same two MODIFY paths above, in the same narrow spirit — not a broader refactor.

## 5. Freeze

This document is frozen at commit time on `product/wow-i3-a`. Its own SHA-256 is computed and recorded in the governing session's report immediately after this file is written, and re-verified at every subsequent phase boundary exactly as CDD-081 and every prior CDD in this program have been.
