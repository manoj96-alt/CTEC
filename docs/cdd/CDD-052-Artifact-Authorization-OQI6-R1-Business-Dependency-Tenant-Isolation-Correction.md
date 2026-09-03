# CDD-052 — Artifact Authorization OQI6-R1 Business Dependency Tenant-Isolation Correction (OQI6-R1)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-050-Artifact-Authorization-H4-R1-Reference-Tenant-Isolation-Correction-Amendment.md` (the
direct precedent for this exact defect class and this exact governance shape: a real-PostgreSQL adversarial
verification discovers a genuine tenant-isolation gap outside a prior phase's own scope, closed by a
narrow, standalone, additive-parent/replaced-child-FK correction); migration `0038_oqi_h4_reference_tenancy`
(the proven technical pattern this correction reuses verbatim: drop the old plain child FK, add a
tenant-qualified composite child FK against an already-existing tenant-qualified parent candidate key);
`CDD-051-OQI-H5-Governed-Timeliness.md` §9 (the origin of this correction's parent candidate key
`uq_oqi_business_processes_tenant_pk`, added by migration `0039`, and the explicit deferral of this exact
correction to "a future, separately-governed OQI6-R1")
Governs: base architecture `CDD-044-Ontology-Quality-Intelligence-Criticality-Business-Impact-Explainable-
Reliance.md` (frozen, NOT reopened, NOT modified by this document); `oqi-h5/timeliness-core` → `main`
authoritative state `a64983929c8f0964c52c5766dd80caa35ca2b126` (H5-VM's independently verified merge commit,
independently re-confirmed unchanged as of this document's own publication)
Classification: DATABASE-LEVEL STRUCTURAL TENANT-ISOLATION GAP (constraint-only correction; no schema
topology change, no table addition, no column addition, no domain/service/API/frontend semantic change)

## 1. Purpose

Authorizes the exact, narrow, additive-then-replacing correction of a genuine database-level tenant-
isolation defect in `oqi_business_dependencies`' foreign key to `oqi_business_processes`, independently
discovered and reproduced by OQI6-R1-DR against real PostgreSQL, and explicitly anticipated (and deferred)
by CDD-051 §9 at the time H5 added the missing parent-side candidate key. **CDD-044, CDD-050, and CDD-051
are not modified, not reopened, and remain FROZEN exactly as originally published** — this document is a
new, standalone, additive governance artifact.

## 2. Context — independently re-derived by this phase, not merely trusted from OQI6-R1-DR

Before drafting this freeze, this phase independently re-verified: `origin/main` and GitHub `main` both
equal `a64983929c8f0964c52c5766dd80caa35ca2b126`, unchanged since OQI6-R1-DR's own verification; the
migration head is still `0040_oqi_h5_timeliness_eval` (40 files); `oqi_business_processes` still carries
`PRIMARY KEY (process_id, version)` and `UNIQUE (tenant_id, process_id, version)` (constraint name
`uq_oqi_business_processes_tenant_pk`, live in `pg_constraint`); `oqi_business_dependencies` still carries
exactly one FK to `oqi_business_processes` — `fk_oqi_business_dependencies_process`, plain
`(business_process_id, business_process_version) → (process_id, version)`, not tenant-qualified. No
intervening commit since the H5-VM merge touches OQI6, OQI4, OQI5, migrations, or tenant isolation of any
kind.

## 3. Root-cause analysis (reaffirming OQI6-R1-DR)

`OqiBusinessDependencyORM` stores its own `tenant_id` column, but its database foreign key to
`OqiBusinessProcessORM` was authored (migration `0026`, CDD-044) against the only composite key that
existed at the time: the plain, globally-unique `(process_id, version)` primary key. That primary key
remains globally unique today — `process_id` is a UUID and the PK enforces global uniqueness independent of
tenant — so the plain FK is not ambiguous (it always resolves to exactly one row); it simply does not prove
that the resolved row belongs to the referencing row's own tenant. PostgreSQL therefore proves only
"referenced process exists," never "referenced process belongs to this dependency's tenant."

`OqiBusinessImpactService.create_dependency` already performs the correct tenant-scoped lookup
(`get_latest_business_process(tenant_id=..., process_id=...)`, which filters by both columns and raises
`ValidationException` on a miss) before constructing a dependency — the governed service path already
rejects cross-tenant creation end-to-end. That protection is bypassable by any direct persistence-layer
write (ORM/session insertion outside the service), independently reproduced in §4 below.

## 4. Live adversarial re-confirmation

Reproduced live against a freshly-migrated PostgreSQL database, direct `Session.add(OqiBusinessDependencyORM(...))`
bypassing the service layer entirely:

```
Tenant A BusinessDependency (tenant_id=A) -> business_process_id/version of a real Tenant B BusinessProcess
Result: ACCEPTED (commit succeeded, zero PostgreSQL rejection)
```

Same-tenant positive control (Tenant A dependency → Tenant A's own process): `ACCEPTED`, as required.
Cross-tenant `(process_id, version)` identity collision: `REJECTED` with `UniqueViolation` — confirming
`(process_id, version)` remains globally unique via the primary key regardless of tenant, so this defect is
an authorization-scope gap, not an identity-ambiguity gap.

## 5. Corrected technical clarification of OQI6-R1-DR's Option A/B reasoning (binding)

OQI6-R1-DR's own Option A/B analysis (§AA/§AB of its report) reasoned that an *additive* tenant-qualified
FK — added alongside the existing plain FK, without dropping it — would fail to close the gap, because "the
old FK would independently permit the unsafe row." **This is incorrect PostgreSQL constraint semantics and
is not carried forward.** PostgreSQL enforces every foreign key on a table conjunctively (`AND`, not `OR`):
a row must satisfy **all** declared FKs simultaneously to be accepted. An additively-added tenant-qualified
FK — `(tenant_id, business_process_id, business_process_version) → oqi_business_processes(tenant_id,
process_id, version)` — would, by itself, already reject the exact §4 cross-tenant attack even if the old
plain FK remained live, because the cross-tenant row could never satisfy the new FK's composite tuple match
regardless of what the old FK independently permits.

This document freezes the **actual, correct** reason to still drop the old FK rather than retain it
additively:

1. the new tenant-qualified FK **fully subsumes** the old FK's entire referential-integrity purpose (any
   row satisfying the new FK necessarily also identifies a genuinely-existing `(process_id, version)`, since
   the new FK's parent target `uq_oqi_business_processes_tenant_pk` is a superset key over the same primary
   key columns);
2. the old FK becomes strictly redundant once the new one is added;
3. retaining a redundant, weaker FK alongside a stronger one creates two overlapping, textually-inconsistent
   statements of the same authority boundary in the schema, inviting future confusion about which one is
   authoritative;
4. `migration 0038` (H4-R1) already established the repository's own precedent of **replacing**, not
   retaining, a tenant-unqualified FK once a tenant-qualified equivalent exists;
5. exactly one FK should express the true authority boundary for a given child-parent relationship.

**The selected correction architecture (§6) is unchanged by this clarification** — replacement remains
correct — but the governing rationale is now the one above, not OQI6-R1-DR's original (flawed) constraint-
interaction claim.

## 6. Selected correction architecture — REPLACE (drop old FK, add tenant-qualified composite FK)

```
DROP    fk_oqi_business_dependencies_process
        FOREIGN KEY (business_process_id, business_process_version)
        REFERENCES oqi_business_processes(process_id, version)

CREATE  fk_oqi_business_dependencies_tenant_process
        FOREIGN KEY (tenant_id, business_process_id, business_process_version)
        REFERENCES oqi_business_processes(tenant_id, process_id, version)
```

No parent-key migration is required: `uq_oqi_business_processes_tenant_pk` already exists (migration
`0039`), independently reconfirmed live in §2. `oqi_business_processes`' primary key
`(process_id, version)` is **not** touched, dropped, or altered by this correction — the defect is a tenant
**authority** gap, not an identity-ambiguity gap (§4), so the correction is scoped to the child FK alone.

## 7. Exact authority boundary (binding — scope statement)

This correction proves and enforces exactly:

```
A BusinessDependency row owned by Tenant A cannot reference a BusinessProcess owned by Tenant B
at the PostgreSQL structural layer, even when all service/API validation is bypassed.
```

It does **not** prove, and must not be represented as proving, that all of OQI6 is tenant-safe.

## 8. OQI6-R2 deferral (binding, explicit)

```
OqiBusinessImpactEvaluationORM -> OqiBusinessDependencyORM
tenant-qualified FK correction:
DEFERRED — FUTURE SEPARATELY GOVERNED OQI6-R2
```

`oqi_business_impact_evaluations`' own FK to `oqi_business_dependencies` (`fk_oqi_business_impact_evaluations_dependency`,
plain `(business_dependency_id, business_dependency_version) → (dependency_id, version)`) is the identical
defect class one hop downstream, independently confirmed still present and unmodified by OQI6-R1-DR and
reconfirmed here. It is a **separate authority boundary** (a different table pair) — correcting
`dependencies→processes` neither requires nor benefits from simultaneously correcting this boundary, and
`oqi_business_dependencies` itself has no tenant-qualified parent candidate key yet, making its own
correction a materially larger, independently-scoped design decision. R1 must not add such a key, must not
modify `OqiBusinessImpactEvaluationORM`, and must not claim to have closed this boundary.

## 9. Production-orchestration deferral (binding, explicit)

```
OQI4/OQI6/OQI5 production-orchestration trigger:
SEPARATE FUTURE GOVERNED INITIATIVE
```

Independently established by OQI-H5-VM (zero production callers repo-wide, for any dimension, of the OQI4
generic write path or the OQI5/OQI6 orchestration entrypoints). R1 is a database structural-integrity
correction only; it neither worsens nor claims to solve this separate, pre-existing characteristic.

## 10. Zero semantic/downstream change (binding)

```
Domain (BusinessDependency, BusinessProcess):     UNCHANGED
Application service (OqiBusinessImpactService):   UNCHANGED — existing tenant-scoped validation
                                                    (create_dependency's get_latest_business_process call)
                                                    remains as defense-in-depth; not removed merely because
                                                    the database becomes independently safe
Repository (OqiBusinessImpactRepositoryImpl):     UNCHANGED
API:                                               UNCHANGED
Frontend:                                          UNCHANGED
OQI4:                                              UNCHANGED
OQI5:                                              UNCHANGED
OQI6 Reliance semantics:                           UNCHANGED — structural integrity only, no evaluator
                                                    decision-table change
H5 Timeliness (TimelinessPolicy/Evaluation/Finding): UNCHANGED — `fk_oqi_timeliness_policies_tenant_
                                                    business_process` and `uq_oqi_business_processes_
                                                    tenant_pk` are read-only inputs to this correction,
                                                    neither touched nor altered
```

Both application-layer tenant validation and database-level structural enforcement remain in force
simultaneously (`SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT` — neither substitutes for the
other; both hold).

## 11. Existing-data / fail-closed migration policy (binding)

Independently reconfirmed: zero `oqi_business_dependencies` rows exist in the currently-inspected dev
(`ctec`) and test (`ctec_test`) databases. This does not guarantee every future deployment database is
empty. The migration's `upgrade()` must attempt the `DROP CONSTRAINT` / `CREATE CONSTRAINT ... FOREIGN KEY`
sequence directly (no data-scanning precondition query is required to be added, since PostgreSQL's own
`ADD CONSTRAINT ... FOREIGN KEY` validation will itself raise a genuine `IntegrityError` and abort the
migration transaction if any existing row would violate the new tenant-qualified FK). The migration must
**not** contain any row-level `UPDATE`/`DELETE` that would rewrite `tenant_id`, reassign a
`business_process_id`, or delete a violating row. If PostgreSQL's own constraint-creation raises, the
migration fails closed and existing data is left byte-unchanged (transactional DDL, matching every other
migration's established convention) — no separate governed remediation exists or is required at this time.

## 12. Table-count freeze (binding)

Constraint-only correction. Governed table count remains **123** before and after this migration. Migrations
`0001`-`0040` remain byte-for-byte unmodified.

## 13. Exact migration (binding)

```
revision:       0041_oqi6_r1_dependency_tenancy      (31 characters; independently verified against the
                                                        live `alembic_version.version_num VARCHAR(32)`
                                                        column width before freezing — not assumed, per the
                                                        H5 0040-revision-length lesson)
down_revision:  0040_oqi_h5_timeliness_eval
filename:       backend/app/infrastructure/persistence/migrations/versions/0041_oqi6_r1_business_dependency_tenancy.py

upgrade():
    op.drop_constraint(
        "fk_oqi_business_dependencies_process",
        "oqi_business_dependencies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_business_dependencies_tenant_process",
        "oqi_business_dependencies",
        "oqi_business_processes",
        ["tenant_id", "business_process_id", "business_process_version"],
        ["tenant_id", "process_id", "version"],
    )

downgrade():
    op.drop_constraint(
        "fk_oqi_business_dependencies_tenant_process",
        "oqi_business_dependencies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_business_dependencies_process",
        "oqi_business_dependencies",
        "oqi_business_processes",
        ["business_process_id", "business_process_version"],
        ["process_id", "version"],
    )
```

Downgrade does **not** touch `uq_oqi_business_processes_tenant_pk` — that constraint remains owned
exclusively by migration `0039`'s own downgrade, which runs strictly after this migration's downgrade in
any full downgrade walk (this migration's `down_revision` is `0040`, placing it later in the chain), so no
ordering conflict exists and H5's own parent key is never at risk of being dropped while this migration's FK
still depends on it.

## 14. Exact new-path authorization (binding — a maximum permitted write set, not a requirement to touch
every listed path beyond what correctness requires)

```
CREATE = 1
MODIFY = 2
DELETE = 0
TOTAL  = 3
```

```
CREATE  backend/app/infrastructure/persistence/migrations/versions/0041_oqi6_r1_business_dependency_tenancy.py
        Migration implementing §13 exactly. No other schema/table/column change.

MODIFY  backend/app/infrastructure/persistence/models/oqi_business_impact.py
        In `OqiBusinessDependencyORM.__table_args__`, replace ONLY the existing
        `ForeignKeyConstraint(["business_process_id", "business_process_version"], [...],
        name="fk_oqi_business_dependencies_process")` with the tenant-qualified declaration:
            ForeignKeyConstraint(
                ["tenant_id", "business_process_id", "business_process_version"],
                [
                    "oqi_business_processes.tenant_id",
                    "oqi_business_processes.process_id",
                    "oqi_business_processes.version",
                ],
                name="fk_oqi_business_dependencies_tenant_process",
            )
        No column addition, no column deletion, no nullability change, no type change, no other class in
        this file changes shape, no new table.

MODIFY  backend/app/tests/test_oqi_business_impact.py
        Add a focused, permanent tenant-isolation adversarial test section (TI-01 through TI-10, §17 below)
        as new top-level test functions, matching this file's own established flat-function style (this
        file has no test classes; H4-R1's own precedent of adding a `class TestR1...` inside a *dedicated*
        `..._authorization_and_tenant_isolation.py` file does not transfer literally, since OQI6 has no such
        dedicated file — `test_oqi_business_impact.py` is itself OQI6's one focused domain/crown/migration
        test file, already using real-PostgreSQL `migrated_engine`-backed fixtures for its own crown tests,
        making it the smallest correct location per repository convention). No existing test function,
        fixture, or assertion in this file is modified — independently confirmed the existing
        `test_migration_round_trips_94_100_94_100`'s two `== 123` assertions and `alembic.command.upgrade
        (config, "head")` call require no change, since table count is unaffected and head resolution is
        already dynamic.
```

Repository-wide compatibility search performed and independently confirmed clean before freezing this
authorization: zero references anywhere to the old constraint name `fk_oqi_business_dependencies_process`
outside migration `0026` (historical, unmodified) and the one model file authorized above; zero collision
with the new constraint name `fk_oqi_business_dependencies_tenant_process` anywhere in the repository; every
migration-head assertion across the test suite resolves dynamically via `ScriptDirectory.get_current_head()`
or `alembic.command.upgrade(config, "head")`, none hardcodes a revision-name list; `test_runtime_
architecture.py`'s `AUTHORIZED_CHANGED_PATHS` firewall governs *uncommitted working-tree* state relative to
`HEAD`, not merged/committed history, and therefore requires no modification for this correction (it will
be satisfied trivially once this phase's changes are committed, leaving no matching dirty-tree diff); no
file anywhere hardcodes a total OQI6/business-dependency migration count. No path beyond the three above is
authorized.

## 15. Frozen permanent tenant-isolation test matrix (binding — TI-01 through TI-10)

```
TI-01  Same-tenant dependency create succeeds (service path, create_dependency).
TI-02  Direct-ORM cross-tenant dependency insert (tenant A dep -> tenant B process) is REJECTED by
       PostgreSQL with a genuine sqlalchemy.exc.IntegrityError. (Service ValidationException alone does
       not satisfy this test -- must bypass the service layer entirely, per §16.)
TI-03  Direct-ORM same-tenant dependency insert (tenant A dep -> tenant A process) is ACCEPTED --
       positive control proving the correction does not regress legitimate data.
TI-04  Existing governed service path (create_dependency) still rejects a foreign-tenant
       business_process_id with ValidationException (defense-in-depth unchanged, §10).
TI-05  pg_constraint introspection: fk_oqi_business_dependencies_process does NOT exist after upgrade.
TI-06  pg_constraint introspection: fk_oqi_business_dependencies_tenant_process exists, with exact child
       columns (tenant_id, business_process_id, business_process_version) and exact parent columns
       (tenant_id, process_id, version) on oqi_business_processes.
TI-07  pg_constraint introspection: uq_oqi_business_processes_tenant_pk still exists, unmodified, after
       this migration (H5 parent-key preservation).
TI-08  H5 Timeliness same-tenant TimelinessPolicy creation (business_process_id/version anchor) still
       succeeds unaffected after this migration.
TI-09  Migration round trip: upgrade to 0041 -> downgrade to 0040 -> upgrade to 0041, table count constant
       at 123 throughout; fk_oqi_business_dependencies_process is restored exactly on downgrade and removed
       exactly on the second upgrade; uq_oqi_business_processes_tenant_pk present at every step.
TI-10  Fail-closed proof: on a pre-R1 schema (post-0040, pre-0041), deliberately insert a cross-tenant
       BusinessDependency row via direct ORM (reusing TI-02's construction, which succeeds pre-correction);
       attempt the 0041 upgrade against that data; upgrade must fail (PostgreSQL raises on
       ADD CONSTRAINT ... FOREIGN KEY validation) and the violating row must remain byte-unchanged; clean
       the row; re-attempt upgrade; it must then succeed.
```

## 16. Proof standard (binding, restated)

Mocks do not count. SQLite does not count. A service-layer `ValidationException` alone does not count as
structural proof. The required negative result for every rejection case above is a genuine
`sqlalchemy.exc.IntegrityError` originating from real PostgreSQL foreign-key enforcement, independently
confirmed via direct `pg_constraint`/`pg_get_constraintdef` introspection of the exact constraint name,
child columns, and parent columns — never a merely textual ORM-source assertion.

## 17. Root invariant (binding, restated for zero ambiguity)

```
TENANT A BUSINESS DEPENDENCY ROW
     |
     +-- tenant_id = A
     |
     +-- business_process_id/version = a process owned by Tenant B
                |
                v
           PostgreSQL
                |
                v
        FOREIGN KEY VIOLATION
```

without invoking any service code. **GLOBAL ROW IDENTITY ≠ TENANT AUTHORITY.** **A VALID FOREIGN KEY
TARGET ≠ AN AUTHORIZED TENANT TARGET.** **SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT.** Both
application validation and database enforcement must hold simultaneously. **NARROW R1 CORRECTION ≠ GLOBAL
OQI6 TENANT SAFETY** (§8's R2 boundary remains open). **DATABASE TENANT INTEGRITY ≠ PRODUCTION
ORCHESTRATION** (§9's separate deferral).

## 18. R1-I STOP conditions (binding, exhaustive)

OQI6-R1-I must STOP, preserve evidence, and return for renewed narrow governance rather than improvise, if
any of the following occurs:

```
 1. authoritative main moves materially (touches OQI6/OQI4/OQI5/migrations/tenant isolation/H5 Timeliness).
 2. this document's own governance hash (recorded §19) drifts before implementation begins.
 3. any file outside the exact three §14 paths requires a write.
 4. the migration requires a new column, a new table, or a parent-key change.
 5. oqi_business_processes' PRIMARY KEY(process_id, version) requires any change.
 6. uq_oqi_business_processes_tenant_pk requires any change.
 7. BusinessDependency or BusinessProcess domain semantics require any change.
 8. service, API, or frontend semantics require any change.
 9. the OQI6-R2 boundary (§8) requires any modification.
10. OQI4/OQI5 orchestration requires any modification.
11. any existing legacy data is found to violate the new FK and no governed remediation exists (§11) --
    migration must fail closed, not silently repair.
12. the same-tenant positive-control path (TI-01/03/04/08) is rejected post-correction.
13. the cross-tenant attack (TI-02) is still ACCEPTED post-correction.
14. H5 Timeliness's own FK or parent key is found altered.
15. any H1-H5 crown/regression value changes semantically.
16. whole-package mypy, black, isort, or ruff fails as a result of this correction.
17. full clean-candidate regression fails as a result of this correction.
18. Docker proof differs materially from host proof.
19. any DELETE is required.
20. CDD-044, CDD-050, CDD-051, or their own frozen Artifact Authorizations require any modification.
```

## 19. Governance byte-integrity

This document and its own content are the sole new governance artifact this phase publishes. `CDD-044`,
`CDD-050`, `CDD-051`, and their respective Artifact Authorizations are independently re-hashed immediately
before this document's own publication and confirmed byte-identical to their prior published values; none
is modified by this correction.

## 20. Historical honesty (disclosed without euphemism)

OQI6-R1-DR correctly identified and reproduced the genuine cross-tenant structural defect, correctly scoped
it to a single FK, and correctly recommended the replace architecture — but its own stated *reason* for
rejecting the additive alternative relied on an incorrect claim about PostgreSQL's constraint-conjunction
semantics (§5). This governance phase corrects that specific reasoning while affirming the DR's ultimate
architectural conclusion was independently still correct for the reasons now frozen in §5.

## 21. P0/P1/P2/P3

```
Before this document: P0 = 0, P1 = 1 (a live, reproduced PostgreSQL structural tenant-isolation gap on
                       oqi_business_dependencies -> oqi_business_processes; the governed service layer
                       remains protective for every current application code path, and zero rows anywhere
                       currently exploit it, so no currently-reachable production exploit is demonstrated --
                       P1, not P0, consistent with the identical H4 defect class's own classification)
After this document:  P0 = 0, P1 = 0, P2 = 0, P3 = 0 (pending the three-path correction §14 authorizes and
                       its own fresh whole-package static / real-PostgreSQL adversarial / Docker / full
                       regression re-verification, per §15's frozen matrix)
```

## 22. Implementation phasing

```
OQI6-R1-G  (this document)
  -> OQI6-R1-I   (single implementation phase -- no I1/I2 split; no genuine architectural boundary
                   was discovered separating the three §14 paths from one another)
  -> OQI6-R1-VM  (adversarial verify + merge, restarting fully against the new candidate, independently
                   re-proving this entire document rather than trusting OQI6-R1-I's own report)
```

## 23. VM merge gate (binding, restated)

OQI6-R1-VM may authorize a merge only if `P0 = 0` and `P1 = 0`, and independently proves: old FK
(`fk_oqi_business_dependencies_process`) absent; new FK (`fk_oqi_business_dependencies_tenant_process`)
present with exact §13 column shape; `uq_oqi_business_processes_tenant_pk` preserved unmodified; the §4
cross-tenant attack rejected by genuine PostgreSQL `IntegrityError`; the §4 same-tenant control accepted;
migration round trip correct (§15 TI-09); fail-closed behavior against deliberately-seeded invalid legacy
data (§15 TI-10); the R2 boundary (§8) untouched; H5 Timeliness unchanged; H1-H5 regressions green; fresh
`--no-cache` Docker matching host; the exact diff matching exactly the §14 three-path authorization; CI
green; exact candidate head unchanged through merge.

## 24. Authorization

This document is approved and published as a standalone governance artifact, following the established
precedent of `CDD-050-Artifact-Authorization-H4-R1-Reference-Tenant-Isolation-Correction-Amendment.md`.
Implementation against §14's exact three-path authorization may proceed under `OQI6-R1-I`.
