# CDD-053 — Artifact Authorization OQI6-R2 Business Impact Evaluation → Business Dependency Tenant-Isolation Correction (OQI6-R2)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-052-Artifact-Authorization-OQI6-R1-Business-Dependency-Tenant-Isolation-Correction.md` (the direct
precedent for this exact defect class, exact governance shape, and exact corrected additive-vs-replacement
reasoning); `CDD-050-Artifact-Authorization-H4-R1-Reference-Tenant-Isolation-Correction-Amendment.md` (the
original proven technical pattern both R1 and R2 reuse: add a tenant-qualified composite candidate key to
the parent table, then replace the child's plain FK with a tenant-qualified composite FK); migration
`0041_oqi6_r1_business_dependency_tenancy.py` (R1's own already-shipped implementation of the identical
pattern one table pair earlier in the same chain)
Governs: base architecture `CDD-044-Ontology-Quality-Intelligence-Criticality-Business-Impact-Explainable-
Reliance.md` (frozen, NOT reopened, NOT modified by this document); `main` authoritative state
`0212eac0579c1abc0a801e3ebf45c56421313461` (OQI6-R1-VM's independently verified merge commit, independently
re-confirmed unchanged as of this document's own publication)
Classification: DATABASE-LEVEL STRUCTURAL TENANT-ISOLATION GAP (constraint-only correction; no schema
topology change, no table addition, no column addition, no domain/service/API/frontend semantic change)

## 1. Purpose

Authorizes the exact, narrow, additive-then-replacing correction of a genuine database-level tenant-
isolation defect in `oqi_business_impact_evaluations`' foreign key to `oqi_business_dependencies`,
independently discovered and reproduced by OQI6-R2-DR, independently re-reproduced by this governance
phase, and explicitly anticipated (and deferred) by CDD-052 §8 at the time R1 closed the sibling
Dependency→Process boundary. **CDD-044, CDD-050, CDD-051, and CDD-052 are not modified, not reopened, and
remain FROZEN exactly as originally published** — this document is a new, standalone, additive governance
artifact.

## 2. Authoritative baseline — independently re-derived by this phase

Before drafting this freeze, this phase independently re-verified: `origin/main` and GitHub `main` both
equal `0212eac0579c1abc0a801e3ebf45c56421313461`, unchanged since OQI6-R2-DR's own verification; the
migration head is still `0041_oqi6_r1_dependency_tenancy` (41 files, single head); `oqi_business_dependencies`
still carries `PRIMARY KEY(dependency_id, version)` with no tenant-qualified candidate key; `oqi_business_
impact_evaluations` still carries exactly one FK to `oqi_business_dependencies` —
`fk_oqi_business_impact_evaluations_dependency`, plain `(business_dependency_id, business_dependency_version)
→ (dependency_id, version)`, not tenant-qualified. No intervening commit since the R1 merge touches OQI6,
OQI4, OQI5, migrations, or tenant isolation of any kind.

## 3. Governing lineage

```
CDD-044 (OQI6 original architecture, migration 0026 -- authored the plain FK against the only key
         oqi_business_dependencies had at the time: its own globally-unique PK)
   -> CDD-050 / H4-R1 precedent (established the replace-FK technical pattern for this defect class)
   -> CDD-051 §9 (added uq_oqi_business_processes_tenant_pk; disclosed the sibling Dependency->Process
         gap; explicitly deferred it to "a future, separately-governed OQI6-R1")
   -> CDD-052 / OQI6-R1 (closed Dependency->Process; §8 explicitly disclosed and deferred this exact
         Evaluation->Dependency boundary to "a future, separately-governed OQI6-R2")
   -> OQI6-R2-DR (independently reproduced the defect; recommended Option B/replace; discovered two
         further out-of-scope Current*-pointer gaps, recommended as a future OQI6-R3)
   -> CDD-053 / OQI6-R2 (this document)
```
The omission was known and disclosed at every step, never accidental.

## 4. Defect re-verification (independently reproduced, not merely trusted from DR)

Reproduced live against a freshly-migrated head-`0041` PostgreSQL database, direct parameterized SQL
bypassing the service layer entirely:
```
CROSS-TENANT ATTACK (evaluation.tenant=A, dependency.tenant=B): ACCEPTED
SAME-TENANT CONTROL: ACCEPTED
```
Schema independently re-queried via `pg_constraint`: `oqi_business_dependencies` carries only its own
`PRIMARY KEY(dependency_id, version)` — no `UNIQUE(tenant_id, dependency_id, version)` exists anywhere.
`oqi_business_impact_evaluations` carries exactly the one plain FK reported by DR, unchanged since migration
`0026`. DR's factual claims are confirmed correct in every respect; no correction to DR's schema findings is
required.

## 5. Root cause (reaffirming OQI6-R2-DR)

`oqi_business_impact_evaluations` was authored (migration `0026`, CDD-044) against the only composite key
`oqi_business_dependencies` had at the time: its own plain, globally-unique `(dependency_id, version)`
primary key. That key remains globally unique today (`dependency_id` is a UUID, the PK enforces uniqueness
independent of tenant), so the plain FK is not ambiguous — it always resolves to exactly one real row — it
simply does not prove that the resolved row belongs to the referencing evaluation's own tenant. PostgreSQL
therefore proves only "referenced dependency exists," never "referenced dependency belongs to this
evaluation's tenant." Identical root cause and identical structural shape to R1.

`OqiBusinessImpactService.evaluate_business_impact_for_dependency` already performs the correct tenant-
scoped lookup (`get_latest_business_dependency(tenant_id=..., dependency_id=...)`, raising
`ValidationException` on a miss) before constructing an evaluation — the one governed production path
already rejects cross-tenant evaluation creation end-to-end. That protection is bypassable by any direct
persistence-layer write, independently reproduced in §4.

## 6. Frozen authority boundary (binding — scope statement)

```
A BusinessImpactEvaluation row owned by Tenant A must be structurally incapable of referencing a
BusinessDependency owned by Tenant B, even when all service/API validation is bypassed.
```
Independently confirmed correct as stated, verbatim, no precision correction needed. This document proves
and enforces exactly this boundary. It does **not** prove, and must not be represented as proving, that all
of OQI6 is tenant-safe.

## 7. Identity vs. tenant-authority distinction (binding, restated for zero ambiguity)

`(dependency_id, version)` is `oqi_business_dependencies`' own `PRIMARY KEY` — globally unique regardless of
tenant, independently reconfirmed live (a cross-tenant identity-collision attempt on the same
`(dependency_id, version)` pair is rejected with `UniqueViolation`, matching R1's own finding). This
correction does **not** redesign that primary key or its identity semantics: the defect is a tenant
**authority** gap at the relationship boundary, not an identity-ambiguity gap.
```
GLOBAL ROW IDENTITY ≠ TENANT AUTHORITY
A VALID FOREIGN KEY TARGET ≠ AN AUTHORIZED TENANT TARGET
```

## 8. Frozen parent candidate key

```
UNIQUE (tenant_id, dependency_id, version)
name: uq_oqi_business_dependencies_tenant_pk
on: oqi_business_dependencies
```
Independently re-verified: does not already exist under this or any other name; no naming collision
anywhere in the repository (`grep` confirms); `(dependency_id, version)` remains the primary key, untouched;
the new key is trivially unique as a superset of an already-unique key — safe by construction, requires no
data backfill or precondition check (identical to R1's own `uq_oqi_business_processes_tenant_pk` addition);
valid as a composite FK target (identical mechanism already proven twice — `uq_oqi_business_processes_
tenant_pk` by both `oqi_timeliness_policies` and, as of R1, `oqi_business_dependencies` itself).

## 9. Frozen child tenant-qualified FK

```
FOREIGN KEY (tenant_id, business_dependency_id, business_dependency_version)
REFERENCES oqi_business_dependencies (tenant_id, dependency_id, version)
name: fk_oqi_business_impact_evaluations_tenant_dependency
on: oqi_business_impact_evaluations
```
Column order and target compatibility independently verified against the frozen §8 parent key.

## 10. Corrected additive-vs-replacement reasoning (binding, carried forward from R1-VM's own correction)

PostgreSQL enforces every foreign key on a table conjunctively (`AND`, not `OR`). An additively-added
tenant-qualified FK (Option A: keep the old plain FK, add the new one alongside it) would, by itself,
already reject the exact §4 cross-tenant attack, because the cross-tenant row could never satisfy the new
FK's composite tuple match regardless of what the old FK independently permits. **This document does not
repeat the R1-DR original reasoning error** (which incorrectly claimed the old FK would "independently
permit" the attack despite a stronger FK). The actual, correct reason to select **Option B (replace)**:

1. the new tenant-qualified FK fully subsumes the old FK's entire referential-integrity purpose (any row
   satisfying it necessarily also identifies a genuinely-existing `(dependency_id, version)`, since the new
   FK's parent target is a superset key over the same primary-key columns);
2. the old FK becomes strictly redundant once the new one is added;
3. retaining a redundant, weaker FK alongside a stronger one creates two overlapping, textually-inconsistent
   statements of the same authority boundary, inviting future confusion about which one is authoritative;
4. migrations `0038` (H4-R1) and `0041` (OQI6-R1) already established the repository's own precedent of
   **replacing**, not retaining, a tenant-unqualified FK once a tenant-qualified equivalent exists;
5. exactly one FK should express the true authority boundary for a given child-parent relationship.

**OPTION B (REPLACE) is selected**, for authority/clarity reasons, not because Option A is technically
incapable of closing the gap.

## 11. Exact migration revision

```
revision:       0042_oqi6_r2_evaluation_tenancy      (31 characters; independently re-verified against the
                                                        live alembic_version.version_num VARCHAR(32) column
                                                        width before freezing)
down_revision:  0041_oqi6_r1_dependency_tenancy
filename:       backend/app/infrastructure/persistence/migrations/versions/0042_oqi6_r2_evaluation_tenancy.py
```
Independently re-confirmed: current head is still `0041_oqi6_r1_dependency_tenancy` (41 migration files);
no migration has appeared since DR; no naming collision.

## 12. Migration chain

`0040 → 0041 → 0042`, linear. `0001`-`0041` remain byte-for-byte unmodified by this migration.

## 13. Frozen upgrade order (binding)

```
op.create_unique_constraint(
    "uq_oqi_business_dependencies_tenant_pk",
    "oqi_business_dependencies",
    ["tenant_id", "dependency_id", "version"],
)
op.drop_constraint(
    "fk_oqi_business_impact_evaluations_dependency",
    "oqi_business_impact_evaluations",
    type_="foreignkey",
)
op.create_foreign_key(
    "fk_oqi_business_impact_evaluations_tenant_dependency",
    "oqi_business_impact_evaluations",
    "oqi_business_dependencies",
    ["tenant_id", "business_dependency_id", "business_dependency_version"],
    ["tenant_id", "dependency_id", "version"],
)
```
No data UPDATE/DELETE. No table/column change. No change to any other constraint.

## 14. Frozen downgrade order (binding)

```
op.drop_constraint(
    "fk_oqi_business_impact_evaluations_tenant_dependency",
    "oqi_business_impact_evaluations",
    type_="foreignkey",
)
op.create_foreign_key(
    "fk_oqi_business_impact_evaluations_dependency",
    "oqi_business_impact_evaluations",
    "oqi_business_dependencies",
    ["business_dependency_id", "business_dependency_version"],
    ["dependency_id", "version"],
)
op.drop_constraint("uq_oqi_business_dependencies_tenant_pk", "oqi_business_dependencies", type_="unique")
```
The candidate key is dropped last — no live FK depends on it once the tenant-qualified FK has already been
dropped in this same downgrade.

## 15. Fail-closed legacy-data policy (binding)

Independently reconfirmed: zero `oqi_business_impact_evaluations` rows and zero `oqi_business_dependencies`
rows exist in the currently-inspected dev/test databases. This does not guarantee every future deployment
database is empty. The migration's `upgrade()` performs no row-level `UPDATE`/`DELETE`/normalization/
reassignment of any kind. PostgreSQL's own `ADD CONSTRAINT ... FOREIGN KEY` validation raises a genuine
`IntegrityError` and aborts the migration transaction if any existing row would violate the new tenant-
qualified FK (transactional DDL, matching R1's and H4-R1's own established, already-proven convention) — no
separate governed remediation exists or is required at this time.
```
INVALID LEGACY CROSS-TENANT DATA
        -> POSTGRESQL CONSTRAINT VALIDATION FAILURE
        -> MIGRATION TRANSACTION ABORTS
        -> ALEMBIC HEAD REMAINS 0041
        -> DATA REMAINS BYTE-UNCHANGED
```

## 16. Table-count invariant

Constraint-only correction. Governed table count remains **123** before and after. Independently
re-verified live.

## 17. ORM authorization (binding)

`backend/app/infrastructure/persistence/models/oqi_business_impact.py`:

`OqiBusinessDependencyORM.__table_args__` — **add ONLY**:
```python
UniqueConstraint(
    "tenant_id", "dependency_id", "version", name="uq_oqi_business_dependencies_tenant_pk"
),
```
No column addition, no column deletion, no nullability change, no type change, no PK change.

`OqiBusinessImpactEvaluationORM.__table_args__` — **replace ONLY** the existing
`ForeignKeyConstraint(["business_dependency_id", "business_dependency_version"], [...],
name="fk_oqi_business_impact_evaluations_dependency")` with:
```python
ForeignKeyConstraint(
    ["tenant_id", "business_dependency_id", "business_dependency_version"],
    [
        "oqi_business_dependencies.tenant_id",
        "oqi_business_dependencies.dependency_id",
        "oqi_business_dependencies.version",
    ],
    name="fk_oqi_business_impact_evaluations_tenant_dependency",
)
```
No other class in this file changes shape. No new table. `fk_oqi_business_impact_evaluations_current_impact`
(the OQI4 cross-domain reference) is untouched.

## 18. Domain/service/repository preservation (binding)

```
BusinessDependency domain model:            UNCHANGED
BusinessImpactEvaluation domain model:      UNCHANGED
BusinessImpactOutcome / Criticality:        UNCHANGED
RelianceState / reliance derivation:        UNCHANGED
Business-impact/dependency/process lifecycle: UNCHANGED
OqiBusinessImpactService:                   UNCHANGED — existing tenant-scoped validation
                                              (evaluate_business_impact_for_dependency's
                                              get_latest_business_dependency call) remains as
                                              defense-in-depth, not removed merely because the
                                              database becomes independently safe
OqiBusinessImpactRepositoryImpl:            UNCHANGED
API:                                         UNCHANGED
Frontend:                                    UNCHANGED
```
```
SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT
```
Both layers remain in force simultaneously; neither substitutes for the other.

## 19. OQI6-R1 preservation (binding)

`fk_oqi_business_dependencies_tenant_process` and `uq_oqi_business_processes_tenant_pk` are read-only inputs
to this correction — neither touched nor altered. Independently reconfirmed live, unmodified, at §4. The
Dependency→Process boundary remains structurally tenant-qualified after this correction. R2-I/VM's own test
matrix (§25 below) must explicitly re-prove this.

## 20. H5 Timeliness preservation (binding)

No R2 change touches `oqi_timeliness_policies`, `TimelinessPolicy`, `TimelinessEvaluation`,
`TimelinessFinding`, or the `BusinessProcess` tenant FK. H5 is entirely outside this table pair — confirmed
via repository-wide grep for any reference connecting H5 Timeliness to `oqi_business_impact_evaluations` or
`oqi_business_dependencies`' new key (none exists).

## 21. OQI4/OQI5/Reliance preservation (binding)

```
FindingFamily / FindingStorageFamily:        UNCHANGED
CurrentOntologyImpact / OntologyImpactEvaluation semantics: UNCHANGED
OQI5 remediation / agent roles / recommendation-authorization boundaries: UNCHANGED
Reliance state model / open_finding_refs / pending-remediation ordering: UNCHANGED
```
Confirmed via source: no OQI4/OQI5/Reliance file references this table pair's FK definition at all; this
correction is scoped to exactly the two `__table_args__` edits in §17.

## 22. OQI6-R3 explicit deferral (binding)

```
OQI6-R3 — Current* Pointer Tenant-Isolation Correction
DEFERRED — FUTURE SEPARATELY GOVERNED PHASE
```
OQI6-R2-DR's exhaustive audit independently reproduced two further structural gaps, each a **separate
authority boundary** from this correction's target (different table pairs, requiring their own new tenant-
qualified parent keys on `oqi_business_impact_evaluations` and `oqi_reliance_evaluations` respectively):
```
current_business_impacts -> oqi_business_impact_evaluations: cross-tenant pointer reproduced ACCEPTED
current_reliance -> oqi_reliance_evaluations: cross-tenant pointer reproduced ACCEPTED
```
This document records these defects and their separation rationale only. R2 does not solve them, does not
prejudge R3's exact architecture, and R3 must begin with its own independent DR.

## 23. Production-orchestration explicit deferral (binding)

```
OQI4/OQI6/OQI5 production-orchestration trigger:
SEPARATE FUTURE GOVERNED INITIATIVE
```
```
R2 STRUCTURAL TENANT CORRECTION ≠ PRODUCTION ORCHESTRATION
```
No scheduler, worker, event bus, CDC, or background-processing change is authorized or required.

## 24. Frozen test-implementation strategy

Expected file: `backend/app/tests/test_oqi_business_impact.py` (unchanged from R1's own conclusion — the
smallest correct, already-established location; no new dedicated file is authorized).

Independently reconfirmed: `test_oqi6_business_impact_orms_have_single_construction_site`
(`test_runtime_architecture.py`) governs `OqiBusinessImpactEvaluationORM` identically to how it governed
`OqiBusinessDependencyORM` for R1 — exactly one authorized construction site
(`oqi_business_impact_repository.py`). `test_oqi_business_impact.py` currently contains zero direct
constructions of `OqiBusinessImpactEvaluationORM` (confirmed via `grep -c`). Therefore, exactly as in R1,
the permanent structural-bypass tests must use **raw parameterized SQL** (`session.execute(text(...))`),
never `OqiBusinessImpactEvaluationORM(...)` construction, to avoid requiring a fourth (unauthorized)
implementation path.

**Naming correction (binding, addressing R1-VM's disclosed P3 finding):** test names must not repeat R1's
"direct_orm" imprecision (R1's tests used raw SQL but were named `test_ti01_direct_orm_...`). R2's test names
must accurately describe the actual mechanism — e.g. `test_r2ti01_direct_persistence_same_tenant_...` /
`test_r2ti02_direct_persistence_cross_tenant_..._rejected_by_postgresql` — never using the word "orm" to
describe raw-SQL-based tests.

## 25. Frozen permanent R2-TI test matrix (binding — R2-TI-01 through R2-TI-12)

```
R2-TI-01  Direct-persistence same-tenant evaluation->dependency accepted (raw parameterized SQL).
R2-TI-02  Direct-persistence cross-tenant evaluation->dependency REJECTED by PostgreSQL with a genuine
          sqlalchemy.exc.IntegrityError (raw parameterized SQL; a service ValidationException alone does
          not satisfy this test).
R2-TI-03  Governed service (evaluate_business_impact_for_dependency) same-tenant path succeeds.
R2-TI-04  Governed service foreign-tenant dependency_id raises ValidationException (defense-in-depth
          unchanged, §18).
R2-TI-05  pg_constraint introspection: fk_oqi_business_impact_evaluations_dependency does NOT exist after
          upgrade.
R2-TI-06  pg_constraint introspection: fk_oqi_business_impact_evaluations_tenant_dependency exists, with
          exact child columns (tenant_id, business_dependency_id, business_dependency_version) and exact
          parent columns (tenant_id, dependency_id, version) on oqi_business_dependencies.
R2-TI-07  pg_constraint introspection: uq_oqi_business_dependencies_tenant_pk exists, unmodified, after
          this migration.
R2-TI-08  pg_constraint introspection: uq_oqi_business_processes_tenant_pk AND
          fk_oqi_business_dependencies_tenant_process (R1's own constraints) remain present and
          functional, unmodified.
R2-TI-09  Migration round trip: upgrade to 0042 -> downgrade to 0041 -> upgrade to 0042, table count
          constant at 123 throughout; old FK restored exactly on downgrade and removed exactly on the
          second upgrade; both tenant-qualified keys present at every relevant step; a legitimate
          same-tenant BusinessImpactEvaluation row survives byte-unchanged across the round trip.
R2-TI-10  Fail-closed proof: on a pre-R2 schema (post-0041, pre-0042), deliberately insert a cross-tenant
          BusinessImpactEvaluation row via raw parameterized SQL (which succeeds pre-correction, per §4);
          attempt the 0042 upgrade against that data; upgrade must fail (PostgreSQL raises on ADD
          CONSTRAINT ... FOREIGN KEY validation), alembic_version must remain 0041, and the violating row
          must remain byte-unchanged; clean the row; re-attempt upgrade; it must then succeed.
R2-TI-11  H5 Timeliness crown/tenant-isolation tests remain green, unmodified (reuse
          test_oqi_h5_timeliness_crown.py's own established seeding helpers by import, as R1 did — do not
          duplicate them).
R2-TI-12  Existing OQI6 BusinessImpact/Reliance crown and domain tests pass unmodified — no existing test
          function, fixture, or assertion in test_oqi_business_impact.py may be altered.
```

## 26. Docker verification contract (binding, mandatory for R2-I and R2-VM)

Fresh `docker compose build --no-cache` (or the repository's exact equivalent); a genuinely fresh compose
project/database, never reused from a prior phase. Inside the fresh runtime, against real PostgreSQL, prove
at minimum: Alembic head = `0042_oqi6_r2_evaluation_tenancy`; table count = 123; `uq_oqi_business_
dependencies_tenant_pk` present; old plain FK absent; new tenant-qualified FK present with exact shape;
same-tenant direct-persistence accepted; cross-tenant direct-persistence rejected with a genuine PostgreSQL
`foreign_key_violation`; R1's own `fk_oqi_business_dependencies_tenant_process`/`uq_oqi_business_processes_
tenant_pk` boundary remains enforced; H5 Timeliness regression passes; OQI6 BusinessImpact/Reliance
regression passes; backend health; frontend health/build. Host-only proof is insufficient — this mirrors
R1's own already-proven Docker contract exactly.

## 27. Full regression contract (binding)

R2-I and R2-VM must run: the focused R2-TI-01 through R2-TI-12 matrix; the full existing
`test_oqi_business_impact.py` suite (BusinessImpact/Reliance crowns, migration round-trip); R1's own tenant-
isolation tests (proving the R1 boundary is undisturbed); H5 Timeliness crown; the full backend test suite
(`pytest app/tests`, with `CTEC_DATABASE_URL`/`CTEC_TEST_DATABASE_URL` set per repository convention); `black
--check`, `isort --check-only`, `ruff check`, whole-package `mypy app`; frontend `npm test`, `npm run lint`,
`npx tsc --noEmit`, `npm run build`; fresh `--no-cache` Docker verification per §26; CI exact-head
verification before any merge.

## 28. Exact new-path authorization (binding — a maximum permitted write set, not a requirement to touch
every listed path beyond what correctness requires)

```
CREATE = 1
MODIFY = 2
DELETE = 0
TOTAL  = 3
```
```
CREATE  backend/app/infrastructure/persistence/migrations/versions/0042_oqi6_r2_evaluation_tenancy.py
        Migration implementing §13/§14 exactly. No other schema/table/column change.

MODIFY  backend/app/infrastructure/persistence/models/oqi_business_impact.py
        Exactly the two edits authorized in §17: add ONE UniqueConstraint to
        OqiBusinessDependencyORM.__table_args__; replace ONE ForeignKeyConstraint in
        OqiBusinessImpactEvaluationORM.__table_args__. No other class in this file changes shape.

MODIFY  backend/app/tests/test_oqi_business_impact.py
        Append the R2-TI-01 through R2-TI-12 matrix (§25) as new top-level test functions, matching this
        file's own established flat-function style, using raw parameterized SQL per §24. No existing test
        function, fixture, or assertion in this file is modified.
```
Independently confirmed clean before freezing this authorization: zero references anywhere to the old
constraint name `fk_oqi_business_impact_evaluations_dependency` outside migration `0026` (historical,
unmodified) and the one model file authorized above; zero collision with either new constraint name; every
migration-head assertion across the test suite resolves dynamically (`ScriptDirectory.get_current_head()` /
`alembic.command.upgrade(config, "head")`), none hardcodes a revision-name list;
`test_runtime_architecture.py`'s `AUTHORIZED_CHANGED_PATHS` firewall governs uncommitted working-tree state
relative to `HEAD` only and requires no modification (satisfied trivially once this phase's changes are
committed); no file anywhere hardcodes a total OQI6/business-impact-evaluation migration count. No path
beyond the three above is authorized.

## 29. Forbidden implementation paths (binding, exhaustive)

Domain models; application services; repositories (beyond the two authorized ORM edits); API routes;
frontend; OQI4; OQI5; Reliance semantics; Timeliness semantics; BusinessProcess semantics;
`current_business_impacts`/`current_reliance` pointer schema (the R3 target); production orchestration;
`architecture/INDEX.md` (independently reconfirmed untouched by any OQI H1–H5/R1 phase, same precedent
applies); any existing governance document. No DELETE. No opportunistic cleanup. No refactoring. No
formatting-only churn outside the three authorized paths.

## 30. R2-I STOP conditions (binding, exhaustive)

OQI6-R2-I must STOP, preserve evidence, and return for renewed narrow governance rather than improvise, if
any of the following occurs:

```
 1. authoritative main moves materially (touches OQI6/OQI4/OQI5/migrations/tenant isolation/H5 Timeliness).
 2. this document's own governance hash (recorded §36) drifts before implementation begins.
 3. any file outside the exact three §28 paths requires a write.
 4. the migration requires a new column, a new table, or a change to any other constraint.
 5. oqi_business_dependencies' PRIMARY KEY(dependency_id, version) requires any change.
 6. uq_oqi_business_dependencies_tenant_pk cannot be added without a data-compatibility issue.
 7. the child tenant columns/order differ from §9.
 8. a naming collision is discovered against either new constraint name.
 9. BusinessDependency or BusinessImpactEvaluation domain semantics require any change.
10. service, API, or frontend semantics require any change.
11. R1's own constraints (fk_oqi_business_dependencies_tenant_process, uq_oqi_business_processes_
    tenant_pk) require any modification.
12. H5 Timeliness requires any change.
13. the R3 boundary (current_business_impacts/current_reliance) requires any modification here.
14. OQI4/OQI5 orchestration requires any modification.
15. any existing legacy data is found to violate the new FK and no governed remediation exists (§15) --
    migration must fail closed, not silently repair.
16. the same-tenant positive-control path is rejected post-correction.
17. the cross-tenant attack is still ACCEPTED post-correction.
18. any H1-H5/OQI6 crown/regression value changes semantically.
19. whole-package mypy, black, isort, or ruff fails as a result of this correction.
20. full clean-candidate regression fails as a result of this correction.
21. Docker proof differs materially from host proof.
22. migration chain becomes non-linear or produces a second head.
23. any DELETE is required.
24. CDD-044, CDD-050, CDD-051, CDD-052, or their own frozen Artifact Authorizations require any
    modification.
25. any P0 appears, or any material P1 remains unresolved outside the exact frozen correction.
```

## 31. VM/merge gate (binding, restated)

OQI6-R2-VM must independently re-derive — not merely trust I's report — every item in §30's proof surface
plus: exact ancestry; governance hash; exact diff (governance-only + implementation-only + combined);
migration chain/round trip/fail-closed proof; R1 preservation; H5 preservation; OQI6 BusinessImpact/Reliance
regression; full backend/static/frontend regression; fresh `--no-cache` Docker proof; CI exact-head status;
confirmation that R3's defects remain explicitly tracked as a separate boundary (not silently treated as
solved or as a hidden R2 P1). Merge requires `P0 = 0` and `P1 = 0` for the R2 authorized boundary. Merge must
bind to the exact approved candidate head (`--match-head-commit` or repository-equivalent exact-head
mechanism); post-merge verification must repeat the full structural and adversarial proof against post-merge
main, including a second fresh `--no-cache` Docker build.

## 32. Allowed claim

```
A BusinessImpactEvaluation can no longer reference a BusinessDependency belonging to another tenant at
the PostgreSQL structural layer.
```

## 33. Forbidden claims

```
"OQI6 is fully tenant-isolated."
"All OQI6 cross-tenant paths are closed."
"No OQI6 tenant-isolation defects remain."
"OQI6 is production-orchestrated."
"R2 closes the Current* pointer defects."
```
Each of these is false because R3 remains required and production orchestration remains a separate,
undertaken-elsewhere initiative.

## 34. Severity status

```
Before this document: P0 = 0, P1 = 1 (a live, independently re-reproduced PostgreSQL structural tenant-
                       isolation gap on oqi_business_impact_evaluations -> oqi_business_dependencies; the
                       governed service layer remains protective for every current application code path,
                       and zero rows anywhere currently exploit it, so no currently-reachable production
                       exploit is demonstrated -- P1, not P0, consistent with R1's own classification)
                       P2 = 1 (the two Current*-pointer gaps, disclosed, explicitly deferred to a future
                       OQI6-R3, not blocking this document's own governance/implementation)
After this document:  P0 = 0, P1 = 0, P2 = 1 (R3 remains open and explicitly tracked, not solved),
                       P3 = 0 (pending the three-path correction §28 authorizes and its own fresh
                       whole-package static / real-PostgreSQL adversarial / Docker / full regression
                       re-verification, per §25's frozen matrix)
```

## 35. Implementation phasing

```
OQI6-R2-G  (this document)
  -> OQI6-R2-I   (single implementation phase -- no I1/I2 split; no genuine architectural boundary
                   separates the three §28 paths from one another)
  -> OQI6-R2-VM  (adversarial verify + merge, restarting fully against the new candidate)
  -> OQI6-R3-DR  (separately governed; begins only after R2 is fully closed)
```

## 36. Governance byte-integrity

This document and its own content are the sole new governance artifact this phase publishes. `CDD-044`,
`CDD-050`, `CDD-051`, `CDD-052`, and their respective Artifact Authorizations are independently re-hashed
immediately before this document's own publication and confirmed byte-identical to their prior published
values; none is modified by this correction.

## 37. Authorization

This document is approved and published as a standalone governance artifact, following the established
precedent of `CDD-052-Artifact-Authorization-OQI6-R1-Business-Dependency-Tenant-Isolation-Correction.md`.
Implementation against §28's exact three-path authorization may proceed under `OQI6-R2-I`.
