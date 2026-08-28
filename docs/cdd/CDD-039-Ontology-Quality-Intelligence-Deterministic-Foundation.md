# CDD-039 — Ontology Quality Intelligence Deterministic Foundation

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-022 (FROZEN, Gate — `FieldValueEvidence`, consumed by call/query only,
never modified, Sec12/Sec29/Sec36 of this document), CDD-031 (FROZEN, Gate T — Currency/intra-source
Consistency firewall, Sec30), CDD-019 (FROZEN, Gate H — `SourceField`/`SourceObject`/`SourceSystem`
schema-identity layer, consumed read-only), CDD-036 (FROZEN, Gate S — sole precedent for a durable,
row-locked, tenant-isolated governed lifecycle; its transactional-locking *principle*, not its exact
SQL, is reused, Sec21), CDD-037 (FROZEN, Gate V — the most recent small-gate governance/Artifact
Authorization precedent this document's structure mirrors), CDD-038 (FROZEN, Gate W — reserves all
future production API/versioning surface; OQI1 builds no API, Sec32)

Mandatory template: CDD Template v2.2

**Publication note**: this document freezes the architecture reached across five read-only,
zero-mutation discovery/refinement phases (DQ0, DQ0-R, OQI0-F, OQI0-FR, OQI0-FS), culminating in
Product-Owner-approved OQI Foundation Contract v1.2. This is a governance-only publication; no
implementation file is created or modified by this document or its companion Artifact
Authorization.

## 1. Title

Ontology Quality Intelligence Deterministic Foundation (OQI1) — the first implementation increment
of Ontology Quality Intelligence (OQI).

## 2. Canonical terminology (binding)

**Ontology Quality Intelligence (OQI)**, formerly referred to during discovery as Generalized Data
Quality / Generalized DQ, is the canonical capability name for all new product-facing architecture,
governance, implementation, APIs, navigation, dashboards, and documentation. Historical frozen
discovery artifacts (DQ0, DQ0-R) retain their original terminology and MUST NOT be rewritten merely
for naming consistency.

Domain classes use unbranded quality-domain vocabulary: `QualityRule`, `QualityEvaluation`,
`QualityFinding`, `QualityDimension`, `QualityFindingType`, `EvaluationSubject`, `EvaluationMode`,
`EvaluationOutcome`, `EvaluationOrigin`, `SourceRecordLineageIdentity`. No class name is
`OQI`-prefixed. "OQI" is reserved for the product/capability name only.

## 3. OQI north star (non-binding on OQI1 scope, binding as strategic context)

CTEC Ontology Quality Intelligence determines whether knowledge represented by the ontology can be
trusted, identifies and explains the source-evidence quality conditions affecting that knowledge,
and governs how those conditions are analyzed, remediated, re-evaluated, and resolved.

**OQI1 implements only the deterministic quality foundation required by that future capability. It
does not calculate ontology trust, ontology impact, business impact, agent recommendations, or
remediation.** No future developer may treat OQI1 as though it already implements the north star.

## 4. Capability statement (exact, binding)

CTEC can deterministically evaluate a governed physical source attribute — identified by one
`SourceField` within one continuing, honestly-scoped source-record lineage — against a versioned,
governed `QualityRule` (Completeness or Validity), persist an idempotent, provenance-complete
`QualityEvaluation` ledger record, and maintain exactly one concurrency-safe `QualityFinding`
representing current quality truth for that attribute — without any API, frontend, agent, scoring,
trust, or remediation capability of any kind.

## 5. OQI1 proof statement (binding success target)

> Given a governed active Completeness or Validity quality rule and a known source-record lineage,
> CTEC can deterministically evaluate the governed source attribute against immutable
> `FieldValueEvidence`, persist an idempotent provenance-complete `QualityEvaluation`, and maintain
> one concurrency-safe `QualityFinding` representing current quality truth without historical
> evaluation, rule retirement, replay, or concurrent execution corrupting that truth.

## 6. Why now

Five read-only phases (DQ0 → DQ0-R → OQI0-F → OQI0-FR → OQI0-FS) resolved every architectural
ambiguity blocking a first deterministic OQI increment, including the final, previously-reopened
question of what an OQI Finding's physical subject precisely and honestly means. `P0=0, P1=0, P2=0`
was reached and Product-Owner-approved (OQI Foundation Contract v1.2). Freezing that architecture now
— before any code exists — prevents implementation from silently making further architectural
decisions inside code.

## 7. Dependencies (binding)

Consumes, by call/query only, entirely unmodified: `FieldValueEvidence` (CDD-022) — read-only query
access to `source_field_id`, `source_record_reference`, `observed_representation`, `observed_at`,
`received_at`, `field_value_evidence_id`; `SourceField`/`SourceObject` (CDD-019/H1) — read-only
foreign-key reference only, for `source_field_id` → `source_object_id` → `tenant_id` resolution.
Does not depend on Gate T (CDD-031), Entity Resolution, Gate S, Gate V, or Gate W in any functional
sense.

## 8. Non-goals (binding, exhaustive)

```
Cross-source comparison                    Record Completeness
AttributeComparisonGroup                    Population Completeness
Source authority                             Dataset Completeness
Consistency                                   CDE/criticality
Currency                                       Severity
Accuracy                                        Confidence
Uniqueness                                       Quality score
Timeliness                                        Trust score
Reasonableness                                     Ontology trust
Integrity                                           Ontology impact
Business impact                                      Agent reasoning
Agent messaging                                       Remediation
Human approval workflow                                API
Frontend                                                Dashboard
Graph annotation                                         Generic expression engine
Free-text executable rules                                Source-record lifecycle tracking
Record deletion detection                                  Record incarnation tracking
Entity Resolution dependency
```

No "small convenience" addition beyond this document's exact freeze is authorized. A third quality
dimension, a new `QualityFindingType`, or a new `subject_type` each require their own future
governance cycle (Sec44).

## 9. OQI1 quality dimensions (binding, exhaustive)

```
QualityDimension: COMPLETENESS, VALIDITY   -- exactly these two, closed StrEnum
```

No hidden generic framework may effectively implement Consistency, Currency, Accuracy, Uniqueness,
Timeliness, Reasonableness, or Integrity under another name.

## 10. Finding types and Validity primitives (binding, exhaustive)

```
QualityFindingType:  MISSING_VALUE, ENUM_VIOLATION, FORMAT_VIOLATION, RANGE_VIOLATION
ValidityPrimitive:   ENUM_MEMBERSHIP, FORMAT_VIOLATION, RANGE_VIOLATION
```

`ValidityPrimitive.FORMAT_VIOLATION`/`RANGE_VIOLATION` share their literal names with
`QualityFindingType.FORMAT_VIOLATION`/`RANGE_VIOLATION` by deliberate Product Owner specification —
this is intentional, binding, and MUST NOT be silently renamed for stylistic disambiguation by
implementation.

Dimension/finding-type/primitive coupling is a closed, exhaustive 4-row table, enforced at rule
construction (Sec33):

```
COMPLETENESS -> MISSING_VALUE      -> validity_primitive = None
VALIDITY     -> ENUM_VIOLATION      -> validity_primitive = ENUM_MEMBERSHIP
VALIDITY     -> FORMAT_VIOLATION    -> validity_primitive = FORMAT_VIOLATION
VALIDITY     -> RANGE_VIOLATION     -> validity_primitive = RANGE_VIOLATION
```

No other combination is valid.

## 11. Attribute Completeness — exact scope freeze (binding)

OQI1 Completeness means **Attribute Completeness for a known governed source-record lineage** only.
It does NOT mean Record Completeness (do all of a lineage's expected attributes have values —
requires cross-Finding aggregation, out of scope), Population Completeness, Dataset Completeness, or
expected-population reconciliation (all require an external expected-population reference that
exists nowhere in frozen governance).

Binding invariant: **OQI MUST NOT convert absence of knowledge into knowledge of absence.**

## 12. Known-lineage semantics (binding, load-bearing)

```
SourceRecordLineageIdentity = tenant_id + source_object_id + source_record_reference
```

a non-persisted, deterministic value object in OQI1 — never a table, never a fresh UUID wrapping the
same raw string.

A source-record lineage is **known** to OQI when CTEC possesses at least one admitted
`FieldValueEvidence` observation, with a non-empty `observed_representation`, for **any**
`SourceField` belonging to the same `SourceObject` and carrying the same `source_record_reference`
within the same tenant boundary — not merely for the specific target field being evaluated.

**Binding precision**: "known" means *observed by CTEC*; it MUST NOT be interpreted as asserting that
the source record currently exists in the originating source system. Observed historically is not
the same claim as verified currently existing.

```
known lineage + target attribute lacks qualifying evidence  = MISSING_VALUE
lineage never observed by CTEC                                = NO EvaluationSubject
                                                                 = NO MISSING_VALUE Finding
```

"Qualifying evidence" means a `FieldValueEvidence` row with a non-empty `observed_representation`
(CDD-022 Sec9's "empty row" and "no row" cases both collapse into MISSING_VALUE for the target field
by deliberate OQI1 design choice; CDD-022's own three-state distinction remains intact, unmodified,
at the evidence layer — OQI1 merely chooses not to distinguish the two sub-cases as different Finding
types).

## 13. SourceRecordLineageIdentity semantics (binding, the resolved P2-2 freeze)

`SourceRecordLineageIdentity` represents **the continuing occupancy of a source-system record key
within one `SourceObject` and tenant.**

It does NOT claim:
```
verified immutable real-world record identity
record incarnation identity
current source-system existence
```
It does NOT depend on Entity Resolution or ontology identity.

If the originating source later reuses the same key after a real-world deletion, OQI1 continues the
**same source-key lineage**, because OQI1 possesses no lifecycle/incarnation signal. This is honest
lineage semantics, not a claim of physical permanence — the identity is true by construction, not an
accepted risk of falsity.

## 14. EvaluationSubject (binding)

```
EvaluationSubject = SourceRecordLineageIdentity + source_field_id
subject_type       = SOURCE_FIELD_RECORD   -- the sole OQI1 subject type
```

The subject represents **one governed physical source attribute within one governed source-key
lineage** — enough information to resolve tenant, source system, source object, source record
reference, and source field, without Entity Resolution.

## 15. QualityFinding subject semantic (binding, fundamental)

> A `QualityFinding`'s subject is the governed source attribute identified by a specific
> `SourceField` within a specific continuing `SourceRecordLineageIdentity`, scoped to one tenant and
> `SourceObject`, whose deterministic quality evaluation produced the Finding. The lineage represents
> continuing source-key occupancy and MUST NOT be interpreted as proof of one immutable real-world
> record incarnation or proof that the source record currently exists.

## 16. Quality-condition identity (binding)

`quality_condition_id` is the stable governed semantic identity of one quality expectation. Across
its lifetime, `dimension` and `information_element_requirement_id` are immutable — changing either
requires a new `quality_condition_id`. No separate persisted `QualityCondition` table exists in
OQI1; `quality_condition_id` is a governed string identity carried directly on `QualityRule` rows.

## 17. Rule change semantics (binding, restated, not to be inferred automatically)

Same `quality_condition_id`, new version, may represent: a metadata-only change; an
execution-equivalent change; a parameter refinement where governance determines the underlying
quality condition remains the same. A new `quality_condition_id` is mandatory for: a dimension
change; an `information_element_requirement_id`/governed-subject-semantic change; a material
applicability change representing a genuinely different expectation. This is a governed semantic
judgment, never automatically inferred by implementation.

## 18. QualityRule (binding)

Persisted, versioned, governed. Conceptual identity: `(quality_condition_id, version)`.

```
Lifecycle:  ACTIVE | RETIRED   -- closed 2-value StrEnum
```

Rules: immutable version rows; append-only versions; exactly one ACTIVE version per
`quality_condition_id` at any time; activating a new version atomically retires the previous ACTIVE
version within the same transaction (retire-then-activate ordering, Sec34); no deletion; no identity
reuse; no persisted DRAFT lifecycle.

Binding: **`rule_version` MUST NOT participate in `QualityFinding` identity.**
Binding: **`rule_version` MUST participate in `QualityEvaluation` identity and immutable evaluation
provenance.**
Binding: **Retiring a rule MUST NOT resolve, reopen, or otherwise mutate an existing
`QualityFinding`.**

If no ACTIVE version exists for a `quality_condition_id`, CURRENT_STATE evaluation is ineligible.
Historical evaluation of a retired version remains possible.

## 19. QualityEvaluation (binding)

The immutable canonical evaluation ledger. Every genuine logical evaluation is persisted.

```
EvaluationMode:   HISTORICAL, CURRENT_STATE
EvaluationOutcome: SATISFIED, VIOLATED
EvaluationOrigin:  RULE_DETERMINISTIC   -- the sole OQI1 value; no AI origin yet
```

No fuzzy outcome. No `UNKNOWN` outcome. Malformed rules/evaluations fail closed with typed errors
(Sec33).

## 20. QualityEvaluation identity (binding, frozen formula)

```
canonical_subject_identity =
    canonical_form(tenant_id) + ":" + canonical_form(source_object_id) + ":" +
    source_record_reference + ":" + canonical_form(source_field_id)

canonical_evidence_set_digest =
    SHA-256("|".join(sorted(str(id) for id in evidence_ids))).hexdigest()
        if evidence_ids else SHA-256("EMPTY_EVIDENCE_SET").hexdigest()

evaluation_id = uuid5(
    OQI_NAMESPACE,
    tenant_id + quality_condition_id + str(rule_version) + subject_type +
    canonical_subject_identity + evaluation_mode + evaluation_horizon.isoformat() +
    canonical_evidence_set_digest
)

OQI_NAMESPACE = uuid5(NAMESPACE_URL, "urn:ctec:oqi:v1")   -- fixed, frozen forever once implemented
```

`canonical_form(x)` renders UUIDs as lowercase-hyphenated strings and leaves strings/ints as their
exact value; `source_record_reference` is never trimmed, cased, or otherwise normalized (CDD-022
Sec10 byte-exactness preserved). `state_revision` MUST NOT participate in this identity.

Zero-evidence evaluations use the `"EMPTY_EVIDENCE_SET"` sentinel digest — a legitimate, distinct,
correctly-representable case (Sec12).

Identical replay (same inputs) produces the same `evaluation_id`; persistence is idempotent
(insert-or-noop on primary-key conflict, never a duplicate row, never an error surfaced to the
caller for a byte-identical replay).

## 21. QualityEvaluation provenance (binding)

Each ledger row preserves enough immutable provenance to answer: tenant; quality condition; exact
rule version; evaluation subject; evaluation mode; evaluation origin; evaluation horizon; exact
evidence rows examined; outcome; ledger admission time; whether it obtained CURRENT_STATE authority;
which `state_revision`, if any, it applied. Raw evidence values are never duplicated into any OQI
table — only `FieldValueEvidence` id references are stored (Sec36).

## 22. Historical evaluation (binding, structurally enforced)

`HISTORICAL` evaluation: may use a caller-supplied `evaluation_horizon`; persists its own
`QualityEvaluation` ledger row; never acquires CURRENT_STATE evaluation authority; never creates,
opens, resolves, or reopens a `QualityFinding`; never increments `state_revision`; never changes
Finding counters. Because a HISTORICAL evaluation's `evaluation_id` differs from any CURRENT_STATE
evaluation's id (evaluation_mode is a direct identity input, Sec20) and it never touches
`QualityFinding`, it cannot conflict or race with a concurrent CURRENT_STATE evaluation of the same
subject — it simply writes a separate, non-colliding ledger row.

## 23. CURRENT_STATE evaluation (binding)

The only evaluation mode capable of changing `QualityFinding` truth. Its `evaluation_horizon` comes
from a trusted runtime clock; it MUST NOT be caller-controlled through any production
API/service path (tests may use dependency injection of the clock only).

## 24. Evaluation-authority concurrency invariant (binding, semantic — not SQL syntax)

> For one tenant + quality condition + `EvaluationSubject`, only one CURRENT_STATE evaluation may
> hold authoritative evaluation authority at a time. Evaluation authority MUST be acquired before
> evidence selection and held through deterministic evaluation, `QualityEvaluation` persistence,
> `QualityFinding` mutation, `state_revision` assignment, and transaction completion.

```
Acquire evaluation authority
        v
Select evidence
        v
Evaluate
        v
Persist QualityEvaluation
        v
Mutate QualityFinding
        v
state_revision++
        v
Commit
        v
Release authority
```

**Critical**: evaluation authority MUST be obtainable even when no `QualityFinding` row exists yet —
this document does NOT freeze `SELECT ... FOR UPDATE` on `QualityFinding` as the implementation
mechanism, because no such row may yet exist for the first violation. The exact mechanism is frozen
in the companion Artifact Authorization (its Sec12), not here, per this document's own
instruction to freeze behavior, not prematurely freeze SQL syntax.

Prohibited: last-commit-wins; UUID lexical ordering; timestamp-only tie-breaking; caller-provided
ordering.

## 25. Evidence selection under authority (binding)

For CURRENT_STATE, evidence selection MUST occur only after authoritative evaluation authority is
acquired. Reason: a stale, pre-lock evidence snapshot must never overwrite newer current truth. The
evaluation operates on the admitted evidence frontier visible within the authoritative evaluation
transaction/window.

## 26. state_revision (binding)

`state_revision` is **the monotonic authoritative revision of `QualityFinding` current state for one
Finding lineage.** It increments exactly once for every successful authoritative CURRENT_STATE
evaluation applied to that Finding lineage. It is NOT: failure count, severity, trust score,
confidence, global sequence, event time, evaluation identity, business impact, or a count of
Findings. It is excluded from `QualityEvaluation` identity (Sec20) but may be recorded on the ledger
row as authority/provenance metadata (`state_revision_applied`).

## 27. QualityFinding (binding)

The universal, dimension-neutral persisted representation of a continuing quality condition for one
`EvaluationSubject`.

```
Truth state: OPEN, RESOLVED   -- exactly these two, closed StrEnum
```

No `RECURRING`, `SUPERSEDED`, `ACKNOWLEDGED`, or `REMEDIATING` state. Those concepts, if ever
required, belong to separate lifecycle/history/remediation models never built by OQI1.

## 28. QualityFinding identity (binding, frozen formula)

```
quality_finding_id = uuid5(
    OQI_NAMESPACE,
    tenant_id + quality_condition_id + subject_type + canonical_subject_identity
)
```

using the same `canonical_subject_identity` defined in Sec20. Excluded from this identity:
`rule_version`, `evaluation_horizon`, `evaluation_time`, `finding_type`, `status`, `state_revision`,
`occurrence_count`, `reopen_count`. One continuing quality condition on one governed subject produces
exactly one continuing Finding lineage.

## 29. Finding state vs. history (binding)

`QualityFinding` = current authoritative truth. `QualityEvaluation` = immutable historical
evaluation ledger. No `QualityFindingOccurrence`/`DQFindingOccurrence` table is created — the ledger
provides history. Finding read-model fields are split exactly:

```
Canonical (mutated only under evaluation authority): status, state_revision
Derived/cached (updated alongside, never independently authoritative):
    first_seen_at, last_seen_at, last_evaluated_horizon, occurrence_count, reopen_count
```

Counters never become identity.

## 30. Finding transitions (binding, exhaustive)

For an authoritative CURRENT_STATE evaluation:

```
No Finding   + SATISFIED  -> no Finding required (none created)
No Finding   + VIOLATED   -> create OPEN Finding
OPEN         + VIOLATED   -> remain OPEN
OPEN         + SATISFIED  -> RESOLVED
RESOLVED     + SATISFIED  -> remain RESOLVED
RESOLVED     + VIOLATED   -> OPEN; reopen_count += 1
```

Every genuine evaluation still receives its immutable `QualityEvaluation` ledger entry regardless of
whether it causes a Finding transition. Finding state transitions never replace evaluation
provenance.

## 31. Validity rule shape — exact payload semantics (binding, load-bearing)

```
ENUM_MEMBERSHIP:   { "allowed_values": [str, ...] }
    required: allowed_values -- non-empty list of unique strings
    prohibited: any other key
    comparison: exact, case-sensitive, no trimming

FORMAT_VIOLATION:  { "pattern": str }
    required: pattern -- a string that compiles as a valid regular expression
    prohibited: any other key
    match semantics: re.fullmatch(pattern, observed_representation); no coercion

RANGE_VIOLATION:   { "min": number | null, "max": number | null }
    required: at least one of min/max present and non-null
    prohibited: any other key; min > max when both present
    numeric coercion: strip whitespace, then int(), then float() (first that succeeds);
                       an unparseable value is a genuine VIOLATED outcome, not a malformed-rule
                       error and not a skipped evaluation
    inclusivity: both bounds inclusive

COMPLETENESS (MISSING_VALUE): {}   -- empty object; no parameters permitted
```

No unknown/extra key is permitted in any shape (closed schema per primitive).

## 32. Missingness/Validity interaction (binding, resolves Sec-34's ordering question)

Completeness and Validity are independently-governed quality conditions — there is no execution
ordering dependency between them. However: **Validity rules evaluate present values only.** A
Validity rule is invoked only when the target field has at least one qualifying (non-empty
`observed_representation`) evidence row; when no qualifying value exists, Validity evaluation for
that subject/condition simply does not occur at that horizon — no `QualityEvaluation` row is written
for the attempted Validity check, and no Finding is touched by it. **A missing value can never
simultaneously produce a Validity Finding.** Missingness belongs exclusively to Completeness.

When multiple qualifying evidence rows exist for the target field, Validity evaluates the
latest-observed one: greatest `observed_at`, ties broken by greatest `received_at` — matching Gate
T's own comparable-evidence selection precedent (CDD-031).

## 33. Malformed-rule validation boundary (binding, resolves the second carried P3)

A single shared validation function enforces the Sec10/Sec31 closed schemas. It runs at exactly
three points using identical logic:

1. **Construction** — a `QualityRule` domain object cannot be constructed with an invalid
   dimension/finding-type/primitive combination or a malformed `rule_parameters` shape.
2. **Persistence/activation** — before INSERT and again before any transition to `ACTIVE`, the same
   function re-validates. **Invalid governed rule definitions must never become ACTIVE.**
3. **Evaluation time (defense-in-depth)** — the same function re-validates whatever persisted
   `rule_parameters` was loaded before use. If validation fails here (only reachable via out-of-band
   database corruption, since all governed write paths already enforce points 1–2), evaluation
   raises a typed `OqiMalformedRuleError` and fails closed: no `QualityEvaluation` row is written for
   that attempt, no `QualityFinding` is touched, no fabricated SATISFIED/VIOLATED outcome is ever
   produced.

## 34. Rule lifecycle transaction ordering (binding)

Activating a new rule version is one transaction: (a) UPDATE the current ACTIVE row for
`quality_condition_id` to `RETIRED` with `retired_on = now()`; (b) then activate the new version row.
This ordering ensures the partial unique index (Sec38) is never transiently violated within the same
transaction.

## 35. Evidence provenance chain (binding, restated)

```
SourceSystem
      v
SourceObject
      v
SourceRecordLineageIdentity   (value abstraction; NOT a persisted table in OQI1)
      v
SourceField
      v
FieldValueEvidence
      v
EvaluationSubject
      v
QualityCondition (identity only, no table)
      v
QualityRule / version
      v
QualityEvaluation
      v
QualityFinding
```

Future chain (NOT implemented by OQI1): `QualityFinding -> Ontology Impact -> Business Impact ->
Agent Reasoning -> Human Authority -> Remediation -> Re-evaluation -> Explainable Trust`.

## 36. Raw-value non-duplication (binding)

`QualityEvaluation` and `QualityFinding` never persist duplicate raw source values. They persist:
evidence id references, rule parameters (governed), outcomes, identities, timestamps, and state
metadata. Source values remain owned exclusively by `FieldValueEvidence`.

## 37. Gate T firewall (binding, restated)

Gate T (CDD-031) retains exclusive ownership of Currency and intra-source Consistency. OQI1 MUST
NOT call, wrap, copy, persist, rename, or duplicate any Gate T outcome or conflict-detection logic.
Gate T and OQI1 are sibling, non-communicating consumers of `FieldValueEvidence`.

## 38. Entity Resolution firewall (binding, restated)

`SourceRecordLineageIdentity` != Entity Resolution identity != ontology entity identity. OQI1 does
not call Entity Resolution and does not merge source subjects. A future OQI2 may govern cross-source
comparability additively, without redefining any existing lineage identity.

## 39. Persistence model (binding, frozen)

Four new tables, one migration:

```
quality_rules
  rule_id                              UUID PRIMARY KEY   -- uuid5(quality_condition_id, version)
  quality_condition_id                   String(200) NOT NULL
  version                                  Integer NOT NULL
  dimension                                 String(16) NOT NULL
  finding_type                                String(32) NOT NULL
  validity_primitive                            String(32) NULL
  information_element_requirement_id              String(200) NOT NULL
  rule_parameters                                   JSON NOT NULL
  status                                              String(16) NOT NULL
  created_by                                           String(200) NOT NULL
  created_on                                            DateTime(timezone=True) NOT NULL
  retired_on                                             DateTime(timezone=True) NULL

  UniqueConstraint(quality_condition_id, version)
  Partial unique index on (quality_condition_id) WHERE status = 'ACTIVE'

quality_evaluations
  evaluation_id            UUID PRIMARY KEY   -- deterministic, Sec20
  tenant_id                  String(200) NOT NULL, indexed
  quality_condition_id         String(200) NOT NULL
  rule_id                        UUID NOT NULL, FK -> quality_rules.rule_id
  rule_version                     Integer NOT NULL
  subject_type                      String(32) NOT NULL
  source_object_id                    UUID NOT NULL, FK -> source_objects.source_object_id
  source_record_reference               String(1000) NOT NULL
  source_field_id                        UUID NOT NULL, FK -> source_fields.source_field_id, indexed
  evaluation_mode                          String(16) NOT NULL
  evaluation_origin                          String(32) NOT NULL
  evaluation_horizon                           DateTime(timezone=True) NOT NULL
  evidence_set_digest                            String(64) NOT NULL
  outcome                                          String(16) NOT NULL
  applied_current_state_authority                    Boolean NOT NULL
  state_revision_applied                               Integer NULL
  evaluated_on                                           DateTime(timezone=True) NOT NULL

  Index(quality_condition_id, source_object_id, source_record_reference, source_field_id,
        evaluation_mode, evaluation_horizon)

quality_evaluation_evidence
  evaluation_id             UUID NOT NULL, FK -> quality_evaluations.evaluation_id
  field_value_evidence_id     UUID NOT NULL, FK -> field_value_evidence.field_value_evidence_id
  sequence_index                Integer NOT NULL   -- 0-based, canonical sort order

  PRIMARY KEY (evaluation_id, field_value_evidence_id)
  Index(field_value_evidence_id)

quality_findings
  finding_id                UUID PRIMARY KEY   -- deterministic, Sec28
  tenant_id                   String(200) NOT NULL, indexed
  quality_condition_id          String(200) NOT NULL
  subject_type                    String(32) NOT NULL
  source_object_id                  UUID NOT NULL, FK -> source_objects.source_object_id
  source_record_reference             String(1000) NOT NULL
  source_field_id                      UUID NOT NULL, FK -> source_fields.source_field_id, indexed
  finding_type                           String(32) NOT NULL   -- cached, never identity
  status                                   String(16) NOT NULL
  state_revision                             Integer NOT NULL
  first_seen_at                                DateTime(timezone=True) NOT NULL
  last_seen_at                                   DateTime(timezone=True) NOT NULL
  last_evaluated_horizon                           DateTime(timezone=True) NOT NULL
  occurrence_count                                   Integer NOT NULL
  reopen_count                                         Integer NOT NULL

  Index(tenant_id), Index(source_field_id), Index(status)
```

No `SourceRecordLineageIdentity` table. No `QualityCondition` table. No `DQFindingOccurrence` table.
No existing table is altered.

## 40. Migration (binding, frozen)

```
revision      = "0020_oqi1_quality_foundation"
down_revision = "0019_gate_v_agent_resolution"
```

## 41. Migration-impact remediation (binding, load-bearing — the Gate S/Gate V lesson, applied
proactively)

The following four pre-existing, OQI-unrelated tests hardcode the overall repository migration head
and table count; their exact, mechanical corrections are authorized directly in the companion
Artifact Authorization, not deferred to a post-hoc Defect Authorization:

```
backend/app/tests/test_decision_engine.py         revision: "0019_gate_v_agent_resolution" -> "0020_oqi1_quality_foundation"
backend/app/tests/test_governance_engine.py        revision: "0019_gate_v_agent_resolution" -> "0020_oqi1_quality_foundation"
backend/app/tests/test_knowledge_engine.py          revision: "0019_gate_v_agent_resolution" -> "0020_oqi1_quality_foundation"
backend/app/tests/test_persistence_integration.py    revision: "0019_gate_v_agent_resolution" -> "0020_oqi1_quality_foundation"
                                                        table_count: 64 -> 68
```

## 42. Concurrency implementation mechanism (frozen at the Artifact Authorization level, invariant
frozen here)

This document freezes the Sec24 behavioral invariant only. The exact PostgreSQL mechanism satisfying
it — a transaction-scoped advisory lock keyed deterministically off `quality_finding_id`, obtainable
before any `QualityFinding` row exists — is frozen in the companion Artifact Authorization (its
its Sec12), consistent with this document's instruction not to prematurely freeze SQL syntax inside
architecture governance.

## 43. Test requirements (binding, minimum set — see companion Artifact Authorization for exact
file distribution)

Identity determinism (lineage, subject, evaluation, Finding); tenant/SourceObject/SourceField
isolation; rule-version exclusion from Finding identity and inclusion in Evaluation identity;
Completeness known/unknown lineage, zero-target-evidence, other-field-establishes-known-lineage,
missing-to-present resolution, present-to-missing reopening; Validity valid/invalid enum, format
pass/fail, range pass/fail and boundary values, malformed rule rejection, missing values never
double-counted as Validity; ledger persistence of every genuine evaluation, replay idempotency,
historical persistence without Finding mutation, evidence id preservation, no raw-value
duplication; Finding lifecycle (first violation, repeat violation, resolve, repeat satisfied,
reopen, counters, state_revision); rule lifecycle (one ACTIVE version, new-version activation,
retirement, retired-rule CURRENT_STATE ineligibility, retirement not mutating Finding, historical
retired-version evaluation); concurrency under real PostgreSQL (concurrent first violation,
concurrent violation/satisfied, evidence arrival during contention, lock-before-evidence-selection,
state_revision monotonicity, no duplicate Finding, no duplicate identical Evaluation, tenant
non-blocking, subject non-blocking); firewalls (no Gate T dependency, no Entity Resolution
dependency, no API, no frontend, no agent, no trust/severity/confidence); provenance
reconstruction (Finding -> Evaluation -> exact rule version -> exact evidence ids -> SourceField ->
SourceObject -> SourceSystem, with tenant identity verified throughout).

## 44. Future extension boundary (binding)

A third `QualityDimension`, a new `QualityFindingType`, a new `subject_type`, cross-source
comparison, `AttributeComparisonGroup`, source authority, any scoring/trust/severity/confidence
concept, ontology impact, business impact, agent reasoning, remediation, an API, a frontend, or a
source-record deletion/incarnation-tracking mechanism each require their own, separate, explicit
Product Owner architecture decision and CDD. `SourceRecordLineageIdentity` may be additively
promoted to a persisted entity, or additively annotated with a future incarnation/deletion signal,
by a future Gate without changing this document's identity formulas or any existing Finding's own
identity.

## 45. Performance / index note (non-binding, informational, flagged for future attention)

`field_value_evidence.source_record_reference` carries no index today (confirmed by direct
inspection of migration `0016_field_value_evidence.py`), and `source_object_id` is not a column on
`field_value_evidence` at all (it is resolved transitively via `source_field_id ->
source_fields.source_object_id`). The Sec12 "known lineage" query therefore joins
`field_value_evidence` to `source_fields` and filters by `source_record_reference` without a
supporting index. This does not affect OQI1's *correctness* — only its performance at realistic
scale. Adding such an index requires a separate, CDD-022-owning-team-authorized migration touching
`field_value_evidence`, which this document does not authorize. Flagged here so a future engineer
does not have to rediscover it.

## 46. Explicit closure claim permitted by OQI1 (binding)

Upon successful implementation and merge, CTEC may truthfully claim: "CTEC can deterministically
evaluate a governed physical source attribute against immutable, unmodified `FieldValueEvidence`
for Completeness or Validity, using an honestly-scoped source-key lineage identity that never
overclaims real-world physical permanence, persist an idempotent and fully provenance-complete
evaluation ledger, and maintain exactly one concurrency-safe current-state Finding per governed
subject — without any API, frontend, agent, scoring, trust, or remediation capability, and without
modifying Gate T, Gate S, Gate V, Gate W, Entity Resolution, or `FieldValueEvidence`." No broader
claim is authorized.

## 47. Implementation authorization relationship (binding, restated)

Publication and freeze of this CDD does NOT itself authorize implementation. The companion Artifact
Authorization enumerates the exact, closed implementation file surface. A further, separate Product
Owner implementation authorization remains required before any authorized file may be created or
modified.

## 48. Authorization

This CDD is approved for publication and freeze, reached via the OQI0/OQI0-R/OQI0-F/OQI0-FR/OQI0-FS
discovery-and-refinement lineage and Product-Owner-approved OQI Foundation Contract v1.2. CDD-019,
CDD-022, CDD-031, CDD-036, CDD-037, and CDD-038 remain FROZEN and PUBLISHED, unchanged by this
document.
