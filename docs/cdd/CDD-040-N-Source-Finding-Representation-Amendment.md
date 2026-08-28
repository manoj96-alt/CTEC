# CDD-040 N-Source Finding Representation Amendment

**Status:** APPROVED ARCHITECTURE AMENDMENT
**Version:** 1.0
**Amends:** CDD-040 §14, §27–§33, §37, §42, §52 (Finding taxonomy, Finding schema, Finding identity coexistence with observation semantics) — narrowly, without reopening correspondence, concurrency, DB provenance integrity, the epistemic 4a/4b resolution, Evaluation identity, participant-keyed digest, or any firewall, all of which remain frozen exactly as written
**Precedent:** this repository's established discipline of never modifying a frozen governance artifact in place — published as a companion, exactly as CDD-039-GR/GC/GM and CDD-040's own two prior corrections were
**Governed by:** OQI2-VN (adversarial discovery) and OQI2-RN (architecture resolution), both Product-Owner-approved

## 1. Why this amendment exists

OQI2-VN proved that

```
A = ABC123, B = ABC123, C = ABC123, D = XYZ999, E = MISSING
```

establishes **two** deterministic quality facts simultaneously — a value conflict among A/B/C/D and a missing-participant condition for E — while CDD-040's frozen single-valued `finding_type` model can expose only one. Direct code inspection confirmed the root cause: the evaluation algorithm returns immediately upon detecting missingness, before the conflict computation over known values is ever reached. This is **not** evidence that PR #166 was implemented incorrectly against CDD-040 as originally frozen — CDD-040 itself never required simultaneous dual-classification, because that requirement did not exist until Product Owner articulated the explicit N-source principles resolved in OQI2-RN. This amendment closes that governance gap.

## 2. Authoritative semantic separation (frozen)

```
QualityComparisonFinding
  Meaning: the continuing current-state lineage of one governed quality
  condition for one comparison subject. Answers only: is this condition
  currently satisfied or violated, and since when?
  Owns: OPEN/RESOLVED lifecycle, state_revision, occurrence_count,
  reopen_count, first_seen_at, last_seen_at, latest_evaluation_id.
  Does NOT own a single failure classification.

QualityComparisonEvaluation
  Meaning: one immutable deterministic evaluation of the governed
  condition over one governed participant/evidence state. Unchanged from
  CDD-040 except for the additive relationship in §5 below.
  Owns: SATISFIED/VIOLATED outcome, rule_version, correspondence_version,
  mode, horizon, participant_evidence_digest, immutable participant
  snapshots, immutable evidence references.

QualityComparisonEvaluationObservation
  Meaning: one deterministic quality fact established by one
  QualityComparisonEvaluation. An Evaluation produces 0..N observations.
  Observations are plural by design.
```

## 3. Critical N-source invariant (frozen, binding)

> One Evaluation MAY establish multiple quality observations simultaneously. No deterministically-provable quality fact may be suppressed merely because another quality fact is also true for the same evaluation.

## 4. Observation types (frozen, closed)

```
CROSS_SOURCE_VALUE_CONFLICT
CROSS_SOURCE_PARTICIPANT_VALUE_MISSING
```

No additional observation type is authorized by this amendment. A future third type requires its own governed extension, exactly mirroring how `CONSISTENCY` itself required governance to join `COMPLETENESS`/`VALIDITY`.

## 5. Conflict observation semantics (frozen)

When two or more distinct values exist among known participants, a `CROSS_SOURCE_VALUE_CONFLICT` observation is recorded for **every** known participant involved — no attribution of correctness. `VALUE_CONFLICT / A` means *"participant A supplied evidence participating in a deterministically established cross-source disagreement,"* never *"participant A is wrong."* OQI2 does not, and must never, determine a correct participant from disagreement alone (Majority Principle, §12).

## 6. Missing observation semantics (frozen)

For each deterministically-provable expected-and-missing participant (CDD-040 §27's 4a/4b resolution, unchanged — see §11), an independent `CROSS_SOURCE_PARTICIPANT_VALUE_MISSING / <role>` observation is recorded. Multiple simultaneously-missing participants produce multiple independent rows — never a single generic "something is missing" signal.

## 7. Finding identity (frozen, unchanged)

```
uuid5(
  OQI_CROSS_SOURCE_NAMESPACE,
  canonical(tenant_id, quality_condition_id, "CROSS_SOURCE_COMPARISON", comparison_subject_id)
)
```

Unchanged from CDD-040 §32. `observation_type`, `participant_role`, `rule_version`, `correspondence_version`, evidence values, horizon, authority, and membership remain excluded, for exactly the reasons CDD-040 already proved. One governed condition + one comparison subject retains exactly one continuing Finding lineage — Option E (multiple Findings per facet) considered and rejected in OQI2-RN §I precisely to preserve this.

## 8. Evaluation identity (frozen, unchanged)

Unchanged from CDD-040 §42. Observations are a deterministic derivative of the same evaluation inputs (same participant-evidence digest, same rule/correspondence versions) — computing more facts about one evaluation does not change what was evaluated. No Evaluation identity redesign is authorized.

## 9. Observation identity (frozen, new)

```
(evaluation_id, observation_type, participant_role)
```

A natural relational key only — no independent `uuid5` derivation. The Evaluation already provides immutable event identity; observations are a decomposition of what that identified evaluation computed, not a new identity domain.

## 10. New persistence object (authorized)

```
quality_comparison_evaluation_observations
    evaluation_id        UUID, PK part, FK -> quality_comparison_evaluations.evaluation_id
    observation_type     String(64), PK part
    participant_role     String(64), PK part
    FK (evaluation_id, participant_role)
      -> quality_comparison_evaluation_participants(evaluation_id, participant_role)
```

The composite FK to the existing participant snapshot extends CDD-040 §49's chained-FK provenance-integrity discipline unchanged: an observation cannot claim a `participant_role` that was not genuinely part of that evaluation's own snapshot — declaratively DB-enforced, no trigger. This does **not** touch, weaken, or duplicate the existing evidence-association chained FK. No new residual tenant-integrity issue is introduced: the tenant boundary for observations is exactly as strong (and exactly as narrowly, honestly disclosed as P3) as it already is for participant snapshots — OQI-P3-002 is unaffected by this table (§17).

## 11. Expected + correspondence semantics (unchanged, reaffirmed)

CDD-040 §27's 4a/4b resolution is unchanged and not reopened: rule-level `expected=true` alone never manufactures subject-level existence; only explicit governed subject-level correspondence membership, combined with `expected=true`, permits a deterministic missing-participant observation.

## 12. Majority and authority principles (unchanged, reaffirmed)

> Agreement count is evidence, not truth. An authoritative source is governed context, not epistemic certainty.

For `A/B/C/D=ABC123, E=XYZ999(authoritative)`: both the peer-agreement cluster and the authoritative dissent remain independently reconstructable; neither is erased; neither is automatically chosen as truth. Authority remains exclusively on the participant snapshot (existing `authoritative` column) — **not** duplicated onto the observation row (§19 of OQI2-RN: "prefer referencing participant snapshot rather than duplicating governance facts").

## 13. Algorithm semantics (frozen, replaces the short-circuit)

```
1. Determine deterministic missing-participant observations (per CDD-040 §27, unchanged rule).
2. Whenever >= 2 known participant values exist, independently evaluate them for
   cross-source disagreement (exact-match, CDD-040 §25, unchanged) and determine
   conflict observations.
3. Combine all observations from steps 1-2. No step suppresses another.
4. outcome = VIOLATED if any observation exists.
   outcome = SATISFIED if zero observations exist AND >= 2 known values exist.
   outcome = NOT_EVALUABLE (no Evaluation persisted, no Finding touched) if
     fewer than 2 known values exist AND no missing-participant observation exists.
```

This is a strict superset of CDD-040's original algorithm — every previously-proven single-condition scenario (OQI2-V/VN's 145+ checks) behaves identically; only the previously-unreachable simultaneous case is now correctly computed.

## 14. Finding lifecycle (unchanged, decoupled from observation composition)

The existing six-row OPEN/RESOLVED transition table (CDD-040 §33) governs Finding purely from `outcome`, never from *which* observation(s) caused it. Observation composition may freely change while Finding remains OPEN:

```
T1: MISSING + CONFLICT   -> Finding OPEN,  rev=1, occurrence=1
T2: MISSING only         -> Finding OPEN,  rev=2 (unchanged occurrence)
T3: (no observations)    -> Finding RESOLVED, rev=3
T4: CONFLICT              -> Finding OPEN (reopened), rev=4, occurrence=2, reopen=1
```

## 15. Observation lifecycle (frozen: none)

Observations have **no** independent mutable lifecycle — no status, occurrence_count, reopen_count, first_seen, or last_seen of their own. They are immutable facts belonging to one immutable Evaluation. The *current* observation set is obtained via `Finding.latest_evaluation_id → Evaluation → its Observations`. Historical observation state at any past evaluation remains available via that evaluation's own immutable rows — exactly mirroring how participant snapshots and evidence already work. A future governance decision may add facet-level lifecycle if a genuine need is proven; none is authorized here.

## 16. Agreement clusters, candidate values, support counts (frozen: none persisted)

```
PERSIST AGREEMENT CLUSTERS:      NO
PERSIST CANDIDATE VALUE IN OQI2: NO
PERSIST SUPPORT COUNT:           NO
```

All three are deterministically derivable at read time from the CONFLICT/MISSING observation's participant set joined to the already-linked participant snapshots and `FieldValueEvidence` — persisting them would duplicate raw/derived state with drift risk and no proven audit requirement, violating CDD-040's own no-raw-value-duplication discipline.

## 17. Tenant/DB integrity reassessment

No new residual tenant-integrity issue is introduced by `quality_comparison_evaluation_observations`. Its only foreign key targets the participant snapshot (already governed, already the sole narrow application-enforced tenant boundary per OQI-P3-002); the observation table itself carries no `source_field_id`/evidence link of its own requiring a separate chained-FK integrity guarantee. OQI-P3-002's disposition is **unchanged**.

## 18. N-source cardinality and source-system agnosticity (reaffirmed, unchanged)

Production architecture supports `2..N` governed participants, proven at N=2,3,5,10 in OQI2-VN. No production code may depend on source vendor/system names. Nothing in this amendment introduces any such dependency.

## 19. Remediation anchor (conceptual only, not implemented)

```
(evaluation_id, observation_type, participant_role)
```

Guarantees a future OQI5/Gate S layer an unambiguous deterministic anchor. For `PARTICIPANT_VALUE_MISSING`, this is directly a remediation target. For `VALUE_CONFLICT`, `participant_role` means "this participant participated in the disagreement," never "this participant is wrong." This amendment does not implement OQI5, Gate V, or Gate S in any way.

## 20. Worked examples (normative)

**Five-source, missing only** (ERP/PLM/MES/Supplier Portal agree, PIM missing, correspondence-bound):
```
Observations: [ (eval_id, PARTICIPANT_VALUE_MISSING, PIM) ]
outcome: VIOLATED
```
Future (unimplemented) remediation derivation, entirely read-time: `target=PIM`, `candidate=ABC123` (read from any peer's evidence), `support=[ERP,PLM,MES,Portal]`, `count=4`, `truth_status=CANDIDATE ONLY`, `automatic_write=NO`. None of this is persisted by OQI2.

**Five-source, conflict + missing** (ERP/PLM/MES=ABC123, ExternalCatalog=XYZ999, PIM missing):
```
Observations: [
  (eval_id, PARTICIPANT_VALUE_MISSING, PIM),
  (eval_id, VALUE_CONFLICT, ERP), (eval_id, VALUE_CONFLICT, PLM),
  (eval_id, VALUE_CONFLICT, MES), (eval_id, VALUE_CONFLICT, ExternalCatalog)
]
outcome: VIOLATED
```
Both facts are simultaneously, explicitly, queryably present — the conflict is never hidden merely because PIM is also missing.

## 21. Documentation factual correction

The prior companion document, `CDD-040-Artifact-Authorization-Finding-Type-Column-Width-Correction.md`, states that `CROSS_SOURCE_PARTICIPANT_VALUE_MISSING` is 39 characters. It is actually **38 characters** (`len("CROSS_SOURCE_PARTICIPANT_VALUE_MISSING") == 38`). This is a narrow factual correction to that document's explanatory text only:

- the original document remains historical and frozen, not edited in place;
- the `VARCHAR(64)` width decision it authorized remains fully correct (38 < 64, exactly as 39 < 64 would have been);
- only the explanatory character-count statement was inaccurate;
- there is no runtime or schema consequence of this correction.

## 22. Firewalls (reaffirmed, unaffected)

This amendment implements no ontology impact, no agents, no remediation, no trust score, no dashboard, no API, no frontend, no Gate V/Gate S runtime change, no Gate T semantics, and no Entity Resolution inference. It exists solely to ensure OQI2 preserves sufficient deterministic evidence for those future layers, exactly as CDD-040's own non-goals already required.

## 23. P3 register (carried forward, unchanged)

```
OQI-P3-001: 64-bit advisory-lock collision space. ACCEPTED, unchanged.
OQI-P3-002: residual DB tenant defense-in-depth gap. ACCEPTED, unchanged
  (§17 above confirms no expansion).
OQI-P3-003: explicit-correspondence scalability. ACCEPTED, unchanged.
OQI-P3-004: deferred composite evidence-lookup index. ACCEPTED, unchanged.
```

## 24. P1 disposition

Publication of this amendment **resolves the architecture question** but does **not** by itself close the implementation P1 (simultaneous conflict+missingness classification collapse in PR #166 as currently written). The P1 remains **OPEN**, now **authorized for repair** under the exact Artifact Authorization Amendment published alongside this document. Only a subsequent implementation phase (OQI2-I-R) followed by independent re-verification (OQI2-VN2) may close it.
