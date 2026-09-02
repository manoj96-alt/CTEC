# CDD-047 — Artifact Authorization CI Migration-Head Closure Amendment (OQI-H1-CI)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md` (OQI-H1-I-R1
— the direct precedent for this exact class of gap: a new migration invalidates a fixed set of
pre-existing hardcoded migration-head/table-count assertions scattered outside the new capability's own
Artifact Authorization); `CDD-041-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md`
(OQI3-GA — the original precedent for this defect class)
Classification: MIGRATION-REGRESSION AUTHORIZATION GAP (mechanical correction only; no architectural,
semantic, migration, or application-behavior change of any kind)

## 1. Purpose

Authorizes the exact, narrow correction of two stale migration-head/table-count assumptions discovered
in `.github/workflows/ci.yml`'s `containers` job after PR #182's CI ran against the real, merged H1
candidate. This is the same defect class OQI-H1-I-R1 already resolved across the Python test suite —
but CI workflow configuration was explicitly excluded from CDD-047's original Artifact Authorization
(`docs/cdd/CDD-047-OQI-H1-Governed-Quality-Coverage-and-Reliance-Generalization-Artifact-Authorization.md`
§4: "any Docker/Compose/CI configuration file... no configuration file changes are authorized") and was
therefore never in scope for R1's own sweep, which was limited to `backend/app/tests/`. This amendment
closes that gap under its own explicit, narrow authorization rather than silently treating CI as already
covered.

## 2. Context

PR #182 (`oqi-h1/governed-quality-coverage` → `main`) carries the fully VM2-verified H1 implementation,
R1's mechanical migration-head correction, and R2's typing correction. Its `containers` CI check failed
on first run: `.github/workflows/ci.yml`'s "Verify the fresh database reached the authoritative migration
head" step hardcodes `[ "$head" = "0026_oqi6_reliance" ]`, which is stale now that H1's own migration
(`0027_h1_coverage_policy`) is the repository's authoritative head. The very next step, "Verify the fresh
schema has exactly the expected table count", hardcodes `[ "$count" -eq 100 ]`, which is stale for the
identical reason — H1 adds exactly two tables (CDD-047 §9, Artifact Authorization §5).

## 3. Exhaustive fresh discovery

`grep -n` across every `.github/workflows/*.yml`/`*.yaml` file (there is exactly one workflow file,
`.github/workflows/ci.yml`) for `0026_oqi6_reliance`, `0027_h1_coverage_policy`, `alembic_version`,
`migration head`, `table count`, `expected table`, `information_schema`, `COUNT(*)`, `upgrade head`,
`alembic upgrade`, `alembic downgrade`, and `alembic heads` produces exactly two occurrences, both in the
`containers` job, both already disclosed above:

```
Classification A — CURRENT-HEAD ASSUMPTION:
    .github/workflows/ci.yml:144   [ "$head" = "0026_oqi6_reliance" ]

Classification C — CURRENT-SCHEMA TABLE-COUNT ASSUMPTION:
    .github/workflows/ci.yml:151   [ "$count" -eq 100 ]
```

No other CI migration/schema assumption exists anywhere in the workflow file. No historical-revision
assertion (Classification B) exists in CI at all — unlike the Python suite, CI only ever asserts the
*current* state of a freshly-migrated stack, never a specific historical boundary. Nothing ambiguous
(Classification E) was found.

## 4. Root-cause classification

```
H1 architectural defect:         NO
Coverage-policy semantic defect: NO
Migration defect:                NO
Application-behavior defect:     NO
Docker/Compose behavior defect:  NO
Authorization defect:            YES -- CDD-047's original Artifact Authorization correctly excluded CI
                                  configuration from H1's own implementation surface, but neither it nor
                                  the R1 amendment anticipated that this exclusion would leave a
                                  CI-resident current-head assertion uncorrected when H1's migration
                                  became the new authoritative head.
```

## 5. Correction design

**Migration head (line 144):** resolved dynamically rather than re-pinned to a literal. The `containers`
job's `backend` service is already running and healthy by this point in the job (the preceding "Wait for
Postgres, Keycloak, and backend to report healthy" step gates on it), and the backend image already has
Alembic installed with `alembic.ini` at its working directory — proven directly, `docker compose exec
backend alembic -c alembic.ini heads` resolves the repository-authoritative head with no additional
job-level dependency (no new `setup-python` step, no new install). This makes the invariant genuinely
`database alembic_version == repository authoritative Alembic head`, not a manually maintained literal,
and is therefore immune to the identical defect class recurring at a future `0028`.

**Table count (line 151):** pinned to the freshly-verified correct value, **102** (100 + H1's exactly two
new tables), not derived dynamically. Identical reasoning to OQI-H1-I-R1 §15: Alembic exposes its current
head programmatically with zero drift risk, but there is no equivalent zero-drift API for "total table
count" — that number is corrected mechanically, exactly as every predecessor amendment in this repository
(OQI1→OQI2, OQI6→H1, and now H1→CI) has handled it. It will itself become stale the next time a migration
is added, at which point this identical, disclosed correction class applies again.

## 6. Semantic-strength requirement — confirmed preserved

Neither corrected step is weakened. Both remain hard failures (`exit 1`) on any mismatch. No assertion is
removed, no `|| true`/`continue-on-error` is introduced, no step is skipped, and the `containers` job
remains a required check. The corrected head check now fails if the database revision differs from the
repository's own authoritative head for *any* reason (including a future migration this amendment did not
anticipate); the corrected table-count check still fails if any unexpected table is missing, extra, or
never created.

## 7. Exact new path authorization

```
MODIFY  .github/workflows/ci.yml
```

Exactly one path. No other file is authorized by this amendment.

## 8. Exact allowed change (binding, minimum only)

```
.github/workflows/ci.yml:142-144
    head=$(docker compose exec -T -e PGPASSWORD=ctec postgres psql -U ctec -d ctec -tAc
        "SELECT version_num FROM alembic_version")
    echo "migration head: $head"
    [ "$head" = "0026_oqi6_reliance" ] || { echo "unexpected migration head: $head"; exit 1; }
        -> add one line resolving the repository-authoritative head via
           `docker compose exec -T backend alembic -c alembic.ini heads`, then compare $head against
           that resolved value instead of the literal "0026_oqi6_reliance". No other line in this step
           changes.

.github/workflows/ci.yml:149-151
    count=$(docker compose exec -T -e PGPASSWORD=ctec postgres psql -U ctec -d ctec -tAc
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND
        table_type='BASE TABLE' AND table_name != 'alembic_version'")
    echo "table count: $count"
    [ "$count" -eq 100 ] || { echo "unexpected table count: $count (expected 100)"; exit 1; }
        -> the literal 100 becomes 102; the error message's parenthetical becomes "(expected 102)". No
           other line in this step changes.
```

No other line in `.github/workflows/ci.yml` may change under this authorization. No step is added,
removed, reordered, renamed, marked `continue-on-error`, or made non-blocking. No other job
(`backend`, `frontend`) is touched. No `docker-compose.yml`, `Dockerfile`, application source, migration
file, backend test, frontend file, or seeder is touched — all remain explicitly out of this amendment's
narrow scope, identical in spirit to the original CDD-047 AA §4 exclusions this amendment is itself
scoped inside of.

## 9. Architecture / product-scope / implementation-artifact impact

```
Product capability scope:    UNCHANGED
H1 architecture:             UNCHANGED
Schema:                      UNCHANGED
Migration:                   UNCHANGED
Coverage/Reliance semantics: UNCHANGED
Application behavior:        UNCHANGED
Docker/Compose behavior:     UNCHANGED
CI closure-gate strength:    UNCHANGED IN SUBSTANCE (identical invariant, now expressed correctly and
                              future-safe against the current-head literal specifically; the table-count
                              literal is mechanically corrected, same class as its Python-side
                              predecessors)
```

Named implementation path set: unaffected. This amendment authorizes a CI-only correction outside the
25-path H1 implementation lineage entirely; it does not renumber or extend that accounting.

## 10. Governance precedent followed

Exactly the same standalone-companion-document pattern as OQI-H1-I-R1, OQI3-GA (CDD-041), and OQI1-GM
(CDD-039): a new, separate governance file; CDD-046, its erratum, CDD-047, CDD-047's original Artifact
Authorization, and the R1 amendment all remain byte-identical (§12 below).

## 11. Governance byte-integrity

`CDD-046-OQI-Hardening-Nine-Dimension-Architecture.md`
(`81af53b0edb8e2b0f12f8b3e784df2aecd5ff2dea3b494435624b00903db30aa`),
`CDD-046-QualityRule-Ownership-Erratum.md`
(`4ea188869f1603af44e58902380e5ab761b32d550570acb594a553d41a5a52cd`),
`CDD-047-OQI-H1-Governed-Quality-Coverage-and-Reliance-Generalization.md`
(`044bbd7551162bdb7efed4375869c06cc12bfd7ce4db0f186bb61b1d07e94b3d`),
`CDD-047-OQI-H1-Governed-Quality-Coverage-and-Reliance-Generalization-Artifact-Authorization.md`
(`aa813fee2b57a3973f7439ac9066aaa6dde8f1c498e5a91dffefe1144af081b5`), and
`CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md`
(`386d1e178278ba234057b6af20a6ac9e12991ec9c152f64a622eb1002f0b7fcc`) were independently re-hashed
immediately before this document was written and confirmed byte-identical to their prior publication
values. This document is the sole new artifact.

## 12. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 0, P2 = 1 (CI closure-gate incompleteness -- a required check fails
                        on the exact VM2-verified candidate for a reason entirely outside every prior
                        phase's authorized scope), P3 = 0
After this amendment:   P0 = 0, P1 = 0, P2 = 0, P3 = 0
```

## 13. Implementation readiness / closure

```
OQI-H1 CI closure authorization is now complete: YES

AUTHORIZED MODIFY = 1 (.github/workflows/ci.yml, exactly the two lines named in §8)
```

No H1 domain, coverage, Reliance, migration, or Docker/Compose semantic is created or modified by this
governance-only amendment.

## 14. Authorization

This amendment is approved and published as a standalone governance artifact, following the established
repository precedent of never silently rewriting an already-approved Artifact Authorization in place, and
never folding an out-of-scope correction into an already-verified implementation commit. OQI-H1 closure is
formally reauthorized to resume against this corrected CI-workflow surface, under the identifier
OQI-H1-CI.
