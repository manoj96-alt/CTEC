# CDD-028 — Governed Visual Ontology Modeling Keycloak Scope Defect Authorization

Version: 1.0
Status: APPROVED FOR DEFECT IMPLEMENTATION
Precedent: `CDD-029-Information-Element-Context-Keycloak-Scope-Defect-Authorization.md`

## Purpose

This post-freeze authorization permits the minimum Keycloak realm correction needed to make the
already-frozen, already-implemented `ontology-modeling:propose`, `ontology-modeling:approve`, and
`ontology-modeling:publish` scopes (CDD-028 §14) definable and assignable through this repository's
shipped Keycloak realm configuration. It does not alter Gate M's semantics, authority, proposal/
approval/publication workflow, state machine, independent-authorization-boundary design, or any other
frozen CDD-028 decision. It does not alter which identity actually receives these scopes today.

## Root-cause record (binding, factual)

CDD-028 §14 correctly defines, and the backend (`backend/app/api/ontology_modeling/router.py`)
correctly enforces, three scopes: `ontology-modeling:propose` (MODEL/SUBMIT), `ontology-modeling
:approve` (governing both APPROVE and REJECT, per CDD-028 §14's own explicit design), and
`ontology-modeling:publish` (independently checked, never implied by `:approve`). None of this
requires correction.

The Gate M Artifact Authorization explicitly and repeatedly excluded Keycloak/auth configuration from
its own implementation surface: "No Keycloak/auth-configuration file change"; "This Artifact
Authorization does not create, modify, or configure any Keycloak realm, client, or role — scope
literals are referenced in application code only... never real Keycloak configuration"; "no
Keycloak/auth-config file touched" (P0 acceptance criterion); "does not authorize... any Keycloak/
auth-configuration change." Unlike the analogous Gate O defect (POST-U/X-DEBT-6), this was not an
incomplete analytical claim — it was a deliberate scoping decision deferring realm wiring to a future
phase. As a result, the shipped realm's `clientScopes` array contains none of these three scope
literals, so no token issued by this repository's own shipped Keycloak realm can ever carry them. The
backend therefore enforces scopes the shipped identity provider cannot issue. This is an identity-
provider provisioning incompleteness, not an authorization bypass, and it fails closed: it makes access
stricter than intended, never more permissive. CDD-028 and the Gate M Artifact Authorization remain
byte-identical, unedited, and otherwise fully binding.

## Product impact (binding, factual)

Today, no caller — including the existing demo persona — can be issued any of these three scopes by
the shipped realm, regardless of what is requested. This authorization corrects only the realm-side
*registrability* of these scopes; it does not, by itself, cause any identity to receive them (see
GAP-11-FOLLOWUP-1, below).

## Narrow supersession (binding — exact scope, nothing else)

This document supersedes **solely** the Gate M Artifact Authorization's Keycloak-exclusion clauses
listed above, and **solely** to the extent of authorizing the two-file correction in the "Exact
changed-path authorization" table below. No other clause of the Gate M Artifact Authorization is
superseded, reopened, or reinterpreted. CDD-028 itself is not amended in any way — it never contained
the superseded clauses; only the Artifact Authorization did.

## Exact changed-path authorization

| Path | Operation | Governing authority | Purpose | Prohibited changes | Required validation |
|---|---|---|---|---|---|
| `keycloak/ctec-realm.json` | MODIFY | This authorization (narrowly superseding the Gate M AA's Keycloak-exclusion clauses, above) | Register `ontology-modeling:propose`, `ontology-modeling:approve`, and `ontology-modeling:publish` as three `clientScopes` objects, and assign all three to `ctec-frontend.optionalClientScopes`. | No modification to `defaultClientScopes`; no modification to any other existing scope, client, user, role, or group; no new Keycloak client; no wildcard scope. | Full realm-JSON structural validation (below), full backend test suite, `docker compose config --quiet`. |
| `backend/app/tests/test_ontology_modeling_router.py` | MODIFY | This authorization | Add one narrowly-scoped regression test that parses the real realm JSON and structurally proves: (1) all three scopes exist in `clientScopes`; (2) all three are assigned to `ctec-frontend.optionalClientScopes`; (3) none of the three is assigned to `ctec-frontend.defaultClientScopes`. | No modification to any existing test in this file; no new test file; no modification to Gate M runtime behavior; no weakened or skipped assertion. | Full router test file execution; full backend suite. |

`backend/app/tests/test_runtime_architecture.py` requires **no modification**: both
`keycloak/ctec-realm.json` and `backend/app/tests/test_ontology_modeling_router.py` are already
members of the existing `AUTHORIZED_CHANGED_PATHS` exhaustive changed-path allowlist. If fresh
verification at implementation time contradicts this, implementation must STOP and return to Product
Owner rather than silently registering a third path.

```
AUTHORIZED_NEW    = 0
AUTHORIZED_CHANGE = 2
TOTAL IMPLEMENTATION SURFACE = 2
```

All other paths are READ-ONLY under this authorization. In particular, **not authorized**: any change
to `frontend/lib/auth/config.ts` or any other frontend file; any change to the frontend's requested
OIDC scope string; any assignment of these scopes to `defaultClientScopes`; any new/modified Keycloak
user, role, or group; any backend production-code, router, application-service, persistence, or
migration change; any change to Gate M's proposal/approval/rejection/publication semantics or its
independent-authorization-boundary design.

## Default-scope firewall (binding, load-bearing)

`ctec-frontend.defaultClientScopes` MUST remain byte-for-byte unchanged by this authorization. None of
`ontology-modeling:propose`, `ontology-modeling:approve`, or `ontology-modeling:publish` may ever be
added to it under this document. Automatically placing all three consequential Gate M scopes in
`ctec-frontend.defaultClientScopes` would co-grant proposal, approval, and publication authorities to
the current frontend identity by default. This Defect Authorization intentionally avoids making that
additional persona/authority-allocation decision. Any future decision about which persona should
receive or request each authority belongs to GAP-11-FOLLOWUP-1, below.

## GAP-11-FOLLOWUP-1 (informational only — not authorized, not repaired)

After this authorization's future implementation, the three scopes will exist in the realm and will be
assignable/requestable, but will **not** be automatically granted to any identity. The existing demo
persona's OIDC scope request (`frontend/lib/auth/config.ts`) does not request any optional scope today,
so it will continue receiving `403 AUTHORIZATION_SCOPE_REQUIRED` for every Gate M consequential
action — exactly mirroring the already-accepted status quo for `entity-resolution:decide` and
`supplier-risk:submit/retry/replay`. This is recorded here as **GAP-11-FOLLOWUP-1 — Deferred
Authorization/Persona-Integration Follow-up**, explicitly out of scope for this document. It is not a
security defect classification. Its future resolution requires independent discovery/governance
addressing: intended Gate M personas; proposer/approver/publisher authority allocation; separation of
duties; whether optional scopes should be requested dynamically per-workspace; whether distinct
personas/roles are required; and whether the demo environment should intentionally continue
demonstrating `403` for unauthorized consequential actions. This document does not authorize, imply
authorization for, or otherwise touch any part of that future work.

## Cross-gate firewall (restated)

This document does not touch or authorize: GAP-8; Gate R; Gate S; Gate V; Gate W; generalized Data
Quality; Simulation execution; MCP execution; any Gate F↔H-U composition; POST-U/X-DEBT-6 (remains
RESOLVED/CLOSED, not reopened); CDD-034 behavior; Evidence Fitness frontend exposure.

## Validation / acceptance contract

Before this future implementation may be accepted: (1) exact 2-file diff, CREATE=0/MODIFY=2/DELETE=0;
(2) all three scope definitions exist exactly once each in `clientScopes`; (3) all three exist exactly
once each in `optionalClientScopes`; (4) all three occur zero times in `defaultClientScopes`; (5)
every pre-existing `optionalClientScopes` entry remains intact; (6) `defaultClientScopes` remains
byte-identical to its pre-implementation state; (7) no existing scope renamed or removed; (8) no
unrelated client/user/role/group modified; (9) the new realm-structural regression test passes; (10)
every existing Gate M router test passes unmodified; (11) `test_runtime_architecture.py`'s existing
tests pass with zero modification to that file; (12) full backend suite passes; (13) `docker compose
config --quiet` passes; (14) `scripts/verify_architecture_release.py` passes; (15) CDD-028, the Gate M
Artifact Authorization, and every other tracked frozen governance document remain byte-identical; (16)
exact-head CI passes before merge; (17) post-merge CI passes; (18) post-merge realm structure is
independently reverified against the same 5-point assertion above.

## Publication / implementation boundary

**Publication/freeze of this document does NOT itself authorize implementation.** A separate,
subsequent Product Owner implementation authorization is required before either file above may be
modified — matching every prior gate's identical multi-step discipline in this lineage, including
POST-U/X-DEBT-6's own.

## Authorization

This Defect Authorization is approved for publication, reached via GAP-11 R0 (discovery) → R1
(drafting, Product Owner decisions GAP-11-D1/GAP-11-D2) → this R2 publication turn, incorporating the
Product Owner's mandatory wording refinement to the default-scope firewall. CDD-028 and the Gate M
Artifact Authorization remain FROZEN and PUBLISHED, unchanged by this approval.
