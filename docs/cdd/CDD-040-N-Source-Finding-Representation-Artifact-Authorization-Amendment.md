# CDD-040 N-Source Finding Representation — Artifact Authorization Amendment

**Status:** APPROVED ARTIFACT AUTHORIZATION AMENDMENT
**Version:** 1.0
**Governs:** implementation of `CDD-040-N-Source-Finding-Representation-Amendment.md` (this document authorizes exactly its repair surface)
**Reference point:** this amendment governs the exact **delta from the currently-held, unmerged PR #166** (`48688a1b58acfc9931c7723bf42536a0adcb3c54`), not from clean `main`. It supersedes no path in the original CDD-040 Artifact Authorization — it adds a repair delta on top of it.
**Companion:** `CDD-040-N-Source-Finding-Representation-Amendment.md` (architecture); this document authorizes its implementation only

## 1. Authorized starting state for the repair

```
Authoritative main:        81e5db720988ea329ae988341167a0292c786cad
Held implementation PR:    #166
Held implementation head:  48688a1b58acfc9931c7723bf42536a0adcb3c54
```

OQI2-I-R MUST branch its work from the currently-held PR #166 branch (`oqi2/cross-source-consistency`) at exactly this head — not from clean main, not from a fresh branch. This is a repair, not a reimplementation.

## 2. Governance dependencies (frozen, must remain byte-identical throughout repair)

```
CDD-039 + all OQI1 amendments                         — unmodified
CDD-019, CDD-022 + its OQI2 companion amendment         — unmodified
CDD-040 (original)                                      — unmodified (amended only via
                                                            companion, never in place)
CDD-040 migration-revision-length correction             — unmodified
CDD-040 finding-type-width correction                    — unmodified (superseded in
                                                            effect but not edited; see
                                                            the architecture amendment §21
                                                            for the narrow factual note)
CDD-040 N-Source Finding Representation Amendment        — this repair implements it exactly
```

## 3. Scope boundary (unchanged from the original Artifact Authorization, reaffirmed)

No API, no frontend, no `main.py`, no auth files, no Gate T/V/S runtime, no Entity Resolution matching/scoring runtime, no OQI4/5/6 code, no performance-only index migration. Any need to cross these boundaries requires a separate governance amendment — STOP and report, do not improvise.

## 4. Exact repair path set (authoritative)

| # | Action | Exact path | Purpose |
|---|---|---|---|
| 1 | MODIFY | `backend/app/domain/oqi_cross_source/evaluation.py` | add `ComparisonObservation` frozen dataclass (`observation_type`, `participant_role`); add `observations: tuple[ComparisonObservation, ...]` field to `QualityComparisonEvaluation` (not part of its identity derivation) |
| 2 | MODIFY | `backend/app/domain/oqi_cross_source/finding.py` | remove `finding_type` from `QualityComparisonFinding`; remove the `finding_type` parameter from `apply_correspondence_finding_transition` (transition now driven by `outcome` alone) |
| 3 | MODIFY | `backend/app/infrastructure/persistence/models/oqi_cross_source_evaluation.py` | add `QualityComparisonEvaluationObservationORM` (composite PK `evaluation_id, observation_type, participant_role`; composite FK to `quality_comparison_evaluation_participants`) |
| 4 | MODIFY | `backend/app/infrastructure/persistence/models/oqi_cross_source_finding.py` | remove the `finding_type` column |
| 5 | MODIFY | `backend/app/infrastructure/persistence/oqi_cross_source_evaluation_repository.py` | `insert_evaluation_idempotent` persists observation rows atomically with the evaluation/participant/evidence rows in the same transaction; `upsert_finding`/`get_finding`/`_finding_to_orm`/`_finding_to_domain` no longer read or write `finding_type` |
| 6 | MODIFY | `backend/app/infrastructure/persistence/migrations/versions/0021_oqi2_cross_source_consistency.py` | (amended in place, per §40 of the governing prompt — PR unmerged) add `quality_comparison_evaluation_observations` table; remove `finding_type` column from `quality_comparison_findings`; `downgrade()` updated symmetrically; `revision`/`down_revision` unchanged |
| 7 | MODIFY | `backend/app/application/oqi_cross_source_evaluation_service.py` | remove the `any_missing` short-circuit; unconditionally collect missing-participant observations and (whenever `len(known_values) >= 2`) conflict observations; derive `outcome` per CDD-040 N-Source Amendment §13; pass `observations` into the persisted `QualityComparisonEvaluation`; call `apply_correspondence_finding_transition` without a `finding_type` argument |
| 8 | MODIFY | `backend/app/tests/test_oqi_cross_source_evaluation_domain.py` | update/remove tests asserting the old `finding_type`-parameterized transition signature; add domain-level observation tests (construction, digest-independence — observations do not enter Evaluation identity) |
| 9 | MODIFY | `backend/app/tests/test_oqi_cross_source_evaluation_service.py` | update every existing epistemic-matrix test to assert on persisted observations instead of `finding_type`; add the simultaneous-condition test matrix (§9–§14 below) |
| 10 | MODIFY | `backend/app/tests/test_oqi_cross_source_postgres.py` | update the schema-shape test for the new table and the removed column; add real-Postgres concurrency/idempotency/DB-integrity tests for observations (§15–§17 below) |
| 11 | MODIFY | `backend/app/tests/test_oqi_cross_source_provenance.py` | extend the full-chain reconstruction test to include observations; add the simultaneous-condition provenance reconstruction (§18 below) |
| 12 | MODIFY | `backend/app/tests/test_runtime_architecture.py` | add `QualityComparisonEvaluationObservationORM` to the OQI2 firewall test's single-construction-site assertions |
| 13 | MODIFY | `backend/app/tests/test_persistence_integration.py` | table-count literal `74` → `75` |

## 5. Mechanically derived accounting

```
CREATE = 0
MODIFY = 13
DELETE = 0
TOTAL  = 13
```

**Independent second count**: rows 1–13 above, all MODIFY, zero CREATE, zero DELETE. `0 + 13 + 0 = 13`. Counts agree — no arithmetic discrepancy.

## 6. File-count safety rule (binding, restated)

> The exact named path set in §4 is authoritative and is a delta on top of the original 25-file Artifact Authorization (unchanged) plus the finding-type-width correction (unchanged). The numeric accounting in §5 is derived mechanically. Any repair path not present in §4 is unauthorized and requires a further governance amendment before modification. No 14th repair path without one.

## 7. Migration strategy (frozen)

`0021_oqi2_cross_source_consistency.py` is **amended in place**, not superseded by a new post-0021 migration — PR #166 is unmerged and nothing external depends on its current shape. `revision = "0021_oqi2_cross_source"` and `down_revision = "0020_oqi1_quality_foundation"` remain **exactly unchanged**. The amended `upgrade()` additionally creates `quality_comparison_evaluation_observations` and drops the `finding_type` column from `quality_comparison_findings` (both additive/removal operations within the same migration that already creates these tables — no separate migration step needed since neither table has shipped to any real environment yet). `downgrade()` is updated symmetrically (drop the new table before dropping its parent evaluations table; the removed column requires no explicit re-add in `downgrade()`, since `downgrade()` already drops the entire `quality_comparison_findings` table).

## 8. Verified table count

```
Pre-repair (current PR #166): 68 (OQI1) + 6 (OQI2) = 74
Post-repair: 68 + 7 = 75  (one additional table: quality_comparison_evaluation_observations;
                            the finding_type column removal does not change table count)
```

Must be mechanically re-verified against the real migrated schema during implementation — this document freezes the *expected* count, not a substitute for that verification.

## 9–14. Required simultaneous-condition test matrix (mandatory, exact)

```
9.  Conflict + single missing:
    A=ABC, B=ABC, C=XYZ, D=MISSING
    Require exactly: MISSING/D, CONFLICT/A, CONFLICT/B, CONFLICT/C
    persisted atomically with the Evaluation.

10. Multiple missing, no conflict:
    A=ABC, B=ABC, C=ABC, D=MISSING, E=MISSING
    Require exactly: MISSING/D, MISSING/E.

11. Multiple missing + conflict:
    A=ABC, B=ABC, C=XYZ, D=MISSING, E=MISSING
    Require exactly: CONFLICT/A, CONFLICT/B, CONFLICT/C, MISSING/D, MISSING/E.

12. Conflict resolves while missing persists (sequential):
    T1: A=ABC,B=ABC,C=XYZ,D=MISSING -> T2: A=ABC,B=ABC,C=ABC,D=MISSING
    T2's latest observations: MISSING/D only. Finding remains OPEN.
    T1's historical evaluation and its own observations remain unchanged and
    independently reconstructable.

13. Missing resolves while conflict persists (sequential):
    T1: A=ABC,B=XYZ,C=MISSING -> T2: A=ABC,B=XYZ,C=ABC
    T2's latest observations: CONFLICT/A, CONFLICT/B only. Finding remains OPEN.

14. Full lifecycle (conflict+missing -> missing only -> resolved -> reopened conflict):
    T1: conflict+missing -> T2: missing only -> T3: all agree -> T4: conflict
    Require Finding lifecycle exactly: OPEN, OPEN, RESOLVED, OPEN(reopened),
    with state_revision/occurrence_count/reopen_count per the existing unchanged
    six-row transition table.
```

## 15–18. Required real-PostgreSQL / provenance tests (mandatory, exact)

```
15. N-source concurrency for observations:
    Worker B waits for Finding authority on a 5-participant evaluation; while
    waiting, evidence is committed for multiple participants. After authority
    is acquired, worker B's observations must reflect the single coherent
    post-lock frontier -- no participant's observation status decided from
    pre-lock evidence.

16. Idempotent observation replay:
    Identical Evaluation replay (sequential and concurrent) must not duplicate
    observation rows -- the natural key (evaluation_id, observation_type,
    participant_role) makes this deterministic by construction; prove it on
    real Postgres, not merely asserted.

17. DB integrity for the new table:
    Attempt to insert an observation row whose participant_role has no
    matching row in that evaluation's own participant snapshot -- must be
    rejected by the composite FK (IntegrityError), proven directly, exception
    type asserted.

18. Full provenance reconstruction under simultaneous conditions:
    From a Finding produced by scenario #9 above, reconstruct end-to-end:
    Finding -> latest Evaluation -> observations -> participant roles ->
    participant snapshots -> evidence IDs -> FieldValueEvidence -> SourceField
    -> SourceObject -> SourceSystem, for BOTH the MISSING and CONFLICT
    observations simultaneously, with zero raw-value duplication anywhere in
    the observation table itself.
```

## 19. Firewall tests (mandatory)

Extend the existing OQI2 firewall test (already covering Gate T/ER/OQI3-7/agent/LLM import prohibitions) to include `QualityComparisonEvaluationObservationORM` in the single-construction-site assertion (exactly one production construction site: `oqi_cross_source_evaluation_repository.py`).

## 20. N-source regression (mandatory)

At least one 10-participant scenario must be re-verified against the amended algorithm and observation model (reusing the N-source test pattern already proven in OQI2-VN), confirming correct observation cardinality at scale and no exactly-two/binary assumption reintroduced by the repair.

## 21. Static quality and full regression (mandatory, unchanged bar)

`black --check .`, `isort --check-only .`, `ruff check .`, `mypy app` all clean; full backend suite green with zero new failures beyond the already-independently-reproduced `test_ontology_api.py` baseline (7 failures, environmental, unrelated); real-PostgreSQL migration round-trip (`0020↔0021`) clean; exact-head CI green on the new repair commit.

## 22. Acceptance criteria

All 13 files present exactly as named (no 14th path); table count 75 confirmed; §9–§18's exact scenarios all present and passing on real PostgreSQL; `finding_type` absent from `QualityComparisonFinding`/`quality_comparison_findings` everywhere; zero raw-value duplication in the new table; zero regression in any of the 145+ previously-proven OQI2-V/VN adversarial checks; firewalls clear; static quality clean; exact-head CI green.

## 23. STOP conditions (fail-closed, unchanged discipline)

STOP and report — do not improvise — if: a repair need requires touching any path outside §4's exact set; any previously-frozen governance file requires editing in place; the two independent counts in §5 ever disagree; the verified table count differs from 75; any firewall boundary would be crossed; the migration cannot be amended in place safely (e.g., if any external consumer is discovered to already depend on the current `0021` shape — none is expected, but must be checked).
