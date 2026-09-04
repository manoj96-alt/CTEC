# CDD-054 — OQI6-R3 Current Pointer Tenant-Isolation Correction (OQI6-R3)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-052-Artifact-Authorization-OQI6-R1-Business-Dependency-Tenant-Isolation-Correction.md` and
`CDD-053-Artifact-Authorization-OQI6-R2-Business-Impact-Evaluation-Dependency-Tenant-Isolation-Correction.md`
(the exact governance shape and corrected additive-vs-replacement reasoning this document reuses);
`CDD-050-Artifact-Authorization-H4-R1-Reference-Tenant-Isolation-Correction-Amendment.md` (precedent for
correcting multiple columns/relationships sharing one defect class in a single amendment)
Governs: base architecture `CDD-044-Ontology-Quality-Intelligence-Criticality-Business-Impact-Explainable-
Reliance.md` (frozen, NOT reopened, NOT modified by this document); `main` authoritative state
`43f3f729165147069992aca3f86f01abc9cb2cb8` (OQI6-R2-VM's independently verified merge commit, independently
re-confirmed unchanged as of this document's own publication)
Classification: DATABASE-LEVEL STRUCTURAL TENANT-ISOLATION GAP (constraint-only correction; no schema
topology change, no table addition, no column addition, no domain/service/API/frontend semantic change)

## 1. Purpose

Authorizes the exact, narrow, additive-then-replacing correction of two genuine database-level tenant-
isolation defects — `current_business_impacts → oqi_business_impact_evaluations` and `current_reliance →
oqi_reliance_evaluations` — independently discovered and reproduced by OQI6-R3-DR, independently
re-reproduced by this governance phase, and explicitly disclosed and deferred throughout the R1/R2 lineage
(most recently CDD-053's own §22 deferral). **CDD-044, CDD-050, CDD-051, CDD-052, and CDD-053 are not
modified, not reopened, and remain FROZEN exactly as originally published** — this document is a new,
standalone, additive governance artifact.

## 2. Authoritative baseline — independently re-derived

`origin/main` and GitHub `main` both equal `43f3f729165147069992aca3f86f01abc9cb2cb8`, unchanged since
OQI6-R3-DR. PR #188 independently reconfirmed `MERGED`. R1's `uq_oqi_business_processes_tenant_pk`/
`fk_oqi_business_dependencies_tenant_process` and R2's `uq_oqi_business_dependencies_tenant_pk`/
`fk_oqi_business_impact_evaluations_tenant_dependency` all independently reconfirmed live, unmodified,
functional. Migration head still `0042_oqi6_r2_evaluation_tenancy`, single head, 123 tables.

## 3. One-R3 decision, re-verified

Both boundaries independently re-reproduced live:
```
BOUNDARY A CROSS-TENANT: ACCEPTED
BOUNDARY A SAME-TENANT CONTROL: ACCEPTED
BOUNDARY B CROSS-TENANT: ACCEPTED
BOUNDARY B SAME-TENANT CONTROL: ACCEPTED
```
Both share the identical invariant, identical root cause (evaluation table has no tenant-qualified
candidate key), identical proposed fix shape, identical lifecycle/transaction semantics, and zero existing-
data risk in both. `OPTION 1 — ONE R3` is reconfirmed correct; independently re-derived, not merely trusted
from DR.

## 4. Frozen R3 architectural invariant (binding)

```
A tenant-owned OQI6 Current* pointer must be structurally incapable of referencing an evaluation
row owned by another tenant, even when service, repository, ORM-construction, and API validation
are bypassed.
```
Applies exactly to `CurrentBusinessImpact → BusinessImpactEvaluation` and `CurrentReliance →
RelianceEvaluation`. Not extended to OQI4's `CurrentOntologyImpact` or any other dimension.

## 5. Identity/authority principle (binding, restated)

```
GLOBAL ROW IDENTITY ≠ TENANT AUTHORITY
TENANT-AWARE UUID GENERATION ≠ TENANT-QUALIFIED FOREIGN-KEY ENFORCEMENT
```
Both `derive_business_impact_evaluation_id` and `derive_reliance_evaluation_id` independently re-confirmed
to embed `tenant_id` as UUID5 material — an identity-derivation convention, not a substitute for structural
database enforcement, exactly as R2 established.

## 6. Re-verified exact schema

```
OqiBusinessImpactEvaluationORM: PRIMARY KEY(evaluation_id); tenant_id present; NO version column.
CurrentBusinessImpactORM: PRIMARY KEY(tenant_id, business_dependency_id); latest_evaluation_id NOT NULL;
    weak FK "fk_current_business_impacts_latest_evaluation_id" -> oqi_business_impact_evaluations(evaluation_id).
OqiRelianceEvaluationORM: PRIMARY KEY(evaluation_id); tenant_id present; NO version column.
CurrentRelianceORM: PRIMARY KEY(tenant_id, ontology_element_type, ontology_element_id);
    latest_evaluation_id NOT NULL; weak FK "fk_current_reliance_latest_evaluation_id" ->
    oqi_reliance_evaluations(evaluation_id).
```
Independently reconfirmed via `pg_constraint` against a freshly-migrated head-`0042` database — byte-for-
byte matching DR, zero ORM/schema disagreement, exact weak-FK names confirmed live (not inferred).

## 7. Non-versioned key semantics (binding)

Neither evaluation table has a version column. The parent authority keys are exactly `(tenant_id,
evaluation_id)` — **two columns**, not R1/R2's `(tenant_id, id, version)` three-column shape. No synthetic
version column is introduced.

## 8. Frozen BusinessImpact parent key

```
UNIQUE (tenant_id, evaluation_id)
name: uq_oqi_business_impact_evaluations_tenant_pk
on: oqi_business_impact_evaluations
```
Additive to the existing `PRIMARY KEY(evaluation_id)`, which remains unchanged. Safe by construction (no
backfill needed — `evaluation_id` is already globally unique, so `(tenant_id, evaluation_id)` is trivially
unique as a superset). No naming collision found anywhere in the repository.

## 9. Frozen BusinessImpact child FK

```
FOREIGN KEY (tenant_id, latest_evaluation_id)
REFERENCES oqi_business_impact_evaluations (tenant_id, evaluation_id)
name: fk_current_business_impacts_tenant_evaluation
on: current_business_impacts
```
Replaces `fk_current_business_impacts_latest_evaluation_id` (confirmed live, exact name).

## 10. Frozen Reliance parent key

```
UNIQUE (tenant_id, evaluation_id)
name: uq_oqi_reliance_evaluations_tenant_pk
on: oqi_reliance_evaluations
```
Additive to the existing `PRIMARY KEY(evaluation_id)`, unchanged. Safe by construction, no collision found.

## 11. Frozen Reliance child FK

```
FOREIGN KEY (tenant_id, latest_evaluation_id)
REFERENCES oqi_reliance_evaluations (tenant_id, evaluation_id)
name: fk_current_reliance_tenant_evaluation
on: current_reliance
```
Replaces `fk_current_reliance_latest_evaluation_id` (confirmed live, exact name).

## 12. Corrected additive-vs-replacement reasoning (binding, carried forward from R1/R2)

PostgreSQL enforces every foreign key on a table conjunctively. Retaining both the weak FK and a correctly-
enforced tenant-qualified FK would **already** structurally prevent cross-tenant references — replacement
is **not** required because coexistence would somehow permit a bypass. **OPTION B (REPLACE) is selected**
for these precise, technically correct reasons:

1. the tenant-qualified FK fully subsumes the weak FK's referential-integrity purpose (its parent target is
   a superset key over the same primary-key column);
2. the weak FK becomes strictly redundant once the new one is added;
3. retaining a redundant, weaker FK creates two overlapping statements of the same authority boundary;
4. migrations `0038`, `0041`, and `0042` (H4-R1, R1, R2) already established the repository's own precedent
   of replacing, not retaining, a tenant-unqualified FK once a tenant-qualified equivalent exists;
5. exactly one FK should express the true authority boundary for a given child-parent relationship.

## 13. Exact migration revision

```
revision:       0043_oqi6_r3_current_tenancy      (28 characters; independently re-verified against the
                                                     live alembic_version.version_num VARCHAR(32) column
                                                     width before freezing)
down_revision:  0042_oqi6_r2_evaluation_tenancy
filename:       backend/app/infrastructure/persistence/migrations/versions/0043_oqi6_r3_current_tenancy.py
```
Independently re-confirmed: current head still `0042_oqi6_r2_evaluation_tenancy`; single linear head; no
naming collision.

## 14. Frozen upgrade order (binding)

```
op.create_unique_constraint(
    "uq_oqi_business_impact_evaluations_tenant_pk",
    "oqi_business_impact_evaluations",
    ["tenant_id", "evaluation_id"],
)
op.create_unique_constraint(
    "uq_oqi_reliance_evaluations_tenant_pk",
    "oqi_reliance_evaluations",
    ["tenant_id", "evaluation_id"],
)
op.drop_constraint(
    "fk_current_business_impacts_latest_evaluation_id",
    "current_business_impacts",
    type_="foreignkey",
)
op.create_foreign_key(
    "fk_current_business_impacts_tenant_evaluation",
    "current_business_impacts",
    "oqi_business_impact_evaluations",
    ["tenant_id", "latest_evaluation_id"],
    ["tenant_id", "evaluation_id"],
)
op.drop_constraint(
    "fk_current_reliance_latest_evaluation_id",
    "current_reliance",
    type_="foreignkey",
)
op.create_foreign_key(
    "fk_current_reliance_tenant_evaluation",
    "current_reliance",
    "oqi_reliance_evaluations",
    ["tenant_id", "latest_evaluation_id"],
    ["tenant_id", "evaluation_id"],
)
```
No data UPDATE/DELETE. No table/column change. No change to any R1/R2/H5 constraint.

## 15. Frozen downgrade order (binding)

```
op.drop_constraint("fk_current_reliance_tenant_evaluation", "current_reliance", type_="foreignkey")
op.create_foreign_key(
    "fk_current_reliance_latest_evaluation_id", "current_reliance", "oqi_reliance_evaluations",
    ["latest_evaluation_id"], ["evaluation_id"],
)
op.drop_constraint(
    "fk_current_business_impacts_tenant_evaluation", "current_business_impacts", type_="foreignkey"
)
op.create_foreign_key(
    "fk_current_business_impacts_latest_evaluation_id", "current_business_impacts",
    "oqi_business_impact_evaluations", ["latest_evaluation_id"], ["evaluation_id"],
)
op.drop_constraint("uq_oqi_reliance_evaluations_tenant_pk", "oqi_reliance_evaluations", type_="unique")
op.drop_constraint(
    "uq_oqi_business_impact_evaluations_tenant_pk", "oqi_business_impact_evaluations", type_="unique"
)
```
Both new tenant-qualified FKs are dropped before their respective candidate keys — no live FK ever depends
on a key already dropped.

## 16. Table-count invariant

Constraint-only correction. Governed table count remains **123** before and after. Independently
re-confirmed live.

## 17. Fail-closed legacy-data policy (binding)

```
INVALID LEGACY CROSS-TENANT CURRENT POINTER
        -> POSTGRESQL FK VALIDATION FAILS
        -> MIGRATION TRANSACTION ABORTS
        -> ALEMBIC HEAD DOES NOT ADVANCE
        -> INVALID ROW REMAINS BYTE-UNCHANGED
        -> NO SILENT REPAIR
```
Independently reconfirmed: zero existing invalid `CurrentBusinessImpact`/`CurrentReliance` pointers in the
current dev database (explicit join query). No row-level UPDATE/DELETE/reassignment/quarantine is
authorized in the migration.

## 18. ORM authorization (binding)

`backend/app/infrastructure/persistence/models/oqi_business_impact.py` — exactly four semantic edits:

1. `OqiBusinessImpactEvaluationORM.__table_args__` — add `UniqueConstraint("tenant_id", "evaluation_id",
   name="uq_oqi_business_impact_evaluations_tenant_pk")`.
2. `CurrentBusinessImpactORM.__table_args__` — replace the existing `ForeignKeyConstraint(["latest_
   evaluation_id"], ["oqi_business_impact_evaluations.evaluation_id"], name="fk_current_business_impacts_
   latest_evaluation_id")` with `ForeignKeyConstraint(["tenant_id", "latest_evaluation_id"],
   ["oqi_business_impact_evaluations.tenant_id", "oqi_business_impact_evaluations.evaluation_id"],
   name="fk_current_business_impacts_tenant_evaluation")`.
3. `OqiRelianceEvaluationORM.__table_args__` — add `UniqueConstraint("tenant_id", "evaluation_id",
   name="uq_oqi_reliance_evaluations_tenant_pk")`.
4. `CurrentRelianceORM.__table_args__` — replace the existing `ForeignKeyConstraint(["latest_evaluation_
   id"], ["oqi_reliance_evaluations.evaluation_id"], name="fk_current_reliance_latest_evaluation_id")` with
   `ForeignKeyConstraint(["tenant_id", "latest_evaluation_id"], ["oqi_reliance_evaluations.tenant_id",
   "oqi_reliance_evaluations.evaluation_id"], name="fk_current_reliance_tenant_evaluation")`.

No column addition, deletion, nullability, or type change. No PK redesign. No version field. No other class
in this file changes shape.

## 19. Domain/service/repository preservation (binding)

```
BusinessImpactEvaluation / RelianceEvaluation / CurrentBusinessImpact / CurrentReliance domain models: UNCHANGED
OqiBusinessImpactService (evaluate_business_impact_for_dependency / evaluate_reliance_for_subject): UNCHANGED
OqiBusinessImpactRepositoryImpl: UNCHANGED
API / Frontend: UNCHANGED
```
```
SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT
```
The existing implicit-by-construction service safety (the service always derives `latest_evaluation_id`
from the same call's own tenant-scoped evaluation) remains as defense-in-depth, not removed.

## 20. R1 preservation

`fk_oqi_business_dependencies_tenant_process` and `uq_oqi_business_processes_tenant_pk` are read-only
inputs — neither touched nor altered. Independently reconfirmed live, unmodified.

## 21. R2 preservation

`fk_oqi_business_impact_evaluations_tenant_dependency` and `uq_oqi_business_dependencies_tenant_pk` are
read-only inputs — neither touched nor altered. Independently reconfirmed live, unmodified.

## 22. OQI4 CurrentOntologyImpact deferral (binding, explicit)

```
OQI4 CURRENTONTOLOGYIMPACT POINTER TENANT-ISOLATION CORRECTION
DEFERRED — FUTURE SEPARATELY GOVERNED PHASE
```
R3-DR independently discovered `current_ontology_impacts → ontology_impact_evaluations` (OQI4) carries the
identical structural defect class. It is a **different, already-frozen dimension** (CDD-042), out of OQI6-
R3's scope. This document does not modify `CurrentOntologyImpactORM`, `ontology_impact_evaluations`, any
OQI4 migration, or any OQI4 test.

## 23. Production-orchestration deferral (binding, restated)

```
OQI4/OQI6/OQI5 Production Orchestration
DEFERRED — SEPARATE FUTURE GOVERNED INITIATIVE
```
No scheduler, worker, event bus, CDC, or new production caller is authorized or required.

## 24. Authority firewall (binding)

No R3 implementation may alter: recommendation/authorization separation; remediation/resolution separation;
human or agent authority; the Reliance three-state model; OQI4 impact semantics; H5 Timeliness semantics;
`FindingFamily`; `FindingStorageFamily`. This is a database tenant-authority correction only.

## 25. Frozen test-implementation strategy

Expected file: `backend/app/tests/test_oqi_business_impact.py` (unchanged from R1/R2's own conclusion).
Independently reconfirmed: `test_oqi6_business_impact_orms_have_single_construction_site`
(`test_runtime_architecture.py`) governs all four relevant classes (`OqiBusinessImpactEvaluationORM`,
`CurrentBusinessImpactORM`, `OqiRelianceEvaluationORM`, `CurrentRelianceORM`) identically to how it governed
R1's and R2's own target classes. Therefore the permanent structural-bypass tests must use **raw
parameterized SQL**, never direct ORM construction of any of these four classes, to avoid requiring a fourth
(unauthorized) implementation path. Legitimate evaluation rows may still be seeded through the governed
service (`evaluate_business_impact_for_dependency`/`evaluate_reliance_for_subject`) where that does not
require constructing a forbidden class directly; the adversarial Current*-pointer insert itself must be raw
SQL. Test names must accurately describe the mechanism (`direct_persistence`, not `direct_orm`), per R2's
own GA2 correction.

## 26. Frozen permanent R3-TI test matrix (binding)

```
Boundary A — CurrentBusinessImpact
R3-TI-A01  Same-tenant direct persistence accepted.
R3-TI-A02  Cross-tenant direct persistence REJECTED by PostgreSQL with genuine sqlalchemy.exc.IntegrityError.
R3-TI-A03  Governed service path (evaluate_business_impact_for_dependency) same-tenant succeeds.
R3-TI-A04  pg_constraint: uq_oqi_business_impact_evaluations_tenant_pk exact.
R3-TI-A05  pg_constraint: fk_current_business_impacts_tenant_evaluation exact shape (ordered columns).
R3-TI-A06  pg_constraint: fk_current_business_impacts_latest_evaluation_id absent.
R3-TI-A07  Current-pointer upsert lifecycle (insert-then-update) still functions correctly post-migration.

Boundary B — CurrentReliance
R3-TI-B01  Same-tenant direct persistence accepted.
R3-TI-B02  Cross-tenant direct persistence REJECTED by PostgreSQL with genuine IntegrityError.
R3-TI-B03  Governed service path (evaluate_reliance_for_subject) same-tenant succeeds.
R3-TI-B04  pg_constraint: uq_oqi_reliance_evaluations_tenant_pk exact.
R3-TI-B05  pg_constraint: fk_current_reliance_tenant_evaluation exact shape (ordered columns).
R3-TI-B06  pg_constraint: fk_current_reliance_latest_evaluation_id absent.
R3-TI-B07  Current-pointer upsert lifecycle still functions correctly post-migration.

Migration
R3-TI-M01  Upgrade 0042 -> 0043 succeeds; table count 123 -> 123.
R3-TI-M02  Downgrade 0043 -> 0042 restores both old weak FKs exactly; both new parent keys absent.
R3-TI-M03  Round trip 0042 -> 0043 -> 0042 -> 0043 preserves valid same-tenant Current*/evaluation data
           byte-unchanged throughout.
R3-TI-M04  Invalid legacy CurrentBusinessImpact pointer (seeded pre-0043) causes the 0043 upgrade to fail
           with genuine IntegrityError.
R3-TI-M05  After that failure, alembic_version remains 0042 and the invalid row is byte-unchanged.
R3-TI-M06  After explicit test cleanup, retry upgrade succeeds, reaching current repository head
           (resolved dynamically via ScriptDirectory, per R2's own GA1 precedent -- never a hardcoded
           "0043" literal for the "current head" assertion).
R3-TI-M07  Invalid legacy CurrentReliance pointer (seeded pre-0043) causes the 0043 upgrade to fail with
           genuine IntegrityError.
R3-TI-M08  After that failure, alembic_version remains 0042 and the invalid row is byte-unchanged.
R3-TI-M09  After explicit test cleanup, retry upgrade succeeds, reaching current repository head
           (dynamic resolution, same as M06).

Regression
R3-TI-R01  R1 BusinessDependency->BusinessProcess: cross-tenant rejected, same-tenant accepted, unchanged.
R3-TI-R02  R2 BusinessImpactEvaluation->BusinessDependency: cross-tenant rejected, same-tenant accepted,
           unchanged.
R3-TI-R03  Explicit demonstration that two tenants' identical logical evaluation inputs produce distinct,
           non-colliding evaluation_id values (tenant-aware UUID5 identity), while a direct-persistence
           cross-tenant Current* pointer using a real, existing foreign evaluation_id is still rejected --
           proving identity distinctness is not the DB authority mechanism.
R3-TI-R04  H5 Timeliness crown unaffected (reuse test_oqi_h5_timeliness_crown.py's own seeding helpers).
R3-TI-R05  OQI6 BusinessImpact/Reliance crown/domain tests pass unmodified.
R3-TI-R06  Demo seeder remains idempotent/deterministic.
```

## 27. Proof standard (binding, restated)

Mocks do not count. SQLite does not count. A service-layer exception alone does not count as structural
proof. The required negative result for every rejection case is a genuine `sqlalchemy.exc.IntegrityError`
originating from real PostgreSQL foreign-key enforcement, confirmed via `pg_constraint`/
`pg_get_constraintdef` introspection of the exact constraint name, child columns, and parent columns.

## 28. Docker verification contract (binding, mandatory)

Fresh `docker compose build --no-cache`, genuinely fresh compose project/database. Inside the fresh
runtime, against real PostgreSQL, prove: Alembic head = `0043_oqi6_r3_current_tenancy`; table count = 123;
both new parent keys present; both new tenant-qualified FKs present with exact shape; both old weak FKs
absent; Boundary A/B same-tenant accepted, cross-tenant rejected; R1's and R2's own constraints remain
present and functional; H5 Timeliness regression passes; OQI6 BusinessImpact/Reliance regression passes;
backend/frontend health. Host-only proof is insufficient.

## 29. Regression contract (binding)

R3-I and R3-VM must run: the focused R3-TI matrix; the full existing `test_oqi_business_impact.py` suite
(R1's and R2's own TI matrices, crowns, migration round-trip); H5 Timeliness crown; the full backend test
suite (`pytest app/tests`); `black --check`, `isort --check-only`, `ruff check`, whole-package `mypy app`;
frontend `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run build`; fresh `--no-cache` Docker
verification per §28; CI exact-head verification before any merge.

```
FORMATTER-ONLY ≠ AUTOMATICALLY AUTHORIZED
```
Restated from R2's own GA2 correction: any formatter-produced change outside this document's exact §30
authorization requires its own explicit governance reconciliation before implementation may rely on it.

## 30. Exact new-path authorization (binding — a maximum permitted write set)

```
CREATE = 1
MODIFY = 2
DELETE = 0
TOTAL  = 3
```
```
CREATE  backend/app/infrastructure/persistence/migrations/versions/0043_oqi6_r3_current_tenancy.py
        Migration implementing §14/§15 exactly. No other schema/table/column change.

MODIFY  backend/app/infrastructure/persistence/models/oqi_business_impact.py
        Exactly the four edits authorized in §18. No other class in this file changes shape.

MODIFY  backend/app/tests/test_oqi_business_impact.py
        Append the R3-TI-A01 through R3-TI-R06 matrix (§26) as new top-level test functions, matching this
        file's own established flat-function style, using raw parameterized SQL per §25. No existing test
        function, fixture, or assertion in this file is modified.
```
Independently confirmed clean before freezing: zero references anywhere to either old constraint name
outside migration `0026` (historical, unmodified) and the one model file authorized above; zero collision
with either new constraint name; migration-head assertions across the suite resolve dynamically
(`ScriptDirectory.get_current_head()`), none hardcodes a revision-name list; `AUTHORIZED_CHANGED_PATHS`
requires no modification (governs uncommitted working-tree state only). No path beyond the three above is
authorized.

## 31. Forbidden implementation paths (binding, exhaustive)

OQI4 persistence/model files (including `CurrentOntologyImpactORM`); OQI5 implementation; H5 implementation;
API; frontend; service semantics beyond the zero change in §19; production orchestration; agent framework;
Docker/compose files; unrelated migrations; `architecture/INDEX.md` (independently reconfirmed untouched by
any OQI H1-R3 phase, same precedent applies); any of CDD-044, CDD-050, CDD-051, CDD-052, CDD-053, or their
own frozen Artifact Authorizations. No DELETE. No opportunistic cleanup. No refactoring.

## 32. R3-I STOP conditions (binding, exhaustive)

```
 1. authoritative main moves materially.
 2. this document's own governance hash drifts before implementation begins.
 3. any file outside the exact three §30 paths requires a write.
 4. the migration requires a new column, a new table, or a change to any other constraint.
 5. either evaluation table's PRIMARY KEY(evaluation_id) requires any change.
 6. either evaluation table unexpectedly has version semantics discovered.
 7. the child tenant columns/order differ from §9/§11.
 8. a naming collision is discovered against any new constraint name.
 9. domain/service/API/frontend semantics require any change.
10. R1's or R2's own constraints require any modification.
11. H5 Timeliness requires any change.
12. OQI4's CurrentOntologyImpact boundary requires any modification here.
13. OQI4/OQI5 orchestration requires any modification.
14. any existing legacy data is found to violate a new FK and no governed remediation exists -- migration
    must fail closed, not silently repair.
15. either same-tenant positive-control path is rejected post-correction.
16. either cross-tenant attack is still ACCEPTED post-correction.
17. any H1-H5/OQI6 crown/regression value changes semantically.
18. whole-package mypy, black, isort, or ruff fails as a result of this correction (including any
    formatter-only hunk not already exactly authorized by §30 -- return to governance rather than
    self-authorize, per R2's own GA2 precedent).
19. full clean-candidate regression fails as a result of this correction.
20. Docker proof differs materially from host proof.
21. migration chain becomes non-linear or produces a second head.
22. any DELETE is required.
23. CDD-044, CDD-050, CDD-051, CDD-052, CDD-053, or their own frozen Artifact Authorizations require any
    modification.
24. any P0 appears, or any material P1 remains unresolved outside the exact frozen correction.
```

## 33. VM/merge gate (binding, restated)

OQI6-R3-VM must independently re-derive — not merely trust I's report — every item in §32's proof surface
plus: exact ancestry; governance hash; exact diff; migration chain/round trip/fail-closed proof (both
boundaries); R1 preservation; R2 preservation; H5 preservation; OQI6 regression; full backend/static/
frontend regression; fresh `--no-cache` Docker proof; CI exact-head status; confirmation that the OQI4
`CurrentOntologyImpact` boundary remains explicitly deferred, not silently solved. Merge requires `P0 = 0`
and `P1 = 0`. Merge must bind to the exact approved candidate head; post-merge verification must repeat the
full structural and adversarial proof against post-merge main, including a second fresh `--no-cache` Docker
build.

## 34. Allowed claim

```
OQI6 CurrentBusinessImpact and CurrentReliance pointers can no longer reference evaluation rows
belonging to another tenant at the PostgreSQL structural layer.
```

## 35. Forbidden claims

```
"OQI is fully tenant-isolated."
"All Current* pointer tenant-isolation defects are fixed."
"OQI4 CurrentOntologyImpact is fixed."
"All OQI6 tenant boundaries are globally proven safe beyond the audited scope."
"Production orchestration is complete."
"Tenant-aware UUID generation provides database authorization."
"R3 completes all OQI hardening."
```

## 36. Severity status

```
Before this document: P0 = 0, P1 = 2 (two live, independently re-reproduced PostgreSQL structural
                       tenant-isolation gaps; both classified P1, not P0, for the same reasons as R1/R2 --
                       implicit service-layer construction prevents any current production code path from
                       exploiting either, and zero rows anywhere currently exploit them), P2 = 1 (OQI4
                       CurrentOntologyImpact analog, disclosed, deferred, not blocking)
After this document:  P0 = 0, P1 = 0, P2 = 1 (OQI4 analog remains open and explicitly tracked, not solved),
                       P3 = 0 (pending the three-path correction §30 authorizes and its own fresh
                       whole-package static / real-PostgreSQL adversarial / Docker / full regression
                       re-verification, per §26's frozen matrix)
```

## 37. Implementation phasing

```
OQI6-R3-G  (this document)
  -> OQI6-R3-I   (single implementation phase -- no split; both boundaries share one migration and one
                   ORM file, and no genuine architectural boundary separates them)
  -> OQI6-R3-VM  (adversarial verify + merge, restarting fully against the new candidate)
```

## 38. Governance byte-integrity

This document and its own content are the sole new governance artifact this phase publishes. `CDD-044`,
`CDD-050`, `CDD-051`, `CDD-052`, `CDD-053`, and their respective Artifact Authorizations/amendments are
independently re-hashed immediately before this document's own publication and confirmed byte-identical to
their prior published values; none is modified by this correction.

## 39. Authorization

This document is approved and published as a standalone governance artifact, following the established
precedent of `CDD-052` and `CDD-053`. Implementation against §30's exact three-path authorization may
proceed under `OQI6-R3-I`.
