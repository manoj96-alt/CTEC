# CDD-055 — OQI4-R1 CurrentOntologyImpact Pointer Tenant-Isolation Correction (OQI4-R1)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-052-Artifact-Authorization-OQI6-R1-Business-Dependency-Tenant-Isolation-Correction.md`,
`CDD-053-Artifact-Authorization-OQI6-R2-Business-Impact-Evaluation-Dependency-Tenant-Isolation-Correction.md`,
and `CDD-054-OQI6-R3-Current-Pointer-Tenant-Isolation-Correction.md` (the exact governance shape, root-cause
framing, and additive-then-replacing correction reasoning this document reuses); `CDD-050-Artifact-
Authorization-H4-R1-Reference-Tenant-Isolation-Correction-Amendment.md` (original precedent establishing the
weak-FK replacement pattern)
Governs: base architecture `CDD-042-Ontology-Quality-Intelligence-Ontology-Impact-Intelligence.md`
(frozen, NOT reopened, NOT modified by this document); `main` authoritative state
`4230add2c2d4099ebfedb818f42338e1785e9943` (OQI6-R3-VM's independently verified merge commit, independently
re-confirmed unchanged as of this document's own publication)
Classification: DATABASE-LEVEL STRUCTURAL TENANT-ISOLATION GAP (constraint-only correction; no schema
topology change, no table addition, no column addition, no domain/service/API/frontend semantic change)

## 1. Purpose

Authorizes the exact, narrow, additive-then-replacing correction of one genuine database-level tenant-
isolation defect — `current_ontology_impacts → ontology_impact_evaluations` (OQI4) — independently discovered
and reproduced by OQI4-R1-DR, independently re-reproduced by this governance phase, and explicitly disclosed
and deferred throughout the R1/R2/R3 OQI6 lineage (most recently CDD-054's own §22 deferral). **CDD-042,
CDD-044, CDD-050, CDD-051, CDD-052, CDD-053, and CDD-054 are not modified, not reopened, and remain FROZEN
exactly as originally published** — this document is a new, standalone governance artifact.

## 2. Authoritative baseline — independently re-derived

`origin/main` and GitHub `main` both equal `4230add2c2d4099ebfedb818f42338e1785e9943`, unchanged since
OQI4-R1-DR. PR #189 independently reconfirmed `MERGED`. R1's `uq_oqi_business_processes_tenant_pk`/
`fk_oqi_business_dependencies_tenant_process`, R2's `uq_oqi_business_dependencies_tenant_pk`/
`fk_oqi_business_impact_evaluations_tenant_dependency`, and R3's `uq_oqi_business_impact_evaluations_tenant_pk`/
`fk_current_business_impacts_tenant_evaluation`/`uq_oqi_reliance_evaluations_tenant_pk`/
`fk_current_reliance_tenant_evaluation` all independently reconfirmed live, unmodified, functional. Migration
head still `0043_oqi6_r3_current_tenancy`, single head, 123 tables.

## 3. Defect re-reproduction (binding evidence)

Independently re-reproduced live, in a fresh isolated PostgreSQL database (dropped after use):
```
SAME TENANT  (CurrentOntologyImpact Tenant A -> OntologyImpactEvaluation Tenant A): ACCEPTED, COMMITTED
CROSS TENANT (CurrentOntologyImpact Tenant A -> OntologyImpactEvaluation Tenant B): ACCEPTED, COMMITTED
```
The cross-tenant row was independently re-queried after commit to confirm genuine persistence, not a
transient or rolled-back statement. Both service/API/repository/ORM-construction paths were bypassed via raw
parameterized SQL.

## 4. Frozen OQI4-R1 architectural invariant (binding)

```
A CurrentOntologyImpact row owned by Tenant A must be structurally incapable of referencing an
OntologyImpactEvaluation row owned by Tenant B, even when service, repository, ORM-construction, and
API validation are bypassed.
```
Applies exactly to `CurrentOntologyImpact → OntologyImpactEvaluation`. Not extended to any other dimension,
including the newly observed OQI2/OQI3 adjacent patterns (§29/§30).

## 5. Identity/authority principle (binding, restated)

```
GLOBAL ROW IDENTITY ≠ TENANT AUTHORITY
TENANT-AWARE DETERMINISTIC UUID GENERATION ≠ DATABASE TENANT ENFORCEMENT
SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT
```
Both `derive_ontology_impact_evaluation_id` and `derive_current_ontology_impact_id` independently reconfirmed
to embed `tenant_id` as UUID5 material — an identity-derivation convention, not a substitute for structural
database enforcement, exactly as R2/R3 established. `OqiOntologyImpactEvaluationService.evaluate_current_state`
independently reconfirmed to always thread one internally-consistent `tenant_id` through its own call,
proving the service path safe by construction — this proves nothing about the database's own independent
enforcement, confirmed unsafe by §3.

## 6. Re-verified exact schema

```
OntologyImpactEvaluationORM (table ontology_impact_evaluations): PRIMARY KEY(evaluation_id); tenant_id
    present; NO version column; NO UNIQUE(tenant_id, evaluation_id) (only
    uq_ontology_impact_evaluations_natural_key = UNIQUE(tenant_id, finding_family, finding_id,
    finding_state_revision, traversed_state_digest), which does not include evaluation_id).
CurrentOntologyImpactORM (table current_ontology_impacts): PRIMARY KEY(current_impact_id) (synthetic,
    not composite); tenant_id present; latest_evaluation_id NOT NULL; weak FK
    "fk_current_ontology_impacts_latest_evaluation_id" -> ontology_impact_evaluations(evaluation_id).
```
Independently reconfirmed via `pg_constraint` against a freshly-migrated head-`0043` database — byte-for-byte
matching DR, zero ORM/schema disagreement, exact weak-FK name confirmed live (not inferred from source).

## 7. Non-versioned key semantics (binding)

`ontology_impact_evaluations` has no version column. The parent authority key is exactly `(tenant_id,
evaluation_id)` — **two columns**, matching R3's own non-versioned shape, not R1/R2's `(tenant_id, id,
version)` three-column shape. No synthetic version column is introduced. `CurrentOntologyImpactORM`'s own
primary key (`current_impact_id` alone, not composite) is independently confirmed **irrelevant** to the
required child FK shape — the child FK is defined by the child's own `tenant_id` + `latest_evaluation_id`
columns referencing the parent's tenant-qualified candidate key, regardless of the child's own PK shape.

## 8. Frozen parent candidate key

```
UNIQUE (tenant_id, evaluation_id)
name: uq_ontology_impact_evaluations_tenant_pk
on: ontology_impact_evaluations
```
Additive to the existing `PRIMARY KEY(evaluation_id)`, which remains unchanged. Safe by construction (no
backfill needed — `evaluation_id` is already globally unique, so `(tenant_id, evaluation_id)` is trivially
unique as a superset). 40 characters, independently re-verified against the PostgreSQL 63-byte identifier
limit. No naming collision found anywhere in the repository.

## 9. Frozen child FK

```
FOREIGN KEY (tenant_id, latest_evaluation_id)
REFERENCES ontology_impact_evaluations (tenant_id, evaluation_id)
name: fk_current_ontology_impacts_tenant_evaluation
on: current_ontology_impacts
```
Replaces `fk_current_ontology_impacts_latest_evaluation_id` (confirmed live, exact name). 45 characters,
independently re-verified against the 63-byte limit. No naming collision found anywhere in the repository.

## 10. Corrected additive-vs-replacement reasoning (binding, carried forward from R1/R2/R3)

PostgreSQL enforces every foreign key on a table conjunctively. Retaining both the weak FK and a correctly-
enforced tenant-qualified FK would **already** structurally prevent cross-tenant references — replacement is
**not** required because coexistence would somehow permit a bypass. **OPTION B (REPLACE) is selected** for
these precise, technically correct reasons:

1. the tenant-qualified FK fully subsumes the weak FK's referential-integrity purpose (its parent target is
   a superset key over the same primary-key column);
2. the weak FK becomes strictly redundant once the new one is added;
3. retaining a redundant, weaker FK creates two overlapping statements of the same authority boundary;
4. migrations `0038`, `0041`, `0042`, and `0043` (H4-R1, R1, R2, R3) already established the repository's own
   precedent of replacing, not retaining, a tenant-unqualified FK once a tenant-qualified equivalent exists;
5. exactly one FK should express the true authority boundary for a given child-parent relationship.

Option A (retain weak FK, add strong FK alongside) was evaluated and rejected as structurally sufficient but
needlessly redundant, for the identical reasons R1/R2/R3 rejected it.

## 11. Exact migration revision

```
revision:       0044_oqi4_r1_current_tenancy      (28 characters; independently re-verified against the
                                                     live alembic_version.version_num VARCHAR(32) column
                                                     width before freezing)
down_revision:  0043_oqi6_r3_current_tenancy
filename:       backend/app/infrastructure/persistence/migrations/versions/0044_oqi4_r1_current_tenancy.py
```
Independently re-confirmed: current head still `0043_oqi6_r3_current_tenancy`; single linear head; no naming
collision.

## 12. Frozen upgrade order (binding)

```
op.create_unique_constraint(
    "uq_ontology_impact_evaluations_tenant_pk",
    "ontology_impact_evaluations",
    ["tenant_id", "evaluation_id"],
)
op.drop_constraint(
    "fk_current_ontology_impacts_latest_evaluation_id",
    "current_ontology_impacts",
    type_="foreignkey",
)
op.create_foreign_key(
    "fk_current_ontology_impacts_tenant_evaluation",
    "current_ontology_impacts",
    "ontology_impact_evaluations",
    ["tenant_id", "latest_evaluation_id"],
    ["tenant_id", "evaluation_id"],
)
```
No data UPDATE/DELETE. No table/column change. No change to any R1/R2/R3/H4/H5 constraint.

## 13. Frozen downgrade order (binding)

```
op.drop_constraint(
    "fk_current_ontology_impacts_tenant_evaluation", "current_ontology_impacts", type_="foreignkey"
)
op.create_foreign_key(
    "fk_current_ontology_impacts_latest_evaluation_id", "current_ontology_impacts",
    "ontology_impact_evaluations", ["latest_evaluation_id"], ["evaluation_id"],
)
op.drop_constraint(
    "uq_ontology_impact_evaluations_tenant_pk", "ontology_impact_evaluations", type_="unique"
)
```
The new tenant-qualified FK is dropped before its candidate key — no live FK ever depends on a key already
dropped. Downgrade restores the exact pre-R1 schema.

## 14. Table-count invariant

Constraint-only correction. Governed table count remains **123** before and after. Independently
re-confirmed live.

## 15. Fail-closed legacy-data policy (binding)

```
INVALID LEGACY CROSS-TENANT CURRENT POINTER
        -> POSTGRESQL FK VALIDATION FAILS
        -> MIGRATION TRANSACTION ABORTS
        -> ALEMBIC HEAD DOES NOT ADVANCE (remains 0043_oqi6_r3_current_tenancy)
        -> INVALID ROW REMAINS BYTE-UNCHANGED
        -> NO SILENT REPAIR
```
No persistent shared/production database exists in this repository's workflow to check for genuine
pre-existing legacy invalid data (every phase in this lineage, including this one, uses ephemeral scratch/
Docker databases); the diagnostic join query itself is independently proven correct (it returned exactly the
single row deliberately injected for the §3 reproduction, dropped with its scratch database). No row-level
UPDATE/DELETE/reassignment/quarantine is authorized in the migration regardless of what a real deployment
target contains; any actual invalid legacy data requires separately governed remediation before the migration
may proceed there.

## 16. ORM authorization (binding)

`backend/app/infrastructure/persistence/models/oqi_ontology_impact_evaluation.py` — exactly two semantic
edits:

1. `OntologyImpactEvaluationORM.__table_args__` — add `UniqueConstraint("tenant_id", "evaluation_id",
   name="uq_ontology_impact_evaluations_tenant_pk")`.
2. `CurrentOntologyImpactORM.__table_args__` — replace the existing `ForeignKeyConstraint(["latest_
   evaluation_id"], ["ontology_impact_evaluations.evaluation_id"], name="fk_current_ontology_impacts_
   latest_evaluation_id")` with `ForeignKeyConstraint(["tenant_id", "latest_evaluation_id"],
   ["ontology_impact_evaluations.tenant_id", "ontology_impact_evaluations.evaluation_id"],
   name="fk_current_ontology_impacts_tenant_evaluation")`.

No column addition, deletion, nullability, or type change. No PK redesign (both `evaluation_id` and
`current_impact_id` primary keys remain exactly as they are). No version field. No other class in this file
(`OntologyImpactObservationORM`, `OntologyImpactPathORM`) changes shape.

## 17. Domain/service/repository preservation (binding)

```
OntologyImpactEvaluation / CurrentOntologyImpact / OntologyImpactObservation / OntologyImpactPath
    domain models: UNCHANGED
OqiOntologyImpactEvaluationService.evaluate_current_state: UNCHANGED
OqiOntologyImpactEvaluationRepositoryImpl: UNCHANGED
API / Frontend: UNCHANGED
```
The existing implicit-by-construction service safety (the service always derives `latest_evaluation_id` from
the same call's own tenant-scoped evaluation) remains as defense-in-depth, not removed.

## 18. CurrentOntologyImpact lifecycle preservation (binding)

```
Current-row natural identity remains exactly: tenant_id, finding_family, finding_id, ontology_element_type,
    ontology_element_id, impact_kind (uq_current_ontology_impacts_natural_key, unchanged).
CurrentOntologyImpact remains an authoritative projection (oqi_business_impact_evaluations.
    considered_current_impact_id continues to FK directly into it), not merely a cache.
OntologyImpactEvaluation rows remain immutable/append-only; no UPDATE/DELETE path is introduced.
Reevaluation remains: new immutable OntologyImpactEvaluation -> move CurrentOntologyImpact.
    latest_evaluation_id.
latest_evaluation_id remains NOT NULL.
Evaluation insert + CurrentOntologyImpact upsert remain in the existing single transaction/session boundary.
    No new transaction manager, outbox, eventing, asynchronous update, scheduler, or orchestration.
```
No semantic lifecycle change is authorized.

## 19. R1/R2/R3 preservation

`fk_oqi_business_dependencies_tenant_process`, `uq_oqi_business_processes_tenant_pk` (R1);
`fk_oqi_business_impact_evaluations_tenant_dependency`, `uq_oqi_business_dependencies_tenant_pk` (R2);
`fk_current_business_impacts_tenant_evaluation`, `uq_oqi_business_impact_evaluations_tenant_pk`,
`fk_current_reliance_tenant_evaluation`, `uq_oqi_reliance_evaluations_tenant_pk` (R3) are read-only inputs —
none touched nor altered. Independently reconfirmed live, unmodified. This matters specifically because
`oqi_business_impact_evaluations.considered_current_impact_id` FKs directly into `current_ontology_impacts` —
the one point where OQI6 and OQI4's Current* tables intersect — and must be independently reconfirmed
unaffected.

## 20. OQI2 deferral (binding, explicit)

```
OQI2 QUALITYCOMPARISONFINDING.LATEST_EVALUATION_ID TENANT-ISOLATION CORRECTION
DEFERRED — SEPARATE FUTURE GOVERNED CORRECTION
```
OQI4-R1-DR independently discovered `quality_comparison_findings.latest_evaluation_id ->
quality_comparison_evaluations(evaluation_id)` (OQI2) carries the identical structural defect class. It is a
**different, already-frozen dimension**, out of OQI4-R1's scope. This document does not modify
`QualityComparisonFindingORM`, `quality_comparison_evaluations`, any OQI2 migration, or any OQI2 test.

## 21. OQI3 deferral (binding, explicit)

```
OQI3 BUSINESSRULEFINDING.LATEST_EVALUATION_ID TENANT-ISOLATION CORRECTION
DEFERRED — SEPARATE FUTURE GOVERNED CORRECTION
```
OQI4-R1-DR independently discovered `business_rule_findings.latest_evaluation_id ->
business_rule_evaluations(evaluation_id)` (OQI3) carries the identical structural defect class. It is a
**different, already-frozen dimension**, out of OQI4-R1's scope. This document does not modify
`BusinessRuleFindingORM`, `business_rule_evaluations`, any OQI3 migration, or any OQI3 test.

## 22. Production-orchestration deferral (binding, restated)

```
OQI4/OQI6/OQI5 PRODUCTION ORCHESTRATION
DEFERRED — NOT AUTHORIZED BY OQI4-R1
```
No scheduler, worker, event bus, CDC, or new production caller is authorized or required. OQI4-R1 alone does
not authorize Production Orchestration to begin — the OQI2/OQI3 readiness question (§20/§21) must be
separately resolved first.

## 23. Authority firewall (binding)

No R1 implementation may alter: recommendation/authorization separation; remediation/resolution separation;
human or agent authority; OQI5 remediation semantics; the Reliance three-state model; H5 Timeliness
semantics; `FindingFamily`; `FindingStorageFamily`; business-criticality semantics. This is a database
tenant-authority correction only.

## 24. Frozen test-implementation strategy

Expected file: `backend/app/tests/test_oqi_ontology_impact_postgres.py` (unchanged from the DR conclusion).
Independently reconfirmed: the single-construction-site firewall (`test_runtime_architecture.py` lines
1461–1472) governs both `OntologyImpactEvaluationORM` and `CurrentOntologyImpactORM` identically to how it
governed R1's/R2's/R3's own target classes. Therefore the permanent structural-bypass tests must use **raw
parameterized SQL**, never direct ORM construction of either class, to avoid requiring an unauthorized
implementation path. Legitimate evaluation rows may still be seeded through the governed service
(`OqiOntologyImpactEvaluationService.evaluate_current_state`) where that does not require constructing a
forbidden class directly; the adversarial Current*-pointer insert itself must be raw SQL. Test names must
accurately describe the mechanism (`direct_persistence`, not `direct_orm`), per R2's own GA2 correction.

## 25. Frozen permanent OQI4-R1-TI test matrix (binding)

```
OQI4-R1-TI-01  Same-tenant direct persistence accepted.
OQI4-R1-TI-02  Cross-tenant direct persistence REJECTED by PostgreSQL with genuine
               sqlalchemy.exc.IntegrityError / ForeignKeyViolation on
               fk_current_ontology_impacts_tenant_evaluation.
OQI4-R1-TI-03  pg_constraint: uq_ontology_impact_evaluations_tenant_pk exact (columns, table).
OQI4-R1-TI-04  pg_constraint: fk_current_ontology_impacts_tenant_evaluation exact shape (ordered source and
               target columns).
OQI4-R1-TI-05  pg_constraint: fk_current_ontology_impacts_latest_evaluation_id absent after upgrade.
OQI4-R1-TI-06  Normal production service path (evaluate_current_state) still succeeds, including both the
               IMPACTED direct-impact and IMPACTED propagated-impact branches.
OQI4-R1-TI-07  Reevaluation of the same natural key inserts a new immutable OntologyImpactEvaluation and
               moves CurrentOntologyImpact.latest_evaluation_id forward; current-pointer lifecycle
               (insert-then-update) still functions correctly post-migration.
OQI4-R1-TI-08  Explicit demonstration that two tenants' identical logical evaluation inputs produce distinct,
               non-colliding evaluation_id/current_impact_id values (tenant-aware UUID5 identity), while a
               direct-persistence cross-tenant Current* pointer using a real, existing foreign evaluation_id
               is still rejected -- proving identity distinctness is not the DB authority mechanism.
OQI4-R1-TI-09  Migration downgrade (0044 -> 0043) restores the exact pre-R1 schema: old weak FK restored
               exactly, new parent key and new FK both absent.
OQI4-R1-TI-10  Upgrade after downgrade (0043 -> 0044) restores the protected schema; table count 123 -> 123
               throughout the round trip.
OQI4-R1-TI-11  Invalid legacy cross-tenant CurrentOntologyImpact pointer (seeded pre-0044) causes the 0044
               upgrade to fail with genuine IntegrityError.
OQI4-R1-TI-12  After that failure, alembic_version remains 0043_oqi6_r3_current_tenancy and the invalid row
               is byte-unchanged.
OQI4-R1-TI-13  (folded into TI-12's own assertion set per this file's established one-test-per-scenario
               style -- row-unchanged and head-unchanged are proven together, mirroring R3-TI-M04/M05's own
               combined structure.)
OQI4-R1-TI-14  After explicit test cleanup, retry upgrade succeeds, reaching the repository's **current**
               head. This assertion MUST resolve the expected head dynamically via
               ScriptDirectory.from_config(config).get_current_head() -- never a hardcoded "0044" literal --
               per the R2-GA1/R3-GA precedent this document explicitly carries forward. Any assertion in this
               same test that specifically proves the pre-upgrade historical state (i.e. that the failed
               attempt left head at 0043) remains an explicit pinned literal "0043_oqi6_r3_current_tenancy" --
               historical targets are never resolved dynamically.

Regression
OQI4-R1-TI-15  R1 BusinessDependency->BusinessProcess: cross-tenant rejected, same-tenant accepted, unchanged.
OQI4-R1-TI-16  R2 BusinessImpactEvaluation->BusinessDependency: cross-tenant rejected, same-tenant accepted,
               unchanged.
OQI4-R1-TI-17  R3 CurrentBusinessImpact/CurrentReliance: cross-tenant rejected, same-tenant accepted,
               unchanged.
OQI4-R1-TI-18  H5 Timeliness crown unaffected.
OQI4-R1-TI-19  OQI6 BusinessImpact/Reliance crown/domain tests pass unmodified (including the
               considered_current_impact_id cross-reference into current_ontology_impacts).
OQI4-R1-TI-20  Demo seeder remains idempotent/deterministic.
```
```
CURRENT REPOSITORY HEAD -> dynamic Alembic metadata resolution
HISTORICAL MIGRATION TARGET -> explicit pinned literal
```
This distinction is frozen precisely to avoid repeating the R2/R3 migration-head regression a fourth time.

## 26. Proof standard (binding, restated)

Mocks do not count. SQLite does not count. A service-layer exception alone does not count as structural
proof. The required negative result for every rejection case is a genuine `sqlalchemy.exc.IntegrityError`
originating from real PostgreSQL foreign-key enforcement, confirmed via `pg_constraint`/
`pg_get_constraintdef` introspection of the exact constraint name, child columns, and parent columns.

## 27. Docker verification contract (binding, mandatory)

Fresh `docker compose build --no-cache`, genuinely fresh compose project/database. Inside the fresh runtime,
against real PostgreSQL, prove: Alembic head = `0044_oqi4_r1_current_tenancy`; table count = 123; new parent
key present; new tenant-qualified FK present with exact shape; old weak FK absent; same-tenant accepted,
cross-tenant rejected by genuine PostgreSQL FK violation; R1's, R2's, and R3's own constraints remain present
and functional; H5 Timeliness regression passes; OQI6 BusinessImpact/Reliance crown passes; OQI4 crown
(`test_oqi_ontology_impact_postgres.py`) passes; backend `/health` = 200; frontend serving = 200. Host-only
proof is insufficient. The exact implementation candidate SHA must be independently bound to the Docker image
(structural file hashes read from inside the built image must match the frozen candidate hashes byte-for-
byte).

## 28. Host↔Docker equivalence contract (binding)

| Proof | Host | Fresh Docker |
|---|---|---|
| Alembic head | required | required |
| table count | required | required |
| parent tenant key | required | required |
| tenant FK | required | required |
| weak FK absent | required | required |
| same-tenant pointer | required | required |
| cross-tenant pointer | required | required |
| OQI4 crown | required | required |
| R1 | required | required |
| R2 | required | required |
| R3 | required | required |
| H5 | required | required |
| OQI6 | required | required |
| backend health | n/a | required |
| frontend serving | n/a | required |

No material disagreement between host and Docker is permitted.

## 29. Regression contract (binding)

OQI4-R1-I and OQI4-R1-VM must run: the focused OQI4-R1-TI matrix; the full existing
`test_oqi_ontology_impact_postgres.py` suite (direct-impact resolution, propagation graph semantics,
concurrent-evaluation convergence, tenant-scoped Finding lookup); the full existing
`test_oqi_business_impact.py` suite (R1's, R2's, and R3's own TI matrices, crowns); H5 Timeliness crown
(`test_oqi_h5_timeliness_crown.py`); the full backend test suite (`pytest app/tests`); `black --check`,
`isort --check-only`, `ruff check`, whole-package `mypy app`; frontend `npm test`, `npm run lint`, `npx tsc
--noEmit`, `npm run build`; fresh `--no-cache` Docker verification per §27; CI exact-head verification before
any merge.

```
FORMATTER-ONLY ≠ AUTOMATICALLY AUTHORIZED
```
Restated from R2's own GA2 correction: any formatter-produced change outside this document's exact §31
authorization requires its own explicit governance reconciliation before implementation may rely on it.

## 30. Adjacent-defect classification (restated, non-binding beyond deferral)

```
OQI2 QualityComparisonFindingORM.latest_evaluation_id  -> NEW ADJACENT OBSERVATION, DEFERRED (§20)
OQI3 BusinessRuleFindingORM.latest_evaluation_id        -> NEW ADJACENT OBSERVATION, DEFERRED (§21)
OQI6 R1/R2/R3 Current* pointers                         -> ALREADY PROTECTED, unaffected by this document
OQI1 QualityFindingORM                                  -> NO latest_*_id PATTERN FOUND, not applicable
```
Neither OQI2 nor OQI3 is fixed, expanded into, or otherwise touched by this document or by OQI4-R1
implementation.

## 31. Exact new-path authorization (binding — a maximum permitted write set)

```
CREATE = 1
MODIFY = 2
DELETE = 0
TOTAL  = 3
```
```
CREATE  backend/app/infrastructure/persistence/migrations/versions/0044_oqi4_r1_current_tenancy.py
        Migration implementing §12/§13 exactly. No other schema/table/column change.

MODIFY  backend/app/infrastructure/persistence/models/oqi_ontology_impact_evaluation.py
        Exactly the two edits authorized in §16. No other class in this file changes shape.

MODIFY  backend/app/tests/test_oqi_ontology_impact_postgres.py
        Append the OQI4-R1-TI-01 through OQI4-R1-TI-20 matrix (§25) as new top-level test functions,
        matching this file's own established style, using raw parameterized SQL per §24. No existing test
        function, fixture, or assertion in this file is modified.
```
Independently confirmed clean before freezing: zero references anywhere to either old constraint name outside
migration `0023` (historical, unmodified) and the one model file authorized above; zero collision with either
new constraint name; migration-head assertions elsewhere in the suite already resolve dynamically
(`ScriptDirectory.get_current_head()`), none hardcodes a revision-name list that this correction would
invalidate. No path beyond the three above is authorized.

## 32. Forbidden implementation paths (binding, exhaustive)

Service (`OqiOntologyImpactEvaluationService`); repository beyond the zero change in §17; domain models;
API; frontend; OQI2 persistence/model files (including `QualityComparisonFindingORM`); OQI3 persistence/model
files (including `BusinessRuleFindingORM`); OQI5 implementation; OQI6 persistence/model files; H5
implementation; production orchestration; agent framework; Docker/compose files; unrelated migrations;
`architecture/INDEX.md`; any of CDD-042, CDD-044, CDD-050, CDD-051, CDD-052, CDD-053, CDD-054, or their own
frozen Artifact Authorizations. No DELETE. No opportunistic cleanup. No refactoring.

## 33. OQI4-R1-I STOP conditions (binding, exhaustive)

```
 1. authoritative main moves materially.
 2. this document's own governance hash drifts before implementation begins.
 3. any file outside the exact three §31 paths requires a write.
 4. the migration requires a new column, a new table, or a change to any other constraint.
 5. OntologyImpactEvaluationORM's PRIMARY KEY(evaluation_id) requires any change.
 6. OntologyImpactEvaluationORM unexpectedly has version semantics discovered.
 7. CurrentOntologyImpactORM's own PRIMARY KEY(current_impact_id) is found to require any change.
 8. the child tenant columns/order differ from §9.
 9. a naming collision is discovered against either new constraint name.
10. domain/service/API/frontend semantics require any change.
11. R1's, R2's, or R3's own constraints require any modification.
12. H5 Timeliness requires any change.
13. OQI2's or OQI3's own adjacent defects require any modification here.
14. OQI4/OQI5/OQI6 orchestration requires any modification.
15. any existing legacy data is found to violate the new FK and no governed remediation exists -- migration
    must fail closed, not silently repair.
16. the same-tenant positive-control path is rejected post-correction.
17. the cross-tenant attack is still ACCEPTED post-correction.
18. any H1-H5/OQI6 crown/regression value changes semantically.
19. whole-package mypy, black, isort, or ruff fails as a result of this correction (including any
    formatter-only hunk not already exactly authorized by §31 -- return to governance rather than
    self-authorize, per R2's own GA2 precedent).
20. full clean-candidate regression fails as a result of this correction.
21. Docker proof differs materially from host proof.
22. migration chain becomes non-linear or produces a second head.
23. any DELETE is required.
24. CDD-042, CDD-044, CDD-050, CDD-051, CDD-052, CDD-053, CDD-054, or their own frozen Artifact
    Authorizations require any modification.
25. any P0 appears, or any material P1 remains unresolved outside the exact frozen correction.
```

## 34. VM/merge gate (binding, restated)

OQI4-R1-VM must independently re-derive — not merely trust I's report — every item in §33's proof surface
plus: exact ancestry; governance hash; exact diff; migration chain/round trip/fail-closed proof; R1/R2/R3
preservation; H5 preservation; OQI6 regression; full backend/static/frontend regression; fresh `--no-cache`
Docker proof; CI exact-head status; confirmation that the OQI2/OQI3 adjacent boundaries remain explicitly
deferred, not silently solved. Merge requires `P0 = 0` and `P1 = 0`. Merge must bind to the exact approved
candidate head; post-merge verification must repeat the full structural and adversarial proof against
post-merge main, including a second fresh `--no-cache` Docker build.

## 35. Allowed claim

```
OQI4 CurrentOntologyImpact pointers cannot reference OntologyImpactEvaluation rows belonging to another
tenant at the PostgreSQL structural layer.
```

## 36. Forbidden claims

```
"All OQI is tenant-isolated."
"All ontology persistence is tenant-isolated."
"All Current* pointers are structurally safe."
"OQI2 is tenant-isolated."
"OQI3 is tenant-isolated."
"Production Orchestration is complete."
"Production Orchestration is authorized."
"OQI hardening is complete."
"Tenant-aware UUID generation provides database authorization."
```

## 37. Severity status

```
Before this document: P0 = 0, P1 = 1 (one live, independently re-reproduced PostgreSQL structural
                       tenant-isolation gap; classified P1, not P0, for the same reasons as R1/R2/R3 --
                       implicit service-layer construction prevents any current production code path from
                       exploiting it, and zero rows anywhere currently exploit it), P2 = 2 (OQI2 and OQI3
                       adjacent analogs, disclosed, deferred, not blocking), P3 = 2 (inherited frontend
                       Docker healthcheck discrepancy; Reliance evaluation-history replay sensitivity --
                       both carried forward, untouched)
After this document:  P0 = 0, P1 = 0, P2 = 2 (OQI2/OQI3 analogs remain open and explicitly tracked, not
                       solved), P3 = 2 (unchanged, pending the three-path correction §31 authorizes and its
                       own fresh whole-package static / real-PostgreSQL adversarial / Docker / full
                       regression re-verification, per §25's frozen matrix)
```

## 38. Implementation phasing

```
OQI4-R1-G  (this document)
  -> OQI4-R1-I   (single implementation phase -- no split; one migration, one ORM file, one boundary)
  -> OQI4-R1-VM  (adversarial verify + merge, restarting fully against the new candidate)
```

## 39. Governance byte-integrity

This document and its own content are the sole new governance artifact this phase publishes. `CDD-042`,
`CDD-044`, `CDD-050`, `CDD-051`, `CDD-052`, `CDD-053`, `CDD-054`, and their respective Artifact
Authorizations/amendments are independently re-hashed immediately before this document's own publication and
confirmed byte-identical to their prior published values; none is modified by this correction.

## 40. Authorization

This document is approved and published as a standalone governance artifact, following the established
precedent of `CDD-052`, `CDD-053`, and `CDD-054`. Implementation against §31's exact three-path authorization
may proceed under `OQI4-R1-I`.
