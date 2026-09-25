# CDD-085 / CDD-086 — Golden/Parity Test-Fixture Transaction Isolation Amendment (NOETVA-CI-BACKEND-ISOLATION-G-R1)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-085-Artifact-Authorization-G-R1-Entity-Resolution-Flush-Ordering-Amendment.md` (the direct
precedent for this exact governance shape: a real, adversarially-reproduced CI defect, root-caused across a
DR → G(STOPPED) → DR-R1 → G-R1 chain, closed by the narrowest correct fix, frozen as a standalone additive
amendment rather than reopening either frozen architecture document); `CDD-084-Artifact-Authorization-H6-G-R1-
Frontend-Test-Path-And-U19-Correction-Amendment.md` (further precedent for a narrow test-path-only amendment)
Classification: TEST-INFRASTRUCTURE DEFECT (two test fixtures durably committing `DemoOqiSeeder` seed data to
the single physical CI database that migration round-trip tests also share) — **not** a production defect,
**not** a migration defect, **not** a CI-workflow defect. Production `DemoOqiSeeder` behavior is correct for
its actual contract (ordinary idempotency on a fully-migrated schema); the defect is that two test fixtures
leave durable, cross-test-visible committed rows that a later, unrelated partial-migration-downgrade test
(exercising a different, legitimate concern — migration `downgrade()` correctness) can collide with.
Governs: this amendment only. `CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md` and its own
original companion Artifact Authorization, `CDD-085-Artifact-Authorization-G-R1-Entity-Resolution-Flush-
Ordering-Amendment.md`, `CDD-086-Generic-Finding-Detail-Parity.md`, and its own companion Artifact
Authorization are all unmodified, unreopened, and remain FROZEN exactly as originally published.

## 1. Purpose

Authorizes the exact, narrow, additive, test-only correction that closes the CI failure blocking PR #248
(`product/noetva-demo-readiness-r1` @ `e9a04bba956ab88694b9113856961436f23661a5`):

```
FAILED app/tests/test_oqi_h4_integrity_crown.py::TestH1H2H3NonRegression::
test_full_demo_seeder_preserves_every_prior_phase_outcome
sqlalchemy.exc.IntegrityError: (psycopg.errors.UniqueViolation) duplicate key value violates unique
constraint "source_systems_pkey"
```

reproduced deterministically on two independent real GitHub Actions CI runs and independently re-reproduced,
byte-identically, in this program's own local investigation across NOETVA-CI-BACKEND-ISOLATION-DR,
NOETVA-CI-BACKEND-ISOLATION-G (STOPPED — the originally-scoped production-hardening fix was empirically
proven insufficient), NOETVA-CI-BACKEND-ISOLATION-DR-R1 (identified the correct contract owner and proved a
complete fix), and this phase's own independent revalidation (§3-§7).

## 2. Context — independently re-verified this phase, not merely trusted from DR-R1's report

```
origin/main                                  91e90b5812a123d08d58e78347f7283d285921f6  (independently
                                              re-fetched and re-confirmed this phase; matches expected)
product/noetva-demo-readiness-r1 (blocked)   e9a04bba956ab88694b9113856961436f23661a5  (unchanged; not
                                              amended, rebased, force-pushed, committed to, or merged by
                                              this phase — confirmed by `git rev-parse` immediately before
                                              and after this phase's own work)
PR #248                                      OPEN, headRefOid e9a04bba... unchanged (independently
                                              re-queried via `gh pr view 248`)
product/noetva-demo-readiness-g-r2 (local)   confirmed 0 commits ahead of origin/main, never pushed; not
                                              reused as a governance artifact by this phase (§37 of the
                                              governing prompt)
```

**Prior phase chain, independently re-derived facts (not merely cited):**

- NOETVA-CI-BACKEND-ISOLATION-DR root-caused the collision to: CI's long-standing, load-bearing
  `CTEC_DATABASE_URL == CTEC_TEST_DATABASE_URL` aliasing (a single-Postgres-service simplification present
  since this project's first CI commit, not itself a defect) + a partial migration downgrade (to
  `0025_oqi5_agent_reasoning`) run by an unrelated migration round-trip test between two committing seed
  fixtures — which drops `oqi_business_dependencies` (migration `0026`) while `source_systems` (migration
  `0001`) and `quality_rules` (migration `0020`) survive with their data intact, fooling `_seed_context()`'s
  existence-proxy guard (`if rule_repo.get_active(...) is not None and existing_dependencies: return ...`)
  into re-running its unconditional `SourceSystem` inserts against rows that already exist.
- NOETVA-CI-BACKEND-ISOLATION-G correctly STOPPED rather than freeze the originally-proposed
  "`SourceSystem`-only guard" fix: empirical monkeypatch testing proved it insufficient (collision moves to
  `SourceObject`), and even a comprehensive generic per-row primary-key guard across all 28 surviving rows
  across 12+ model types in `_seed_context()`'s full H1-H6 call graph still failed — on a *domain-level*
  `ValidationException` from `semantic_mapping_repository.py:188` ("An Approved SemanticMapping already
  exists for source_field_id..."), a natural-key business invariant no primary-key guard can satisfy.
- NOETVA-CI-BACKEND-ISOLATION-DR-R1 (this session, immediately prior to this phase) determined the correct
  contract owner is **test-fixture isolation, not production hardening** (§4 below), and proved a complete
  fix end-to-end. This phase independently re-derives and re-verifies that proof from scratch rather than
  freezing it on trust.

## 3. Independent re-verification of the DR-R1 decisive chain (§5 of the governing prompt)

All five facts independently re-confirmed this phase, by direct source read and/or fresh reproduction:

```
A. demo-reset (backend/app/infrastructure/persistence/database_cli.py) performs downgrade(base) ->
   upgrade(head) -> reseed — confirmed by direct read of docs/demo/NOETVA-GOLDEN-DEMO-RUNBOOK.md §2 and the
   demo_reset() implementation; it never performs a partial-revision downgrade.        CONFIRMED
B. No real product/operator path calls DemoOqiSeeder.seed() against an arbitrary mixed partial-migration
   state; the only two seed()-adjacent lifecycles are (i) ordinary re-seed on an unchanged, fully-migrated
   schema, and (ii) demo-reset's full base-wipe cycle.                                  CONFIRMED
C. Partial-revision downgrade states are created exclusively by migration round-trip tests (e.g.
   test_oqi_business_impact.py, test_oqi_api_postgres.py, test_oqi_cross_source_postgres.py and others),
   verifying alembic downgrade()/upgrade() correctness for their own migration — a legitimate, unrelated
   test concern.                                                                        CONFIRMED
D. Ordinary DemoOqiSeeder idempotency (seed() -> seed() again, same fully-migrated schema) remains a real,
   tested contract — test_d1_golden_supplier_deterministic_and_idempotent exercises exactly this, across two
   genuinely separate Session/connection objects, and must keep passing unchanged (§8 below).  CONFIRMED
E. Production-wide partial-migration recovery is not a contract DemoOqiSeeder ever promised or needs; it was
   never exercised by demo-reset, docker-entrypoint.sh, or any other production caller — only by the
   accidental interaction between two test fixtures' commits and unrelated migration tests' schema surgery.
                                                                                          CONFIRMED
```

No fact in this chain was found false. Per §5's own instruction, this phase did not STOP.

## 4. Fresh control reproduction (this phase's own, independent of DR-R1's)

```
Container:    genuinely fresh postgres:16, port 55471, never touched before this run
Worktree:     disposable scratch worktree at the unmodified candidate SHA e9a04bba..., verified clean
              (git status --porcelain empty) before and after
Invocation:   bare `pytest -q --no-header`, CTEC_DATABASE_URL == CTEC_TEST_DATABASE_URL, coverage on — the
              exact CI-faithful invocation
Result:       1 failed, 2316 passed — IDENTICAL to both real CI runs and to DR-R1's own reproduction:
              FAILED app/tests/test_oqi_h4_integrity_crown.py::TestH1H2H3NonRegression::
              test_full_demo_seeder_preserves_every_prior_phase_outcome
```

## 5. Why production hardening remains rejected (restated, independently re-confirmed)

`_seed_context()` calls `_seed_h2_context()` through `_seed_h6_context()` in sequence (confirmed by direct
read, `demo_oqi_seeder.py:636-640`); `SemanticMapping` rows are created unconditionally at two call sites,
`_seed_h3_context()` (line 889) and `_seed_h5_context()` (line 1370), each enforcing a strict one-Approved-
mapping-per-`(information_element_requirement_id, tenant)` natural-key invariant
(`semantic_mapping_repository.py:188`). A primary-key-based guard, however comprehensive, cannot satisfy a
natural-key/business-invariant uniqueness violation. Hardening every H1-H6/Aurora creation site to survive an
arbitrary, product-impossible mixed-schema state (§3 items A/B/E) would require cross-cutting changes to
domain identity/uniqueness handling across at least 12+ unrelated model types spanning multiple bounded
contexts — for a scenario that occurs nowhere in real operation. This amendment does not authorize any such
change.

## 6. The frozen mechanism — SQLAlchemy external-transaction / SAVEPOINT join

```
1. obtain a Connection directly from the already-migrated engine (migrated_engine.connect())
2. begin one outer transaction on that Connection (connection.begin())
3. construct a sessionmaker bound to that Connection, not the engine
4. configure join_transaction_mode="create_savepoint" on that sessionmaker
5. every Session created from that sessionmaker joins the SAME outer transaction; each Session's own
   session.commit() releases a SAVEPOINT rather than committing to the physical database
6. production code under test (DemoOqiSeeder, OntologySeeder, BlueprintSeeder) calls session.commit() exactly
   as it always has — its own commit semantics, and the tests' own cross-Session visibility guarantees, are
   fully preserved (§8)
7. at fixture teardown, the ONE outer transaction is rolled back and the Connection closed — every row any
   nested Session ever "committed" is undone; nothing is ever visible to any other Connection
```

This is SQLAlchemy 2.0's own documented pattern for joining a Session into an external transaction for test
isolation (`join_transaction_mode="create_savepoint"`, available in the pinned `sqlalchemy>=2.0,<3`;
independently confirmed installed version `2.0.43` supports it). The purpose is explicitly **not** to
suppress or replace commits with flushes (§9 of the governing prompt) — the tests continue to exercise real
commit behavior; only the outermost, physical-database boundary changes.

## 7. Empirical revalidation — every required crown, this phase's own fresh runs

All runs performed against a genuinely fresh Postgres 16 container (port 55471), the unmodified candidate
worktree with the two-file correction applied *only in an uncommitted, disposable scratch copy, reverted
before this phase concluded* — no repository write occurred as part of proving this.

```
Golden alone       (test_noetva_demo_readiness_golden_story.py):                18 passed   (§24 baseline)
Parity alone       (test_generic_finding_detail_parity.py):                     23 passed   (§25 baseline)
Parity -> Golden   (combined, natural alphabetical order):                      41 passed   (§26)
Golden -> Parity   (combined, reversed order):                                  41 passed   (§26 — no order
                                                                                              dependence)
Parity+Golden+H4   (exact natural collision trio, unfiltered):                  73 passed   (§22/§23)
H4 crown alone     (test_oqi_h4_integrity_crown.py, fully unfiltered):          32 passed   (§23)
Full CI-faithful suite (bare pytest, coverage on, exact CI DB-URL aliasing):    2316 passed, 1 failed (§27)
```

The sole remaining failure, both in this phase's own reproduction and independently reconfirmed as a
scratch-worktree artifact (§9), is `test_runtime_architecture.py::test_changed_files_
match_cdd_010_and_cdd_012_exhaustive_allowlists` — not a product, test, or CI regression.

## 8. Cross-session D1 preservation — explicitly verified, not assumed

`test_d1_golden_supplier_deterministic_and_idempotent` (`test_noetva_demo_readiness_golden_story.py:138-160`)
opens a **second, genuinely distinct** `Session` object via
`sessionmaker(bind=session.get_bind(), join_transaction_mode="create_savepoint")()`, calls
`DemoOqiSeeder(second_session).seed()`, commits it, and then re-queries via the **original**, still-open
`session` object to confirm no duplicate row was created. Both Session objects are distinct Python objects
issuing genuinely separate SQL statements; `join_transaction_mode="create_savepoint"` makes the *second*
Session's commit a SAVEPOINT release joined to the *same* underlying Connection/outer transaction as the
first, so the first Session's subsequent query correctly observes the second Session's just-committed
row — preserving the test's real, intended cross-Session idempotency proof. This was independently confirmed
by this phase's own §7 run: `test_d1` passed inside the 18/18 Golden-alone crown, unchanged. The correction
does **not** collapse "two sessions" into one shared ORM Session object — each `factory()`/`sessionmaker()`
call still returns its own new `Session`; only the underlying `Connection` and its SAVEPOINT chain are
shared.

## 9. Scratch-diff allowlist disposition (§28 of the governing prompt)

Independently re-confirmed: `test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists` failed in
both the unmodified baseline run and the corrected run, in this phase's disposable scratch worktree, solely
because that worktree carried uncommitted edits to the two named test files at the moment that specific test
executed (`git status`/`git diff` subprocess calls inside the test see the scratch worktree's own uncommitted
state). The assertion failure explicitly names the two edited paths as "Extra items in the left set" —
direct proof of the cause. This is not a product, test-semantics, or CI regression; it will not occur against
a real committed candidate branch, and must not be treated as a genuine allowlist gap. No allowlist file may
be modified to work around it; none is authorized by this amendment.

## 10. Static-gate note (formatter shape, not semantics)

`ruff check` on both corrected files: **all checks passed** (no lint violation introduced). `ruff format
--check`: the corrected `test_noetva_demo_readiness_golden_story.py` line
`with sessionmaker(bind=session.get_bind(), join_transaction_mode="create_savepoint")() as second_session:`
exceeds the project's configured line length and must be wrapped by the repository's own formatter at
implementation time (mirroring the exact multi-line call-wrapping the formatter already produces for other,
pre-existing long lines in this same file, independently confirmed present in the *unmodified* candidate —
two pre-existing format-check findings at unrelated lines, confirmed NOT introduced by this correction, via a
before/after `git stash` comparison). Per §8 of the governing prompt ("exact syntax may follow repository
conventions"), implementation must run the project's formatter over its two changed files rather than hand-
wrap; no other line may be reformatted as opportunistic cleanup.

## 11. Amendment authorization — effective Artifact Authorization (two documents amended)

Because the Golden test file exists only in the still-open candidate (governed by CDD-085's own AA) and the
Parity test file already exists on authoritative main (governed by CDD-086's own AA, already merged via PR
#247), this single amendment authorizes one MODIFY row against **each** of those two Artifact Authorizations.
Neither original AA document, nor CDD-085's own G-R1 amendment, is reopened or rewritten; both are amended
by addition only, exactly as this program's convention requires.

**Against `CDD-086-Generic-Finding-Detail-Parity-Artifact-Authorization.md` (effective on `main`):**

```
MODIFY  backend/app/tests/test_generic_finding_detail_parity.py
        Inside the module-scoped `factory` fixture only: rebind it from a plain
        `sessionmaker(bind=migrated_engine)` to a Connection-owned, savepoint-joined sessionmaker per §6
        above — obtain one Connection from `migrated_engine`, begin one outer transaction on it, yield
        `sessionmaker(bind=<that Connection>, join_transaction_mode="create_savepoint")`, roll the outer
        transaction back and close the Connection at fixture teardown. No other fixture, helper function,
        parametrization, or assertion in this file may change. No test may be added, removed, reordered, or
        renamed.
```

**Against `CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture-Artifact-Authorization.md` (effective on
the still-open candidate; carried forward into whatever branch composes the corrected final candidate, §14):**

```
MODIFY  backend/app/tests/test_noetva_demo_readiness_golden_story.py
        (a) Inside the module-scoped `factory` fixture only: the identical rebinding described above.
        (b) Inside `test_d1_golden_supplier_deterministic_and_idempotent` only: change the one existing
        `sessionmaker(bind=session.get_bind())` call to additionally pass
        `join_transaction_mode="create_savepoint"`, preserving its existing cross-Session semantics under
        the new outer-transaction model (§8 above). No other line in this test's body — its assertions,
        its expected values, its narrative — may change. No other fixture, test, parametrization, or
        assertion in this file may change. No test may be added, removed, reordered, or renamed.
```

No third implementation path is authorized. Exact syntax must satisfy `ruff check`/`ruff format` (§10); the
semantic mechanism (§6) is what is frozen, not literal source text.

## 12. Fix-scope negative proof (binding)

This amendment authorizes zero change to: `DemoOqiSeeder` or any other production seeder/repository/service
code; any migration; `.github/workflows/ci.yml` (including, explicitly, the `CTEC_DATABASE_URL ==
CTEC_TEST_DATABASE_URL` aliasing, which remains load-bearing and untouched); `backend/app/tests/conftest.py`
or the `migrated_engine` fixture it defines; `test_oqi_h4_integrity_crown.py` or any migration round-trip
test; test collection/ordering configuration (`pytest.ini`/`pyproject.toml` `[tool.pytest.ini_options]`); any
allowlist file; `docs/demo/NOETVA-GOLDEN-DEMO-RUNBOOK.md` (its stale Integrity-404 warning remains explicitly
out of scope, §35 of the governing prompt); any assertion, expected value, or narrative text in either
corrected test file. Migration count: zero, before and after. Total non-test production paths touched: zero.

## 13. Updated exact Artifact Authorization accounting

```
CDD-086 AA (main, effective now):
  Original authorized paths:                         (unchanged by this amendment's own text — CDD-086 AA
                                                        is not re-tabulated here; it remains independently
                                                        readable at its own frozen hash, §F of the report)
  This amendment's addition:                          MODIFY = 1  (test_generic_finding_detail_parity.py)

CDD-085 AA (candidate, effective once composed, §14):
  Original authorized paths (CDD-085 AA §1):          CREATE = 2, MODIFY = 5, DELETE = 0, TOTAL = 7
  G-R1 amendment's addition:                          MODIFY = 1, TOTAL = 1  (entity_resolution_store.py)
  This amendment's addition:                          MODIFY = 1, TOTAL = 1  (test_noetva_demo_readiness_
                                                        golden_story.py — already CDD-085 AA §2 row 1's own
                                                        CREATE path; this amendment narrows what MODIFY is
                                                        permitted against an already-authorized path, not a
                                                        new path)
  Updated CDD-085 effective total:                    CREATE = 2, MODIFY = 6, DELETE = 0, TOTAL = 8
                                                        (unchanged from G-R1's own total, §18 of that
                                                        amendment — this amendment adds a permitted-
                                                        modification note against an already-CREATE-
                                                        authorized path, not a new MODIFY row)

This amendment's own publication:                     CREATE = 1 (this document) — self-authorizing, not
                                                        counted against either implementation ceiling above,
                                                        per identical convention to every prior phase.

Total implementation paths this amendment governs:    2  (§18 of the governing prompt: "TOTAL IMPLEMENTATION
                                                        PATHS: 2. No third implementation path.")
```

## 14. Composition and branch strategy (§14/§41/§42 of the governing prompt)

- `product/noetva-demo-readiness-r1` @ `e9a04bba...` and PR #248 remain **exactly as they are** — historical
  evidence, preserved, never amended/rebased/force-pushed/merged. This amendment does not touch them.
- This amendment is published on a **new branch cut from authoritative `origin/main`**,
  `product/noetva-demo-readiness-g-r3` (the prior `product/noetva-demo-readiness-g-r2`, confirmed still at
  zero commits ahead of `origin/main` and never pushed, is left untouched and is not reused).
- Future implementation (`NOETVA-CI-BACKEND-ISOLATION-I-R1`) must compose the corrected final candidate as:
  `origin/main` (carrying `CDD-086` and its own already-merged `test_generic_finding_detail_parity.py`) as
  the base, with the blocked candidate's own commits (which introduce `CDD-085`, its G-R1 amendment, and
  `test_noetva_demo_readiness_golden_story.py`) reconciled on top — exactly the same reconciliation shape
  `NOETVA-DEMO-READINESS-R1` already performed once (`git rebase --onto`, `git patch-id --stable` semantic-
  equivalence proof) — followed by applying this amendment's two named corrections as new, additional
  commits. Implementation must **not** branch fresh from `main` alone and re-author
  `test_noetva_demo_readiness_golden_story.py` from scratch — that file's full D1-D25 content already exists,
  frozen, on the blocked candidate, and must be inherited, not reinvented.
- **PR #248 disposition:** preserve it, unmodified, as historical/closed-eventually evidence. Create a
  **new** final PR from the new, corrected, reconciled candidate branch once implementation and its own VM
  phase complete. Do not push additional commits onto PR #248's existing head.

## 15. STOP conditions — binding, exhaustive, restated for the record; none triggered this phase

```
 1. correction found to require a production seeder change.                    NOT TRIGGERED (§5, §12)
 2. correction found to require a third implementation path.                   NOT TRIGGERED (§11, §13)
 3. correction found to require a migration.                                   NOT TRIGGERED (§12)
 4. correction found to require a CI-workflow change.                          NOT TRIGGERED (§12)
 5. correction found to require an H4/migration-test change.                   NOT TRIGGERED (§12)
 6. correction found to require an assertion change.                           NOT TRIGGERED (§8, §11)
 7. correction found to require test-order manipulation.                       NOT TRIGGERED (§7 — both
                                                                                 orders pass)
 8. correction found to require commit suppression / monkeypatched commit.     NOT TRIGGERED (§6, §9 of the
                                                                                 governing prompt — real
                                                                                 commit semantics preserved)
 9. correction found to require a Golden product semantic change.              NOT TRIGGERED (§12)
10. any DR-R1 decisive fact found false.                                       NOT TRIGGERED (§3)
11. authoritative main or blocked candidate found to have moved.               NOT TRIGGERED (§2)
```

## 16. P0/P1/P2/P3

```
Before this amendment: P0 = 1 (PR #248 blocked on deterministic, unexplained-at-the-time red CI; correctly
                        never merged, per this program's "never waive red CI" discipline)
After this amendment:   P0 = 0, P1 = 0, P2 = 0, P3 = 0 (pending NOETVA-CI-BACKEND-ISOLATION-I-R1's own full,
                         independent implementation and re-verification of the two named corrections, real
                         GitHub Actions CI green on both backend and frontend/containers jobs, and a final
                         VM-phase exact-head merge)
```

## 17. Authorization

This amendment is approved and published as a standalone governance artifact, following this program's
established convention (`CDD-050-Artifact-Authorization-H4-R1`, `CDD-084-Artifact-Authorization-H6-G-R1`,
`CDD-085-Artifact-Authorization-G-R1`) of never silently rewriting an already-approved Artifact Authorization
in place. `CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md`, its original companion Artifact
Authorization, its own G-R1 amendment, `CDD-086-Generic-Finding-Detail-Parity.md`, and its own companion
Artifact Authorization all remain FROZEN, unmodified, and fully authoritative. This amendment's §11
authorizes exactly two MODIFY corrections — one against each of the two named, already-existing test files —
confined to the exact fixture-transaction mechanism in §6, and nothing else. No implementation write against
any path has occurred as part of this amendment; it is a governance-artifact-only correction. Implementation
readiness is reauthorized to resume, under the identifier NOETVA-CI-BACKEND-ISOLATION-I-R1, only after that
phase's own complete, independent re-verification of every crown in §7 against the real, committed correction
and against real GitHub Actions CI.
