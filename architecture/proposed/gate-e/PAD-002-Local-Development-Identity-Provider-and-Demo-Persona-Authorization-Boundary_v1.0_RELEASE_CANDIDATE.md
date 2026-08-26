# PAD-002 v1.0 — Local Development Identity Provider and Demo Persona Authorization Boundary

Version: 1.0 DRAFT
Status: RELEASE CANDIDATE — PENDING PRODUCT OWNER AUTHORIZATION
Current: NO
Authority: NON-AUTHORITATIVE — PENDING REGISTRY PUBLICATION

## 0. Purpose

This clarification freezes how CTEC's already-authoritative, provider-neutral
OIDC/JWKS authentication architecture (`app.api.supplier_risk.authentication`)
is realized in a local/demo runtime, where no real external identity provider
has ever been provisioned. It resolves the Gate E blocker discovered while
attempting end-to-end browser acceptance of Priority 6 ("Ask CTEC"): the local
`.env`/`.env.example` OIDC values are the literal placeholder
`https://identity.example.com/`, which cannot resolve, cannot issue tokens,
and therefore cannot be signed in against.

This document defines no new canonical entity, attribute, relationship,
Protocol Version, or business semantics, and changes no existing one. It does
not touch `institutional_relationships`, `enterprise_entities`, RFC-015,
RFC-016, or either PAD-001 (the Product Access Protocol Specification or its
Gate D1 Clarification). It is infrastructure/operational governance: it states
which local identity provider CTEC's local/demo environment targets, how
trust is established between that provider and the existing backend verifier
without any code change to the verifier, and what the minimal-privilege demo
persona is authorized to do.

## 1. Context / problem

Gate D delivered a fully implemented, fully tested Ask CTEC capability
(`POST /api/v1/ontology-copilot/ask`), verified end-to-end at the HTTP/database
layer. Attempting the final manual browser acceptance step exposed that no
local identity provider has ever existed for this repository: `.env` is a
byte-for-byte copy of `.env.example`'s OIDC section, every OIDC value in both
files is the reserved-domain placeholder `identity.example.com`, and clicking
"Sign in" fails silently (an unhandled promise rejection from a DNS resolution
failure during OIDC discovery, with no `.catch()` anywhere in the call chain).

A separate, independently confirmed defect compounds this: `NEXT_PUBLIC_OIDC_SCOPE`
is absent from `docker-compose.yml`'s frontend build args entirely, so
`frontend/Dockerfile`'s own stale hardcoded default
(`"openid profile supplier-risk:read"`) always wins over the correct,
currently-committed default in `frontend/lib/auth/config.ts`
(which already includes `entity-resolution:read entity-resolution:decide
ontology-copilot:ask`). Even once a real IdP exists, the browser would request
too narrow a scope set until this wiring is also fixed.

## 2. Existing provider-neutral authentication baseline (unchanged)

`OidcJwtVerifier` (`backend/app/api/supplier_risk/authentication.py`) is
explicitly documented as "provider-neutral OIDC/JWKS bearer-token
verification." It validates, per request: RS256 (or configured algorithm)
signature via live JWKS fetch (`PyJWKClient`), `iss` exact match against
`CTEC_OIDC_ISSUER`, `aud` exact match against `CTEC_OIDC_AUDIENCE`, presence
of `exp`/`nbf`/configured subject claim, and extracts `TrustedPrincipal`
fields from configurable claim names (`CTEC_OIDC_SUBJECT_CLAIM`,
`CTEC_OIDC_TENANT_CLAIM`, `CTEC_OIDC_SCOPE_CLAIM`, `CTEC_OIDC_ROLES_CLAIM`).
This mechanism is not modified, extended, weakened, or bypassed by this
document or by anything it authorizes.

This backend contract is itself governed by the existing FROZEN, AUTHORITATIVE
`IDP-001` ("Provider-Neutral OIDC Identity Validation Contract," v1.0,
`architecture/released/v1.4/`), which establishes that deployment
configuration — not any caller — exclusively owns issuer, audience,
discovery/JWKS endpoint, algorithm allowlist, and subject/tenant/scope/role
claim names, and that unavailable discovery/keys fail closed. Every
requirement this document places on local Keycloak configuration (§7–§10) is
a configuration of IDP-001's existing contract, not an amendment to it.

The browser-side counterpart, `BSP-001` ("Supplier Risk Browser
Authentication and Session Profile," v1.0, `architecture/released/v1.6/`),
normatively governs `CDD-014` — registered in `architecture/INDEX.md` as
"CDD-014 Supplier Risk Business Workflow and User Experience" — and every
BSP-001 "SHALL" requirement (Authorization Code + PKCE S256, memory-only
token storage, exact redirect-URI matching, multi-tab broadcast logout,
fail-closed network/provider failure) is stated in terms of CDD-014
specifically, including in its closing Validation section. `frontend/lib/auth/browser-session.ts`
already implements this same behavior and is shared, unchanged, by Entity
Resolution and Ask CTEC.

This document does not supersede, rewrite, or contradict BSP-001. BSP-001's
own normative scope is CDD-014 (Supplier Risk); it does not, by its own
text, extend its "SHALL" obligations to Entity Resolution or Ask CTEC. This
document addresses the Gate E local/demo identity-provider and
least-privilege authorization requirements for capabilities — Entity
Resolution and Ask CTEC — that share BSP-001's underlying browser
authentication/session substrate without falling within BSP-001's own
registered scope. Where this document's requirements overlap BSP-001's
existing behavior (PKCE S256, memory-only token storage, fail-closed
failure handling), they restate, not alter, that behavior; see §23 for full
traceability.

## 3. Decision: Keycloak as local/demo reference identity provider

CTEC's local/demo runtime SHALL use Keycloak as its reference OIDC identity
provider, provisioned declaratively (§12) inside `docker-compose.yml`. This
decision is scoped strictly to local development and demo environments.

## 4. Explicit production non-decision

This document makes no statement, recommendation, or commitment regarding
CTEC's production identity provider. Keycloak is NOT mandated, endorsed, or
implied as a production choice. `OidcJwtVerifier`'s provider-neutral design is
precisely what makes this possible: a production deployment may point
`CTEC_OIDC_ISSUER`/`CTEC_OIDC_AUDIENCE`/`CTEC_OIDC_JWKS_URL` at any
standards-compliant OIDC provider without any backend source change. Any
future production IdP selection is a separate decision, out of scope here.

## 5. Trust boundaries

Three independent trust boundaries exist and remain independent under this
design:

1. **Browser ↔ Keycloak** — unauthenticated until the user completes login;
   Keycloak is the sole authority over credential verification and token
   issuance.
2. **Browser ↔ CTEC backend** — a bearer token is the only credential
   presented; the backend trusts nothing about its claims until independent
   cryptographic and claim verification succeeds (§2). No shared secret
   exists between frontend and backend.
3. **CTEC backend ↔ PostgreSQL** — unaffected by this document; RFC-015/RFC-016
   tenant-ownership invariants remain the sole isolation mechanism at the data
   layer, downstream of and independent from authentication.

The frontend is, and remains, an OAuth **public client**: no client secret is
issued to it, none is stored in it, and none is required by the Authorization
Code + PKCE flow.

## 6. Authorization Code + PKCE flow (unchanged, confirmed compatible)

The browser SHALL continue to use `oidc-client-ts`'s `UserManager` with
`response_type: "code"`. PKCE (S256) is `oidc-client-ts@^3.5.0`'s default,
mandatory behavior for the authorization code flow in this codebase (no
`disablePKCE` flag is set anywhere) and requires no code change. Keycloak
natively supports Authorization Code + PKCE (S256) for public clients. This
document requires the Keycloak client `ctec-frontend` be configured as
`publicClient: true`, `standardFlowEnabled: true`, PKCE method `S256`.

## 7. Issuer/JWKS local networking model — DECISION E-01

The canonical issuer, embedded in every token's `iss` claim and validated by
the backend, is fixed as:

    http://localhost:8081/realms/CTEC

The browser's configured OIDC authority SHALL be identical:

    NEXT_PUBLIC_OIDC_AUTHORITY=http://localhost:8081/realms/CTEC

The backend's issuer validation SHALL be identical:

    CTEC_OIDC_ISSUER=http://localhost:8081/realms/CTEC

The backend's JWKS retrieval (`CTEC_OIDC_JWKS_URL`) MAY use a
Docker-host-reachable transport address, for example
`http://host.docker.internal:8081/realms/CTEC/protocol/openid-connect/certs`,
strictly as a network path for fetching the public signing keys — this value
never participates in `iss` comparison and carries no trust weight of its own.

The binding invariant, which implementation MUST preserve regardless of the
exact Keycloak environment-variable mechanism used to achieve it, is:

    browser-visible issuer == JWT "iss" claim == CTEC_OIDC_ISSUER

Implementation MUST empirically verify the exact hostname/issuer
environment-variable semantics (e.g. `KC_HOSTNAME`, `KC_HOSTNAME_PORT`, or
successor settings) for the specific Keycloak image/version selected, rather
than assuming behavior from documentation of a different version. JWKS
retrieval using a host-internal transport address MUST NOT weaken signature
verification, MUST NOT introduce `--net=host` or equivalent host networking,
and MUST NOT introduce any authentication bypass.

## 8. `tenant_id` claim contract

`tenant_id` is not a native Keycloak claim. It SHALL be sourced from a
Keycloak user attribute named `tenant_id`, propagated into the issued token
via a declaratively configured protocol mapper (realm-JSON, §12) — never via
backend source code, never via a request body or query parameter. The demo
user's `tenant_id` attribute SHALL be exactly `ctec-demo-tenant`, matching the
tenant already seeded by `DemoOntologyCopilotSeeder` (Gate D) and validated by
RFC-016's tenant-ownership invariant at the persistence layer. This
reaffirms, without modifying, the existing principle: tenant identity for
every request originates exclusively from a trusted, signed claim.

## 9. Audience contract

Keycloak does not emit an `aud` claim matching a custom client by default. A
declaratively configured Keycloak audience protocol mapper (§12) SHALL ensure
every issued token carries `aud` equal to the existing, already-configured
`CTEC_OIDC_AUDIENCE` value (`ctec-supplier-risk-api`), requiring no change to
that backend setting.

## 10. Canonical scope contract — DECISION E-05

CTEC's existing colon-delimited scope names are authoritative and SHALL NOT
be renamed to fit Keycloak's own naming conventions:

    supplier-risk:read
    supplier-risk:submit
    supplier-risk:retry
    supplier-risk:replay
    entity-resolution:read
    entity-resolution:decide
    ontology-copilot:ask

Implementation MUST empirically verify that the selected Keycloak version
accepts colon-delimited client scope names before relying on this contract at
the provisioning layer (§12). If the selected version rejects such names, the
resulting conflict is a stop condition requiring governance return, not a
license to rename CTEC's scopes.

## 11. Least-privilege demo persona

The initial business-user demo persona is authorized for exactly:

    supplier-risk:read
    entity-resolution:read
    ontology-copilot:ask

`entity-resolution:decide`, `supplier-risk:submit`, `supplier-risk:retry`, and
`supplier-risk:replay` are explicitly NOT granted to this persona. These
require independent, future persona/use-case justification and are out of
scope for Gate E. The frontend does not, and under this document continues
not to, gate any UI element by token scope (confirmed: no scope-conditional
rendering exists anywhere in the Entity Resolution or Supplier Risk
workspaces today) — the backend's existing `_authorize()` 403 response remains
the sole enforcement point. A demo user attempting a decide/submit/retry/replay
action is expected to receive `403 AUTHORIZATION_SCOPE_REQUIRED`; this is
correct security behavior, not a defect, and MUST be reflected in demo
scripting/expectations rather than "fixed" by over-granting scope.

## 12. Declarative provisioning requirements

Local Keycloak provisioning SHALL be fully declarative and version-controlled:
a realm-import JSON (e.g. `keycloak/ctec-realm.json`), imported automatically
at Keycloak container startup via its standard import mechanism. No manual
admin-console configuration step may be required to reach a working local
demo state. The realm import SHALL define: realm `CTEC`; public client
`ctec-frontend` per §6; client scopes per §10; an audience protocol mapper per
§9; a `tenant_id` user-attribute protocol mapper per §8; one demo user with
`tenant_id=ctec-demo-tenant` and the three minimal scopes from §11 assigned as
default (not optional) scopes. The client's registered valid redirect URIs
SHALL include exactly `http://localhost:3000/auth/callback`, and its valid
post-logout redirect URIs SHALL include exactly `http://localhost:3000/`,
matching `NEXT_PUBLIC_OIDC_REDIRECT_URI` and
`NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI` respectively and the existing
`frontend/app/auth/callback/page.tsx` implementation. Implementation MUST verify the chosen Keycloak
version's exact realm-import JSON schema and mapper type names empirically
before finalizing the import file, per the same discipline required in §7.

## 13. Credential-handling requirements — DECISION E-03

No demo-user password may be committed to Git, present in any Dockerfile
instruction, baked into any built image, or given a non-empty default in
`docker-compose.yml`. Any local secret/config file containing the credential
value MUST be gitignored. The stack MUST fail clearly and immediately if the
required credential is absent — mirroring the existing, already-established
`CTEC_RUNTIME_HANDOFF_KEY` pattern ("the stack refuses to start without it").

Preference order for the mechanism, in strict priority order:

1. Declarative Keycloak realm-import environment-variable substitution for
   the demo user's credential (Keycloak's native `${ENV_VAR}` substitution
   inside realm-import JSON, if verified supported and functioning cleanly
   for the selected Keycloak version) — this satisfies every requirement
   above with zero additional bootstrap tooling.
2. Only if (1) is verified unavailable or unclean for the selected version: a
   minimal, deterministic, idempotent bootstrap step (e.g. one `kcadm.sh`
   invocation reading the same required environment variable) — not a
   general-purpose or speculative scripting framework.

Implementation MUST NOT invent a custom bootstrap script if declarative
provisioning satisfies these requirements for the selected Keycloak version.
Which mechanism is actually used is an implementation-time empirical finding,
not a decision this document prejudges.

## 14. Configuration ownership

| Layer | Owns |
|---|---|
| Keycloak realm-import JSON | Client definition, protocol mappers, demo user, scope-to-user assignment (declarative, version-controlled) |
| `.env.example` | Documented shape of every variable *except* `NEXT_PUBLIC_OIDC_SCOPE`, which MUST remain unset in the template so `config.ts`'s default is authoritative by default (§15); other OIDC values use real local-Keycloak-shaped placeholders instead of `identity.example.com` |
| `docker-compose.yml` | Env-to-build-arg / env-to-container wiring only, including the new Keycloak service and the corrected `NEXT_PUBLIC_OIDC_SCOPE` propagation (§15) |
| `frontend/Dockerfile` | Build-arg-to-build-time-`ENV` plumbing only; its currently-stale `NEXT_PUBLIC_OIDC_SCOPE` default must no longer be able to silently win |
| `frontend/lib/auth/config.ts` | The single authoritative application-level scope default (§15) |
| Backend `CTEC_OIDC_*` | Runtime verification configuration; unchanged shape, pointed at the local Keycloak realm |

## 15. `NEXT_PUBLIC_OIDC_SCOPE` single-authority design

There SHALL be exactly one authoritative source for the default browser OIDC
scope request: `frontend/lib/auth/config.ts`'s existing code-level default.
`frontend/Dockerfile`'s competing hardcoded `ARG NEXT_PUBLIC_OIDC_SCOPE`
default MUST be removed or realigned so it can never again silently override
the application code's default, and `docker-compose.yml` MUST propagate
`NEXT_PUBLIC_OIDC_SCOPE` end-to-end from `.env` exactly as its four sibling
`NEXT_PUBLIC_OIDC_*` variables already are. Per §11, `config.ts`'s default
SHALL be narrowed to the least-privilege demo-persona scope set. Real
enforcement of least privilege remains at the Keycloak provisioning layer
(§11, §12) regardless of what the browser requests — a broader client-side
request against a narrowly provisioned Keycloak client/user simply yields a
narrower granted scope, never an escalation.

`.env.example` SHALL NOT set a value for `NEXT_PUBLIC_OIDC_SCOPE` — the line
MUST be omitted or left commented, so that `docker-compose.yml`'s
`${NEXT_PUBLIC_OIDC_SCOPE:-}` substitution evaluates to empty whenever an
operator has not explicitly overridden it, allowing `config.ts`'s code-level
default to apply unopposed. An operator MAY set `NEXT_PUBLIC_OIDC_SCOPE`
explicitly in their own local `.env` to override the default — this is the
one sanctioned override path, not a second competing default.

## 16. Failure behavior (unchanged principles, restated for this context)

- OIDC discovery/redirect failure (e.g. unreachable authority): visible UX
  error, per §17 — no silent failure.
- Expired, invalid-signature, wrong-issuer, or wrong-audience token: existing
  `AuthenticationError` codes, unchanged, resulting in `401`.
- Valid signature, valid issuer/audience, but token missing the `tenant_id`
  claim entirely (e.g. a misconfigured Keycloak protocol mapper): existing
  `AUTH_TENANT_MISSING_OR_AMBIGUOUS` code, unchanged, resulting in `401` —
  distinct from, and in addition to, the wrong-tenant case below.
- Valid token missing a required scope: existing `403
  AUTHORIZATION_SCOPE_REQUIRED`, unchanged.
- Valid token, wrong tenant: existing tenant-scoped query behavior (RFC-016)
  — never cross-tenant data, never a distinguishable "wrong tenant" versus
  "not found" response.

None of this behavior is modified by this document; it is restated here only
to confirm Gate E introduces no new failure mode and weakens none of the
existing ones.

## 17. UX error-surfacing requirement

The shared `signIn()` helper (`frontend/lib/auth/browser-session.ts`) is
used identically by every capability that currently exposes an explicit
sign-in action — confirmed at exactly two call sites,
`entity-resolution-workspace.tsx` and `ask-ctec-workspace.tsx` — currently has
no caller anywhere that attaches a `.catch()` to its returned promise, causing
any discovery/redirect failure to become an unhandled rejection with zero
visible UI change. (Supplier Risk's workspace does not call `signIn()`
directly today; whether and how it triggers authentication is a separate,
pre-existing question this document does not address.) Gate E implementation
SHALL fix this once, systemically, at the shared helper and both existing
call sites — not as an Ask-CTEC-specific patch — and SHALL apply the same
hardening to any new sign-in call site added during Gate E implementation, so
that every authenticated capability's sign-in button surfaces a clear
"sign-in unavailable" error state on failure.

## 18. Session-lifecycle non-goal — DECISION E-04

`automaticSilentRenew: false` is pre-existing, unrelated to Gate E, and SHALL
remain unchanged by this document and its implementation. Access tokens are
held only in an in-memory store (not `localStorage`/`sessionStorage`); a full
browser page reload during an active demo session loses the session and
requires re-authentication. This is a known, accepted demo limitation, to be
documented in demo-runbook material, not remediated under Gate E. Any future
silent-renewal or session-persistence redesign is out of scope here and
requires its own governance pass.

## 19. Security invariants (binding on all Gate E implementation)

- No authentication bypass, in any environment, under any flag or mode.
- No fabricated, unsigned, or hand-constructed JWT accepted by the backend
  under any circumstance.
- No hardcoded bearer token anywhere in source, configuration, or documentation.
- No "dev mode" that skips or weakens authentication.
- No weakening of issuer, audience, or signature verification, for any
  environment, including local/demo.
- No backend confidential credential reused as a frontend/SPA credential.
- The frontend remains an OAuth public client at all times.
- Authorization Code + PKCE (S256) remains mandatory for the SPA.
- `tenant_id` MUST originate exclusively from a trusted, signed token claim.
- The backend remains the sole authoritative enforcement point for tenant
  isolation and scope authorization; frontend scope handling is UX only.
- No historical FROZEN architecture artifact is modified by this document or
  its implementation.

## 20. Acceptance criteria

Gate E implementation is complete only when all of the following hold,
verified by a combination of automated tests (§8 of the prior Gate E
architecture analysis) and manual browser acceptance:

1. User can click "Sign in."
2. Browser redirects to the real local Keycloak instance.
3. User authenticates against Keycloak.
4. Browser returns through `/auth/callback`.
5. Frontend obtains a genuine, Keycloak-signed access token.
6. Backend validates the token's signature via Keycloak's JWKS endpoint.
7. Backend validates `iss` and `aud` per §7 and §9.
8. Backend obtains `tenant_id = ctec-demo-tenant` per §8.
9. The issued token carries only the approved demo-persona scopes (§11),
   verified by decoding the actual token during acceptance, not merely by
   inspecting static Keycloak configuration.
10. Ask CTEC UI can submit "Which products depend on TSMC?"
11. Backend returns the deterministic Gate D answer.
12. The "Why?" evidence renders correctly.
13. A token missing `ontology-copilot:ask` receives `403`.
14. A different tenant cannot access `ctec-demo-tenant` data.
15. Logout works (session cleared, Keycloak end-session redirect, multi-tab
    `BroadcastChannel` signal).
16. OIDC discovery/redirect failures produce visible UX (§17), not silent
    inertness.
17. Existing Supplier Risk and Entity Resolution security behavior is
    unchanged and unregressed.
18. No historical FROZEN architecture artifact changed.
19. Full backend/frontend/container CI passes.
20. Git tree is clean at closure.

## 21. Explicit non-goals

- This is not a production identity-provider selection decision (§4).
- This does not grant any new backend capability, relationship type, or write
  path.
- This does not modify RFC-015, RFC-016, PAD-001 (either the Product Access
  Protocol Specification or its Gate D1 Clarification), or any other
  historical FROZEN artifact.
- This does not redesign session persistence or silent token renewal (§18).
- This does not broaden any existing persona's granted scopes beyond §11's
  least-privilege set; broader grants require separate justification.
- This does not introduce, authorize, or imply any LLM, generic SQL/SPARQL
  generation, or other capability excluded by Gate D's own non-goals.

## 22. Implementation sequence after PAD-002 approval

1. Empirically verify Keycloak hostname/issuer environment-variable semantics
   and realm-import credential-substitution support for the specific image
   tag selected (§7, §12, §13) before finalizing exact environment-variable
   names.
2. Add the Keycloak service and realm-import JSON to `docker-compose.yml`
   (new branch), satisfying §12 and §13.
3. Fix `NEXT_PUBLIC_OIDC_SCOPE` build-arg propagation and align
   `frontend/lib/auth/config.ts`'s default to the least-privilege demo-persona
   scope set (§15).
4. Add the systemic `signIn()` promise-rejection UX hardening across all
   authenticated workspaces (§17).
5. Update `.env.example` with real local-Keycloak-shaped, still-non-secret
   values in place of `identity.example.com`.
6. Implement the test matrix, prioritizing backend integration tests against
   a real disposable Keycloak instance (tenant claim extraction, scope
   authorization, missing-scope rejection, wrong-tenant rejection, invalid
   issuer/audience/signature rejection).
7. Full local rebuild/restart cycle using the same disposable,
   non-destructive container discipline used throughout every prior gate in
   this program, followed by manual browser acceptance against all twenty
   §20 criteria.
8. Stage/commit/push/PR/merge under the same explicit-approval gating used
   for every prior gate.

## 23. Traceability

`app.api.supplier_risk.authentication.OidcJwtVerifier` (provider-neutral OIDC/JWKS
verification, unchanged); `IDP-001` v1.0 (Provider-Neutral OIDC Identity
Validation Contract, `released/v1.4/` — the pre-existing authoritative
contract `OidcJwtVerifier` implements; unaffected and unamended by this
document, see §2); `BSP-001` v1.0 (Supplier Risk Browser Authentication and
Session Profile, `released/v1.6/` — the pre-existing authoritative contract
for `CDD-014`'s browser OIDC/PKCE/session behavior; unaffected and unamended
by this document, which addresses capabilities outside CDD-014's own
registered scope that share the same underlying implementation, see §2);
`frontend/lib/auth/browser-session.ts` and
`frontend/lib/auth/config.ts` (unchanged flow, corrected configuration);
RFC-015 v1.0; RFC-016 v1.0 (tenant-ownership invariants, unaffected); PAD-001
v1.5 (Product Access Protocol Specification, unaffected — Gate E introduces no
Cognitive Engine invocation and is out of that document's scope entirely);
PAD-001 v1.0 Gate D1 Clarification ("Product-Internal Deterministic Capability
Boundary Clarification," unaffected); `docs/entity-resolution-steward.md`
§"OIDC prerequisites" (documents the pre-existing scope-default contract this
clarification narrows for the demo persona); `DEMO_RUNBOOK.md` (documents the
pre-existing "no baked-in default" OIDC design this clarification realizes
locally for the first time).

## 24. Authorization

Submitted for Product Owner review. Decisions E-01 through E-05 and the
least-privilege primary demo persona, as reflected in §7, §10, §11, §13, and
§18 respectively, were approved prior to drafting this document. This
document's text itself is pending explicit authorization before registry
publication.
