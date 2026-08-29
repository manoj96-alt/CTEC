# CDD-041 — Ontology Quality Intelligence: Business-Rule Quality Intelligence

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-039 (FROZEN, OQI1 — `QualityRule`/`Finding`/`Evaluation` identity and
lifecycle patterns reused by structural analogy, never reopened), CDD-040 + its N-Source Finding
Representation Amendment (FROZEN, OQI2 — `Finding→Evaluation→Observation` separation and the
simultaneous-deterministic-facts principle reused by structural analogy, never reopened), CDD-019
(FROZEN, Gate H — `SourceField`/`SourceObject`/`SourceSystem` schema-identity layer, consumed
read-only, never modified), CDD-022 + its OQI2 companion amendment (FROZEN, Gate — `FieldValueEvidence`,
consumed by query only, never modified), CDD-031 (FROZEN, Gate T — evidence fitness/temporal-conflict
firewall, not duplicated), CDD-037 (FROZEN, Gate V — agent/LLM reasoning firewall), CDD-036 (FROZEN,
Gate S — human-authority/remediation firewall)

Mandatory template: CDD Template v2.2 (same structure as CDD-039/CDD-040)

**Publication note**: this document freezes the architecture reached across three read-only,
zero-mutation discovery/resolution phases (OQI3-D, OQI3-R), both Product-Owner-approved. This is a
governance-only publication; no implementation file is created or modified by this document or its
companion Artifact Authorization. Implementation is a separately-authorized future phase (OQI3-I1).

---

## 1. Purpose

OQI3 allows CTEC to represent governed deterministic business expectations over governed source
evidence, evaluate those expectations against an explicit subject and immutable rule version,
preserve the deterministic facts explaining satisfaction or violation, maintain stable
quality-condition Finding lifecycle, and provide provenance sufficient for future ontology-impact
analysis, governed remediation, business-impact reasoning, and explainable product experiences.

OQI3 is not a generic rules engine. A business-rule engine tells us whether an expression returned
true or false. OQI3 must tell us what governed expectation was evaluated, why it applied, which
deterministic facts satisfied or violated it, which evidence established those facts, what quality
condition remains open, and provide the evidence foundation required to determine what ontology
knowledge and business processes may consequently be trusted.

## 2. Architecture north star

```
Governed Business Condition
        ↓
BusinessRule Version
        ↓
Input Bindings (input_role → SourceField, expected_type)
        ↓
Single-Record Evaluation Subject (SourceRecordLineageIdentity)
        ↓
Governed FieldValueEvidence
        ↓
Deterministic Typed Interpretation (per-binding expected_type)
        ↓
Applicability Evaluation
        ↓
Declarative AST Evaluation (no short-circuit)
        ↓
BusinessRuleEvaluation (immutable ledger)
        ↓
BusinessRuleEvaluationObservation(s) (immutable deterministic facts)
        ↓
BusinessRuleFinding (stable condition-state lineage)
        ↓
Future OQI4 Ontology Impact → OQI5 Governed Remediation → OQI6 Criticality/Trust → OQI7 Product Experience
```

## 3. BusinessRule is first-class; QualityRule firewall

`BusinessRule` is a first-class governed OQI3 artifact — a **sibling** of `QualityRule`, never a
subtype, extension row, QualityRule configuration, shared-table discriminator, or `QualityExpectation`
superclass. OQI3 does not reopen frozen CDD-039/CDD-040 `QualityRule` semantics: the existing closed
`_ALLOWED_COMBINATIONS` coupling table, its dimension/finding_type/validity_primitive contract, and
`validate_rule_shape` remain byte-identical and untouched. No modification to `QualityRule`,
`quality_rules`, or any OQI1/OQI2 table is authorized by this document.

## 4. Business condition identity and rule versioning

`business_condition_id: str` is the stable identity of one governed business expectation, carried
on every `BusinessRule` row (mirrors `QualityRule.quality_condition_id` — no separate `Condition`
table, same precedent). A `BusinessRule` row is one immutable executable version of that expectation:

```
rule_id = uuid5(OQI_BUSINESS_RULE_NAMESPACE, f"business_rule:{business_condition_id}:{version}")
```

Changing executable meaning (predicate, applicability, bindings, thresholds) always creates a new
version. Rows are never mutated in place once published. Exactly one `ACTIVE` version exists per
`(tenant_id, business_condition_id)` at any time; all other versions for that condition are `RETIRED`.
Retirement does not mean `SATISFIED`, `NOT_APPLICABLE`, or `RESOLVED` — it proves nothing about
source data, and never mutates an existing Finding.

## 5. Initial rule families (closed)

Exactly three initial executable families are authorized. No other family is implicitly authorized;
adding one requires a new governance amendment.

- **`CONDITIONAL_REQUIRED`** — `IF <applicability> THEN <input_role> MUST EXIST`. Distinguishes the
  applicability predicate from the required target input and from deterministic missingness; a
  known subject with a known-true applicability predicate and zero qualifying evidence for the
  required input is a genuine `VIOLATED` fact (mirrors OQI1's Completeness treatment).
- **`CONDITIONAL_PROHIBITED`** — `IF <applicability> THEN <input_role> MUST NOT satisfy <predicate>`.
  The evaluator preserves exactly which governed clause/input established the violation.
- **`FIELD_COMPARISON`** — a typed relational comparison between two input roles on the same subject
  (e.g. `effective_start <= effective_end`), including the evidence-relative temporal special case.
  Comparison uses the governed typed interpretation from §9; raw lexical ordering is prohibited for
  typed relational comparison.

## 6. Initial subject model

The only authorized initial subject type is `SINGLE_RECORD`, identified by the existing
`SourceRecordLineageIdentity` from OQI1 — reused verbatim, no new record-correspondence mechanism.
Subject-known semantics preserve OQI1 epistemic discipline exactly: *absence of knowledge is not
knowledge of absence*. A rule's expectation must never manufacture record existence.

Deferred subject types (not authorized by this document): cross-record, population/dataset,
aggregate, cross-source `BusinessRule`, ontology-entity subjects. When cross-source `BusinessRule`
execution is introduced in a future gate, it must compose with OQI2's `comparison_subject_id` /
correspondence architecture — no second record-matching mechanism is ever authorized.

## 7. Input bindings

Each `BusinessRule` version has immutable input bindings, each carrying a stable semantic
`input_role` (e.g. `material_type`, `hazmat_classification`, `effective_start`) — never an opaque
`arg1`/`arg2` position — bound to exactly one `source_field_id`, a `required: bool` flag, and an
`expected_type` (§9). `input_role` is unique within one rule version; `(rule_id, input_role)` is the
binding's natural key.

## 8. Typed evidence contract — ownership

Per OQI3-R: the governed canonical value type required for deterministic `FIELD_COMPARISON`
evaluation is owned by **`BusinessRuleInputBinding.expected_type`**, not `SourceField`. `SourceField`
is not modified by this document, carries no type metadata, and no `SourceFieldSemanticDefinition`
or equivalent versioned-type concept is introduced. `expected_type` is the OQI3 rule-binding
canonical interpretation required for deterministic evaluation — it is not necessarily the source's
native physical datatype (e.g. a SAP `DATS` field may be bound with `expected_type=DATE` while the
source-native metadata says something else entirely; OQI3 does not consume source-native type
metadata at all, and no agent/connector inference ever seeds `expected_type`).

Because `BusinessRuleInputBinding` rows are immutable once their rule version is published, historical
type interpretation is pinned for free: an `Evaluation.rule_version` always determines the exact
`expected_type` contract in force at that time. No separate per-Evaluation type-snapshot table is
authorized or required.

## 9. Closed initial canonical type set

Exactly four types are authorized:

```
STRING
DECIMAL
BOOLEAN
DATE
```

Deferred (not authorized): `INTEGER` (merged into `DECIMAL`), `DATETIME`, `TIME`, `BINARY`, `JSON`,
any business-semantic type (currency, country code, material number, percentage, etc.).

## 10. Parsing, coercion, and invalid evidence

Parsing occurs **only inside the OQI3 evaluator, at evaluation time**, from
`FieldValueEvidence.observed_representation`, per input binding's declared `expected_type`, via a
closed deterministic parser per type:

- **STRING** — the observed representation is used exactly as governed (no case-folding, no
  trimming beyond whatever normalization CDD-022 already governs for evidence itself).
- **DECIMAL** — a single canonical deterministic numeric parse (mirrors OQI1 `RANGE_VIOLATION`'s
  strip → int/float coercion style); decimal, not binary-floating-point, comparison semantics.
- **BOOLEAN** — exactly the closed literal set `{"true", "false"}` (case-sensitive); no other token
  is accepted.
- **DATE** — strict ISO-8601 calendar date `YYYY-MM-DD` only; no locale-dependent parsing.

**Implicit coercion is PROHIBITED.** A `STRING` observed representation `"10"` never silently
becomes `DECIMAL 10` without an explicit `expected_type=DECIMAL` binding and a successful
deterministic parse. `FieldValueEvidence` itself is never rewritten into typed storage — it remains
raw, immutable, governed evidence exactly as CDD-022 defines it.

**Parser failure**: if the raw evidence for a bound input cannot be parsed according to its
binding's `expected_type`, the result is `NOT_EVALUABLE` (§13), never `VIOLATED` — the business
relationship cannot be deterministically established from malformed input. This does not alter OQI1
semantics in any way; an independent OQI1 `QualityRule` (e.g. `FORMAT_VIOLATION`) may separately
flag the same malformed evidence if one is configured, but OQI3 never creates or infers one.

## 11. Operator/type compatibility (publication-time closed matrix)

```
EQ / NE                    — valid for STRING, DECIMAL, BOOLEAN, DATE
LT / LTE / GT / GTE        — valid only for DECIMAL, DATE  (prohibited for STRING and BOOLEAN)
IS_NULL / IS_NOT_NULL      — valid for all four types (tests evidence presence, not parsed content)
AND / OR / NOT / IMPLIES   — type-agnostic composition
```

This matrix is validated at **rule-publication time**, never discovered at runtime — a malformed
operator/type combination (e.g. `LT(STRING, STRING)`) must never reach `ACTIVE` status.

## 12. Declarative AST (closed, no arbitrary code)

`BusinessRule.applicability` and `BusinessRule.predicate` are each a closed, schema-validated,
canonicalizable, bounded declarative AST — never an arbitrary expression string, callable reference,
or executable code. Authorized node types:

```
Comparators: EQ, NE, LT, LTE, GT, GTE, IS_NULL, IS_NOT_NULL
Composition: AND, OR, NOT, IMPLIES
```

No other comparator or composition operator is authorized without a new governance amendment.
**Arbitrary code execution is PROHIBITED absolutely**: no `eval`, `exec`, dynamic imports,
user-supplied callable names, arbitrary Python/SQL/shell/JavaScript, and no CEL or other external
expression-engine dependency in initial OQI3 (the repository has zero rule-engine dependencies
today, and none is introduced by this document). AST depth and node-count bounds must be enforced at
publication time; unbounded recursive expressions are prohibited.

Compound predicates must never short-circuit in a way that loses a deterministic failure fact:
implementation may optimize evaluation internally only if every clause's deterministic result is
still established and observable (§16).

## 13. Four semantic evaluation results

```
SATISFIED       — the rule applies, and governed evidence proves the expectation is met.
VIOLATED        — the rule applies, and governed evidence proves the expectation is violated.
NOT_APPLICABLE  — governed evidence positively, deterministically proves the applicability
                  predicate is false.
NOT_EVALUABLE   — CTEC cannot deterministically establish applicability or the predicate result
                  from the governed evidence frontier (includes: subject/applicability-input
                  existence unknown; a bound input's evidence fails to parse per §10).
```

`NOT_APPLICABLE` and `NOT_EVALUABLE` are never collapsed into each other:
`NOT_APPLICABLE` is a positive fact; `NOT_EVALUABLE` is the absence of a deterministic fact.

**`NOT_EVALUABLE` produces NO `BusinessRuleEvaluation` row.** No Evaluation, no Observation, no new
Finding, no mutation of an existing Finding — this mirrors OQI2's proven epistemic fail-closed
pattern exactly (`return None`, no ledger entry). Operational diagnostics for this case belong to
observability/logging, never the governed quality ledger.

`SATISFIED`, `VIOLATED`, and `NOT_APPLICABLE` each persist an immutable `BusinessRuleEvaluation` row.

## 14. Finding lifecycle

`BusinessRuleFinding.status` is exactly `OPEN | RESOLVED` — no `NOT_APPLICABLE`, `UNKNOWN`, or
`INVALID` Finding status is authorized; those are Evaluation-level semantics, never Finding
lifecycle states. `BusinessRuleFinding.resolution_basis` is an explicit column with closed values
`SATISFIED | NOT_APPLICABLE`, `NULL` while `status=OPEN`, non-`NULL` while `status=RESOLVED`.

CURRENT_STATE transition table (extends OQI1's 4-arm table with the orthogonal `resolution_basis`
dimension — not a redesign):

```
No existing Finding:
  VIOLATED       → create OPEN (occurrence_count=1, reopen_count=0)
  SATISFIED      → no Finding created
  NOT_APPLICABLE → no Finding created
  NOT_EVALUABLE  → no Evaluation persisted; nothing happens

Existing Finding:
  OPEN + VIOLATED            → remain OPEN, state_revision+1, last_seen_at updated
  OPEN + SATISFIED           → RESOLVED, resolution_basis=SATISFIED, state_revision+1
  OPEN + NOT_APPLICABLE      → RESOLVED, resolution_basis=NOT_APPLICABLE, state_revision+1
  RESOLVED (any basis) + SATISFIED       → remain RESOLVED, resolution_basis=SATISFIED, +1
  RESOLVED (any basis) + NOT_APPLICABLE  → remain RESOLVED, resolution_basis=NOT_APPLICABLE, +1
  RESOLVED (any basis) + VIOLATED        → OPEN, occurrence_count+1, reopen_count+1, +1
  * + NOT_EVALUABLE                       → Finding completely untouched
```

`BusinessRule` retirement never mutates an existing Finding — an OPEN Finding under a retired
condition remains OPEN, untouched (identical, never-observed-otherwise discipline to OQI1/OQI2).

## 15. Finding identity

```
finding_id = uuid5(
    OQI_BUSINESS_RULE_NAMESPACE,
    f"business_rule_finding:{tenant_id}:{business_condition_id}:{subject_type}:{subject_identity}"
)
```

Excludes: rule version, evaluation horizon, evidence IDs, observations, resolution_basis, current
values. This preserves condition continuity across executable rule versions — the same governed
business expectation continues to be tracked as it evolves. `subject_type` is included in identity
(unlike OQI1, which has exactly one subject type) because future subject types must never collide
in identity space with `SINGLE_RECORD`.

## 16. BusinessRuleEvaluation (immutable ledger) and identity

An Evaluation represents one successfully-evaluable execution result: `SATISFIED`, `VIOLATED`, or
`NOT_APPLICABLE`. `NOT_EVALUABLE` creates no Evaluation (§13).

```
evaluation_id = uuid5(
    OQI_BUSINESS_RULE_NAMESPACE,
    f"business_rule_evaluation:{tenant_id}:{business_condition_id}:{rule_version}:"
    f"{subject_type}:{subject_identity}:{evaluation_mode}:{evaluation_horizon}:{input_evidence_digest}"
)
```

Observation content is **excluded** from Evaluation identity — observations are deterministic
derivatives of the frozen inputs above, proven (not assumed) not to need independent representation
in identity, exactly as OQI2 proved for its own Observation model.

## 17. Input evidence digest

A role-keyed canonical digest over all bound inputs, generalizing OQI1/OQI2's evidence-digest
pattern from "participant role" to "input role": role-sorted (not insertion-order), evidence-content
sensitive, explicit about zero qualifying evidence when the subject is known, deterministic. Included
in Evaluation identity (§16) so identical evidence yields an identical Evaluation id; changed
evidence yields a new one.

## 18. Evaluation input / evidence linkage

Every evaluation input using evidence retains immutable linkage to the exact `FieldValueEvidence`
row(s) used — never only a parsed value. A required bound field with zero qualifying evidence is
represented deterministically in the input frontier/digest; no `FieldValueEvidence` row is ever
manufactured. Parsed typed values are never persisted independently (no `parsed_value` or
`candidate_value` column) — they are reconstructed at read/explanation time from
`rule_version → binding.expected_type → FieldValueEvidence.observed_representation`, consistent with
OQI2's no-raw-value-duplication discipline.

## 19. BusinessRuleEvaluationObservation (immutable deterministic facts)

One Evaluation may establish zero-to-many observations. Compound rules must preserve **every**
independently-established deterministic failure fact from the same evaluation — never short-circuit
after the first failure (direct OQI2 invariant, §12/§54 of the governing phase prompts).

Closed initial observation-type set:

```
REQUIRED_INPUT_MISSING     — a required bound input had no qualifying evidence when the rule applied
CLAUSE_VIOLATED            — a leaf predicate clause evaluated false
```

No generic `RULE_FAILED` type is authorized — it would destroy explainability. No third type without
a governance amendment.

Natural identity:

```
(evaluation_id, clause_id, observation_type, input_role)
```

`clause_id` is new relative to OQI2's flat participant-role key, required because a compound
predicate tree needs a stable sub-identity to distinguish *which* leaf failed when multiple leaves
fail simultaneously. `clause_id` is unique within `(rule_version, clause_id)`.

`SATISFIED` and `NOT_APPLICABLE` evaluations normally produce zero observations. Observations are
never created merely for verbosity.

## 20. Evaluation type resolution and provenance chain

```
source representation
        ↓
FieldValueEvidence (raw, immutable, unchanged)
        ↓
BusinessRuleInputBinding.expected_type (declares interpretation, pinned by rule_version)
        ↓
closed deterministic parser (§10)
        ↓
typed evaluation value (never persisted independently)
```

Explanation chain (fully reconstructable from persisted state alone, no generated narrative
required as authority):

```
BusinessRuleFinding → latest BusinessRuleEvaluation → Observations(clause_id, input_role)
  → input snapshot → FieldValueEvidence → SourceField → SourceObject → SourceSystem
```

## 21. Concurrency model (CURRENT_STATE)

One advisory-lock authority per Finding identity (never one lock per field/input — no multi-lock
deadlock architecture). OQI1 uses advisory-lock seed `1`; OQI2 uses seed `2`; **OQI3 uses seed `3`**,
verified to introduce no conflict with either frozen seed.

```
1.  load ACTIVE BusinessRule version for business_condition_id
2.  validate ACTIVE/executable status
3.  establish SINGLE_RECORD subject (SourceRecordLineageIdentity)
4.  compute stable Finding identity
5.  acquire pg_advisory_xact_lock(seed=3, finding_identity)
6.  re-check defensive rule/subject invariants
7.  select ALL bound input evidence under one governed evaluation horizon (coherent post-lock frontier)
8.  build the complete immutable input frontier
9.  parse each bound input according to its binding's expected_type
10. if not evaluable (§13) → release lock, return; no Evaluation, no Finding mutation
11. evaluate applicability against the frontier
12. if NOT_APPLICABLE → proceed to persist Evaluation + Finding transition (§14); no predicate
    evaluation needed
13. evaluate the full predicate AST without failure short-circuit (§12)
14. derive observations (REQUIRED_INPUT_MISSING / CLAUSE_VIOLATED) independently per clause
15. derive outcome: any observation ⇒ VIOLATED; zero observations (rule applicable) ⇒ SATISFIED
16. persist Evaluation + input snapshot + evidence links + observations, atomically, in one transaction
17. mutate Finding per §14's transition table (CURRENT_STATE only)
18. commit; release lock
```

All bound inputs for one CURRENT_STATE evaluation are selected **after** advisory-lock acquisition,
under one evaluation horizon — never across an unlocked race window (mirrors OQI2 exactly).

## 22. Idempotency

The same `(rule_version, subject, evaluation_mode, evaluation_horizon, input evidence frontier)`
produces the same Evaluation identity, the same result, and the same observation set. Replay
(sequential or concurrent) must not duplicate immutable Evaluation or Observation rows — enforced by
the natural keys in §16/§19, not application-level deduplication alone.

## 23. HISTORICAL mode

`HISTORICAL` evaluation never acquires Finding authority and never creates, mutates, reopens, or
resolves a current `BusinessRuleFinding` — it persists an immutable Evaluation (any of `SATISFIED`,
`VIOLATED`, `NOT_APPLICABLE`) and its Observations only, exactly mirroring OQI2's `evaluate_historical`
discipline. `NOT_EVALUABLE` remains non-persisted in HISTORICAL mode as well. Historical evaluation
of a rule family or subject type not yet authorized (deferred per §6) is out of scope; historical
reproducibility for the three initial families requires only the immutable rule version + binding
`expected_type` + exact evidence links already frozen above — no additional historical infrastructure
is needed.

## 24. Tenant isolation and database integrity

Every new table (`business_rules`, `business_rule_input_bindings`, `business_rule_evaluations`,
`business_rule_evaluation_inputs`, `business_rule_evaluation_observations`, `business_rule_findings`)
is tenant-consistent, enforced by database FK/constraint where practical, mirroring the exact
discipline OQI1/OQI2 were held to. At minimum:

```
- exactly one ACTIVE BusinessRule version per (tenant_id, business_condition_id) — enforced by a
  partial unique index (status='ACTIVE'), mirroring QualityRule's own precedent
- unique input_role per rule_id
- unique clause_id per rule_id
- Finding uniqueness on (tenant_id, business_condition_id, subject_type, subject_identity)
- Evaluation uniqueness on evaluation_id (identity-derived, §16)
- Observation natural uniqueness on (evaluation_id, clause_id, observation_type, input_role)
- chained composite FK from evaluation inputs/observations back to their owning Evaluation
- resolution_basis/status consistency (CHECK: status='OPEN' → resolution_basis IS NULL;
  status='RESOLVED' → resolution_basis IS NOT NULL), enforced at the database level where the
  target RDBMS supports it
```

This introduces no new cross-tenant FK risk beyond what OQI1/OQI2 already carry — every new table's
FKs target already tenant-scoped OQI1/OQI2/OQI3-owned tables or `SourceField`/`FieldValueEvidence`.
OQI-P3-002 (residual DB tenant defense-in-depth gap, §31) is inherited, not worsened.

## 25. Security

Prohibited absolutely: arbitrary code execution, dynamic imports, dynamic class loading, external
network calls during evaluation, nondeterministic functions (wall clock, random), locale-dependent
parsing. AST depth/size bounds and the closed operator/type registry (§11-12) are the enforcement
mechanism; publication-time validation (§26) rejects anything violating them before `ACTIVE` status
is reachable.

## 26. Rule publication validation

Before a `BusinessRule` version may become `ACTIVE`, the following are validated (mirrors
`validate_rule_shape`'s precedent of one shared validator invoked at construction/activation/
evaluation-time defensive re-check):

```
- AST schema conformance (§12)
- rule family is one of the three closed families (§5)
- all referenced input roles are defined bindings; all input roles unique within the rule
- all referenced clause_ids are unique within the rule
- every input binding's source_field_id exists and is tenant-consistent
- every input binding's expected_type is one of the closed four (§9)
- operator/type compatibility for every comparator node (§11)
- AST depth and node-count within governed bounds
- no unsupported operator, no cross-source binding (deferred, §6)
```

A malformed rule must never become `ACTIVE`. Engine-level failures discovered at runtime
(unsupported operator somehow reaching execution, internal parser defect, database failure) are
observability/logging concerns, never a Finding — they must fail closed, never fabricate a
`SATISFIED`/`VIOLATED` result.

## 27. Firewalls (explicit, binding)

- **OQI1 firewall**: OQI3 typed interpretation does not change OQI1 Completeness, Validity,
  `RANGE_VIOLATION`, parsing behavior, or Finding semantics. Any future OQI1 use of canonical typing
  requires separate governance. `SourceField` and every OQI1 table are untouched by this document.
- **OQI2 firewall**: OQI2 cross-source equality remains governed by its existing exact/trim/
  case-preserving semantics. OQI3 typed comparison never replaces or is consulted by OQI2 comparison.
  Majority is never truth; authority is never truth — both firewalls carry over unchanged.
- **Gate T firewall**: OQI3 does not recreate Gate T evidence-fitness/temporal-conflict semantics; it
  consumes governed evidence/horizon semantics as a plain reader, never reinterpreting Gate T's own
  `CONFLICTING` outcome.
- **Gate V firewall**: no LLM/agent reasoning decides a deterministic `BusinessRule` outcome.
  Evaluation is deterministic AST execution only.
- **Gate S firewall**: no automatic source correction, no consequential remediation authority. Human
  authority remains the future boundary for any consequential action.
- **OQI4 firewall**: no ontology-graph impact implementation. OQI3 preserves
  `Finding → condition → subject → input roles → SourceFields → evidence` linkage sufficient for a
  future OQI4 to consume; it implements no impact mapping itself.
- **OQI5 firewall**: no remediation candidate, no agent recommendation, no write-back. Observations
  are precise enough for future reasoning but no remediation logic exists in OQI3.
- **OQI6 firewall**: no severity-derived trust, DQ score, trust score, or confidence score anywhere
  in OQI3.
- **OQI7 firewall**: no dashboard, graph visualization, frontend, or executive card. OQI7 consumes
  the deterministic foundation in a future gate.

## 28. Deferred scope (explicit, binding)

Not authorized by this document, and not implicitly available to a future implementation gate
without a new governance amendment: cross-source `BusinessRule` execution, cross-record rules,
aggregate/population rules, reference-data membership rules, clock-relative temporal rules, agentic
rule authorship/execution, remediation, ontology impact, trust scoring, frontend/dashboard exposure.
When cross-source composition is eventually authorized, it must reuse OQI2's `comparison_subject_id`
and correspondence architecture — no second matching mechanism.

## 29. DQ dimension semantics

`BusinessRule` is not itself synonymous with one data-quality dimension. Each governed business
condition carries an explicitly governed dimension appropriate to what it establishes:

```
CONDITIONAL_REQUIRED   → COMPLETENESS and/or INTEGRITY, per the governed condition
CONDITIONAL_PROHIBITED → VALIDITY / CONSISTENCY / INTEGRITY, per the governed condition
FIELD_COMPARISON       → VALIDITY / CONSISTENCY / INTEGRITY, per the governed condition
```

Rule conformance does not by itself prove real-world Accuracy. Single-record rules do not prove
enterprise Uniqueness (no population scope exists in initial OQI3). Timeliness is not claimed
without explicit temporal/SLA semantics (clock-relative rules remain deferred, §28).

## 30. Finding version continuity

A rule-version change does not change Finding identity as long as `business_condition_id` continues
to represent the same governed business expectation (§15 excludes rule_version from identity). A
materially different business expectation requires a new `business_condition_id` — this is a
governance/authoring responsibility, not something OQI3 runtime infers.

## 31. Inherited P3 register (reassessed, not silently carried forward)

```
OQI-P3-001 — 64-bit advisory-hash collision / harmless over-serialization: unaffected in kind by
  OQI3's introduction of a third seed (seed=3, §21); same risk profile, new namespace.
OQI-P3-002 — residual DB tenant defense-in-depth gap: OQI3's new tables introduce no new write path
  to field_value_evidence beyond what OQI1/OQI2 already established; unchanged, not worsened.
OQI-P3-003 — explicit correspondence doesn't scale by design: relevant only once cross-source
  BusinessRule execution is authorized (deferred, §28); not resolved by this document.
OQI-P3-004 — deferred composite evidence lookup index: OQI3's multi-field (N-input) evidence
  selection stresses this lookup path harder than OQI1/OQI2 (N inputs per evaluation instead of
  1-2). This P3 should be revisited before OQI3-I2 implementation, not left indefinitely deferred.
```

## 32. OQI3 architecture risk register

```
P0 = 0
P1 = 0
P2 = 0 (resolved by OQI3-R: type ownership via BusinessRuleInputBinding.expected_type requires no
       reopening of frozen governance and no SourceField modification)
Deferred design questions carried forward: DATETIME type (deferred until a real need appears);
  BOOLEAN token strictness (exact true/false only; revisit only if a real connector needs broader
  tokens); OQI-P3-004 revisit timing (before OQI3-I2, not before OQI3-I1).
```

## 33. Implementation decomposition (authorized sequence)

```
OQI3-G   (this document) — governance freeze
OQI3-I1  — BusinessRule + input binding foundation, publication-time validator, migration
OQI3-I2  — deterministic AST evaluator, typed parsers, Evaluation/Observation persistence
OQI3-I3  — Finding CURRENT_STATE lifecycle + concurrency + HISTORICAL mode
OQI3-V   — independent adversarial verification
OQI3-M   — merge/closure
```

Each of OQI3-I1/I2/I3 is constrained to the exact file subset of the full Artifact Authorization
(companion document) relevant to that stage; the full Artifact Authorization may be implemented
across one or more PRs at the Product Owner's discretion, but no path outside the frozen exact set
is ever authorized without a new governance amendment.

## 34. Product explanation invariant

Persisted structures must support, without any generated prose as authority, an explanation
equivalent to:

```
Rule: Hazmat materials require classification        Rule version: 3
Subject: MAT-100
Applicability: material_type = HAZMAT
Failed clause: hazmat_classification required
Evidence: <exact FieldValueEvidence provenance>
Outcome: VIOLATED                                     Finding: OPEN
```

## 35. Final standard

CTEC does not merely execute a business-rule expression and record true or false. It preserves the
governed expectation, immutable executable version, semantic inputs, typed interpretation,
applicability decision, complete deterministic failure facts, exact evidence provenance, stable
quality-condition lifecycle, and sufficient explanation structure for future ontology impact and
governed remediation. That is the OQI3 contract, frozen before implementation.
