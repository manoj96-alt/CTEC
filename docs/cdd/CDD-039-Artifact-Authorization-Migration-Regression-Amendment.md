# CDD-039 — Artifact Authorization Migration Regression Amendment (OQI1-GM)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-039-Artifact-Authorization-Concurrency-Hardening-Amendment.md`,
`CDD-039-Artifact-Authorization-Count-Correction.md` (separate-companion-document correction
pattern; an already-approved Artifact Authorization is never silently rewritten in place),
`CDD-036-Migration-Head-Regression-Assertion-Defect-Authorization.md` (the original precedent for
authorizing exactly a mechanical migration-head literal correction as its own governance artifact)
Classification: MIGRATION-REGRESSION AUTHORIZATION GAP (mechanical correction only; no
architectural, semantic, or scope change of any kind)

## 1. Purpose

Authorizes exactly one additional mechanical correction discovered only at OQI1 implementation
time: `backend/app/tests/test_gate_v_agent_postgres.py` contains a hardcoded assertion of the
*overall repository migration head* against `"0019_gate_v_agent_resolution"` — a fifth instance of
the same fragility class the "canonical four" files (`test_decision_engine.py`,
`test_governance_engine.py`, `test_knowledge_engine.py`, `test_persistence_integration.py`) were
already tracked and corrected for by the original OQI1 Artifact Authorization, but this fifth
occurrence — inside Gate V's own postgres test suite — was never added to that tracked list when
Gate V (CDD-037) was implemented. This document authorizes the identical class of correction for
that one additional path. It changes no architecture, no OQI semantic, no migration design, no
concurrency mechanism, and no Gate V behavior.

## 2. Context

OQI1-I implementation completed all 21 originally-authorized paths, passed every OQI1-scoped test,
and then ran the full backend regression suite as its own required diligence step (per its own
Section 44/59's "run all established repository test/CI suites" and "do not touch unauthorized
files to make CI green" instructions). That full run surfaced exactly one failure outside the
21-path surface: `test_gate_v_agent_postgres.py::test_migration_head_and_down_revision`. OQI1-I
correctly stopped rather than editing an unauthorized file, exactly as its own stop conditions
require. This is the disciplined outcome that phase was designed to produce.

## 3. Independent re-verification (performed in a clean worktree from authoritative main, not the
dirty implementation branch)

```
backend/app/tests/test_gate_v_agent_postgres.py:94-95
    revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "0019_gate_v_agent_resolution"
```

This queries `alembic_version` directly — the single-row table holding the *entire repository's*
current migration head, identical in shape and semantics to the assertions already present (and
already corrected by OQI1) in the four canonical files. It is not a Gate-V-specific schema check
(that is a separate, earlier assertion in the same test, `test_migration_creates_expected_schema`,
unaffected and not touched here) — it is a global migration-head assertion, and migration `0020`
legitimately invalidates it. The required correction is exactly one literal.

## 4. Exhaustive fresh repository search

Every literal occurrence of `0019_gate_v_agent_resolution` repository-wide was re-enumerated and
classified:

```
backend/app/tests/test_runtime_architecture.py:622
    -> AUTHORIZED_CHANGED_PATHS entry (a path string, not a migration-head assertion) — no
       correction needed; the path `.../0019_gate_v_agent_resolution.py` itself never changes.

backend/app/tests/test_gate_v_agent_postgres.py:3   -> docstring prose describing what Gate V's
    OWN migration proves ("migration `0019_gate_v_agent_resolution` produces exactly the expected
    schema") — remains true regardless of later migrations; not a global-head claim; no correction
    needed.
backend/app/tests/test_gate_v_agent_postgres.py:95  -> NEWLY-DISCOVERED IMPACT (Section 3).

backend/app/infrastructure/persistence/migrations/versions/0019_gate_v_agent_resolution.py:16
    -> migration definition (`revision = "0019_gate_v_agent_resolution"`) — immutable historical
       fact about that migration's own identity; never changes.
backend/app/infrastructure/persistence/migrations/versions/0020_oqi1_quality_foundation.py:15
    -> `down_revision = "0019_gate_v_agent_resolution"` — the correct, frozen chain link (Section 5).

docs/cdd/CDD-037-Governed-Agent-Resolution.md (5 occurrences)
docs/cdd/CDD-037-Governed-Agent-Resolution-Artifact-Authorization.md (5 occurrences)
    -> historical, frozen governance documentation of Gate V's own already-closed migration-impact
       remediation (0018 -> 0019) — correctly describes what was true at Gate V's own
       implementation time; never rewritten (matches this entire lineage's own discipline of never
       editing historical frozen governance).

docs/cdd/CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation-Artifact-Authorization.md
docs/cdd/CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation.md
    -> already-authorized OQI1 update descriptions (0019 -> 0020) — already correctly govern the
       four canonical files; unaffected by this amendment.
```

A parallel, independent search for every file actually querying the live `alembic_version` table
(`grep -rl "FROM alembic_version"`) found exactly seven:

```
test_decision_engine.py                              -> asserts "0020_oqi1_quality_foundation" (already corrected by OQI1)
test_gate_v_agent_postgres.py                          -> asserts "0019_gate_v_agent_resolution" (THE GAP)
test_governance_engine.py                               -> asserts "0020_oqi1_quality_foundation" (already corrected by OQI1)
test_institutional_relationship_tenant_migration_postgres.py
    -> asserts `current == PRE_MIGRATION_REVISION`, a symbolic constant scoped to an isolated,
       pinned historical fixture (`pre_0012_engine`) testing a specific historical migration
       transition in complete isolation from the live repository head -- confirmed NOT a global-head
       assertion, NOT impacted by migration 0020, requires no correction.
test_knowledge_engine.py                                -> asserts "0020_oqi1_quality_foundation" (already corrected by OQI1)
test_oqi_quality_postgres.py                             -> OQI1's own new test, already asserts "0020_oqi1_quality_foundation"
test_persistence_integration.py                           -> asserts "0020_oqi1_quality_foundation" (already corrected by OQI1)
```

## 5. Migration topology proof

```
backend/app/infrastructure/persistence/migrations/versions/0020_oqi1_quality_foundation.py:
    revision      = "0020_oqi1_quality_foundation"
    down_revision = "0019_gate_v_agent_resolution"
```

Confirmed: exactly one migration file declares `down_revision = "0019_gate_v_agent_resolution"`
(no competing branch); no migration file declares `down_revision = "0020_oqi1_quality_foundation"`
(0020 is genuinely the linear tip). The migration chain `0019 -> 0020` is the sole, uncontested
topology.

## 6. Answer required by this phase

> Is `test_gate_v_agent_postgres.py` the only remaining executable test/code location outside the
> existing authorization that incorrectly assumes `0019` remains the repository migration head
> after `0020`?

**YES.**

## 7. Comparison to the four already-authorized regression paths

All four (`test_decision_engine.py`, `test_governance_engine.py`, `test_knowledge_engine.py`,
`test_persistence_integration.py`) were independently re-inspected in this same worktree (Section
4's search output above) and confirmed to already carry the exact same semantic-class correction
(`"0019_gate_v_agent_resolution"` -> `"0020_oqi1_quality_foundation"` on their own
`SELECT version_num FROM alembic_version` assertion). They are evidence only; none is modified by
this amendment.

## 8. Root-cause classification

```
Architectural defect:           NO
OQI semantic defect:            NO
Implementation logic defect:    NO
Authorization defect:           YES -- Gate V's own migration-impact cataloging (CDD-037 §17)
                                 never registered its own test's identical global-head assertion
                                 alongside the four canonical files it did register.
```

## 9. Architecture / product-scope / implementation-artifact impact

```
Product capability scope:  UNCHANGED
Architecture:               UNCHANGED
Schema:                       UNCHANGED
Migration:                     UNCHANGED (0020's own definition is untouched)
OQI semantics:                   UNCHANGED
Concurrency mechanism:             UNCHANGED
Gate V behavior:                     UNCHANGED
Test obligation:                       UNCHANGED IN SUBSTANCE (same assertion, corrected literal)
Regression coverage:                     CORRECTED

Named implementation path set: EXPANDS BY ONE PATH (21 -> 22) -- an honest, precise statement, not
"unchanged": one additional file is now part of the authorized implementation surface.
```

## 10. Exact new path authorization

```
MODIFY  backend/app/tests/test_gate_v_agent_postgres.py
```

## 11. Exact allowed change (binding, minimum only)

```
Line 95:  assert revision == "0019_gate_v_agent_resolution"
      ->  assert revision == "0020_oqi1_quality_foundation"
```

No other line in this file may change. No Gate V agent behavior, no Gate V domain semantics, no
other assertion, and no docstring prose (Section 4's line-3 classification: unaffected, no
correction authorized or required) may be touched.

## 12. New 22-file accounting (binding, supersedes OQI1-GC's 21-file accounting)

```
CREATE = 16   (unchanged -- identical to the OQI1-GC-corrected count)
MODIFY = 6    (was 5; +1 for backend/app/tests/test_gate_v_agent_postgres.py)
DELETE = 0
TOTAL  = 22
```

The first 21 named paths (CDD-039's own Artifact Authorization §4, as corrected by OQI1-GC) remain
completely unchanged, in the same order, with the same purposes. Path 22 is exactly the one named
in Section 10 above. No wildcard, no implied file, no 23rd path.

## 13. Governance precedent followed

Exactly the same standalone-companion-document pattern as OQI1-GR (Concurrency Hardening
Amendment) and OQI1-GC (Count Correction): a new, separate governance file; the original Artifact
Authorization, CDD-039, and every prior amendment remain byte-identical; direct commit to `main`
from a clean state (here, an isolated `git worktree` rather than the dirty implementation branch,
since one already existed with uncommitted authorized work — a stronger, more careful application
of the same "never contaminate frozen governance with in-progress implementation" discipline).

## 14. Governance byte-integrity

`CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation.md`,
`CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation-Artifact-Authorization.md`,
`CDD-039-Artifact-Authorization-Concurrency-Hardening-Amendment.md`, and
`CDD-039-Artifact-Authorization-Count-Correction.md` all remain byte-identical to their prior
publication state, independently re-verified by SHA-256 from this clean worktree before this
document was written. This document is the sole new artifact.

## 15. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 1 (authorization gap blocking a clean commit), P2 = 0, P3 = 1
After this amendment:  P0 = 0, P1 = 0, P2 = 0, P3 = 1 (unchanged -- the already-accepted 64-bit
                        advisory-lock collision characteristic)
```

## 16. Implementation readiness

```
OQI1 implementation authorization is now internally consistent and complete: YES

AUTHORIZED CREATE = 16
AUTHORIZED MODIFY = 6
AUTHORIZED DELETE = 0
AUTHORIZED TOTAL  = 22
```

No OQI implementation file, migration, test, frontend, or API file is created or modified by this
governance-only amendment. The dirty `oqi1/deterministic-quality-foundation` branch, holding the
already-completed 21-path implementation, is untouched by this publication and remains to be
brought onto the new authoritative main and have path 22 applied in a subsequent, separately
authorized OQI1-I resume step.

## 17. Authorization

This amendment is approved and published as a standalone governance artifact, following the
established repository precedent of never silently rewriting an already-approved Artifact
Authorization in place. OQI1 implementation may resume against the corrected 22-path, 16-CREATE/
6-MODIFY/0-DELETE authorization once the Product Owner separately re-authorizes resumption of
OQI1-I.
