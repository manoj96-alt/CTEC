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
applicable. The Product Owner's Gate F F1 Decision 3 approved exactly one
new read scope, capability-oriented, with the final name left to this PAD.

**F5.1 correction (binding, supersedes the single-scope model below).**
Gate F F5 found, and the Product Owner's Gate F F5.1 Decision 2 confirmed,
that this PAD's original single-scope model conflated two structurally
different operations: *reading* Gate F's governed output surface, and
*creating* a new, persisted Decision Evaluation (CDD-015 §16) — which this
repository's own existing precedent (`supplier-risk:submit` vs.
`supplier-risk:read`, CDD-013) treats as a distinct, command-shaped
authority, never folded into a `:read` scope. This PAD now defines **two**
scopes: `supply-chain-impact:read` (§2a, unchanged boundary from the
original single-scope design) and `supply-chain-impact:evaluate` (§2b, new).
Neither introduces approval, execution, or administration authority of any
kind.

## 1. Context

PAD-002 §10 ("Canonical scope contract — DECISION E-05") establishes that
CTEC's scope names are colon-delimited and authoritative, and states they
"SHALL NOT be renamed to fit Keycloak's own naming conventions"
(`PAD-002-..._FROZEN.md:197-198`). That is a renaming prohibition, not a
prohibition on adding new scopes — PAD-002 itself is the precedent vehicle
for scope-contract changes (it added the current four scopes on top of
IDP-001/BSP-001/PAS-001's prior authority), and this PAD follows that same
pattern for Gate F.

## 2. Scope names — FINAL

### 2a. `supply-chain-impact:read`

Rationale: capability-oriented (names the business capability — "Supply
Chain Impact" — not an implementation detail), colon-delimited consistent
with the existing four canonical scopes, and structurally distinct from
`supplier-risk:read` (a different resource — see §5). This literal scope
name is FINAL, authorized by the Product Owner as part of this document's
publication (§14).

### 2b. `supply-chain-impact:evaluate` (F5.1 addition)

Rationale: same colon-delimited, capability-oriented naming convention as
§2a, using the verb `evaluate` — matching CDD-015's own vocabulary for the
governed computation this scope authorizes ("Gate F evaluation," CDD-015
§4-5) — rather than `:submit` (already claimed by the structurally different
PAS-001/supplier-risk resource, §5) or `:write`/`:create` (which would
misleadingly suggest canonical-master-data mutation, which this scope
explicitly does not authorize — see §3a). This literal scope name is FINAL,
approved by the Product Owner (Gate F F5.1 Decision 2), subject to the
repository-consistency verification performed in this document's
remediation (Gate F F5.1 Part 7 of the governing report) — no conflict with
any existing FROZEN authority was found.

## 3. Read boundary (`supply-chain-impact:read`)

`supply-chain-impact:read` authorizes **retrieval of existing, already-persisted**
Gate F governed output only:

- Dependency-chain / impact-path results (Supplier → Material → Product/BOM
  → Facility)
- Revenue exposure associated with the affected business context
- Alternate-supplier evaluation results (qualification, capacity, lead time,
  cost)
- The governed mitigation recommendation (DRM output)
- The `HUMAN_APPROVAL_REQUIRED` governance-standing indicator (GRM output —
  see CDD-015 §14 and Gate F F1 Decision 4)
- Existing, previously-created Decision Evaluations (CDD-015 §16) and their
  child records

It authorizes **nothing** else. In particular, per the Product Owner's Gate F
scope boundary, it MUST NOT be interpreted or implemented to authorize:

- **creation of a new Decision Evaluation, or re-evaluation of an existing
  one** (F5.1 correction — this was ambiguous under the original single-scope
  model; it is now exclusively `supply-chain-impact:evaluate`'s authority,
  §3a)
- approval, rejection, or conditional approval of a recommendation
- any execution action (ERP write-back, sourcing execution, purchase-order
  creation, contract amendment, supplier activation)
- mutation of any canonical enterprise fact
- entity-resolution decision authority (that remains `entity-resolution:decide`
  exclusively — see §7)
- architecture/governance administration of any kind

## 3a. Evaluate boundary (`supply-chain-impact:evaluate`) (F5.1 addition)

`supply-chain-impact:evaluate` authorizes **governed computation that
creates new, persisted, runtime decision records** — explicitly not
canonical-master-data mutation, and explicitly not human decision authority:

- Initiating one governed Gate F evaluation for a specific at-risk Supplier
- Creating the one `decision_evaluations` group row for that evaluation
  (CDD-015 §16 item 1)
- Performing the read-only ontology/Ask CTEC traversal that feeds it
  (CDD-015 §8 — unchanged, still bounded to fact-reporting only, per PAD-001
  §2 item 5)
- Deriving governed knowledge inputs (qualification, capacity, lead time,
  cost) as `assertions` (CDD-015 §9)
- Executing the deterministic DRM policy evaluation and persisting the
  resulting `decision_evaluation_records` row(s) (CDD-015 §11, §16 item 4)
- Executing the GRM evaluation and persisting the resulting single
  `governance_evaluation_records` row (CDD-015 §12, §16 item 5)

It authorizes **nothing** else. This is **governed computation, not human
decision authority and not operational execution authority** — it MUST NOT
be interpreted or implemented to authorize:

- human approval, rejection, or conditional approval of the recommendation
  it produces
- any execution action (ERP write-back, sourcing execution, purchase-order
  creation, contract amendment, supplier activation)
- mutation of any canonical enterprise master data — the evaluation reads
  canonical facts (via traversal) and writes only the noncanonical runtime
  records CDD-015 §16-17 authorizes; it never alters an `enterprise_entity`,
  `institutional_relationship` instance beyond the `candidateFor` evaluation
  edges CDD-015 §9 already authorizes, or any other canonical record
- governance/architecture administration of any kind
- entity-resolution decision authority (`entity-resolution:decide` remains
  exclusively separate — see §7)

## 4. APIs/surfaces requiring these scopes

Any new Gate F API surface (defined by CDD-015, not this PAD — this PAD
authorizes the boundary, CDD-015 defines the concrete endpoints) MUST
require the scope matching the operation's actual shape: a **retrieval**
operation over §3's output categories requires `supply-chain-impact:read`; an
operation that **creates** a new Decision Evaluation (§3a) requires
`supply-chain-impact:evaluate`. This PAD does not itself create any
endpoint. A caller performing an evaluate operation MAY receive, in the same
response, the initial result of the specific Decision Evaluation it just
created, without separately holding `:read` — this is not a grant of general
retrieval access to *other*, previously-existing Decision Evaluations, only
to the one the same call just produced (§4a addresses scope composition in
full).

## 4a. Scope composition semantics (F5.1 addition)

**`supply-chain-impact:read` and `supply-chain-impact:evaluate` are
independent, non-compositional scopes.** Holding one does not imply or grant
the other. This follows the exact, unambiguous precedent already
established for `supplier-risk:*`: `supplier-risk:submit`, `:read`,
`:retry`, and `:replay` are each independently checked
(`_authorize(authenticated, scope, ...)`, one exact-string membership test
per endpoint — `api/supplier_risk/router.py`) with no scope implying
another anywhere in this codebase. A caller wanting both to retrieve
historical Decision Evaluations and to initiate new ones must hold both
`supply-chain-impact:read` and `supply-chain-impact:evaluate` explicitly.
The single narrow exception is §3a/§4's own-result carve-out: an evaluate
call's response may include that call's own freshly-created result without
requiring `:read` — this is not scope composition, it is a single
operation's response shape, identical in kind to how `supplier-risk:submit`'s
`POST /executions` returns its own newly-created execution's initial state
without the caller separately holding `supplier-risk:read`.

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
CTEC directly) — whether that composition happens within a `:read` retrieval
or within a `:evaluate` computation (F5.1 correction: both, not `:read`
alone) — the caller authorizes via `supply-chain-impact:read` or
`supply-chain-impact:evaluate` respectively, whichever the operation
actually is; this PAD does not require a caller to separately hold
`ontology-copilot:ask` to receive Gate F's composed output, following the
general CTEC pattern that a bounded capability's own scope governs its own
composed response (precedent: CDD-011's supplier-risk pipeline does not
require its callers to separately hold ERM/SRM/ASM/KRM/DRM/GRM-internal
authority).

## 7. Interaction with `entity-resolution:read` and explicit separation from `entity-resolution:decide`

Gate F reads governed enterprise-entity and relationship data through the
same underlying persistence Entity Resolution and Ask CTEC already read
(`institutional_relationships`, `enterprise_entities`) but does so under its
own `supply-chain-impact:read`/`supply-chain-impact:evaluate` scopes (F5.1
correction: both, not `:read` alone) — neither requires, grants, or implies
`entity-resolution:read`. **Explicit separation, binding, applies to both
Gate F scopes equally**: nothing authorized by this PAD, under either
`:read` or `:evaluate`, may be implemented in a way that invokes, requires,
substitutes for, or otherwise crosses into `entity-resolution:decide`'s
authority boundary (`entity_resolution/router.py:170`, a mutating decision
endpoint). Gate F F1 confirmed that returning a `HUMAN_APPROVAL_REQUIRED`
state from a read-scoped endpoint is a governed *fact* about
decision-readiness, not an exercise of decide authority (analogous to DRM's
existing `HumanOverrideService` returning override-eligibility as data,
`decision_engine/service.py:113-117`) — this PAD confirms that boundary
explicitly rather than leaving it implicit.

## 8. TrustedPrincipal / tenant authority

Unchanged from Gate E, applies identically to both scopes. Tenant authority
for any Gate F read or evaluate operation MUST originate exclusively from
`TrustedPrincipal.tenant_id` → `AuthorityContext.organization_id`, identical
to the rule RFC-015 §1 and RFC-016 §2b already establish for every other
tenant-scoped operation in this system — never from a client-supplied
request field. This PAD introduces no new tenant-derivation mechanism; it
reuses the existing one without modification. A client-supplied tenant value
on an evaluate request MUST be ignored/rejected in favor of the trusted
value, identical treatment to every other tenant-scoped write in this
system.

## 9. Normal demo persona permissions

**F5.1 correction (binding).** Per PAD-002 §11's least-privilege
demo-persona principle, and per the Product Owner's Gate F F5.1 Decision 5:
the normal demo persona SHALL be granted **both**
`supply-chain-impact:read` **and** `supply-chain-impact:evaluate` — the
Product Owner's explicit intent is that the demo persona can run the full
Gate F evaluation end-to-end for demonstration purposes, not merely view
pre-existing results. This is consistent with, not a departure from, PAD-002
§11's own reasoning: `supply-chain-impact:evaluate` carries no approval or
execution authority (§3a), exactly the same property that justified
granting the demo persona `supplier-risk:read`/`entity-resolution:read`/
`ontology-copilot:ask` while withholding `entity-resolution:decide`.
**Verified against existing frozen Gate E authority**: PAD-002 §11 sets a
least-privilege *principle* (grant read-shaped, non-decision capabilities;
withhold decision/administration capabilities), not a closed enumeration of
which future scopes may be added to the demo persona — granting
`supply-chain-impact:evaluate` (governed computation, no human-decision or
execution authority, per §3a) does not violate that principle; withholding
`entity-resolution:decide` remains unchanged (§18/§7). No conflict with any
existing FROZEN authority was found. This architectural decision is final
as of this document's authorization (§14); actual identity-provider grant
provisioning (e.g., Keycloak configuration) remains Gate F
implementation-time work, not authorized by this document.

## 10. Forbidden approval/execution behavior

Binding, restated from the Product Owner's Gate F F1 Decision 4 and Gate F
business boundary, **applies to both scopes**: no scope authorized by this
PAD — neither `:read` nor `:evaluate` — now or by future amendment without a
new PAD, may gate an approve, reject, conditionally approve, execute, or any
other mutating operational action. `:evaluate`'s authority to persist
runtime decision records (§3a) is governed computation, not human decision
authority and not operational execution authority (Gate F F5.1 Decision 2)
— it terminates the moment GRM produces its standing. Gate F stops at
`HUMAN_APPROVAL_REQUIRED`. Any future capability that implements human
approval, execution, or workflow requires its own, separately authorized PAD
— it is explicitly out of scope here and neither of this PAD's scopes may be
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

Unchanged from Gate E, applies to both scopes. `supply-chain-impact:read`-
and `supply-chain-impact:evaluate`-gated endpoints inherit Gate E's existing
session-lifecycle behavior in full: RP-initiated logout, local session
termination, Keycloak SSO termination, and the requirement that protected
actions re-require authentication after logout apply to any Gate F endpoint
exactly as they already apply to `supplier-risk:read`- and
`entity-resolution:read`-gated endpoints. This PAD defines no new
session-lifecycle behavior.

## 13. Non-claims

This PAD does not authorize any endpoint, persistence change, ontology
vocabulary (see RFC-017), decision/recommendation logic, or frontend
implementation. It does not modify `supplier-risk:read`, `supplier-risk:submit`,
`entity-resolution:read`, `entity-resolution:decide`, or `ontology-copilot:ask`
in any way. It does not introduce any approval, execution, or administration
scope. **It authorizes exactly two new scopes (F5.1 correction, supersedes
the original single-scope claim): `supply-chain-impact:read` (§2a, §3) and
`supply-chain-impact:evaluate` (§2b, §3a) — nothing else.**
`supply-chain-impact:evaluate` does not authorize human approval, execution,
or canonical-master-data mutation (§3a); it is governed computation only.

## 14. Authorization

Authorized by CTEC Product Owner Manoj Nair on 2026-08-18: the
`supply-chain-impact:read` scope and its access boundary (§2a, §3), final
and not merely recommended, following Gate F F0 through F3 architecture
review and the Gate F F3 release-candidate consistency and dependency
verification (see the architecture/released/v1.11/ Architecture Consistency
Report). **Amended by Product Owner authorization, Gate F F5.1 governance
remediation, 2026-08-18**: the `supply-chain-impact:evaluate` scope and its
access boundary (§2b, §3a, §4, §4a), distinguishing it from `:read` per
Decision 2, and the demo-persona correction in §9 per Decision 5; and this
document's publication to FROZEN/AUTHORITATIVE governance state as part
of architecture baseline v1.11 (this authorization).
