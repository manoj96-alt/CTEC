# CDD-040 Artifact Authorization — OQI2 Multi-Source Quality Intelligence

**Status:** APPROVED ARTIFACT AUTHORIZATION
**Version:** 1.0
**Governs:** CDD-040 v1.0 (this document authorizes exactly its implementation surface)
**Companion:** `CDD-022-Artifact-Authorization-OQI2-Evidence-Composite-Uniqueness-Amendment.md` (authorizes the one additive touch to a CDD-022-governed table; not counted in this document's file budget, which covers `backend/app/` implementation paths only, per established precedent)

## 1. Authorized starting main SHA

```
8310b4379cf76c098e1f4dcaf4bc26500626a209
```

Implementation MUST branch from this exact commit (or a fast-forward descendant that re-verifies this document's preconditions unchanged).

## 2. Governance dependencies (frozen, must remain byte-identical throughout implementation)

```
CDD-039  (OQI1 foundation)                         — unmodified
CDD-039 Artifact Authorization                     — unmodified
CDD-039 GR / GC / GM amendments                     — unmodified
CDD-019  (Semantic mapping)                          — unmodified
CDD-022  (FieldValueEvidence) + this phase's         — amended ONLY via its own
         narrow companion amendment                    separate companion document
CDD-004  (Entity Resolution)                          — unmodified
CDD-031  (Gate T)                                      — unmodified
CDD-040  (this document's governing CDD)                — frozen, this authorization
         implements it exactly
```

## 3. Scope boundary (binding)

This authorization covers **backend domain/persistence/application/test code only**. It explicitly does NOT authorize:

```
frontend/**                          backend/app/main.py
backend/app/api/**                   Keycloak/auth files
Gate T domain/runtime                Gate V agent runtime
Gate S approval runtime              Entity Resolution matching/scoring runtime
OQI4/OQI5/OQI6 code (none exist)     Any performance-only index migration
                                      (CDD-022 hardening — separate future gate)
```

Any implementation need touching the above requires a governance amendment before proceeding — STOP and report, do not improvise.

## 4. Exact implementation path set (authoritative)

| # | Action | Exact path | Purpose |
|---|---|---|---|
| 1 | CREATE | `backend/app/domain/oqi_cross_source/__init__.py` | package marker |
| 2 | CREATE | `backend/app/domain/oqi_cross_source/correspondence.py` | `ComparisonSubjectCorrespondence` domain model, lifecycle validation, `derive_correspondence_id`, `OqiMalformedCorrespondenceError` |
| 3 | CREATE | `backend/app/domain/oqi_cross_source/evaluation.py` | `QualityComparisonEvaluation`, `canonical_comparison_subject_identity`, `participant_evidence_digest`, `derive_comparison_evaluation_id`, `derive_comparison_finding_id`, `evaluate_consistency()` |
| 4 | CREATE | `backend/app/domain/oqi_cross_source/finding.py` | `QualityComparisonFinding`, `apply_correspondence_finding_transition` |
| 5 | CREATE | `backend/app/infrastructure/persistence/models/oqi_cross_source_correspondence.py` | `ComparisonSubjectCorrespondenceORM`, `ComparisonSubjectCorrespondenceMemberORM` |
| 6 | CREATE | `backend/app/infrastructure/persistence/models/oqi_cross_source_evaluation.py` | `QualityComparisonEvaluationORM`, `QualityComparisonEvaluationParticipantORM`, `QualityComparisonEvaluationEvidenceORM` |
| 7 | CREATE | `backend/app/infrastructure/persistence/models/oqi_cross_source_finding.py` | `QualityComparisonFindingORM` |
| 8 | CREATE | `backend/app/infrastructure/persistence/oqi_cross_source_correspondence_repository.py` | correspondence create/get_active/retire |
| 9 | CREATE | `backend/app/infrastructure/persistence/oqi_cross_source_evaluation_repository.py` | authority acquisition, idempotent evaluation insert, participant/evidence selection, finding upsert |
| 10 | CREATE | `backend/app/application/oqi_cross_source_evaluation_service.py` | `OqiCrossSourceEvaluationService.evaluate_historical` / `.evaluate_current_state` |
| 11 | CREATE | `backend/app/infrastructure/persistence/migrations/versions/0021_oqi2_cross_source_consistency.py` | migration: 6 new tables + additive `field_value_evidence` constraint |
| 12 | CREATE | `backend/app/tests/test_oqi_cross_source_correspondence_domain.py` | correspondence domain unit tests |
| 13 | CREATE | `backend/app/tests/test_oqi_cross_source_evaluation_domain.py` | evaluation/finding domain unit tests, identity adversarial matrix |
| 14 | CREATE | `backend/app/tests/test_oqi_cross_source_evaluation_service.py` | service-level tests against a fake repository |
| 15 | CREATE | `backend/app/tests/test_oqi_cross_source_postgres.py` | real-Postgres: schema, DB constraints (negative tests), concurrency (12 scenarios), migration round-trip |
| 16 | CREATE | `backend/app/tests/test_oqi_cross_source_provenance.py` | full provenance-chain reconstruction tests |
| 17 | MODIFY | `backend/app/domain/oqi/quality_rule.py` | add `QualityDimension.CONSISTENCY`, 2 new `QualityFindingType` values, `_ALLOWED_COMBINATIONS` rows, `CONSISTENCY` branch in `validate_rule_shape` |
| 18 | MODIFY | `backend/app/tests/test_oqi_quality_rule_domain.py` | new parametrized case for the `CONSISTENCY` coupling |
| 19 | MODIFY | `backend/app/tests/test_runtime_architecture.py` | new `AUTHORIZED_CHANGED_PATHS` block (this exact path set); new firewall test mirroring `test_oqi1_quality_foundation_respects_every_firewall` for `oqi_cross_source` |
| 20 | MODIFY | `backend/app/tests/test_persistence_integration.py` | migration-head literal `0020_oqi1_quality_foundation` → `0021_oqi2_cross_source_consistency`; `table_count == 68` → `== 74` |
| 21 | MODIFY | `backend/app/tests/test_oqi_quality_postgres.py` | migration-head literal bump (line 190) |
| 22 | MODIFY | `backend/app/tests/test_knowledge_engine.py` | migration-head literal bump (line 305) |
| 23 | MODIFY | `backend/app/tests/test_gate_v_agent_postgres.py` | migration-head literal bump (line 95) |
| 24 | MODIFY | `backend/app/tests/test_governance_engine.py` | migration-head literal bump (line 388) |
| 25 | MODIFY | `backend/app/tests/test_decision_engine.py` | migration-head literal bump (line 307) |

## 5. Mechanically derived accounting

```
CREATE = 16   (rows 1-16)
MODIFY = 9    (rows 17-25)
DELETE = 0
TOTAL  = 25
```

**Independent second count** (rows only, by action column): CREATE rows = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16} = 16 entries. MODIFY rows = {17,18,19,20,21,22,23,24,25} = 9 entries. 16 + 9 = 25. **Counts match — both derivations agree. No arithmetic discrepancy (cf. OQI1-G's original defect, deliberately re-checked here).**

## 6. File-count safety rule (binding, restated)

> The exact named path set in §4 is authoritative. The numeric CREATE/MODIFY/DELETE/TOTAL summary in §5 is derived mechanically from that set. Any implementation path not present in the exact authorized set is unauthorized and requires a governance amendment before modification. No 26th file.

No vague/future-placeholder paths are authorized anywhere in this document.

## 7. Migration

```
revision      = "0021_oqi2_cross_source_consistency"
down_revision = "0020_oqi1_quality_foundation"
```

Verified single-head topology before freeze (0001→...→0019→0020, confirmed the true head with no branch). Expected table count at new head: **74** (68 existing + 6 new: `comparison_subject_correspondences`, `comparison_subject_correspondence_members`, `quality_comparison_evaluations`, `quality_comparison_evaluation_participants`, `quality_comparison_evaluation_evidence`, `quality_comparison_findings`).

## 8. Required tests (minimum, exact — implementation is not complete without all of these passing on real PostgreSQL)

### Concurrency (real Postgres, ≥12 scenarios)
1. First cross-source Finding, no contention.
2. Two concurrent identical evaluations (idempotent convergence).
3. Three concurrent evaluations, sequential state_revision.
4. Stale evidence arriving while a worker waits on the lock.
5. Participant evidence changing independently across two participants mid-wait.
6. Rollback releases authority promptly; zero partial state persists.
7. Two different comparison subjects do not block each other.
8. Two different tenants do not block each other.
9. HISTORICAL evaluation never acquires the lock.
10. `comparison_subject_correspondence_id` is pinned correctly under concurrency (matches the version loaded pre-lock, §46 CDD-040).
11. `rule_version` is pinned correctly under concurrency.
12. `state_revision` increments exactly once per authoritative (newly-inserted) evaluation, never on idempotent replay.

### DB integrity (real Postgres, negative tests expecting DB rejection)
Wrong participant-role evidence; evidence with mismatched `source_field_id`; evidence swapped between two participants; duplicate `ACTIVE` correspondence for one subject; duplicate participant role within one correspondence version; duplicate correspondence member lineage across two roles; invalid FK on every new composite constraint (§49/§52 of CDD-040); cross-tenant participant-snapshot construction attempt — expect **service/repository-level rejection** (application-enforced boundary, §50 CDD-040), not a DB error, and the test must assert this is the ONLY construction site for that table.

### Epistemic matrix (exact cases of CDD-040 §29, no ambiguity)
Case 1 (known+expected+no target evidence → VIOLATED); Case 2 (known+optional+no target evidence → excluded/no Finding); Case 3 (correspondence silent on role → excluded); Case 4 (correspondence names lineage, unknown, expected → VIOLATED); Case 5 (correspondence names lineage, unknown, optional → excluded); one known value only (NOT_EVALUABLE); two agreeing values (SATISFIED); two conflicting values (VIOLATED); three agreeing values (SATISFIED); 2-vs-1 conflict (VIOLATED); authority disagrees with majority (VIOLATED, authority does not suppress).

### Identity adversarial matrix
Participant input order; role changes; rule-version changes; authority changes; membership changes; correspondence-version changes; `comparison_subject_id` changes; tenant changes; condition changes; evidence changes; horizon changes; mode changes; Unicode `source_record_reference`; delimiter-collision attempts against the canonical encoding.

### Provenance chain
`QualityComparisonFinding → latest_evaluation_id → QualityComparisonEvaluation → rule_version → comparison_subject_correspondence_id → participant snapshots → SourceRecordLineageIdentity → evidence IDs → SourceField → SourceObject → SourceSystem`, reconstructable end-to-end with zero raw-value duplication anywhere in the chain.

### Firewalls
AST-import-based test (mirroring `test_oqi1_quality_foundation_respects_every_firewall`) proving `oqi_cross_source` modules never import Gate T, Gate V, Gate S, Entity Resolution matching, any LLM/model SDK, `app.api`, or `app.runtime`.

## 9. Acceptance criteria

All 25 files present exactly as named; full backend suite green; black/ruff/mypy clean; migration round-trips cleanly (`0020`→`0021`→`0020`); table count 68→74 confirmed; all §8 tests present and passing on real PostgreSQL; zero modification to any OQI1 table; the one authorized `field_value_evidence` constraint present and matching its CDD-022 companion exactly; exact-head CI green (backend/frontend/containers).

## 10. STOP conditions (fail-closed, unchanged discipline from OQI1)

STOP and report — do not improvise — if: an implementation need requires touching any path outside §4's exact set; the CDD-022 companion amendment's authorized constraint differs in any way from what CDD-040 §49 specifies; a migration-head assertion is discovered outside the 6 files in §4 rows 20-25; the two independent counts in §5 ever disagree; any OQI1 table's shape needs to change; any firewall boundary (§3, CDD-040 §57) would be crossed.
