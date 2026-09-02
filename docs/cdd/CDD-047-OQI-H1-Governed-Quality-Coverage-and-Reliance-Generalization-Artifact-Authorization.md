# CDD-047 OQI-H1 Governed Quality Coverage + Reliance Generalization — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** exact OQI-H1-I implementation surface. No wildcard authorization. No directory-level
grant. Any path not named below is unauthorized — OQI-H1-I must STOP and return for a governance
amendment rather than touch it.

## 1. Accounting

```
CREATE = 9
MODIFY = 4
DELETE = 0
TOTAL  = 13
```

## 2. CREATE (9)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/domain/oqi_quality_coverage/__init__.py` | package marker |
| 2 | `backend/app/domain/oqi_quality_coverage/policy.py` | `CoverageDimension` closed StrEnum (CDD-047 §4); `QualityCoveragePolicy`, `QualityCoveragePolicyStatus` domain dataclasses; deterministic identity/versioning helpers; construction-time validation (non-empty `required_dimensions`, no duplicate, closed vocabulary only) |
| 3 | `backend/app/infrastructure/persistence/models/oqi_quality_coverage_policy.py` | `QualityCoveragePolicyORM` (single-column `policy_id` PK, `previous_version_id` self-FK, partial unique index on `(tenant_id, ontology_element_type, ontology_element_id)` `WHERE status='ACTIVE'` — CDD-047 §10-§11), `QualityCoveragePolicyDimensionORM` (composite `(policy_id, dimension)` key, `dimension` column constrained to the closed `CoverageDimension` vocabulary) |
| 4 | `backend/app/infrastructure/persistence/oqi_quality_coverage_policy_repository.py` | policy insert/version-chain read, active-version lookup by anchor, `compute_generalized_coverage` (CDD-047 §13), `has_qualifying_coverage_for_dimension` dispatch across `CoverageDimension` members (delegating to rows 12/13 below for `COMPLETENESS`/`VALIDITY`/`CONSISTENCY`, returning `False` unconditionally for the other six — CDD-047 §14), the relationship-boundary fallback (CDD-047 §15) |
| 5 | `backend/app/infrastructure/persistence/migrations/versions/0027_oqi_h1_quality_coverage_policy.py` | creates the 2 tables in row 3; `revision="0027_oqi_h1_quality_coverage_policy"`, `down_revision="0026_oqi6_reliance"` |
| 6 | `backend/app/tests/test_oqi_quality_coverage_policy_domain.py` | domain construction, identity/versioning, closed-vocabulary validation, empty/duplicate-dimension rejection |
| 7 | `backend/app/tests/test_oqi_quality_coverage_policy_service.py` | fake-repo: `compute_generalized_coverage` for all cases in CDD-047 §18 truth table, §12 unsupported-dimension behavior, §15 relationship boundary, exception-propagation-never-defaults-True proof |
| 8 | `backend/app/tests/test_oqi_quality_coverage_policy_postgres.py` | real-Postgres: partial active-uniqueness index (concurrent activation → exactly one succeeds), dimension-table closed-vocabulary constraint, migration round-trip, tenant isolation for policy rows |
| 9 | `backend/app/tests/test_oqi_h1_reliance_coverage_crown.py` | the CDD-047 §20 crown proof (`PARTIAL REQUIRED COVERAGE ≠ SUPPORTED`); the full §18 backward-compatibility truth table as executable no-policy-branch identity tests; `NO FINDINGS ≠ TRUSTED` re-verified unaffected; §15's relationship-anchor-never-achieves-True proof |

## 3. MODIFY (4) — narrow, additive only

Every row below is bounded to exactly the addition named. No other line in these files may change.

| # | Path | Permitted modification |
|---|---|---|
| 10 | `backend/app/infrastructure/persistence/oqi_quality_evaluation_repository.py` | add one new method, `has_qualifying_coverage_for_dimension(tenant_id, source_object_ids, dimension)` — `quality_evaluations JOIN quality_rules ON rule_id WHERE quality_rules.dimension = ? AND ...` (CDD-047 §14). No change to any existing method, including the untouched `has_any_evaluation_for_source_objects`. |
| 11 | `backend/app/infrastructure/persistence/oqi_cross_source_evaluation_repository.py` | add one new method, `has_qualifying_coverage_for_dimension(tenant_id, source_object_ids, dimension)` — for `dimension == CONSISTENCY`, delegates to the existing, unmodified `has_any_evaluation_for_source_objects` query verbatim; for any other dimension, returns `False` without querying (CDD-047 §14). No change to any existing method. |
| 12 | `backend/app/infrastructure/persistence/oqi_business_impact_repository.py` | generalize the `_compute_coverage` call site inside `compute_subject_finding_state` to route through the new `QualityCoveragePolicyRepositoryImpl.compute_generalized_coverage` per CDD-047 §13/§17, passing the existing, unmodified `_compute_coverage`-derived value as `legacy_any_evaluation_ever_run`. No change to `_compute_coverage` itself, to the open-Finding `UNION ALL` query, or to `acquire_current_projection_authority`. |
| 13 | `backend/app/application/oqi_business_impact_service.py` | no change to `derive_reliance_state`'s call shape beyond the value now flowing from row 12's generalized computation (CDD-047 §17). The `any_active_impact_unknown=False` line is explicitly **not** touched (CDD-047 §26). No change to `evaluate_business_impact_for_dependency` or any Business Process/Dependency authoring method. |

## 4. Unauthorized paths

**ALL OTHERS.** In particular, explicitly unauthorized without a further governance amendment:
`backend/app/domain/oqi/quality_rule.py` (`QualityDimension`, `_ALLOWED_COMBINATIONS` — CDD-047 §5);
`backend/app/domain/oqi_business_impact/reliance.py` (`derive_reliance_state` itself — CDD-047 §17);
`backend/app/domain/oqi_ontology_impact/evaluation.py` (`CurrentImpactStatus` — CDD-047 §26); any OQI3/
business-rule domain, persistence, or repository file (H1 touches no OQI3-shaped coverage path — CDD-047
§14 explicitly returns `False` unconditionally for the dimensions that would require it); any change to
`EntityResolutionStore`/`identity_resolution` (H1 reads the existing tenant-scoped
`_resolve_source_object_ids_for_entity` path unmodified, via row 12, never writes to it); any API route
file (`backend/app/api/oqi/router.py` or any other); any frontend file; `keycloak/ctec-realm.json` or any
other authorization-configuration file — **no route enforces `oqi-coverage:configure` in H1** (CDD-047
§22, §24), so no scope registration is authorized or required this phase; any Docker/Compose/CI
configuration file (verification against the existing pipeline is required, per §8 below, but no
configuration file changes are authorized); any demo-seeder file (the seeder must remain
behaviorally unaffected — proving that requires zero seeder code change, per CDD-047 §18/§23); any new
advisory-lock seed constant beyond exactly one new value, `5`, declared inside row 4 above (distinct from
the existing `1`/`2`/`3`/`4` — no other file may declare or reference it).

## 5. Migration

```
Expected revision:       0027_oqi_h1_quality_coverage_policy
Expected down_revision:  0026_oqi6_reliance
Pre-H1 table count:      TO BE VERIFIED FRESH AT IMPLEMENTATION TIME — NOT assumed as 100.
                          (CDD-046 §46's own pre-implementation estimate was 94→100 for OQI6;
                          OQI-H1-DR's own proxy check was inconclusive and explicitly deferred
                          exact verification to implementation, per that report's own discipline.)
Post-H1 table count:     Pre-H1 count + 2 (exactly two new tables — row 3 above).
```

Round-trip required: `N → N+2 → N → N+2` (where `N` is the freshly-verified pre-H1 count), single
Alembic head, no `0028` introduced by this authorization.

## 6. Implementation shape

`SINGLE OQI-H1-I` (CDD-047, no explicit split authorized). If implementation discovers a genuine
correctness boundary requiring a split (not merely convenience), that is itself a STOP-worthy finding
requiring a return to governance, per CDD-047 §29 — not a decision implementation may make unilaterally.

## 7. API / Frontend

`NONE`. Not authorized by this document under any circumstance (CDD-047 §24).

## 8. Mandatory test matrix (binding on the 4 new test files, rows 6-9)

Legacy compatibility: no-policy + OQI1 evaluation, no-policy + OQI2 evaluation, no-policy + no
evaluation, all reproducing exact pre-H1 output via the unmodified `_compute_coverage`/
`derive_reliance_state` code paths; existing `ReasonCode` values unchanged (CDD-047 §19). Policy
coverage: one required dimension covered; one uncovered; three required, all covered; three required,
one missing; nine required, only three covered; open Finding still yields `AT_RISK` regardless of
coverage state; `RETIRED` policy does not govern; a new `ACTIVE` version supersedes a retired one
correctly; two `ACTIVE` versions structurally impossible (real-Postgres). Explainability: missing
required dimension identifiable; the specific evaluation proving a covered dimension identifiable.
Tenant: cross-tenant policy read/activate/retire denied; cross-tenant evaluation cannot satisfy
coverage; cross-tenant anchor reference rejected. Concurrency: concurrent activation attempts on the
same anchor — exactly one succeeds (real-Postgres); repeated coverage derivation is idempotent.
PostgreSQL: partial active-uniqueness index; dimension child-table constraint rejects an unknown
value; migration up/down/up. Regression: every existing test in `test_oqi_business_impact.py` (all 27,
including the three tenant-isolation crown tests) passes unmodified. Docker: image build; migration
inside Docker with the exact table-count assertion from §5; Compose health; demo seeder produces
identical output with zero policy rows created; a manually-created `ACTIVE` policy in a running Docker
environment demonstrably produces `RELIANCE_UNKNOWN` for a subject with genuinely partial coverage —
a real runtime proof, not merely a unit test, per CDD-046 §45's binding Docker/runtime requirement
(unchanged and restated by CDD-047 §29).
