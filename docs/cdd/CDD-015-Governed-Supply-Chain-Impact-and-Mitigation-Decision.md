# CDD-015 — Governed Supply Chain Impact and Mitigation Decision

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Architecture Baseline: v1.11
Governing authorities: RFC-017 (FROZEN, semantic vocabulary), PAD-003
(FROZEN, `supply-chain-impact:read` and `supply-chain-impact:evaluate`
scopes), plus already-FROZEN CDD-004 through CDD-013, PAD-001, RFC-015,
RFC-016
Mandatory template: CDD Template v2.2 (§31-35 — F5.1 remediation)

**Publication note**: this Work Order is an architecture authority
(CDD Gate: FROZEN), published as part of Gate F architecture baseline
v1.11. No implementation exists yet — this document does not itself
authorize implementation; a separate Product Owner
implementation-planning authorization is required before any code is
written against it (see `architecture/INDEX.md`'s Governed implementation
work orders entry for this CDD's current Implementation State).

**F5.1 governance remediation note**: Gate F F5 (Implementation Planning)
found this Work Order lacked CDD Template v2.2's mandatory exhaustive
per-artifact authorization records (§7-11 of the template) and conflated
read and evaluate operations under a single read-only claim. Both are
remediated below (§31-35 add the authorization records; §12, §18, §21, §25,
§28 correct the read/evaluate conflation) without altering any previously
approved Gate F business/architecture decision.

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
(OIDC session, PAD-002), holding `supply-chain-impact:read` and
`supply-chain-impact:evaluate` (PAD-003 §2a-§2b, §9 — F5.1 correction) — a
risk/sourcing analyst reviewing a specific at-risk supplier and, per the
Product Owner's Gate F F5.1 Decision 5, able to run the governed evaluation
itself.

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
the recommendation (§16); two new API operation kinds (§21 — F5.1
correction): retrieval under `supply-chain-impact:read` and governed
evaluation under `supply-chain-impact:evaluate`.

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

**Per-(candidate, material) pairing (F2.1 correction — binding)**: because a
single Material may have multiple candidate Alternate Suppliers, and a single
Alternate Supplier may be a candidate for multiple Materials, a qualification/
capacity/lead-time/cost `assertions` row alone cannot disambiguate *which*
Material a given fact applies to — `assertions`' subject/predicate/object
shape is binary (`assertion.py:24-27` XOR constraint), not ternary. Gate F
MUST create one `institutional_relationships` row per (Alternate Supplier,
Material) pair under evaluation, using the RFC-017 `candidateFor` relationship
type, and attach each derived assertion to that specific relationship
instance via the existing `institutional_relationship_assertions` junction
table (`institutional_relationship_assertion.py:13-24`, composite primary key
`(institutional_relationship_id, assertion_id)`). This is the mechanism that
makes "A1 qualified for M1" and "A1 qualified for M2" representable as two
distinct, non-colliding facts — generic, unscoped `assertions` alone do not
guarantee this (Gate F F2.1 persistence verification).

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
fact about decision-readiness, not an approval action (PAD-003 §3a, §7). Gate F
implements no code path that can produce `APPROVED`, `REJECTED`, or any
other action-implying state; the only GRM outputs Gate F defines are
`HUMAN_APPROVAL_REQUIRED` and its absence.

**F5.1 correction — internal outcome vs. business semantic mapping
(binding, resolves the F5 open design question).** `domain/governance_engine/model.py`'s
shared `GovernanceOutcome` enum (`COMPLIANT`, `NON_COMPLIANT`,
`EXCEPTION_GRANTED`, `REQUIRES_REVIEW`) is **not** extended with a new
`HUMAN_APPROVAL_REQUIRED` member — per the Product Owner's Gate F F5.1
Decision 3, Gate F reuses the existing `REQUIRES_REVIEW` outcome as GRM's
internal, persisted engine result. The persisted
`governance_evaluation_records` row retains `governance_outcome =
REQUIRES_REVIEW`, unchanged from how every other GRM consumer's
`REQUIRES_REVIEW` outcome is already persisted (no new column, no new enum
value, no change to `domain/governance_engine/model.py`). Gate F's own
API/view-model layer (§21, §17) applies a **deterministic, Gate F-specific,
non-authoritative-for-other-GRM-consumers projection**: internal outcome
`REQUIRES_REVIEW` → Gate F business/API semantic state
`HUMAN_APPROVAL_REQUIRED`. This projection is a presentation-layer mapping
only — it introduces no shared architecture change, no approval workflow,
and does not imply GRM itself has gained an additional outcome. Any other
capability that also produces `REQUIRES_REVIEW` is unaffected and does not
inherit Gate F's `HUMAN_APPROVAL_REQUIRED` label.

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

Per the Product Owner's Gate F F1 Decision 5 (hybrid persistence) and Gate F
F2.1 Decision D (persistence proof required): the dependency path and
traversal-derived exposure facts (Material, Product/BOM, Facility) remain
recomputable from `institutional_relationships` and are **not** separately
persisted as their own canonical artifact.

**F2.2 correction (binding, supersedes F2.1's `business_context_reference`
convention).** F2.1 had proposed correlating multiple `decision_evaluation_records`
rows for one Gate F evaluation by convention, via the existing
`business_context_reference` column. The Product Owner rejected this at
F2.2: `business_context_reference` already has a distinct, documented,
FROZEN/AUTHORITATIVE meaning — "Existing canonical Context reference"
(`docs/architecture/CIM-001-Cognitive-Integration-Contract-Model-DRAFT.md:94`,
frozen identically at `architecture/released/v1.2/CIM-001-...v1.1_FROZEN.md:94`)
— scoped to CIM-001's own bounded supplier-risk vertical-slice contract
(CIM-001 §1: "bounded MVP semantics authorized for this vertical slice only
[...] not universal canonical vocabulary"). Repurposing it for Gate F's
decision-evaluation-group identity would silently overload one field with
two unrelated meanings — exactly what was rejected. Gate F instead introduces
a small, explicit, noncanonical runtime persistence extension:

**New concept: Decision Evaluation.** The stable identity of one governed
Gate F decision evaluation, whose result may require multiple persisted
decision records — a business/decision-layer concept, deliberately distinct
from `runtime_executions.execution_id` (an infrastructure/admission-layer
concept: one per physical pipeline run, and a *new* `execution_id` is minted
on every replay — `runtime_recovery_attempts.replay_execution_id`,
`persistence/models.py:104-106`) and from `runtime_executions.logical_execution_id`
(the runtime layer's own replay-stable identity for *that infrastructure
concern*, `persistence/models.py:25`, distinct in kind even though its
replay-stability behavior is the model this design follows).

1. **`decision_evaluations`** (new, noncanonical, CDD-015-governed — same
   governance tier as `decision_evaluation_records`/`governance_evaluation_records`
   themselves, CDD-008/CDD-009-authorized, and `runtime_executions`,
   CDD-012-authorized; not a canonical entity, no RFC implication — see §17
   below):
   one row per governed Gate F decision evaluation. Carries its own direct,
   DB-constrained `tenant_id` (following the `institutional_relationships`/
   `runtime_executions` pattern for tables new enough to get this right from
   the start, not the older, indirect-only `assertions`/`decision_evaluation_records`
   pattern), `decision_evaluation_id` (PK), and an optional
   `logical_execution_id` reference column (nullable, for audit traceability
   back to the runtime execution(s) that computed it — not a foreign key
   `runtime_executions` depends on, purely a backward-pointing audit trail).
2. **`decision_evaluation_records.decision_evaluation_id`** (new, nullable
   `ForeignKey("decision_evaluations.decision_evaluation_id")` column):
   every Gate F-produced decision record sets this to its evaluation's group
   ID. Nullable for backward compatibility — CDD-011's existing single-material
   supplier-risk rows are unaffected and remain valid with this column NULL
   ("stands alone, no explicit group" remains a legitimate state; this CDD
   does not retrofit historical rows).
3. Every derived alternate-supplier fact (qualification, capacity, lead time,
   cost) remains an `assertions` row attached to a specific
   `(Alternate Supplier, Material)` `institutional_relationships` instance
   via `institutional_relationship_assertions` (§9) — unchanged from the
   F2.1 correction; this is what preserves per-pair cardinality without
   collision, and is orthogonal to the correlation problem this section now
   resolves.
4. DRM produces one `decision_evaluation_records` row per recommended
   (Material, Alternate Supplier, allocation) unit, each carrying the same
   `decision_evaluation_id` (item 2) and referencing (via `knowledge_references`)
   the specific assertions/relationship instance that fed that unit.
5. Exactly **one** `governance_evaluation_records` row per Gate F evaluation
   references the group directly: `governed_record_reference = decision_evaluations.decision_evaluation_id`,
   `governed_record_type = "DecisionEvaluation"` — reusing
   `governance_evaluation_records`' existing, already-polymorphic
   `governed_record_reference`/`governed_record_type` columns
   (`governance_evaluation.py:29-30`) with a new type-string convention.
   **No schema change to `governance_evaluation_records` is needed** — its
   reference is now to a real, referentially-integrous row (the group),
   rather than to a bare shared UUID value with nothing backing it.
6. A Material/Alternate-Supplier pair that was considered but not selected
   is represented implicitly (absence from any child record's references),
   not by a dedicated rejection/exclusion flag — unchanged from F2.1.
7. **Tenant isolation invariant (binding)**: every child `decision_evaluation_records`
   row belonging to a `decision_evaluations` group MUST resolve, through its
   referenced business facts/relationships, to the same tenant as
   `decision_evaluations.tenant_id`. This is an application-layer validation
   invariant (the persistence adapter must check it at write time), not a
   claim of automatic composite-FK enforcement — `decision_evaluation_records`
   itself still carries no direct `tenant_id` (F2.1 finding, unchanged; this
   CDD does not redesign that system-wide pattern). The group table's own
   direct `tenant_id` is the enforcement anchor this invariant checks against.

Items 1-7 are sufficient to reproduce why CTEC made the recommendation at
decision time, with real referential integrity for the one-to-many
relationship the F2.1 convention-based approach lacked. This is a genuine,
if small, persistence extension — not "no schema change" (Gate F F2.2
persistence classification: **P3** — see §17's canonical-vs-runtime
distinction below and the Gate F F2.2 report).

## 17. Persistence behavior

Summarized from §16: dependency path/traversal results are derived-on-read,
never persisted as their own table. Alternate-supplier facts are persisted as
`assertions` scoped to per-pair `institutional_relationships` instances via
`institutional_relationship_assertions` (§9, §16 item 3). The recommendation
is persisted as one-or-more `decision_evaluation_records` rows, each FK'd to
a `decision_evaluations` group row (§16 items 1-2, 4). The governance
standing is persisted as one `governance_evaluation_records` row per group,
referencing it via the existing polymorphic `governed_record_reference`/
`governed_record_type` columns (§16 item 5).

**Canonical semantic change vs. noncanonical runtime persistence change
(binding distinction — Gate F F2.2)**: this CDD makes two structurally
different kinds of change, and they must not be conflated:

- **A. Canonical semantic vocabulary change**: three new `relationship_types`
  data rows (`assembledAt`, `coveredBy`, `candidateFor`) plus retroactive
  ratification of the pre-existing ten concepts/seven relationship types —
  authorized exclusively by RFC-017, per RFC-010 §10's requirement that any
  canonical entity/attribute/relationship change go through a new RFC. This
  CDD does not self-authorize any of it (§31).
- **B. Noncanonical runtime persistence change**: the new `decision_evaluations`
  table and the new `decision_evaluation_records.decision_evaluation_id`
  column (§16). This is **not** a canonical-ontology change under RFC-010's
  own scope — RFC-010 §10 governs "canonical entities, attributes,
  relationships or lifecycle changes" within the Canonical Enterprise
  Ontology (RFC-010 §4); `decision_evaluations` is a peer, at the same
  governance tier, to `decision_evaluation_records`/`governance_evaluation_records`
  (CDD-008/CDD-009-authorized) and `runtime_executions` (CDD-012-authorized)
  — none of which were ever RFC-gated, added to the ECOM Physical Data Model
  SQL artifact, or added to EAD-001 when they were created (confirmed:
  `decision_evaluation_records`/`governance_evaluation_records` do not appear
  in `architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql` at all,
  and neither table nor `runtime_executions` has any entry in
  `docs/persistence/traceability/EAD-001-v1.7.json`). **This CDD authorizes
  change B directly, on its own authority**, following that exact precedent
  — no RFC, no Physical Model regeneration, no EAD-001 update, no Logical
  Model update. See the Gate F F2.2 report §24-32 for the full evidence
  trail.

## 18. Authorization

**F5.1 correction (binding, supersedes the single-scope claim below).** Per
the Product Owner's Gate F F5.1 Decision 2 and the revised PAD-003 §2a-§4a:
Gate F has **two** distinct scopes, not one. Every Gate F **retrieval**
endpoint (existing Decision Evaluations and their results, §21) requires
`supply-chain-impact:read` (PAD-003 §3). Every Gate F **evaluate** operation
(creating a new Decision Evaluation, §16) requires
`supply-chain-impact:evaluate` (PAD-003 §3a) — this operation MUST NOT be
gated by `supply-chain-impact:read` alone; the two scopes are
non-compositional (PAD-003 §4a). Tenant authority originates exclusively
from `TrustedPrincipal.tenant_id` (PAD-003 §8), never from client input, for
both scopes. No endpoint defined by this CDD accepts or requires
`entity-resolution:decide`, under either scope.

## 19. Tenant isolation

Unchanged mechanism: every new `institutional_relationships` row (using the
RFC-017 relationship types) carries the existing composite
`(tenant_id, entity_id)` FK pattern (migration 0012, RFC-016 §2b) — this is a
real, DB-constrained guarantee. **F2.1 finding (unchanged)**: `assertions`,
`decision_evaluation_records`, `governance_evaluation_records`, and
`institutional_relationship_assertions` carry **no direct `tenant_id` column**
and are **not** DB-constrained against cross-tenant reference — tenant
scoping for these is available only by the application following their
entity-owning foreign keys back to a tenant-scoped `institutional_relationships`/
`enterprise_entities` row. This is the existing, system-wide pattern for
these table types (not a gap Gate F introduces), and this CDD does not
redesign it.

**F2.2 addition**: the new `decision_evaluations` table (§16) **does**
carry a direct, DB-constrained `tenant_id` column — new tables introduced by
this CDD get this right from the start, following the
`institutional_relationships`/`runtime_executions` pattern rather than the
older, indirect-only `assertions`/`decision_evaluation_records` pattern.
**Binding tenant isolation invariant**: every child `decision_evaluation_records`
row referencing a given `decision_evaluations.decision_evaluation_id` MUST
resolve, through its own referenced business facts/relationships, to the
same tenant as that group's `tenant_id`. This is an application-layer
invariant the persistence adapter must validate at write time (§16 item 7)
— it is not claimed to be enforced by a composite foreign key, since
`decision_evaluation_records` itself is not being given a direct `tenant_id`
column (this CDD does not redesign that existing pattern). No new
tenant-propagation mechanism is introduced beyond this one new table and
this one new invariant.

## 20. Replay/recovery

Gate F's new adapters (§9) plug into the existing six-port CDD-010/CDD-012
durable-execution and replay model unmodified — no seventh stage, no change
to `runtime/recovery.py`'s `STAGES` tuple or `range(6)` validation (Gate F F1
§4). Ask CTEC's traversal step is not part of the durable-execution pipeline
(as today, unchanged) and requires no replay semantics of its own, consistent
with how it already behaves outside the CDD-010 shell.

**F2.1 verification (confirms, does not change, the above)**: replay/recovery
was traced concretely, not assumed from docstrings.
`runtime/persistence/repository.py` (`_recover_handoff`) recovers a stage's
input by decrypting and hash-verifying (`sha256`) the `protected_payload`
captured on the *original* `RuntimeHandoffORM` row at first-execution time,
not by re-querying live `institutional_relationships`/`assertions` state; the
DRM adapter (`integration/adapters/drm.py`) reads `policy_identifier`/
`policy_version` from that same recovered payload, not a live policy lookup.
This confirms a Gate F decision's replay/recovery reuses the original
decision-time facts and does not silently re-derive a different explanation
if the live ontology or a supplier's capacity has since changed — satisfying
the reproducibility requirement — **at the runtime-execution layer**. This
guarantee does not extend to whether the business-fact references inside an
already-completed `decision_evaluation_records.knowledge_references` remain
resolvable indefinitely after the fact (those references are not
FK-enforced — §16), which is a separate, longer-horizon data-retention
question this CDD does not resolve.

**F2.2 addition — correlation identity lifecycle across replay (binding)**:
`decision_evaluations.decision_evaluation_id` is minted exactly once, by
Gate F's new capability itself, at the moment it begins deriving/evaluating
a decision (i.e., when the new adapter set starts producing the assertions
and Knowledge described in §9-10) — **not** at trusted admission (too early;
the runtime envelope does not yet know this is a multi-record Gate F
evaluation) and **not** implicitly by first persistence write (would be
accidental, not explicit). If the underlying runtime execution is
subsequently replayed/recovered (§20 above), the recovery path MUST look up
and reuse the SAME `decision_evaluation_id` for that logical decision —
found via the optional `logical_execution_id` audit-trail column on
`decision_evaluations` (§16 item 1) — rather than minting a new one; this
mirrors, without reusing, the exact replay-stability guarantee
`runtime_executions.logical_execution_id` already provides at the
infrastructure layer (`persistence/models.py:25`, `runtime_recovery_attempts.logical_execution_id`
at line 100). This is a specification for implementation, not implemented
by this CDD.

## 21. API behavior

**F5.1 correction (binding, supersedes the original "read-only" claim,
resolves the F5 §21 flagged gap).** Gate F F5's implementation-planning pass
found that this CDD's original claim — "read-only API surface... no
command/mutating endpoint is introduced" — was inaccurate: §16 requires
creating new persisted rows (`decision_evaluations`, N
`decision_evaluation_records`, one `governance_evaluation_records`) on every
governed evaluation, which is unambiguous write behavior. The Product
Owner's Gate F F5.1 Decision 2 resolves this by splitting Gate F's API
surface into two operation kinds, precisely distinguished:

1. **READ endpoint(s)**: additive, genuinely read-only, retrieve existing,
   previously-created Decision Evaluations and their results (the §3 PAD-003
   output categories) under `supply-chain-impact:read` (PAD-003 §3). No
   existing API's contract is modified.
2. **GOVERNED EVALUATION endpoint/operation**: creates one new
   `decision_evaluations` group and its child records (§16) under
   `supply-chain-impact:evaluate` (PAD-003 §3a). This operation is
   **mutating with respect to runtime decision persistence** (new rows in
   `decision_evaluations`/`decision_evaluation_records`/`governance_evaluation_records`,
   new `candidateFor` `institutional_relationships` instances and their
   attached `assertions`, §9) but **is not mutating with respect to
   canonical enterprise master data** — it never alters an
   `enterprise_entity`, never alters an existing `institutional_relationship`
   beyond the bounded candidate-evaluation edges §9 already authorizes, and
   performs no ERP/execution action (§27). This distinction — governed
   runtime-decision persistence vs. canonical master-data mutation — is the
   basis for `:evaluate` being a distinct, non-`:read`, non-approval,
   non-execution scope (PAD-003 §3a).

Evaluation-creation persistence MUST NOT be described or implemented as a
"read side effect" of `supply-chain-impact:read` — it is its own, separately
scoped operation (PAD-003 §4a on scope composition). Exact routes remain
unspecified by this CDD, to be defined at implementation time.

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

**F5.1 correction (binding)**: applies independently to both scopes. A
caller without `supply-chain-impact:read` MUST receive the existing standard
authorization-failure behavior on any retrieval endpoint; a caller without
`supply-chain-impact:evaluate` MUST receive the same standard
authorization-failure behavior on the evaluate operation — **holding
`supply-chain-impact:read` does not, by itself, authorize creating a new
Decision Evaluation** (PAD-003 §4a, non-compositional scopes). A caller may
not supply a `tenant_id` to influence which tenant's data is read or which
tenant a new Decision Evaluation is created under (PAD-003 §8). No Gate F
endpoint, under either scope, accepts or exposes any parameter that could
trigger `entity-resolution:decide`-scoped behavior (PAD-003 §7). No Gate F
endpoint, under either scope, accepts an approval, rejection, or execution
instruction of any kind — there is no code path for one to exist (PAD-003
§3a, §10).

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

**F5.1 correction (binding)**: criteria 1 and 5 are corrected below to
reflect the read/evaluate split (PAD-003 §2a-§4a); criteria 9-15 are added
per the Product Owner's Gate F F5.1 Decision 2/Part 8, testing both
authorities explicitly.

**Evaluate acceptance:**

1. A Gate F **evaluate** request for an at-risk Supplier, authorized under
   `supply-chain-impact:evaluate`, returns a dependency chain (Material,
   Product/BOM, Facility) derived via Ask CTEC traversal, with no traversal
   result persisted as a new canonical artifact.
2. Alternate-supplier qualification/capacity/lead-time/cost are represented
   as `assertions` attached to per-(candidate, material) `institutional_relationships`
   instances via `institutional_relationship_assertions` (§9, §16 item 3) —
   not as caller-supplied request fields, and not as unscoped `assertions`
   that could collide across materials/candidates.
3. One `decision_evaluations` row is created per governed Gate F evaluation;
   one or more `decision_evaluation_records` rows (one per recommended
   Material/Alternate-Supplier/allocation unit — §16 item 4) reference it via
   `decision_evaluation_id`; exactly one `governance_evaluation_records` row
   references the same group via `governed_record_reference`/`governed_record_type`
   (§16 item 5) — not per-unit.
4. The governance-standing output is exactly `HUMAN_APPROVAL_REQUIRED` or its
   absence — no other action-implying state is producible (§12's
   `REQUIRES_REVIEW` → `HUMAN_APPROVAL_REQUIRED` projection applies).
9. A caller without any token is denied on the evaluate endpoint.
10. A caller holding only `supply-chain-impact:read` (no `:evaluate`) is
    denied when attempting to create a new Decision Evaluation — `:read`
    does not imply `:evaluate` (PAD-003 §4a).
11. A caller holding `supply-chain-impact:evaluate` may perform the
    evaluation; tenant authority for the created `decision_evaluations` row
    originates exclusively from `TrustedPrincipal`; a client-supplied tenant
    value is ignored/rejected (PAD-003 §8).
12. No approval, rejection, or execution operation exists on the evaluate
    endpoint or anywhere in Gate F's API surface (§27).

**Read acceptance:**

5. Every Gate F retrieval endpoint requires `supply-chain-impact:read`; none
   accept or grant `entity-resolution:decide`.
13. A caller without any token is denied on every read endpoint.
14. A caller holding `supply-chain-impact:read` can retrieve a
    previously-created Decision Evaluation and its results; a caller holding
    only `supply-chain-impact:evaluate` (no `:read`) is denied general
    retrieval of *other*, previously-existing Decision Evaluations — except
    for the single-response carve-out in PAD-003 §4a (an evaluate call's own
    freshly-created result).
15. A caller from the wrong tenant is denied retrieval of another tenant's
    Decision Evaluation.

**Shared acceptance (both scopes):**

6. Tenant scoping: `decision_evaluations.tenant_id` is DB-constrained;
   every child `decision_evaluation_records` row's own resolved tenant
   (via its existing indirect entity-join pattern) is verified at the
   application layer to match its group's `tenant_id` (§16 item 7, §19); no
   cross-tenant read or evaluate is possible via that verification.
7. `runtime/orchestration.py`'s six-port contract and `runtime/recovery.py`'s
   `STAGES` tuple are unmodified.
8. `/demo/supplier-risk` and its scenario/rule files are unmodified.

## 29. Automated test requirements (for implementation time, not authorized by F2)

Domain: new-adapter unit tests for qualification/capacity/lead-time/cost
derivation, following the CDD-011 adapter test pattern. Persistence:
assertion/decision/governance record creation and tenant-isolation tests,
following `test_institutional_relationship_tenant_migration_postgres.py`'s
pattern — **including an explicit cardinality test** (F2.1/F2.2 addition)
that constructs the multi-material/multi-candidate case (§16) and asserts
that per-pair facts do not collide and that all `decision_evaluation_records`
rows for one evaluation correctly reference the same `decision_evaluations`
group, with exactly one `governance_evaluation_records` row per group — plus
a migration test for the new `decision_evaluations` table and
`decision_evaluation_records.decision_evaluation_id` column, and a
tenant-isolation test asserting the §16 item 7 / §19 invariant is rejected
when violated. Security: scope-enforcement tests for **both**
`supply-chain-impact:read` and `supply-chain-impact:evaluate` (F5.1
correction), following `test_supplier_risk_api_security.py`'s pattern,
including an explicit test that `:read` does not imply `:evaluate` and
`:evaluate` does not imply general `:read` (PAD-003 §4a), and an explicit
negative test that no Gate F endpoint, under either scope, accepts or is
reachable via `entity-resolution:decide`. Architecture-drift: a Gate-F
equivalent of
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

## 31. Authorized Business Artifacts (F5.1 addition — CDD Template v2.2 §7)

**None authorized.** Gate F implements released BCS capability semantics
(ERM-001, SRM-001, ASM-001, KRM-001, DRM-001, GRM-001) and RFC-017's
released semantic vocabulary; it creates no new Business Capability
Specification or other business-authority artifact. This matches CDD-011
§5's identical precedent exactly.

## 32. Authorized External Contracts (F5.1 addition — CDD Template v2.2 §8)

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| Gate F read/evaluate API package marker — `backend/app/api/supply_chain_impact/__init__.py` | CREATE | PAD-003 v1.0 (§2a-§4a) | Define the bounded Gate F API package. | No product exports beyond the router. | Import/file-boundary test. |
| Gate F API router — `backend/app/api/supply_chain_impact/router.py` | CREATE | PAD-003 v1.0 (§2a-§4a); CDD-013 v1.0 pattern | Expose the READ endpoint(s) (§21 item 1) under `supply-chain-impact:read` and the GOVERNED EVALUATION endpoint (§21 item 2) under `supply-chain-impact:evaluate`, using the existing `_authorize()` pattern. | No approval, rejection, or execution endpoint (PAD-003 §3a, §10). No endpoint reachable via `entity-resolution:decide`. | Security tests (§29); acceptance criteria 9-15 (§28). |
| Gate F API request/response schemas — `backend/app/api/supply_chain_impact/schemas.py` | CREATE | CDD-015 §16, §21 | Define the evaluate-request and read/evaluate-response contracts (dependency chain, evaluated alternates, recommendation, governance standing). | No field accepts an approval/rejection/execution instruction (§25). No field accepts a client-supplied `tenant_id` (§19, PAD-003 §8). | Schema validation tests. |
| Gate F API scope dependency — `backend/app/api/supply_chain_impact/dependencies.py` | CREATE | PAD-003 v1.0 (§2a-§4a) | Wire `TrustedPrincipal`/container dependencies for the new router, following the `api/supplier_risk/dependencies.py` pattern. | No new authentication mechanism (PAD-003 §11, unchanged from Gate E). | Dependency-injection tests. |

No other external contract is authorized. This authorization set implements
the read/evaluate split (§21) precisely: the router and schemas exist to
carry the two distinct scopes, not to introduce a third undifferentiated
surface.

## 33. Authorized Persistence Artifacts (F5.1 addition — CDD Template v2.2 §9)

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| Migration — `backend/app/infrastructure/persistence/migrations/versions/0013_decision_evaluation_group.py` | CREATE | CDD-015 §16 items 1-2 | Create `decision_evaluations` (direct `tenant_id`, `decision_evaluation_id` PK, nullable `logical_execution_id` audit column per §16 item 1, §8 F5 recommendation) and add the nullable `decision_evaluation_records.decision_evaluation_id` foreign-key column (§16 item 2). | No structural change to any other existing table. No new column on `governance_evaluation_records` (§16 item 5 — its existing polymorphic reference is reused unchanged). No `NOT NULL` retrofit of existing rows. | Migration test; backward-compatibility test confirming existing CDD-011 rows remain valid with the column NULL. |
| Decision Evaluation group model — `backend/app/infrastructure/persistence/models/decision_evaluation.py` | MODIFY | CDD-015 §16 items 1-2 | Add the `DecisionEvaluationGroupORM` model (or equivalent class in this file) for `decision_evaluations`, and add the `decision_evaluation_id` field to the existing `DecisionEvaluationORM`. | No change to any other existing column, constraint, or the table's existing DB-level immutability trigger. No FK to `runtime_executions` on `logical_execution_id` (§8 F5 recommendation: non-FK stable association). | Model test. |
| Decision repository — `backend/app/infrastructure/persistence/decision_repository.py` | MODIFY | CDD-015 §16 | Add create/query methods for `decision_evaluations` rows and for retrieving all `decision_evaluation_records` belonging to one group. | No change to existing `DecisionEvaluationRepositoryImpl` behavior for CDD-011's existing single-material callers. | Repository test; cardinality test. |
| Decision application request model — `backend/app/application/decision_engine.py` | MODIFY | CDD-015 §16 item 2 | Add an optional `decision_evaluation_id` field to `DecisionEvaluationRequest`, mirroring its existing `business_context_reference` field, threaded through to the ORM. | `business_context_reference` itself is not repurposed as Gate F correlation (Product Owner Gate F F2.2/F4 Decision, restated binding here). | Request/response contract test. |
| Ontology seed — `backend/app/infrastructure/persistence/ontology_seed.py` | MODIFY | RFC-017 v1.0 §3, §6 | Append exactly three tuples to `REQUIRED_RELATIONSHIPS`: `("assembledAt","Product","Facility")`, `("coveredBy","Material","Contract")`, `("candidateFor","Alternate Supplier","Material")`. | `ONTOLOGY_SEED_VERSION` MUST NOT be bumped (would break idempotency of the ten already-ratified concepts/seven already-ratified relationship types, RFC-017 §6). No new concept added (RFC-017 §1: zero new concepts). No production-startup wiring change (Product Owner Gate F F5.1 Decision 5 — explicitly deferred, not authorized here). | Ontology seed test extension (idempotency + correct domain/range bindings). |
| Gate F contextual-fact adapters — `backend/app/integration/adapters/gate_f/{__init__.py,krm.py,drm.py,grm.py}` | CREATE | CDD-015 §9-§12 | New, separate adapter package (distinct from CDD-011's existing `integration/adapters/{krm,drm,grm}.py`, to avoid any regression risk to the existing, implemented supplier-risk pipeline — §27) implementing: qualification/capacity/lead-time/cost derivation as `institutional_relationship_assertions` via `candidateFor` relationship instances (§9); DRM policy evaluation producing `decision_evaluation_records` (§11, §16 item 4); GRM evaluation producing the one `governance_evaluation_records` row per group with the `REQUIRES_REVIEW` → `HUMAN_APPROVAL_REQUIRED` projection (§12) and `governed_record_type = "DecisionEvaluation"` (no space — §16 item 5, distinct from CDD-011's existing `"Decision Evaluation"` per-record string). | No modification to CDD-011's existing `integration/adapters/{erm,srm,asm,krm,drm,grm}.py`. No modification to the shared `domain/governance_engine/model.py` `GovernanceOutcome` enum (Product Owner Gate F F5.1 Decision 3, binding). No seventh cognitive-engine port (§7, §20). | Domain/adapter unit tests; cardinality test. |
| Gate F traversal orchestration — `backend/app/application/supply_chain_impact_api.py` | CREATE | CDD-015 §8, §14 (F5 recommendation) | New, separate orchestration entry point (distinct from `application/ontology_copilot_api.py`, which remains scoped to Ask CTEC only) that loads the tenant graph once and calls the existing `find_paths_to_target_type` once per chain segment (Supplier→Material→Product/BOM→Facility, Product→Revenue-Exposure, Alternate-Supplier via `candidateFor`), then hands results to the §9-§12 adapters. | No modification to `domain/ontology_copilot/traversal.py` or `application/ontology_copilot_api.py`. No traversal result persisted as a new canonical artifact (§28 criterion 1). | Traversal-integration test (§29's identified gap, now authorized here for creation). |
| Gate F pipeline factory — `backend/app/integration/gate_f_pipeline.py` | CREATE | CDD-015 §7 (CDD-011 pattern reuse) | Construct the Gate F adapter set and return the in-process dependency set, mirroring `integration/pipeline.py`'s existing CDD-011 factory pattern. | No alternate cognitive-engine port order; no bypass of the existing six-port `CapabilityStepPorts` contract (§7, §20). | Integration test. |

All existing domain services, models, and CDD-011 adapters are READ-ONLY
implementation dependencies under this authorization — Gate F's new
artifacts may call them but may not alter their business behavior, matching
CDD-011 §8's identical precedent for its own dependencies. No other
persistence source file, ORM model, migration, schema, index, or database
configuration beyond the table above may be created or modified. Each new
adapter owns one capability-local transaction, following the existing
`SqlAlchemyCapabilityPersistence` pattern (§27, F5 §27 recommendation) — no
new cross-cutting distributed transaction is authorized.

## 34. Authorized Configuration Artifacts (F5.1 addition — CDD Template v2.2 §10)

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| Keycloak realm configuration — `keycloak/ctec-realm.json` | MODIFY | PAD-003 v1.0 §2a-§2b, §9 | Add two new client-scope blocks (`supply-chain-impact:read`, `supply-chain-impact:evaluate`), following the existing per-scope block pattern (e.g. the `supplier-risk:read` block), and add both to the demo persona's granted-scopes list per PAD-003 §9/Product Owner Gate F F5.1 Decision 5. | No change to any existing scope block (`supplier-risk:*`, `entity-resolution:*`, `ontology-copilot:ask`). No grant of `entity-resolution:decide` to the demo persona (unchanged, PAD-003 §7, §18). | Manual/negative security tests. |
| DRM policy configuration — `backend/app/domain/decision_engine/configuration.py` | MODIFY | CDD-015 §11 | Add a Gate F materiality-threshold policy-configuration entry, replacing the frontend prototype's hardcoded `MATERIALITY_THRESHOLD_USD` (§23) with a governed configuration value. | No change to any existing DRM configuration entry used by CDD-011. No business-semantics change beyond representing the existing prototype threshold as governed configuration. | Domain unit test. |

No other configuration file, environment key, loader, or validator is
authorized. Runtime/application startup composition, deployment
configuration, and environment provisioning beyond the two entries above are
explicitly out of scope (Product Owner Gate F F5.1 Decision 5 — ontology
seeder startup wiring is deferred, not authorized here).

## 35. Authorized Test Artifacts (F5.1 addition — CDD Template v2.2 §11)

| Path | Action | Required coverage |
|---|---|---|
| `backend/app/tests/test_decision_evaluation_group_migration.py` | CREATE | Migration correctness; backward compatibility (existing CDD-011 rows valid with `decision_evaluation_id` NULL); index/FK presence. |
| `backend/app/tests/test_gate_f_cardinality.py` | CREATE | The multi-material/multi-candidate case (§16): per-pair facts via `institutional_relationship_assertions` do not collide; all `decision_evaluation_records` for one evaluation reference the same `decision_evaluations` group; exactly one `governance_evaluation_records` row per group. |
| `backend/app/tests/test_gate_f_adapters.py` | CREATE | New KRM/DRM/GRM adapter unit tests (§9-§12), following the CDD-011 `test_capability_adapters.py` pattern; explicit assertion that GRM can only produce `REQUIRES_REVIEW`/its absence, never `COMPLIANT`/`NON_COMPLIANT`/`EXCEPTION_GRANTED` for a Gate F evaluation. |
| `backend/app/tests/test_gate_f_traversal_orchestration.py` | CREATE | Multi-segment traversal correctness (Supplier→Material→Product/BOM→Facility→Revenue-Exposure→Candidate-Supplier); confirms no traversal result is persisted as a new canonical artifact (§28 criterion 1). |
| `backend/app/tests/test_gate_f_tenant_isolation.py` | CREATE | The §16 item 7/§19 tenant invariant is rejected when violated. |
| `backend/app/tests/test_gate_f_api_security.py` | CREATE | Both scopes independently: missing token, wrong scope, `:read` does not imply `:evaluate` and vice versa (PAD-003 §4a), wrong tenant, `entity-resolution:decide` unreachable — following the `test_supplier_risk_api_security.py` 3-pattern template. Acceptance criteria 9-15 (§28). |
| `backend/app/tests/test_gate_f_replay_recovery.py` | CREATE | Gate F's adapters participate correctly in the existing two-case (fresh/resume) replay model (§20); `decision_evaluation_id` stability across a simulated resume. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Extend the existing six-stage allowlist/architecture-drift assertions (`test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists`) to confirm no seventh stage was introduced by Gate F's new adapters. |
| `frontend/tests/supply-chain-impact-api-client.test.ts` | CREATE | New Gate F frontend API client, following the existing per-capability client test pattern. |
| `frontend/tests/supply-chain-impact-accessibility.test.tsx` | CREATE | Accessibility check, following `supplier-risk-accessibility.test.tsx`'s pattern. |

No other test artifact is authorized. `/demo/supplier-risk`'s existing test
files (`demo-supplier-risk-*.test.tsx`) are explicitly READ-ONLY reference
material under this CDD — none may be modified (§23, §28 criterion 8).

## 36. Non-claims

This CDD does not itself authorize any canonical semantic vocabulary (see
RFC-017) or any access scope (see PAD-003) — it cites both and relies on
their authorization. It does not modify CDD-010's six-stage contract, any
existing CDD-004–014 boundary, PAD-001, PAD-002, RFC-015, or RFC-016. **This
CDD does directly authorize** the noncanonical runtime persistence extension
in §16-17 (the `decision_evaluations` table and
`decision_evaluation_records.decision_evaluation_id` column) on its own
authority, per the CDD-008/009/012 precedent (§17) — this is not a canonical
change and is explicitly distinguished from RFC-017's scope (§17's
canonical-vs-runtime distinction). **F5.1 addition**: §31-35 above are this
CDD's exhaustive CDD Template v2.2 artifact-authorization records — no
artifact outside those records may be created, modified, or deleted under
this CDD's authority (Template v2.2 §18-19, "omission grants no
permission"). It does not modify `domain/governance_engine/model.py`'s
`GovernanceOutcome` enum (Product Owner Gate F F5.1 Decision 3). It does not
authorize implementation; F5.1 remains architecture/governance remediation
only — no code may be written under this authorization until a separate,
explicit Product Owner implementation-planning authorization is given
(unchanged from §32/F4).

## 37. Authorization

Authorized by CTEC Product Owner Manoj Nair on 2026-08-18: this Work Order's
capability contract (§1-30, §36) as the governing architecture for Gate F
("Governed Supply Chain Impact & Mitigation Decision"), following Gate F F0
through F3 architecture review and the Gate F F3 release-candidate
consistency and dependency verification; publication alongside RFC-017 and
PAD-003 as part of architecture baseline v1.11 (this authorization).
**Amended by Product Owner authorization, Gate F F5.1 governance
remediation, 2026-08-18**: the exhaustive CDD Template v2.2 artifact
authorization records in §31-35 (closing the F5-identified template
compliance gap); the read/evaluate operation split in §18, §21, §25, §28
(closing the F5-identified authorization-model gap, per PAD-003's parallel
amendment); and the `REQUIRES_REVIEW` → `HUMAN_APPROVAL_REQUIRED` mapping
clarification in §12 (Product Owner Gate F F5.1 Decisions 1-3).
**This authorization covers the architecture contract only.** CDD Gate:
FROZEN; Implementation State: NOT STARTED (per `architecture/INDEX.md`).
No implementation, migration, seed, scope, API, or frontend work is
authorized by this document — a separate, explicit Product Owner
implementation-planning authorization is required before any such work
begins, consistent with §36's non-claims.
