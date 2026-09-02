# CDD-048 OQI-H2 Governed Accuracy, Reasonableness, Reference Evidence, and Generalized Finding Origin — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** implementation of `CDD-048-OQI-H2-Governed-Accuracy-Reasonableness-Reference-Evidence-and-Generalized-Finding-Origin.md` only. No wildcard, no directory-level grant. Any path not named below is unauthorized; if implementation discovers a genuine need to touch an unnamed path, implementation must STOP and return for an amendment, exactly as the `OQI-H1-I-R1`/`OQI-H1-CI` precedent amendments did for H1.

## 1. Accounting

```
CREATE = 19
MODIFY = 11
DELETE = 0
TOTAL  = 30
```

## 2. CREATE (19)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/domain/oqi_reference_evidence/assertion.py` | `ReferenceEvidenceAssertion` domain shape + three form-specific value objects, versioning/activation logic (CDD-048 §15) |
| 2 | `backend/app/domain/oqi_reference_evidence/conflict.py` | `OqiReferenceEvidenceConflict` domain shape and detection/lifecycle logic (CDD-048 §16) |
| 3 | `backend/app/infrastructure/persistence/models/oqi_reference_evidence.py` | ORM: `oqi_reference_evidence_assertions`, `oqi_governed_reference_dataset_entries`, `oqi_human_verified_evidence_entries`, `oqi_business_rule_derived_reference_entries`, `oqi_reference_evidence_conflicts` (CDD-048 §15/§16) |
| 4 | `backend/app/infrastructure/persistence/oqi_reference_evidence_repository.py` | Repository: CRUD/versioning for assertions, conflict detection query, active-assertion lookup by form (CDD-048 §15/§16) |
| 5 | `backend/app/application/oqi_reference_evidence_service.py` | Service: assertion activation/versioning workflow, human-verification recording, conflict evaluation (CDD-048 §15–§18) |
| 6 | `backend/app/application/oqi_accuracy_evaluation_service.py` | Accuracy evaluator: `evaluate_current_state`/`evaluate_historical`, observation-granularity comparison against qualifying Reference Evidence (CDD-048 §7) |
| 7 | `backend/app/infrastructure/persistence/oqi_accuracy_evaluation_repository.py` | Repository for Accuracy evaluation persistence, `has_qualifying_coverage_for_dimension` support, `oqi_quality_evaluation_reference_evidence` link-table access (CDD-048 §7/§23) |
| 8 | `backend/app/domain/oqi_finding_origin/origin.py` | `QualityFindingOrigin` value object, `FindingStorageFamily` (renamed-in-identity `FindingFamily`), `finding_type → quality_dimension` static mapping (CDD-048 §12) |
| 9 | `backend/app/infrastructure/persistence/migrations/versions/0028_oqi_h2_reference_evidence.py` | Migration: reference-evidence envelope + 3 children + conflict table (CDD-048 §28) |
| 10 | `backend/app/infrastructure/persistence/migrations/versions/0029_oqi_h2_accuracy_dimension.py` | Migration: `oqi_quality_evaluation_reference_evidence` link table (CDD-048 §28) |
| 11 | `backend/app/infrastructure/persistence/migrations/versions/0030_oqi_h2_reasonableness_dimension.py` | Migration: `business_rules.dimension`, `business_rule_findings` finding-type-equivalent column, both nullable with legacy server default (CDD-048 §28) |
| 12 | `backend/app/tests/test_oqi_reference_evidence_domain.py` | Unit tests: assertion/conflict domain invariants, versioning, form validation |
| 13 | `backend/app/tests/test_oqi_reference_evidence_service.py` | Service tests: activation, human-verification recording, conflict detection (RC1–RC5) |
| 14 | `backend/app/tests/test_oqi_reference_evidence_postgres.py` | Real-Postgres: migration round-trip, active-uniqueness-per-form constraint, tenant isolation |
| 15 | `backend/app/tests/test_oqi_accuracy_evaluation_service.py` | Accuracy evaluator unit/service tests (A1–A7, A11–A13) |
| 16 | `backend/app/tests/test_oqi_accuracy_evaluation_postgres.py` | Real-Postgres Accuracy evaluation tests (A8–A10) |
| 17 | `backend/app/tests/test_oqi_reasonableness_evaluation_service.py` | Reasonableness evaluator unit/service tests (R1–R7, R9–R10), reusing `OqiBusinessRuleEvaluationService` with `purpose=REASONABLENESS` |
| 18 | `backend/app/tests/test_oqi_reasonableness_evaluation_postgres.py` | Real-Postgres Reasonableness evaluation tests (R8) |
| 19 | `backend/app/tests/test_oqi_h2_accuracy_reasonableness_crown.py` | Crown suite: `C1`–`C11`, `F1`–`F10`, `RC1`–`RC5`, `CY1`–`CY6` (CDD-048 §31) |

## 3. MODIFY (11) — narrow, additive only

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/domain/oqi/quality_rule.py` | Add `ACCURACY` to `QualityDimension` (CDD-048 §14); add the `ACCURACY` rows to `_ALLOWED_COMBINATIONS`; add `_validate_accuracy_parameters` following the exact shape of `_validate_consistency_parameters`; add `REFERENCE_VALUE_UNSUPPORTED` to `QualityFindingType`. No change to `COMPLETENESS`/`VALIDITY`/`CONSISTENCY` rows or any existing validation function. |
| 2 | `backend/app/domain/oqi_business_rule/rule.py` | Add the new `BusinessRulePurpose` closed vocabulary (CDD-048 §14) and a `dimension`/`purpose` field on `BusinessRule`, defaulted for existing construction paths to `LEGACY_UNCLASSIFIED_BUSINESS_RULE`; add the single-purpose-per-version invariant (CDD-048 §19.1). No change to `RuleFamily`, `Operator`, `ComparandKind`, the AST evaluation functions, or any existing `BusinessRule` field. |
| 3 | `backend/app/domain/oqi_business_rule/finding.py` | Add the new finding-type-equivalent field for `CONTEXTUAL_PLAUSIBILITY_VIOLATION`, defaulted for legacy rows. No change to `QualityFindingStatus`, `ResolutionBasis`, or existing transition logic. |
| 4 | `backend/app/domain/oqi_remediation/candidate.py` | Add exactly two new `RemediationCandidateBasis` members: `ACCURACY_REFERENCE_EVIDENCE`, `REASONABLENESS_CONTEXTUAL_RULE` (CDD-048 §24). No change to the existing four members or `__post_init__` validation shape beyond the isinstance check already present. |
| 5 | `backend/app/application/oqi_remediation_service.py` | `extract_candidates` gains dispatch on `quality_dimension` (via `QualityFindingOrigin`) for the two new bases, adding `extract_accuracy_candidates`/`extract_reasonableness_candidates` (CDD-048 §24). `_get_finding_state`'s existing 3-branch dispatch is unchanged (still keyed on `finding_storage_family`, itself unchanged). No change to `extract_oqi1_candidates`/`extract_oqi2_candidates`/`extract_oqi3_candidates`. |
| 6 | `backend/app/application/oqi_remediation_agent_service.py` | Mirror the identical, narrow `_get_finding_state`-adjacent change needed only if this file's own copy requires updating to construct `QualityFindingOrigin` alongside `FindingFamily` for consistency with row 5 — additive only, no change to agent advisory logic or authority. |
| 7 | `backend/app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py` | `resolve_finding_subject` additionally resolves and returns `quality_dimension` as part of its existing per-family row lookup (CDD-048 §12.3.1). No change to its physical-table dispatch shape or return type beyond this one additive field. |
| 8 | `backend/app/infrastructure/persistence/oqi_quality_coverage_policy_repository.py` | `has_qualifying_coverage_for_dimension` gains exactly two new branches, `ACCURACY` and `REASONABLENESS`, each an existence-only qualifying-evaluation query (CDD-048 §23). No change to the `COMPLETENESS`/`VALIDITY`/`CONSISTENCY` branches or the unconditional `False` fallback for `UNIQUENESS`/`TIMELINESS`/`INTEGRITY`/`CONFORMITY`. |
| 9 | `backend/app/api/oqi/schemas.py` | `FindingSummary`/`FindingDetailResponse` gain an additive `dimension: str` field (CDD-048 §29). No change to `finding_family: str`'s existing shape or any other field. |
| 10 | `backend/app/api/oqi/router.py` | Add the minimal reference-evidence-configuration, human-verification, and reference-evidence-conflict-read routes, gated respectively by `oqi-reference-evidence:configure`, `oqi-reference-evidence:verify`, and the existing `oqi:read` (CDD-048 §26/§29). No change to any existing route's behavior or scope requirement. |
| 11 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` | Add the Accuracy/Reasonableness demo flow (CDD-048 §30): seed raw evidence + a governed reference-evidence assertion + a `REASONABLENESS`-purpose `BusinessRule`, then invoke the new evaluator services (mirroring the existing OQI2 invocation pattern). No change to any existing seeded OQI1/OQI2/OQI3 fixture or invocation. |

## 4. Unauthorized paths

**ALL OTHERS.** Explicitly not authorized, called out because a reasonable implementer might assume otherwise: any OQI Command Center or dashboard redesign (CDD-048 §29, DEFER); `frontend/app/quality/findings/page.tsx`'s family dropdown or any other frontend file beyond what row 9/10 above expose through the existing unconstrained-`str` API shape (no frontend file is authorized to change in this phase); `keycloak/ctec-realm.json` beyond the two new `clientScope` entries for `oqi-reference-evidence:configure`/`:verify` required to make row 10 genuinely enforceable (this file MAY be modified, narrowly, for exactly those two entries plus their `optionalClientScopes` references — treated as implicitly authorized alongside row 10 since a scope named in row 10 without this entry would repeat the `oqi-coverage:configure` gap CDD-048 §4/§26 explicitly warns against; no other realm/client configuration may change); `.github/workflows/ci.yml` (the table-count re-pin is explicitly deferred to a separate, disclosed companion amendment per CDD-048 §28, never folded into this implementation); any file implementing Uniqueness, Timeliness, Integrity, or Conformity; any tenant-private reference-dataset authoring path (PO-02); any production orchestration/scheduler/event-trigger file; any autonomous-remediation logic; any `oqi-quality-rule:configure` route (named, not wired, CDD-048 §26); `architecture/INDEX.md` or any release-manifest file (this OQI CDD track has never registered there, per confirmed precedent — CDD-044 through CDD-047 are likewise absent); `docs/product/` (explicitly out of scope and untouched throughout H2-DR and H2-G).

**Advisory lock seed registry**: no new advisory-lock seed value is authorized or required by this phase — the new evaluators (Accuracy, Reasonableness) reuse the existing per-evaluator advisory-lock discipline (Accuracy, being OQI1-shaped, uses the existing seed `1`; Reasonableness, being OQI3-shaped, uses the existing seed `3`) with no new seed constant declared anywhere.

## 5. Migration

```
Expected revision (0028): 0028_oqi_h2_reference_evidence   (24 chars)
Expected down_revision:    0027_h1_coverage_policy
Expected revision (0029): 0029_oqi_h2_accuracy_dimension    (26 chars)
Expected down_revision:    0028_oqi_h2_reference_evidence
Expected revision (0030): 0030_oqi_h2_reasonableness_dimension (26 chars)
Expected down_revision:    0029_oqi_h2_accuracy_dimension

Pre-H2 table count:  102 (VERIFY FRESH at implementation time — this is the value confirmed
                            during H2-DR/H2-G discovery as of origin/main 132d6c744f4e99086b211871473d8e15b6e1d2e4;
                            re-derive, do not assume, if additional migrations have landed since)
Post-0028 table count: pre-count + 5
Post-0029 table count: post-0028 + 1  (one link table, oqi_quality_evaluation_reference_evidence)
Post-0030 table count: post-0029 + 0  (column additions only)
```
Required round-trip: `N → N+5 → N+6 → N+6 → N+6 → N+6+6 → N+6+1 → N+6` (each migration's own upgrade/downgrade/re-upgrade proven independently, then the full three-migration chain proven together) for every migration authorized here. Single Alembic head required at all times. No `0031` or any migration beyond the three named here is authorized by this document.

## 6. Implementation shape

Single implementation phase (`OQI-H2-I`) is expected. A split (e.g. Reference Evidence landing before Accuracy/Reasonableness evaluators) is permitted only if each sub-phase independently satisfies this Artifact Authorization's exact path list and migration ordering — introducing a genuinely new intermediate migration revision to accommodate a split is itself a STOP-worthy governance return, not a decision implementation may make unilaterally.

## 7. API / Frontend

Minimal, named exactly in row 9/10 above: two new authorization scopes wired end-to-end (Python + Keycloak), one additive response field, one read-only conflict-listing route. No frontend file authorized. No OQI Command Center change authorized.

## 8. Mandatory test matrix (binding on the 8 new test files, rows 12–19)

Every category in CDD-048 §31 (`A1`–`A13`, `R1`–`R10`, `F1`–`F10`, `RC1`–`RC5`, `CY1`–`CY6`, `C1`–`C11`) must be proven, tied to the exact CDD section it verifies: legacy OQI1/OQI2/OQI3 backward compatibility (`F1`–`F3`, `C1`–`C8`) proven against real Postgres using existing fixture data, never fabricated; Reference Evidence versioning/activation/conflict combinatorics (`RC1`–`RC5`) including the deliberately-adversarial conflicting-forms case; tenant isolation (`A8`, `R6`) proven the same way `test_cross_tenant_active_policy_lookup_returns_none` proves it for `QualityCoveragePolicy`; concurrency (advisory-lock reuse, no new seed, §4) proven not to deadlock against OQI1/OQI3's existing lock holders; PostgreSQL-specific constraints (active-uniqueness-per-form partial index, new CHECK constraints) proven to fail closed, never silently permit a second `ACTIVE` row; full regression suite (all pre-existing OQI1–OQI7 tests) must still pass unmodified; Docker/Compose/demo-seeder runtime proof (CDD-048 §32) required before any claim of H2-I completion.
