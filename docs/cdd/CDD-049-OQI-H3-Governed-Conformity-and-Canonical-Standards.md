# CDD-049 — OQI-H3 Governed Conformity and Canonical Standards

Version: 1.0 FROZEN
Status: FROZEN (architecture only — implementation authorized only via the paired Artifact Authorization)
Implementation state: NOT STARTED
Governing authorities: CDD-046 (FROZEN, Nine-Dimension Architecture — this document implements exactly
Boundary 3, `CONFORMITY`), `CDD-046-QualityRule-Ownership-Erratum.md` (FROZEN, `QualityRule` is shared
platform structure, read as binding precedent), CDD-047 (FROZEN, H1 Governed Quality Coverage + Reliance
Generalization — `CoverageDimension.CONFORMITY` already exists, consumed unmodified), CDD-048 (FROZEN, H2
Governed Accuracy + Reasonableness + Reference Evidence + Generalized Finding Origin — `QualityDimension`
extension precedent, `QualityFindingOrigin` reused unmodified), CDD-039/040/041/042/043/044/045 (FROZEN,
OQI1-7, read-only consumed, never modified by this document), CDD-017/019 (Blueprint / Information
Element / Semantic Mapping lineage, read as the load-bearing anchor precedent — see §8)

Mandatory template: CDD Template v2.2 (this repository's established house style)

**Publication note**: this document freezes the exact governed semantics, schema, evaluator contract,
Consistency-integration algorithm, provenance model, Finding design, coverage/Reliance/impact
integration, remediation shape, authorization, migration plan, and test matrix required to implement
`CONFORMITY` — the tenth OQI-H0 architectural boundary and the third dimension actually implemented,
following exactly the discovery performed in OQI-H3-DR and the Product Owner decisions PO-H3-01 through
PO-H3-03. Implementation is authorized only via the paired
`CDD-049-OQI-H3-Governed-Conformity-and-Canonical-Standards-Artifact-Authorization.md`.

## 1. Purpose

Allow Noetva to answer, for any governed observation with an applicable governed canonical
representation: *"is this observed representation expressed in its governed canonical form?"* —
independent of whether the value is permitted (Validity), independent of whether it is correct
(Accuracy), and as an input to whether cross-source observations of the same governed fact should be
compared as their canonical projections rather than their raw representations (Consistency). This
closes the tenth dimension CDD-046 named and the third to receive a concrete evaluator, following
exactly the extend-existing-family precedent H2 established for Accuracy.

## 2. Capability claim (exact, binding)

Noetva can: represent a governed, versioned, shared-platform `CanonicalStandard` anchored to a governed
Information Element; deterministically resolve an observed representation's canonicalization outcome
(`CANONICAL` / `ALIAS_RESOLVED` / `NOT_MAPPED` / `AMBIGUOUS` / `NO_STANDARD`) against the exact standard
version applicable at evaluation time; produce a `CONFORMITY`-dimension `QualityFinding`
(`NON_CANONICAL_REPRESENTATION`) exactly when a recognized non-canonical alias is observed; generalize
cross-source `CONSISTENCY` comparison to compare canonical projections instead of raw representations
when, and only when, every required known participant canonicalizes successfully under one governed
standard/version, failing closed to `NOT_EVALUABLE` otherwise; propose an evidence-backed `UPDATE_FIELD`
remediation candidate for a recognized non-canonical alias; and do all of this without mutating any
`FieldValueEvidence` row, without altering H2 Accuracy's comparison semantics, without inventing a new
Finding-origin taxonomy, and without silently changing Consistency behavior for any subject with no
applicable `CanonicalStandard`.

No broader claim is authorized. In particular: no claim of semantic/unit conversion capability; no claim
that Accuracy consults canonical projection; no claim of tenant-specific canonical standards; no public
CanonicalStandard management API or frontend surface; no claim about `UNIQUENESS`, `TIMELINESS`, or
`INTEGRITY`, which remain entirely unimplemented.

## 3. Product Owner decisions frozen (PO-H3-01 through PO-H3-03)

**PO-H3-01 — Anchor.** `CanonicalStandard` is anchored to a governed Information Element
(`information_element_requirement_id`), never independently per `SourceField`. §8 proves this is
implementable against real, existing, governed repository structure — no architectural prerequisite is
missing.

**PO-H3-02 — Accuracy non-interference.** H3 canonical projection applies to `CONFORMITY` and
`CONSISTENCY` only. `OqiAccuracyEvaluationService`'s comparison semantics are untouched, unmodified,
unauthorized to change by this document. §18 freezes explicit regression requirements.

**PO-H3-03 — Ownership.** `CanonicalStandard` is shared-platform only. Tenant override is deferred,
unauthorized, unmodified by this document (CDD-046 §43 DD-02 remains open, not resolved here).

## 4. `QualityDimension` — additively extended

```
QualityDimension (StrEnum, additively extended a third time):
    COMPLETENESS   (CDD-039)
    VALIDITY       (CDD-039)
    CONSISTENCY    (CDD-040)
    ACCURACY       (CDD-048)
    CONFORMITY     (NEW, this document)
```

**Binding placement decision**: `CONFORMITY` joins `QualityDimension` — it does **not** join
`BusinessRulePurpose`. `REASONABLENESS` remains exactly where CDD-048 froze it
(`BusinessRule.dimension`, BusinessRule-shaped) — this document does not touch `BusinessRulePurpose` in
any way. Semantic dimension vocabulary (`QualityFindingOrigin.quality_dimension`, the union of
`QualityDimension` and `BusinessRulePurpose` values) and evaluator/storage-family identity
(`FindingStorageFamily`) remain structurally distinct concepts, exactly as CDD-048 §12 established; this
document does not collapse them into one physical family merely for symmetry. `CoverageDimension`
(CDD-047 §4) already contains `CONFORMITY` and requires **zero change** — only `has_qualifying_
coverage_for_dimension`'s dispatch gains a new branch (§21).

## 5. Conformity — exact governed definition (frozen)

```
CONFORMITY: is an observed representation expressed in the governed canonical representation defined
for the applicable Information Element?
```

Conformity does **not** ask:

```
"Is this value permitted?"    -> VALIDITY
"Is this value correct?"      -> ACCURACY
"Do sources agree?"           -> CONSISTENCY
```

**Frozen invariants** (binding, testable — see §32 for the complete crown set):

```
VALID ≠ CONFORMING
CONFORMING ≠ ACCURATE
CANONICAL ≠ ACCURATE
```

A value can be simultaneously Valid and non-Conforming (`"US"` domain-permitted, not the governed
canonical `"USA"`), simultaneously Conforming and Accuracy-`VIOLATED` (correctly formatted, wrong fact),
and simultaneously non-Conforming and Accuracy-`SATISFIED` (correct fact, non-standard format) — CDD-046
§11/§24's discriminator and worked table, re-affirmed unmodified, govern every one of these
combinations.

## 6. `_ALLOWED_COMBINATIONS` extension (frozen, exact)

One new row, mirroring `ACCURACY`'s own row exactly:

```
(QualityDimension.CONFORMITY, QualityFindingType.NON_CANONICAL_REPRESENTATION, None)
```

`QualityFindingType` gains exactly one new member: `NON_CANONICAL_REPRESENTATION` (CDD-046 §19, already
named). `_validate_conformity_parameters` is required, following `_validate_accuracy_parameters`'s exact
shape: **`rule_parameters` must be empty** — the applicable `CanonicalStandard` is resolved dynamically
per observation via `QualityRule.information_element_requirement_id` (already a required field on every
`QualityRule`, unmodified in shape by this document), never configured per-rule. This mirrors exactly
why Accuracy's `rule_parameters` is empty (CDD-048 §7) — no Conformity-specific key is authorized.

## 7. Canonical Standard scope (frozen, binding)

`CanonicalStandard` governs **representation-level canonicalization only**: a deterministic mapping from
zero or more recognized alias strings to exactly one canonical string, for a governed semantic concept.

```
AUTHORIZED:      "US" -> "USA"        (alias -> canonical, representation-level)
                 "U.S." -> "USA"
                 "Y" -> "YES"          (illustrative — boolean-shaped representations)

NOT AUTHORIZED:  "1 kg" -> "1000 g"    (semantic/unit conversion — a different, heavier problem:
                                        dimensional analysis, rounding correctness, not representation
                                        mapping)
                 currency conversion
                 fuzzy/similarity-based matching of any kind
                 probabilistic or LLM-assisted resolution
                 Entity Resolution normalization reuse (§L below, ER's own governance boundary)
```

H3 is explicitly, permanently **not** a general-purpose transformation engine. A future CDD would be
required to introduce semantic/unit conversion; nothing in this document anticipates or half-authorizes
it.

## 8. Information Element anchor — proof of feasibility (binding, PO-H3-01 satisfied)

Independently re-verified against current merged-main source (no invention required):

```
information_element_requirements   (backend/app/infrastructure/persistence/models/blueprint.py,
                                     InformationElementRequirementORM) — confirmed shared, global,
                                     no tenant_id anywhere (CDD-017 §9, re-confirmed).
                                     Primary key: information_element_requirement_id (UUID).

semantic_mappings                  (backend/app/infrastructure/persistence/models/semantic_mapping.py,
                                     SemanticMappingORM) — the EXISTING, GOVERNED, database-enforced
                                     resolution mechanism:
                                       source_field_id (FK -> source_fields)
                                       information_element_requirement_id
                                           (FK -> information_element_requirements)
                                     uq_semantic_mappings_approved_source_field: a PostgreSQL partial
                                     unique index, WHERE governance_status = 'Approved' — guarantees AT
                                     MOST ONE Approved semantic mapping per source_field_id. The
                                     resolution SourceField -> InformationElementRequirement is therefore
                                     already deterministic wherever an Approved mapping exists, and
                                     provably absent (not ambiguous — genuinely absent) otherwise.

QualityRule.information_element_requirement_id  (backend/app/domain/oqi/quality_rule.py:339,
                                     backend/app/infrastructure/persistence/models/oqi_quality_rule.py:39)
                                     — ALREADY a required, non-empty field on EVERY QualityRule of every
                                     dimension today (String(200) in the ORM, no FK constraint currently
                                     enforced at that layer — an existing, pre-H3 looseness this
                                     document does not need to correct to proceed, but which
                                     CanonicalStandard's OWN anchor column, below, does NOT repeat).
```

**Frozen resolution path (the evaluator's exact, deterministic algorithm)**:

```
1. A Conformity QualityRule (like every QualityRule) carries information_element_requirement_id.
2. The Conformity evaluator resolves the ACTIVE CanonicalStandard row whose own
   information_element_requirement_id matches the rule's — a single indexed equality lookup.
3. If no ACTIVE CanonicalStandard exists for that Information Element: NO_STANDARD (§14).
4. If one exists: canonicalize the observed representation against it.
```

**Two SourceFields governed by the same Information Element (SAP `COUNTRY_OF_ORIGIN`, PLM
`MANUFACTURING_COUNTRY`) resolve the identical `CanonicalStandard`** because each field's own governing
`QualityRule` independently carries the same `information_element_requirement_id` — achieving PO-H3-01's
exact goal (one standard, shared across sources) with **zero new resolution mechanism invented**, reusing
structure that already exists and is already load-bearing elsewhere in the OQI family.

**Binding column decision**: `CanonicalStandard.information_element_requirement_id` is declared as a real
`Uuid()` column with a genuine `ForeignKey("information_element_requirements.information_element_
requirement_id")` constraint — stricter than `QualityRule`'s own current unconstrained-`String(200)`
looseness, not merely matching it. This document does not authorize adding an FK to `QualityRule` itself
(out of scope, unrelated to Conformity's own correctness).

**No STOP condition is triggered.** The Information Element anchor is fully implementable against
existing, real, governed repository structure.

## 9. `CanonicalStandard` ownership (frozen)

**Shared platform only.** No `tenant_id` column on `oqi_canonical_standards`,
`oqi_canonical_standard_values`, or `oqi_canonical_standard_aliases` — identical classification to
`information_element_requirements` itself and to `QualityRule` (CDD-046 erratum). Tenant-scoped
*evidence* (`FieldValueEvidence`, `QualityEvaluation`, `QualityFinding`) freely consults the shared
standard read-only; no tenant may create, version, or retire a `CanonicalStandard` row without the
authority named in §25. Configuration authority is governed separately from evidence tenancy — a
tenant's evaluation reading a shared standard is not itself a tenant-ownership question, exactly as a
tenant's Accuracy evaluation reading a shared `GOVERNED_REFERENCE_DATASET` entry is not (CDD-048 §29/§30
precedent).

## 10. `CanonicalStandard` versioning (frozen)

```
canonical_standard_id     UUID, single-column primary key
information_element_requirement_id   UUID, FK (§8)
version_number             int, explicit, incrementing per logical standard
previous_version_id        UUID | None, self-referencing FK, immutable version chain
status                      ACTIVE | RETIRED  (closed, exactly two)
created_by                  str
created_on                  datetime
retired_on                  datetime | None
```

Direct structural precedent: `ImpactPropagationPolicyORM` / H1's `oqi_quality_coverage_policies` (CDD-047
§10's own reasoning — *"a policy whose entire purpose is preventing a false positive must not rely on
application discipline alone for its own single most important invariant"* — applies identically here: a
standard whose entire purpose is correct canonicalization must not rely on application discipline for
its own uniqueness). **Database-enforced**: `UNIQUE ACTIVE (information_element_requirement_id)` as a
PostgreSQL partial unique index, `WHERE status = 'ACTIVE'` — at most one ACTIVE standard per Information
Element, enforced at the database level, never merely by application code. Historical versions are
immutable once superseded — a new mapping is always a new version, never an in-place row mutation.

**Historical pinning (binding)**: every Conformity evaluation and every canonically-projected Consistency
participant must persist the exact `canonical_standard_id` + `version_number` consulted (§16/§17). A
standard's later re-versioning never retroactively alters what a past evaluation recorded as its basis —
mirrored exactly on Accuracy's `oqi_quality_evaluation_reference_evidence` version-pinning precedent
(CDD-048 §15).

## 11. Canonical value + alias model (frozen, normalized)

**Rejected**: JSONB, PostgreSQL `ARRAY`, or any opaque blob for the canonical dictionary — identical
reasoning to CDD-047 §9's own explicit rejection for `QualityCoveragePolicy.required_dimensions`: a
normalized child table supports a real database-level uniqueness constraint neither JSONB nor `ARRAY`
can express as strongly, and matches every other closed-vocabulary, per-item-constrainable pattern this
repository already establishes.

```
CanonicalStandard (§10)
      │  1
      │
      │  N
CanonicalValue
    canonical_value_id       UUID, primary key
    canonical_standard_id     UUID, FK -> oqi_canonical_standards
    canonical_representation   str (the governed target string, e.g. "USA")
    UNIQUE (canonical_standard_id, canonical_representation)
      │  1
      │
      │  N
CanonicalAlias
    canonical_alias_id        UUID, primary key
    canonical_value_id         UUID, FK -> CanonicalValue
    alias_representation       str (a recognized non-canonical representation, e.g. "US")
    UNIQUE (canonical_standard_id [denormalized for the constraint], alias_representation)
        WHERE status = 'ACTIVE'   -- see §12
```

**Comparison discipline (frozen, binding)**: exact match, leading/trailing whitespace trimmed only —
**no case-folding, no punctuation stripping, no fuzzy matching of any kind**. This is the narrowest
possible generalization of `evaluate_consistency`'s own existing, unmodified discipline
(`app/domain/oqi_cross_source/evaluation.py:325`, confirmed: `{value.strip() for value in
participant_values.values()}` — whitespace-trim, case-preserving). A canonical value's own
`canonical_representation` is implicitly resolvable as its own trivial alias (i.e., an observation
matching the canonical string exactly, after trimming, is `CANONICAL`, requiring no separate row in
`CanonicalAlias`).

**Deterministic resolution (binding)**: `UNIQUE(canonical_standard_id, alias_representation) WHERE
ACTIVE` in `CanonicalAlias`, combined with `UNIQUE(canonical_standard_id, canonical_representation)` in
`CanonicalValue` and the one-ACTIVE-standard-per-anchor constraint (§10), jointly make it **structurally
impossible** for one observed representation to resolve to two canonical values under the same
applicable active standard. Ambiguity is prevented by construction, not merely checked at read time.

## 12. Alias ambiguity (frozen, binding)

**No `CanonicalStandardConflict` object is authorized.** Reference Evidence's own conflict object
(`OqiReferenceEvidenceConflict`, CDD-048 §16) exists because independently-authorized, differently-timed
assertions from different actors/forms can *legitimately* disagree — an inherent multi-writer race this
document's own precedent correctly modeled with a conflict object. A canonical alias table under one
governance authority does not share this shape: an ambiguous alias mapping is a **configuration defect**,
never a legitimate governance disagreement between two independently-authorized claims. Ambiguity is
therefore prevented structurally (§11's constraints), not detected-and-recorded after the fact.

**Defensive runtime behavior (binding, in case corrupt/legacy state nevertheless produces ambiguity —
e.g. a future schema migration bug, never expected under §11's constraints)**: the resolver **fails
closed** — `AMBIGUOUS`, treated identically to `NOT_MAPPED` for every downstream purpose (§14, §21) — it
never guesses, never picks the first match, never picks by creation order.

## 13. Canonicalization resolver contract (frozen)

```
CanonicalizationResult:
    observed_representation      str        (verbatim, as read from FieldValueEvidence)
    resolution_state              {CANONICAL, ALIAS_RESOLVED, NOT_MAPPED, AMBIGUOUS, NO_STANDARD}
    resolved_canonical_value      str | None  (the governed target string; None iff NOT_MAPPED,
                                                AMBIGUOUS, or NO_STANDARD)
    canonical_standard_id         UUID | None (None iff NO_STANDARD)
    standard_version               int | None  (None iff NO_STANDARD)
```

Deterministic, pure, side-effect-free — no probabilistic resolution, no fuzzy matching, **no import from
`app.domain.identity_resolution.normalization` or any ER-internal module of any kind** (§L). Sufficient
provenance is carried by construction to reconstruct: what was observed, what it resolved to (if
anything), whether the observed representation was itself already canonical, and exactly which governed
standard/version produced the answer.

## 14. Conformity evaluation semantics (frozen)

```
CANONICAL          -> SATISFIED,   persisted quality_evaluations row, no Finding
ALIAS_RESOLVED      -> VIOLATED,    persisted quality_evaluations row, NON_CANONICAL_REPRESENTATION Finding
NOT_MAPPED           -> NOT_EVALUABLE, zero persisted evaluation row, no Finding
AMBIGUOUS             -> NOT_EVALUABLE, zero persisted evaluation row, no Finding
NO_STANDARD            -> NOT_EVALUABLE, zero persisted evaluation row, no Finding
```

Mirrors OQI3's `NOT_EVALUABLE` zero-row precedent exactly (CDD-041 §13), already reused verbatim by
Accuracy (CDD-048 §6). Missing raw value: **remains Completeness's domain exclusively** —
`MISSING_VALUE` is unaffected by, and unrelated to, this document; Conformity never fabricates a Finding
for an absent observation, and Completeness's own evaluation is untouched by this document in every
respect.

Storage family: `OQI1` (`quality_evaluations` / `quality_findings`, unmodified tables, matching Accuracy's
own reuse exactly — Conformity is OQI1-shaped per CDD-046 §9). `QualityFindingOrigin.finding_storage_
family = OQI1`, `.quality_dimension = "CONFORMITY"` — resolved via one new entry in `origin.py`'s static
`_OQI1_FINDING_TYPE_TO_DIMENSION` mapping: `NON_CANONICAL_REPRESENTATION -> CONFORMITY`, mirroring
exactly the one entry H2 added (`REFERENCE_VALUE_UNSUPPORTED -> ACCURACY`). **No further Finding-origin
change is required or authorized** — `_VALID_QUALITY_DIMENSION_VALUES`'s existing construction
(`{QualityDimension members} | {BusinessRulePurpose members}`) automatically widens the moment
`CONFORMITY` is added to `QualityDimension`, with zero additional code change to `origin.py` beyond that
one dictionary entry.

## 15. Persisted Conformity evidence link (frozen)

```
oqi_quality_evaluation_canonical_standard   (mirrors oqi_quality_evaluation_reference_evidence exactly,
                                              CDD-048 §7)
    evaluation_id            UUID, PK, FK -> quality_evaluations.evaluation_id
    canonical_value_id        UUID, PK, FK -> oqi_canonical_standard_values.canonical_value_id
    standard_version           int, NOT NULL   (denormalized pin — the exact version consulted, since
                                                 canonical_value_id alone does not carry version if a
                                                 value's alias set changes across versions)
```

One row per Conformity evaluation (Conformity compares against exactly one qualifying canonical value,
mirroring Accuracy's "exactly one qualifying value" discipline, CDD-048 §8).

## 16. G0 — Consistency fail-closed resolution (frozen, binding — supersedes the H3-DR recommendation)

**`GOVERNED CANONICALIZATION FAILURE ≠ SEMANTIC DISAGREEMENT`** — a canonicalization failure is a
statement about Noetva's own inability to interpret a representation under a governed standard, never
evidence that the underlying sources disagree. Adopted as a new crown invariant, restated as
`CANONICALIZATION FAILURE ≠ VALUE CONFLICT` (§32).

### 16.1 Exact algorithm (frozen)

```
FOR the Information Element governing this comparison (via each participant's own governing
QualityRule.information_element_requirement_id, which must be identical across all participants of one
comparison — an existing CDD-040 requirement, unaffected by this document):

CASE A — no ACTIVE CanonicalStandard exists for that Information Element:
    Existing raw Consistency comparison, byte-for-byte unchanged (evaluate_consistency, unmodified).
    This is the exact legacy behavior for every subject with no applicable standard — full backward
    compatibility, identical to pre-H3.

CASE B — an ACTIVE CanonicalStandard exists:
    For every KNOWN participant value that would otherwise enter the value-agreement computation
    (i.e., every role with a non-missing, resolved value under CDD-040's existing participant-selection
    algorithm — Amendment §13 step 1's missingness determination is entirely unaffected, computed
    first, exactly as today):

        canonicalize each known value under the one applicable ACTIVE standard/version.

        IF every required known participant resolves to CANONICAL or ALIAS_RESOLVED:
            compare the resolved canonical representations (exact match) instead of the raw values.
            -> SATISFIED if all canonical projections agree, VIOLATED (CROSS_SOURCE_VALUE_CONFLICT)
               otherwise -- an ordinary, real, governed comparison outcome.

        IF any required known participant resolves to NOT_MAPPED or AMBIGUOUS:
            the VALUE-AGREEMENT sub-computation for this attempt is NOT_EVALUABLE:
                no CROSS_SOURCE_VALUE_CONFLICT observation is added;
                no fabricated conflict Finding is opened or reopened from this cause.
```

### 16.2 Mixed participant state (frozen, binding — resolves the missingness interaction precisely)

The canonicalization gate applies **exclusively** to the value-agreement sub-computation (Amendment §13
step 2, the `known_values >= 2` branch). It does **not** suppress, alter, or interact with the
independent missingness-observation computation (Amendment §13 step 1), which remains entirely
unconditional and unchanged — a missing participant produces its `CROSS_SOURCE_PARTICIPANT_VALUE_
MISSING` observation regardless of whether canonicalization succeeds, fails, or was never applicable.

```
Consequence, exhaustive:

  missingness observations exist, value-agreement gate SUCCEEDS (or Case A applies)
      -> evaluation row inserted, both observation types as applicable, existing behavior generalized.

  missingness observations exist, value-agreement gate FAILS (canonicalization failure)
      -> evaluation row IS still inserted, carrying the missingness observation(s) only -- the
         value-agreement sub-computation contributes NOTHING (no conflict observation added), but the
         attempt is not wholly discarded merely because canonicalization also failed for the known
         participants. This is the one case where a G0-shaped canonicalization failure and a genuine,
         unrelated Finding (missingness) coexist in the same evaluation row -- correctly, since they are
         answering two independent questions.

  NO missingness observations, value-agreement gate FAILS, and no successful comparison was possible
      -> the ENTIRE attempt is NOT_EVALUABLE: zero new QualityComparisonEvaluation row is inserted for
         this attempt -- mirroring the existing "fewer than 2 known-and-valued participants, no
         deterministically-provable missingness" None-return path exactly, generalized to include
         "canonicalization failure with nothing else to report."

  NO missingness observations, value-agreement gate SUCCEEDS (or Case A applies), fewer than 2 known
  values
      -> unchanged from today: no evaluation, no Finding touched (existing None-return path, untouched).
```

### 16.3 Idempotency (frozen)

A `NOT_EVALUABLE`-for-value-agreement attempt that inserts no row is trivially idempotent — nothing is
written, so repeated identical attempts under identical inputs remain no-ops. Where an evaluation row
*is* inserted (missingness present, or a genuine canonical/raw comparison succeeded), the existing
deterministic-identity + idempotent-ledger-insert discipline (CDD-040 §43, unmodified) applies exactly
as today — no new idempotency mechanism is introduced.

### 16.4 Coverage (frozen)

`has_qualifying_coverage_for_dimension(CONSISTENCY)` remains: *any qualifying persisted
`QualityComparisonEvaluation` row establishes coverage* (CDD-047 §14, unmodified). A `NOT_EVALUABLE`
attempt that inserts zero row does **not** establish coverage — if every attempt for a subject happens to
hit the canonicalization-failure path with no missingness to record, `CONSISTENCY` coverage remains
unsatisfied for that subject absent some other qualifying historical row. This is the correct,
fail-closed generalization, consistent with `PARTIAL REQUIRED COVERAGE ≠ SUPPORTED` (CDD-047 §20).

### 16.5 Historical Finding lifecycle (frozen, binding — the single most important resolution in this
section)

**Introduction, retirement, or re-versioning of a `CanonicalStandard`, or a G0-shaped `NOT_EVALUABLE`
outcome, NEVER by itself closes, reopens, or otherwise mutates a pre-existing open `CROSS_SOURCE_VALUE_
CONFLICT` Finding.** History is never rewritten: every historical `QualityComparisonEvaluation` row
(raw-comparison-produced, before this document existed) remains exactly as persisted, permanently
explainable under the comparison basis actually used at that time. Only a **fresh** `CURRENT_STATE`
evaluation that genuinely computes `SATISFIED` — whether via successful canonical-projection agreement
(Case B) or via raw comparison because no standard applies (Case A) — may transition an open Finding
closed, through the existing, entirely unmodified `apply_correspondence_finding_transition` mechanism
(CDD-040, unchanged). A `NOT_EVALUABLE` outcome inserts no row and therefore triggers no Finding
transition of any kind — an open Finding a canonicalization-failure attempt could not resolve remains
open, exactly matching `REMEDIATION ≠ RESOLUTION`'s existing discipline: only real, independent,
successful re-evaluation proves resolution, never a mere configuration change (a new `CanonicalStandard`
appearing) and never an inability-to-evaluate outcome.

## 17. Consistency canonical-projection provenance (frozen)

```
oqi_comparison_participant_canonical_projection
    evaluation_id            UUID, PK, FK -> quality_comparison_evaluations.evaluation_id
    participant_role          str(64), PK
    canonical_value_id         UUID, FK -> oqi_canonical_standard_values.canonical_value_id
    standard_version            int, NOT NULL
    raw_participant_value        -- NOT duplicated here; reconstructable via the existing
                                     quality_comparison_evaluation_evidence link
                                     (evaluation_id, participant_role) -> field_value_evidence_id,
                                     unmodified, which itself resolves to FieldValueEvidence.
                                     observed_representation -- immutable raw evidence is never
                                     duplicated into new H3 tables.
```

One row per participant that was **successfully** canonicalized and consulted in a Case-B comparison —
absent row for a participant means either Case A applied (no standard) or that specific participant was
missing/not part of the value-agreement computation. This answers, from governed reference data alone,
never generated prose: *"Why did Noetva consider `US` and `USA` equivalent?"* — join
`quality_comparison_evaluation_evidence` (raw value) → `oqi_comparison_participant_canonical_projection`
(standard + version + resolved canonical value) → `oqi_canonical_standard_aliases` (the exact alias row
matched, at that version).

## 18. Accuracy non-interference (frozen, binding, PO-H3-02)

`OqiAccuracyEvaluationService` is **not modified by this document in any way**. Its comparison remains
exactly raw `observed_representation` vs. the qualifying `ReferenceEvidenceAssertion.asserted_value`,
byte-for-byte, unchanged since CDD-048. **No import, call, or dependency from Accuracy's evaluation path
to any H3 `CanonicalStandard` artifact is authorized.**

**Explicit regression requirement (binding on H3-I/H3-VM)**: the existing H2 Accuracy crown scenario
(SAP `"US"`, PLM `"MX"`, governed Reference Evidence `"US"` → SAP `SATISFIED`, PLM `VIOLATED`) must be
re-proven, live, against a database state where an H3 `CanonicalStandard` genuinely exists for the same
`Country of Origin` Information Element (populated by the H3 crown scenario, §30) — proving by direct
observation, not mere absence-of-change, that Accuracy's outcome is identical whether or not a
`CanonicalStandard` happens to exist for the same governed concept it is evaluating. `CANONICAL ≠
ACCURATE` and `CONFORMING ≠ ACCURATE` must hold structurally: nothing in Accuracy's code path is capable
of reading a `CanonicalStandard` row, so this is enforceable by the same absence-of-import proof CDD-046
§17 already established for ER (§L).

A future, separately-governed CDD may revisit semantic-equivalence comparison for Accuracy; this
document explicitly does not anticipate, half-design, or reserve schema for it.

## 19. Validity independence (frozen)

`ValidityPrimitive.ENUM_MEMBERSHIP`'s `allowed_values` and a `CanonicalStandard`'s alias set are
**independent governed artifacts, deliberately not reconciled by any structural constraint.**
`canonical aliases ⊆ allowed_values` is **not** a hard H3 invariant — requiring it would create a
cross-artifact consistency obligation neither CDD-046 nor any prior CDD establishes, and would make
Conformity configuration fail depending on unrelated Validity rule state under a different authority. No
alias is silently added to any `ValidityPrimitive.allowed_values` list by this document or its
implementation. A configured alias absent from Validity's own domain is a legitimate, if noteworthy,
governance signal for a human steward to notice — not a validation error this document authorizes any
code to raise.

## 20. Finding + Finding-origin design (frozen — restated from §14/§6 for completeness)

```
NON_CANONICAL_REPRESENTATION    (QualityFindingType, new, sole H3 addition)
Storage family:                  OQI1 (unmodified FindingStorageFamily, no new member)
QualityFindingOrigin.quality_dimension:   "CONFORMITY"
```

No `FindingStorageFamily` change. No `RemediationCandidateBasis` structural redesign (one additive
member only, §24). No OQI4/OQI5/OQI6 taxonomy redesign of any kind — validated directly in §W of the
OQI-H3-DR report and reconfirmed here: `_VALID_QUALITY_DIMENSION_VALUES`'s existing union-of-two-enums
construction absorbs `CONFORMITY` with zero structural change beyond the one enum member and the one
`_OQI1_FINDING_TYPE_TO_DIMENSION` entry.

## 21. H1 coverage integration (frozen)

One new branch in `has_qualifying_coverage_for_dimension`, identical shape to `ACCURACY`'s existing
branch (CDD-048, R1-retroactive-authorized precedent):

```
CONFORMITY:
    JOIN quality_evaluations -> quality_rules ON rule_id
    WHERE quality_rules.dimension = 'CONFORMITY'
      AND quality_evaluations.tenant_id = ?
      AND quality_evaluations.source_object_id IN (source_object_ids)
```

`NO_STANDARD` / `NOT_MAPPED` / `AMBIGUOUS` all produce zero persisted evaluation rows (§14) and are
therefore, structurally, **uncovered** — never a computed negative, a structural fact identical to
CDD-047 §14's own "no table is queried, because none exists" discipline generalized to "no *qualifying*
row exists, because canonicalization could not resolve." `PARTIAL REQUIRED COVERAGE ≠ SUPPORTED` and `NO
FINDINGS ≠ TRUSTED` both hold unchanged — Conformity participates through the existing, entirely
unmodified `compute_generalized_coverage` loop (CDD-047 §13).

## 22. Reliance integration (frozen)

No new `RelianceState` member. No trust score. `derive_reliance_state`'s three-input shape (`any_open_
finding`, coverage, `any_active_impact_unknown`) is unmodified and dimension-agnostic by construction —
an open `NON_CANONICAL_REPRESENTATION` Finding participates through the existing, generic `any_open_
finding` input identically to every other dimension's Finding. A subject with `CONFORMITY` named in an
`ACTIVE` `QualityCoveragePolicy` but never evaluated correctly produces `RELIANCE_UNKNOWN` via the
existing, unmodified coverage-gap mechanism (CDD-047 §12.2) — no new code path is required beyond §21's
one branch.

## 23. Ontology + business impact integration (frozen)

**`NON-CONFORMITY ≠ ONTOLOGY IMPACT`** — adopted as a new crown invariant (§32). A `NON_CANONICAL_
REPRESENTATION` Finding enters OQI4's existing, unmodified, dimension-blind propagation mechanism exactly
as every other dimension's Finding does (CDD-046 §33, re-verified unchanged post-H2). No automatic
`IMPACTED` conclusion is authorized or introduced — impact remains a function of whether a real ontology
relationship traversal from the Finding's subject reaches something, computed identically regardless of
which dimension produced the Finding. Business impact remains entirely `BusinessDependency`-driven and
contextual (CDD-044 §12, unchanged) — no universal Conformity criticality is introduced; a non-canonical
representation with zero declared `BusinessDependency` carries identical `BUSINESS_IMPACT_UNKNOWN`
treatment to any other dimension's Finding in the same position.

## 24. Remediation design (frozen)

`RemediationCandidateBasis` gains exactly one new member: `CONFORMITY_CANONICAL_STANDARD`, mirroring
`ACCURACY_REFERENCE_EVIDENCE`'s own addition pattern (CDD-048 §24) — **no dispatch logic anywhere in the
codebase branches on `basis`** (verified, CDD-048's own docstring, re-confirmed unchanged), so this
extension carries zero risk to existing behavior.

A new `extract_conformity_candidates` function, mirroring `extract_accuracy_candidates`'s exact shape
(CDD-048 §24):

```
extract_conformity_candidates(
    case_id, target_source_object_id, target_source_field_id, observed_evidence_id,
    canonical_value: str,              -- the exact governed replacement, never re-derived here
    canonical_standard_id: UUID, standard_version: int,     -- provenance, not authority
    now,
) -> tuple[RemediationCandidate, ...]
```

Produces a candidate **only** for `ALIAS_RESOLVED` (VIOLATED, evidence-backed exact replacement exists)
— never for `NOT_MAPPED`/`AMBIGUOUS`/`NO_STANDARD` (no defensible replacement exists; `NOT_EVALUABLE`
never produces a remediation candidate, mirroring every other dimension's identical discipline). **No new
`RemediationActionType` is authorized or required** — `UPDATE_FIELD` (closed to exactly one member since
CDD-043) fully expresses "replace the observed representation with its governed canonical form."

**Preserved, unmodified**: `CANONICAL ≠ ACCURATE` (the candidate never claims the canonical value is also
correct — a candidate purely a defensible representation *format* correction, never a truth claim);
`CANDIDATE ≠ TRUTH`; `RECOMMENDATION ≠ AUTHORIZATION`; `AUTHORIZATION ≠ REMEDIATION`; `REMEDIATION ≠
RESOLUTION` — resolution requires fresh `FieldValueEvidence` and a genuine, independent Conformity
re-evaluation producing `SATISFIED`, exactly as every other dimension's resolution contract (CDD-046
§36) requires, never a human's or agent's say-so.

## 25. Authorization (frozen)

```
oqi-canonical-standard:configure
```

New, distinct scope, confirmed against the existing naming convention (`<resource-family>:<verb>`,
verified directly against `keycloak/ctec-realm.json`'s current `oqi-remediation:authorize`/`:report-
execution`, `oqi-reference-evidence:configure`/`:verify`). Required for create/version/retire of any
`CanonicalStandard`/`CanonicalValue`/`CanonicalAlias` row. Never satisfied by, and never satisfies,
`oqi:read`, `oqi-reference-evidence:configure`, `oqi-reference-evidence:verify`,
`oqi-remediation:authorize`, `oqi-remediation:report-execution`, or `oqi-coverage:configure` (which
itself remains unwired in the realm — §29). `CONFIGURATION AUTHORITY ≠ REMEDIATION AUTHORITY` is
preserved structurally, identical to every prior OQI-family scope-separation precedent.

**H3 authorizes no public configuration API** (§26). The scope's enforcement is service-level only — a
future application-boundary write path (whenever one is authorized) must gate on this scope exactly as
`oqi-reference-evidence:configure` gates its own routes; until such a route exists, the scope's
declaration in the realm (if the paired Artifact Authorization determines it is required for internal
readiness) documents the authority without implying a route, mirroring CDD-047 §22's own precedent
exactly.

## 26. API + frontend boundary (frozen)

**No CanonicalStandard CRUD API of any kind is authorized by this document.** Confirmed directly:
`FindingDetailResponse`'s existing `dimension: str` field (CDD-048 §29, already additive/unconstrained)
requires **zero schema change** to carry `"CONFORMITY"` — no enumerated closed set exists anywhere in
`api/oqi/schemas.py` constraining accepted dimension values. Confirmed directly against
`frontend/lib/oqi/contracts.ts`: `finding_family` is typed as a plain, unconstrained `string` — a
Conformity Finding (storage family `OQI1`) renders through existing Finding-detail code with **zero
required frontend change**. One pre-existing, non-blocking, **explicitly deferred** cosmetic item:
`frontend/app/quality/findings/page.tsx:120-122`'s hardcoded family-filter dropdown labels `OQI1` as
`"Completeness / Validity"` — functionally correct (Conformity Findings still appear under that filter
option), label text merely incomplete. This document does not authorize touching this file (§38).

## 27. Exact persistence schema (frozen, exact table count)

**Five (5) new tables, no more, no fewer:**

```
1. oqi_canonical_standards                       (§10)   — SHARED PLATFORM
2. oqi_canonical_standard_values                 (§11)   — SHARED PLATFORM
3. oqi_canonical_standard_aliases                (§11)   — SHARED PLATFORM
4. oqi_quality_evaluation_canonical_standard      (§15)   — provenance link, tenant-scoped via the
                                                             evaluation it links (no own tenant_id column
                                                             needed, mirrors oqi_quality_evaluation_
                                                             reference_evidence exactly)
5. oqi_comparison_participant_canonical_projection (§17)  — provenance link, tenant-scoped via the
                                                             comparison evaluation it links
```

`quality_evaluations`, `quality_findings`, `quality_rules` (Conformity reuses all three directly, OQI1-
storage-shaped, no schema change to any of them beyond the two enum-vocabulary extensions in §4/§6,
which are `StrEnum`-backed `VARCHAR` columns, not native PostgreSQL enum types — confirmed by the exact
precedent of every prior `QualityDimension`/`QualityFindingType` extension, none of which required a
column-type migration). `quality_comparison_evaluations` and its existing child tables are similarly
reused unmodified.

**Every new table's ownership/PK/FK/uniqueness/lifecycle/deletion is fully specified above (§10, §11,
§15, §17). No DELETE of any existing table or column is authorized by this document.**

## 28. Migration plan (frozen, exact)

```
Current head:              0030_oqi_h2_reasonableness   (confirmed, re-verified this phase)
Current table count:        109                           (confirmed via the exact governed query —
                                                            BASE TABLE only, excluding alembic_version)

New migrations (revision IDs, each <=32 chars):
    0031_oqi_h3_canonical_standard        (24 chars) — creates tables 1-3 (§27), plus the
                                            _ALLOWED_COMBINATIONS-adjacent enum-value extension is a
                                            pure Python/domain-layer change requiring no migration of
                                            its own (VARCHAR columns, no CHECK constraint on dimension
                                            values exists today — confirmed: quality_rules.dimension is
                                            String(16), unconstrained by any DB-level enum type).
    0032_oqi_h3_conformity_evidence        (26 chars) — creates table 4 (§15).
    0033_oqi_h3_consistency_projection      (27 chars) — creates table 5 (§17).

H3-created table count:      N = 5
Expected final table count:   109 + 5 = 114
```

**Required round-trip (binding on H3-I/H3-VM, mirroring CDD-048's own exact discipline)**:

```
109 -> 114 -> 109 -> 114
```

using real PostgreSQL, each migration's own upgrade/downgrade/re-upgrade proven independently, then the
full three-migration chain proven together, single Alembic head required at all times. No migration
beyond the three named here is authorized. If implementation discovery proves a different table count is
genuinely required (e.g., a constraint needs its own index-only table, which is not currently
anticipated), this is a STOP condition (§37) — a disclosed governance return, not a silent adjustment.

## 29. CI companion decision (frozen, explicit — resolves the task's own instruction not to repeat H1/H2's
discovery-after-implementation pattern)

Read-only inspection of `.github/workflows/ci.yml` performed this phase confirms:

```
Line 139-146   migration-head check: already DYNAMIC (compares against `alembic heads` output at
               runtime) — requires NO H3 change.
Line 148-153   table-count check: hardcoded `[ "$count" -eq 109 ]` — REQUIRES an H3 change, to 114
               (§28), exactly mirroring the CDD-048-OQI-H2-I-R1 precedent.
Line 170-173, 198, 233   authorization-proof scope checks: currently verify ONLY
               oqi-remediation:authorize/:report-execution as default/optional scopes and in the PKCE
               scope string — CONFIRMED this block has NEVER been extended to check
               oqi-reference-evidence:configure/:verify either, a pre-existing H2-era gap.
```

**Decision (binding): Option A.** H3-I is authorized to add exactly one new line to this same CI block
proving `oqi-canonical-standard:configure` is present, correctly classified `optional` (never `default`),
in the realm — following the identical pattern already used for `oqi-remediation:*`. **H3 is explicitly
NOT authorized to retroactively add `oqi-reference-evidence:*` scope proof to this CI block** — that is
pre-existing, unrelated H2-era authorization-hardening debt, and repairing it here would silently broaden
H3's scope into a different governed capability's own gap, which this document's own DR phase (§AO)
explicitly warned against absorbing. If that gap is ever closed, it must be its own narrow, disclosed
companion amendment against CDD-048, not folded into H3.

The exact H3-authorized CI change: `.github/workflows/ci.yml` line 153, `109` → `114` (and its message
text), plus one new scope-check line for `oqi-canonical-standard:configure`, mirroring lines 170-173's
existing shape exactly.

## 30. Deterministic H3 crown scenario (frozen)

```
Information Element:  Manufacturing Country (the same Information Element the H2 seeder's
                       Country of Origin fields already resolve to via existing semantic_mappings)
CanonicalStandard:     canonical "USA", alias "US" -> "USA"
SAP:                   "US"    (the EXISTING SAP field the H2 crown already seeds)
PLM:                   "USA"   (a NEW value on a NEW field/subject, distinct from H2's own PLM="MX"
                                 crown value -- see §31)

Expected, real, derived (never terminal-inserted):
    Conformity SAP:      VIOLATED  (NON_CANONICAL_REPRESENTATION)
    Conformity PLM:      SATISFIED
    Consistency:          canonical(SAP)=USA, canonical(PLM)=USA -> SATISFIED, no
                          CROSS_SOURCE_VALUE_CONFLICT (where raw comparison, absent H3, would have
                          disagreed -- "US" != "USA")
    Remediation candidate: SAP "US" -> "USA" (UPDATE_FIELD, CONFORMITY_CANONICAL_STANDARD basis)
```

This scenario must derive entirely from raw seeded evidence through the real evaluator services, exactly
matching CDD-046 §45's binding "never a pre-scripted terminal state" requirement, identical to H2's own
seeder discipline.

## 31. H2 non-regression crown (frozen, binding)

```
SAP:        "US"
PLM:        "MX"
Reference:   "US"   (GOVERNED_REFERENCE_DATASET, unchanged from H2)

Required, unchanged:
    Accuracy SAP:    SATISFIED
    Accuracy PLM:     VIOLATED
    Reasonableness:    unchanged H2 outcome (VIOLATED, per the existing H2 crown scenario)
```

**H3-I/H3-VM must prove this exact H2 scenario is byte-for-byte unaffected** by the mere existence of an
H3 `CanonicalStandard` for the same `Manufacturing Country` Information Element (§18's explicit
regression requirement) — run live, in the same database state where §30's `CanonicalStandard` also
exists, not merely asserted by absence of code change.

## 32. Frozen crown invariants (complete set)

**New, adopted by this document:**

```
VALID ≠ CONFORMING
CONFORMING ≠ ACCURATE
CANONICAL ≠ ACCURATE                          (reaffirmed, originally CDD-046 §41)
CANONICAL EQUIVALENCE ≠ RAW EQUALITY
NORMALIZED FOR MATCHING ≠ GOVERNED CANONICAL
CANONICALIZATION ≠ SOURCE MUTATION
NON-CONFORMITY ≠ ONTOLOGY IMPACT
CANONICALIZATION FAILURE ≠ VALUE CONFLICT
```

Each is architecturally enforceable and independently testable against a specific mechanism named above
(§5/§11/§13/§16/§18/§23/§27's structural guarantees) — none is adopted as an unenforceable slogan.

**Preserved, unmodified, reaffirmed:**

```
MAJORITY ≠ TRUTH                    AUTHORIZATION ≠ REMEDIATION      VALID ≠ ACCURATE
AUTHORITY ≠ TRUTH                   REMEDIATION ≠ RESOLUTION         CONSISTENT ≠ ACCURATE
CANDIDATE ≠ TRUTH                   AUTHORIZATION_ID ≠ AUTHORITY     DUPLICATE CANDIDATE ≠ DUPLICATE FACT
AGENT ≠ FACT                        UNKNOWN ≠ LOW                    ANOMALY ≠ QUALITY DEFECT
RECOMMENDATION ≠ AUTHORIZATION      NO FINDINGS ≠ TRUSTED             QUALITY CONCLUSION ≠ REFERENCE EVIDENCE
PARTIAL REQUIRED COVERAGE ≠ SUPPORTED
```

None of the twenty pre-existing invariants is touched, weakened, or reinterpreted by this document.

## 33. Frozen H3 test matrix

Binding on H3-I's test suite, exhaustive, mirroring the exact category structure CDD-048 §31 already
established:

```
CONFORMITY:      C1 canonical->SATISFIED; C2 alias->VIOLATED; C3 unmapped->NOT_EVALUABLE/zero row;
                 C4 no standard->NOT_EVALUABLE/zero row; C5 inactive standard; C6 version supersession;
                 C7 missing value stays Completeness; C8 idempotency; C9 immutable raw evidence;
                 C10 exact standard/version provenance
CONSISTENCY:      K1 raw different/canonical same; K2 canonical different; K3 no standard->legacy raw;
                 K4 applicable standard + unmapped participant->NOT_EVALUABLE; K5 applicable standard +
                 ambiguous participant->NOT_EVALUABLE; K6 no fabricated conflict from canonicalization
                 failure; K7 missing-participant behavior preserved (incl. mixed state, §16.2); K8
                 version provenance; K9 historical raw conflict not rewritten; K10 fresh evaluation after
                 standard introduction closes only via a genuine SATISFIED re-evaluation
VALIDITY:         V1 valid+conforming; V2 valid+nonconforming; V3 Validity unaffected by aliases
ACCURACY:         A1 H2 Accuracy unchanged by CanonicalStandard existence (live, §18); A2
                 conforming≠accurate; A3 nonconforming does not imply inaccurate
ORIGIN/DOWNSTREAM: F1 origin=CONFORMITY; F2 storage family=OQI1; F3 ontology impact generic; F4 business
                 impact generic; F5 Reliance generic
COVERAGE:         CV1 persisted satisfied Conformity counts; CV2 persisted violated Conformity counts;
                 CV3 no standard does not count; CV4 unmapped does not count; CV5 partial required
                 coverage≠supported
REMEDIATION:      R1 alias violation produces exact canonical UPDATE_FIELD candidate; R2 no candidate
                 for NOT_EVALUABLE; R3 candidate≠truth; R4 remediation≠resolution
TENANCY/AUTHORITY: T1 shared standard readable for tenant evaluation; T2 unauthorized configuration
                 rejected; T3 canonical configuration authority≠remediation authority
ER BOUNDARY:      E1 no ER normalization import/dependency (static, AST-verified, mirrors CDD-048's own
                 CY3-CY5 import-firewall precedent); E2 ER normalization cannot satisfy Conformity
                 (adversarial: attempting to wire an ER function as the resolver fails/is structurally
                 absent)
MIGRATION:        M1 upgrade; M2 table count (114); M3 downgrade; M4 re-upgrade; M5 active-standard
                 uniqueness (adversarial, real PostgreSQL); M6 alias uniqueness (adversarial, real
                 PostgreSQL)
DOCKER:           D1 real CanonicalStandard; D2 real SAP US; D3 real PLM USA; D4 SAP Conformity
                 violated; D5 PLM Conformity satisfied; D6 Consistency satisfied through canonical
                 projection; D7 no raw evidence mutation (adversarial: attempt and fail to update
                 FieldValueEvidence); D8 remediation candidate derived; D9 H2 Accuracy crown unchanged
                 (§31, live); D10 downstream chain (Ontology/Business Impact/Reliance) works
```

Every case must be proven by real behavioral evidence against real PostgreSQL where persistence is
involved — never code-inspection-only, mirroring CDD-048's own binding quality bar exactly.

## 34. Explicit deferrals (frozen — out of H3 scope, not silently absorbed)

```
Tenant CanonicalStandard override                    (PO-H3-03, CDD-046 §43 DD-02, still open)
Semantic/unit conversion                               (§7)
Fuzzy canonicalization                                  (§11, §13)
Probabilistic/LLM canonicalization                      (§13)
Accuracy canonical projection                           (PO-H3-02, §18)
Production evaluator orchestration/scheduling            (CDD-046 §42, unchanged, pre-existing P1
                                                        platform debt)
Command Center frontend redesign                         (§26, CDD-046 Boundary 8)
Broad CanonicalStandard CRUD UX                          (§26)
Frontend Docker healthcheck binding defect                (pre-existing, H2-VM-disclosed, unrelated)
Generic FK -> HTTP 500 pattern                            (pre-existing, H2-VM-disclosed, unrelated)
docs/product local allowlist condition                    (pre-existing, unrelated, untouched)
oqi-quality-rule:configure / oqi-coverage:configure wiring  (pre-existing, unwired since H1/H2,
                                                        unrelated to H3's own correctness)
```

None of the above is a correctness prerequisite for H3 as frozen in this document. If a future
implementation phase discovers otherwise, that is a STOP condition (§37), not a silent scope expansion.

## 35. STOP conditions for H3-I (binding, for the future implementation phase against this document)

H3-I must STOP rather than improvise if:

1. Information Element anchoring cannot be implemented exactly as frozen in §8;
2. the evaluator would need a `SourceField`-level fallback anchor;
3. canonicalization would require mutating `FieldValueEvidence` in any way;
4. ER normalization (`identity_resolution/normalization.py` or any ER-internal module) must become
   governed truth for Conformity to function;
5. alias ambiguity cannot be prevented/fail-closed exactly as §11/§12 require;
6. a historical `CanonicalStandard` version cannot be pinned/reconstructed per §10/§15/§17;
7. canonical Consistency provenance cannot be reconstructed per §17;
8. `OqiAccuracyEvaluationService` would need to change in any way to make H3 correct;
9. Conformity requires any Finding-origin redesign beyond §14/§20's one enum member + one dictionary
   entry;
10. H1 coverage cannot distinguish `NOT_EVALUABLE` from genuine coverage per §21;
11. remediation would require claiming `canonical = accurate` in any code path;
12. Docker runtime exposes a material ungoverned requirement not named in this document.

Any STOP must be disclosed in full, never silently worked around.

## 36. Acceptance criteria (binding)

An H3-I implementation is acceptable only if: it implements exactly §4-§33 without inventing additional
semantics; it does not modify `OqiAccuracyEvaluationService`'s comparison logic in any way (§18); it does
not modify `FieldValueEvidence` in any way; it does not import from `identity_resolution/normalization.py`
anywhere in the Conformity/Consistency-projection code path; it does not introduce a sixth
`CanonicalizationResult` state beyond §13's five; it enforces §10's and §11's uniqueness constraints at
the database level, verified against real PostgreSQL; it satisfies §16's exact G0 algorithm including
§16.2's mixed-participant-state resolution and §16.5's historical-Finding-lifecycle resolution as real,
executable tests; it proves §31's H2 non-regression crown live; and it satisfies the paired Artifact
Authorization's Docker/runtime verification requirements in full, including §33's complete test matrix.

## 37. Authorization

This CDD is approved for publication following OQI-H0 (CDD-046), OQI-H1 (CDD-047), OQI-H2 (CDD-048), and
OQI-H3-DR's repository-grounded discovery, resolved by explicit Product Owner decisions PO-H3-01 through
PO-H3-03. CDD-039 through CDD-048 (plus all amendments/erratum) remain FROZEN and PUBLISHED, unmodified
by this document. Implementation is authorized only via the paired Artifact Authorization companion,
enumerating the exact, closed H3-I file surface.
