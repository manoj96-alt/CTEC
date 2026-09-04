# CDD-057 — Production-Orchestration R1 GA1: H5 Timeliness Crown Tenant-Scoped Test-Isolation Amendment

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-056-Production-OQI-Explicit-Evaluation-Orchestration.md` (governs this correction's own parent
implementation); the already-applied analogous tenant-scoping fix inside
`backend/app/tests/test_oqi_evaluation_orchestration_postgres.py` (§11 below)
Governs: `main` authoritative state `5e1a859df5c8608e7d5cfa0fe6b5b93e94119962`, unchanged since CDD-056's own
publication; PR `#191` (`production-orchestration/explicit-evaluation-trigger`), still `OPEN`, still
`UNMERGED`, head still the rejected `4cd7d812cc30727b19efbd86389d0fe08da6c760`
Classification: NARROW GOVERNANCE AMENDMENT — TEST-ONLY, ONE ADDITIONAL AUTHORIZED PATH, ZERO PRODUCTION
CODE, ZERO DOMAIN/SCHEMA CHANGE

## 1. Purpose

Authorizes exactly one additional test-only implementation path and exactly two narrow assertion
corrections inside it, discovered necessary by Production-Orchestration-I-R1's own full-backend regression
run. CDD-056's architectural decisions are not reopened, not reinterpreted, and not modified by this
document. This amendment exists solely so that the already-verified I-R1 correction (fixing VM's P0
transaction-boundary defect and P1 response-contract defect) can be committed without knowingly leaving a
newly-exposed, deterministic full-suite regression in place.

## 2. History (binding, restated for standalone traceability)

```
CDD-056 (Production-Orchestration-G) froze the explicit-evaluation-trigger architecture.
Production-Orchestration-I produced candidate 4cd7d812cc30727b19efbd86389d0fe08da6c760, PR #191.
Production-Orchestration-VM independently found:
    P0 -- transaction-boundary violation (one shared Session/transaction spanned DQ->OQI4->OQI6->Reliance;
          a genuine downstream DB failure discarded already-computed upstream DQ state and escaped as an
          unhandled exception instead of the documented graceful HTTP 202 + FAILED stage).
    P1 -- response-contract violation (`evaluation_id` exposed where CDD-056 SS9 requires `finding_id`).
    VM STOPPED. No merge.
Production-Orchestration-I-R1 corrected both defects inside CDD-056's own 4 authorized paths, proved the
    corrections adversarially against real PostgreSQL (genuine DBAPI-level failure injection, Session-
    recovery proof, retry-convergence proof, `finding_id` persisted-equality proof), and additionally
    strengthened the OQI6/Reliance shared-transaction proof beyond what VM had required.
I-R1's own full-backend run (`pytest app/tests`) then surfaced 2 NEW failures in
    `backend/app/tests/test_oqi_h5_timeliness_crown.py` -- a file entirely outside CDD-056 SS36's 4
    authorized paths. I-R1 correctly STOPPED rather than touch a 5th, unauthorized file.
This document (GA1) is the narrow governance response to that STOP.
```

## 3. Independent re-verification (binding)

Re-confirmed immediately before this document's own publication:
```
origin/main = local main = GitHub main = 5e1a859df5c8608e7d5cfa0fe6b5b93e94119962 (unchanged)
PR #191: OPEN, base=main(5e1a859...), head=4cd7d812cc30727b19efbd86389d0fe08da6c760 (unchanged, still rejected)
CDD-056 SHA-256 = 0b23f059289aae15e38fb3978fa00b6e8f3ad690f695426ede24d1d88d3e9c1a (unchanged)
migration head = 0044_oqi4_r1_current_tenancy (single head, unchanged)
table count = 123 (unchanged)
The uncommitted I-R1 correction (4 files: oqi_evaluation_orchestration_service.py, router.py, schemas.py,
    test_oqi_evaluation_orchestration_postgres.py) remains present, uncommitted, unmodified by this
    document's own publication -- independently re-fingerprinted before and after (SHA-256 per file, plus a
    SHA-256 of the full `git diff` against 4cd7d812... as a single combined fingerprint).
```

## 4. Independent reproduction of the newly-exposed failure (binding)

```
backend/app/tests/test_oqi_h5_timeliness_crown.py alone: 19/19 PASS.
    (Matches the I-R1 report's own claimed baseline exactly -- re-derived, not trusted.)
backend/app/tests/test_oqi_evaluation_orchestration_postgres.py
    + backend/app/tests/test_oqi_h5_timeliness_crown.py, same collection order `pytest app/tests` itself
    uses (alphabetical -- "e" precedes "h"):
        test_stale_evidence_is_violated                       FAILS
        test_repeated_identical_evaluation_is_idempotent      FAILS
        33 passed, 2 failed (reproduced twice, identical both times)
```
Both failing assertions are genuine `AssertionError`s (`2 == 1`), not errors, not flakes, not timing-
dependent -- fully deterministic given the fixed collection order.

## 5. The two actual failing assertions (binding, re-derived from current source, not trusted line numbers)

Located directly in current source (not from any prior report's claimed line numbers):
```
backend/app/tests/test_oqi_h5_timeliness_crown.py:439-440 (inside test_stale_evidence_is_violated)
    findings = session.execute(select(TimelinessEvaluationORM)).all()
    assert len(findings) == 1

backend/app/tests/test_oqi_h5_timeliness_crown.py:723-724 (inside test_repeated_identical_evaluation_is_idempotent)
    rows = session.execute(select(TimelinessEvaluationORM)).all()
    assert len(rows) == 1  # second call was a genuine no-op, not a duplicate
```
Both are unscoped, whole-table `select(TimelinessEvaluationORM)).all()` counts. Both tests already have a
live, in-scope `tenant_id` local variable (from `_setup_freshness_scenario(session)`) that is simply not
applied to the query.

## 6. Extra-row provenance (binding, independently proven)

A standalone investigation script (never committed, scratch-only) reproduced exactly
`test_oqi_evaluation_orchestration_postgres.py::test_timeliness_evaluated_through_orchestrator`'s own fixture
(a fresh, random `tenant-{uuid4()}`, one governed `TimelinessPolicy`, one piece of fresh evidence) and called
the corrected `OqiEvaluationOrchestrationService.evaluate(...)` directly, then queried
`timeliness_evaluations` before any H5 test ran. Result:
```
Total rows in the whole table: 1
evaluation_id=f3e6376d-a277-56de-8454-d93b06643348
tenant_id=tenant-c85394c6-2303-4475-86eb-6cb6e8941ac3 (the orchestration test's own synthetic tenant)
finding_type=STALE_SOURCE_EVIDENCE
outcome=SATISFIED
All rows belong to the orchestration test's own tenant: True
```
This is a single, genuine, correctly-computed, correctly-committed SATISFIED Timeliness evaluation for an
entirely unrelated, randomly-generated tenant -- not a duplicate, not corrupt, not a stray H4 or other-
dimension row. It exists specifically because the I-R1 correction's own fix (each DQ dimension, including
Timeliness, now commits durably in its own transaction immediately after success, per CDD-056 SS22) makes
this row survive to the database at all.

Confirmed by direct source inspection: `test_timeliness_evaluated_through_orchestrator` calls
`_orchestrator(session).evaluate(...)` and never itself calls `session.commit()` afterward -- its own
Timeliness row's durability depends entirely on the orchestrator's own internal commit. Under the *rejected*
`4cd7d812...` candidate (no internal per-stage commits), this same row would never have reached the database
at all when the `with factory() as session:` block exited without an explicit commit -- which is precisely
why Production-Orchestration-VM's own full-backend run (`2086 passed, 8 failed`, zero H5 failures) never
observed this interaction. The newly-exposed H5 failures are a direct, provable *consequence of the P0 fix
being correct*, not a new defect introduced by it.

## 7. H5 governance semantic analysis (binding)

Read directly from `CDD-051-OQI-H5-Governed-Timeliness.md`: `TimelinessPolicy`/`TimelinessEvaluation`
carry `tenant_id VARCHAR(200) NOT NULL` as a first-class column; H5's own governed uniqueness constraints
are explicitly tenant-qualified (e.g. `UNIQUE (tenant_id, information_element_requirement_id,
business_process_id, business_process_version)` for policies). No clause anywhere in CDD-051 or its
Artifact Authorization requires or even references a *global*, cross-tenant `TimelinessEvaluation` row-count
invariant. `TimelinessEvaluation` is unambiguously tenant-owned state.

## 8. Global-vs-tenant-cardinality decision (binding)

Both assertions' semantic intent, confirmed by test name, fixture, and (for the idempotency test) the
test's own inline comment ("second call was a genuine no-op, not a duplicate"), is **Option B**: *exactly N
Timeliness evaluations exist for the tenant/subject this specific test created* -- never Option A (global
database cardinality). Freezing the general principle this document authorizes:
```
A tenant-isolated OQI test must assert over the tenant-owned state created by that test, unless the test
explicitly exists to verify global database cardinality (no such test exists in this file).
```
This is not a weakening of either test -- both continue to prove exactly what they always claimed to prove
(one genuine VIOLATED Finding; one genuine idempotent no-op), now correctly scoped to the state each test
itself is responsible for, matching this whole test suite's own tenant-isolation architecture.

## 9. Rejected alternative (binding)

Explicitly considered and rejected: leaving both assertions unscoped and reclassifying the 2 new failures as
an "accepted test-order artifact," alongside the 7 pre-existing `test_ontology_api.py` failures and the 1
pre-existing changed-files-allowlist failure. Rejected because a narrow, semantically-correct, precedented
tenant-scoping correction is available and sufficient to restore a fully green crown; accepting a known,
deterministic, reproducible full-suite failure when a minimal fix exists would abandon this whole campaign's
own standard (`full regression green`, not `green except known order-dependent failures`).

## 10. H5 governance re-confirmed unmodified

This document authorizes no change to H5 domain semantics, freshness thresholds, ingestion-latency
semantics, policy setup, Finding identity derivation, evaluation-history behavior, or idempotency behavior.
`CDD-051` and its own Artifact Authorization remain frozen, untouched, independently re-confirmed unchanged.

## 11. Existing precedent (binding, re-derived)

`backend/app/tests/test_oqi_evaluation_orchestration_postgres.py` already contains four instances of the
identical correction pattern, applied during this same campaign's earlier phases:
```
select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_a)     (lines 304, 315)
select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)    (lines 374, 606)
```
each replacing an original unscoped `select(QualityEvaluationORM)).all()` for exactly the same reason: a
blanket whole-table count is unsafe once more than one legitimate tenant's rows can exist in the same
session-scoped database across a combined test run. This precedent supports consistency of style; it does
not by itself authorize the H5 change, which is separately justified in SS6-SS9 above.

## 12. Exact additional path authorization (binding — a maximum permitted write set)

```
GA1 adds exactly ONE additional path to CDD-056 SS36's existing four:

MODIFY (TEST-ONLY)  backend/app/tests/test_oqi_h5_timeliness_crown.py
    Exactly two corrections, both of the same shape: an unscoped `select(TimelinessEvaluationORM)).all()`
    becomes `select(TimelinessEvaluationORM).where(TimelinessEvaluationORM.tenant_id == tenant_id)`, using
    each test's own already-in-scope `tenant_id` local variable (from `_setup_freshness_scenario`). No
    other line in this file may change.
```
Combined with CDD-056 SS36, the complete amended Production-Orchestration-I-R1 path set is:
```
backend/app/application/oqi_evaluation_orchestration_service.py     (CDD-056, unchanged by GA1)
backend/app/api/oqi/router.py                                       (CDD-056, unchanged by GA1)
backend/app/api/oqi/schemas.py                                      (CDD-056, unchanged by GA1)
backend/app/tests/test_oqi_evaluation_orchestration_postgres.py     (CDD-056, unchanged by GA1)
backend/app/tests/test_oqi_h5_timeliness_crown.py                   (GA1, this document, TEST-ONLY)
```
`TOTAL = 5`. No sixth path. No production code in the GA1 path.

## 13. Forbidden changes inside the GA1 path (binding, exhaustive)

Inside `test_oqi_h5_timeliness_crown.py`, forbidden: deleting any assertion; weakening any expected count
beyond the two named corrections; changing any expected Timeliness outcome, finding type, or threshold;
changing policy setup or fixture architecture; changing Finding/evaluation identity derivation; changing
idempotency expectations beyond correctly scoping the count; adding blanket cleanup, table truncation, or
cross-test database resets; changing any other test's fixture; adding test ordering, `pytest-order`
dependencies, sleeps, or retries; marking any test `flaky` or `xfail`; skipping any test. The only
authorized transformation is `GLOBAL TABLE COUNT -> TENANT-SCOPED TABLE COUNT`, exactly twice.

## 14. Verification contract (binding, restated for resumed I-R1)

Resumed Production-Orchestration-I-R1 must prove, after applying exactly the two authorized corrections:
```
test_oqi_h5_timeliness_crown.py alone            = 19/19 PASS (unchanged from today's baseline)
test_oqi_evaluation_orchestration_postgres.py
    + test_oqi_h5_timeliness_crown.py, alphabetical order = fully green (the 2 named failures gone)
CDD-056 SS49 frozen 11-file regression matrix     = fully green except only the independently-adjudicated,
    pre-existing changed-files-allowlist failure (never the 2 H5 failures this document authorizes fixing)
pytest app/tests (full backend)                   = no longer contains either of the 2 named H5 failures;
    the 7 pre-existing test_ontology_api.py cache-ordering failures and the 1 pre-existing changed-files-
    allowlist failure remain separately, previously adjudicated, out of this document's scope
migration head                                    = 0044_oqi4_r1_current_tenancy (unchanged)
table count                                       = 123 (unchanged)
whole-package static quality (black/isort/ruff/mypy) = clean on all 5 amended paths
```
Fresh `--no-cache` Docker verification (transaction-boundary attack, `finding_id` contract, all nine
dimensions, OQI1, cross-tenant attack, idempotent retrigger, authenticated HTTP success, health, and the
combined Production-Orchestration + H5 regression) remains resumed-I-R1's own responsibility, not GA1's.
Strengthened multi-source Consistency and all-three-Reliance-state proofs, and the governed concurrency
attack, remain frozen as mandatory before Production-Orchestration-VM-R1 (carried forward from I-R1's own
report, unchanged by this document).

## 15. Deferred register (restated, unchanged)

```
P2 -- OQI2 QualityComparisonFindingORM.latest_evaluation_id tenant-pointer observation
P2 -- OQI3 BusinessRuleFindingORM.latest_evaluation_id tenant-pointer observation
P2 -- OQI4->OQI6 considered_current_impact_id structural observation
P3 -- Reliance evaluation-history replay sensitivity
P3 -- frontend Docker internal-loopback healthcheck discrepancy
Capability gap -- zero working real production connectors
```
None authorized for correction by this document.

## 16. Schema/migration firewall (binding)

```
NO SCHEMA CHANGE
NO MIGRATION
NO ORM CHANGE
```
This document authorizes test-file bytes only.

## 17. Governance byte-integrity

`CDD-056` is re-hashed immediately before and after this document's own publication and confirmed
byte-identical both times (`0b23f059289aae15e38fb3978fa00b6e8f3ad690f695426ede24d1d88d3e9c1a`); it is not
modified by this document. `architecture/INDEX.md` independently confirmed to list none of CDD-053/054/055/
056; this document follows the same established precedent and requires no index update. The uncommitted
Production-Orchestration-I-R1 implementation diff (4 files, against candidate `4cd7d812...`) is independently
fingerprinted (per-file SHA-256, plus a SHA-256 of the combined `git diff`) both immediately before and
immediately after this document's own publication, and confirmed byte-identical both times.

## 18. Phase sequence (binding, restated)

```
Production-Orchestration-R1-GA1  (this document)
        |
resume Production-Orchestration-I-R1 (apply exactly the two authorized corrections; full verification
        contract per SS14; fresh --no-cache Docker; commit the corrected 5-file candidate only after)
        |
push PR #191
        |
exact-head CI
        |
Production-Orchestration-VM-R1
```
Do not skip directly to VM-R1. Do not merge PR #191 as part of this document's own publication.

## 19. Authorization

This document is approved and published as a standalone, narrow governance amendment companion to
CDD-056. Resumed Production-Orchestration-I-R1 may proceed against exactly the one additional path and two
corrections authorized in SS12-SS13.
