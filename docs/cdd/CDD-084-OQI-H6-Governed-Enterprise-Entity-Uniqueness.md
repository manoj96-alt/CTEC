# CDD-084 — OQI-H6: Governed Enterprise-Entity Uniqueness

Version: 1.0 FROZEN
Status: FROZEN (architecture — implementation authorized only via the companion Artifact Authorization)
Implementation state: NOT STARTED
Governing authorities: CDD-046 (OQI-H0, Nine-Dimension Architecture — read-only consumed, never modified),
CDD-047 (H1 Coverage/Reliance generalization), CDD-048 (H2 Accuracy/Reasonableness/Finding-origin
generalization), CDD-049 (H3 Conformity), CDD-050 + Artifact Authorization + R1 (H4 Integrity, tenant
isolation), CDD-051 + Artifact Authorization + its two amendments + CDD-057 (H5 Timeliness, tenant
isolation, migration/test corrections), CDD-052/053/054/055 (OQI6/OQI4 tenant-isolation corrections),
CDD-056 (Production Explicit Evaluation Orchestration), CDD-058 (Production Governed Remediation
Orchestration) — all read directly against current `origin/main` during this phase's own discovery
(OQI-H6-DR), never assumed from memory.

Precedent phase: `OQI-H6-DR — UNIQUENESS — FINAL DISCOVERY + RESOLUTION REPORT` (same session), concluding
`PRODUCT OWNER DECISION REQUIRED BEFORE H6-G`. Both requested decisions (source-record scope; remediation
boundary) are now made (§2) and are binding inputs to this document.

**Publication note**: this document freezes the *architecture* for OQI-H6 — governed Uniqueness, scoped in
this implementation cycle to **EnterpriseEntity Uniqueness only**. It authorizes no implementation directly;
implementation is authorized only through this document's companion Artifact Authorization
(`CDD-084-OQI-H6-Governed-Enterprise-Entity-Uniqueness-Artifact-Authorization.md`), mirroring the
CDD-047/048/049/050/051 main-document/Artifact-Authorization pairing exactly.

## 1. Authoritative baseline (verified at H6-G start, re-verified before publication)

```
HEAD (this worktree):    0e2223d26697b53d84478780b814102c2bb571cb  (= origin/main, fresh worktree)
origin/main:              0e2223d26697b53d84478780b814102c2bb571cb  (unchanged since OQI-H6-DR)
GitHub main:               0e2223d26697b53d84478780b814102c2bb571cb  (independently cross-checked)
Governance branch:        oqi-h6/uniqueness (new, from origin/main, clean worktree)
User's local branch/worktree (untouched by this phase): postgres-data-model-closure/step-13,
    working tree unchanged (`?? docs/product/` only, same as at H6-DR's own start)
Highest existing CDD on origin/main: CDD-083  →  this document is CDD-084
Current migration head: 0046_oqi5_remediation_tenancy (filename
    0046_oqi5_remediation_tenant_integrity.py) — re-derived fresh, not trusted from any prior report
Current table count: 126 — re-derived fresh from `.github/workflows/ci.yml`'s own assertion and
    cross-checked against every test file asserting it (§9 of the companion Artifact Authorization)
```

No origin/main movement occurred between OQI-H6-DR and this phase. No conflicting Uniqueness governance or
implementation exists anywhere on `origin/main` (re-confirmed: zero `oqi_uniqueness*` paths, no CDD numbered
084 or higher existed before this document).

## 2. Product Owner decisions (binding inputs, restated exactly as received)

**PO-1 — Implementation scope.** H6 implements **EnterpriseEntity Uniqueness only**. Source-record
Uniqueness (`DUPLICATE_SOURCE_RECORD_CANDIDATE`) remains part of CDD-046's target architecture but is
**deferred, not cancelled** — blocked on a real prerequisite this phase re-confirms (§3). A future, separate
`SOURCE-RECORD-IDENTITY-DR` → `SOURCE-RECORD-IDENTITY-G` phase is required before source-record Uniqueness
can be governed.

**PO-2 — Remediation authority.** H6 is DETECT, EXPLAIN, ASSESS IMPACT, ROUTE TO STEWARD, RECORD
ADJUDICATION, RE-EVALUATE. H6 is explicitly **not** MERGE, DEACTIVATE, REPOINT, CONSOLIDATE, or any
EnterpriseEntity-identity mutation, by any actor (automatic evaluator, agent, threshold, or steward
confirmation alone). `extract_candidates(quality_dimension="UNIQUENESS")` returns zero remediation
candidates (§20).

## 3. Source-record deferral — re-confirmed, exact reason (binding)

Re-verified directly against current `origin/main` source (`backend/app/infrastructure/persistence/models/
field_value_evidence.py`): `FieldValueEvidenceORM.source_record_reference` is `String(1000)`, free text, no
uniqueness constraint, no index, no normalization, and identity only transitively tenant-scoped
(`source_field_id → source_objects.tenant_id`). There is no first-class, governed `SourceRecord` entity
anywhere in the schema. Grouping `FieldValueEvidence` rows by `(source_object_id, source_record_reference)`
and treating that grouping as a governed record identity would be exactly the "invent a pseudo-record
identity" failure mode PO-1 forbids: it is unindexed (full-table-scan cost), exact-string (no case/whitespace
normalization), and carries no dedicated governance row. H6 implementation MUST NOT construct this grouping
and MUST NOT emit `DUPLICATE_SOURCE_RECORD_CANDIDATE` under any circumstance. CDD-046 §14/§19/§21's
source-record-scope semantics remain frozen, unmodified, and unimplemented pending the named prerequisite.

## 4. Formal capability name (binding)

**OQI-H6 — Governed Enterprise-Entity Uniqueness.** Consistent with the CDD-047("H1 — Governed Quality
Coverage and Reliance Generalization")/048("H2 — Governed Accuracy, Reasonableness...")/049/050/051 naming
convention: the phase name states the governed capability, the CDD title states the exact scope boundary.
This document's title makes the EnterpriseEntity boundary explicit rather than implying full CDD-046
Uniqueness coverage.

## 5. Governing principle (restated, binding)

H6 is governed Uniqueness **quality intelligence**, not a duplicate detector. Noetva may say "these
EnterpriseEntities are candidates for duplicate review because governed evidence placed them in the
candidate set." Noetva may never say "these entities are duplicates" until a governed human steward
establishes that via adjudication (§17) — and even then, per §19, confirmation is not resolution.

## 6. Core definition (binding)

**UNIQUENESS**: the degree to which a governed enterprise subject has exactly one intended enterprise
representation, evaluated through governed, bounded candidate generation and evidence-backed duplicate
review.

**EnterpriseEntity Uniqueness (this document's exact implementation scope)**: whether two `EnterpriseEntity`
rows, within the same tenant and the same ontology `entity_type_id`, share a governed blocking-key match
strong enough to require steward adjudication as a possible duplicate representation — never itself a claim
that they are the same real-world thing.

## 7. Core invariants (binding, extending CDD-046 §41 and the H1-H5 crown, unmodified)

```
DUPLICATE CANDIDATE ≠ DUPLICATE FACT              (CDD-046 §41)
ER CANDIDATE ≠ UNIQUENESS FINDING                  (new, H6)
ER RESOLUTION ≠ DUPLICATE CONFIRMATION             (new, H6)
MATCH SCORE ≠ DUPLICATE FACT                       (new, H6 — restated from ER's own BusinessConfidence
                                                      precedent; no numeric score is ever exposed, §14)
SIMILARITY ≠ IDENTITY                              (new, H6)
NO CANDIDATE FOUND ≠ PROOF OF UNIQUENESS            (new, H6 — the central §16 distinction)
SEARCHED AND NONE FOUND ≠ COULD NOT SEARCH          (new, H6 — the SATISFIED/NOT_EVALUABLE boundary, §16-17)
CONFIRMED DUPLICATE ≠ RESOLVED DUPLICATE REPRESENTATION  (new, H6, §19)
DUPLICATE CONFIRMATION ≠ MERGE                      (new, H6, §2 PO-2)
MERGE ≠ EVIDENCE DELETION                           (new, H6 — binding on the future, separately-governed
                                                      merge capability named in §21, not itself authorized
                                                      here)
POLICY CHANGE ≠ QUALITY RESOLUTION                  (CDD-046 §36, restated for H6, §18)
AGENT INFERENCE ≠ DUPLICATE FACT                    (CDD-046 §34/§41, restated, §22)
CROSS-SOURCE REPRESENTATION ≠ DUPLICATE SOURCE RECORD  (CDD-046 §6/§14/§21 — not this document's
                                                      implementation scope, but the boundary it must never
                                                      blur when explaining why EnterpriseEntity Uniqueness
                                                      candidates are generated)
NORMALIZED FOR MATCHING ≠ GOVERNED CANONICAL         (CDD-046 §17, restated — §13's blocking key reuses ER's
                                                      matching normalization explicitly as a non-authoritative
                                                      blocking aid, never a Conformity claim)
```

Restated unmodified from CDD-046 §41 and every prior OQI phase: `MAJORITY ≠ TRUTH`, `AUTHORITY ≠ TRUTH`,
`CANDIDATE ≠ TRUTH`, `AGENT ≠ FACT`, `RECOMMENDATION ≠ AUTHORIZATION`, `AUTHORIZATION ≠ REMEDIATION`,
`REMEDIATION ≠ RESOLUTION`, `UNKNOWN ≠ LOW`, `NO FINDINGS ≠ TRUSTED`. All H1-H5 crown suites remain
unmodified and must stay green through H6 (§26).

## 8. QualityDimension (binding)

Add `UNIQUENESS` as the **eighth** `QualityDimension` member (`backend/app/domain/oqi/quality_rule.py`).
`REASONABLENESS` remains BusinessRule-shaped, unaffected. `CoverageDimension` (`backend/app/domain/
oqi_quality_coverage/policy.py`) is **not modified** — `UNIQUENESS` already exists there (CDD-047 §4); H6
adds a real dispatch branch to `has_qualifying_coverage_for_dimension` (§16) where today it unconditionally
returns `False`.

## 9. FindingStorageFamily (binding)

Add `UNIQUENESS` as the **seventh** `FindingStorageFamily` member (`backend/app/domain/oqi_finding_origin/
origin.py`), mirroring `INTEGRITY` (H4) and `TIMELINESS` (H5)'s own twice-proven additive precedent exactly.
`FindingFamily` (`app.domain.oqi_ontology_impact.evaluation`) stays permanently closed to OQI1/OQI2/OQI3,
unmodified. Uniqueness Findings integrate exclusively through the generalized `QualityFindingOrigin`
mechanism (CDD-048 §12), via new, additive `resolve_uniqueness_finding_origin`/
`resolve_uniqueness_finding_subject` methods (§14), mirroring `resolve_integrity_structural_finding_origin`/
`resolve_timeliness_finding_origin` exactly. No existing `resolve_*` method is modified.

## 10. Finding type (binding)

Exactly `DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE` (CDD-046 §19). `DUPLICATE_SOURCE_RECORD_CANDIDATE` is not
implemented (§3) and must not appear in any `CHECK` constraint, enum, or dispatch branch this document
authorizes.

## 11. Pair-subject architecture (binding)

The Uniqueness natural subject is a **canonical, evidence-bearing `EnterpriseEntity` pair** within one
tenant — first-class in persistence (§23-§25), never reduced to an arbitrary "primary" member. Re-verified
this phase, directly against current source: `OqiOntologyImpactEvaluationRepositoryImpl.resolve_finding_
subject`'s existing `FindingFamily.OQI2` branch already returns a **tuple** of `source_object_ids`/
`source_record_references` for one Finding with multiple legitimate subjects (N-source correspondence) —
proof, from the codebase itself, that a Finding legitimately having more than one propagated ontology-impact
subject is an already-established, already-shipped pattern, not a novel shape this document invents. H6's
pair (N=2) reuses this precedent (§14), not a bespoke mechanism.

## 12. Pair canonicalization (binding)

`member_a_id < member_b_id`, using PostgreSQL's native `uuid` ordering (re-verified this phase: `enterprise_
entity_id` is `Uuid()` — PostgreSQL's `uuid` type has a well-defined, deterministic total byte-order
comparison operator; `<`/`>` on `uuid` columns is stable and index-usable). A single `CHECK (member_a_id <
member_b_id)` constraint simultaneously forbids self-pairs (`A,A`, since `A < A` is false) and duplicate
mirrored pairs (`A,B` and `B,A`, since only one of `member_a_id < member_b_id` can ever hold for an ordered
pair) — no separate self-pair check is required.

## 13. Tenant isolation (binding)

Both pair members require tenant-qualified composite foreign keys — service-only filtering is explicitly
insufficient (H4's own lesson, restated: `SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT`,
`TENANT FILTERING ≠ STRUCTURAL TENANT ISOLATION`). Re-verified this phase, directly against current source:
`EnterpriseEntity.__table_args__` already carries `UniqueConstraint("tenant_id", "enterprise_entity_id",
name="uq_enterprise_entities_tenant_pk")` — the exact parent candidate key H6's composite FKs need already
exists on `origin/main`. **No prerequisite migration is required on the `EnterpriseEntity` side.** Every
H6 table referencing an `EnterpriseEntity` does so via `ForeignKeyConstraint(["tenant_id", "<column>"],
["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"], ...)`, never a plain
single-column FK.

## 14. Entity-type compatibility (binding)

By default, a candidate pair requires `member_a.entity_type_id == member_b.entity_type_id`. Re-verified this
phase: current ontology architecture (`entity_types` table, plain shared-platform vocabulary, no
tenant-scoped or governed cross-type-equivalence mechanism found anywhere in `backend/app/domain/ontology*`
or `blueprint*`) offers no governed cross-type duplicate-equivalence concept — a `Product` may never become
a duplicate candidate of a `Facility`. Entity-type compatibility is enforced at **candidate-generation time**
(bucketing scoped by `(tenant_id, entity_type_id)`, §15), not merely at Finding-persistence time, so
incompatible-type comparisons are never attempted.

## 15. Policy architecture (binding)

A new, dedicated `UniquenessPolicy` — never `QualityRule.rule_parameters` (CDD-046 §10 explicitly excludes
Uniqueness from that shape), never ER's `ResolutionPolicyDefinition` (a different authority question: ER's
own resolve/steward decisions are *evidence input* to Uniqueness per CDD-046 §21, never Uniqueness's own
governing policy), never `BusinessRule`. Tenant-owned, versioned, anchored to `entity_type_id` (a shared
platform, non-tenant-owned vocabulary member — plain FK, mirroring `information_element_requirement_id`'s
plain-FK-to-shared-platform pattern in `TimelinessPolicyORM` exactly, re-verified this phase against current
source). Exactly one `ACTIVE` policy per `(tenant_id, entity_type_id)` — a partial unique index, mirroring
`uq_oqi_timeliness_policies_one_active_per_anchor` exactly.

## 16. Blocking architecture — corrected from H6-DR's own optimistic framing (binding)

**Re-verified this phase, a load-bearing correction**: `EnterpriseEntity` persists exactly one comparable
attribute — `enterprise_entity_name` (re-confirmed directly against `backend/app/infrastructure/persistence/
models/enterprise_entity.py`: no strong-identifier column of any kind exists on this table). ER's own
strong-identifier evidence (`STRONG_IDENTIFIER_LEI`/`EXTERNAL_ID`/`TAX_REGISTRATION`) exists only as
caller-supplied, transient `SourceRepresentation` input, or buried inside a specific historical
`EnterpriseEntityResolutionRecord.evidence_profile` JSON blob per resolution case — **never as a queryable,
per-entity persisted attribute**. Building strong-identifier-based Uniqueness blocking today would require
inventing new persistence infrastructure this document does not authorize. **H6 v1's blocking strategy is
therefore fixed, not policy-configurable, to exactly one deterministic key: `canonical_name(enterprise_
entity_name)`** (reusing `app.domain.identity_resolution.normalization.canonical_name` directly, as a
non-authoritative blocking aid — `NORMALIZED FOR MATCHING ≠ GOVERNED CANONICAL`, §7 — never wired into any
Conformity claim). Strong-identifier-based blocking is explicitly named as a **deferred v2 enhancement**,
alongside source-record scope (§3), not silently dropped.

Candidate generation: `tenant scope → entity_type_id scope → bucket by canonical_name(enterprise_entity_
name) → within-bucket pairwise comparison, bounded by §17's cap`. Because the blocking key is an *exact*
normalized-name equality (not a fuzzy prefix/phonetic key), **bucket membership itself is the candidate-
qualifying evidence** (§18) — no separate fuzzy-scoring layer is required, and candidate qualification stays
fully deterministic and categorical, never "similar enough."

## 17. Bucket cap (binding)

`UniquenessPolicy.bucket_max_size` (INTEGER, `CHECK > 0`, tenant-configurable, no platform-wide default
frozen here — a genuinely tenant-specific operational tuning knob, mirroring `TimelinessPolicy`'s
`freshness_window_seconds`' own tenant-configurability). If a `(tenant_id, entity_type_id, canonical_name)`
bucket's cardinality exceeds `bucket_max_size` at evaluation time: **every entity in that oversized bucket
evaluates to `NOT_EVALUABLE` with `not_evaluable_reason = 'BUCKET_EXCEEDED_CAP'`** (§25) — never silent
truncation, never an arbitrary first-N comparison, never a fallback to all-pairs. This bounds worst-case
per-bucket comparison cost to `bucket_max_size × (bucket_max_size - 1) / 2`, never the tenant-wide
population's own `N(N-1)/2`.

## 18. Candidate qualification (binding)

A `DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE` candidate exists for an unordered pair `{A, B}` if and only if:
same tenant; same `entity_type_id`; `canonical_name(A.enterprise_entity_name) == canonical_name(B.
enterprise_entity_name)`; both within the same bounded bucket (§17). This is the entire, deterministic,
categorical qualification rule for H6 v1 — no numeric score of any kind is computed, stored, or exposed
(`MATCH SCORE ≠ DUPLICATE FACT`, §7). Strong-identifier equality (§16) is named as the v2 qualification
enhancement, not designed here.

## 19. Candidate vs. evaluation vs. Finding separation (binding)

Three layers, mirroring the H2 Reference-Evidence → Accuracy-Finding and H4/H5 policy → evaluation → Finding
precedent exactly, never collapsed:

```
UniquenessCandidate    a persisted, immutable fact: this canonical pair qualified under this policy
                        version's blocking rule. Existence alone is evidence, never itself a Finding.
UniquenessEvaluation    a persisted, immutable ledger row: this EnterpriseEntity was searched, under this
                        policy version, at this time, with this outcome (§24-§25). Required for honest
                        Coverage (§16 of the companion Artifact Authorization's crown matrix; §16 of this
                        document).
UniquenessFinding       the current-state governed quality conclusion, opened when ≥1 qualifying candidate
                        exists for either member, closed only per §20's lifecycle rule.
```

## 20. Evaluation semantics (binding)

**SATISFIED**: persisted only when an `ACTIVE` `UniquenessPolicy` existed for the entity's `entity_type_id`;
the entity's bucket was resolved and did not exceed `bucket_max_size`; the bounded within-bucket comparison
completed; and zero qualifying candidates resulted for this entity. `SEARCHED AND NONE FOUND ≠ COULD NOT
SEARCH` — an empty candidate table alone never implies SATISFIED without a persisted evaluation row proving
the search ran (§7).

**VIOLATED**: the governed Uniqueness evaluation identified at least one active `DUPLICATE_ENTERPRISE_
ENTITY_CANDIDATE` requiring adjudication for this entity. **`VIOLATED` never means "duplicate proven."**

**NOT_EVALUABLE**, two distinct causes, deliberately not conflated:
```
No ACTIVE UniquenessPolicy exists for the entity's entity_type_id  →  ZERO persisted row (mirrors
    Accuracy's own §13/CDD-046 precedent exactly — there is no policy_id to persist an evaluation under).
Policy exists, but the entity's bucket exceeds bucket_max_size      →  a PERSISTED oqi_uniqueness_
    evaluations row, outcome = 'NOT_EVALUABLE', not_evaluable_reason = 'BUCKET_EXCEEDED_CAP'. A persisted
    row is required here — not the Accuracy zero-row pattern — because a policy DID apply and a bounded
    attempt WAS genuinely made; Coverage (§16) must be able to see that an attempt occurred and honestly
    could not complete, never confusing this with "never evaluated at all."
```
This is H6's deliberate, evidence-justified divergence from both Accuracy's uniform zero-row pattern and
H5's uniform two-value (`SATISFIED`/`VIOLATED`, no `NOT_EVALUABLE` row) pattern — chosen because H6 is the
first dimension whose evaluability itself can fail *after* a policy is confirmed to apply, for a reason
(bucket-cap) requiring durable, auditable evidence.

## 21. Candidate lifecycle and steward adjudication (binding)

`oqi_uniqueness_candidates` rows are **immutable** once created (never updated, never deleted) — current
disposition is derived from the latest row in the append-only `oqi_uniqueness_adjudications` ledger for that
candidate, mirroring Entity Resolution's own `EnterpriseEntityResolutionRecord` append-only discipline
(re-verified this phase directly against `identity_resolution/service.py`'s `decide_steward_action`) and
CDD-044/CDD-042's immutable-ledger + derived-current-state pattern. Exactly two allowed adjudication
actions: `REJECT_NOT_DUPLICATE`, `CONFIRM_DUPLICATE`. **No `MERGE`. No `DEACTIVATE`** (§2 PO-2).

**Rejection persistence (binding)**: a durable `oqi_uniqueness_adjudications` row with `action =
'REJECT_NOT_DUPLICATE'` for a candidate is a governed fact this phase's own architecture requires future
candidate-generation runs to consult — re-verified this phase that ER itself provides **no** equivalent
"don't resurface" guarantee (a steward's `REJECT_MATCH` in ER produces a new, independent, append-only
record but does not structurally prevent re-proposal). H6's own adjudication ledger closes this gap
explicitly: a future candidate-generation pass for the same canonical pair, under the **same policy
version**, must not reopen a Finding already closed by a `REJECT_NOT_DUPLICATE` adjudication (§37 companion
crown U12) — because the qualifying evidence (identical normalized-name match under an unchanged policy) has
not materially changed. A **policy version change** (§18 above) is the one explicit, named condition that
legitimately makes the pair reviewable again (§22) — never mere re-running of an unchanged policy.

## 22. Rejection vs. policy change (binding)

If a steward rejects `{A, B}` under policy version `v1`, and a later policy version `v2` is activated for
the same `entity_type_id`: the candidate qualification rule itself did not change (§18's rule has no
per-version parameter for v1 beyond `bucket_max_size`, which does not affect whether a *given* pair already
in the same bucket qualifies) — so a version bump alone does not, by itself, reopen a `REJECT_NOT_DUPLICATE`
pair. The pair becomes reviewable again only if a fresh candidate-generation run under the new policy
produces a **new, distinct** `UniquenessCandidate` row for the same canonical pair (identity per §23) — which
can only happen if the underlying `enterprise_entity_name` values themselves changed (a new normalized-name
match), since `bucket_max_size` changes alone do not alter bucket *membership*, only whether membership stays
within the evaluable bound. This keeps `POLICY CHANGE ≠ QUALITY RESOLUTION` and its mirror-invariant
(policy change alone must not silently *reopen* either) both honestly satisfied by construction, not by a
special-cased rule.

## 23. Candidate identity and idempotency (binding)

`UNIQUE(tenant_id, member_a_id, member_b_id, policy_id, policy_version)` on `oqi_uniqueness_candidates` — a
repeated identical candidate-generation run converges to the same row (no-op insert), never a duplicate.
This is the deterministic identity discipline (CDD-046 §5.4) applied to a pair-shaped subject.

## 24. Finding identity (binding)

`uuid5(OQI_NAMESPACE, f"UNIQUENESS|DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE|{tenant_id}|{member_a_id}|
{member_b_id}")` — **excludes** `policy_id`/`policy_version` and any evidence value, mirroring `derive_
timeliness_finding_id`'s exact exclusion of `policy_version` (CDD-051 §17) and CDD-046 §5.4's general
identity-survives-rule-churn discipline. A policy version bump never fabricates a new semantic Finding for
the same canonical pair.

## 25. Finding lifecycle (binding)

```
First qualifying candidate for {A,B} under any policy version  →  open (or reopen) the Finding, status
    'OPEN', increment occurrence_count (first open) or reopen_count (subsequent).
Steward REJECT_NOT_DUPLICATE                                    →  close the Finding, status 'RESOLVED',
    UNLESS §22's reopen condition is independently met by a later, genuinely new candidate.
Steward CONFIRM_DUPLICATE                                       →  Finding remains 'OPEN'. Confirmation is
    governed human evidence, not remediation, and does not merge, deactivate, or otherwise change the
    underlying duplicate representation (§7: CONFIRMED DUPLICATE ≠ RESOLVED DUPLICATE REPRESENTATION).
Future, separately-governed consolidation/merge (§21)          →  still does not directly close the
    Finding. Only a fresh H6 re-evaluation demonstrating the duplicate condition no longer exists (e.g.
    the pair no longer shares a qualifying canonical-name match, because one representation was
    independently corrected) closes it (`REMEDIATION ≠ RESOLUTION`, restated).
```

## 26. OQI4 integration (binding)

New, additive `resolve_uniqueness_finding_origin`/`resolve_uniqueness_finding_subject` on
`OqiOntologyImpactEvaluationRepositoryImpl`, mirroring the H4/H5 additive precedent exactly (§9). Per §11's
re-verified N-subject precedent: **both pair members receive their own independent ontology-impact
resolution**, each producing its own `CurrentOntologyImpactORM` row referencing the **same** `finding_id` —
no arbitrary "primary" subject in persistence. When one or both members cannot map to a valid ontology-impact
subject (re-using `resolve_direct_impact`'s existing `ImpactOutcome`), the existing `IMPACT_UNKNOWN` outcome
applies per-member, never silently dropping the unresolvable member from the Finding's own subject list.

## 27. OQI6 integration (binding)

One new, narrow `UNION` branch in `compute_subject_finding_state` (`oqi_business_impact_repository.py`) for
`FindingStorageFamily.UNIQUENESS`, joined through `CurrentOntologyImpactORM.finding_family == 'UNIQUENESS'`
back to `oqi_uniqueness_findings`, mirroring the `INTEGRITY`/`TIMELINESS` branches' exact shape. Because each
pair member independently produces its own `CurrentOntologyImpact` row (§26), each member's own
`compute_subject_finding_state` call naturally observes the open Finding with zero pair-aware logic inside
OQI6 itself. **Recorded, not resolved, as accumulating technical debt** (re-verified this phase: this will
be the 4th hardcoded per-family branch in this function) — a future governance phase should assess whether a
5th dimension justifies generalizing this dispatch; H6 does not attempt that refactor.

## 28. H1 Coverage integration (binding)

`has_qualifying_coverage_for_dimension`'s existing unconditional `return False` for `UNIQUENESS` (re-verified
this phase, current source, immediately following the `TIMELINESS` branch) is replaced by a real,
existence-only, subject-scoped dispatch: **coverage is satisfied for a subject only if a qualifying
`oqi_uniqueness_evaluations` row exists for that `enterprise_entity_id`** — critically, an evaluation row
with outcome `SATISFIED` or `VIOLATED` counts; **a zero-row state (no `ACTIVE` policy, §20) does not**;
whether `NOT_EVALUABLE`-with-persisted-row (bucket-exceeded, §20) counts as qualifying coverage is frozen
here as **yes** — a genuine, bounded, policy-governed attempt was made and is auditable, satisfying the same
"at least one evaluation has run" existence predicate CDD-044 §18/CDD-046 §12.2 already generalize; it is not
the same as never having evaluated the subject at all. Candidate existence alone is never coverage
(`NO CANDIDATE FOUND ≠ PROOF OF UNIQUENESS`). Tenant-global existence is never coverage — subject-scoped
only, matching every other dimension's coverage discipline.

## 29. Remediation, agent, and orchestration integration (binding)

**Remediation**: `extract_candidates`'s existing `elif quality_dimension == "TIMELINESS": candidates =
extract_reasonableness_candidates()` branch (re-verified this phase, current source) is mirrored exactly:
`elif quality_dimension == "UNIQUENESS": candidates = extract_reasonableness_candidates()` — zero
`RemediationCandidateBasis` member, zero new `RemediationActionType`, zero external-mutation authority,
identical to Integrity's/Timeliness's own precedent (§2 PO-2).

**Agents**: the existing three roles (`EVIDENCE_CONSISTENCY_ANALYST`, `IMPACT_CONTINUITY_ANALYST`,
`RECOMMENDATION_SYNTHESIZER`) remain sufficient (CDD-046 §34, unmodified). An agent may compare candidate
evidence, explain why a pair was generated, explain ontology/business impact, and recommend steward review.
An agent may never confirm/reject on a steward's behalf, merge, deactivate, or mutate any identity.

**Production orchestration**: no new orchestrator. Re-verified this phase: `OqiEvaluationOrchestrationService
.evaluate()` already resolves `enterprise_entity_id` (via `_resolve_enterprise_entity_id(source_object_id=
...)`) for its existing Integrity Structural dispatch stage. Uniqueness slots in as one more dispatch stage,
**reusing that same already-resolved `enterprise_entity_id`**, own transaction, own commit, mirroring the
per-dimension isolation discipline CDD-056 §22 already establishes for every existing stage — no new trigger
shape, no new orchestrator entry point. This means Uniqueness re-evaluation for entity X is triggered
reactively, whenever any source record mapped to X is itself evaluated — consistent with this whole
program's "evaluate on read / explicit trigger, no scheduler" philosophy (CDD-051 §12, restated), not a
population-wide sweep.

**Ingestion**: Enterprise REST ingestion (CDD-059) does not synchronously perform any population-level
Uniqueness search. Uniqueness runs exclusively through the explicit production evaluation orchestration path
above — no hidden ingestion side effect.

## 30. API and frontend (binding, minimum scope)

**API**: the existing generic Finding-listing service (`oqi_product_experience_service.py::list_findings`)
gains one new branch mirroring the `TIMELINESS` branch's exact shape (§9's origin resolvers feed it). Because
a Uniqueness Finding's natural subject is a pair, the generic single-`entity_id` list-row (`FindingSummaryRow`)
carries `entity_id = member_a_id` as a deterministic, documented display anchor for the list view only — this
is a narrow, justified exception to §11's "no arbitrary primary subject in persistence": persistence itself
(§25-§27) treats both members equally; only this one generic list-row's single-entity display field picks a
deterministic anchor for backward-compatible rendering. A new, narrow, read-only candidate-detail endpoint is
required to render both members' matched evidence side by side (exact route/schema is an I2 implementation
detail within this document's frozen shape: tenant-scoped, returns `member_a`/`member_b` identity + name +
matched `canonical_name` value + adjudication history + per-member OQI4/OQI6 impact — no additional
authority, no write capability).

**Frontend**: `frontend/app/quality/findings/page.tsx`'s family filter gains one `<option value="UNIQUENESS">
Uniqueness</option>`, mirroring the two-line `INTEGRITY`/`TIMELINESS` precedent exactly (current source
re-verified this phase). A pair-candidate detail view (both entities, matched evidence, adjudication state,
impact) is required — the existing single-subject Finding UI cannot honestly render a pair — but its exact
visual design belongs to whatever investigation-spine pattern the WOW product-experience track (CDD-078-083)
has established; this document freezes only that the capability must exist, not its pixel-level shape.

## 31. Future merge capability (named, not designed, not authorized here)

Working name: **Governed Enterprise Entity Consolidation**. Out of scope for H6 entirely (§2 PO-2). A future,
separately governed capability must address: `InstitutionalRelationship` repointing; ER resolution history
(supersede, never delete); every open Finding across every dimension referencing either entity; ontology/
business-impact records; `BusinessDependency` criticality; remediation history; full audit/lineage;
reversibility. No CDD number is reserved here — normal governance procedure assigns one when that capability
is actually proposed.

## 32. Explicit non-goals (binding, restated for H6)

Source-record Uniqueness implementation (§3). Strong-identifier-based candidate generation (§16). Any
EnterpriseEntity merge/deactivate/consolidate capability (§31). Any numeric confidence score anywhere in the
H6 pipeline. Any probabilistic/ML/LLM duplicate determination. Any new `RemediationActionType`. Any
modification to `FindingFamily`, `RemediationCandidateBasis`, `QualityRule`, `ResolutionPolicyDefinition`,
or any existing ER domain file. Any modification to `EnterpriseEntity`'s own schema (its existing candidate
key already suffices, §13). Monetary quantification of any quality condition. A parallel product-experience
UX architecture outside the established WOW investigation-spine pattern.

## 33. STOP conditions for implementation (binding, restated for I1/I2)

I1/I2 must STOP and return for a narrow governance amendment — never improvise — if: source-record identity
work is discovered necessary despite §3's deferral; the `EnterpriseEntity` tenant-qualified candidate key
(§13) is found missing or altered from what this document verified; the canonical-pair CHECK (§12) cannot be
expressed exactly as frozen; a bucket cannot be bounded as frozen (§17) and a naive-scan fallback is
considered; candidate qualification drifts toward "similar enough" instead of §18's exact rule; `SATISFIED`
cannot be honestly distinguished from an incomplete search (§20); the evaluation ledger cannot represent a
successful zero-candidate search (§20); a rejected candidate cannot be durably remembered (§21); `CONFIRM_
DUPLICATE` is found to imply any identity mutation; the Finding lifecycle cannot preserve confirmation ≠
resolution (§25); OQI4 cannot honestly represent both pair members (§26); OQI6 cannot consume the new family
without contradiction (§27); the persistence topology, migration, or table count in the companion Artifact
Authorization proves materially wrong; implementation requires touching any path not named in that
Authorization; or any governance question is deferred for implementation convenience rather than genuinely
resolved here.

## 34. Authorization

This CDD is approved and published as FROZEN. Implementation of `OQI-H6-I1`/`OQI-H6-I2` is authorized only
against the exact path list, schema, and test matrix frozen in the companion `CDD-084-OQI-H6-Governed-
Enterprise-Entity-Uniqueness-Artifact-Authorization.md`. This document itself authorizes no code, migration,
test, seeder, API, frontend, or Docker/CI change.
