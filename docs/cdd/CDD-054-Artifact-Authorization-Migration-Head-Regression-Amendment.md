# CDD-054 — Artifact Authorization Migration-Head Regression Amendment (OQI6-R3-GA)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-053-Artifact-Authorization-Migration-Head-Regression-Amendment.md` (OQI6-R2-GA — the direct,
identical-shape precedent: a new migration invalidates a pre-existing hardcoded "current head" assertion
outside the new capability's own Artifact Authorization); `CDD-047-Artifact-Authorization-Mechanical-
Migration-Head-Regression-Amendment.md` and `CDD-041-Artifact-Authorization-Mechanical-Migration-Head-
Regression-Amendment.md` (the original precedents establishing that this correction is a companion
amendment reusing the parent phase's own CDD number); the already-established, already-proven repository-
native idiom `ScriptDirectory.from_config(config).get_current_head()`, already in production use at three
locations in `test_oqi_business_impact.py` itself (line 1304, R1's own GA1-corrected test; lines 2057/2118,
R3's own newly-authored fail-closed migration tests)
Classification: MIGRATION-REGRESSION AUTHORIZATION GAP (mechanical correction only; no architectural,
semantic, or scope change of any kind; does not reopen `CDD-054-OQI6-R3-Current-Pointer-Tenant-Isolation-
Correction.md`, which remains FROZEN, byte-identical, unmodified)
Governs: `oqi6-r3/current-pointer-tenant-isolation` branch, structural implementation candidate
`2af8d3e37e1055bb8c743d0517940175fa1ed0fc`

## 1. Purpose

Authorizes the exact, narrow, single-line correction of a pre-existing hardcoded migration-head assertion
in `backend/app/tests/test_oqi_business_impact.py`, discovered by OQI6-R3-I's own fail-closed full-
regression run to be invalidated by the correct, expected introduction of migration `0043` on top of `0042`.
**CDD-054 (the R3 correction architecture and Artifact Authorization) is not modified, not reopened, and
remains FROZEN exactly as originally published** — this document is a new, standalone, additive companion
amendment, reusing CDD-054's own number per this repository's own established precedent (mirroring
`CDD-053`, `CDD-051`, `CDD-047`, and `CDD-040`, each of which published narrow companion amendments under
their own number rather than consuming a new one).

## 2. Independent re-verification — authoritative baseline

Before drafting this amendment, this phase independently re-verified: `origin/main` and GitHub `main` both
equal `43f3f729165147069992aca3f86f01abc9cb2cb8`, unchanged since OQI6-R3-I's own stop; the R3 governance
commit `98c7507e48328c1731a3e87e16e8014164c38357` and its artifact hash
`dbaf17e2ec9840351713ae999672dc8bced496b9eb9ee8445f6ac523a09e3b24` are unchanged; the R3 structural
implementation candidate `2af8d3e37e1055bb8c743d0517940175fa1ed0fc` is a clean, linear descendant of the
governance commit, containing exactly the frozen three-path diff (`0043_oqi6_r3_current_tenancy.py` CREATE;
`oqi_business_impact.py` and `test_oqi_business_impact.py` MODIFY) and nothing else.

## 3. Independent reproduction of the blocking failure

Reproduced fresh, from a clean worktree at `2af8d3e`, against a freshly-migrated database:
```
app/tests/test_oqi_business_impact.py::test_r2ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_evaluation FAILED

app/tests/test_oqi_business_impact.py:1606: in test_r2ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_evaluation
    assert version == "0042_oqi6_r2_evaluation_tenancy"
AssertionError: assert '0043_oqi6_r3_current_tenancy' == '0042_oqi6_r2_evaluation_tenancy'
```
Exactly one assertion, at line 1606, in exactly one pre-existing test (itself already once amended by R2's
own GA1, for a materially identical reason), fails. No other test in the full backend suite is affected.

## 4. R2 structural-behavior preservation (distinguishing defect classes)

Independently re-read `test_r2ti10_...`'s complete body (lines 1540-1606). Because pytest reports failure at
the exact line of the first failing assertion, and the reported failure is at line 1606 (the final line) and
nowhere earlier, every prior assertion in the test is independently confirmed to have passed:
```
downgrade to 0041_oqi6_r1_dependency_tenancy (the pre-R2 schema)         -> historical setup, unaffected by R3
seed cross-tenant BusinessImpactEvaluation row (accepted pre-R2)         -> PASSES (implicit, no earlier failure)
pytest.raises(IntegrityError): alembic upgrade to "head"                 -> PASSES (R2's own tenant FK correctly
                                                                              rejects the row on the way to 0042,
                                                                              regardless of what lies beyond it)
version == "0041_oqi6_r1_dependency_tenancy" (migration did not
    partially apply)                                                     -> PASSES
_row() == invalid_row (byte-unchanged)                                   -> PASSES
cleanup + retry: alembic upgrade to "head"                                -> PASSES (reaches 0043 successfully)
version == "0042_oqi6_r2_evaluation_tenancy"  <- LINE 1606                -> FAILS (stale literal)
```
This conclusively confirms:
```
NOT: an R3 implementation defect (the R3 correction itself is independently proven correct in every
     dimension by OQI6-R3-I's own evidence, unaffected by this failure)
NOT: an R2 structural regression (every R2-specific assertion in this exact test still passes)
IS:  a pre-existing test assumption ("head" == a specific historical literal) invalidated by the normal,
     expected, correctly-authorized advancement of the migration chain from 0042 to 0043 -- the identical
     class of regression R2's own GA1 amendment already corrected once, at 0041, for R1's own analogous test
```

## 5. Final-assertion semantic intent

The test's own docstring and structure make its intent unambiguous: after the deliberately-seeded invalid
row is cleaned up, the retried upgrade must succeed and the database must reach **the repository's current
migration head** — proving the fail-closed migration genuinely "un-blocks" once the offending data is gone,
not that it stops at any particular numbered revision. `"0042_oqi6_r2_evaluation_tenancy"` was correct only
because it happened to be the repository's head at the moment R2 authored this test — it was never itself
part of the tenant-isolation invariant being proven (unlike the `"0041_oqi6_r1_dependency_tenancy"`
occurrences, which are semantically load-bearing: they identify the specific pre-R2 schema state required to
reproduce the historical vulnerability, and must remain pinned literals regardless of how many later
migrations exist).

## 6. Complete `0042` literal inventory (exhaustive)

Independently re-confirmed via `grep` across the full test file — exactly six occurrences of
`"0041_oqi6_r1_dependency_tenancy"`/`"0042_oqi6_r2_evaluation_tenancy"`-shaped literals relevant to this
boundary; isolating specifically the `0042` string:

| Line | Context | Classification |
|---|---|---|
| 1606 | `test_r2ti10_...`'s final assertion, "we reached head" | **CURRENT HEAD ASSUMPTION — CORRECT** (this amendment) |
| (all `0041` occurrences in this same test and elsewhere) | downgrade targets / "migration did not partially apply" checks | HISTORICAL TARGET — KEEP LITERAL (unaffected, not `0042`, not in scope) |

No occurrence of the literal `"0042_oqi6_r2_evaluation_tenancy"` exists anywhere else in the file as a
"current head" assumption — independently confirmed via exhaustive `grep`. Exactly one occurrence is in
scope.

## 7. Repository `ScriptDirectory` precedent

Independently confirmed: `from alembic.script import ScriptDirectory` is already imported in
`test_oqi_business_impact.py` (line 19, added by R2's own GA1 amendment) and already used at three
locations: line 1304 (R1's own GA1-corrected `test_ti10_...`), and lines 2057 and 2118 (R3's own newly-
authored `test_r3tim04_to_m06_...`/`test_r3tim07_to_m09_...` fail-closed migration tests, authored under
CDD-054's own original authorization). No new import is required for this amendment.

## 8. Option A — hardcode `0043` (rejected)

Textually smallest, but merely defers the identical interruption to the next migration (a future `0044`).
Rejected — repeats the exact class of governance interruption this amendment exists to close, for the
second time in this exact repository's OQI6 lineage.

## 9. Option B — dynamic Alembic-head resolution (selected)

```python
current_head = ScriptDirectory.from_config(config).get_current_head()
assert version == current_head
```
Resolves the actual repository-current head from Alembic's own metadata at test-run time — correct at
`0043` today and correct at any future `0044`, `0045`, ... without further amendment. Not new infrastructure:
the exact idiom already in independent, established use at three locations in this same file (§7).

## 10. Selected correction

**Option B**, using the identical inline idiom already established in this exact file, requiring zero new
import.

## 11. Frozen future-proof invariant (restated, binding)

```
A migration test that semantically asserts successful recovery to the repository's current Alembic head
must resolve that head from Alembic metadata rather than pinning a migration identifier that becomes stale
when a legitimate later migration is added. Historical migration-scenario targets remain explicit literals.
```
```
CURRENT REPOSITORY HEAD -> dynamic
HISTORICAL TEST TARGET  -> pinned literal
```

## 12. Exact authority boundary (binding — scope statement)

This amendment authorizes correction of exactly one pre-existing assertion, inside exactly one pre-existing
test function, in exactly one file:
```
backend/app/tests/test_oqi_business_impact.py
  test_r2ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_evaluation
    line 1606 only
```
No other line in this test, no other test in this file (including all of R1's, R2's, and R3's own TI
matrices), and no file outside this one path is authorized to change.

## 13. Exact new-path authorization (binding)

```
CREATE = 0
MODIFY = 1
DELETE = 0
TOTAL  = 1
```
```
MODIFY  backend/app/tests/test_oqi_business_impact.py

        Exactly one change, confined to this one file:
        Replace ONLY line 1606's `assert version == "0042_oqi6_r2_evaluation_tenancy"` with:
            current_head = ScriptDirectory.from_config(config).get_current_head()
            assert version == current_head
        No import addition is required (ScriptDirectory is already imported at line 19). No other line
        in this test function changes. No other test function in this file changes.
```

## 14. Structural candidate byte-preservation baseline (binding)

Recorded immediately before this amendment's publication, to be independently re-verified as unchanged by
OQI6-R3-I-R1:
```
b9105ca6d35307b4fe24d9b71e855c2f65a2a028b29add923ae4b492dc037606
  backend/app/infrastructure/persistence/migrations/versions/0043_oqi6_r3_current_tenancy.py
a7a867dcba66aab5d8b9e9f8096e282d5396df81cd2008108a01837b1b0a9de8
  backend/app/infrastructure/persistence/models/oqi_business_impact.py
```
Neither file is modified by this amendment, and neither may be modified by the resumed implementation.

## 15. Existing Black-hunk classification

Independently reconfirmed: `black --check app` is **fully clean** on candidate `2af8d3e` — the one
formatter hunk OQI6-R3-I disclosed (a line-wrap of the newly authored `_seed_business_impact_evaluation_
direct` function signature) was already applied and committed as part of that candidate itself, entirely
within R3's own newly-authorized test content, touching zero pre-existing code. No outstanding formatter-
authorization question remains; no further governance action is required for this item.

## 16. Dirty-tree firewall classification

Independently reconfirmed: on a genuinely clean worktree checked out at the committed candidate `2af8d3e`
(`git status --short` empty), `test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists` **passes**.
This conclusively confirms the failure OQI6-R3-I observed was a transient, self-resolving dirty-working-tree
effect (the test compares `git diff --name-only HEAD` plus untracked files against an allowlist; it was
never evaluating committed repository state) — not an implementation defect, and not requiring any
governance amendment.

## 17. R3-I-R1 resumed-implementation verification contract (binding)

OQI6-R3-I-R1 must, at minimum: verify authoritative main, CDD-054 hash, this amendment's hash, and exact
ancestry; verify both structural files remain byte-identical to the §14 baseline; apply exactly the §13
one-line correction; re-run the corrected `test_r2ti10_...` and confirm it passes; re-run the complete
R1/R2/R3 tenant-isolation matrix; re-run both R3 fail-closed migration proofs; re-run the migration round
trip; re-prove both R3 boundaries and R1/R2 preservation against real PostgreSQL; re-introspect all R1/R2/R3
constraints; prove head `0043`/table count `123`; run the full backend suite to green; run `black`/`isort`/
`ruff`/whole-package `mypy`; run complete frontend tests/lint/typecheck/build; perform a **fresh**
`docker compose build --no-cache` (mandatory — OQI6-R3-I never reached Docker verification) and, inside it,
re-prove migration head/table count/both R3 boundaries/R1/R2 preservation/H5/OQI6 regression/backend and
frontend health; produce explicit host-Docker equivalence; re-confirm both CDD-054 documents (the original
correction and this amendment) remain byte-identical; derive the exact final diff and inspect every hunk;
push, open/update the PR, verify the exact PR file set, wait for CI on the exact candidate head, and STOP
for OQI6-R3-VM. Do not merge in I-R1.

## 18. Expected final PR shape

If the amendment is implemented as expected, the final PR should contain exactly 5 unique paths:
```
CDD-054 (original correction)
CDD-054 migration-head regression amendment (this document)
0043 migration
oqi_business_impact.py
test_oqi_business_impact.py
```
No sixth unexplained path — the amended test file is already one of the original three implementation
paths, not a new one.

## 19. OQI4 deferral (restated, unchanged)

```
OQI4 CURRENTONTOLOGYIMPACT POINTER TENANT-ISOLATION CORRECTION
DEFERRED — FUTURE SEPARATELY GOVERNED PHASE
```

## 20. Production-orchestration deferral (restated, unchanged)

```
OQI4/OQI6/OQI5 Production Orchestration
DEFERRED — SEPARATE FUTURE GOVERNED INITIATIVE
```

## 21. Governance byte-integrity

Independently re-hashed immediately before this document's own publication and confirmed byte-identical to
its prior published value:
```
dbaf17e2ec9840351713ae999672dc8bced496b9eb9ee8445f6ac523a09e3b24
  CDD-054-OQI6-R3-Current-Pointer-Tenant-Isolation-Correction.md
```
Neither that file nor any other prior CDD is modified by this amendment. This document and its own content
are the sole new governance artifact this phase publishes.

## 22. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 0 (the R3 structural correction itself is sound and independently
                        proven), P2 = 2 (the OQI4 CurrentOntologyImpact deferral, unchanged; this
                        mechanical migration-head regression, blocking full verification but not
                        indicating any structural defect)
After this amendment:   P0 = 0, P1 = 0, P2 = 1 (OQI4 analog remains deferred; the mechanical regression
                        remains UNIMPLEMENTED as of this document -- this amendment freezes the
                        correction, it does not apply it), P3 = 0
```
The mechanical issue is not resolved by this document alone; OQI6-R3-I-R1 must still apply and verify it.

## 23. Allowed claim

```
The R3 structural candidate remains preserved, and governance now explicitly authorizes the narrow
future-proof correction of the stale R2 current-head test assertion required by legitimate migration-head
advancement to 0043.
```

## 24. Forbidden claims

```
"R3 implementation is complete."
"R3 is verified."
"R3 is closed."
```

## 25. Authorization

This document is approved and published as a standalone governance artifact, following the established
precedent of `CDD-053-Artifact-Authorization-Migration-Head-Regression-Amendment.md`,
`CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md`, and
`CDD-041-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md`. Implementation against
§13's exact one-path authorization may proceed under `OQI6-R3-I-R1`.
