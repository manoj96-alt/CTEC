# CDD-029 — Information-Element-Context Keycloak Scope Defect Authorization

Version: 1.0
Status: APPROVED FOR DEFECT IMPLEMENTATION
Lineage: Baseline `2a18eec6bdba3dadd20eb60bd3fc20db2929d513` (CDD-034 implementation merge)
Precedent: `CDD-012-CDD-014-Replay-Frontend-Defect-Authorization.md`

## Purpose

This post-freeze authorization permits the minimum Keycloak realm correction needed to make the
already-frozen, already-implemented `information-element-context:read` scope (CDD-029 §10) actually
issuable to the `ctec-frontend` client under this repository's own shipped Keycloak realm
configuration. It does not alter Gate O's semantics, authority, request/response contract, HTTP
mapping, tenant isolation, or any other frozen CDD-029 decision. It does not alter Gate X code or
the Context Explorer workspace in any way.

## Root-cause record (binding, factual)

CDD-029 correctly freezes the backend scope literal `information-element-context:read` (§10). The
live backend route (`backend/app/api/information_element_context/router.py`) correctly requires that
scope before Blueprint resolution, Gate I, or H4 ever execute. The live Context Explorer frontend
(`frontend/app/context/page.tsx` → `frontend/app/context/_components/context-lookup.tsx` →
`frontend/lib/context/api-client.ts`) correctly obtains a real bearer token and sends it to the live
Gate O endpoint. None of this requires correction.

The Gate O Artifact Authorization (`CDD-029-...-Artifact-Authorization.md`) §4 states:
`keycloak/ctec-realm.json` must remain unchanged — direct inspection confirms Gate M's own three new
scope literals (`ontology-modeling:propose/approve/publish`) were introduced without any realm-file
change, and production `OidcJwtVerifier` trusts validated token scopes without consulting this file
at runtime.

That reasoning is correct as far as it goes but materially incomplete. `OidcJwtVerifier`
(`backend/app/api/supplier_risk/authentication.py`) genuinely never reads `keycloak/ctec-realm.json`
— it validates a token's signature/issuer/audience against a real JWKS endpoint and trusts whatever
scope claims a validly-signed token carries. However, this repository's own `docker-compose.yml`
provisions its Keycloak service with `start-dev --import-realm`, mounting
`./keycloak/ctec-realm.json` as the sole realm-import source. That file therefore *is* the
authoritative source of which scopes the repository's own shipped Keycloak server can ever mint into
a token for `ctec-frontend`. The Gate O AA's own analysis conflated "the backend verifier does not
need this file" with "the realm configuration does not need this file" — only the first claim is
true. The implementation correctly followed the frozen AA's own instruction; the authorization
analysis at Gate O's own publication time was incomplete. This document corrects the record without
rewriting it: CDD-029 and the Gate O Artifact Authorization remain byte-identical, unedited, and
otherwise fully binding.

## Product impact (binding, factual)

`information-element-context:read` is absent from `keycloak/ctec-realm.json`'s `clientScopes` array
and from `ctec-frontend`'s `defaultClientScopes`/`optionalClientScopes` arrays. Under this
repository's own shipped realm configuration, no token issued to `ctec-frontend` can ever carry this
scope. Every authenticated Context Explorer lookup therefore receives HTTP 403 against the shipped
configuration. This is an authorization *provisioning/configuration* failure — not an authentication
failure, not a backend semantic failure, not a frontend semantic failure, and not a security
weakening: the system fails closed, and no unauthorized access is possible as a result of this
defect. Before the future repair described below, Gate X's Context Explorer `SUPPORTED_NOW` status is
not mechanically defensible against the shipped realm configuration. This document does not change
Gate X code or its status; it records the condition under which the existing status becomes
mechanically defensible once the future two-file repair (below) is implemented.

## Narrow supersession (binding — exact scope, nothing else)

This document supersedes **solely** the following clause of the Gate O Artifact Authorization §4:

> `keycloak/ctec-realm.json` must remain unchanged

and **solely** to the extent of authorizing the two-file correction in the "Exact changed-path
authorization" table below. No other clause of the Gate O Artifact Authorization is superseded,
reopened, or reinterpreted. `backend/app/core/dependency_container.py` remains unchanged and its own
"must remain unchanged" clause remains fully binding. `backend/app/tests/conftest.py` remains
unchanged and its own "must remain unchanged" clause remains fully binding. CDD-029 itself is not
amended in any way — it never contained the superseded clause; only the Gate O Artifact
Authorization did.

## Exact changed-path authorization

| Path | Operation | Governing authority | Purpose | Prohibited changes | Required validation |
|---|---|---|---|---|---|
| `keycloak/ctec-realm.json` | MODIFY | This authorization (narrowly superseding Gate O AA §4, above) | Register `information-element-context:read` as one `clientScopes` object and assign it to `ctec-frontend.defaultClientScopes`, mirroring the existing `entity-resolution:read`/`information-element-evidence-fitness:read` pattern exactly. | No modification to `ontology-modeling:propose/approve/publish` or any other existing scope; no modification to `optionalClientScopes`; no modification to any client other than `ctec-frontend`; no wildcard scope; no change to authentication mechanics, issuer, audience, PKCE/OIDC flow, or session behavior. | Focused Keycloak-realm structural tests (below), full backend test suite, `docker compose config --quiet`. |
| `backend/app/tests/test_information_element_context_router.py` | MODIFY | This authorization | Add one narrowly-scoped regression test that parses the real realm JSON and structurally proves both: (1) `information-element-context:read` exists in `clientScopes`, and (2) it is assigned to `ctec-frontend.defaultClientScopes` — mirroring `test_gate_f_api_security.py::test_keycloak_demo_persona_has_both_gate_f_scopes`'s exact structural-parsing approach, not a string search. | No modification to any existing test in this file; no new test file; no modification to Gate O runtime behavior; no weakened or skipped assertion. | Full router test file execution; full backend suite. |

`backend/app/tests/test_runtime_architecture.py` requires **no modification**: both
`keycloak/ctec-realm.json` and `backend/app/tests/test_information_element_context_router.py` are
already members of the existing `AUTHORIZED_CHANGED_PATHS` exhaustive changed-path allowlist
(registered during Gate O's own original implementation), so the future implementation surface
remains mechanically bounded to exactly the two paths above. If fresh verification at
implementation time contradicts this, implementation must STOP and return to Product Owner rather
than silently registering a third path.

All other paths are READ-ONLY under this authorization. No wildcard, directory-level,
implicit-descendant, or alternate-path authorization is granted. In particular, **not authorized**:
any change to `ontology-modeling:propose`, `ontology-modeling:approve`, or `ontology-modeling:publish`
registration (see GAP-11 audit note, below); any backend production-code file; any frontend file; any
migration; any change to Gate X code or status presentation.

## GAP-11 audit note (informational only — not authorized)

During discovery (A13), the identical root cause described above was found to also affect Gate M's
`ontology-modeling:propose`, `ontology-modeling:approve`, and `ontology-modeling:publish` scopes,
which are likewise absent from `keycloak/ctec-realm.json`. This is recorded here as **GAP-11 — Gate M
Ontology Modeling Keycloak Scope Registration — OPEN / DEFERRED**, pending its own separate,
independently governed decision. This document does not authorize, imply authorization for, or
otherwise touch any Gate M scope, file, or governance artifact.

## Broader backlog preserved (informational only — not authorized)

GAP-2 (Gate R, Governed Tool Execution, MISSING), GAP-3 (Gate S, Durable Human Approval, MISSING),
GAP-4 (Gate V, Governed Agent Execution, MISSING), GAP-5 (Gate W, production API
expansion/versioning/management, MISSING/UNDERSPECIFIED), GAP-6 (Generalized Data Quality, MISSING),
GAP-7 (Gate F ↔ H–U runtime bridge, MISSING, requires orchestration-layer design first), GAP-8
(Evidence Fitness frontend exposure, DISCONNECTED), GAP-9 (Simulation execution, service exists /
API+UX MISSING), GAP-10 (Governed MCP execution, MISSING, dependent on Gate R), GAP-11 (above). None
of these is authorized, begun, or otherwise affected by this document.

## Auth-firewall restatement (binding)

The future correction authorized above makes an already-required, already-frozen scope issuable. It
does not remove or weaken the requirement for it. Explicitly, the future implementation must not:
remove or bypass `_authorize`; make the Gate O endpoint unauthenticated or public; introduce a
wildcard scope; broaden any client's permissions beyond the one named scope on `ctec-frontend`;
change token validation, issuer, audience, PKCE, or OIDC-flow behavior; change session behavior;
change backend authorization semantics; or perform any unrelated Keycloak cleanup.

## Publication sequence

This authorization and its two-file implementation allowlist must be reviewed and published before
any implementation PR touching `keycloak/ctec-realm.json` or
`backend/app/tests/test_information_element_context_router.py`. The implementation PR must contain
no governance-file change and must validate against exactly the two-file allowlist above.

## Architecture release impact

This record is implementation authorization associated with frozen CDD-029 and does not itself
introduce a new architecture artifact or dependency. `scripts/verify_architecture_release.py` is
expected to pass unchanged against this publication.
