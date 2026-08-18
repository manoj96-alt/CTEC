# CDD-015 — Governed Supply Chain Impact and Mitigation Decision

Version: 1.0 (DRAFT)
Status: PROPOSED
Current: NO
Authority: NON-AUTHORITATIVE
Approval: PENDING Product Owner review — not yet authorized
Governing authorities: RFC-017 (PROPOSED, semantic vocabulary), PAD-003
(PROPOSED, `supply-chain-impact:read` scope), plus already-FROZEN CDD-004
through CDD-013, PAD-001, RFC-015, RFC-016

## 1. Purpose

Defines the bounded vertical capability "Governed Supply Chain Impact &
Mitigation Decision" (Gate F): given a risky supplier, produce a governed,
evidence-linked, reproducible mitigation recommendation and a governance
standing indicating whether human approval is required — and stop there.
This CDD does not authorize approval, execution, or any protected future
platform capability (§27).

## 2. Business problem

Today, when a supplier becomes risky, CTEC has no governed way to answer
"which materials, products, facilities, and revenue are affected, what
qualified alternatives exist, and what should be done" — that reasoning
exists only in an unauthenticated, unscoped frontend prototype
(`frontend/lib/demo/scenario-facts.ts`, `decision-rules.ts` — F0 §4-5) with
hardcoded facts and a hardcoded allocation formula, disconnected from the
governed backend. Gate F closes this gap for exactly this one vertical slice.

## 3. Persona

The same authenticated demo/production persona Gate E already establishes
(OIDC session, PAD-002), holding `supply-chain-impact:read` (PAD-003) — a
risk/sourcing analyst reviewing a specific at-risk supplier.

## 4. Trigger

A caller requests Gate F's impact-and-mitigation view for a specific
Supplier already known to be at risk (an existing Risk Event associated with
that Supplier's Region, via the existing `exposedTo`/`locatedIn` chain — CDD-015
does not define how a Risk Event is created; that remains out of scope, see
§27).

## 5. End-to-end business journey

External Risk Signal (pre-existing, out of scope) → Supplier (existing
concept) → Risk + Evidence (existing `locatedIn`/`exposedTo` chain +
assertion/evidence mechanism) → Material Dependency (`supplies`) → Product/BOM
Dependency (`usedIn`/`defines`) → Facility Exposure (new `assembledAt`,
RFC-017 §3a) → Revenue Exposure (existing `generatesRevenue`) → Alternative
Supplier (new `candidateFor`, RFC-017 §3c) → Qualification/Capacity/Lead
Time/Cost (new governed derivation, §9-10) → Governed Mitigation
Recommendation (DRM, §11) → GRM governance standing:
`HUMAN_APPROVAL_REQUIRED` (§12) → STOP.

## 6. Gate F capability boundary

In scope: read-only dependency traversal; governed derivation of alternate-
supplier qualification/capacity/lead-time/cost as assertions; a mitigation
recommendation (DRM); a governance-standing/human-authority-required
indicator (GRM); an immutable decision-time snapshot sufficient to reproduce
the recommendation (§16); one new read API surface (§21) under
`supply-chain-impact:read`.

Out of scope (binding, restated from the Product Owner's Gate F business
boundary): human approval workflow, approve/reject/conditionally-approve
actions, ERP write-back, sourcing execution, purchase-order creation,
contract amendment, supplier activation, outcome tracking, post-decision
effectiveness analysis, any generalized workflow engine, any of the six
protected future platform capabilities (§27), a seventh cognitive engine,
and any change to `architecture/released/*`.

## 7. Existing architecture reused

Ask CTEC traversal engine (`domain/ontology_copilot/traversal.py`, PAD-001
boundary, unmodified); the six existing cognitive-engine ports
(`erm, srm, asm, krm, drm, grm` — `runtime/orchestration.py`, unmodified,
frozen CDD-010 contract respected in full, no seventh stage); the CDD-011
bounded-adapter pattern (`integration/adapters/*.py`) as the template for
Gate F's new adapters; `assertions`/`assertion_evidence`
(`infrastructure/persistence/models/assertion.py`) for evaluative facts;
`decision_evaluation_records`/`governance_evaluation_records` for the
recommendation and governance-standing outputs; `institutional_relationships`
for all new relationship instances, using the RFC-017 relationship types.

## 8. Ontology traversal responsibility

Ask CTEC's existing `find_paths_to_target_type` (bounded BFS, depth-limited,
read-only) performs the Material Dependency, Product/BOM Dependency, and
Facility Exposure steps and reads the existing `generatesRevenue` edge for
Revenue Exposure — all as **fact-reporting only**. Per PAD-001 §2 item 5,
Ask CTEC's boundary MUST NOT be extended to synthesize the mitigation
recommendation itself (Gate F F1 §4); traversal output is handed off to KRM
(§9-10) as input, never treated as a recommendation.

## 9. Governed fact derivation

A new bounded adapter set (CDD-011-shaped, feeding the existing SRM/ASM/KRM
ports, no new port) derives alternate-supplier qualification, capacity,
lead-time, and cost as `assertions` (Evidence-backed where sourced from an
external system, Institutional where governance-asserted —
`assertion.py:127-129`), replacing the current requirement (CDD-011,
`schemas.py:47-79`) that a caller pre-supply these as scores. This is the one
genuine capability gap Gate F closes that no existing engine currently fills
(Gate F F1 §7).

## 10. KRM responsibility

Unchanged role, per its own CDD-007 boundary ("does not create approval,
modify upstream cognitive records, or alter the CEO," `CDD-007-REVIEW.md:9`):
KRM turns the assertions from §9 into Institutional Knowledge, the only input
form DRM is permitted to consume (`CDD-008-REVIEW.md:9`). KRM performs no
aggregation beyond what its existing contract already allows; if revenue
exposure is ever found to require cross-product rollup rather than a
single-hop `generatesRevenue` read, that is an open question (Gate F F1
§34.3) explicitly deferred, not resolved by this CDD (§27).

## 11. DRM responsibility

Unchanged role: `DecisionRecommendationService.recommend()`
(`decision_engine/service.py:19-20`), fed by real Knowledge from §10 instead
of caller-supplied scores, evaluates the derived facts against a governed,
versioned policy (`decision_engine/configuration.py:7-38`, reusing the
Gate F F1-confirmed `MATERIALITY_THRESHOLD_USD`-equivalent as a policy
configuration value, not a frontend constant — see §23) and produces the
mitigation recommendation, persisted per §16.

## 12. GRM responsibility — human-authority-required boundary

Per the Product Owner's Gate F F1 Decision 4: GRM, not DRM, owns the
`HUMAN_APPROVAL_REQUIRED` state. DRM's existing `HumanOverrideService`
(`decision_engine/service.py:113-117`) is **not** used for this purpose in
Gate F (noted as an open question in F1 §34.2; the Product Owner's F1
decision resolves it in favor of GRM). GRM evaluates the DRM recommendation
against governance policy and produces a `governance_evaluation_records` row
whose outcome includes the `HUMAN_APPROVAL_REQUIRED` indicator — a governed
fact about decision-readiness, not an approval action (PAD-003 §7). Gate F
implements no code path that can produce `APPROVED`, `REJECTED`, or any
other action-implying state; the only GRM outputs Gate F defines are
`HUMAN_APPROVAL_REQUIRED` and its absence.

## 13. Mitigation recommendation

DRM's output (§11): a structured recommendation (candidate alternate
supplier, proposed allocation, narrative reasoning), persisted as a
`decision_evaluation_records` row (§16). Gate F does not execute, queue, or
otherwise act on this recommendation — it is terminal output.

## 14. Human-authority-required boundary

Restated, binding: Gate F's business journey (§5) terminates at
`HUMAN_APPROVAL_REQUIRED`. No approval, rejection, conditional approval,
workflow, or execution is implemented by this CDD, now or by silent future
extension — any such capability requires its own CDD and PAD.

## 15. Evidence / provenance

Every assertion produced under §9 carries its existing
`assertion_evidence`/`source_system_id`/`source_object_id` linkage where
Evidence-backed (`assertion.py`, `assertion_evidence` table) or is marked
Institutional where governance-asserted without external sourcing. The DRM
recommendation (§13) references its input assertions/knowledge via the
existing `knowledge_references` column (`decision_evaluation.py:28`) — no new
evidence mechanism is introduced.

## 16. Decision-time reproducibility

Per the Product Owner's Gate F F1 Decision 5 (hybrid persistence): the
dependency path and traversal-derived exposure facts (Material, Product/BOM,
Facility) remain recomputable from `institutional_relationships` and are
**not** separately persisted as their own canonical artifact (avoiding a new
canonical entity merely to store a calculated path, per the Product Owner's
explicit instruction). The `decision_evaluation_records` row produced by DRM
(§11) is the immutable decision-time snapshot: its existing
`knowledge_references` (JSON list), `governing_policy_reference`+
`policy_version`, `decision_recommendation`, `structured_reasons`, and
`narrative_explanation` columns (`decision_evaluation.py:10-42`) are
populated to reference or preserve, at minimum: the Supplier, the triggering
Risk Event, the affected Material and Product/BOM, the Facility, the revenue
exposure value used, the evaluated Alternate Supplier, its qualification
state, capacity used, lead time used, and cost impact used — each as a
`knowledge_references` pointer into the §9-10 assertions/knowledge that fed
this decision, plus the policy version that governed it. The paired
`governance_evaluation_records` row (§12) references this decision record
via its existing generic `governed_record_reference`/`governed_record_type`
columns (`governance_evaluation.py:29-30`) and carries the
`HUMAN_APPROVAL_REQUIRED` outcome. Together these two existing, already-
governed, append-only, policy-versioned record types are sufficient to
reproduce why CTEC made the recommendation at decision time — **no new
schema is introduced** (satisfying the Product Owner's instruction not to
design new schema unless the existing runtime model is proven insufficient;
F1 §20 confirmed it is not).

## 17. Persistence behavior

Summarized from §16: dependency path/traversal results are derived-on-read,
never persisted as their own table. Alternate-supplier facts are persisted as
`assertions`. The recommendation is persisted as one `decision_evaluation_records`
row. The governance standing is persisted as one `governance_evaluation_records`
row. No new table is authorized by this CDD.

## 18. Authorization

Every Gate F read endpoint requires `supply-chain-impact:read` (PAD-003).
Tenant authority originates exclusively from `TrustedPrincipal.tenant_id`
(PAD-003 §8), never from client input. No endpoint defined by this CDD
accepts or requires `entity-resolution:decide`.

## 19. Tenant isolation

Unchanged mechanism: every new `institutional_relationships` row (using the
RFC-017 relationship types) carries the existing composite
`(tenant_id, entity_id)` FK pattern (migration 0012, RFC-016 §2b); every
`assertions`/`decision_evaluation_records`/`governance_evaluation_records`
row inherits tenant scoping through its existing subject-entity linkage. No
new tenant-propagation mechanism is introduced.

## 20. Replay/recovery

Gate F's new adapters (§9) plug into the existing six-port CDD-010/CDD-012
durable-execution and replay model unmodified — no seventh stage, no change
to `runtime/recovery.py`'s `STAGES` tuple or `range(6)` validation (Gate F F1
§4). Ask CTEC's traversal step is not part of the durable-execution pipeline
(as today, unchanged) and requires no replay semantics of its own, consistent
with how it already behaves outside the CDD-010 shell.

## 21. API behavior

One new, additive, read-only API surface (exact routes to be specified at
implementation time, not by this CDD) returning the §3 PAD-003 output
categories under `supply-chain-impact:read`. No existing API's contract is
modified. No command/mutating endpoint is introduced.

## 22. Frontend responsibility

None in this CDD. Gate F F2 authorizes no frontend implementation (F2
scope is document drafting only). A future implementation CDD/PR would build
a new, authenticated production frontend surface consuming the §21 API;
`/demo/supplier-risk` is not modified or wired to this API by this CDD (§23).

## 23. Demo transition

The existing frontend prototype (`frontend/lib/demo/scenario-facts.ts`,
`decision-rules.ts`, `/demo/supplier-risk`) remains explicitly
REFERENCE/BEHAVIORAL PROTOTYPE — NON-AUTHORITATIVE, unmodified by this CDD,
per the Product Owner's explicit instruction. Migration mapping (Gate F F1
§18, informational only — not authorized for implementation by this CDD):
prototype scenario facts → governed persisted facts (`institutional_relationships`
+ `assertions`); prototype `MATERIALITY_THRESHOLD_USD` → DRM policy
configuration; prototype `decision-rules.ts` allocation formula → DRM
recommendation logic; prototype's four boolean gating conditions →
assertions feeding DRM. Retirement of the prototype's calculation authority
is an explicit later decision, out of scope for this CDD.

## 24. Audit requirements

Every §9 assertion, §11 recommendation, and §12 governance-standing record is
append-only/immutable-by-versioning per its existing table's design
(§16, §20). No Gate F operation may update or delete a
`decision_evaluation_records` or `governance_evaluation_records` row in
place. `api_security_audit_events` (existing, CDD-013) applies unmodified to
every Gate F endpoint, consistent with how it already applies to
`supplier-risk:*` and `entity-resolution:*` endpoints.

## 25. Negative/security behavior

A caller without `supply-chain-impact:read` MUST receive the existing
standard authorization-failure behavior (unchanged mechanism, CDD-013). A
caller may not supply a `tenant_id` to influence which tenant's data is
returned (PAD-003 §8). No Gate F endpoint accepts or exposes any parameter
that could trigger `entity-resolution:decide`-scoped behavior (PAD-003 §7).
No Gate F endpoint accepts an approval, rejection, or execution instruction
of any kind — there is no code path for one to exist.

## 26. Future platform compatibility

See `GATE-F-ARCHITECTURE-DECISION-TRACE.md` for the full mapping. Summary:
Gate F introduces no schema or engine change that would need to be reworked
for Supply Chain Blueprint, Source-to-Blueprint Semantic Mapping, Profiling +
Gap Engine, Gap Impact + Remediation Engine, Decision Requirements, or
Decision Readiness to be introduced later — all reuse the same taxonomy,
assertion, and decision/governance record primitives Gate F itself reuses.
Gate F's own decision-readiness check (§12) is implemented as a bounded,
supplier-risk-specific rule and is explicitly flagged as a known future
generalization point for Decision Readiness, not a permanent architecture
(Gate F F1 §28).

## 27. Explicit non-goals

No seventh cognitive engine. No human approval/execution workflow. No ERP
write-back, sourcing execution, purchase-order creation, contract amendment,
or supplier activation. No outcome tracking or post-decision effectiveness
analysis. No generalized workflow engine. No generalized revenue-aggregation
engine (Product Owner Decision 6) — revenue exposure is read via the existing
single-hop `generatesRevenue` edge only. No implementation of Supply Chain
Blueprint, Source-to-Blueprint Semantic Mapping, Profiling + Gap Engine, Gap
Impact + Remediation Engine, Decision Requirements, or Decision Readiness. No
modification of `/demo/supplier-risk` or its calculation logic. No new
canonical vocabulary beyond RFC-017 (this CDD cites RFC-017; it does not
itself authorize vocabulary). No new access scope beyond PAD-003 (this CDD
cites PAD-003; it does not itself authorize a scope).

## 28. Acceptance criteria

1. A Gate F read request for an at-risk Supplier returns a dependency chain
   (Material, Product/BOM, Facility) derived via Ask CTEC traversal, with no
   traversal result persisted as a new canonical artifact.
2. Alternate-supplier qualification/capacity/lead-time/cost are represented
   as `assertions`, not caller-supplied request fields.
3. Exactly one `decision_evaluation_records` row and one
   `governance_evaluation_records` row are produced per Gate F evaluation,
   each referencing the input assertions/knowledge used.
4. The governance-standing output is exactly `HUMAN_APPROVAL_REQUIRED` or its
   absence — no other action-implying state is producible.
5. Every Gate F endpoint requires `supply-chain-impact:read`; none accept or
   grant `entity-resolution:decide`.
6. Tenant scoping is enforced identically to existing `institutional_relationships`/
   `assertions` behavior; no cross-tenant read is possible.
7. `runtime/orchestration.py`'s six-port contract and `runtime/recovery.py`'s
   `STAGES` tuple are unmodified.
8. `/demo/supplier-risk` and its scenario/rule files are unmodified.

## 29. Automated test requirements (for implementation time, not authorized by F2)

Domain: new-adapter unit tests for qualification/capacity/lead-time/cost
derivation, following the CDD-011 adapter test pattern. Persistence:
assertion/decision/governance record creation and tenant-isolation tests,
following `test_institutional_relationship_tenant_migration_postgres.py`'s
pattern. Security: scope-enforcement tests for `supply-chain-impact:read`,
following `test_supplier_risk_api_security.py`'s pattern, including an
explicit negative test that no Gate F endpoint accepts or is reachable via
`entity-resolution:decide`. Architecture-drift: a Gate-F equivalent of
`test_runtime_architecture.py`'s allowlist/six-stage-contract assertions,
confirming no seventh stage was introduced. Replay/recovery: confirm Gate
F's adapters participate correctly in the existing six-stage checkpoint
model. None of these tests are created by F2 (document drafting only).

## 30. Demo acceptance scenario (for implementation time, not authorized by F2)

Using the frontend prototype's existing scenario as behavioral reference
only (`SUP-001`/`MAT-100`/`PROD-01`/`SUP-002` — F0 §4): an analyst requests
Gate F's view for `SUP-001`; the response shows the real dependency chain to
`PROD-01` via governed traversal, alternate supplier `SUP-002`'s
governed-derived qualification/capacity/cost/lead-time, a DRM recommendation,
and a GRM `HUMAN_APPROVAL_REQUIRED` indicator — with every fact traceable to
a persisted assertion or decision/governance record, none of it computed in
frontend TypeScript. This scenario is not implemented by F2.

## 31. Non-claims

This CDD does not itself authorize any canonical semantic vocabulary (see
RFC-017) or any access scope (see PAD-003) — it cites both and relies on
their authorization. It does not modify CDD-010's six-stage contract, any
existing CDD-004–014 boundary, PAD-001, PAD-002, RFC-015, or RFC-016. It does
not authorize implementation; F2 is document drafting only.

## 32. Authorization

**PENDING.** This CDD is proposed and non-authoritative. It requires explicit
Product Owner authorization, and authorization of RFC-017 and PAD-003, before
any implementation may begin.
