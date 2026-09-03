# CDD-051 — OQI-H5 Governed Timeliness

Version: 1.0 FROZEN
Status: FROZEN (architecture only — implementation NOT authorized by this document; see the companion
Artifact Authorization for the exact, separately-frozen implementation grant)
Implementation state: NOT STARTED
Governing authorities: CDD-046 (OQI-H0, FROZEN, AD-14/§15/§19/§22/§26/§29/§30/§35/§36/§44 Boundary 5 —
read-only consumed, never modified by this document), CDD-050 + its H4-R1 amendment (Governed Integrity,
read as the direct structural precedent for tenant isolation and additive-integration discipline), CDD-047
(Governed Quality Coverage, read as precedent for `CoverageDimension.TIMELINESS`'s existing placeholder),
CDD-044 (Criticality/Business Impact/Reliance, read as precedent for `BusinessProcess`), CDD-042 (Ontology
Impact, read as precedent for the closed `FindingFamily` firewall), CDD-043 (Governed Remediation, read as
precedent for the recommendation/authorization boundary)

Mandatory template: CDD Template v2.2 (this repository's established house style)

**Publication note**: this document is the governance freeze produced by OQI-H5-G. It converts the
repository-backed conclusions of OQI-H5-DR into binding, implementation-authoritative decisions. It
authorizes no implementation by itself — the companion `CDD-051-OQI-H5-Governed-Timeliness-Artifact-
Authorization.md` is the only document that grants file-level implementation permission, and only for the
exact paths it names.

## 1. Authoritative baseline (verified at G start)

```
HEAD:              f75c0bc3637d4234d451980c547fddd846c7b222
origin/main:       1b50bb8cc0efd96750a3b7f6dce6356c53feb066  (Merge PR #185 "oqi-h4/integrity")
merge-base(HEAD, origin/main) = HEAD — HEAD is a strict ancestor, zero content diff beyond the merge itself
Branch:            oqi-h4/integrity
Working tree:      clean except pre-existing untracked docs/product/ (inherited, untouched)
Migration head:    0038_oqi_h4_reference_tenancy.py  (38 linear revisions)
PostgreSQL table count baseline: 120 (H4 closure figure, re-confirmed unchanged — no migration has run
                                        since H4 closed)
```

Unchanged from the OQI-H5-DR baseline. No STOP condition triggered on repository grounds.

## 2. Capability claim (exact, binding)

This document freezes: the exact Timeliness semantic definition and two-Finding-type taxonomy (already
named by CDD-046, now made implementation-exact); the exact temporal-axis model and clock discipline; the
exact policy anchor (resolving CDD-046 §43 DD-06); the exact threshold representation and its structural
invariants; the exact policy versioning/uniqueness/precedence model; the exact Finding/Evaluation identity
formulas; the exact continuous-time reevaluation trigger for H5 v1; the exact persistence shape and every
required PostgreSQL invariant, including a narrow, disclosed, additive correction to a pre-existing OQI6
tenant-isolation gap this phase discovered; the exact OQI4/OQI5/OQI6/Coverage integration seams; the exact
API/frontend visibility decision; the exact I1/I2 implementation boundary; and the exact migration/table-
count plan. It does not implement any of this. Its only authorized repository writes are itself and its
companion Artifact Authorization.

## 3. Frozen Timeliness definition (AD-14, restated exact, binding)

> **Timeliness determines whether present enterprise evidence is current enough for a specific governed
> contextual use.** It is never a single global age threshold.

Binding invariants (restated from CDD-046 §41 and the OQI-H5-DR, unmodified, extended to zero exception):

```
AGE ≠ TIMELINESS DEFECT
RECENCY ≠ BUSINESS FITNESS
SYSTEM WRITE TIME ≠ SOURCE OBSERVATION TIME
RE-INGESTION MUST NOT LAUNDER STALE EVIDENCE
```

Timeliness is explicitly not: timestamp existence: Completeness's concern when absent; generic age
without governed context; a universal freshness threshold; Accuracy; Consistency; Reasonableness;
Integrity; source authority; or system persistence recency (`created_at`/`updated_at`/`produced_at` on any
non-`FieldValueEvidence` table).

## 4. Frozen Finding taxonomy (AD-07/§19, exact, binding)

Exactly two Finding types, never a third, never merged:

```
STALE_SOURCE_EVIDENCE          evaluation_horizon - observed_at > freshness_window_seconds
INGESTION_LATENCY_EXCEEDED     received_at - observed_at > ingestion_sla_seconds
```

**Threshold boundary (frozen, exact equality semantics)**:

```
age_seconds <= threshold_seconds   →  SATISFIED
age_seconds >  threshold_seconds   →  VIOLATED
```

Equality (`age_seconds == threshold_seconds`) is `SATISFIED` — the threshold names the maximum acceptable
age, inclusive. Implementation must not improvise this boundary; it is binding as written.

A given evidence/policy pair produces **up to two independent Evaluation lineages** — one per Finding type
— each governed by its own threshold field on the same `TimelinessPolicy` row. If a threshold field is
`NULL` on the applicable `ACTIVE` policy, that specific reason path is simply never evaluated (zero rows
for that type only) — the other reason path, if its own threshold is populated, is unaffected.

## 5. Frozen temporal axes

```
Source observation time    FieldValueEvidence.observed_at   (existing, immutable, identity-bearing)
Noetva receipt time        FieldValueEvidence.received_at   (existing, immutable, excluded from identity)
Evaluation horizon         NEW — the governed "as-of" instant an Evaluation represents (tz-aware, explicit,
                            caller-supplied or defaulted to the injected clock at call time)
Evaluation write time      NEW — evaluated_on, the wall-clock instant the Evaluation row was actually
                            persisted (tz-aware)
```

No effective/validity-interval field is introduced — no repository evidence justifies one for H5 v1
(avoids timestamp proliferation). `evaluation_horizon` is the sole authoritative "as-of" instant; age is
always computed as `evaluation_horizon - observed_at` (or `received_at - observed_at` for the latency
path), **never** `datetime.now() - observed_at`, **never** any table's `created_at`/`updated_at`, **never**
`EnterpriseEntityResolutionRecord.produced_at` or any Entity/Semantic/Assertion/Knowledge Resolution
record's timestamp (OQI-H5-DR §E.3's confirmed laundering-risk fields — explicitly prohibited as a
Timeliness input).

## 6. Frozen evaluation/outcome semantics

Stored outcomes: `SATISFIED` / `VIOLATED` only — identical vocabulary to every existing OQI evaluator.
`NOT_EVALUABLE` is represented by zero persisted `Evaluation` row, never a stored third value. Frozen cases
producing zero rows for a given reason path:

```
1. No ACTIVE TimelinessPolicy exists for the (information_element_requirement, business_process) pair.
2. The ACTIVE policy's relevant threshold field (freshness_window_seconds or ingestion_sla_seconds) is
   NULL for the reason path being considered.
3. No FieldValueEvidence exists for the subject at or before evaluation_horizon.
```

None of these may ever produce a stored `SATISFIED` row. A database state that is genuinely invalid (e.g.
an `ACTIVE` policy row that somehow violates its own CHECK constraints) is a defect to fail closed on with
an application error, never silently reinterpreted as `NOT_EVALUABLE`.

## 7. Frozen policy anchor — DD-06 resolved (binding)

**Resolved: Option B — `InformationElementRequirement` only, not `SourceField`.**

Evidence: `SourceFieldORM` carries no `tenant_id` column of its own (tenant is resolved transitively
through `source_object_id`, `backend/app/infrastructure/persistence/models/source_field.py:3-5`), and
`FieldValueEvidenceORM` carries no `tenant_id` column either (transitively through `source_field_id ->
source_objects.tenant_id`, `field_value_evidence.py:3-5`). A composite tenant-qualified FK from a
tenant-owned `TimelinessPolicy` directly to `source_field_id` is therefore structurally unbuildable without
denormalizing `tenant_id` onto an existing, out-of-H5-scope, shared evidence table — a change this
document does not authorize (§17 prohibited scope).

`InformationElementRequirementORM`, by contrast, is confirmed **shared-platform, global, no `tenant_id`
column at all** (`blueprint.py:129-138`, docstring: "Global, product-owned; no `tenant_id` anywhere") —
anchoring `TimelinessPolicy` to it requires only a **plain** FK, exactly mirroring
`relationship_type_id`/`relationship_requirement_id`'s established plain-FK-to-shared-platform pattern from
H4 (CDD-050 §27). No tenant-composability problem exists on this side of the anchor at all.

**Practical consequence, disclosed**: a raw source field that has never been mapped to a governed
Information Element (via the existing H1 semantic-mapping layer, CDD-019) cannot have a `TimelinessPolicy`
and is therefore permanently `NOT_EVALUABLE` for Timeliness until it is mapped. This is judged correct, not
a gap: Timeliness is defined as a business-contextual concern, and an unmapped field has no governed
business meaning to be timely *for* yet.

No XOR/dual-anchor machinery is required — resolving DD-06 to a single anchor type removes an entire class
of constraint complexity the DR left open.

## 8. Frozen policy architecture

`TimelinessPolicy` — tenant-owned, versioned, governed:

```
Table: oqi_timeliness_policies
PK:    (policy_id, version)   — policy_id STABLE across versions of "the same governed policy" (assigned
                                 once, reused on every subsequent version row), version increments from 1.
                                 This mirrors OqiBusinessProcessORM's own (process_id, version) shape
                                 exactly (backend/app/infrastructure/persistence/models/oqi_business_impact.py:33-34)
                                 — the closest, most directly relevant existing precedent, since
                                 TimelinessPolicy references BusinessProcess anyway.

Columns (conceptual):
  policy_id                          UUID, stable lineage identity
  version                            INTEGER, >= 1
  tenant_id                          VARCHAR(200), NOT NULL
  information_element_requirement_id UUID, NOT NULL, FK -> information_element_requirements (plain FK,
                                      shared-platform target, §7)
  business_process_id                UUID, NOT NULL  \
  business_process_version           INTEGER, NOT NULL \  composite FK -> oqi_business_processes
                                                            (process_id, version) — §9 for the tenant
                                                            enforcement decision on this specific edge
  freshness_window_seconds           INTEGER, NULLABLE, CHECK (> 0) when non-NULL
  ingestion_sla_seconds              INTEGER, NULLABLE, CHECK (> 0) when non-NULL
  status                             VARCHAR(16), NOT NULL, {ACTIVE, RETIRED}
  created_by                         VARCHAR(200), NOT NULL
  created_on                         TIMESTAMPTZ, NOT NULL

CHECK constraint (structural, required):
  freshness_window_seconds IS NOT NULL OR ingestion_sla_seconds IS NOT NULL
  (an ACTIVE policy governing neither reason path is meaningless and must be rejected structurally)

Partial unique index (exactly one ACTIVE version per exact anchor, required):
  UNIQUE (tenant_id, information_element_requirement_id, business_process_id, business_process_version)
  WHERE status = 'ACTIVE'
```

Supersession creates a new row with the same `policy_id`, `version + 1`; the prior row transitions to
`RETIRED` in the same transaction (mirrors `QualityCoveragePolicy`'s immutable-version discipline — rows
are never updated in place, following `oqi_quality_coverage/policy.py:60-183`'s established pattern).

## 9. Frozen decision — `oqi_business_processes` tenant-FK correction (disclosed, additive-only)

**Discovered defect (P1, disclosed here in full, not silently worked around)**: `OqiBusinessProcessORM`
(`oqi_business_impact.py:25-41`) carries `tenant_id` but has **no** `UniqueConstraint(tenant_id,
process_id, version)` — only independent, non-composite indexes on `tenant_id` and `process_id`
separately. The existing consumer, `OqiBusinessDependencyORM.business_process_id/version`
(`oqi_business_impact.py:47-52`), is therefore a **plain composite FK on `(process_id, version)`, not
tenant-qualified** — structurally the identical defect class H4-R1 found and corrected for `source_objects`
and `enterprise_entity_resolution_records`, present here in an earlier (OQI6/CDD-044), already-shipped
subsystem, never previously adversarially tested for this exact attack shape.

**Frozen decision**: authorize one narrow, purely additive correction as part of H5-I1 — add
`UniqueConstraint("tenant_id", "process_id", "version", name="uq_oqi_business_processes_tenant_pk")` to
`OqiBusinessProcessORM`. This is safe by construction and requires no data migration/backfill: `(process_id,
version)` is already the table's primary key, so `(tenant_id, process_id, version)` is trivially unique as
a superset of an already-unique key — no duplicate-row precondition check is needed (unlike H4-R1's
retrofit, which corrected an FK against data that could already have violated the intended invariant; here
no such risk exists structurally). `oqi_timeliness_policies` then composes a proper tenant-qualified
composite FK against this corrected key: `FOREIGN KEY (tenant_id, business_process_id,
business_process_version) REFERENCES oqi_business_processes(tenant_id, process_id, version)`.

**Explicitly NOT authorized by this document**: correcting `OqiBusinessDependencyORM`'s own existing plain
FK to the same corrected key. That is a genuine, real, separately-scoped OQI6 tenant-isolation defect this
phase discovers and discloses, but does not fix — fixing it touches an existing, already-shipped,
out-of-H5-scope table/query path with its own regression surface, and deserves its own narrow,
independently-verified correction exactly as H4-R1 was its own independently-governed amendment, not a
change bundled silently into an unrelated H5 phase. **Recommendation, not authorization**: a future
`OQI6-R1`-style governance correction should adversarially re-verify and fix `OqiBusinessDependencyORM`'s
FK using the identical `session.add()`+`flush()` direct-insertion attack methodology H4-R1 established.

## 10. Frozen policy precedence

No runtime precedence hierarchy exists or is needed. The partial unique index in §8 makes "more than one
applicable ACTIVE policy for an exact anchor" a structural impossibility, not a runtime ambiguity to
resolve. There is no coarser-grained (dimension-wide, source-wide) fallback policy in H5 v1 — no repository
evidence evidences a need for one, and inventing one would be scope creep beyond what DD-06's resolution
(§7) requires.

## 11. Frozen threshold representation

Plain integer seconds: `freshness_window_seconds`, `ingestion_sla_seconds`. Age computed in application
code as `int((evaluation_horizon - observed_at).total_seconds())`, compared with plain integer arithmetic —
no floating-point time comparison, no PostgreSQL `INTERVAL` type (no existing table in this repository uses
one — confirmed absent from every migration; introducing one here would be a novel, unprecedented pattern
this document does not authorize). `CheckConstraint(> 0)` on each column when non-NULL, per §8.

## 12. Frozen clock architecture

`clock: Callable[[], datetime]`, default `lambda: datetime.now(UTC)`, injected into the new Timeliness
application service constructor — identical to every existing OQI evaluation service (e.g.
`oqi_integrity_structural_evaluation_service.py:101`). Production wiring: the existing
`core/dependency_container.py:121-123` clock (`functools.partial(datetime.now, UTC)`), reused unmodified,
not re-wired. `evaluation_horizon` defaults to `clock()` at call time unless a caller supplies an explicit
historical horizon (§13). Tests use fixed injected clock constants — no `freezegun`, no `sleep()`-based
timing assertions, matching the repository's exclusive existing convention (zero `freezegun` hits
repository-wide, confirmed).

## 13. Frozen historical/as-of semantics

Reuse the existing `evaluation_horizon`-is-authoritative discipline unmodified: a caller may supply an
explicit historical `evaluation_horizon`; age is always computed against that value, never against
wall-clock `datetime.now()`, regardless of when the evaluation actually executes. This mirrors the
established `received_at <= evaluation_horizon` filtering idiom used by every existing OQI evaluator
(`oqi_quality_evaluation_repository.py:20-26`) and is required for audit reproducibility (Principle 13).

## 14. Frozen timezone/clock-skew boundary

All new timestamp columns are `TIMESTAMPTZ`, defensively re-validated tz-aware at domain-object
construction, matching universal existing convention (zero naive-datetime columns anywhere in this
repository). **Clock-skew ownership**: a future-dated `observed_at` (a source clock running ahead) is
**not** a Timeliness concern — it is deferred to a future, separately-governed Reasonableness rule (per
CDD-046 §11's discriminator discipline: Timeliness asks "is present evidence current enough," never "is
this timestamp itself plausible"). `TimelinessPolicy` carries no skew-tolerance field in H5 v1. This is a
frozen scope boundary, not an oversight — if a future concrete gap proves this insufficient, it is a new,
separately-governed decision, not an H5 amendment.

## 15. Frozen multi-source semantics

Each source's `FieldValueEvidence` is evaluated independently against whichever `TimelinessPolicy` applies
to its resolved `(InformationElementRequirement, BusinessProcess)` pair — no cross-source aggregation,
consensus, or authority adjudication of any kind occurs inside Timeliness. A stale authoritative source and
a fresh secondary source each produce their own independent Evaluation/Finding; **authority never cures
staleness**, and **fresh secondary evidence never silently substitutes for a stale authoritative source's
own Timeliness Finding** — both are governed exclusively by Consistency/authority (CDD-040, unchanged).

## 16. Frozen cross-dimension boundaries

Restated exact from CDD-046 §11/§41, zero deviation:

```
Completeness vs Timeliness    absent value -> Completeness fires, Timeliness NOT_EVALUABLE (nothing to date)
Timeliness vs Accuracy        fully independent — fresh-but-inaccurate and stale-but-correct both representable
Timeliness vs Consistency     independent, coexist without interaction — see §15
Timeliness vs Reasonableness  future/impossible timestamps -> Reasonableness (§14), never Timeliness
Timeliness vs Integrity       no overlap — Integrity is graph-shaped, Timeliness is evidence-age-shaped
```

## 17. Frozen Finding identity

```
derive_timeliness_finding_id(tenant_id, policy_id, finding_type, subject_identity)
```

where `policy_id` is the **stable lineage identity** (§8 — never `version`), `finding_type` is
`STALE_SOURCE_EVIDENCE` or `INGESTION_LATENCY_EXCEEDED` (the two types never collide, since they are
distinct identity inputs), and `subject_identity` is the evaluated `source_object_id` (the tenant-composable
anchor, §18). **Excluded from identity**: `evaluation_horizon`, `evaluated_on`, computed age, the specific
`field_value_evidence_id`, and `policy` `version` — a policy threshold tuning must not create a new Finding
lineage; only a change of anchor (a different `InformationElementRequirement`/`BusinessProcess` pair, i.e. a
different `policy_id`) does. This directly satisfies Principle 14 (age increasing must never churn
identity) and mirrors `derive_quality_finding_id`'s exact discipline (`oqi/finding.py:194-212`).

## 18. Frozen Evaluation identity

```
derive_timeliness_evaluation_id(tenant_id, policy_id, policy_version, finding_type, source_object_id,
                                 field_value_evidence_id, evaluation_horizon)
```

Includes `policy_version`, `field_value_evidence_id`, and `evaluation_horizon` (all deliberately excluded
from Finding identity) — an Evaluation is an immutable, append-only ledger row representing one concrete
run; repeated identical execution (same inputs) converges to the same row (idempotent insert, no
duplicate), matching every existing OQI evaluator's ledger discipline.

## 19. Frozen lifecycle

Reuse the proven six-branch transition table unmodified in shape, applied independently per `finding_type`:

```
no-finding + SATISFIED  -> none
no-finding + VIOLATED   -> OPEN
OPEN       + VIOLATED   -> OPEN (state_revision++)
OPEN       + SATISFIED  -> RESOLVED
RESOLVED   + SATISFIED  -> RESOLVED
RESOLVED   + VIOLATED   -> OPEN (reopen, occurrence_count++/reopen_count++)
```

Resolution requires an independent, fresh `SATISFIED` re-evaluation only — never a human/agent assertion,
never a remediation authorization, never an execution report. `REMEDIATION ≠ RESOLUTION` applies with zero
Timeliness-specific exception.

## 20. Frozen continuous-time reevaluation model (H5 v1, binding)

# EVALUATE ON READ / EXPLICIT REQUEST

Timeliness evaluation executes synchronously when a governed caller (API request, seeder, agent
investigation) requests current Timeliness state for a subject, using `evaluation_horizon = clock()` at
that call unless a valid historical horizon is supplied (§13). **No scheduler, cron, background worker, CDC
listener, or polling framework is introduced or authorized by H5 v1** (§17 prohibited scope). The
explainability contract (§21) must state "Timeliness evaluated at `evaluated_on`" and must never imply
continuously-guaranteed freshness.

## 21. Frozen explainability contract

Persisted, not generated-prose, fields sufficient to answer every question in this table:

```
Why did this Finding exist?          Finding identity (§17) + the Evaluation ledger row that opened it (§18)
What evidence was used?              field_value_evidence_id (traceable, even though not identity-bearing)
What rule/policy was applied?        policy_id + policy_version (Evaluation-level, §18)
What evidence was missing?           NOT_EVALUABLE reason (§6) — zero row + the specific missing-input case
What ontology context mattered?      OQI4 impact chain (§22, unchanged mechanism)
What business context mattered?      BusinessProcess (already governed, unchanged)
When was this evaluated?             evaluation_horizon + evaluated_on, both persisted, both surfaced
What would resolve it?               A fresh SATISFIED re-evaluation (§19) — no other path
Who authorized remediation?          N/A for Timeliness v1 — no authorization surface exists (§23)
```

## 22. Frozen OQI4 integration

Add exactly `resolve_timeliness_finding_origin` / `resolve_timeliness_finding_subject`, mirroring
`resolve_integrity_structural_finding_origin`/`_subject`
(`oqi_ontology_impact_evaluation_repository.py:268-323`) exactly in shape. `FindingFamily`
(`oqi_ontology_impact/evaluation.py:38-45`) stays permanently closed — never touched. No column-width
migration is needed: `finding_family`/adjacent columns are already `String(16)` (widened by `0037` for
`"INTEGRITY"`), and `"TIMELINESS"` (10 chars) fits.

## 23. Frozen OQI5 integration

Timeliness routes to the existing **zero-candidate `STEWARD_INVESTIGATION`** dispatch path in
`extract_candidates` (`oqi_remediation_service.py:~107-134`), mirroring the `INTEGRITY`/`REASONABLENESS`
precedent exactly. **No new `RemediationActionType` member, no new `RemediationCandidateBasis` member, no
external-system-write authority of any kind is introduced.** An agent may recommend "refresh source
evidence" as advisory explanation text; this recommendation carries zero authorization weight and
triggers no automated action — `RECOMMENDATION ≠ AUTHORIZATION` applies with zero exception (CDD-046 §35's
own conclusion, adopted verbatim, not revisited).

## 24. Frozen OQI6 integration

Add exactly one or two new `selects.append(...)` blocks to `compute_subject_finding_state`'s `union_all`
(`oqi_business_impact_repository.py:129-333`) for `oqi_timeliness_findings` — mechanically identical in
shape to H4's two additions. `RelianceState`'s decision logic and its three-value vocabulary
(`RELIANCE_SUPPORTED`/`RELIANCE_AT_RISK`/`RELIANCE_UNKNOWN`) are **unmodified** — the population step
alone gains the new branch(es); the dimension-agnostic "any open Finding" predicate requires zero change.

## 25. Frozen Coverage integration

Replace the current literal fallthrough in `has_qualifying_coverage_for_dimension`
(`oqi_quality_coverage_policy_repository.py:304-307`, currently `# UNIQUENESS, TIMELINESS: no evaluator
exists ... return False`) with a real `TIMELINESS` dispatch branch, existence-only, subject-scoped, querying
`oqi_timeliness_evaluations` for `≥1` qualifying row. The `UNIQUENESS` half of that fallthrough comment is
untouched — it remains exactly as-is, since Uniqueness has no evaluator in this or any prior phase.

## 26. Frozen API/frontend visibility decision

**Adopted: close the pre-existing visibility gap for both `INTEGRITY` and `TIMELINESS` together, in I2.**
The generic `list_findings` (`oqi_product_experience_service.py:414-489`) currently branches only on
`OQI1/OQI2/OQI3` — `INTEGRITY` findings are invisible via `/oqi/findings` today, an inherited, disclosed,
not-H5-introduced gap. Rationale for closing both together rather than repeating the gap for Timeliness:
H5's own product mandate is to surface DQ gaps honestly; shipping a second invisible dimension while a
known-invisible one already exists would compound, not merely repeat, an already-disclosed inconsistency,
and the fix is narrow (two additive branches in one service method, two additive `<option>` entries in one
dropdown) — not a redesign. Scope is strictly: add `INTEGRITY` and `TIMELINESS` branches/options only. No
other findings-experience change is authorized.

## 27. Frozen deterministic crown

Extends `demo_oqi_seeder.py`'s existing fixed-`SEED_TIMESTAMP` + injectable-per-phase-clock + `uuid5`-ID
pattern, unmodified in shape. No Shipment/Carrier entity exists in the repository today (confirmed absent);
H5's crown introduces new demo-only entity/source names (e.g. a `Shipment` `EnterpriseEntity` type, a
`Carrier` source system alongside the existing `SAP`/`PLM`) — explicitly classified as demo-seeder data, not
a new production ontology/domain architecture. Minimum required cases, all independently seeded through
real evaluator services (never a pre-scripted terminal state, per CDD-046 §45):

```
A. Stale SAP source evidence, ACTIVE policy exists      -> STALE_SOURCE_EVIDENCE, VIOLATED
B. Fresh Carrier source evidence, ACTIVE policy exists  -> SATISFIED (zero Finding)
C. Evidence exists, no ACTIVE policy for its anchor     -> NOT_EVALUABLE (zero Evaluation row)
D. Case A's Finding propagates via OQI4 to a real ontology assertion
E. Case D's subject correctly computes RELIANCE_AT_RISK via OQI6
F. Recommendation text is visible on Case A's Finding; no authorization/mutation occurs
G. Re-running the seeder/evaluation is idempotent — zero duplicate Evaluation/Finding rows
```

## 28. Frozen migration strategy

```
0039_oqi_h5_timeliness_policy.py
    CREATE  oqi_timeliness_policies
    MODIFY  oqi_business_processes  (+ UniqueConstraint(tenant_id, process_id, version), §9 — additive
            only, no data change, no existing query/behavior affected)
    down_revision: 0038_oqi_h4_reference_tenancy

0040_oqi_h5_timeliness_evaluation.py
    CREATE  oqi_timeliness_evaluations
    CREATE  oqi_timeliness_findings
    down_revision: 0039_oqi_h5_timeliness_policy

Pre-H5 table count:     120 (unchanged since H4 closure, re-verify fresh at I1 start per every prior
                              OQI-phase's own established discipline — do not trust this document's figure
                              without a live re-count)
Post-0039 table count:  121  (+ oqi_timeliness_policies; oqi_business_processes MODIFY adds zero tables)
Post-0040 table count:  123  (+ oqi_timeliness_evaluations, oqi_timeliness_findings)
Final expected table count: 123
```

Required round-trip: `120 → 121 → 123 → 121 → 120 → 123` (each migration's own upgrade/downgrade/re-upgrade
proven independently, then the full two-migration chain proven together, mirroring CDD-050 §23's
discipline exactly). Single Alembic head required at all times. No migration beyond these two is
authorized. No H1-H4 migration (`0001`-`0038`) is rewritten.

## 29. Frozen tenant isolation (non-negotiable, binding)

Every tenant-owned H5 relationship uses a composite tenant-qualified FK, proactively, not retrofitted:

```
oqi_timeliness_policies.(tenant_id, business_process_id, business_process_version)
    -> oqi_business_processes(tenant_id, process_id, version)          [requires §9's additive correction]
oqi_timeliness_evaluations.(tenant_id, policy_id, policy_version)
    -> oqi_timeliness_policies(tenant_id [implicit via policy row], policy_id, version)
    -- exact shape: oqi_timeliness_policies itself needs (tenant_id, policy_id, version) uniqueness for
       this composite FK to compose; add it alongside the table's own PK at creation (§8), not retrofitted
oqi_timeliness_evaluations.(tenant_id, source_object_id) -> source_objects(tenant_id, source_object_id)
    [uq_source_objects_tenant_pk, already exists post-0038 — composes directly, zero further correction]
oqi_timeliness_findings.(tenant_id, policy_id) -> oqi_timeliness_policies(tenant_id, policy_id, ...)
    [same shape as evaluations]
oqi_timeliness_findings.(tenant_id, source_object_id) -> source_objects(tenant_id, source_object_id)
```

`information_element_requirement_id` and `field_value_evidence_id` remain **plain** FKs — the former
because its target is shared-platform with no tenant column (§7, correct by design, mirrors
`relationship_requirement_id`); the latter because `field_value_evidence` itself has no tenant column
anywhere in this repository (§7's evidence) and is referenced by plain FK everywhere it is used today (the
established, documented CDD-022 convention) — not a new H5 weakness.

**Mandatory, non-deferrable verification**: I1 must prove, against real PostgreSQL, using direct
`session.add()`+`flush()` insertion that deliberately bypasses the service layer, that every composite FK
above rejects a cross-tenant row with `IntegrityError` — for every relationship listed, not a sample. This
runs in I1, not deferred to VM, per the explicit lesson of H4-R1 (§43.10 fail-closed condition).

## 30. Explicit non-goals / prohibited scope (binding)

```
Scheduler / cron / background-worker / CDC / polling framework
Kafka / event sourcing / temporal database
External-system writes of any kind (no "refresh source," no connector trigger)
New RemediationActionType or RemediationCandidateBasis member
New agent role
Clock-skew tolerance inside TimelinessPolicy
Correcting OqiBusinessDependencyORM's own pre-existing FK (§9 — disclosed, not authorized)
Reopening FindingFamily
Expanding RelianceState's vocabulary
Frontend redesign beyond the two additive dropdown options (§26)
Any H1-H4 semantic change
Any Uniqueness implementation
Fixing the inherited Docker frontend healthcheck loopback-bind mismatch
Cleanup of docs/product/
```

## 31. STOP conditions (binding for this document and for I1/I2)

STOP and return to governance if: `origin/main` moves materially before implementation begins; the
semantic-mapping mechanism resolving `InformationElementRequirement -> SourceField -> FieldValueEvidence`
(referenced in §21, needed to actually locate evidence for a governed policy) proves not to exist or not to
support this lookup shape as assumed (P2, flagged in §33, verify at I1 kickoff before writing the
evaluator); any composite tenant FK in §29 fails its real-PostgreSQL adversarial proof; the table-count
round-trip in §28 does not match; any H1-H4 crown regresses; any P0/P1 defect is discovered requiring a
correction beyond §9's narrow, pre-authorized scope.

## 32. Implementation boundary (I1/I2, exact, binding)

**I1 — Timeliness core**: `oqi_timeliness_policies`/`_evaluations`/`_findings` tables and the `0039`/`0040`
migrations (including the `oqi_business_processes` correction), domain dataclasses, evaluator service,
repositories, the OQI4 resolver-method pair, all tenant-isolation adversarial proof, the demo crown, and
I1's own dedicated test files. Independently verified before I2 begins — no downstream integration is
authorized to assume I1's shape until I1's own crown/tenant tests are green against real PostgreSQL.

**I2 — Downstream governed integration**: the Coverage dispatch branch, the OQI6 `union_all` addition, the
OQI5 zero-candidate dispatch branch, and the API/frontend visibility correction for `INTEGRITY` +
`TIMELINESS` together (§26). Depends on I1's tables/services existing and passing their own tests.

No I3 is authorized — nothing in the OQI-H5-DR or this governance pass surfaces a boundary of comparable
independent risk.

## 33. Deferred / P2 verification item (named so I1 does not invent it silently)

The exact repository mechanism resolving "which `SourceField`(s) currently map to a given
`InformationElementRequirement`" (the H1 semantic-mapping layer, CDD-019) must be read and confirmed at I1
kickoff before the evaluator's evidence-lookup query is written. This document freezes the *semantic*
requirement (Timeliness evaluates the latest qualifying `FieldValueEvidence` for whichever `SourceField`(s)
currently map to the policy's `InformationElementRequirement`, reading the mapping read-only, exactly as
Integrity's Reference evaluator read `ResolutionOutcome` read-only, CDD-050 §10.2 precedent) without
re-deriving the exact repository/method names, which is an implementation-time lookup, not a governance
decision.

## 34. Acceptance criteria (binding)

An implementation phase against this document is acceptable only if: it implements exactly the semantics
frozen in §3-§27 without inventing new ones; it does not modify `FindingFamily`, `RemediationActionType`,
or `RemediationCandidateBasis`; it does not modify `OqiBusinessDependencyORM`'s existing FK (§9); it does
not introduce any scheduler/external-write capability; it proves every composite tenant FK adversarially in
I1, not VM; it passes the deterministic crown (§27) as real, executable tests; and it satisfies the
companion Artifact Authorization's exact path list with zero unauthorized-path additions.

## 35. Governance recommendation

# OQI-H5-G COMPLETE — READY FOR OQI-H5-I1
