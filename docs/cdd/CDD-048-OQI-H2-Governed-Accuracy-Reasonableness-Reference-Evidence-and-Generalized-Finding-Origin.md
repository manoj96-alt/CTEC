# CDD-048 — OQI-H2 — Governed Accuracy, Reasonableness, Reference Evidence, and Generalized Finding Origin

Version: 1.0 FROZEN
Status: FROZEN (architecture only — implementation authorized only via the paired Artifact Authorization companion)
Implementation state: NOT STARTED
Governing authorities:
  CDD-046-OQI-Hardening-Nine-Dimension-Architecture.md — FROZEN
  CDD-046-QualityRule-Ownership-Erratum.md — FROZEN, APPROVED
  CDD-047-OQI-H1-Governed-Quality-Coverage-and-Reliance-Generalization.md — FROZEN, IMPLEMENTED
  CDD-047-OQI-H1-Governed-Quality-Coverage-and-Reliance-Generalization-Artifact-Authorization.md — FROZEN, IMPLEMENTED
  CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md — APPROVED
  CDD-047-Artifact-Authorization-CI-Migration-Head-Closure-Amendment.md — APPROVED
Mandatory template: CDD Template v2.2 (this repository's established house style)

**Publication note:** This document freezes the architecture for OQI-H2 — the two remaining OQI1/OQI2/OQI3-adjacent quality dimensions (ACCURACY, REASONABLENESS) plus the governed Reference Evidence substrate they require and the minimum generalized Finding-origin prerequisite discovered necessary for their Findings to participate natively in Noetva's existing downstream quality-to-impact chain. It follows OQI-H2-DR (discovery + resolution, complete) and incorporates four binding Product Owner decisions (PO-01 through PO-04, §3). Implementation is authorized only via the paired `CDD-048-...-Artifact-Authorization.md` companion. No implementation has occurred as of this freeze.

---

## 1. Purpose

CDD-046 froze the target nine-dimension OQI architecture but authorized no implementation. CDD-047 (H1) implemented only the governance-vocabulary and coverage-derivation half of that architecture (`CoverageDimension`, `QualityCoveragePolicy`), explicitly disclaiming any of the six unimplemented evaluators. OQI-H2-DR (discovery) found that CDD-046's own design for Accuracy and Reasonableness is nearly complete, but surfaced one genuine, previously-unaddressed architectural prerequisite: the physical mechanism by which a Finding enters Noetva's ontology-impact → business-impact → Reliance → remediation chain (`FindingFamily`, `RemediationCandidateBasis`) is a closed, two-member-enum-pair vocabulary that conflates "which physical table stores this Finding" with "which quality dimension produced it," and is not extensible to new dimensions without either (a) semantic corruption (treating an Accuracy Finding as if it were an OQI1 Completeness/Validity Finding) or (b) an unbounded taxonomy redesign. This document resolves that prerequisite with the smallest architecture that is both sufficient for H2 and forward-compatible with all nine governed dimensions, and freezes the complete Accuracy/Reasonableness/Reference-Evidence architecture on top of it.

Backward-compatibility promise: no existing OQI1/OQI2/OQI3 behavior, Finding, evaluation row, crown invariant, or API/frontend contract changes meaning. Every generalization introduced here is additive.

## 2. Capability claim (exact, binding)

Once implemented per the paired Artifact Authorization, Noetva will be able to:

- Evaluate an observed value (`FieldValueEvidence`) against qualifying, governed, versioned Reference Evidence and persist a categorical Accuracy result (`SATISFIED`/`VIOLATED`), or persist zero rows when no qualifying Reference Evidence exists (`NOT_EVALUABLE`).
- Evaluate deterministic, governed, contextual plausibility rules (extending the existing OQI3 business-rule engine) and persist a categorical Reasonableness result, or persist zero rows when no applicable governed rule exists.
- Detect and durably record — without inventing a truth-selection rule — the condition where qualifying Reference Evidence itself disagrees.
- Let both new dimensions' Findings participate natively in ontology-impact evaluation, business-impact evaluation, Reliance derivation, and the governed remediation lifecycle, through a generalized Finding-origin mechanism that never misrepresents a Finding's true quality dimension.
- Let a tenant's `QualityCoveragePolicy` (H1) require `ACCURACY`/`REASONABLENESS` and have that requirement satisfied only by a real, qualifying, persisted evaluation — never by rule existence, reference existence, or evaluator-code existence alone.

**No broader claim is authorized.** In particular: no claim that Uniqueness, Timeliness, Integrity, or Conformity are implemented; no claim that any production orchestration/trigger for any OQI evaluator (old or new) exists; no claim that Reference Evidence, human verification, or the reference-evidence-conflict object are exposed through any public API beyond the minimum named in §V; no claim that remediation for these two dimensions is autonomous; no claim of numeric confidence, statistical, or model-derived quality conclusions anywhere in this document's scope.

## 3. Product Owner decisions frozen (PO-01 through PO-04)

**PO-01 — Downstream Finding integration (binding, drives §F–§S of this document).** H2-DR's Option A (defer OQI4/OQI5 integration entirely) is rejected. Accuracy and Reasonableness Findings must be architecturally capable of participating natively in the existing governed chain. The minimum coherent generalization is resolved in §E/§F as a value-object `QualityFindingOrigin` — not a redesign of `FindingFamily`'s persisted values, not a new physical Finding table, and not the full previously-deferred `QualityFindingOrigin` *program* (whatever broader scope that name might have accreted) — scoped exactly to what H2 requires plus forward-compatible semantics for the four still-deferred dimensions.

**PO-02 — Governed reference datasets (binding, drives §I.1).** H2 supports shared-platform governed reference datasets only. Tenant-private reference datasets are explicitly deferred (§AA). A tenant's `ReferenceEvidenceAssertion` (§I) may reference a shared-platform dataset; it may not define one.

**PO-03 — Human verification authority (binding, drives §K, §T).** `HUMAN_VERIFIED_EVIDENCE` requires its own, distinct verification-authority scope, never satisfied by reference-evidence configuration authority, quality-rule configuration authority, or remediation authority.

**PO-04 — Production evaluator trigger (binding, drives §W, §AA).** Production orchestration for any OQI evaluator (old or new) is explicitly deferred. H2 follows the existing, unbroken precedent: deterministic service invocation exercised by tests, real-PostgreSQL verification, demo-seeder invocation, and Docker/runtime proof — never a scheduler, event bus, or ingestion trigger. This is recorded as inherited P1 platform debt (§AB), not an H2 defect.

## 4. Current-state evidence (re-verified for this freeze, not assumed from H2-DR alone)

Re-inspection for this phase confirms, against live code:

- `FindingFamily` is independently defined **twice** (`app/domain/oqi_ontology_impact/evaluation.py`, `app/domain/oqi_remediation/case.py`), both closed to exactly `OQI1`/`OQI2`/`OQI3`, bridged only by ad hoc re-wrap calls at specific sites (`oqi_business_impact_repository.py`, `oqi_product_experience_service.py`). This duplication is itself a pre-existing structural wart this document does not need to eliminate to satisfy PO-01 (see §F) but records for the reader's awareness.
- Every dispatching call site on `FindingFamily` in the codebase today dispatches on **physical storage table**, never on semantic quality dimension — because until now, storage family and quality dimension have been 1:1. `QualityDimension` (a wholly separate, already-precedented-as-additively-extensible enum: it grew from 2 to 3 members once already, CDD-040) is never read by any `FindingFamily`-dispatching code path.
- `RemediationCandidateBasis` is a write-once, closed, 4-member opaque label with **zero dispatch call sites anywhere in the codebase** — the least risky vocabulary in this entire document to extend.
- Neither `FindingFamily` nor `RemediationCandidateBasis` is a native PostgreSQL `ENUM` type; both persist as plain `VARCHAR` columns validated only in Python (`quality_findings`-family tables use no CHECK constraint at all; H1's `oqi_quality_coverage_policy_dimensions` is the only OQI table using a `CheckConstraint` for a closed-vocabulary column, and this document follows that pattern for every new closed-vocabulary column it introduces — see §X).
- The `finding_family` column on OQI4's two tables is `String(8)` — exactly sized for the current 4-character values with 4 characters of headroom. Because this document does **not** add a new `FindingFamily` member (§F), this column requires **no width migration**.
- `OntologyElementType` (`ENTITY`/`RELATIONSHIP`) is the strongest existing precedent for a type-discriminator + id pattern reused across models without a database-level polymorphic foreign key — this document's `QualityFindingOrigin` follows that precedent, not the weaker JSON-list precedent `FindingReference`'s own docstring cites.
- `oqi-coverage:configure` (H1) remains, confirmed, registered in **zero** places beyond a CDD sentence — no Python call site, no Keycloak realm entry. This document treats that as a cautionary precedent (§T) and does not repeat it: every scope this document names as enforced in H2 is required to have both a real `authorize(...)` call site and a real `keycloak/ctec-realm.json` entry before H2-I may claim it is enforced.
- Alembic head remains `0027_h1_coverage_policy`. Longest existing revision id is `0013_decision_evaluation_group` (30 chars); `alembic_version.version_num` is `VARCHAR(32)`. New revision ids in §X are chosen with margin below this ceiling, per the documented CDD-040 precedent of a prior revision-id-length production failure.

## 5. Definitions (frozen vocabulary)

```
Quality Dimension      the governed WHY — the semantic quality concept a Finding represents
                        (COMPLETENESS, VALIDITY, CONSISTENCY, ACCURACY, REASONABLENESS today;
                        UNIQUENESS/TIMELINESS/INTEGRITY/CONFORMITY remain future/deferred).
                        Lives on QualityDimension (extended by this document).

Evaluator Family        the governed HOW — which evaluation engine produced the result
                        (OQI1 field-evidence evaluator, OQI2 cross-source evaluator,
                        OQI3 business-rule evaluator). Unchanged by this document.

Finding Type             the governed WHAT-WENT-WRONG — the specific defect shape
                        (MISSING_VALUE, ENUM_VIOLATION, CROSS_SOURCE_VALUE_CONFLICT,
                        REFERENCE_VALUE_UNSUPPORTED [new], CONTEXTUAL_PLAUSIBILITY_VIOLATION [new], ...).

Physical Finding Table   the governed WHERE — which table a Finding row physically lives in
                        (quality_findings / quality_comparison_findings / business_rule_findings).
                        Renamed-in-meaning (not renamed-in-value) as FindingStorageFamily, §E.

Finding Origin            the governed WHICH — the composite (tenant, storage family, dimension,
                        finding id, state revision) needed by any downstream consumer to
                        correctly and losslessly identify a specific Finding and what it means.
                        New: QualityFindingOrigin, §E/§F.

Remediation Action        the governed CORRECTIVE-STEP shape (today: UPDATE_FIELD only).
                        Not expanded by this document (§S).
```

These five concepts are independent axes. Prior to this document, `FindingFamily` silently collapsed "Evaluator Family," "Physical Finding Table," and (accidentally, by 1:1 coincidence) "Quality Dimension" into one value. This document does not collapse them back — it makes the axes explicit and threads the previously-missing one (Quality Dimension) through every downstream dispatch site alongside the existing one (storage family).

## 6. Accuracy — frozen operational definition

Unchanged from CDD-046 §7/§13, operationalized:

```
observation (FieldValueEvidence)
      +
qualifying, ACTIVE, governed Reference Evidence
      ↓
deterministic comparison
      ↓
SATISFIED | VIOLATED

no qualifying Reference Evidence  →  NOT_EVALUABLE  →  zero persisted Accuracy evaluation row
```

No numeric confidence, ever. Never inferred from source authority, majority, agreement, canonicalization, Validity, LLM judgment, agent output, or anomaly score. Preserved, unchanged, as binding crown invariants (§Z): `VALID ≠ ACCURATE`, `CONSISTENT ≠ ACCURATE`, `CANONICAL ≠ ACCURATE`, `AUTHORITY ≠ TRUTH`, `MAJORITY ≠ TRUTH`.

## 7. Accuracy — frozen evaluation granularity and evaluator architecture

**Subject**: the immutable observation (`FieldValueEvidence` context: tenant, source object, source field, source record reference, observed representation) — never a collapsed enterprise-entity attribute. This is required for SAP and PLM observations of the same fact to be scored independently against one Reference Evidence row (H2-DR Case C), while Consistency independently and separately reports whether SAP and PLM agree.

**Evaluator family**: extends the OQI1 `QualityRule`/`QualityEvaluation`/`QualityFinding` family directly (not a new table family) — `QualityDimension` gains `ACCURACY`; `QualityRule._ALLOWED_COMBINATIONS` gains the rows pairing `ACCURACY` with a new `rule_parameters` shape (validated by a new `_validate_accuracy_parameters` function, following `_validate_consistency_parameters`'s exact precedent) naming: the field(s) the rule evaluates, and the Reference Evidence subject/form the comparison draws against. `QualityFindingType` gains exactly one new member: `REFERENCE_VALUE_UNSUPPORTED`.

**Persisted provenance (frozen, minimum reconstructable set)**: every persisted Accuracy `QualityEvaluation` row must make reconstructable — tenant; the exact observed `FieldValueEvidence` id; source object; source field; observed value; the exact `ReferenceEvidenceAssertion` id **and version** consulted (new FK, §I); the Reference Evidence **form** (`GOVERNED_REFERENCE_DATASET`/`HUMAN_VERIFIED_EVIDENCE`/`BUSINESS_RULE_DERIVED_VALUE`); the deriving rule id + version + evaluation id when the form is `BUSINESS_RULE_DERIVED_VALUE`; the categorical result; the evaluation timestamp; and the same deterministic uuid5 identity/idempotency basis every other OQI evaluation ledger row already uses (tenant + rule + subject + evidence + horizon, extended to also hash the pinned reference-evidence version). This reuses `QualityEvaluation`'s existing shape plus exactly one new link table, `oqi_quality_evaluation_reference_evidence` (mirrors the existing `quality_evaluation_evidence` link table precedent exactly: composite PK, FK to the evaluation and to the reference-evidence assertion+version).

**Result vocabulary**: reuses `EvaluationOutcome.SATISFIED`/`VIOLATED` exactly. No `ACCURACY_SUPPORTED`/`ACCURACY_AT_RISK`/`ACCURACY_UNKNOWN` vocabulary is introduced (explicitly rejected, matching CDD-046).

## 8. Accuracy semantic case matrix — frozen resolutions

| Case | Frozen resolution |
|---|---|
| Matching / mismatching single reference | Evaluation row persisted; `SATISFIED`/`VIOLATED` |
| SAP=USA, PLM=Mexico, Reference=USA | Independent per-observation Accuracy rows: SAP `SATISFIED`, PLM `VIOLATED`. Consistency reports its own, separate, unmodified conflict result. Neither dimension reads the other's result. |
| Sources agree, no Reference Evidence | `NOT_EVALUABLE`, zero row. `CONSISTENT ≠ ACCURATE` holds structurally — no Accuracy row can exist to be conflated with a Consistency pass. |
| Authoritative source, no Reference Evidence | `NOT_EVALUABLE`, zero row. `AUTHORITY ≠ TRUTH`. |
| Majority of sources disagrees with reference | Irrelevant to Accuracy — each observation scored independently against Reference Evidence only; majority never consulted. |
| Qualifying Reference Evidence itself conflicts | The affected observation's Accuracy evaluation is `NOT_EVALUABLE` (zero row) **and** an `OqiReferenceEvidenceConflict` governance condition is raised (§J) — never an invented precedence rule, never a silent choice. |
| Reference Evidence stale/inactive/superseded | Does not qualify. Only the current `ACTIVE` version of a `ReferenceEvidenceAssertion` for the subject may back an evaluation. This is a scope-eligibility check, not Timeliness reimplemented inside Accuracy. |
| `BUSINESS_RULE_DERIVED_VALUE` reference | Provenance pins the deriving `BusinessRule` id, version, and the exact `BusinessRuleEvaluation.evaluation_id` that produced it (§L). |
| `HUMAN_VERIFIED_EVIDENCE` reference | Requires a real, non-anonymous, distinctly-scoped steward actor (§K); never conflated with remediation authorization. |

## 9. Reasonableness — frozen operational definition

Unchanged from CDD-046 §7/§18:

```
deterministic governed contextual rule (extends OQI3's BusinessRule engine directly)
      ↓
SATISFIED | VIOLATED    (finding type on VIOLATED: CONTEXTUAL_PLAUSIBILITY_VIOLATION)
no applicable governed rule → NOT_EVALUABLE → zero persisted Reasonableness evaluation row
```

Never anomaly detection, model judgment, LLM judgment, probability, or a confidence score. An anomaly-detection model's output, if one is ever built, may exist only as advisory `ANOMALY_SIGNAL` — structurally incapable of producing a Finding. This is the already-adopted crown invariant `ANOMALY ≠ QUALITY DEFECT` (CDD-046 §41), reaffirmed unmodified (§Z).

## 10. Reasonableness — frozen rule representation and contextual applicability

`BusinessRule` (OQI3) gains exactly one new, additive, nullable-with-default column: `dimension` (a closed vocabulary — see §14 for its exact membership and legacy-default value). Its existing AST (`CONDITIONAL_REQUIRED`/`CONDITIONAL_PROHIBITED`/`FIELD_COMPARISON`), 12 operators, `ComparandKind.LITERAL|INPUT_ROLE`, three-valued Kleene evaluation, `NOT_EVALUABLE`-zero-row precedent, per-family advisory lock (seed 3), and `INSERT ... ON CONFLICT DO NOTHING` idempotency are reused **entirely unchanged** — no new evaluation mechanism is introduced. `BusinessRuleFinding` gains one new, additive, nullable-with-default field carrying the finding-type-equivalent value `CONTEXTUAL_PLAUSIBILITY_VIOLATION` for `dimension=REASONABLENESS` rows (mirroring `QualityFinding`'s existing `finding_type`-style pattern, which OQI3 has never had until now).

Contextual applicability (business-process-scoped rules — e.g. "price > 0 for commercial sales, but price may be 0 for samples") reuses the existing `CONDITIONAL_REQUIRED`/`CONDITIONAL_PROHIBITED` applicability-predicate mechanism directly, exactly as OQI3 already supports today for its existing rule families. No new mechanism, no global plausibility threshold, no per-tenant "reasonableness score."

## 11. Reasonableness semantic case matrix — frozen resolutions

| Case | Frozen resolution |
|---|---|
| Deterministic rule violated (e.g. `quantity >= 0`) | `CONTEXTUAL_PLAUSIBILITY_VIOLATION` |
| No governed rule exists (e.g. `lead_time = 400`, no rule) | `NOT_EVALUABLE`, zero row. Noetva never independently decides "that looks wrong." |
| Anomaly model flags an outlier, no governed rule | At most an `ANOMALY_SIGNAL` (advisory, non-Finding). No Reasonableness row, no Finding, ever. |
| Business-process-scoped rule (e.g. `lead_time <= 365` for process P) | Violation only when the rule's applicability predicate for P holds — reuses existing applicability mechanism. |
| Context-dependent zero value (price=0 reasonable for samples, not commercial sales) | Resolved via applicability binding to business-process context on the rule itself — never a global threshold. |

## 12. `QualityFindingOrigin` — frozen generalized Finding-origin architecture

### 12.1 The prerequisite problem, resolved (G0)

`FindingFamily` today conflates two independent facts that happened, by historical accident, to be 1:1: *which physical table* stores a Finding, and *which quality dimension* it represents. Because H2 places Accuracy findings in the same physical table as Completeness/Validity (`quality_findings`, the OQI1-shaped family) and Reasonableness findings in the same physical table as legacy business-rule findings (`business_rule_findings`, the OQI3-shaped family), the 1:1 relationship breaks for the first time. Passing the bare, unmodified `FindingFamily.OQI1` value for an Accuracy Finding to any downstream dispatch site would be — per PO-01, explicitly — "pretending Accuracy is OQI1." This is rejected.

### 12.2 Resolution: separate the two axes; generalize by value object, not by new persistence

`QualityFindingOrigin` is introduced as an immutable value object (a frozen dataclass, exactly matching the existing precedent set by `FindingReference`) — **not a new persisted table**:

```
QualityFindingOrigin (value object, not persisted):
    tenant_id: str
    finding_storage_family: FindingStorageFamily   # WHERE — closed, still exactly 3 members
    quality_dimension: QualityDimension             # WHAT — closed, now 5 members (§14)
    finding_id: UUID
    finding_state_revision: int
```

`FindingStorageFamily` is `FindingFamily`, renamed **in code identity only** — its three persisted string values (`"OQI1"`, `"OQI2"`, `"OQI3"`) are **not** changed, so every existing row, every existing column, every existing test assertion, and every existing frontend label continues to work unmodified. The rename exists only to state plainly, in the type system, what this vocabulary has always actually meant (physical-table selector), so it is never again mistaken for a semantic-dimension tag. `FindingStorageFamily` gains **zero new members** in H2, because H2 introduces no new physical Finding table — Accuracy reuses `quality_findings` (storage family value unchanged: `OQI1`), Reasonableness reuses `business_rule_findings` (storage family value unchanged: `OQI3`).

`quality_dimension` is **derived, never redundantly persisted**, because it is already safely and immutably reconstructable at read time: for OQI1-shaped rows (including Accuracy), via the existing static `finding_type → dimension` mapping already implicit in `QualityFindingType` (`MISSING_VALUE→COMPLETENESS`, `{ENUM_VIOLATION,FORMAT_VIOLATION,RANGE_VIOLATION}→VALIDITY`, and now `REFERENCE_VALUE_UNSUPPORTED→ACCURACY`); for OQI2-shaped rows, it is the constant `CONSISTENCY`; for OQI3-shaped rows (including Reasonableness), via the new `BusinessRule.dimension` column (§10/§14), joined through the same immutable, append-only evaluation ledger every other provenance fact in this system already relies on. Persisting a redundant copy was considered and rejected: it would either drift from the immutable source of truth or require a second write path with its own consistency risk, for a value that costs one already-necessary join to obtain. *(H2-I confirmation item, not a design gap: confirm whether `quality_findings` already carries its own `finding_type` column directly — believed yes, per existing `QualityFinding`/`QualityFindingType` architecture — or requires one join through `quality_evaluations`; either way the derivation is correct and requires no new column on `quality_findings` itself.)*

### 12.3 Where `QualityFindingOrigin` replaces the bare `(FindingFamily, finding_id)` pair

Exactly the four hardcoded dispatch sites discovery identified are generalized to construct and consume `QualityFindingOrigin` instead of a bare `FindingFamily`:

1. **OQI4** `OqiOntologyImpactEvaluationRepositoryImpl.resolve_finding_subject` — physical-row fetch continues to dispatch on `finding_storage_family` alone (unchanged 3-branch shape; OQI4's propagation logic needs *where*, not *why*), and additionally resolves and returns `quality_dimension` as part of the already-read row (a one-field addition to an existing lookup, not a new query).
2. **OQI5** `OqiRemediationService._get_finding_state` / `OqiRemediationAgentService._get_finding_state` (both copies) — physical-row fetch: unchanged 3-branch dispatch on `finding_storage_family`. **`extract_candidates` is genuinely upgraded**: it must dispatch first on `quality_dimension`, not merely on `finding_storage_family`, because Accuracy and Reasonableness require materially different candidate-extraction logic than the OQI1/OQI3 findings that happen to share their storage table (§S).
3. **OQI6** `OqiBusinessImpactRepositoryImpl.compute_subject_finding_state` — **requires no code change** for Reliance's "any open Finding" fact: its existing per-storage-family `SELECT`s already enumerate every row in `quality_findings`/`business_rule_findings` by tenant/subject/status, with no dimension filter — an `OPEN` Accuracy or Reasonableness row is therefore already picked up by the existing OQI1/OQI3 selects with zero modification. This is confirmed, not assumed (H2-DR's open verification item is resolved: `any_open_finding` is storage-family-scoped, not dimension-scoped).
4. **OQI7 (product experience)** `_resolve_finding`/`list_findings` — physical-row fetch: unchanged. The `family` query-parameter/response field remains the existing unconstrained `str` (no Pydantic `Literal`, confirmed — additive by construction, §V); a `dimension` field is added to the response schema so a caller can distinguish an Accuracy Finding from a Completeness/Validity Finding sharing the same `family=OQI1` label, closing the exact provenance gap PO-01 forbids leaving open.

### 12.4 Answering the eleven G0 questions explicitly

1. Today `FindingFamily` means, in practice, "physical storage table selector" — never anything else, at every real dispatch site.
2. It is a mixture in name only; in behavior it is purely (b) physical-table-family / evaluator-family (the two happen to coincide today).
3. `RemediationCandidateBasis` today means an opaque, write-once explanatory label — a mixture of family and dimension baked into one string, consumed by zero dispatch logic anywhere.
4. Four services dispatch on `FindingFamily`/basis; none dispatch on `QualityDimension` today (§4).
5-6. Physical-table knowledge is needed by all four dispatch sites (row fetch). Semantic quality-dimension knowledge is needed only where extraction/remediation *logic* differs by dimension — concretely, `extract_candidates` (§12.3.2).
7. Yes — `QualityFindingOrigin`'s three fields (`finding_storage_family`, `quality_dimension`, `finding_id`) are independently populated and independently readable.
8. Yes, losslessly — see backward-compatibility mapping (§13).
9. Yes — `quality_dimension=ACCURACY`/`REASONABLENESS` is structurally distinct from `COMPLETENESS`/`VALIDITY`/`LEGACY_UNCLASSIFIED_BUSINESS_RULE` even where `finding_storage_family` is shared.
10. Yes — a future dimension reusing an existing physical table needs only a new `QualityDimension` member (already-proven-safe, additive, §4); a future dimension requiring a genuinely new physical table needs exactly one new `FindingStorageFamily` member and one new branch at each of the same four, now-isolated, dispatch sites — the same bounded cost H2 itself pays, never worse, never another taxonomy redesign.
11. No — `RemediationCandidateBasis` needs no *architecture* change (its shape already tolerates dimension-named members); it needs exactly two new additive members (§S).
12. Yes, directly — remediation dispatch consumes `quality_dimension` from `QualityFindingOrigin` with no further translation.
13. No — ontology-impact dispatch needs only `finding_storage_family` (§12.3.1); it does not need the dimension axis for its own propagation logic.
14-15. No backfill of any kind is required for `quality_findings`/`quality_comparison_findings`/`business_rule_findings`'s existing `FindingFamily`-shaped columns — their persisted values do not change. The only new columns (`business_rules.dimension`, `business_rule_findings`'s new finding-type-equivalent field) are additive with a safe, honest legacy default (§13/§14) — no `UPDATE` statement against existing rows is required at all.

This resolves G0. **This is, in effect, the minimum coherent slice of the previously-deferred `QualityFindingOrigin` generalization** — named explicitly as such, scoped exactly to what H2 requires (two new dimensions, zero new physical tables), and structurally ready for the four still-deferred dimensions without requiring another redesign.

## 13. Backward compatibility — frozen mapping

| Existing Finding | `finding_storage_family` | `quality_dimension` |
|---|---|---|
| OQI1 Completeness/Validity Finding | `OQI1` (unchanged) | `COMPLETENESS` or `VALIDITY`, already stored today via `QualityRule.dimension`/`finding_type` — unchanged |
| OQI2 Consistency Finding | `OQI2` (unchanged) | `CONSISTENCY` — constant, unchanged |
| OQI3 legacy Business Rule Finding | `OQI3` (unchanged) | `LEGACY_UNCLASSIFIED_BUSINESS_RULE` — new, honest, non-fabricated default (§14) |

No historical Finding's `finding_family`/storage-table value, identity, status, or any existing crown-invariant-tested behavior changes. `LEGACY_UNCLASSIFIED_BUSINESS_RULE` is the frozen, safe treatment for the fact that no `BusinessRule` created before this document existed carries real dimension information — this document does not, and forbids implementation from, retroactively asserting that any pre-H2 business rule was secretly a Reasonableness rule.

## 14. `QualityDimension` and `BusinessRule.dimension` — frozen vocabulary

```python
class QualityDimension(StrEnum):
    COMPLETENESS = "COMPLETENESS"   # unchanged
    VALIDITY = "VALIDITY"           # unchanged
    CONSISTENCY = "CONSISTENCY"     # unchanged
    ACCURACY = "ACCURACY"           # new
    REASONABLENESS = "REASONABLENESS"  # new
```
`_ALLOWED_COMBINATIONS` gains the rows required for `ACCURACY`'s new `rule_parameters` shape (§7). No row is added for `REASONABLENESS`, because Reasonableness is not `QualityRule`-shaped — it is `BusinessRule`-shaped (§10).

```python
class BusinessRulePurpose(StrEnum):   # new column: business_rules.dimension
    LEGACY_UNCLASSIFIED_BUSINESS_RULE = "LEGACY_UNCLASSIFIED_BUSINESS_RULE"  # default for pre-H2 rows
    REASONABLENESS = "REASONABLENESS"
    ACCURACY_REFERENCE_DERIVATION = "ACCURACY_REFERENCE_DERIVATION"
```
A single `BusinessRule` version carries exactly one purpose (§16, circular-proof prevention — a rule may never simultaneously serve as both a Reasonableness plausibility check and an Accuracy reference-deriving rule). `UNIQUENESS`/`TIMELINESS`/`INTEGRITY`/`CONFORMITY` are not added to either vocabulary in H2 (explicitly deferred, §AA).

## 15. Reference Evidence — frozen persistence architecture

Frozen exactly as H2-DR recommended and validated fresh against current code: a shared, tenant-owned **envelope** table plus three normalized, per-form **child** tables — never opaque JSONB, never one wide nullable table, never three unrelated tables with no shared governance envelope. This matches the repository's consistently-applied normalization discipline (`QualityCoveragePolicy`'s own parent+dimension-child shape is the closest direct precedent) and its `CheckConstraint`-over-native-`ENUM` convention (§4).

```
oqi_reference_evidence_assertions           (envelope — one row per governed subject-claim version)
    assertion_id            UUID PK (deterministic uuid5, mirrors QualityRule's pattern)
    tenant_id                str, indexed
    ontology_element_type    ENTITY | RELATIONSHIP           (reuses OntologyElementType verbatim)
    ontology_element_id      UUID
    source_field_id          UUID, FK — the specific field this assertion claims a value for
    form                     GOVERNED_REFERENCE_DATASET | HUMAN_VERIFIED_EVIDENCE | BUSINESS_RULE_DERIVED_VALUE
    status                   ACTIVE | RETIRED                (no DRAFT — mirrors QualityRule/BusinessRule/QualityCoveragePolicy)
    version_number            int
    previous_version_id       UUID, self-FK
    asserted_value             str  (the claimed correct value, denormalized here for uniform read access)
    created_by / created_on

oqi_governed_reference_dataset_entries      (child — form = GOVERNED_REFERENCE_DATASET)
    assertion_id              UUID, FK + PK (1:1 with envelope row)
    dataset_name               str          (e.g. "ISO-3166-1-ALPHA-3")
    dataset_version              str
    entry_key                    str         (the lookup key the dataset resolves)
    dataset_owner               SHARED_PLATFORM   (frozen constant — PO-02; no tenant-owned dataset form in H2)

oqi_human_verified_evidence_entries         (child — form = HUMAN_VERIFIED_EVIDENCE)
    assertion_id                UUID, FK + PK
    verifying_actor_id           str   (real, non-anonymous steward principal — never an agent, never a rule author)
    verification_timestamp
    verification_rationale       str   (structured minimum: a reason field, required, never optional free text only)
    revoked_at                    timestamptz, nullable       (revocation supersedes, never deletes — §U)

oqi_business_rule_derived_reference_entries (child — form = BUSINESS_RULE_DERIVED_VALUE)
    assertion_id                 UUID, FK + PK
    deriving_business_rule_id     UUID, FK
    deriving_rule_version           int
    deriving_evaluation_id          UUID, FK — the exact immutable BusinessRuleEvaluation row that produced this value
```

**Binding constraints**: exactly one ACTIVE `oqi_reference_evidence_assertions` row per `(tenant_id, ontology_element_type, ontology_element_id, source_field_id)` **per form** — a DB-enforced partial unique index, mirroring `QualityCoveragePolicy`'s `uq_...one_active` pattern exactly (multiple forms may each hold their own ACTIVE assertion for the same subject simultaneously — this is what makes reference-evidence conflict detection meaningful, §16). Every child table's PK is its `assertion_id` (1:1, not 1:N) — the envelope carries identity/lifecycle/tenancy uniformly; the child carries only what is genuinely form-specific. No fourth form is authorized without a future governance amendment.

## 16. Reference Evidence conflict — frozen `OqiReferenceEvidenceConflict` architecture

Following this repository's `Oqi<Noun>` naming discipline (mirrors `OqiRemediationCase`, `OqiBusinessDependency`): **`OqiReferenceEvidenceConflict`**, table `oqi_reference_evidence_conflicts`. **Persisted, mutable current-state** (mirrors `CurrentOntologyImpact`'s `ACTIVE`/`RESOLVED` lifecycle pattern) — not derived on read, because a steward needs a stable, followable governance item ("this conflict was first flagged 3 days ago, still open"), not a value recomputed fresh on every query.

```
oqi_reference_evidence_conflicts
    conflict_id            UUID PK (deterministic uuid5 over tenant + subject + the sorted conflicting assertion ids)
    tenant_id
    ontology_element_type / ontology_element_id / source_field_id   (the shared subject in tension)
    conflicting_assertion_ids   list[UUID]  (≥2 ACTIVE oqi_reference_evidence_assertions rows that disagree)
    status                    ACTIVE | RESOLVED
    first_detected_at
    last_observed_at
```

**It is explicitly NOT a Quality Finding.** It carries no `QualityFindingOrigin`, no `FindingStorageFamily`, no `QualityDimension`, and must never be labeled `REFERENCE_VALUE_UNSUPPORTED` — doing so would misrepresent "Noetva currently lacks a defensible reference basis" as "this specific observed enterprise value is wrong," which is a different and unsupported claim. It is a governance condition about the evidence layer itself, surfaced separately (via its own read path, §V) for steward attention.

**Resolution semantics**: a conflict is `RESOLVED` only by a genuine governed change — one of the conflicting assertions being superseded by a new `ACTIVE` version (§U) that removes the disagreement, or explicit retirement of one of the conflicting assertions by the authority that owns its form (§K/§L). There is no "pick one" action; no actor authority short of creating a new governed version may resolve a conflict.

**Effect on Reliance (frozen, minimal)**: a conflict does **not** feed `derive_reliance_state`'s three booleans directly — no fourth boolean, no new Reliance state. It only ever manifests to Reliance indirectly: the affected observation's Accuracy evaluation is `NOT_EVALUABLE` (zero row, §8), so required Accuracy coverage for that subject remains absent, which may (via the already-frozen H1 coverage mechanism, §R) cause Reliance to read `RELIANCE_UNKNOWN`. No new invariant is required beyond the ones already frozen.

## 17. Human verification authority — frozen (`HUMAN_VERIFIED_EVIDENCE`)

Per PO-03: distinct verification-authority scope, `oqi-reference-evidence:verify` (§T), never satisfiable by `oqi-reference-evidence:configure`, `oqi-remediation:authorize`, or `oqi-remediation:report-execution`. Preserved: `CONFIGURATION AUTHORITY ≠ VERIFICATION AUTHORITY`, `VERIFICATION AUTHORITY ≠ REMEDIATION AUTHORITY`. `verifying_actor_id` must resolve to a real human principal (never an agent principal, never the rule-authoring principal by construction — enforced by requiring the `oqi-reference-evidence:verify` scope, distinct from any agent-service or rule-configuration credential). Human verification is governed evidence, not absolute truth — a `HUMAN_VERIFIED_EVIDENCE` assertion participates in Accuracy comparisons exactly like the other two forms; it does not bypass the `NOT_EVALUABLE`/conflict machinery.

## 18. Business-rule-derived reference — frozen (`BUSINESS_RULE_DERIVED_VALUE`)

Pins, without exception: the exact `BusinessRule` id and version (`purpose=ACCURACY_REFERENCE_DERIVATION`, §14); the exact bound input evidence that rule consumed; the exact, deterministic `BusinessRuleEvaluation.evaluation_id` (already immutable/append-only) that produced the derived value; and the derivation context (subject). No probabilistic or LLM-produced value may ever back this form — enforced structurally by the fact that `BusinessRuleEvaluation` rows are only ever produced by `OqiBusinessRuleEvaluationService`'s deterministic AST evaluator, never by any agent/model service.

## 19. Circular-proof prevention — frozen crown invariant

**`QUALITY CONCLUSION ≠ REFERENCE EVIDENCE`.**

Normative meaning: an OQI evaluation, Finding, ontology-impact result, business-impact result, Reliance result, agent recommendation, or remediation conclusion may never recursively become the governed evidence used to prove its own (or any other) quality conclusion.

Structural enforcement, frozen:
1. A single `BusinessRule` version carries exactly one `purpose` (§14) — never simultaneously `REASONABLENESS` and `ACCURACY_REFERENCE_DERIVATION`.
2. `BusinessRuleInputBinding` — preserved, unchanged — resolves only against raw `FieldValueEvidence`-backed inputs. This document adds an explicit, binding prohibition (not merely a convention): a rule input binding must never resolve against another evaluation's or Finding's output, an Accuracy/Reasonableness result, a Reliance result, an ontology-impact result, or an agent recommendation — enforced by application-level validation at rule activation time (rejecting any binding whose target is not a raw evidence-backed field) and proved by a dedicated crown test (`CY1`–`CY6`, §Y).
3. Reference Evidence of form `BUSINESS_RULE_DERIVED_VALUE` may only be produced by a `purpose=ACCURACY_REFERENCE_DERIVATION` rule, and that rule's own inputs are subject to the same raw-evidence-only restriction — so an Accuracy result can never, even transitively, become the evidence that proves itself.
4. Agent output, Reliance results, and remediation conclusions are, by pre-existing and unmodified architecture (`AGENT ≠ FACT`), structurally incapable of writing to any Reference Evidence table — this document does not grant any new write path from those subsystems into `oqi_reference_evidence_assertions` or its children.

## 20. Finding types — frozen

```
ACCURACY:        REFERENCE_VALUE_UNSUPPORTED
REASONABLENESS:  CONTEXTUAL_PLAUSIBILITY_VIOLATION
```
No aliases. No numeric severity/confidence substituting for evidence. Every Finding of either type is reconstructable through `QualityFindingOrigin` (§12).

## 21. OQI4 ontology-impact integration — frozen

Accuracy/Reasonableness Findings enter ontology-impact evaluation through the **same** `evaluate_current_state`/`evaluate_historical` entry points as every other Finding, called with `(tenant_id, finding_storage_family, finding_id)` exactly as today — `finding_storage_family` for Accuracy is `OQI1`, for Reasonableness is `OQI3` (§12.2), which is correct and sufficient because OQI4's own logic needs only physical-row location, never semantic dimension (§12.4, Q13). No masquerading occurs because `finding_storage_family` genuinely, honestly describes physical location — it is `quality_dimension` (never read by OQI4) that carries the semantic claim, and that value is never asserted to be COMPLETENESS/VALIDITY/legacy-business-rule for these Findings anywhere downstream that reads it. `IMPACTED`/`NO_IMPACT`/`IMPACT_UNKNOWN` are unchanged, unexpanded; impact is never invented merely because a Finding exists.

## 22. OQI6 business-impact + Reliance integration — frozen

Business-impact evaluation is unmodified — it consumes only the OQI4 `CurrentOntologyImpact` projection and never touches `FindingFamily`/`FindingStorageFamily` directly; it requires zero changes. Reliance's "any open Finding" fact requires zero code changes for the reasons proven in §12.3.3. Reliance itself remains exactly `RELIANCE_SUPPORTED`/`RELIANCE_AT_RISK`/`RELIANCE_UNKNOWN` — no score, no fourth state. `derive_reliance_state` is unmodified.

## 23. H1 coverage integration — frozen

The single, narrow, already-identified extension point: `OqiQualityCoveragePolicyRepositoryImpl.has_qualifying_coverage_for_dimension` gains exactly two new branches — `ACCURACY` and `REASONABLENESS` — each an existence-only query for a real, persisted, qualifying evaluation row (mirroring the `COMPLETENESS`/`VALIDITY`/`CONSISTENCY` branches' exact shape). `CoverageDimension` requires zero changes (already has all nine members, H1). Never synthesized from rule existence, reference existence, policy requirement, evaluator-code existence, or absence of a Finding. `PARTIAL REQUIRED COVERAGE ≠ SUPPORTED` and `NO FINDINGS ≠ TRUSTED` are reaffirmed unmodified.

## 24. OQI5 remediation integration — frozen (minimum necessary, no autonomy)

`RemediationCandidateBasis` gains exactly two new, purely additive members (zero dispatch sites depend on the existing four today, §4, so this is genuinely zero-risk): `ACCURACY_REFERENCE_EVIDENCE`, `REASONABLENESS_CONTEXTUAL_RULE`. `extract_candidates` is upgraded to dispatch first on `quality_dimension` (§12.3.2):

- **Accuracy** (`REFERENCE_VALUE_UNSUPPORTED`): a `RemediationCandidate` proposing `UPDATE_FIELD` on the affected observation's source object/field, with the proposed value equal to the (non-conflicting, by construction — conflicting reference evidence never produces this Finding type, §16) supporting Reference Evidence's asserted value. This mirrors OQI2's existing cross-source candidate-extraction precedent structurally (propose correcting a value toward governed evidence) and reuses the existing `UPDATE_FIELD` action type — no new action type introduced.
- **Reasonableness** (`CONTEXTUAL_PLAUSIBILITY_VIOLATION`): a `RemediationCase`/`basis` is created (so the Finding is genuinely visible to and reachable by the governed remediation subsystem, satisfying PO-01's "participate natively" requirement at the case level), but candidate *value* proposals are not fabricated — a Reasonableness violation does not, in general, carry a derivable single correct value. `extract_candidates` may legitimately return zero corrective candidates for these findings pending steward investigation — an already-legitimate, existing outcome shape (OQI3's extraction can already return no candidates), not a new action type or new autonomy.

Preserved, unmodified: `RECOMMENDATION ≠ AUTHORIZATION`, `AUTHORIZATION ≠ REMEDIATION`, `REMEDIATION ≠ RESOLUTION`. Fresh evidence and a fresh, independent re-evaluation remain required for `RESOLVED` — nothing in this document creates any automatic resolution path. No autonomous remediation is introduced.

## 25. Tenant + authority model — frozen

`ReferenceEvidenceAssertion`: tenant-owned (mirrors `QualityCoveragePolicy`/`ImpactPropagationPolicy`/`BusinessDependency` pattern exactly) — a tenant's assertion may reference a shared-platform `GOVERNED_REFERENCE_DATASET` (PO-02) but never define one. `BusinessRule.dimension`/`purpose`: no tenant-model change (`BusinessRule` is already tenant-owned). `QualityRule` dimension expansion: no tenant-model change (`QualityRule` remains shared platform structure, per the CDD-046 erratum, unaffected). `OqiReferenceEvidenceConflict`: tenant-owned (derived from tenant-owned assertions).

## 26. Authority scopes — frozen naming (§T detail)

Following this repository's confirmed convention (`<domain-slug>:<verb>`, a new domain-slug per distinct authority boundary, mirroring the `oqi` / `oqi-remediation` split and the `governed-approval:request`/`governed-approval:decide` same-domain-different-verb non-substitutability pattern):

| Capability | Scope | Status in H2 |
|---|---|---|
| (A) Reference-evidence configuration | `oqi-reference-evidence:configure` | New — must be genuinely wired in H2-I (Python `authorize(...)` call site **and** `keycloak/ctec-realm.json` entry) before any claim of enforcement, unlike the `oqi-coverage:configure` cautionary precedent (§4) |
| (B) Human verification | `oqi-reference-evidence:verify` | New — same-domain, distinct-verb, non-substitutable with (A) per the `governed-approval` precedent; must be genuinely wired in H2-I |
| (C) Quality-rule / business-rule configuration | `oqi-quality-rule:configure` | Named for forward reference only. **Not exposed via any API route in H2** (§V) — explicitly documented as unenforced, exactly like `oqi-coverage:configure` today, and explicitly disclosed as such so it is never mistaken for a live control |
| (D) Remediation authorization | `oqi-remediation:authorize` (existing, unchanged) | Reused as-is — remediation authority does not vary by quality dimension |
| (E) Remediation execution reporting | `oqi-remediation:report-execution` (existing, unchanged) | Reused as-is |

`CONFIGURATION AUTHORITY ≠ VERIFICATION AUTHORITY`, `VERIFICATION AUTHORITY ≠ REMEDIATION AUTHORITY`, `CONFIGURATION AUTHORITY ≠ REMEDIATION AUTHORITY` are all structurally preserved — no code path may accept scope (A), (D), or (E) as satisfying (B), and vice versa. No scope in this table is claimed enforced by this document itself (this document authorizes no implementation); H2-I's Artifact Authorization test matrix (§Y, `A12`) binds H2-I to prove genuine end-to-end enforcement for (A) and (B) before H2 may be considered complete.

## 27. Versioning + immutability — frozen

`ReferenceEvidenceAssertion`: `ACTIVE`/`RETIRED`, `version_number`/`previous_version_id`, DB-enforced at-most-one-`ACTIVE`-per-`(subject, form)` partial unique index — identical structural discipline to `QualityRule`/`BusinessRule`/`QualityCoveragePolicy`. Human-verification revocation (`revoked_at`) never rewrites a historical evaluation: revocation creates a new evidence state (the assertion's `RETIRED`, or a new version reflecting the correction); any evaluation that already ran against the prior `ACTIVE` version remains, permanently, an honest historical record of "what was supportable under the governed evidence available at that evaluation's time" — never eternal truth, never silently invalidated or rewritten. Future re-evaluation (triggered per §W's deterministic-invocation precedent, not automatically) is the only mechanism by which a changed reference is reflected in a new evaluation result.

## 28. Migrations — frozen sequence (no migration files created in this phase)

Current head: `0027_h1_coverage_policy`. Three migrations, one concern each, matching this repository's established one-migration-per-concern discipline and its `sa.String` + `sa.CheckConstraint` (never native `ENUM`) convention for every new closed-vocabulary column:

```
0028_oqi_h2_reference_evidence         down_revision = 0027_h1_coverage_policy
    creates: oqi_reference_evidence_assertions, oqi_governed_reference_dataset_entries,
             oqi_human_verified_evidence_entries, oqi_business_rule_derived_reference_entries,
             oqi_reference_evidence_conflicts
    (revision id: 24 chars — within margin of VARCHAR(32))

0029_oqi_h2_accuracy_dimension         down_revision = 0028_oqi_h2_reference_evidence
    alters: QualityDimension-backed columns require no DB change (plain String, no CHECK today,
            §4) — this migration adds the one new link table,
            oqi_quality_evaluation_reference_evidence, plus the new
            ck_quality_findings_finding_type-equivalent CheckConstraint additions if any exist
            at implementation time (verify at H2-I; add only if a CHECK already exists to extend)
    (revision id: 26 chars)

0030_oqi_h2_reasonableness_dimension   down_revision = 0029_oqi_h2_accuracy_dimension
    alters: business_rules ADD COLUMN dimension (nullable, server_default
            'LEGACY_UNCLASSIFIED_BUSINESS_RULE'); business_rule_findings ADD COLUMN
            finding_type-equivalent (nullable, server_default matching the same legacy value)
    (revision id: 26 chars)
```

No migration authored in this phase. All three are additive; none require a data-backfill `UPDATE` statement (server defaults cover every existing row). Post-H2 table count: pre-H2 count (102) + 5 new tables from `0028` = **107**; `0029`/`0030` add zero new tables (link table in `0029` is +1, so **108** after `0029`; `0030` adds zero tables). **Governance process for the CI table-count literal (frozen, following the established, disclosed precedent — §4/§X):** the mechanical `[ "$count" -eq 102 ]` re-pin in `.github/workflows/ci.yml` must be updated to the freshly-verified post-`0030` count as a **separate, disclosed companion amendment** — never folded into the implementation commit — following exactly the `OQI-H1-CI`/`OQI-H1-I-R1` precedent this document cites as binding process, not merely as prior art.

## 29. API + frontend scope — frozen (minimal)

Backend/domain/persistence/service correctness first, per default. API changes are authorized **only** where required for genuine authority enforcement or downstream compatibility:

- **MUST**: a minimal API surface for reference-evidence configuration (scope A) and human verification (scope B) — without it, `HUMAN_VERIFIED_EVIDENCE` and tenant-scoped `GOVERNED_REFERENCE_DATASET` assertions could never be created by a real steward, and PO-03 would be unenforceable in practice.
- **MUST**: `finding_family` response fields on the existing `/api/v1/oqi/findings*` surface gain a sibling `dimension` field (plain `str`, additive, no schema-breaking change — §12.3.4) so a caller can distinguish an Accuracy Finding from a Completeness/Validity Finding sharing `family=OQI1`.
- **MUST**: a minimal read path for `OqiReferenceEvidenceConflict` rows (steward-facing; conflicts must be discoverable, §16) — read-only, gated by `oqi:read` (no new read scope required, mirrors existing OQI read-scope precedent).
- **DEFER**: any OQI Command Center redesign; any Reference Evidence authoring UI; any Reasonableness-rule-authoring UI; the frontend family dropdown (`findings/page.tsx`) needs no new option (Accuracy/Reasonableness findings surface under the existing `OQI1`/`OQI3` filter values with the new `dimension` field distinguishing them) — a cosmetic label/finding-type-display update is optional and explicitly deferred, not required for correctness. If the frontend cannot yet faithfully distinguish an Accuracy Finding from a Completeness/Validity one in its UI, that is recorded as deferred UX work (§AA), not silently presented as already-handled.

## 30. Demo-seeder design — frozen

Following OQI2's (not OQI1's/OQI3's) existing, correct precedent of actually invoking the evaluator rather than only seeding evidence:

```
raw evidence:  SAP Manufacturing Country = USA
               PLM Manufacturing Country = Mexico
governed Reference Evidence: GOVERNED_REFERENCE_DATASET assertion, value = USA

→ OQI2 evaluator runs (unchanged): Consistency conflict
→ OQI-H2 Accuracy evaluator runs: SAP SATISFIED, PLM VIOLATED → REFERENCE_VALUE_UNSUPPORTED
→ generalized origin permits: Accuracy Finding → OQI4 ontology impact → OQI6 business impact → Reliance

separately: raw evidence (e.g. Quantity = -10) + a governed REASONABLENESS BusinessRule (quantity >= 0)
→ OQI-H2 Reasonableness evaluator runs → CONTEXTUAL_PLAUSIBILITY_VIOLATION
```

No terminal Finding/Impact/Reliance row is ever seeded directly — every derived row is produced by actually invoking the corresponding evaluator/service against seeded raw evidence and rule/reference-evidence configuration, exactly as the frozen crown-proof discipline requires.

## 31. Test / crown matrix — frozen (binding on H2-I)

The complete A1–A13, R1–R10, F1–F10, RC1–RC5, CY1–CY6, C1–C11 matrix specified for this phase is adopted in full and is binding on H2-I's test suite. Representative structural precedents already exist for every layer (domain, service/algorithm, real-Postgres repository, tenant isolation, migration round-trip, crown/invariant) in `test_oqi_h1_reliance_coverage_crown.py` and the OQI1/OQI2/OQI3 test families identified during discovery. A new sibling suite, `test_oqi_h2_accuracy_reasonableness_crown.py`, is the required home for `C1`–`C11` and the cross-cutting `F`/`RC`/`CY` proofs; per-dimension `A`/`R` proofs follow the existing per-evaluator test-file precedent (service-level Kleene-matrix style, real-Postgres NOT_EVALUABLE-zero-row style, tenant-isolation style).

## 32. Docker / runtime quality gate — frozen (binding on H2-I/H2-VM)

At minimum: format/lint/typecheck; targeted H2 tests; full backend regression; real-PostgreSQL H2 crown tests; migration upgrade/downgrade/re-upgrade round-trip across all three new migrations; table-count verification (post-`0030` = 108, §28, applied as a disclosed companion amendment to CI, §4); tenant-isolation proof; authorization proof for scopes (A)/(B) with genuine end-to-end enforcement (Python + Keycloak realm entry, §26); backend Docker build (a full repull/rebuild is expected post-cleanup and is not a defect); fresh compose runtime; PostgreSQL/Keycloak/backend health; bootstrap success; migration-head-inside-Docker check (dynamic, unchanged mechanism); deterministic demo seeder producing real Accuracy and Reasonableness derivations (§30, never fabricated terminal state); generalized-origin flow proof through OQI4/OQI6 (and OQI5 candidate provenance where applicable); clean-candidate verification.

## 33. Crown invariants — frozen (reaffirmed + newly adopted)

```
VALID ≠ ACCURATE                                    (reaffirmed, unmodified)
CONSISTENT ≠ ACCURATE                                (reaffirmed, unmodified)
CANONICAL ≠ ACCURATE                                 (reaffirmed, unmodified)
AUTHORITY ≠ TRUTH                                    (reaffirmed, unmodified)
MAJORITY ≠ TRUTH                                     (reaffirmed, unmodified)
ANOMALY ≠ QUALITY DEFECT                             (reaffirmed, unmodified)
NO FINDINGS ≠ TRUSTED                                (reaffirmed, unmodified)
PARTIAL REQUIRED COVERAGE ≠ SUPPORTED                (reaffirmed, unmodified)
CONFIGURATION AUTHORITY ≠ VERIFICATION AUTHORITY      (new, §26)
VERIFICATION AUTHORITY ≠ REMEDIATION AUTHORITY        (new, §26)
QUALITY CONCLUSION ≠ REFERENCE EVIDENCE               (new, §19)
```
None of the eight reaffirmed invariants required any design change to remain true under this document's architecture.

## AA. Explicit deferred scope

`QualityFindingOrigin`-as-a-persisted-table (rejected in favor of a value object, §12.2, and not reconsidered without new evidence that derivation-on-read is insufficient); tenant-private `GOVERNED_REFERENCE_DATASET`s (PO-02); Uniqueness, Timeliness, Integrity, Conformity evaluators and their `FindingStorageFamily`/`QualityDimension` implications; any OQI Command Center or Reference-Evidence-authoring frontend beyond the minimal read/write surface named in §29; production evaluator orchestration/scheduling/eventing for any OQI family (PO-04, recorded as P1 platform debt, §AB); `oqi-quality-rule:configure` enforcement (named, not wired); autonomous remediation of any kind; numeric confidence, statistical, or model-derived quality conclusions anywhere in OQI.

## AB. STOP conditions encountered

None. Specifically checked and confirmed clear: `origin/main` unchanged from the declared baseline throughout; no unauthorized mutation occurred; no subagent wrote to the repository; CDD-046/CDD-047 governance integrity intact and unmodified by this document; `AUTHORITY ≠ TRUTH` and `CONSISTENT ≠ ACCURATE` are preserved, not weakened (§6, §8); majority-as-truth is nowhere introduced (§8); Accuracy requires no numeric confidence (§6/§7); Reasonableness requires no probabilistic/model-generated Finding (§9); the reference-conflict resolution invents no precedence (§16); tenant isolation is preserved for every new object (§25); no historical provenance is rewritten (§27); the generalized Finding origin represents every existing OQI1/OQI2/OQI3 Finding losslessly (§13); OQI4/OQI5 integration requires no lossy semantic mapping (§21/§24); the circular-proof invariant is structurally enforced, not merely documented (§19); implementation scope is bounded by the paired Artifact Authorization (below); every semantic decision in this document is exact, not deferred to implementation judgment.

## AC. Acceptance criteria (binding)

This freeze is acceptable only if H2-I: (1) introduces zero new `FindingStorageFamily` members; (2) never persists a `quality_dimension` value for a legacy OQI3 Finding other than `LEGACY_UNCLASSIFIED_BUSINESS_RULE` without independently verified evidence that a specific rule's true historical purpose is knowable (which this document asserts it is not); (3) never claims `oqi-reference-evidence:configure`/`:verify` are enforced without both a live `authorize(...)` call site and a live `keycloak/ctec-realm.json` entry; (4) introduces no numeric confidence, score, or probability anywhere in the Accuracy/Reasonableness/conflict/remediation-candidate path; (5) proves the full crown/test matrix (§31) against real PostgreSQL before any claim of completion; (6) touches no path outside the paired Artifact Authorization's exact enumeration.

## AD. Authorization

This document is approved for publication under OQI-H2-G, incorporating Product Owner decisions PO-01 through PO-04 (§3). CDD-046 and CDD-047 (both documents and both migration-head amendments) remain frozen and unmodified. Implementation is authorized only via `CDD-048-OQI-H2-Governed-Accuracy-Reasonableness-Reference-Evidence-and-Generalized-Finding-Origin-Artifact-Authorization.md`.
