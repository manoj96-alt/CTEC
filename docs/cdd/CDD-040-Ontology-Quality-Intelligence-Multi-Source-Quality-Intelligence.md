# CDD-040 — Ontology Quality Intelligence: Multi-Source Quality Intelligence (OQI2)

**Status:** FROZEN
**Version:** 1.0
**Depends on:** CDD-039 (OQI1, frozen, unmodified), CDD-019 (Source-to-Blueprint Semantic Mapping, frozen, unmodified), CDD-022 (Governed Source Field-Value Evidence, frozen, additively amended by a companion document — see §7), CDD-004 (Entity Resolution, frozen, unmodified), CDD-031 (Gate T, frozen, unmodified)
**Governed by:** Product Owner decisions across OQI2-D, OQI2-R, OQI2-G

---

## 1. Canonical terminology

The canonical capability name is **Ontology Quality Intelligence (OQI)**. This document governs its second deterministic foundation increment, **OQI2 — Multi-Source Quality Intelligence**. "Generalized DQ" is not and must never become the product-facing name (CDD-039 §2, unchanged).

## 2. Product north star (unchanged from CDD-039 §3)

> CTEC Ontology Quality Intelligence determines whether knowledge represented by the ontology can be trusted, identifies and explains the source-evidence quality conditions affecting that knowledge, and governs how those conditions are analyzed, remediated, re-evaluated, and resolved.

## 3. OQI2 proof statement

OQI2 implements only the deterministic foundation required to answer:

> When multiple governed source systems provide evidence about the same governed semantic attribute for the same governed comparison subject, does the evidence agree, conflict, or expose an explicitly governed expected-participant missingness condition?

No future developer may treat OQI2 as though it establishes truth, correctness, source authority as guaranteed accuracy, or record identity via inference. OQI2 does not calculate ontology trust, ontology impact, business impact, agent recommendations, or remediation (CDD-039 §3 principle, extended).

## 4. Scope (binding)

OQI2 governs, and only governs:

1. A `CONSISTENCY` extension of the existing `QualityDimension` (§14).
2. A new, explicit, non-inferring, governed record-correspondence primitive, `ComparisonSubjectCorrespondence` (§8–§13).
3. Cross-source deterministic comparison of `FieldValueEvidence` values across explicitly corresponding source-record lineages (§25).
4. Immutable cross-source `QualityComparisonEvaluation` ledger and current-state `QualityComparisonFinding` read-model, structurally sibling to (never modifying) OQI1's tables (§29, §39).
5. One narrow, additive, non-destructive composite-uniqueness amendment to the CDD-022-governed `field_value_evidence` table (§7, authorized by a separate companion document).

## 5. Non-goals (binding, exhaustive)

```
Fuzzy/probabilistic/AI record matching     Automatic source-authority inference
Majority-truth voting                       Generic unit-conversion engine
Reference-data mastering                    Record Completeness / Population Completeness
Generic business-rule engine (OQI3)         Ontology-impact propagation (OQI4)
Agent reasoning / remediation (OQI5)        Trust/confidence/criticality score (OQI6)
Frontend/dashboard (OQI7)                   API (any gate)
Modification of Gate T semantics            Modification of Entity Resolution matching
Modification of any OQI1 table shape        Case-folding / Unicode normalization / synonym mapping
```

A third `QualityDimension`, a new subject_type beyond `CROSS_SOURCE_COMPARISON`, a scalable (ER-owned) record-correspondence replacement, or any of the above each require their own future governance cycle.

## 6. Foundational separation (binding)

```
WHAT DOES THE ATTRIBUTE MEAN?          → Governed OQI comparison membership (§18, rule-owned)
WHICH SOURCE RECORDS CORRESPOND?       → ComparisonSubjectCorrespondence (§8)
WHAT VALUES WERE OBSERVED?             → FieldValueEvidence (CDD-022, read-only)
                                        → Cross-source QualityComparisonEvaluation (§27)
                                        → Cross-source QualityComparisonFinding (§28)
```

These four proofs must never be conflated. `semantic comparability ≠ record correspondence ≠ source authority ≠ truth`. `absence of knowledge ≠ knowledge of absence` (CDD-039 principle, reused unmodified).

## 7. SourceObject semantics (frozen fact, not reinterpreted)

`SourceObject` is a schema/object-type identity (e.g. SAP's `LFA1` table), never an individual physical record. Individual records are distinguished solely by `FieldValueEvidence.source_record_reference` (a free-text string) scoped under one `source_field_id`. This document does not alter CDD-019/CDD-022's model of `SourceObject`/`SourceField`/`FieldValueEvidence` in any way.

This document authorizes exactly one additive change touching a CDD-022-governed table: `UNIQUE(field_value_evidence_id, source_field_id)` on `field_value_evidence` (§37). Per this repository's established governance discipline (never modify a frozen artifact's authorized surface without its own explicit companion), this change is authorized by a **separate, narrow companion document**: `CDD-022-Artifact-Authorization-OQI2-Evidence-Composite-Uniqueness-Amendment.md`, published alongside this document. CDD-040 alone does not authorize touching CDD-022's surface; the companion does, explicitly.

## 8. Entity Resolution boundary (frozen fact)

Existing Entity Resolution (CDD-004):

- operates exclusively in the organizational/legal-entity matching domain (evidence types: LEI, DUNS/external ID, tax registration, address match, legal/trading name match — no part/material/product attribute exists in its evidence model);
- persists `EnterpriseEntityResolutionRecord.supporting_source_object_ids` at `SourceObject` (table-identity) granularity only — it carries no `source_record_reference` and therefore cannot express individual-record correspondence;
- consequently **does not, and cannot today, prove that a specific record in one source (e.g. SAP `MAT-100`) corresponds to a specific record in another source (e.g. PLM `P-442`)**.

CDD-040 does not claim otherwise. No future artifact may cite existing Entity Resolution output as proof of individual-record correspondence for OQI2 purposes.

## 9. `ComparisonSubjectCorrespondence` (new, OQI2-owned)

**Purpose:** explicitly and non-inferentially establish which governed source-record lineages belong to the same stable OQI2 comparison subject.

It **MUST**:
- be explicit (created only by governed action, never inferred);
- be deterministic in its own identity derivation (§11);
- be versioned, immutable per version;
- be tenant-scoped;
- support exactly the lifecycle `ACTIVE` / `RETIRED` (no `DRAFT` — not justified by this document).

It **MUST NOT**:
- contain any fuzzy matching, similarity score, AI inference, probabilistic matching, or majority-based inference of any kind;
- be populated algorithmically by OQI2 code guessing record identity.

**Firewall (binding):**

```
ENTITY RESOLUTION OWNS: inferring/scoring whether records represent the same
  real-world organizational entity, via weighted evidence matching.
ComparisonSubjectCorrespondence RECORDS: an already-governed, explicit,
  human-attested assertion that specific source-record lineages may be
  compared as one OQI2 subject. It performs no inference of its own.
```

`ComparisonSubjectCorrespondence` is explicitly **not** a general-purpose Entity Resolution capability and must never be generalized into one within OQI2. The recommended long-term scalable replacement — extending Entity Resolution's own governance (CDD-004) to natively persist record-level correspondence — is explicitly deferred and is not part of OQI2 (§46, P3 register).

## 10. Correspondence identity model (binding — two distinct identities)

- **`comparison_subject_id`** (UUID) — the stable governed identity of *the thing whose cross-source quality is being evaluated*. Assigned once, by governed action, at first-governance time. It has **no derivation formula** — it is a fresh governed identity, not a function of other inputs (structurally analogous to `SourceSystem`/`SourceObject`'s own server-generated identities). It remains stable across correspondence version changes.
- **`comparison_subject_correspondence_id`** (UUID) — the identity of *one specific, immutable, versioned correspondence assertion*. Deterministically derived (§11). Represents "the exact governed correspondence version establishing which source-record lineages were associated for an Evaluation."

These MUST NOT be conflated. `comparison_subject_id` never appears with a version suffix; `comparison_subject_correspondence_id` always identifies exactly one immutable version.

## 11. Correspondence identity derivation

```
OQI_CROSS_SOURCE_NAMESPACE = uuid5(NAMESPACE_URL, "urn:ctec:oqi:cross-source:v1")
```

Frozen forever once implemented, deliberately distinct from OQI1's `OQI_NAMESPACE` (`urn:ctec:oqi:v1`) and CDD-022's `BOOTSTRAP_SEED_NAMESPACE`, so no OQI2 identity can collide with an OQI1 or evidence identity under any adversarially-chosen input.

```
correspondence_id = uuid5(
    OQI_CROSS_SOURCE_NAMESPACE,
    canonical("comparison_subject_correspondence", tenant_id, str(comparison_subject_id), str(version))
)
```

using the exact length-prefixed canonical encoding already defined in `app.domain.oqi.evaluation._length_prefixed`/`canonical_form` (reused, imported, never reimplemented).

## 12. Correspondence lifecycle

```
ACTIVE   — exactly one per (tenant_id, comparison_subject_id) at any time,
           DB-enforced via a partial unique index, mirroring
           uq_quality_rules_one_active_per_condition exactly.
RETIRED  — terminal for that version; a correction creates a NEW version
           (new correspondence_id, version+1), never mutates a RETIRED or
           ACTIVE row in place.
```

No historical version may ever be deleted or mutated. Retiring a correspondence version **does not** automatically resolve any `QualityComparisonFinding` that depends on it — retirement only makes future `CURRENT_STATE` evaluation of that subject ineligible (mirrors CDD-039's rule-retirement precedent exactly, §22).

## 13. Correspondence members

Each correspondence version has 2..N immutable member rows, each binding one stable `participant_role` to exactly one `SourceRecordLineageIdentity` component pair (`source_object_id` + `source_record_reference`; `tenant_id` is inherited from the correspondence header, never duplicated per member).

```
one role → at most one lineage per correspondence version (v1 simplification,
           explicit, not silent — a role needing multiple lineages
           requires a future governance cycle)
```

DB constraints (§37): `PRIMARY KEY (correspondence_id, participant_role)`; `UNIQUE (correspondence_id, source_object_id, source_record_reference)` — the latter declaratively prevents the same physical lineage from being bound to two conflicting roles within one correspondence version.

`SourceRecordLineageIdentity` here carries the exact OQI1 meaning (CDD-039 §11): *continuing governed source-key lineage within one SourceObject and tenant* — never a claim of current real-world physical incarnation.

## 14. `QualityDimension.CONSISTENCY` (extension of OQI1's `QualityRule`)

`app.domain.oqi.quality_rule.QualityDimension` gains exactly one new member: `CONSISTENCY`. Scoped explicitly to **cross-source** value consistency. This does not reinterpret, rename, or narrow Gate T's own `CONFLICTING` outcome (CDD-031, intra-source, unchanged) — the two are namespaced by their owning capability and must never be conflated in code, tests, or product copy.

`QualityFindingType` gains exactly two new members: `CROSS_SOURCE_VALUE_CONFLICT`, `CROSS_SOURCE_PARTICIPANT_VALUE_MISSING`. No further Finding types are authorized (§20).

This is a purely additive, zero-migration change: `dimension`/`finding_type` are plain `String` columns with no native Postgres ENUM/CHECK (confirmed by direct inspection of `models/oqi_quality_rule.py`/`models/oqi_quality_finding.py`); the closed `_ALLOWED_COMBINATIONS` frozenset and its "exactly these N, closed" docstrings gain the new rows/wording, mechanically, in `quality_rule.py` (§37, MODIFY).

## 15. Gate T firewall (binding)

```
GATE T OWNS: fitness/currency/intra-source evidence context — FIT/STALE/
  CONFLICTING among FieldValueEvidence rows sharing one source_field_id.
OQI2 OWNS: governed cross-source comparison across explicitly corresponding
  source-record lineages, using its own CONSISTENCY dimension and its own
  Finding types.
```

OQI2 code MUST NOT import `app.application.source_evidence_fitness_evaluation` or any Gate T module, and MUST NOT reinterpret, duplicate, or reuse Gate T's `FIT`/`STALE`/`CONFLICTING` vocabulary for any OQI2 outcome (§43, firewall test).

## 16. Quality condition (reused unchanged)

`quality_condition_id` retains its OQI1 meaning exactly: a stable, versioned semantic-expectation identity (e.g. "Manufacturer Part Number must be consistent across governed participating sources"). It MUST NOT include rule version, participant values, evidence IDs, horizon, authority, or correspondence version.

## 17. `QualityRule` extension (reused, not reinvented)

OQI2 extends `QualityRule` rather than inventing a parallel rule system. Reused unchanged: `quality_condition_id`, `version`, `ACTIVE`/`RETIRED`, immutable version rows, one `ACTIVE` version per condition (DB-enforced, unchanged constraint), `rule_version` as evaluation provenance.

## 18. Comparison membership (governed semantic assertion, distinct from CDD-019)

CDD-019 `SemanticMapping`'s cardinality (at most one `Approved` mapping per `(information_element_requirement_id, tenant)`) structurally cannot express multiple simultaneously-participating source fields for one target — this is a frozen fact, not a defect, and CDD-019 is not reopened or reinterpreted here.

**OQI2 comparison membership is therefore its own, new, governed semantic assertion**, distinct from CDD-019 blueprint-fulfillment `SemanticMapping`: the rule's own governed, versioned, human-authored participant declaration (§20) *is* the comparability proof. It is not derived from, and does not depend on, any participant independently holding `Approved` `SemanticMapping` status.

## 19. Semantic target reference

`rule_parameters.semantic_target_id` (an `information_element_requirement_id`) MAY be carried purely as descriptive vocabulary/context (for future OQI7 explainability and OQI4 traceability). It is documentary only — it does **not** mean, and MUST NOT be interpreted to mean, that every participant independently holds an `Approved` CDD-019 mapping to that target (§18).

## 20. Rule participant schema (canonical, frozen)

```json
{
  "semantic_target_id": "<information_element_requirement_id UUID, optional>",
  "participants": [
    {
      "role": "<stable governed role token, unique within this rule version>",
      "source_field_id": "<UUID>",
      "eligible": true,
      "expected": true,
      "authoritative": false
    }
  ]
}
```

`role` MUST be a stable, immutable-within-rule-version, non-display token (not a mutable `SourceSystem` natural name); any human-readable label is separate display metadata, never identity. `role` uniqueness is enforced within one rule version by validation (§22), not by a rule_parameters-internal DB constraint (JSON has no native uniqueness enforcement — validated at construction/activation time, mirroring `validate_rule_shape`'s existing discipline).

## 21. Explicit eligibility, expectation, authority — no silent defaults (binding, Product-Owner-mandated)

`eligible`, `expected`, `authoritative` are three **independent, explicitly-governed booleans**. **No implicit boolean defaults are permitted anywhere in this schema** — a participant configuration missing any of the three fields is malformed and MUST be rejected (`OqiMalformedRuleError`), never defaulted.

**`authoritative=true` MUST NOT imply `expected=true`.** This inference is explicitly rejected. A rule author designating a participant authoritative but not expected is a legitimate, if unusual, governance choice this document does not forbid — OQI2 never manufactures a quality expectation from another piece of metadata; expectations must be explicitly governed (Product Owner core principle, verbatim).

- `eligible=true` means: this governed participant may participate in this comparison. It does **not** by itself establish that a record or value must exist.
- `expected=true` means: this rule explicitly governs that, *where the correspondence names a lineage for this role* (§27), the participant's value is expected to exist. (See §27 for the full, non-naive resolution of what `expected` combined with correspondence membership actually permits OQI2 to conclude.)
- `authoritative=true` means: governance has designated this participant as preferred for explanation purposes in this comparison context. It never overrides deterministic conflict detection (§24).

## 22. Participant validation (deterministic, fail-closed)

At rule construction/activation and defensively re-validated at evaluation time (mirroring `validate_rule_shape`'s existing "construction + evaluation-time defensive re-check" discipline):

```
role: MUST be present, non-empty, unique within the rule version
source_field_id: MUST be present; existence checked against source_fields
eligible: MUST be an explicit boolean (no default)
expected: MUST be an explicit boolean (no default)
authoritative: MUST be an explicit boolean (no default)
at most one participant with authoritative=true
authoritative=true REQUIRES eligible=true
expected=true REQUIRES eligible=true
duplicate source_field_id across two roles: REJECTED (one field, one role)
minimum configured participants: >= 2
```

Any violation raises `OqiMalformedRuleError` before persistence or evaluation — fail-closed, never silently coerced.

## 23. Authority semantics (binding)

Authority means governance has designated a participant as preferred/authoritative for this attribute comparison context. It does **not** mean the authoritative value is guaranteed correct, and it does not suppress or override deterministic conflict detection:

```
SAP = ABC, PLM = XYZ (PLM authoritative)  →  still VIOLATED.
```

Authority affects Finding **explanation** metadata only, never whether disagreement is detected (§24).

## 24. Majority voting (rejected, binding)

```
SAP = ABC, PLM = ABC, Portal = XYZ  →  VIOLATED.
```

Two-of-three agreement is never truth. OQI2 must never conclude a value is correct merely because a plurality of participants share it.

## 25. Exact-match v1 semantics

Comparison equality = `value.strip() == other.strip()` (whitespace-trimmed, **case-preserving**, no Unicode normalization, no numeric coercion, no unit conversion, no synonym mapping, no fuzzy comparison, no LLM normalization). This is the smallest deterministic semantics that satisfies the north star without introducing non-determinism disputes. Richer normalization is out of scope and requires its own future governance cycle.

## 26. Participant eligibility (restated, binding)

See §21. Eligibility alone never establishes existence expectation.

## 27. Participant expectation vs. missingness — the epistemic resolution (mandatory, binding)

Rule-level `expected=true` **alone is never sufficient** to produce a missing-participant Finding for a specific comparison subject. The governing rule is:

```
4a. Correspondence NAMES a lineage for this role for THIS subject, but
    CTEC has never observed any FieldValueEvidence for it (known-lineage
    test, §28, returns false)
      → this IS positive, subject-level, governed knowledge (a human/
        governance process explicitly asserted this record's existence)
      → VIOLATED / CROSS_SOURCE_PARTICIPANT_VALUE_MISSING is justified,
        IF AND ONLY IF the rule also marks this role expected=true.

4b. Correspondence does NOT name any lineage for this role for THIS
    subject at all
      → the role is simply not part of this subject's governed
        correspondence
      → EXCLUDED — no Finding, regardless of the rule's expected flag.
```

`ComparisonSubjectCorrespondence` membership (§13) **is** the "stronger subject-level expectation primitive" required to avoid manufacturing missingness from rule-level metadata alone. `expected` only has teeth for roles the correspondence has already, explicitly, subject-specifically committed to. A role present in the rule but absent from the active correspondence is **never** evaluated and **never** produces a Finding, independent of `expected` (this directly resolves rule/correspondence role-compatibility, §33, without requiring exact role-set equality between rule and correspondence).

## 28. Known-lineage rule (reused unchanged from CDD-039 §12)

A participant lineage is known iff CTEC possesses at least one admitted, non-empty `FieldValueEvidence` row anywhere under that participant's own `SourceObject` + `source_record_reference` (any `SourceField`, not only the target field — reusing OQI1's `select_known_lineage_evidence_id` exactly, scoped per participant lineage). *Observed historically ≠ exists currently.*

## 29. Missingness — full case resolution

```
Case 1: known lineage, expected=true,  zero qualifying target evidence
        → VIOLATED / CROSS_SOURCE_PARTICIPANT_VALUE_MISSING

Case 2: known lineage, expected=false, zero qualifying target evidence
        → EXCLUDED from value comparison for this evaluation cycle;
          informational only; no Finding. (The participant contributes
          nothing to compare, but its absence is not itself a violation
          since it was never governed as expected.)

Case 3: correspondence names no lineage for this role (§27, case 4b)
        → EXCLUDED, regardless of expected.

Case 4: correspondence names a lineage, lineage unknown (no evidence at
        all, §28), expected=true
        → VIOLATED / CROSS_SOURCE_PARTICIPANT_VALUE_MISSING (§27, case 4a
          — the correspondence's own naming of the lineage is the
          positive knowledge that justifies this, not the rule's
          expected flag in isolation).

Case 5: correspondence names a lineage, lineage unknown, expected=false
        → EXCLUDED, no Finding (same treatment as Case 2 semantically:
          optional participant, absence uninformative).
```

## 30. Minimum evaluable set

```
VIOLATED  if any deterministically-provable expected-participant
          missingness exists (Cases 1 or 4 above), independent of how
          many other participants are known.

otherwise: >= 2 known-and-valued participants required to evaluate
          agreement/conflict. A single observed value cannot prove or
          disprove cross-source consistency; fewer than 2 known values
          with no missingness triggered → NOT_EVALUABLE (no Evaluation
          persisted, no Finding touched — mirrors OQI1's None-return
          convention exactly).
```

## 31. Finding taxonomy (minimal, frozen)

```
CROSS_SOURCE_VALUE_CONFLICT
CROSS_SOURCE_PARTICIPANT_VALUE_MISSING
```

No further Finding types (`AUTHORITATIVE_SOURCE_WRONG`, `NON_AUTHORITATIVE_SOURCE_WRONG`, `MAJORITY_CONFLICT`, or similar) are authorized — OQI2 cannot claim those truths. Authority is explanation metadata, never a Finding-type discriminator.

## 32. Cross-source Finding identity (frozen formula)

```
finding_id = uuid5(
    OQI_CROSS_SOURCE_NAMESPACE,
    canonical(tenant_id, quality_condition_id, "CROSS_SOURCE_COMPARISON", str(comparison_subject_id))
)
```

**Explicitly excluded, with justification:**

| Excluded | Justification |
|---|---|
| `rule_version` | mirrors CDD-039's proven exclusion — a Finding tracks the same condition against the same subject across rule-version changes (participant membership added/removed, authority changed) |
| participant membership | membership lives in `rule_version`; adding/removing a participant is the same business quality condition against the same subject, not a new one (OQI2-R §AI, tested and confirmed) |
| participant order | canonicalized before any identity computation, never a raw input |
| authority | rule configuration, not identity — an authority change is a new rule version, same Finding history |
| evidence IDs / evidence values | Findings track the current-state truth, not any one evaluation's inputs — mirrors CDD-039 exactly |
| `evaluation_horizon` | belongs to Evaluation identity (§42), not Finding identity — a Finding persists across many evaluations at many horizons |
| `comparison_subject_correspondence_id` | a correspondence correction (new version, same `comparison_subject_id`) is still the same subject being tracked — mirrors the rule_version exclusion principle exactly |

## 33. Finding lifecycle (reused, six-transition table)

`app.domain.oqi.finding.apply_transition`'s exact six-row OPEN/RESOLVED transition table (CDD-039 §27–§30) is mechanically reproduced for `QualityComparisonFinding` in a new function (`app.domain.oqi_cross_source.finding.apply_correspondence_finding_transition`, §37) — not reused directly, since the subject shape differs (`comparison_subject_id` vs. `EvaluationSubject`), but semantically identical: `occurrence_count` increments only on transitions into `OPEN`; `last_seen_at` updates only on `VIOLATED`; `last_evaluated_horizon` updates on every touching evaluation; `state_revision` increments on every authoritative touch including `OPEN→OPEN`/`RESOLVED→RESOLVED`.

Only `CURRENT_STATE` evaluation may mutate a `QualityComparisonFinding`. `HISTORICAL` evaluation may never open, resolve, reopen, increment `state_revision`, increment `occurrence_count`, or change `latest_evaluation_id` — reused exactly from CDD-039 §22.

## 34. Correspondence retirement (does not resolve Findings)

Retiring a `ComparisonSubjectCorrespondence` version does not automatically resolve any `QualityComparisonFinding` that depended on it. It only makes future `CURRENT_STATE` evaluation of that subject ineligible (raises an ineligibility error, mirroring `OqiRuleNotActiveError`) until a new `ACTIVE` correspondence version is governed for that subject. Prerequisite disappearance is not proof the quality problem disappeared (mirrors CDD-039's rule-retirement precedent exactly).

## 35. Rule retirement (reused unchanged)

Retiring the `CONSISTENCY` rule version behaves exactly as CDD-039 §framework already specifies for any `QualityRule`: no Finding mutation merely because the rule is retired.

## 36. Participant SourceField loss

If a participant's `source_field_id` becomes invalid (SourceField retired/unavailable), future `CURRENT_STATE` evaluation becomes ineligible for that role unless a new governed rule version supersedes it. Existing Findings are never silently resolved.

## 37. Evaluation participant snapshot (required, immutable)

Persisted per `(evaluation_id, participant_role)`:

```
evaluation_id, participant_role, source_field_id, source_object_id,
source_record_reference, expected, authoritative
```

`eligible` is **not** persisted — every snapshot row, by construction, represents a participant that was actually eligible and evaluated; storing it would be redundant. `expected`/`authoritative` **are** snapshotted, because historical explanation of *why* a Finding was or wasn't raised requires knowing what the rule governed at evaluation time, independent of later rule-version changes. No raw observed source values are ever duplicated here.

## 38. Rule configuration vs. evaluation snapshot (two layers, not conflated)

```
Rule version (rule_parameters, JSON, §20): defines CONFIGURED comparison
  participants and governance semantics — cheap, versioned, low-
  cardinality, exactly OQI1's proven pattern.
Evaluation participant snapshot (§37, normalized DB rows): records the
  CONCRETE participant/source-record lineage actually used for one
  specific Evaluation — normalized because this is where DB-integrity
  and historical-explainability needs live (§39, §51).
```

## 39. Correspondence provenance (required, immutable)

Every `QualityComparisonEvaluation` references `comparison_subject_correspondence_id` — the exact correspondence version used, pinned at evaluation time. This is immutable provenance: ten years later, "why were SAP MAT-100 and PLM P-442 compared?" is answered by an immutable foreign key, never a live re-query of current correspondence state.

## 40. Participant-keyed evidence digest

```
canonical_form([
  { role, canonical_subject_identity, evidence_ids: sorted(evidence_ids, key=str) }
  for role in sorted(participants_present, key=role)
])
→ SHA-256 hex digest
```

Reuses `app.domain.oqi.evaluation`'s exact length-prefixed canonical encoding (imported, never reimplemented). Role-sensitive, subject-sensitive, evidence-sensitive, input-order-independent (canonicalized by role before hashing) — this closes the flat-digest collision risk a naive reuse of OQI1's `evidence_set_digest` alone would introduce (swapping SAP's and PLM's evidence would otherwise hash identically; it must not).

## 41. Zero-evidence sentinel (reused, with an added distinction)

A participant present in the evaluation (correspondence names its lineage, §27) with known lineage but zero qualifying target-field evidence is represented in the digest list using OQI1's exact `evidence_set_digest(())` = `SHA-256("EMPTY_EVIDENCE_SET")` sentinel for that entry. A participant **not part of the evaluation at all** (correspondence doesn't name it, §27 case 4b/case 3, or `expected=false` + unknown lineage, case 5) is **absent from the digest list entirely** — these are not the same representation and must never be conflated.

## 42. Cross-source Evaluation identity (frozen formula)

```
evaluation_id = uuid5(
    OQI_CROSS_SOURCE_NAMESPACE,
    canonical(
        tenant_id, quality_condition_id, str(rule_version),
        "CROSS_SOURCE_COMPARISON", str(comparison_subject_id),
        evaluation_mode, evaluation_horizon.isoformat(),
        participant_evidence_digest, str(comparison_subject_correspondence_id)
    )
)
```

Explicitly excluded: `state_revision`, any raw observed value. `comparison_subject_correspondence_id` **is** included here (unlike Finding identity, §32) — an Evaluation is a historical fact tied to the specific correspondence it relied on; two evaluations relying on different correspondence versions for the same nominal subject are genuinely different evaluations.

## 43. Idempotency (frozen)

Identical `(tenant, condition, rule_version, comparison_subject_id, correspondence_id, mode, horizon, participant_evidence_digest)` MUST produce the same `evaluation_id`. Changing any one of these MUST change `evaluation_id`, including: any one participant's evidence, a swap of which evidence belongs to which participant, a membership/authority change via new rule version, or a correspondence-version change. Participant input ordering alone MUST NOT change `evaluation_id` (canonicalized before hashing, §40).

## 44. HISTORICAL mode

Reused unchanged: caller-supplied horizon; persists its own immutable `QualityComparisonEvaluation` row; never acquires authority; never mutates `QualityComparisonFinding`.

**Documented limitation (not silently hidden):** a freshly-requested historical evaluation for an arbitrary past horizon can only use the current `ACTIVE` correspondence version — there is no governed "as-of" correspondence history query. True historical accuracy for a past horizon is only guaranteed for evaluations that already pinned their `comparison_subject_correspondence_id` at original evaluation time (§39). Solving temporal correspondence history is explicitly out of OQI2 v1 scope.

## 45. CURRENT_STATE mode

Trusted runtime horizon; requires an `ACTIVE` rule **and** an `ACTIVE` correspondence for the subject (both preconditions, §27/§36); exclusive evaluation authority acquired before any participant evidence selection; may mutate `QualityComparisonFinding`.

## 46. Concurrency (frozen ordering, resolves the OQI2-R wording tension)

Reuses OQI1's proven authority mechanism exactly:

```sql
SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))
```

with `OQI_CROSS_SOURCE_ADVISORY_LOCK_SEED = 2` (distinct from repository.py's replay-lock seed 0 and OQI1's own seed 1 — defense-in-depth, mirroring the exact rationale that chose seed 1 for OQI1), and `identity` = the exact canonical material used for cross-source Finding identity (§32) — `lock identity material == Finding UUID5 input material`, preserved exactly.

**Frozen, single, non-contradictory ordering** — mirrors OQI1's actual merged implementation exactly (the caller loads the rule *before* the service call; the service only defensively re-checks the in-memory object's own status field; it never re-queries the DB after lock acquisition):

```
1. Caller loads ACTIVE rule (RuleRepository.get_active(quality_condition_id))
2. Caller loads ACTIVE correspondence (CorrespondenceRepository.get_active(tenant_id, comparison_subject_id))
3. Caller invokes the evaluation service with both pre-loaded objects
4. Service defensively checks rule.status == ACTIVE (in-memory; raises OqiRuleNotActiveError-equivalent if not)
5. Service defensively checks correspondence.status == ACTIVE (in-memory; raises correspondence-ineligibility error if not)
6. Service computes Finding-identity material (needs only tenant_id + quality_condition_id + comparison_subject_id — never the rule/correspondence CONTENT, only their already-known identifiers)
7. Service acquires the advisory transaction lock — BEFORE the first Finding row exists, BEFORE any participant evidence selection
8. Service selects per-participant evidence (role-by-role, using the correspondence's per-role lineages + the rule's per-role source_field_id, §27's algorithm)
9. Service evaluates SATISFIED/VIOLATED per §29/§30
10. Service persists the Evaluation idempotently (rule_version + correspondence_version pinned from the objects loaded in steps 1-2, before the lock — this exactly mirrors how OQI1 pins rule_version from its own pre-lock-loaded rule object)
11. If the insert was genuinely new: service mutates the Finding
12. Transaction commits, releasing the lock
```

A concurrent correspondence retraction or rule retirement between steps 1-2 and step 7 does not affect the in-flight worker — it already captured its versions; the *next* evaluation attempt sees the change.

## 47. Lock-before-evidence (restated, binding)

`CURRENT_STATE` evaluation authority MUST be acquired before selecting evidence for any participant, and held through evidence selection, comparison, Evaluation persistence, Finding mutation, `state_revision` increment, and transaction commit — reused exactly from CDD-039 §24–§25.

## 48. Coherent evaluation frontier

All participants in one `CURRENT_STATE` evaluation share one trusted `evaluation_horizon`. Per participant: qualifying evidence requires `received_at <= evaluation_horizon` (the trust/eligibility boundary, reused from CDD-039 exactly); among qualifying rows, the latest by `observed_at` (then `received_at`) is selected for value comparison — reusing `select_latest_target_field_value`'s exact ordering, looped per participant. No second temporal model is introduced.

## 49. DB provenance constraints (frozen design)

Confirmed feasible by direct Postgres-mechanics verification (no trigger required, fully declarative):

```
field_value_evidence  gains:  UNIQUE(field_value_evidence_id, source_field_id)
                               [additive, no data mutation, no backfill —
                               authorized by the separate CDD-022 companion
                               amendment, §7]

quality_comparison_evaluation_participants:
    UNIQUE(evaluation_id, participant_role, source_field_id)

quality_comparison_evaluation_evidence:
    FK (evaluation_id, participant_role, source_field_id)
      → quality_comparison_evaluation_participants(evaluation_id, participant_role, source_field_id)
    FK (field_value_evidence_id, source_field_id)
      → field_value_evidence(field_value_evidence_id, source_field_id)
```

This chained composite-FK structure makes it **structurally impossible** at the database level to insert an evidence-association row whose evidence does not genuinely belong to the exact `source_field_id` the governed participant snapshot recorded for that role (Invariants II and V, OQI2-R §V, are DB-enforced — no trigger, no application-only gap).

## 50. Tenant integrity boundary (honest, not overclaimed)

Full native DB-level tenant enforcement is **not** available for evidence linkage — `field_value_evidence` has no `tenant_id` column (CDD-022, unmodified), so no composite FK can validate tenant match directly at that table. Tenant integrity for OQI2 is **application-enforced, narrowed to exactly one governed write site**: creation of the `quality_comparison_evaluation_participants` snapshot row, where the resolved tenant of `source_field_id` (transitively, via `source_objects.tenant_id`) MUST be asserted equal to the Evaluation's own `tenant_id` before the row is written. This is a real, honestly-disclosed residual gap (§59 P3 register), narrowed from OQI1's already-accepted posture, not eliminated. An architecture test MUST prove this is the single, exclusive construction site for this table (§43).

## 51. `OQI-P3-002` disposition

```
SUBSTANTIALLY RESOLVED — field/participant evidence binding (Invariants II
and V) is now genuinely DB-enforced via chained composite FKs (§49).
Residual: full DB-level tenant-evidence linkage enforcement remains
deferred defense-in-debt (§50), narrowed to one governed write site.
```

## 52. Persistence schema (exact, frozen)

### `comparison_subject_correspondences`
```
correspondence_id            UUID PK  (deterministic, §11)
comparison_subject_id        UUID NOT NULL  (opaque governed identity, no FK — outlives any one correspondence version)
tenant_id                    String(200) NOT NULL
version                      Integer NOT NULL
status                       String(16) NOT NULL   -- ACTIVE | RETIRED
created_by, created_on       audit columns (existing pattern)
Indexes: tenant_id, comparison_subject_id
Partial unique index: uq_comparison_subject_correspondences_one_active
  ON (tenant_id, comparison_subject_id) WHERE status = 'ACTIVE'
  (mirrors uq_quality_rules_one_active_per_condition exactly)
```

### `comparison_subject_correspondence_members`
```
correspondence_id            UUID, FK → comparison_subject_correspondences.correspondence_id, PK part 1
participant_role              String(64), PK part 2
source_object_id              UUID NOT NULL, FK → source_objects.source_object_id
source_record_reference       String(1000) NOT NULL
UNIQUE(correspondence_id, source_object_id, source_record_reference)
  -- declaratively prevents one lineage bound to two conflicting roles
Index: correspondence_id
```

### `quality_comparison_evaluations`
```
evaluation_id                       UUID PK (deterministic, §42)
tenant_id                           String(200) NOT NULL
quality_condition_id                 String(200) NOT NULL
rule_id                               UUID NOT NULL, FK → quality_rules.rule_id (reused unchanged)
rule_version                          Integer NOT NULL
subject_type                          String(32) NOT NULL  -- "CROSS_SOURCE_COMPARISON"
comparison_subject_id                 UUID NOT NULL  (opaque, no FK)
comparison_subject_correspondence_id  UUID NOT NULL, FK → comparison_subject_correspondences.correspondence_id
evaluation_mode                       String(16) NOT NULL
evaluation_origin                     String(32) NOT NULL
evaluation_horizon                    DateTime(timezone=True) NOT NULL
participant_evidence_digest           String(64) NOT NULL
outcome                               String(16) NOT NULL
applied_current_state_authority        Boolean NOT NULL
state_revision_applied                 Integer NULL
evaluated_on                           DateTime(timezone=True) NOT NULL
Indexes: tenant_id;
  (quality_condition_id, comparison_subject_id, evaluation_mode, evaluation_horizon)
```

### `quality_comparison_evaluation_participants`
```
evaluation_id            UUID, FK → quality_comparison_evaluations.evaluation_id, PK part 1
participant_role          String(64), PK part 2
source_field_id            UUID NOT NULL, FK → source_fields.source_field_id
source_object_id           UUID NOT NULL, FK → source_objects.source_object_id
source_record_reference     String(1000) NOT NULL
expected                     Boolean NOT NULL
authoritative                Boolean NOT NULL
UNIQUE(evaluation_id, participant_role, source_field_id)   -- §49 FK target
```

### `quality_comparison_evaluation_evidence`
```
evaluation_id            UUID, PK part 1
participant_role          String(64), PK part 2
source_field_id            UUID NOT NULL  (denormalized, required for §49's chained FK)
field_value_evidence_id     UUID, PK part 3
sequence_index               Integer NOT NULL
FK (evaluation_id, participant_role, source_field_id)
  → quality_comparison_evaluation_participants(evaluation_id, participant_role, source_field_id)
FK (field_value_evidence_id, source_field_id)
  → field_value_evidence(field_value_evidence_id, source_field_id)
Index: field_value_evidence_id
```

### `quality_comparison_findings`
```
finding_id               UUID PK (deterministic, §32)
tenant_id                 String(200) NOT NULL
quality_condition_id       String(200) NOT NULL
subject_type                String(32) NOT NULL  -- "CROSS_SOURCE_COMPARISON"
comparison_subject_id       UUID NOT NULL  (opaque, no FK)
finding_type                 String(32) NOT NULL
status                        String(16) NOT NULL  -- OPEN | RESOLVED
state_revision                 Integer NOT NULL
first_seen_at                   DateTime(timezone=True) NOT NULL
last_seen_at                     DateTime(timezone=True) NOT NULL
last_evaluated_horizon             DateTime(timezone=True) NOT NULL
occurrence_count                     Integer NOT NULL
reopen_count                          Integer NOT NULL
latest_evaluation_id                   UUID NOT NULL, FK → quality_comparison_evaluations.evaluation_id
Indexes: tenant_id; status
```

No OQI1 table's shape or semantics changes. The only touch to a pre-existing table anywhere in this document is the single additive `field_value_evidence` constraint (§49), authorized by the separate CDD-022 companion (§7).

## 53. Migration

```
revision      = "0021_oqi2_cross_source_consistency"
down_revision = "0020_oqi1_quality_foundation"
```

Single head, confirmed by exhaustive chain inspection before freeze. Adds the six tables of §52 plus the one additive constraint of §49. Expected table count at new head: **74** (68 + 6).

## 54. Domain module organization

New subpackage `backend/app/domain/oqi_cross_source/` (one subpackage per feature, consistent with `domain/gate_s/`, `domain/gate_v/`, `domain/oqi/` — never mixed into the existing `domain/oqi/` package, to avoid ambiguity with OQI1's single-source concepts).

## 55. Rule shape validation (extended, not duplicated)

`app.domain.oqi.quality_rule.validate_rule_shape` gains the `CONSISTENCY`-dimension branch (§22's rules) inside its existing single shared validator — mirroring OQI1's own architecture (one shared validator for all dimensions), not a second parallel validator. Raises the existing `OqiMalformedRuleError`.

## 56. Correspondence shape validation

A new typed exception, `OqiMalformedCorrespondenceError` (subclass of `DomainException`, sibling to `OqiMalformedRuleError`), validates at minimum: `>= 2` members; unique participant roles within the version; unique `(source_object_id, source_record_reference)` across roles (also DB-enforced, §52); valid tenant; non-empty `source_record_reference`; exactly one `ACTIVE` version per `(tenant_id, comparison_subject_id)` (DB-enforced, §52).

## 57. Firewalls (binding, tested — §61)

```
OQI2 MUST NOT import: Gate T evidence-fitness modules, Gate V agent modules,
  Gate S approval modules, Entity Resolution matching/scoring modules,
  any LLM/model-provider SDK, any OQI3/OQI4/OQI5/OQI6 module (none exist
  yet — forward-declared prohibition), any frontend or API route module.
OQI2 MAY consume: persisted/governed ComparisonSubjectCorrespondence output
  (read-only), FieldValueEvidence (read-only), QualityRule infrastructure
  (reused).
OQI2 MUST perform: zero record-matching inference of any kind.
```

## 58. Testing obligations (exact, required at Artifact Authorization)

Concurrency (12 real-Postgres tests, §82 of the governing prompt); DB integrity negative tests (8+, §84); provenance chain test (§83); epistemic matrix (13+ cases, §85, covering every row of §29 exactly); identity adversarial matrix (14+, §86); firewall architecture tests (§57/§61); full lint/type/format clean; exact-head CI green.

## 59. Performance / debt (explicitly deferred)

The composite `field_value_evidence(source_field_id, source_record_reference, received_at)` index is **not** part of OQI2's Artifact Authorization. It is recommended as a separate, future CDD-022 hardening amendment (benefits OQI1's own existing queries too, not OQI2-specific) — not smuggled into this freeze.

## 60. P3 register (carried forward and reassessed)

```
OQI-P3-001: 64-bit advisory-lock hash collision space.
  ACCEPTED / harmless over-serialization / non-blocking. Unchanged.

OQI-P3-002: RESOLVED for field/participant-evidence binding (§49, §51).
  Residual: full DB-level tenant-evidence linkage remains application-
  enforced at one narrow, tested write site (§50). ACCEPTED / non-blocking
  / documented defense-in-depth debt.

OQI-P3-003: ComparisonSubjectCorrespondence (§9) is deliberately explicit
  and does not scale to very large comparison-subject populations by
  design (explicit enumeration, not inference). Future direction: extend
  Entity Resolution's own governance (CDD-004) to natively persist
  record-level correspondence at scale — explicitly out of OQI2 scope.
  ACCEPTED / non-blocking / documented future direction.

OQI-P3-004: field_value_evidence(source_field_id, source_record_reference,
  received_at) composite index for multi-participant fan-out performance
  — deferred to a future CDD-022 hardening amendment, not hidden OQI2
  debt (§59). ACCEPTED / non-blocking.
```

## 61. Future evolution

Any of the following require their own future governance cycle and are explicitly not authorized here: an ER-owned scalable record-correspondence replacement (P3-003's stated direction); a third `QualityDimension`; normalization richer than exact-match; ranked/contextual source authority (beyond single attribute-specific authority); an OQI2 API or frontend.

## 62. Closure criteria

OQI2 governance is frozen when: CDD-040 and its exact Artifact Authorization are published byte-identical to their hashed record; the CDD-022 companion amendment is published alongside; all OQI1 governance hashes remain unchanged; exact-head CI is green; the working tree returns to clean. Implementation proceeds only under the exact 25-file Artifact Authorization surface (§ Artifact Authorization document) — no 26th file without a governance amendment.
