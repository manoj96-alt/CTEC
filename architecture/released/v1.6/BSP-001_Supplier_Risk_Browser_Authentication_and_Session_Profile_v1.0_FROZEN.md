# BSP-001 — Supplier Risk Browser Authentication and Session Profile

Version: 1.0
Status: FROZEN
Owner: ECOM Platform Enterprise (`00000000-0000-0000-0000-000000000004`)

## Boundary and flow

CDD-014 is a public browser client. It SHALL use OAuth 2.0 Authorization Code with PKCE S256 and
OIDC. A fresh cryptographically random `state`, `nonce`, and PKCE verifier SHALL be created per
authorization request; callback processing SHALL validate exact state, nonce, issuer, client ID,
redirect URI, authorization response, and token claims before establishing a session. Implicit and
resource-owner-password flows, client secrets in the browser, dynamic issuer selection, and open
redirects are prohibited.

Issuer, public client ID, API audience, exact registered redirect URI, exact post-logout redirect
URI, and requested PAS scopes come only from deployment-controlled public configuration. Redirects
must exactly match a registered same-origin value. Callers cannot select issuer, tenant, audience,
redirect, roles, scopes, or authority mappings.

## Session and token handling

Access and ID tokens exist only in memory. They SHALL NOT enter URLs after callback processing,
browser history, localStorage, sessionStorage, IndexedDB, Cache Storage, service workers, logs,
analytics, error reports, or serialized application state. No refresh token is requested or stored
for this MVP. Renewal uses bounded OIDC authorization with PKCE; if silent authorization is not
supported or fails, explicit reauthentication is required. Expired, missing, malformed, wrong
audience/issuer, or insufficient-scope sessions fail closed.

The frontend carries bearer access tokens only in the `Authorization` header to the configured
CDD-013 origin. It never constructs AuthorityContext. Tenant and authorization are derived by
CDD-013 from the validated token. On logout, expiry, tenant/session change, or authorization loss,
the application clears tokens and sensitive in-memory state, cancels requests, and broadcasts a
non-sensitive logout/expiry signal to other same-origin tabs. Tokens are never placed in the
broadcast payload.

## Browser protections

- Bearer-header mutations do not use cookies; CSRF tokens are therefore not required, but the API
  CORS allowlist and browser origin must be exact and credentials mode disabled.
- Callback and logout validate state and exact same-origin return paths. Login/logout CSRF and
  redirect manipulation are prohibited.
- Required deployment headers: restrictive CSP, `frame-ancestors 'none'`,
  `X-Content-Type-Options: nosniff`, strict referrer policy, and a least-privilege Permissions Policy.
- Protected API responses and authentication routes use `Cache-Control: no-store`.
- Untrusted content is rendered only as encoded text; unsafe HTML and dynamic script construction
  are prohibited.
- Telemetry may include route class, correlation ID, latency, and safe code only. Authorization
  codes, tokens, claims, evidence, request bodies, and authority details are prohibited.

## Failure and recovery

Authentication failure presents a safe reauthentication action without preserving sensitive
response state. Browser refresh loses the in-memory token and requires bounded renewal or login;
the deep-link path may be retained only as a validated same-origin path without query secrets.
Multi-tab logout/expiry clears every tab. Network or provider failure never falls back to caller
identity, stale tokens, alternate issuers, or weakened validation.

## Validation

CDD-014 SHALL test PKCE S256, state/nonce mismatch, exact redirects, open-redirect rejection,
expiry/renewal/logout, memory-only storage, redaction, multi-tab clearing, refresh recovery,
identity/tenant/scope injection, CORS/origin behavior, CSP expectations, and unsafe-content
rendering.
