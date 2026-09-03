# CDD-053 — Artifact Authorization Migration-Head Regression Amendment (OQI6-R2-GA)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md` (OQI-H1-I-R1
— the direct precedent for this exact class of gap: a new migration invalidates a pre-existing hardcoded
"current head" assertion outside the new capability's own Artifact Authorization); `CDD-041-Artifact-
Authorization-Mechanical-Migration-Head-Regression-Amendment.md` (OQI3-GA — the original precedent
establishing that this correction is a companion amendment reusing the parent phase's own CDD number,
never an in-place rewrite of an already-approved Artifact Authorization); the already-established, already-
proven repository-native idiom `ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()`,
already in production use in `test_decision_engine.py`, `test_governance_engine.py`, `test_gate_v_agent_
postgres.py`, `test_knowledge_engine.py`, `test_oqi_business_rule_postgres.py`, `test_oqi_cross_source_
postgres.py`, `test_oqi_quality_postgres.py`, and `test_persistence_integration.py`
Classification: MIGRATION-REGRESSION AUTHORIZATION GAP (mechanical correction only; no architectural,
semantic, or scope change of any kind; does not reopen `CDD-053-Artifact-Authorization-OQI6-R2-Business-
Impact-Evaluation-Dependency-Tenant-Isolation-Correction.md`, which remains FROZEN, byte-identical,
unmodified)
Governs: `oqi6-r2/business-impact-evaluation-tenant-isolation` branch, structural implementation candidate
`be3def414ce9f7c29cd3137cc4dff5cd0b7ae9d3`

## 1. Purpose

Authorizes the exact, narrow, single-line correction of a pre-existing hardcoded migration-head assertion
in `backend/app/tests/test_oqi_business_impact.py`, discovered by OQI6-R2-I's own fail-closed full-
regression run to be invalidated by the correct, expected introduction of migration `0042` on top of `0041`.
**CDD-053 (the R2 correction architecture and Artifact Authorization) is not modified, not reopened, and
remains FROZEN exactly as originally published** — this document is a new, standalone, additive companion
amendment, reusing CDD-053's own number per this repository's own established precedent (mirroring how
`CDD-051`, `CDD-047`, and `CDD-040` each published narrow companion amendments under their own number
rather than consuming a new one).

## 2. Independent re-verification — authoritative baseline

Before drafting this amendment, this phase independently re-verified: `origin/main` and GitHub `main` both
equal `0212eac0579c1abc0a801e3ebf45c56421313461`, unchanged since OQI6-R2-I's own stop; the R2 governance
commit `4646ada349ea464e8fff6c363a5dcca8ff3cb533` and its artifact hash
`abfa9f643ece58240b422c356c2a0b124aa6339ec705f45cbad1ab79fdb9186e` are unchanged; the R2 structural
implementation candidate `be3def414ce9f7c29cd3137cc4dff5cd0b7ae9d3` is a clean, linear descendant of the
governance commit, containing exactly the frozen three-path diff (`0042_oqi6_r2_evaluation_tenancy.py`
CREATE; `oqi_business_impact.py` and `test_oqi_business_impact.py` MODIFY) and nothing else.

## 3. Independent reproduction of the blocking failure

Reproduced fresh, from a clean worktree at `be3def4`, against a freshly-migrated database:
```
app/tests/test_oqi_business_impact.py::test_ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_data FAILED

app/tests/test_oqi_business_impact.py:1302: in test_ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_data
    assert version == "0041_oqi6_r1_dependency_tenancy"
AssertionError: assert '0042_oqi6_r2_evaluation_tenancy' == '0041_oqi6_r1_dependency_tenancy'
```
Exactly one assertion, at line 1302, in exactly one pre-existing test, fails. No other test in the full
backend suite is affected (independently re-confirmed: full-suite run shows `1 failed` and this is the sole
failure).

## 4. R1 and R2 structural-behavior verification (distinguishing defect classes)

Independently re-read `test_ti10_...`'s complete body (lines 1235-1302) and confirmed every assertion prior
to the final one passes and correctly proves R1's own fail-closed invariant is fully intact:
```
downgrade to 0040 (the pre-R1 schema)                          -> historical setup, unaffected by R2
seed cross-tenant BusinessDependency row (accepted pre-R1)      -> PASSES
pytest.raises(IntegrityError): alembic upgrade to "head"        -> PASSES (R1's own tenant FK correctly
                                                                    rejects the row on the way to 0041,
                                                                    regardless of what lies beyond it)
version == "0040_oqi_h5_timeliness_eval" (migration did not
    partially apply)                                            -> PASSES
_row() == invalid_row (byte-unchanged)                          -> PASSES
cleanup + retry: alembic upgrade to "head"                       -> PASSES (reaches 0042 successfully)
version == "0041_oqi6_r1_dependency_tenancy"  <- LINE 1302       -> FAILS (stale literal)
```
This conclusively distinguishes:
```
NOT: an R2 implementation defect (the R2 correction itself is independently proven correct in every
     dimension — see CDD-053's own §Q-§X evidence, reconfirmed unaffected by this failure)
NOT: an R1 structural regression (every R1-specific assertion in this exact test still passes)
IS:  a pre-existing test assumption ("head" == a specific historical literal) invalidated by the normal,
     expected, correctly-authorized advancement of the migration chain from 0041 to 0042
```

## 5. Assertion semantic-intent analysis

The test's own docstring and structure make its intent unambiguous: after the deliberately-seeded invalid
row is cleaned up, the retried upgrade must succeed and the database must reach **the repository's current
migration head** — proving the fail-closed migration genuinely "un-blocks" once the offending data is gone,
not that it stops at any particular numbered revision. `"0041_oqi6_r1_dependency_tenancy"` was correct only
because it happened to be the repository's head at the moment R1 authored this test — it was never itself
part of the tenant-isolation invariant being proven (unlike the `"0040_oqi_h5_timeliness_eval"` occurrences,
which are semantically load-bearing: they identify the specific pre-R1 schema state required to reproduce
the historical vulnerability, and must remain pinned literals regardless of how many later migrations
exist).

## 6. Inventory of all `"0041_oqi6_r1_dependency_tenancy"` literal occurrences (exhaustive)

Independently re-confirmed via `grep` across the full test suite — exactly four occurrences, all in
`test_oqi_business_impact.py`, all in R2's own newly-added tests except the one under amendment:

| Line | Context | Classification |
|---|---|---|
| 1302 | `test_ti10_...`'s final assertion, "we reached head" | **CURRENT HEAD ASSUMPTION — CORRECT** (this amendment) |
| 1528 | R2-TI-09's `alembic.command.downgrade(config, "0041_oqi6_r1_dependency_tenancy")` | HISTORICAL TARGET — KEEP LITERAL (deliberately downgrades one step behind 0042 to test the R2 round trip specifically) |
| 1547 | R2-TI-10's `alembic.command.downgrade(config, "0041_oqi6_r1_dependency_tenancy")` | HISTORICAL TARGET — KEEP LITERAL (deliberately reproduces the pre-R2 schema to seed the R2 invalid-legacy-data scenario) |
| 1589 | R2-TI-10's own "migration did not partially apply" check, `version == "0041_oqi6_r1_dependency_tenancy"` | HISTORICAL TARGET — KEEP LITERAL (identical semantic role to line 1290's `0040` check — the pre-R2-upgrade-attempt point, not "current head") |

No global search-and-replace is authorized. Exactly one occurrence (line 1302) is in scope.

## 7. Option A — hardcode `0042` (rejected)

Textually smallest, but merely defers the identical interruption to `0043` (R3's own future migration) and
embeds R2's specific migration topology into a test whose invariant predates and is independent of R2's
existence. Rejected — repeats the exact class of governance interruption this amendment exists to close
permanently.

## 8. Option B — dynamic Alembic-head resolution (selected)

```python
current_head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
assert version == current_head
```
Resolves the actual repository-current head from Alembic's own metadata at test-run time — correct at
`0042` today and correct at any future `0043`, `0044`, ... without further amendment. This is not new
infrastructure: it is the exact idiom already in independent production use in eight other test files in
this repository (§ header, Precedent).

## 9. Option C — existing helper reuse (this is Option B)

No project-local wrapper helper (e.g. `get_current_migration_head()`) exists anywhere in the repository —
every one of the eight precedent files calls `ScriptDirectory.from_config(Config(...)).get_current_head()`
directly, inline, at the point of use. Option B **is** the existing repository convention; no new shared
helper/file is created or would be idiomatic here.

## 10. Selected correction

**Option B**, using the identical inline idiom already established at `test_decision_engine.py:307` and its
seven siblings. `test_oqi_business_impact.py` already imports `Config` from `alembic.config` (line 18); the
only new import required is `from alembic.script import ScriptDirectory`.

## 11. Exact authority boundary (binding — scope statement)

This amendment authorizes correction of exactly one pre-existing assertion, inside exactly one pre-existing
test function, in exactly one file:
```
backend/app/tests/test_oqi_business_impact.py
  test_ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_data
    line 1302 only
```
No other line in this test, no other test in this file (including all of R1's and R2's own TI matrices),
and no file outside this one path is authorized to change.

## 12. Exact new-path authorization (binding)

```
CREATE = 0
MODIFY = 1
DELETE = 0
TOTAL  = 1
```
```
MODIFY  backend/app/tests/test_oqi_business_impact.py

        Exactly two changes, both confined to this one file:
        1. Add ONE import: `from alembic.script import ScriptDirectory` (alongside the existing
           `from alembic.config import Config` on line 18, following this repository's own established
           import-grouping convention for this exact idiom, as seen in every precedent file).
        2. In test_ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_data, replace ONLY line
           1302's `assert version == "0041_oqi6_r1_dependency_tenancy"` with:
               current_head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
               assert version == current_head
           No other line in this test function changes. No other test function in this file changes.
```

## 13. Forbidden implementation paths (binding, exhaustive)

`0042_oqi6_r2_evaluation_tenancy.py` (unchanged, byte-for-byte); `oqi_business_impact.py` (unchanged,
byte-for-byte); every other line of `test_oqi_business_impact.py` (including lines 1528, 1547, and 1589
per §6); any domain/service/API/frontend file; any R1 or R2 structural constraint; any R3 (`current_
business_impacts`/`current_reliance`) file; any production-orchestration file; `CDD-044`, `CDD-050`,
`CDD-051`, `CDD-052`, `CDD-053` (the original R2 correction document), or any of their own frozen Artifact
Authorizations.

## 14. Structural candidate preservation

`be3def414ce9f7c29cd3137cc4dff5cd0b7ae9d3` is not amended, rebased, or squashed by this document. History
remains: R1 main (`0212eac`) → R2 governance (`4646ada`) → R2 structural implementation candidate
(`be3def4`) → this governance amendment (additive on top of `be3def4`) → the resumed implementation's own
mechanical test-correction commit (`OQI6-R2-I-R1`).

## 15. R1 preservation

No change to any R1 assertion's *meaning*. Lines 1245/1290 (the `0040` historical-schema-state literals)
are explicitly confirmed out of scope and unmodified — they remain pinned exactly because the vulnerability
they reproduce is defined relative to the pre-R1 schema state, not to "current head."

## 16. R2 preservation

No change to any of R2's own eleven new tests (`test_r2ti01`-`test_r2ti11`) or their own three legitimate
`0041`-literal historical-target usages (§6, lines 1528/1547/1589) — all three remain correctly pinned as
the pre-R2 schema state R2's own fail-closed proof is defined against.

## 17. R3 deferral (restated, unchanged)

```
OQI6-R3 — Current* Pointer Tenant-Isolation Correction
DEFERRED — FUTURE SEPARATELY GOVERNED PHASE
```

## 18. Production-orchestration deferral (restated, unchanged)

```
OQI4/OQI6/OQI5 production-orchestration trigger:
SEPARATE FUTURE GOVERNED INITIATIVE
```

## 19. Resumed-implementation verification contract (binding on OQI6-R2-I-R1)

OQI6-R2-I-R1 must, at minimum: apply exactly the §12 one-line-plus-one-import correction; re-run
`test_ti10_...` and confirm it passes with the dynamically-resolved head; re-run the complete R2-TI-01
through R2-TI-11 matrix; re-run the full backend suite (`pytest app/tests`) and confirm zero failures;
re-run whole-package `mypy`, `black --check`, `isort --check-only`, `ruff check`; re-run frontend
`npm test`/`npm run lint`/`npx tsc --noEmit`/`npm run build`; perform a **fresh** `docker compose build
--no-cache` (mandatory — OQI6-R2-I never reached Docker verification, and a host-only proof is
insufficient per every prior phase's own established standard) and, inside it, re-prove migration head
`0042`/table count `123`/both tenant-qualified FKs/both tenant-qualified candidate keys/cross-tenant
rejection/same-tenant acceptance/R1 preservation/H5 preservation/OQI6 regression/backend and frontend
health; verify host-Docker structural equivalence explicitly (not merely "both passed"); re-confirm both
CDD-053 documents (the original correction and this amendment) remain byte-identical; verify the exact
combined diff; push, open/update the PR, wait for CI on the exact candidate head, and STOP for OQI6-R2-VM.
Do not merge in I-R1.

## 20. Governance byte-integrity

Independently re-hashed immediately before this document's own publication and confirmed byte-identical to
its prior published value:
```
abfa9f643ece58240b422c356c2a0b124aa6339ec705f45cbad1ab79fdb9186e
  CDD-053-Artifact-Authorization-OQI6-R2-Business-Impact-Evaluation-Dependency-Tenant-Isolation-Correction.md
```
Neither that file nor any other prior CDD is modified by this amendment. This document and its own content
are the sole new governance artifact this phase publishes.

## 21. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 0 (the R2 structural correction itself is sound and independently
                        proven), P2 = 2 (the R3 deferral, unchanged; this mechanical migration-head
                        regression, blocking full verification but not indicating any structural defect)
After this amendment:   P0 = 0, P1 = 0, P2 = 1 (R3 remains deferred; the mechanical regression remains
                        UNIMPLEMENTED as of this document — this amendment freezes the correction, it does
                        not apply it), P3 = 0
```
The mechanical issue is not resolved by this document alone; OQI6-R2-I-R1 must still apply and verify it.

## 22. Authorization

This document is approved and published as a standalone governance artifact, following the established
precedent of `CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md` and
`CDD-041-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md`. Implementation against
§12's exact one-path authorization may proceed under `OQI6-R2-I-R1`.
