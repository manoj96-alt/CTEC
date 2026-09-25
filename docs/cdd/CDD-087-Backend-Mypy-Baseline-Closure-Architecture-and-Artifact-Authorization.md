# CDD-087 — Backend Mypy Baseline Closure Architecture and Artifact Authorization (NOETVA-CI-MYPY-BASELINE-CLOSURE-DRG)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Classification: DISCOVERY + ARCHITECTURE + ARTIFACT AUTHORIZATION ONLY. No implementation write occurred as part of
this document. It freezes independently-proven evidence, a root-cause taxonomy, a runtime-semantic assessment, and
an exact 19-path remediation Artifact Authorization for a future, separate implementation phase
(`NOETVA-CI-MYPY-BASELINE-CLOSURE-I`).
Governs: this amendment only. It does not modify, reopen, or reauthorize any path in CDD-085 (Golden Signature UX,
all revisions G-R1 through G-R5) or CDD-086 (Generic Finding Detail Parity). Signature UX PR #251 is explicitly out
of scope for implementation here.

## 1. Purpose

Golden Signature UX PR #251 (`product/noetva-demo-readiness-signature-ux-i-r1`, head `31c06a6f`) is blocked on
backend CI's `mypy app` step: 61 errors across 19 files. The implementation phase that discovered this
(`NOETVA-GOLDEN-SIGNATURE-UX-I-R1`) reported these as pre-existing baseline debt unrelated to its own 33-path
change, based on one quick reproduction against the frozen historical candidate `b254372`. This amendment
independently re-verifies that claim to full rigor — three-way reproduction, byte-exact diagnostic comparison,
root-cause taxonomy, runtime-semantic assessment, consumer search, and a frozen, narrow, non-implemented
remediation Artifact Authorization — before anyone is asked to trust it enough to act on it.

## 2. Authoritative state, independently re-verified this phase

```
origin/main                    91e90b5812a123d08d58e78347f7283d285921f6
product/noetva-demo-readiness-final (PR #250)   b254372b9632c0bd16174678e2ba7f2afd95688c  OPEN, unmerged, unmoved
PR #251 head                   31c06a6fa6625f444af6541e57a72d6bea40adcc  OPEN, unmerged, MERGEABLE
```

## 3. CI invocation, confirmed by direct inspection of `.github/workflows/ci.yml`

```
working-directory: backend
pip install -e '.[dev]'
black --check .
isort --check-only .
ruff check .
mypy app          <-- fails
pytest            <-- never reached
```

`backend/pyproject.toml` declares `sqlalchemy>=2.0,<3` and `mypy>=1.15,<2` — open ranges, not exact pins, and there
is no lockfile covering the `[dev]` extra (`backend/requirements.txt` exists but does not mention mypy or
sqlalchemy). Every `pip install -e '.[dev]'` — including every CI run — freely re-resolves within those ranges.

## 4. Three-way reproduction (Task 1)

`mypy app` run from a clean, isolated `git worktree add --detach <ref>` copy with a fresh venv, for three refs:

```
origin/main (91e90b58)     Found 61 errors in 19 files (checked 657 source files)   mypy 1.20.2, sqlalchemy 2.1.0
b254372                    Found 61 errors in 19 files (checked 658 source files)   mypy 1.20.2, sqlalchemy 2.1.0
PR #251 head (31c06a6f)    Found 61 errors in 19 files (checked 659 source files)   mypy 1.20.2, sqlalchemy 2.1.0
```

(Source-file counts differ only because each ref has a different number of files in the repository; the touched
Signature UX files are additive to PR #251's tree and contribute zero new diagnostics — see §6.)

## 5. Mechanical diagnostic comparison (Task 2)

Full `(file, line, code, message)` tuples extracted from all three raw outputs and diffed programmatically.

```
b254372 vs main:    byte-for-byte identical diagnostic set. Zero difference.
b254372 vs PR #251: byte-for-byte identical diagnostic set. Zero difference — not even a line-number shift.
```

Classification against the five categories:

```
A. identical baseline diagnostic:            61 / 61
B. baseline diagnostic shifted by line only:   0
C. Signature-UX-introduced diagnostic:         0
D. disappeared baseline diagnostic:            0
E. genuinely new diagnostic:                   0
```

**Zero Signature-UX regression.** None of the 19 debt files intersect the 33-path Signature UX Artifact
Authorization (CDD-085 G-R5 §8) — confirmed by direct set comparison, zero overlap.

## 6. Main-branch comparison (Task 4) — the debt is not candidate-lineage-specific

`main` at `91e90b58` reproduces the identical 61/19 result today. Cross-checking GitHub's own recorded CI history
for that exact commit:

```
backend CI on 91e90b58: conclusion "success", completed 2026-09-22T01:41:31Z
```

That successful run's own install log resolved `sqlalchemy-2.0.54` (mypy already at `1.20.2`, unchanged). Today's
(2026-09-25) fresh installs on all three refs resolve `sqlalchemy-2.1.0`. **This is the root cause in full**: the
open range `sqlalchemy>=2.0,<3` allowed a `2.0.54 -> 2.1.0` minor-version upgrade to land silently between one CI
run and the next, with no commit to any of the 19 affected files, no commit to `main`, and no relation whatsoever
to Golden Signature UX. `main`'s own backend CI would fail identically if re-run today — this is a live,
repository-wide condition, not something specific to the historical Golden candidate lineage or to PR #251.

## 7. Root-cause taxonomy (Task 3) — exactly two families, both traced to the same dependency drift

**Family 1 — stale `Select[tuple[X]]` return annotations on private ordered-statement helpers (3 files, 9
diagnostics: 6 `arg-type` + 3 `return-value`).**

```
backend/app/infrastructure/persistence/decision_repository.py        (3: lines 136, 150, 220)
backend/app/infrastructure/persistence/governance_repository.py      (3: lines 106, 131, 146)
backend/app/infrastructure/persistence/knowledge_evaluation_store.py (3: lines 47, 59, 66)
```

Each file has a private static helper (`_ordered_statement`) explicitly annotated `-> Select[tuple[X]]`. Under
SQLAlchemy 2.0.54, `select(SingleORMEntity)`'s own inferred generic matched that wrapped-tuple convention closely
enough that no conflict surfaced. Under 2.1.0, SQLAlchemy corrected `select(SingleORMEntity)`'s own type-stub
inference to `Select[X]` (no tuple wrapper) for a single-entity select — exposing the three files' own
already-stale explicit annotations as now conflicting with the (now correctly) inferred body type. Every caller of
these helpers already consumes them via `Session.scalars(...)`, which at runtime always yields the entity directly,
never a row-tuple — confirmed by reading every call site (`decision_repository.py:135-137`,
`governance_repository.py`, `knowledge_evaluation_store.py`, and three test call sites in
`test_decision_engine.py`, `test_governance_engine.py`, `test_knowledge_engine.py`, all of which only call
`.compile()` on the returned `Select`, a method indifferent to the generic parameter). **The correct annotation was
always `Select[X]`; the explicit `tuple[X]` wrapper was already wrong, just previously unexposed.**

**Family 2 — unannotated locals/unpacked tuples from raw `text()` SQL execution (16 files, 52 diagnostics: 50
`var-annotated` + 2 `arg-type`).**

```
test_oqi_business_rule_postgres.py (16)   test_oqi_ontology_impact_postgres.py (5)
test_oqi_business_impact.py (4)           test_institutional_relationship_tenant_migration_postgres.py (4)
test_oqi_provenance.py (3)                test_decision_engine.py (3)
test_persistence_integration.py (2)       test_oqi_h4_integrity_crown.py (2)
test_oqi_business_rule_provenance.py (2)  test_knowledge_engine.py (2)
test_governance_engine.py (2)             test_oqi_quality_postgres.py (1)
test_oqi_cross_source_postgres.py (1)     test_gate_v_agent_postgres.py (1)
test_field_value_evidence_persistence_postgres.py (1)
test_atomic_admission_postgres_concurrency.py (1 var-annotated + 2 arg-type = 3)
```

Every instance is a raw `connection.execute(text("..."))` (or `.execute(text(...), params)`) followed by
`.scalar()`/`.scalar_one()` assigned to a bare local (`revision = ...`, `table_count = ...`, `current_schema =
...`), or a `.one()` result unpacked into a bare tuple of locals (`schema_name, constraint_name = row` in
`test_atomic_admission_postgres_concurrency.py:110`, feeding a `ConstraintInfo(schema_name=..., constraint_name=...)`
constructor that requires `str`). SQLAlchemy 2.1's typing for `text()`-based execution results changed in a way
that requires these locals to be explicitly annotated (or cast) where 2.0.54 allowed mypy to leave them unannotated
without complaint. All 16 files are test files performing direct schema/row introspection against Postgres for
assertion purposes — the SQL, and the runtime values it produces, are unaffected; only their static Python-side
type visibility changed.

Both families trace to the single, exact, verified root cause in §6. There is no third cluster, no unrelated
category, and no diagnostic that groups only superficially by mypy error code without sharing this cause.

## 8. Runtime-semantic assessment (Task 4 answers)

For every diagnostic in both families: runtime behavior is already correct; the typing is stale or newly
under-specified, not wrong-and-silently-tolerated. Correcting either family's annotations changes zero runtime
behavior — Family 1's fix corrects a type witness to match code that already runs correctly via `.scalars()`;
Family 2's fix adds annotations/casts to values already correctly produced by the SQL and already correctly used by
the assertions that consume them. No cluster crosses an architecture or domain boundary. No cluster requires a
schema or public API change. This closes cleanly as **type-correctness hardening**, not product redesign, per §8 of
the governing prompt.

## 9. Complete consumer search (Task 5)

Family 1's only public-surface change is the private helper's own return-type annotation (not a public
function/protocol signature) — `_ordered_statement` is name-mangled-private-by-convention and used only within its
own file plus three test files already inside the 19-path debt set (they only call `.compile()`, indifferent to the
generic parameter). No consumer outside these already-enumerated 19 files exists. Family 2's fixes are local
variable annotations with no downstream consumers by construction (a local variable is never itself a public
interface). **Complete transitive scope is exactly the 19 files already listed — no 20th path.**

## 10. Test-owner map (Task 6)

Every affected file in Family 1 is itself a repository implementation with its own existing test suite
(`test_decision_engine.py`, `test_governance_engine.py`, `test_knowledge_engine.py` — already in the debt set,
already exercising these repositories' runtime behavior end-to-end against real Postgres). Every affected file in
Family 2 IS the test file whose existing assertions already prove the runtime value is correct (that is precisely
what each test was written to check) — the annotation fix only makes the already-correct, already-tested value
visible to mypy. **No new test coverage is required for either family**; existing coverage already proves runtime
equivalence before and after a purely-annotation-level fix.

## 11. Frozen remediation design — NOT implemented in this document

**Family 1 (3 files)**: change each `_ordered_statement`'s explicit return annotation from `Select[tuple[X]]` to
`Select[X]`, matching SQLAlchemy 2.1's own corrected inference and the runtime behavior already relied upon. No
call site requires any change (their consumption pattern is already correct).

**Family 2 (16 files)**: add an explicit local type annotation (or a narrow `assert isinstance(...)`/cast
appropriate to the specific value, e.g. `revision: str = ...`, `table_count: int = ...`) at each of the 52
diagnostic sites, matching the actual SQL column type already known from each query's own `SELECT` clause. No
runtime logic changes.

**No suppression of any kind** (`# type: ignore`, `cast(Any, ...)`, `--ignore-missing-imports`, CI weakening, file
exclusion) is proposed or authorized. This is 100% forbidden by §7 of the governing prompt and unnecessary here —
every diagnostic has a precise, local, typed, zero-risk correction available.

**Complementary CI-hygiene recommendation (not part of this Artifact Authorization, a separate future decision)**:
`backend/pyproject.toml`'s open ranges (`sqlalchemy>=2.0,<3`, `mypy>=1.15,<2`) allowed this exact class of
silent, time-based CI breakage and will do so again for any future minor release in either range. Introducing an
exact pin or a resolved lockfile for the `[dev]` extra is worth a dedicated, separate governance decision — it is
explicitly NOT authorized or implemented here, since it is a CI/dependency-policy decision distinct from the
type-correctness repair itself (per §13 of the governing prompt: CI configuration changes require their own
governance step).

## 12. Exact Artifact Authorization — literal, for a future implementation phase only

### 12.1 CREATE (0)
None.

### 12.2 MODIFY (19)

```
1.  backend/app/infrastructure/persistence/decision_repository.py
2.  backend/app/infrastructure/persistence/governance_repository.py
3.  backend/app/infrastructure/persistence/knowledge_evaluation_store.py
4.  backend/app/tests/test_oqi_business_rule_postgres.py
5.  backend/app/tests/test_oqi_ontology_impact_postgres.py
6.  backend/app/tests/test_oqi_business_impact.py
7.  backend/app/tests/test_institutional_relationship_tenant_migration_postgres.py
8.  backend/app/tests/test_oqi_provenance.py
9.  backend/app/tests/test_decision_engine.py
10. backend/app/tests/test_persistence_integration.py
11. backend/app/tests/test_oqi_h4_integrity_crown.py
12. backend/app/tests/test_oqi_business_rule_provenance.py
13. backend/app/tests/test_knowledge_engine.py
14. backend/app/tests/test_governance_engine.py
15. backend/app/tests/test_oqi_quality_postgres.py
16. backend/app/tests/test_oqi_cross_source_postgres.py
17. backend/app/tests/test_gate_v_agent_postgres.py
18. backend/app/tests/test_field_value_evidence_persistence_postgres.py
19. backend/app/tests/test_atomic_admission_postgres_concurrency.py
```

### 12.3 VERIFY ONLY (0)
### 12.4 DELETE (0)

### 12.5 Mechanical reconciliation

```
CREATE (0) + MODIFY (19) + VERIFY ONLY (0) + DELETE (0) = 19 = UNIQUE PATH COUNT
```

Independently recounted by listing: 19 numbered entries in §12.2, no duplicates, no path shared with CDD-085 G-R5's
33-path table (checked by direct set comparison, §5).

### 12.6 Explicitly PROHIBITED for the future implementation phase

```
Any Signature UX path (the 33-path CDD-085 G-R5 table) — do not touch merely because it coexists on PR #251.
.github/workflows/ci.yml — no CI weakening, no step removal, no continue-on-error.
backend/pyproject.toml's sqlalchemy/mypy version ranges — a separate, not-yet-authorized governance decision (§11).
Any # type: ignore, cast(Any, ...), or blanket suppression anywhere.
```

## 13. Runtime/CI non-weakening proof obligation for the future implementation phase

The future phase must prove, not assume: `black`, `isort`, `ruff check .` remain clean; `mypy app` reaches **zero**
errors (not a reduced count); the full backend pytest suite passes with the exact same pass count already
established for `main`/PR #251 today (no test behavior change); and CI's exact existing `mypy app` invocation
passes unmodified — no `--exclude`, no per-file override, no config relaxation.

## 14. Composition strategy with PR #251 (Task 15 design only — not executed here)

Preferred sequence, based on actual Git ancestry already verified in this document:

```
A. Implement this §12 remediation on its own branch from origin/main (91e90b58), independent of PR #251 entirely.
B. Verify independently (§13), open its own PR, merge to main.
C. Rebase PR #251 (product/noetva-demo-readiness-signature-ux-i-r1) onto the new main, preserving the CDD-085
   G-R3/G-R4/G-R5 governance-commit provenance and the exact 33-path Signature UX delta unchanged.
D. Re-run PR #251 CI. No new Signature UX path should be needed — the baseline repair and Signature UX are
   orthogonal by construction (§5, §9).
```

This sequencing is preferred over fixing the baseline directly inside the Signature UX branch because it keeps the
two concerns — pre-existing repository-wide type debt vs. a specific product feature — independently reviewable,
independently revertible, and correctly attributed in history. It is not executed in this document.

## 15. PR #251's 47-file whole-diff vs. the 33-path Signature UX delta — recorded for future VM

GitHub reports PR #251 as touching more than 33 files because its base-to-head diff includes everything `b254372`
already carried relative to `main` (inherited Golden-candidate implementation, CDD-085 original/G-R1/G-R2
governance and code) plus the G-R3/G-R4/G-R5 governance-commit provenance plus the 33-path Signature UX
implementation delta itself. **CDD-085 G-R5's 33-path Artifact Authorization applies to the Signature UX
implementation delta on top of its governed base (`b254372` + G-R3/G-R4/G-R5), not to the raw `main..PR#251`
diff.** A future verification phase must independently confirm both figures and must not misclassify the larger
whole-PR file count as an Artifact Authorization violation.

## 16. Browser-crown residual — unchanged, independent blocker

The 22-step authenticated Keycloak Authorization Code + PKCE browser crown (CDD-085 G-R5 §37/§44) remains
unperformed and mandatory before Signature UX merge, for the same reason already disclosed on PR #251: no
browser-automation tool is available in this environment. This document does not address or waive it. The
containers job's own authenticated OQI request check is a valuable but non-equivalent substitute — it is not the
interactive governed browser journey.

## 17. Process-authority audit

All investigation in this phase (three-way clean-worktree reproduction, diagnostic comparison, taxonomy, consumer
search) was performed read-only — zero files written or modified in any inspected ref, all disposable worktrees
removed after use, confirmed clean before teardown. This governance document itself, its filing, its commit, and
its push are all performed exclusively by the primary session. No delegated process performed any write in this
phase.

## 18. Authorization

This amendment is approved and published as a standalone governance artifact. It authorizes a future, separate
implementation phase (`NOETVA-CI-MYPY-BASELINE-CLOSURE-I`) to the exact 19-path table in §12 and no others, subject
to the non-weakening proof obligations in §13 and the composition strategy in §14. It does not modify, weaken, or
reopen any CDD-085 or CDD-086 decision, and it does not authorize any Signature UX path change. No implementation
write has occurred as part of this document.
