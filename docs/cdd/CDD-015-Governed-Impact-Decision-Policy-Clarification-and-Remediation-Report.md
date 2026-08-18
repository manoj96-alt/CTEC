# CDD-015 — Governed Impact Decision Policy Clarification and Remediation Report

Version: 1.0
Status: APPROVED CLARIFICATION
Authority base: `75d289dc804ce3706c696cfcb35a3e2c4be023ff`

## Decision

This report resolves the Gate F F-I2.1/F-I2.2/F-I2.2A/F-I2.2B governance review findings. It
clarifies CDD-015's existing text and closes one narrow authorization gap; it introduces no new
canonical vocabulary (RFC-017 unchanged), no new access scope (PAD-003 unchanged), and no new
persistence schema. It follows the CDD-013 Business-Facing API Contract Clarification and
Remediation Report precedent: a standalone companion document to an already-FROZEN CDD, not an
edit to CDD-015 itself, and not a new architecture baseline.

## Resolved items

**A/B — Governance and decision repository public contracts.** `governance_repository.py` is
authorized for the narrow addition of one entry to its existing `GOVERNED_RECORD_MODELS` dict:
`"DecisionEvaluation": DecisionEvaluationGroupORM`, so `GovernanceEvaluationRepositoryImpl.append()`
can persist the CDD-015 §16 item 5 governance record through its existing public contract. No other
change to that file is authorized. `decision_repository.py` was already authorized for modification
by CDD-015 §33; this report clarifies that Gate F decision persistence must use an added public
method there, not `DecisionEvaluationRepositoryImpl._to_orm` directly. Gate F production code MUST
NOT call either repository's `_to_orm` directly under any circumstance.

**C/D — Materiality.** `MATERIALITY_THRESHOLD_USD = 10_000_000`, confirmed at
`frontend/lib/demo/decision-rules.ts:11`. Comparison operator, confirmed at
`decision-rules.ts:50-51`: strictly greater-than (`>`). Subject: **annual revenue exposure**
(`revenue.annualRevenueUsd`) only. `$9,999,999` → condition false. `$10,000,000` → condition false.
`$10,000,001` → condition true. Candidate supplier cost has no role in this condition.

**E/F — Lead time and candidate cost.** Both remain decision evidence/context only. Neither
independently determines `RECOMMENDED`/`REJECTED`. No lead-time or candidate-cost acceptance
threshold is authorized.

**G — Qualification/capacity.** Confirmed directly from prototype source
(`decision-rules.ts:52-54`): `alternateHasCapacity = candidate.qualificationStatus === "Qualified"
&& candidate.availableCapacityPct > 0`. This is the fourth of four required prototype conditions,
mapped onto Gate F's governed `qualified`/`capacity_sufficient` candidate facts. No new policy
invented.

**H/I — High-severity disruption (new governed fact, minimum representation).** Reuses the
existing `Risk Event` concept (already governed, `ontology_seed.py:46`, reached via the existing
`exposedTo`/`locatedIn` chain CDD-015 §4 already cites) and the existing physical `assertions`
mechanism (already used by Gate F for candidate facts, CDD-015 §9): a literal assertion,
`subject_entity_id` = the Risk Event entity, `predicate = "severity"`, `object_value` = a governed
value (e.g. `"Severe"`), `assertion_type = "Institutional"` or `"Evidence-backed"` per its actual
source. **No new relationship type, no new concept, no RFC-017 change** — `assertions.predicate` is
free-text MVP-curated metadata (RFC-017 §5, same status as Gate F's existing `qualification`/
`capacity`/`leadTimeDays`/`costUsd` predicates), not an RFC-governed vocabulary term.

**J — Sourcing concentration (derived fact, no new vocabulary).** Single-source vs. multi-source
is **derived**, not separately asserted: count currently valid `supplies` relationship instances
(`institutional_relationships` rows with `relationship_type_name = "supplies"`,
`to_entity_id` = the impacted Material) targeting that Material, filtered to
`lifecycle_state = "Active"`, `governance_status = "Approved"`, and currently effective
(`effective_from <= now` and (`effective_to IS NULL` or `effective_to > now`)) — the same
currentness discipline RFC-011 already establishes elsewhere in this system. Exactly one such
relationship → single-sourced. More than one → multi-sourced. No allocation-percentage field is
introduced; `supplies` already means "an actual, current sourcing relationship" (RFC-017 §3c), so
counting valid instances is a safe, direct derivation from existing governed state. **No new
relationship type, no new assertion, no RFC-017 change.**

**K — Binary DRM policy.** Gate F's governed recommendation is **binary**:
`RECOMMENDED` or `REJECTED`. Gate F does not use `CANDIDATE` as a policy outcome. All four
conditions (high-severity disruption, single-source exposure, revenue exposure > $10,000,000,
qualified alternate with sufficient capacity) are combined with logical AND, mirroring the
prototype's `conditions.every(passed)` exactly.

**L — UNKNOWN ≠ FALSE.** A required condition may be positively **True**, positively **False**, or
**Unknown** (insufficient governed evidence to establish it). Decision rule, resolving the AND-gate
precisely:

- If **any** condition is positively established False → `REJECTED`, regardless of the other
  conditions' status (known or unknown). A single confirmed-false condition is sufficient under AND
  logic.
- Else if **all four** conditions are positively established True → `RECOMMENDED`.
- Else (no condition is positively False, and at least one is Unknown) → **no
  `decision_evaluation_records` row is created for that unit.** This reuses CDD-015 §16 item 6's
  existing "considered but not selected... represented implicitly (absence... not by a dedicated
  rejection/exclusion flag)" precedent, extended to "cannot be autonomously decided." No new shared
  enum is introduced — `domain/decision_engine/model.py`'s `EvaluationOutcome` and
  `domain/governance_engine/model.py`'s `GovernanceOutcome` are both unmodified. The Gate F
  application-layer result (`application/supply_chain_impact_api.py`'s own, non-shared result
  types — the same pattern already established for `GateFGovernanceStanding`, CDD-015 §12) MUST
  distinguish, per evaluated unit, "not recommended: `<false condition>`" from "insufficient
  governed evidence: `<unknown condition(s)>`" for explainability — this distinction lives entirely
  in Gate F's own application layer, not in any shared persisted domain concept.

**M — No alternate.** "No alternate supplier exists" is a known business condition, distinct from
missing evidence: when candidate discovery (an existing `Alternate Supplier`-typed entity search
within the tenant) completes successfully and finds zero governed candidates for an impacted
Material, condition 4 (qualified alternate with sufficient capacity) is **positively established
False** — not unknown — because the search itself, and its zero-result outcome, is preserved
evidence of a definite negative fact. Per Amendment L's rule, a single positively-false condition is
sufficient to persist `REJECTED` for that Material, regardless of whether conditions 1-3 are known.
This differs from "zero candidates submitted without discovery having run," which remains Unknown
(Amendment L), not False.

**N — RECOMMENDED / REJECTED mapping.** Fully specified by Amendments K, L, and M above.

**O/P — GRM and HUMAN_APPROVAL_REQUIRED.** Unchanged from CDD-015 §12 (F5.1 correction): a
governed `RECOMMENDED` **or** `REJECTED` DRM result both continue through the existing GRM
boundary, producing the existing, unmodified `GovernanceOutcome.REQUIRES_REVIEW` internal outcome,
projected at Gate F's application layer to `HUMAN_APPROVAL_REQUIRED`. Even a `RECOMMENDED` DRM
result means "CTEC recommends this mitigation, but a human authority must approve the action" — no
approval, rejection, or execution capability is authorized by this report or by CDD-015.

**Q — Policy reference/version.** The four-condition binary rule (Amendments G, H/I, J, K, L, M) is
one governed Gate F policy version. `GATE_F_POLICY_REFERENCE`/`GATE_F_POLICY_VERSION`
(`domain/decision_engine/configuration.py`, CDD-015 §34) identify it; any future change to the four
conditions, the $10M threshold, the `>` operator, qualification/capacity semantics, or the binary
mapping requires a `GATE_F_POLICY_VERSION` bump. No generalized policy-management platform is
authorized or required — version-string discipline on the existing, already-persisted
`governing_policy_reference`/`policy_version` columns is the complete, sufficient mechanism.

**R — Future API authority boundary.** A future F-I3 external contract may identify the evaluation
target (which Supplier) and other explicitly governed request context, but MUST NOT make external
request fields authoritative for qualification, capacity, lead time, cost, disruption severity,
sourcing concentration, tenant, recommendation, or governance result. All decision-relevant facts
must be derived/read from governed CTEC state (existing or seeded assertions/relationships) by the
evaluation service itself. Tenant remains derived exclusively from `TrustedPrincipal.tenant_id`.

## Compatibility and boundaries

- No modification to RFC-017: both new facts (disruption severity, sourcing concentration) reuse
  existing concepts (`Risk Event`, `Supplier`, `Material`), the existing physical `assertions`
  mechanism's free-text predicate field, and the existing `institutional_relationships` currentness
  fields (`lifecycle_state`, `governance_status`, `effective_from`, `effective_to`) — no new
  relationship type, no new concept, no new canonical attribute.
- No modification to PAD-003: no new access scope, no new endpoint, no change to identity or
  runtime trust boundaries.
- No modification to `docs/cdd/CDD-015-Governed-Supply-Chain-Impact-and-Mitigation-Decision.md`
  itself — this report clarifies it, following the CDD-013 precedent exactly.
- No modification to `architecture/released/*` and no new architecture baseline. The only
  genuinely new/revised RFC/PAD-tier (checksum-tracked, Authoritative-artifacts-table) document
  historically associated with a baseline bump is not present here — this remediation is scoped
  entirely within CDD-015's own, non-baseline-tracked "Governed implementation work orders" entry
  (`architecture/INDEX.md`, confirmed structurally exempt from `scripts/verify_architecture_release.py`'s
  governance-combination and per-baseline manifest checks, which apply only to rows carrying
  `Status`/`Current`/`Authority` columns and `released/v1.\d+/` locations — neither of which this
  report's registry entry has).
- `domain/decision_engine/model.py`'s `EvaluationOutcome` and `domain/governance_engine/model.py`'s
  `GovernanceOutcome` remain unmodified (Amendment L).

## Validation and rollback

Implementation under this report must pass: the migration/persistence/tenant-isolation/semantic
tests already established for Gate F F-I1/F-I2, a new repository-contract test proving
`GovernanceEvaluationRepositoryImpl.append()` accepts `"DecisionEvaluation"` only when the
referenced group exists and rejects it otherwise while every existing governed-record type remains
unaffected, an architecture test proving no Gate F production code calls either repository's
`_to_orm` directly, materiality boundary tests at $9,999,999/$10,000,000/$10,000,001, a test proving
candidate cost changes never alter materiality classification, a test proving lead-time changes
never independently alter the governed recommendation, and provenance tests proving persisted
candidate-fact assertions retain their candidate/material relationship, predicate, value, and
source. Rollback reverts only the additive persistence/policy implementation described here;
existing F-I1 persistence and CDD-011's supplier-risk pipeline remain unaffected and unmodified.
