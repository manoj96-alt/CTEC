# CDD-031 — Governed Source-Evidence Fitness Evaluation and Ontology Impact

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: RFC-010 (FROZEN, Canonical Enterprise Ontology Boundary — this CDD introduces no
cognitive capability and no canonical entity, §23 below), RFC-013 (FROZEN, Governance Authority and
Evaluation Separation — this CDD is pure Governance Evaluation exposure, never Governance Authority),
RFC-015 (FROZEN, Tenant Ownership Physical Model Authorization — tenant origin exclusively from the
existing governed evidence-retrieval path, §19 below), CDD-017 (FROZEN, Blueprint Requirement Contract,
unchanged — the origin of "Profiling + Gap Engine" and the five protected future platform capabilities,
§3 below), CDD-019 (FROZEN, Gate H H1-H3, unchanged), CDD-020 (FROZEN, Gate I, unchanged — the sole
coverage authority and, at its own §19, the origin of this CDD's mandate, §3 below), CDD-021 (FROZEN,
Gate J, unchanged — reused only as a non-normative structural pattern, never as a runtime dependency,
§23 below), CDD-022 (FROZEN, `FieldValueEvidence`, unchanged), CDD-023 (FROZEN, H4, unchanged — the sole
evidence-availability authority, §23 below), CDD-024 (FROZEN, Gate N, unchanged — the sole
context-composition authority, entirely unmodified and unconsumed by this CDD, §23 below)

Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via a Product-Owner-directed capability
audit (Source Data Quality → Ontology Impact Audit, Recommendation C — material gap) → discovery (Gate T0)
→ Product Owner architecture-decision resolution (Gate T1, resolving T-D1 through T-D6) → drafting
(Gate T2) → Product Owner CDD review and contract normalization (Gate T3, resolving T-D7, T-D8, T-D9 and
three P2 editorial corrections, P0=0/P1=0/P2=0 after resolution) → this Gate T4 publication turn. No
implementation exists, and none is authorized by this frozen document — a separate, subsequent Artifact
Authorization companion remains required before any file is created or modified.

## 1. Objective and business outcome

Answer, for a governed `InformationElementRequirement` that is already `MAPPED` (Gate I) with evidence
already `EVIDENCE_PRESENT` (H4): **is this governed evidence currently fit under Gate T's explicitly
bounded freshness and conflict semantics — and if not, why, what ontology context is affected, and what
deterministic remediation can CTEC recommend?** This is the initial, deliberately narrow implementation of
the capability CDD-020 §19 explicitly named and deferred: *"No trust/staleness/disconnection/low-confidence
overlay of any kind is authorized (reserved for a future, separately-governed, not-yet-named capability)."*
This CDD is that capability, bounded to exactly staleness and value-conflict detection — it does not
evaluate, and does not claim to evaluate, validity, allowed-domain conformance, format correctness,
accuracy, completeness beyond H4, or referential integrity.

## 2. Governing authorities

(restated per header)

## 3. Relationship to CDD-020 §19 deferral and CDD-017 §23

CDD-020 §19's own text is quoted verbatim in §1 above and is the direct origin of this CDD's mandate. CDD-017
§23 names five protected future platform capabilities in sequence: *Source-to-Blueprint Semantic Mapping,
Profiling + Gap Engine, Gap Impact + Remediation Engine, Decision Requirements, Decision Readiness.* The
Product-Owner-directed audit that produced this CDD found that "Profiling + Gap Engine" was previously
claimed complete (CDD-021 §1) but was, on direct code evidence, fulfilled only in its narrowest
presence/absence sense (Gate I/H4) — never in the fuller "profiling" sense CDD-020 §19 itself named. This
CDD closes that specific, previously disclosed gap. It does not reopen, amend, or reinterpret CDD-017 or
CDD-020, both of which remain FROZEN and unchanged.

## 4. Frozen upstream authorities (binding)

Gate I (CDD-020) remains the sole authority for `CoverageStatus.MAPPED`/`UNMAPPED`. H4 (CDD-023) remains the
sole authority for `EvidenceAvailabilityStatus.NO_EVIDENCE`/`EVIDENCE_EMPTY`/`EVIDENCE_PRESENT`. Gate N
(CDD-024) remains the sole authority for lossless Gate I + H4 composition and is never consumed, modified,
or wrapped by this CDD. Gate J (CDD-021) remains the sole authority for `UNMAPPED` structural impact and
`REVIEW_SEMANTIC_MAPPING` remediation; this CDD reuses only its *structural traversal pattern*, never its
code, its file, or its output type.

## 5. Definitions

**Comparable evidence group**: the set of `FieldValueEvidence` rows sharing both `source_field_id` and
`source_record_reference`, **restricted to rows with non-empty `observed_representation`** (a row with
`observed_representation == ""` is excluded entirely from Gate T's comparable-group analysis). **Fitness
evaluation eligibility**: a requirement is eligible for Gate T evaluation only when `CoverageStatus.MAPPED`
and `EvidenceAvailabilityStatus.EVIDENCE_PRESENT` both hold. **`as_of`**: the caller-supplied evaluation
instant against which staleness is judged.

## 6. Gate T owned concepts (binding)

Gate T introduces exactly one new enum (`EvidenceFitnessStatus`, §7), one new application service consuming
existing H4 output and the existing `FieldValueEvidenceRepositoryImpl.get_by_source_field` read path (§9),
and one new, independent structural-impact/remediation service (§15-§16). No new domain entity, no new
persistence model, no new ontology concept.

## 7. `EvidenceFitnessStatus` contract (binding)

```python
class EvidenceFitnessStatus(StrEnum):
    FIT = "FIT"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"
```

Exactly these three members. No numeric score, probability, confidence tier, or generic "quality" status of
any kind is authorized, now or by future amendment without a new governance cycle.

## 8. Eligibility for fitness evaluation (binding)

Gate T produces a non-`None` `EvidenceFitnessStatus` only when the corresponding `CoverageStatus` is `MAPPED`
and the corresponding `EvidenceAvailabilityStatus` is `EVIDENCE_PRESENT`. In every other case (`UNMAPPED`,
`NO_EVIDENCE`, `EVIDENCE_EMPTY`) Gate T's own result is `None`. `UNMAPPED`, `NO_EVIDENCE`, `EVIDENCE_EMPTY`,
`STALE`, and `CONFLICTING` remain five permanently distinct, non-overlapping outcomes.

## 9. Evidence retrieval contract (binding)

Gate T obtains the resolved `source_field_id` from H4's own already-public
`InformationElementEvidenceAvailabilityResult.source_field_id` (the top-level field — equivalent to, and
simpler than, drilling into `semantic_mapping_resolution.source_field_id`) and retrieves `FieldValueEvidence`
rows via the existing, unmodified `FieldValueEvidenceRepositoryImpl.get_by_source_field(*, tenant_id,
source_field_id)`. No new repository method. No new persistence read-path. No modification to H4's file.

## 10. Staleness semantics (binding)

Within one non-conflicting comparable group (§5), the group's freshness is the age of its most recent row's
`observed_at`, relative to `as_of`. `received_at` is never used for freshness.

## 11. Seven-day threshold (binding)

The fixed, global, Gate-T-v1 threshold is **7 days**, applied as a **strict inequality**: a comparable group
contributes to `STALE` only when `(as_of - observed_at) > 7 days`. Evidence aged exactly 7 days relative to
`as_of` remains eligible for `FIT`. No Blueprint-, requirement-, or tenant-specific threshold, and no
configurable freshness-policy framework, is authorized.

## 12. Explicit `as_of` determinism and future-timestamp handling (binding)

Gate T's own classification method accepts an explicit `as_of: datetime` parameter supplied by the caller.
Production classification logic never calls `datetime.now()`. Tests supply fixed `as_of` values. When
`observed_at > as_of` for a row within a comparable group, Gate T treats that row as contributing to a
`STALE` classification for that comparable group, regardless of the ordinary threshold comparison in §11. No
new `EvidenceFitnessStatus` member is introduced by this rule — it remains governed entirely by the existing
`FIT`/`STALE`/`CONFLICTING` vocabulary (§7). Gate T makes no claim about *why* a timestamp is in the future;
that determination remains deferred invalid-value territory (§24).

## 13. Conflict-comparison semantics (binding)

Within one comparable group (§5, already restricted to non-empty rows): identical `observed_representation`
values are not conflicting; any two distinct (non-identical) non-empty values classify the group
`CONFLICTING`. Comparison is exact and raw — no whitespace trimming, case-folding, canonicalization,
datatype coercion, fuzzy matching, or similarity scoring. Gate T never selects a winning value and never
infers that a newer differing row supersedes an older one — it surfaces the conflict only. A comparable
group containing only empty-valued rows is excluded before this comparison and can never be classified
`CONFLICTING` — this does not alter H4's own `EVIDENCE_EMPTY`/`EVIDENCE_PRESENT` classification in any way.

## 14. Requirement-level roll-up semantics (binding)

Requirement-level `EvidenceFitnessStatus` is computed conservatively across every non-empty-restricted
comparable group (§5, §13) under the resolved `SourceField`: **`CONFLICTING`** if any group has disagreeing
non-empty values; otherwise **`STALE`** if any group's most recent `observed_at` exceeds the 7-day threshold
(§11, strict `>`) relative to `as_of`, **or if any group contains a future-dated row** (§12); otherwise
**`FIT`**. Precedence is strictly `CONFLICTING` > `STALE` > `FIT`. A comparable group consisting entirely of
empty-valued rows does not contribute to this determination in any way.

## 15. Structural impact semantics (binding)

A new, independent service reuses Gate J's owning-`ConceptRequirement`/relationship-context traversal
*pattern* (mirroring `_find_owning_concept`/`_relationship_context` exactly in shape) without importing from,
extending, or modifying `backend/app/application/gap_impact_remediation.py` in any way. Output is a new,
Gate-T-owned result type — never a reinterpretation of `GapImpactContext`.

## 16. Remediation semantics (binding)

```python
class EvidenceFitnessRemediationAction(StrEnum):
    REFRESH_SOURCE_EVIDENCE = "REFRESH_SOURCE_EVIDENCE"      # for STALE
    REVIEW_CONFLICTING_EVIDENCE = "REVIEW_CONFLICTING_EVIDENCE"  # for CONFLICTING
```

Exactly these two members, mirroring `RemediationAction.REVIEW_SEMANTIC_MAPPING`'s own naming shape without
extending or modifying that existing enum. Pure deterministic recommendations only: no source-data mutation,
no external/agent/MCP invocation, no workflow or approval state, no persisted execution state.

## 17. Determinism of the public result (binding)

Gate T's externally observable per-requirement result is the single scalar `EvidenceFitnessStatus | None`
value (§7-§8, §14). This value is fully deterministic and **value-equal** (reproducible under `==`
comparison) for identical evidence and an identical `as_of` — the requirement-level roll-up (§14) is an
order-independent aggregation (`CONFLICTING`/`STALE` triggered by the *existence* of a qualifying group, not
by which group is evaluated first), so no internal iteration order affects the public result, and no
ordering requirement is imposed on implementation beyond what is needed to produce this scalar value
deterministically. Structural-impact/remediation detail exposed by the sibling service (§15-16), if any,
remains an Artifact-Authorization-level design question, not frozen here.

## 18. Failure semantics (binding)

Malformed/missing timestamps cannot occur (enforced at `FieldValueEvidence` construction). Malformed evidence
fails closed at construction time before Gate T ever sees it. The fitness enum is closed and exhaustive by
construction — no "unknown" branch exists. Evidence-retrieval failures reuse
`FieldValueEvidenceRepositoryImpl`'s own existing `ValidationException` behavior unchanged. No new failure
taxonomy is introduced.

## 19. Tenant isolation (binding)

Tenant identity flows exclusively through the existing `get_by_source_field(tenant_id=...)` call, exactly as
H4 already enforces it — no new tenant-scoping mechanism.

## 20. Persistence boundary (binding)

**Zero new persistence.** No table, column, cache, or durable fitness/remediation result of any kind.

## 21. Migration boundary (binding)

**Zero migration.**

## 22. API/frontend boundary (binding)

**No new REST API endpoint. No frontend artifact. No Ask CTEC modification.** Proof lives entirely at the
application-service/test layer, mirroring Gate Q's own precedent.

## 23. Frozen Gate I/H4/N/J firewall (binding, restated)

Gate T does not modify, reinterpret, or import production logic from `semantic_coverage_evaluation.py`,
`information_element_evidence_availability.py`, `information_element_context_availability.py`, or
`gap_impact_remediation.py`. It reads only already-public output fields and calls only already-existing,
unmodified repository methods. Gate T also does not modify or depend on Gate Q's MCP client/connector
capability in any way.

## 24. Invalid-value deferral (binding)

Datatype, allowed-domain, and format validation of `observed_representation` remain explicitly deferred — no
governed validation vocabulary exists for `InformationElementRequirement` today, and inventing one in
application code is not authorized by this CDD. This explicitly includes not evaluating *why* a timestamp
might be implausible (§12).

## 25. Disconnected-evidence deferral (binding)

Detection of evidence that "exists but cannot be correctly associated with its requirement" remains
explicitly deferred — the existing FK-enforced association architecture (H1 mapping creation, `SourceField`
foreign keys) already makes this state either structurally impossible or not meaningfully representable, and
no new association model is authorized by this CDD.

## 26. No confidence/scoring semantics (binding)

No numeric score, probability, weighting, or confidence tier appears anywhere in this CDD's contract, now or
by silent future extension.

## 27. Explicit non-goals

This CDD does not authorize: an enterprise Data Quality platform; a generic trust-score engine; a
configurable profiling platform; a generic rules/policy engine; a cleansing platform; a
duplicate-resolution platform; an Entity Resolution replacement; an anomaly-detection platform; an
observability platform; a data catalog; a workflow engine; an approval engine; an agent framework; MCP
integration; a simulation engine; any modification to Gate U, R, S, V, or X. **This CDD does not preclude
or preempt a future, separately-governed, broader Data Quality capability encompassing business-rule
validity, conformance, uniqueness, accuracy, referential integrity, consistency, and completeness beyond
what Gate T evaluates. `EvidenceFitnessStatus` and the remediation actions defined here (§7, §16) are not
intended to be extended into the vocabulary of that future capability — a future gate addressing that
broader scope should introduce its own contract rather than growing Gate T's narrow enum.**

## 28. Future Gate U compatibility

Gate U may consume Gate T's own `EvidenceFitnessStatus | None` result as an independent sibling to Gate N's
own composed result, keyed by `information_element_requirement_id` — no new coupling mechanism, no new API.

## 29. Testable invariants

`UNMAPPED`/`NO_EVIDENCE`/`EVIDENCE_EMPTY` always yield Gate T `None`. `CONFLICTING` always outranks `STALE`
at the requirement level. Identical `as_of` and unchanged evidence always yield value-equal results. No
Gate T code path ever calls `datetime.now()`. No Gate T code path ever writes to persistence. A comparable
group with one empty-valued row and one later non-empty row for the same record never yields `CONFLICTING`.
Evidence aged exactly 7 days is `FIT`, not `STALE`. A future-dated row always contributes to `STALE`, never
to `FIT`.

## 30. Acceptance criteria

1. A requirement whose sole comparable group has one fresh, non-conflicting row resolves `FIT`.
2. A requirement whose sole comparable group's most recent row exceeds 7 days (relative to `as_of`) resolves
   `STALE`.
3. A requirement with two comparable-group rows sharing `source_record_reference` but differing
   `observed_representation` resolves `CONFLICTING`, regardless of either row's age.
4. A requirement with one stale group and one conflicting group resolves `CONFLICTING` (precedence proven).
5. `UNMAPPED`, `NO_EVIDENCE`, and `EVIDENCE_EMPTY` requirements never receive a non-`None` Gate T status.
6. No test or code path writes to any persistence store.
7. `gap_impact_remediation.py`, and every Gate I/H4/N production file, pass unmodified, with zero behavior
   change, before and after Gate T implementation.
8. A comparable group transitioning from an empty observation to a later non-empty observation for the
   same record resolves `FIT` (not `CONFLICTING`), all else equal.
9. A comparable group whose most recent observation is aged exactly 7 days (relative to `as_of`) resolves
   `FIT`.
10. A comparable group containing a future-dated observation resolves at least `STALE` (or `CONFLICTING`
    if it also disagrees with another row), never `FIT`.

## 31. Governance firewall / prohibited interpretations

No implementation of this CDD may reinterpret `MAPPED`/`UNMAPPED` (Gate I), `NO_EVIDENCE`/`EVIDENCE_EMPTY`/
`EVIDENCE_PRESENT` (H4), Gate N's lossless composition, or Gate J's `UNMAPPED`/`REVIEW_SEMANTIC_MAPPING`
semantics. Gate T is a sibling capability; it does not supersede, narrow, or broaden any of the above.

## 32. Rollback

Reverting this CDD's eventual implementation removes a small number of new, self-contained files with no
existing-file rollback required — no frozen file is ever modified.

## 33. Numbered architecture baseline determination

No new numbered architecture baseline is required, following the identical method every CDD since CDD-016 has
used: this CDD cites RFC-010/013/015 and CDD-017/019/020/021/022/023/024 unchanged, and is registered via
`architecture/INDEX.md`'s existing "Governed implementation work orders" table alone.

## 34. Authorization

This document reached FROZEN status via: Gate T0 discovery (Product-Owner-directed capability audit,
Recommendation C) → Gate T1 Product Owner architecture-decision resolution (T-D1 through T-D6) → Gate T2 CDD
drafting → Gate T3 Product Owner CDD review and contract normalization (T-D7, T-D8, T-D9, and three P2
editorial corrections, P0=0/P1=0/P2=0 after resolution) → Gate T4 publication authorization, under which
this document is published and frozen.

**Implementation remains unauthorized.** A separate, subsequent Artifact Authorization is required before
any file governed by this CDD may be created or modified, matching every prior CDD's identical multi-step
discipline in this lineage.
