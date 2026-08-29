# CDD-041 — OQI3 I2 Provenance, Compound Semantics, and Historical Replay Amendment (OQI3-G2)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-041-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md`
(OQI3-GA — companion-amendment pattern for a defect disclosed during implementation, never an
in-place rewrite of an already-approved CDD or its Artifact Authorization),
`CDD-040-N-Source-Finding-Representation-Amendment.md` (OQI2 precedent for a companion amendment
that corrects a genuine architecture gap discovered by adversarial verification rather than
patching frozen governance silently)
Classification: ARCHITECTURE CORRECTION (provenance completeness, family-shape contradiction
resolution, and idempotency hardening; does not reopen OQI1/OQI2, does not authorize a general
rules engine, does not authorize Finding lifecycle or seed-3 CURRENT_STATE concurrency — those
remain OQI3-I3's exclusive scope)

## 1. Purpose

Freezes the architecture resolution produced by OQI3-R2 for the two P2s disclosed at the close of
OQI3-I2:

- **P2-A** — `business_rule_evaluations` persists `source_record_reference` but not
  `source_object_id`, so the frozen `SourceRecordLineageIdentity` subject cannot always be
  reconstructed from persisted Evaluation provenance alone.
- **P2-B** — CDD-041 §5 froze a singular one-comparator consequence shape for
  `CONDITIONAL_REQUIRED`/`CONDITIONAL_PROHIBITED`, which I1 faithfully implemented, but §12/§19
  and this CDD's own Artifact Authorization mandatory test matrix require compound,
  never-short-circuited simultaneous failure observations — a genuine text contradiction, not an
  implementation defect.

It additionally freezes one hardening requirement discovered as a byproduct of the same
investigation: concurrent identical HISTORICAL replay must converge idempotently rather than
surface a uniqueness `IntegrityError` to the caller.

This amendment authorizes correction of these three items. It does not reopen any other CDD-041
decision, does not touch OQI1 or OQI2, and does not authorize any OQI3-I3 (Finding lifecycle,
seed-3 CURRENT_STATE advisory authority) work.

## 2. Independent re-verification (performed fresh, not trusted from prior reports)

```
Authoritative main:        7d689a46abab35e1c931d9a57eb7bb9863bf92d8   (confirmed: local ==
                                                                        origin == GitHub API)
PR #167 head:               db3a5824c0140542ece5daf9da91cbe6ac872852  (confirmed: OPEN, base
                                                                        main, MERGEABLE, CLEAN)
CDD-041:                    95536bfeb4039ca8ae166ffcb51ce868a61847af0c46f9c0ceba393977a0b289
CDD-041 original AA:        13daab67a5e7c9a9ef79f81754254d782c6e68702acabb1c4721d33ba9e61c5c
CDD-041 GA amendment:       fb7fed368570d638d42968aa4b53b775cec397bdbc24e92e0c6a40cb6a960c88
Branch protection on main:  NONE (confirmed, `404 Branch not protected`)
```

All three pre-existing governance documents were read directly and confirmed byte-identical to
their previously recorded hashes. None is edited by this amendment.

Migration `0022_oqi3_business_rule.py` was read directly from `origin/oqi3/business-rule-quality-
intelligence` (PR #167's branch — the migration is not yet on `main`, since PR #167 is unmerged).
Confirmed directly from source:

- `business_rule_evaluations` columns are exactly: `evaluation_id`, `tenant_id`,
  `business_condition_id`, `rule_id`, `subject_type`, `source_record_reference`,
  `evaluation_mode`, `evaluation_horizon`, `input_evidence_digest`, `outcome`, `evaluated_at`.
  **No `source_object_id` column exists.** P2-A confirmed as a real persistence gap.
- `business_rule_evaluation_observations` has composite primary key exactly
  `(evaluation_id, clause_id, observation_type, input_role)`, with a chained composite FK
  `(evaluation_id, input_role) → business_rule_evaluation_inputs(evaluation_id, input_role)`.
  **This schema already supports multiple simultaneous clause observations per Evaluation with
  zero schema change** — the compound-observation gap is entirely in the domain-layer family-shape
  validator and evaluator, not the physical schema. The §22 STOP condition does not trigger.

The repository-native pattern for a table referencing `SourceObject` directly was located in
OQI2's own `ComparisonSubjectCorrespondenceMemberORM`
(`backend/app/infrastructure/persistence/models/oqi_cross_source_correspondence.py`), which already
pairs `source_object_id: Mapped[UUID]` (non-nullable, `ForeignKey("source_objects.source_object_id")`)
directly beside `source_record_reference: Mapped[str]` — the identical column pairing this
amendment now authorizes for `business_rule_evaluations`. This is not an invented pattern; it is
the established repository convention for exactly this situation.

The Artifact Authorization's original 18-path table was read directly. Every file the repair
touches — `rule.py` (#2), `evaluation.py` (#3), `oqi_business_rule_evaluation.py` (#6),
`oqi_business_rule_evaluation_repository.py` (#9), `oqi_business_rule_evaluation_service.py`
(#10), migration `0022` (#11), `test_oqi_business_rule_evaluation_domain.py` (#13),
`test_oqi_business_rule_evaluation_service.py` (#14), `test_oqi_business_rule_postgres.py` (#15)
— is already inside the **original** 18-path authorization. **Zero new files are required; the
GA amendment's +6 mechanical paths are untouched by this repair.**

## 3. Decision A — Evaluation subject provenance (P2-A)

`business_rule_evaluations.source_object_id` is **required persisted subject provenance**,
frozen as `Mapped[UUID]`, `nullable=False`, `ForeignKey("source_objects.source_object_id",
name="fk_business_rule_evaluations_source_object_id")`, positioned beside the existing
`source_record_reference` column.

**Why indirect reconstruction is rejected**, restated precisely:

1. Bound inputs may legitimately have zero qualifying evidence (`EMPTY`, per CDD-041 §18 — no
   evidence row is ever manufactured for a missing input). A `CONDITIONAL_REQUIRED` violation —
   the very case this architecture exists to detect — is exactly the case where every bound
   input can be `EMPTY`, leaving zero `business_rule_evaluation_inputs` rows with a non-null
   `field_value_evidence_id` and therefore zero FK path to any `SourceField` at all.
2. Even when evidence exists, nothing in publication validation or the evaluator enforces that
   every `source_field_id` a rule binds belongs to the same `SourceObject` as the evaluation's
   actual subject. A join through one evidenced input's `SourceField.source_object_id` is not
   structurally guaranteed to equal the subject's true `source_object_id`.
3. Immutable Evaluation provenance must be self-sufficient for subject reconstruction — it must
   not depend on the accidental presence of non-empty evidence, nor on mutable current
   `SourceField`/binding state remaining consistent with what was true at evaluation time.

An indirect `EvaluationInput → SourceField → SourceObject` path is therefore insufficient and is
rejected as the provenance mechanism. A dedicated `EvaluationSubject` snapshot table was
considered and rejected under the same minimality principle already applied throughout OQI3
(OQI3-D's rejection of a `QualityExpectation` umbrella, OQI3-R's rejection of a
`SourceFieldSemanticDefinition` concept): one column, on the one table that already carries the
sibling half of subject identity, fully closes the gap.

### 3.1 Identity firewall (binding)

Adding `source_object_id` changes **no** identity formula:

- `BusinessRuleEvaluation` deterministic identity (`derive_business_rule_evaluation_id`)
- `BusinessRuleFinding` identity (`derive_business_rule_finding_id`)
- the role-keyed input evidence digest
- `business_condition_id` semantics
- `SourceRecordLineageIdentity` subject semantics

`source_object_id` was already consumed in memory at write time when constructing
`subject_identity` for both uuid5 derivations (`canonical_single_record_subject_identity`, a
plain length-prefixed concatenation of `source_object_id` and `source_record_reference` — not a
hash). This amendment corrects **persistence completeness for read-back**, not identity
semantics. Any repair that changes an existing Evaluation or Finding identity value for
previously-persisted rows is out of scope and would itself be a governance violation.

### 3.2 Migration strategy

Migration `0022_oqi3_business_rule` is **unmerged** — PR #167 has not merged, and the migration
exists only on the PR's branch, not on authoritative `main`. This exactly mirrors OQI2's own
precedent (`0021_oqi2_cross_source` was amended in place twice, for the revision-length and
finding-type-width corrections, specifically because it was unmerged at the time). **Amend 0022
in place.** Do not create `0023`. `revision`/`down_revision` remain unchanged. This is a single
additive column plus its FK and index consequence — no new table. Expected table count after
repair remains **81**.

## 4. Decision B — Compound consequence clauses (P2-B)

### 4.1 Root cause, restated precisely

CDD-041 §5 states (verbatim intent, reproduced from OQI3-G's own frozen text): `CONDITIONAL_REQUIRED`
is `IF <applicability> THEN <input_role> MUST EXIST` and `CONDITIONAL_PROHIBITED` is
`IF <applicability> THEN <input_role> MUST NOT satisfy <predicate>` — both singular. I1's
`validate_business_rule_shape` faithfully implements exactly this: `predicate` is type-checked as
a bare `ComparatorNode` for all three families. But CDD-041 §12 and §19 both state, unchanged and
unamended by this document, that compound rules "must never short-circuit in a way that loses a
deterministic failure fact" and must "preserve every independently-established deterministic
failure fact," and the original Artifact Authorization's own mandatory test matrix requires "at
least 3" simultaneous clause failures, mirroring OQI2's N-source discipline. §5's singular shape
and §12/§19/AA's compound requirement cannot both be literally true of the same frozen document.
This is a **governance text contradiction**, not an implementation over-restriction and not test
overreach — I1's implementation is a correct, faithful reading of §5 alone.

### 4.2 Corrected family shape (frozen)

`CONDITIONAL_REQUIRED` and `CONDITIONAL_PROHIBITED` may each have a `predicate` that is **either**:

- a single `ComparatorNode` (the original §5 shape, unchanged, fully backward compatible), **or**
- an `AND`-only `CompositionNode` whose direct children are each a single, family-appropriate
  `ComparatorNode` (all `IS_NOT_NULL` for `CONDITIONAL_REQUIRED`; each a single comparator against
  its own bound input role for `CONDITIONAL_PROHIBITED`) — no nesting, no mixed connective.

`FIELD_COMPARISON` **remains strictly atomic** — exactly two input roles, one comparator, exactly
as originally frozen in §5. This amendment authorizes no compound `FIELD_COMPARISON` shape.

No connective other than `AND` is authorized for consequence composition by this amendment.
Explicitly **not authorized**: `OR`, `NOT`, nested `IMPLIES`, `XOR`, arbitrary functions, loops,
scripts, dynamic predicates, or any form of executable code. `applicability` composition rules
(already permitting `ComparatorNode | CompositionNode` since I1) are unchanged by this amendment.

### 4.3 One governed policy, not fragmented rules

The initial OQI3 business-policy model is frozen as: **one governed conditional `BusinessRule`
may represent one business policy containing multiple independently observable consequence
clauses** — never fragmented into multiple atomic `BusinessRule`s sharing one applicability
predicate merely to keep the evaluator simple. Concretely:

```
one business_condition_id
one BusinessRule version
one BusinessRuleEvaluation
zero-to-many BusinessRuleEvaluationObservation rows
one future BusinessRuleFinding (I3)
```

Future Finding semantics (I3's to implement, frozen here for continuity): if clauses A and C fail
while B succeeds, the Evaluation is `VIOLATED` with observations for A and C only; the Finding is
`OPEN`. If A is later fixed while C remains failing, the latest Evaluation is `VIOLATED` with an
observation for C alone; the Finding remains the same `OPEN` Finding — no per-clause Finding is
ever created. Once all clauses are satisfied, the Evaluation is `SATISFIED` and I3 resolves the
one stable Finding.

### 4.4 Clause and Observation identity (unchanged, confirmed sufficient)

`ComparatorNode.clause_id` already exists per-leaf in I1's frozen domain model — no schema or
domain change is required for clause identity. `BusinessRuleEvaluationObservationORM`'s composite
primary key `(evaluation_id, clause_id, observation_type, input_role)`, confirmed by direct read
of migration `0022` (§2 above), already correctly represents multiple simultaneous clause
failures with zero schema change. `BusinessRuleEvaluation` identity and the role-keyed evidence
digest are **unchanged** by this amendment: `rule_version` already pins the exact compound
executable policy in force, and compound consequence introduces no new input roles beyond those
already bound.

### 4.5 Complete failure-set semantics

For an `AND`-composed consequence, the evaluator must evaluate every clause needed to construct
the complete deterministic failure set. It must not stop after the first `FALSE` clause merely
because the overall boolean result is already determined. Example: `A=FALSE, B=TRUE, C=FALSE`
under `AND` yields overall `FALSE` (→ `VIOLATED`) with observations for **A and C only** — never
for B, which succeeded.

### 4.6 Strong Kleene three-valued semantics (frozen)

Three truth values are frozen for compound consequence evaluation: `TRUE`, `FALSE`, `UNKNOWN`
(an individual clause is `UNKNOWN` exactly when its bound evidence fails to parse under its
declared `expected_type`, per the existing CDD-041 typed-evidence contract — this amendment adds
no new source of `UNKNOWN`). Strong Kleene `AND` is frozen exactly:

```
TRUE  AND TRUE    = TRUE          FALSE AND TRUE    = FALSE      UNKNOWN AND TRUE    = UNKNOWN
TRUE  AND FALSE   = FALSE         FALSE AND FALSE   = FALSE      UNKNOWN AND FALSE   = FALSE
TRUE  AND UNKNOWN = UNKNOWN       FALSE AND UNKNOWN = FALSE      UNKNOWN AND UNKNOWN = UNKNOWN
```

No other connective's truth table is authorized as compound *consequence* composition by this
amendment (§4.2). `applicability`'s existing `AND/OR/NOT/IMPLIES` support (already valid since I1)
is unchanged; this amendment does not freeze new truth tables for those connectives in the
applicability position, since applicability already maps its own result to
`NOT_APPLICABLE`/`NOT_EVALUABLE` per CDD-041 §13 without needing per-clause observations.

Host-language (Python) truthiness must never substitute for this explicit three-valued table.

### 4.7 Top-level outcome mapping under Kleene consequence evaluation

```
applicability FALSE                          → NOT_APPLICABLE
applicability UNKNOWN                        → NOT_EVALUABLE
applicability TRUE, consequence TRUE          → SATISFIED
applicability TRUE, consequence FALSE         → VIOLATED
applicability TRUE, consequence UNKNOWN       → NOT_EVALUABLE
```

Critically: a compound consequence containing an `UNKNOWN` leaf may still resolve to overall
`FALSE` under strong Kleene `AND` (`FALSE AND UNKNOWN = FALSE`). This is `VIOLATED`, **not**
`NOT_EVALUABLE` — the whole-Evaluation result is only `NOT_EVALUABLE` when Kleene logic itself
cannot resolve the top level (i.e. the only cases reaching `UNKNOWN`: `TRUE AND UNKNOWN`, or
`UNKNOWN` on its own).

### 4.8 Observations under UNKNOWN (frozen)

An Observation may be created **only** for a clause whose failure is deterministically
established (`FALSE`). No Observation is ever created for a clause whose result is `UNKNOWN`.
Example: `A=FALSE, B=FALSE, C=UNKNOWN` under `AND` → outcome `VIOLATED`, observations for `A` and
`B` only, nothing for `C`. This is "absence of knowledge is not knowledge of absence" applied to
compound evaluation: OQI3 does not assert `C` is fine, does not assert `C` is violated — it
reports only what is deterministically known, exactly as it already does for a single-clause rule
whose sole input is `EMPTY`.

### 4.9 Whole-Evaluation NOT_EVALUABLE persistence (unchanged, reaffirmed)

When the top-level result is `NOT_EVALUABLE` (§4.7), the existing frozen non-persistence rule
applies without modification: zero `BusinessRuleEvaluation` rows, zero `EvaluationInput` rows,
zero evidence links, zero Observations, zero Finding mutation. Compound evaluation introduces no
exception to this rule.

### 4.10 OR and NOT — explicitly deferred

`OR` and `NOT` are **not authorized** as compound consequence composition by this amendment. The
following architectural principle is frozen for future reference, so that a future authorization
does not have to rediscover it: a failed alternative beneath an `OR` that is satisfied by another
allowed alternative is not itself a business-policy violation and must not produce an Observation
— "an unrealized alternative is not a violation," the direct structural analogue of OQI2's
"conflict participation ≠ blame." No implementation of compound consequence `OR` or `NOT` is
authorized by this document; a future amendment must freeze the exact semantics before either
connective may be used in consequence position.

### 4.11 IMPLIES / applicability — unchanged

The existing `applicability`/`predicate` field pair already implements the two sides of an
implication correctly: a false antecedent (`applicability`) already maps to `NOT_APPLICABLE`, not
`SATISFIED`, per CDD-041 §13. This amendment makes no change here. `IMPLIES` as an explicit AST
node remains reserved for potential future compound-applicability use, out of this amendment's
scope.

## 5. Decision C — Historical replay idempotency

### 5.1 Requirement (frozen)

Concurrent replay of an identical `HISTORICAL` evaluation (same `business_condition_id`,
`rule_version`, `subject`, `evaluation_mode=HISTORICAL`, `evaluation_horizon`, and input evidence
frontier — therefore the same deterministic `evaluation_id`) must converge on one immutable
ledger row-set. It must never expose a uniqueness `IntegrityError` to the governed caller. This is
required by CDD-041 §22's own existing text ("enforced by the natural keys ... not
application-level deduplication alone"), which the current check-then-insert repository pattern
does not satisfy for the unlocked `HISTORICAL` path (`CURRENT_STATE` is protected once OQI3-I3
installs the seed-3 advisory lock; `HISTORICAL` never takes Finding authority and has no
equivalent protection).

### 5.2 Frozen conflict-safe pattern

The repository's historical-insert path is authorized to change to:

```
INSERT INTO business_rule_evaluations (...) VALUES (...)
ON CONFLICT (evaluation_id) DO NOTHING
RETURNING evaluation_id
```

If a row is returned (this transaction won the race, or no prior row existed), proceed to insert
`EvaluationInput`, evidence links, and `Observation` rows normally, in the same transaction, exactly
as today. If no row is returned (a concurrent transaction already committed the identical,
deterministically-identical Evaluation), this transaction **must not** attempt to insert any child
rows — doing so would either violate the children's own natural-key constraints or, worse, silently
succeed and leave two purportedly-independent-but-identical child sets. Instead it re-selects the
already-committed `BusinessRuleEvaluation` (and its children, if the caller needs them) and returns
that row. This closes the race at the single point where the natural key is authoritative — the
`RETURNING`-gated conflict check on the parent row — before any child table is touched, which is
what makes the pattern safe across all four tables (`business_rule_evaluations`,
`business_rule_evaluation_inputs`, evidence links, `business_rule_evaluation_observations`) without
requiring `ON CONFLICT` handling on each child individually: only the transaction that
successfully inserts (or finds no existing) parent row ever attempts to insert children, so no
transaction can leave a partial or orphaned child set.

`ON CONFLICT DO NOTHING` used only on the parent table, gated by `RETURNING`, is confirmed
sufficient for this transaction shape — a genuinely unsafe pattern (e.g. `ON CONFLICT DO NOTHING`
applied independently and unconditionally to all four tables, which could let a losing
transaction's children silently vanish while its parent row also silently vanishes, breaking
provenance completeness) is explicitly rejected. No repair may adopt that unconditional variant.

### 5.3 OQI-P3-005 (new, recorded)

**OQI-P3-005 — Inherited unlocked historical-replay race in OQI1/OQI2.** OQI1's and OQI2's own
`evaluate_historical` paths share the identical unlocked check-then-insert race pattern that
OQI3-I2 discovered and this amendment now requires OQI3 to close for its own `HISTORICAL` path.
This is **inherited technical debt**, not a new defect introduced by OQI3, and is not authorized
or required to be fixed as part of this amendment or any OQI3 phase. OQI1 and OQI2 are **not**
reopened by this document. A future cross-cutting hardening pass may address `OQI-P3-005`
independently, at Product Owner discretion, at any point after OQI3 closes.

## 6. CURRENT_STATE concurrency (reaffirmed, not re-derived)

OQI3-I2 empirically proved, on real PostgreSQL, that sequential unlocked multi-field evidence
reads do not guarantee a coherent `CURRENT_STATE` evaluation frontier — a concurrent writer's
evidence committed between two field reads is visible to the later read. This is **reaffirmed as
an established, binding finding**, not a new open question: `CURRENT_STATE` concurrency safety is
**not optional hardening**; it is a correctness prerequisite that only OQI3-I3's seed-3 advisory
lock supplies. The frozen I3 sequence (unchanged from CDD-041 §21) is reaffirmed exactly:

```
load/validate ACTIVE BusinessRule
→ establish subject
→ compute stable Finding identity
→ acquire seed-3 pg_advisory_xact_lock
→ re-check relevant rule/subject state if required
→ select ALL evidence under one horizon
→ construct complete role-keyed frontier
→ typed interpretation
→ applicability
→ complete AST/consequence evaluation
→ derive all deterministic Observations
→ persist immutable Evaluation ledger
→ mutate BusinessRuleFinding
→ commit
```

The lock is acquired **before evidence selection** and held through Finding mutation and
transaction commit. OQI3-I2's unlocked `CURRENT_STATE` evaluation must not be described, in any
future report, as concurrency-safe on its own — its functional correctness (outcome/observation
derivation given a frontier) is proven; its concurrency safety is not, and is explicitly deferred
to OQI3-I3 by design, not by oversight.

## 7. Artifact Authorization consequence

No new file is authorized or required by this amendment. Every path the repair touches is already
within CDD-041's original 18-path Artifact Authorization (confirmed in §2 above):

```
Domain:        backend/app/domain/oqi_business_rule/rule.py                          (#2)
               backend/app/domain/oqi_business_rule/evaluation.py                     (#3)
Persistence:   backend/app/infrastructure/persistence/models/oqi_business_rule_evaluation.py  (#6)
               backend/app/infrastructure/persistence/oqi_business_rule_evaluation_repository.py (#9)
Application:   backend/app/application/oqi_business_rule_evaluation_service.py        (#10)
Migration:     backend/app/infrastructure/persistence/migrations/versions/0022_oqi3_business_rule.py (#11)
                 — amended in place; revision/down_revision unchanged; adds
                   business_rule_evaluations.source_object_id (UUID, NOT NULL,
                   FK → source_objects.source_object_id) and its index consequence only
Tests:         backend/app/tests/test_oqi_business_rule_evaluation_domain.py           (#13)
               backend/app/tests/test_oqi_business_rule_evaluation_service.py          (#14)
               backend/app/tests/test_oqi_business_rule_postgres.py                    (#15)
```

`CREATE = 0, MODIFY = 9 (subset of the original 18), DELETE = 0`. The GA amendment's separate
+6-path mechanical-migration-head authorization is untouched and irrelevant to this repair.
Expected table count after repair: **81** (column addition only; no new table; no `0023`).

### 7.1 Mandatory regression tests (binding on OQI3-I2-R)

**Provenance:**
- A CURRENT_STATE- or HISTORICAL-mode Evaluation, read back via the repository, reconstructs the
  exact original `source_object_id` matching what was supplied at write time.
- An Evaluation where every bound input is `EMPTY` (no evidence at all) still persists and
  reconstructs a complete, correct subject identity — the case indirect reconstruction could not
  handle.
- Read-back subject reconstruction does not depend on current mutable `SourceField`/binding state
  (e.g. remains correct even if a `SourceField` used elsewhere is later modified).

**Compound consequence:**
- Two independently-failing `AND` clauses on one rule → exactly two Observations, correct
  `clause_id`s, single `VIOLATED` Evaluation.
- Three independently-failing `AND` clauses → exactly three Observations (the AA's own mandatory
  ≥3-clause test, finally implementable).
- Mixed success/failure (`A=FALSE, B=TRUE, C=FALSE`) → observations for A and C only, none for B.
- `FALSE AND UNKNOWN` → `VIOLATED`, an Observation for the known-failing clause only, none for the
  `UNKNOWN` clause.
- `TRUE AND UNKNOWN` → `NOT_EVALUABLE`; zero Evaluation, zero Observations, zero Finding mutation.
- Clause order permutation does not change the outcome, the Observation set, or the Evaluation
  identity.
- `FIELD_COMPARISON` publication validation still rejects a `CompositionNode` predicate — confirms
  atomicity is preserved, not accidentally broadened.

**Historical replay:**
- Two concurrent identical `HISTORICAL` evaluations, executed against real PostgreSQL, converge to
  exactly one `BusinessRuleEvaluation` row with a complete, non-duplicated, non-orphaned child
  row-set (inputs, evidence links, observations) — no `IntegrityError` surfaced to either caller.

## 8. Not authorized by this amendment

This amendment authorizes none of the following, all of which remain exclusively OQI3-I3's scope
or explicitly deferred future work:

- `BusinessRuleFinding` lifecycle implementation (create/resolve/reopen, `resolution_basis`
  mutation, `state_revision`/`occurrence_count` mutation).
- Seed-3 advisory-lock `CURRENT_STATE` authority implementation.
- Compound `OR`, `NOT`, or nested `IMPLIES` consequence composition.
- Compound `FIELD_COMPARISON`.
- Any repair to OQI1's or OQI2's own `evaluate_historical` paths (`OQI-P3-005` is recorded, not
  fixed, and neither capability layer is reopened).
- Any change to `SourceField`, `FieldValueEvidence`, `QualityRule`, or any OQI1/OQI2 table, model,
  or semantic.
- Any OQI4/OQI5/OQI6/OQI7 capability.

## 9. Disposition

```
P2-A:  GOVERNANCE RESOLUTION FROZEN — IMPLEMENTATION OPEN (pending OQI3-I2-R)
P2-B:  GOVERNANCE RESOLUTION FROZEN — IMPLEMENTATION OPEN (pending OQI3-I2-R)
OQI-P3-005: RECORDED (inherited OQI1/OQI2 debt; not authorized for repair under OQI3)
```

`OQI3-I2` remains **FORMAL CLOSURE HELD** until `OQI3-I2-R` implements and independently verifies
both corrections against this amendment. `OQI3-I3` remains **NOT AUTHORIZED**.

## 10. Authorization

Effective immediately upon publication. `OQI3-I2-R` is authorized to implement exactly the scope
frozen in §3–§7 of this document, against the exact 9-path subset of CDD-041's original Artifact
Authorization enumerated in §7, using the migration-amendment strategy in §3.2, and must produce
the mandatory regression tests in §7.1. No other CDD-041 decision is reopened by this document.
