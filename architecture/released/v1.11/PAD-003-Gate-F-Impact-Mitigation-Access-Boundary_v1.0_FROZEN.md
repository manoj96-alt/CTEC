# PAD-003 v1.0 — Gate F Impact & Mitigation Access Boundary

Version: 1.0
Status: FROZEN
Current: YES
Authority: AUTHORITATIVE
Approval: Product Owner authorization, Gate F (v1.11)

## 0. Purpose

Gate F F1 Architecture Decision Analysis (Decision 3) found that no existing
scope covers Gate F's read surface: `supplier-risk:read` is scoped to PAS-001
assessment submission/execution/evidence, a different resource, and PAD-002's
canonical scope set (`supplier-risk:read`, `entity-resolution:read`,
`entity-resolution:decide`, `ontology-copilot:ask`) contains nothing
applicable. The Product Owner's Gate F F1 Decision 3 approved exactly **one**
new read scope, capability-oriented, with the final name left to this PAD.
This PAD names that scope and defines its boundary. It introduces no
approval, execution, or administration authority of any kind.

## 1. Context

PAD-002 §10 ("Canonical scope contract — DECISION E-05") establishes that
CTEC's scope names are colon-delimited and authoritative, and states they
"SHALL NOT be renamed to fit Keycloak's own naming conventions"
(`PAD-002-..._FROZEN.md:197-198`). That is a renaming prohibition, not a
prohibition on adding new scopes — PAD-002 itself is the precedent vehicle
for scope-contract changes (it added the current four scopes on top of
IDP-001/BSP-001/PAS-001's prior authority), and this PAD follows that same
pattern for Gate F.

## 2. Scope name — FINAL

**`supply-chain-impact:read`**

Rationale: capability-oriented (names the business capability — "Supply
Chain Impact" — not an implementation detail), colon-delimited consistent
with the existing four canonical scopes, and structurally distinct from
`supplier-risk:read` (a different resource — see §5). This literal scope
name is FINAL, authorized by the Product Owner as part of this document's
publication (§14) — it is no longer a recommendation.

## 3. Product-access boundary

`supply-chain-impact:read` authorizes read access to Gate F's governed
output surface only:

- Dependency-chain / impact-path results (Supplier → Material → Product/BOM
  → Facility)
- Revenue exposure associated with the affected business context
- Alternate-supplier evaluation results (qualification, capacity, lead time,
  cost)
- The governed mitigation recommendation (DRM output)
- The `HUMAN_APPROVAL_REQUIRED` governance-standing indicator (GRM output —
  see CDD-015 §14 and Gate F F1 Decision 4)

It authorizes **nothing** else. In particular, per the Product Owner's Gate F
scope boundary, it MUST NOT be interpreted or implemented to authorize:

- approval, rejection, or conditional approval of a recommendation
- any execution action (ERP write-back, sourcing execution, purchase-order
  creation, contract amendment, supplier activation)
- entity-resolution decision authority (that remains `entity-resolution:decide`
  exclusively — see §7)
- architecture/governance administration of any kind

## 4. APIs/surfaces requiring this scope

Any new Gate F read API (defined by CDD-015, not this PAD — this PAD
authorizes the boundary, CDD-015 defines the concrete endpoints) that returns
any of the §3 output categories MUST require `supply-chain-impact:read`. This
PAD does not itself create any endpoint.

## 5. Interaction with `supplier-risk:read`

Distinct, non-overlapping resource. `supplier-risk:read` remains scoped to
PAS-001 assessment submission/execution/evidence (CDD-013,
`PAS-001_..._v1.1_FROZEN.md:10-19`) and is unchanged by this PAD. Gate F does
not read or write PAS-001 assessment data, and PAS-001 assessment endpoints
do not require `supply-chain-impact:read`. A caller may legitimately hold
one scope without the other.

## 6. Interaction with Ask CTEC (`ontology-copilot:ask`)

Gate F's dependency-traversal step (Gate F F1 Decision 1, Option-C-refined)
reuses the existing Ask CTEC traversal engine in-process, governed by its own
existing PAD-001 boundary and `ontology-copilot:ask` scope where Ask CTEC is
called directly by a caller. Where Gate F's own governed API composes a
traversal result into its own response (rather than the caller invoking Ask
CTEC directly), the caller authorizes via `supply-chain-impact:read` only —
this PAD does not require a caller to separately hold `ontology-copilot:ask`
to receive Gate F's composed output, following the general CTEC pattern
that a bounded capability's own scope governs its own composed response
(precedent: CDD-011's supplier-risk pipeline does not require its callers to
separately hold ERM/SRM/ASM/KRM/DRM/GRM-internal authority).

## 7. Interaction with `entity-resolution:read` and explicit separation from `entity-resolution:decide`

Gate F reads governed enterprise-entity and relationship data through the
same underlying persistence Entity Resolution and Ask CTEC already read
(`institutional_relationships`, `enterprise_entities`) but does so under its
own `supply-chain-impact:read` scope — it does not require, grant, or imply
`entity-resolution:read`. **Explicit separation, binding**: nothing
authorized by this PAD may be implemented in a way that invokes, requires,
substitutes for, or otherwise crosses into `entity-resolution:decide`'s
authority boundary (`entity_resolution/router.py:170`, a mutating decision
endpoint). Gate F F1 confirmed that returning a `HUMAN_APPROVAL_REQUIRED`
state from a read-scoped endpoint is a governed *fact* about
decision-readiness, not an exercise of decide authority (analogous to DRM's
existing `HumanOverrideService` returning override-eligibility as data,
`decision_engine/service.py:113-117`) — this PAD confirms that boundary
explicitly rather than leaving it implicit.

## 8. TrustedPrincipal / tenant authority

Unchanged from Gate E. Tenant authority for any Gate F read MUST originate
exclusively from `TrustedPrincipal.tenant_id` → `AuthorityContext.organization_id`,
identical to the rule RFC-015 §1 and RFC-016 §2b already establish for every
other tenant-scoped read in this system — never from a client-supplied
request field. This PAD introduces no new tenant-derivation mechanism; it
reuses the existing one without modification.

## 9. Normal demo persona permissions

Per PAD-002 §11's least-privilege demo-persona principle, and because
`supply-chain-impact:read` is a read-only scope with no approval or execution
authority, the normal demo persona SHALL be granted
`supply-chain-impact:read`, on the same reasoning PAD-002 already applied to
grant the demo persona `supplier-risk:read`, `entity-resolution:read`, and
`ontology-copilot:ask` but withhold `entity-resolution:decide`. This
architectural decision is final as of this document's authorization (§14);
actual identity-provider grant provisioning (e.g., Keycloak configuration)
remains Gate F implementation-time work, not authorized by this document.

## 10. Forbidden approval/execution behavior

Binding, restated from the Product Owner's Gate F F1 Decision 4 and Gate F
business boundary: no scope authorized by this PAD, now or by future
amendment without a new PAD, may gate an approve, reject, conditionally
approve, execute, or any other mutating operational action. Gate F stops at
`HUMAN_APPROVAL_REQUIRED`. Any future capability that implements human
approval, execution, or workflow requires its own, separately authorized PAD
— it is explicitly out of scope here and this PAD's scope MUST NOT be
silently reinterpreted to cover it later.

## 11. Frontend authentication expectations

Unchanged from Gate E. Any production Gate F frontend surface authenticates
through the existing OIDC session-establishment flow (Authorization Code +
PKCE S256) PAD-002 already governs; no new authentication mechanism is
introduced. The existing, non-authoritative `/demo/supplier-risk` behavioral
prototype remains explicitly out of this PAD's scope (F0 §4, F1 §19) — it
performs no authenticated backend calls today and this PAD does not change
that; wiring it directly to a governed API is a CDD-015/implementation-time
decision, not authorized here.

## 12. Logout / reauthentication inheritance from Gate E

Unchanged from Gate E. `supply-chain-impact:read`-gated endpoints inherit
Gate E's existing session-lifecycle behavior in full: RP-initiated logout,
local session termination, Keycloak SSO termination, and the requirement
that protected actions re-require authentication after logout apply to any
Gate F endpoint exactly as they already apply to `supplier-risk:read`- and
`entity-resolution:read`-gated endpoints. This PAD defines no new
session-lifecycle behavior.

## 13. Non-claims

This PAD does not authorize any endpoint, persistence change, ontology
vocabulary (see RFC-017), decision/recommendation logic, or frontend
implementation. It does not modify `supplier-risk:read`, `entity-resolution:read`,
`entity-resolution:decide`, or `ontology-copilot:ask` in any way. It does not
introduce any approval, execution, or administration scope. It authorizes
exactly one new read scope (§2) and its boundary (§3).

## 14. Authorization

Authorized by CTEC Product Owner Manoj Nair on 2026-08-18: the
`supply-chain-impact:read` scope and its access boundary (§2-§10), final and
not merely recommended, following Gate F F0 through F3 architecture review
and the Gate F F3 release-candidate consistency and dependency verification
(see the architecture/released/v1.11/ Architecture Consistency Report); and
this document's publication to FROZEN/AUTHORITATIVE governance state as part
of architecture baseline v1.11 (this authorization).
