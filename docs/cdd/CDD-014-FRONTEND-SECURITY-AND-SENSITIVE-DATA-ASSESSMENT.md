# CDD-014 — Frontend Security and Sensitive-Data Assessment

Version: 1.0

## Required controls

- Use the BSP-001 public-client OIDC Authorization Code flow with PKCE S256 and memory-only tokens.
  Never use client credentials in the browser.
- Bearer tokens must not appear in URLs, browser history, local/session storage, IndexedDB, logs,
  analytics, error reports, or serialized application state. Prefer memory or secure HttpOnly
  same-site cookies according to the approved session architecture.
- Validate same-origin return paths; prohibit open redirects. Clear sensitive in-memory state and
  cached queries at logout, expiry, tenant/session change, and authorization loss.
- Render all server text as escaped text. No `dangerouslySetInnerHTML`, dynamic script execution,
  or untrusted URL navigation. Establish CSP expectations (`default-src 'self'`, restrictive
  script/connect/frame ancestors) through the later deployment authority.
- Assess CSRF after the session transport is selected: bearer-header flows require origin/XSS
  controls; cookie flows require SameSite plus CSRF token/origin validation for mutations.
- Use `Cache-Control: no-store` expectations for protected responses and prevent service-worker or
  application caches from retaining complete responses/evidence.
- Never accept tenant, privilege, scope, role, AuthorityContext, checkpoint, or authorization
  reference from user-editable form state.
- Redact diagnostics to stable safe codes. Telemetry may contain correlation ID, route class,
  latency, and safe code only; no token, payload, evidence, authority details, or cross-tenant ID.
- Dependency additions require lockfile review, license/vulnerability assessment, minimal package
  scope, and protected CI checks.

## Disclosure

Evidence and provenance views render only CDD-013-permitted references. They do not fetch capability
records directly, expose opaque handoffs, or persist full responses. A server `403/404` replaces
stale client visibility immediately and reveals no cross-tenant existence.

## Governing resolution

BSP-001 v1.0 freezes login, token transport/storage, renewal, logout, redirects, CSRF, caching, and
public client configuration. IDP-001 remains the resource-server validation authority.
