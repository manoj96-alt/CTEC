# CDD-050 — Artifact Authorization H4-R1 Reference Tenant-Isolation Correction Amendment (OQI-H4-R1)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-049-Artifact-Authorization-H3-VM-R1-CI-Type-Safety-Amendment.md` (the direct precedent for
this exact defect class and governance shape: a real-runtime/adversarial-verification phase discovers a
genuine gap outside the scope any prior phase's own Artifact Authorization anticipated, closed by a
narrow, standalone, additive amendment rather than by silently rewriting an already-verified candidate);
`CDD-039-Artifact-Authorization-Concurrency-Hardening-Amendment.md` (the established precedent for a
narrow structural-database-hardening correction discovered after initial implementation); migration
`0011_erm_tenant_and_evidence.py` (the exact, already-proven-safe technical pattern this amendment reuses:
add a tenant-qualified composite candidate key to a parent table, then replace a single-column child FK
with a tenant-qualified composite FK)
Classification: DATABASE-LEVEL STRUCTURAL TENANT-ISOLATION GAP (constraint-only correction; no schema
topology change, no table addition, no column addition, no semantic/evaluator/downstream change of any
kind)
Governs: `oqi-h4/integrity` branch, stopped candidate `42448ee8014d9844db9c0161939f21595cb27061`

## 1. Purpose

Authorizes the exact, narrow, additive correction of a genuine database-level tenant-isolation defect
discovered by OQI-H4-VM's own real-PostgreSQL adversarial verification of the stopped H4-I candidate, and
independently confirmed complete by OQI-H4-R1-DR: three tenant-sensitive foreign keys across the two
Reference Integrity tables use plain (non-tenant-qualified) foreign keys instead of the tenant-qualified
composite foreign keys CDD-050 §12/§27 require. **CDD-050 itself is not modified, not reopened, and remains
FROZEN exactly as originally published** — this amendment closes a missing physical prerequisite CDD-050's
own architecture already assumed, exactly mirroring the OQI-H1-CI/OQI-H3-VM-R1 precedent's own reasoning:
the original document's architecture was correct; a required physical fact about the existing schema was
not independently verified before implementation, and implementation substituted a weaker mechanism instead
of stopping.

## 2. Context — independently re-derived, not merely trusted from prior reports

OQI-H4-VM adversarially attacked the stopped candidate `42448ee8014d9844db9c0161939f21595cb27061` against
real PostgreSQL (migration head `0037_oqi_h4_impact_width`, 120 governed tables) by constructing a
`oqi_integrity_reference_evaluations` row with `tenant_id` = Tenant A directly referencing a real Tenant
B-owned `source_object_id`, bypassing the service layer entirely (`session.add()` + `session.flush()`).
**The database accepted it.** OQI-H4-VM stopped pre-merge rather than repair the candidate in place.

OQI-H4-R1-DR then independently re-attacked the full surface, using isolated `SAVEPOINT`-scoped attacks
against real PostgreSQL so each attack's rollback could not corrupt shared fixture data (an error present
in an earlier, uncommitted draft of that same discovery script, itself caught and corrected before R1-DR's
own final report). R1-DR proved the defect is **not limited to the one column OQI-H4-VM found**: both
tenant-sensitive foreign keys on `oqi_integrity_reference_evaluations`, and the independent
`source_object_id` foreign key on `oqi_integrity_reference_findings` (which carries no `evaluation_id`
linkage to the evaluation table at all — each row is independently keyed), are all vulnerable.

This session independently re-verified every R1-DR fact directly against real PostgreSQL and the exact ORM
source of the unmoved, unmerged candidate `42448ee8014d9844db9c0161939f21595cb27061` (`git rev-parse HEAD`
reconfirmed; `git merge-base --is-ancestor 42448ee... origin/main` reconfirmed NOT an ancestor) immediately
before writing this document:

```
$ SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'source_objects'::regclass;
  -- no UNIQUE(tenant_id, source_object_id) exists; only uq_source_objects_tenant_name (tenant_id, source_object_name)

$ SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
  WHERE conrelid = 'enterprise_entity_resolution_records'::regclass;
  -- uq_eer_records_tenant_pk  UNIQUE (tenant_id, record_id)   [already exists, added by migration 0011]

$ SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
  WHERE conrelid = 'oqi_integrity_reference_evaluations'::regclass;
  -- fk_oqi_integrity_reference_evaluations_source_object_id      FOREIGN KEY (source_object_id) REFERENCES source_objects(source_object_id)
  -- fk_oqi_integrity_reference_evaluations_resolution_record_id  FOREIGN KEY (resolution_record_id) REFERENCES enterprise_entity_resolution_records(record_id)

$ SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
  WHERE conrelid = 'oqi_integrity_reference_findings'::regclass;
  -- fk_oqi_integrity_reference_findings_source_object_id  FOREIGN KEY (source_object_id) REFERENCES source_objects(source_object_id)

$ SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
  WHERE conrelid = 'oqi_integrity_structural_evaluations'::regclass;
  -- fk_oqi_integrity_structural_evaluations_entity  FOREIGN KEY (tenant_id, enterprise_entity_id)
  --     REFERENCES enterprise_entities(tenant_id, enterprise_entity_id)   [control group: already correct]
```

All plain (single-column) as R1-DR reported; the Structural Integrity control group's own
`enterprise_entity_id` foreign key is confirmed already tenant-qualified composite, isolating the defect
precisely to the two Reference tables. A fresh adversarial re-attack (control group) confirms Structural
correctly rejects a cross-tenant entity reference (`ForeignKeyViolation` on
`fk_oqi_integrity_structural_evaluations_entity`), while the Reference tables' three vulnerable columns
were reconfirmed to accept cross-tenant rows.

## 3. Root-cause analysis (independently re-derived, reaffirming R1-DR)

**PRIMARY — governance prerequisite omission.** CDD-050 §12 correctly froze a tenant-qualified composite
foreign key for `oqi_integrity_reference_evaluations.source_object_id` and
`oqi_integrity_reference_findings.source_object_id`. Neither OQI-H4-DR nor OQI-H4-G independently confirmed,
against the real schema, that `source_objects` already exposed the required PostgreSQL composite candidate
key `UNIQUE(tenant_id, source_object_id)`. It does not, and never has — confirmed directly: no table in this
repository has ever needed a *relational* (non-JSON-array) tenant-qualified reference to
`source_objects.source_object_id` before H4; every pre-existing consumer (`QualityFindingORM`,
`BusinessRuleEvaluationORM`, `QualityComparisonEvaluationParticipantORM`, `SourceFieldORM`, `AssertionORM`,
`EvidenceORM`, and others) uses the identical plain single-column FK, so H4-I's implementation choice
mirrored true, if incomplete, repository-wide precedent rather than inventing a novel shortcut.

**SECONDARY — implementation fail-closed process violation.** CDD-050 §12's literal text also specifies a
plain (non-composite) FK for `resolution_record_id` — an internal asymmetry in the original document,
despite `enterprise_entity_resolution_records` already exposing the required
`uq_eer_records_tenant_pk UNIQUE(tenant_id, record_id)` composite candidate key (added by migration `0011`,
confirmed unrelated to and unmodified by H4). CDD-050 §27's own general, binding tenancy invariant — "No
tenant's graph or ER result may satisfy another tenant's evaluation... structurally enforced by... composite
FKs" — governs both references equally; §12's asymmetric literal schema text under-specified §27's own
already-frozen requirement for `resolution_record_id`. This is resolved here as the literal completion of
an already-frozen invariant, never as a new H4 semantic requirement (§6 below).

**TERTIARY — incomplete adversarial verification.** Neither H4-I nor its own internal verification executed
the exact real-PostgreSQL cross-tenant Reference Integrity attack CDD-050 §27 itself explicitly required
("Real-PostgreSQL adversarial proof required at H4-I"). OQI-H4-VM correctly caught this by finally running
it.

```
CDD-050 §12/§27 architecture:         SOUND -- confirmed by the exact, already-proven-safe RFC-016/
                                       migration-0011 pattern; no redesign required
Structural Integrity implementation:  ALREADY CORRECT (control group, independently reconfirmed)
Reference Integrity implementation:   DEFECTIVE -- 3 plain FKs where composite is required/intended
Missing prerequisite:                 source_objects lacks UNIQUE(tenant_id, source_object_id)
Available prerequisite unused:        enterprise_entity_resolution_records already carries
                                       uq_eer_records_tenant_pk -- H4-I never used it
```

## 4. §12/§27 resolution-record clarification (binding, resolves the internal asymmetry disclosed in §3)

This amendment does not alter CDD-050. It records, as binding interpretive clarification requested by
OQI-H4-R1-G's own governing instructions, that CDD-050 §27's general tenancy invariant governs
`resolution_record_id` identically to `source_object_id`, and that §12's own less-explicit literal phrasing
for `resolution_record_id` is completed, not contradicted, by this amendment's correction. Future readers of
CDD-050 §12 should read the `resolution_record_id` FK row as tenant-qualified composite, consistent with
§27, exactly as this amendment implements it.

## 5. Selected correction — OPTION A (structural database-level tenant isolation, no downgrade)

No service-only enforcement. No trigger-based workaround. No application-managed check presented as
"structural." No Reference persistence redesign. No new table. No new tenant model. No change to Structural
Integrity (already correct).

**A. New parent candidate key** (`source_objects` — no other table needs a new parent key):

```
uq_source_objects_tenant_pk   UNIQUE (tenant_id, source_object_id)
```

Semantically redundant for identity alone (`source_object_id` is already a single-column primary key, so
`(tenant_id, source_object_id)` can never contain a duplicate — independently reconfirmed: zero duplicate
pairs exist in the real, populated `ctec_test` database, and duplicates are structurally impossible under
the existing PK regardless of data). It is not redundant for its actual purpose: **GLOBAL ID UNIQUENESS ≠
TENANT CONSISTENCY ENFORCEMENT** — only a tenant-qualified candidate key lets PostgreSQL itself reject a
child row whose `tenant_id` disagrees with its parent's true owning tenant.

**B/C/D. Three composite child foreign keys** (exact names, independently re-verified ≤63 bytes and free of
any existing collision by repository-wide search):

```
oqi_integrity_reference_evaluations:
  DROP  fk_oqi_integrity_reference_evaluations_source_object_id
  ADD   fk_oqi_integrity_ref_eval_tenant_source_object
        FOREIGN KEY (tenant_id, source_object_id) REFERENCES source_objects (tenant_id, source_object_id)

  DROP  fk_oqi_integrity_reference_evaluations_resolution_record_id
  ADD   fk_oqi_integrity_ref_eval_tenant_resolution_record
        FOREIGN KEY (tenant_id, resolution_record_id)
            REFERENCES enterprise_entity_resolution_records (tenant_id, record_id)

oqi_integrity_reference_findings:
  DROP  fk_oqi_integrity_reference_findings_source_object_id
  ADD   fk_oqi_integrity_ref_finding_tenant_source_object
        FOREIGN KEY (tenant_id, source_object_id) REFERENCES source_objects (tenant_id, source_object_id)
```

No fourth child reference requires correction: `relationship_requirement_id` on both tables references the
shared-platform (non-tenant-owned) `relationship_requirements` table, unaffected by this amendment. No
`evaluation_id`-to-Finding linkage exists on either table to correct (independently reconfirmed against the
real ORM: `IntegrityReferenceFindingORM` carries no `evaluation_id` column).

## 6. Zero semantic/downstream change (binding)

This amendment changes constraints only. It authorizes **zero** change to: the Structural or Reference
evaluator algorithms; `UNRESOLVED`/`POSSIBLE`/no-outcome/`RESOLVED` semantics; Finding identity or lifecycle;
`QualityFindingOrigin`; OQI4; OQI6; H1 coverage; Reliance; remediation; authority/Keycloak; Entity
Resolution; `FieldValueEvidence`; ontology; the demo seeder's own crown values; any API route; any frontend
file. Every insert path in every existing repository/service already supplies `tenant_id` correctly on
every affected row; a purely additive constraint changes zero currently-passing behavior. Existing
application/service-layer tenant validation (`EntityResolutionStore`'s own tenant-ownership assertion, the
Reference repository's tenant-scoped queries) is preserved unchanged and unremoved — this amendment adds a
second, independent, structural layer, it does not replace the first:

```
SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT.  Both required.  Neither is a substitute for the
other.
```

## 7. Legacy `source_objects` consumer boundary (binding — explicit non-goal)

`uq_source_objects_tenant_pk` is a purely additive parent-side constraint; it changes nothing for any
existing consumer. This amendment explicitly does **not** authorize converting any other repository's
existing plain `source_object_id` foreign key (OQI1's `QualityFindingORM`, OQI2/OQI3's own evaluation
tables, `SourceFieldORM`, `AssertionORM`, `EvidenceORM`, or any other) to a composite FK. That is a distinct,
repository-wide RFC-016-retrofit class of hardening, out of scope for this H4-specific correction, and may
be separately governed later if ever pursued.

## 8. Table-count freeze (binding)

```
H4 pre-R1 (candidate 42448ee, migration head 0037):   120 governed business tables
H4 post-R1 (migration head 0038):                     120 governed business tables
```

Zero tables created. Zero tables deleted. Every existing `== 120` / `-eq 120` assertion (the six mechanical
test files and `.github/workflows/ci.yml` already corrected by H4-I) requires **no further change** —
independently reconfirmed by repository-wide search: none of them assert a migration-file count or exact
revision-name list, only the live table count, which this amendment does not alter.

## 9. Exact migration (binding — additive only, `0034`-`0037` remain byte-for-byte unmodified)

```
Revision:      0038_oqi_h4_reference_tenancy    (29 chars, independently re-verified <=32)
down_revision: 0037_oqi_h4_impact_width         (independently re-confirmed exact current head string)
```

Upgrade (exact order, no data rewrite, no ID rewrite, no backfill):

```
1. CREATE UNIQUE constraint  uq_source_objects_tenant_pk  ON source_objects (tenant_id, source_object_id)
2. DROP   fk_oqi_integrity_reference_evaluations_source_object_id
3. CREATE fk_oqi_integrity_ref_eval_tenant_source_object
4. DROP   fk_oqi_integrity_reference_evaluations_resolution_record_id
5. CREATE fk_oqi_integrity_ref_eval_tenant_resolution_record
6. DROP   fk_oqi_integrity_reference_findings_source_object_id
7. CREATE fk_oqi_integrity_ref_finding_tenant_source_object
```

Downgrade (exact reverse; the parent candidate key must never be dropped while any child composite FK still
depends on it):

```
1. DROP    fk_oqi_integrity_ref_finding_tenant_source_object
2. RESTORE fk_oqi_integrity_reference_findings_source_object_id  (single-column)
3. DROP    fk_oqi_integrity_ref_eval_tenant_resolution_record
4. RESTORE fk_oqi_integrity_reference_evaluations_resolution_record_id  (single-column)
5. DROP    fk_oqi_integrity_ref_eval_tenant_source_object
6. RESTORE fk_oqi_integrity_reference_evaluations_source_object_id  (single-column)
7. DROP    uq_source_objects_tenant_pk   (last -- only once no child FK depends on it)
```

**Duplicate-data precondition (binding, fail-closed):** before step 1, H4-R1-I must execute
`SELECT tenant_id, source_object_id, count(*) FROM source_objects GROUP BY tenant_id, source_object_id
HAVING count(*) > 1` and confirm zero rows before proceeding — independently reconfirmed zero duplicates
exist today, and duplicates are structurally impossible under the existing single-column primary key, but
H4-R1-I must prove this fresh against its own target database rather than trust this document's own
snapshot. If any duplicate is found: STOP, do not deduplicate, do not delete, return for renewed governance.
`tenant_id`/`source_object_id`/`resolution_record_id`/`record_id` are all `NOT NULL` on every affected
column (independently reconfirmed) — no `MATCH SIMPLE` NULL-skip ambiguity applies to any of the three new
composite FKs.

Brief `ACCESS EXCLUSIVE` locks during constraint add/drop on `source_objects`,
`enterprise_entity_resolution_records`, and the two H4 Reference tables are expected and acceptable —
identical operational class to migration `0011`'s own precedent, appropriate for this project's current
pre-production/demo phase; no `CONCURRENTLY` mechanism applies to constraint DDL.

## 10. Exact new-path authorization (binding — a maximum permitted write set, not a requirement to touch
every listed path beyond what correctness requires)

```
CREATE = 1
MODIFY = 3
DELETE = 0
TOTAL  = 4
```

```
CREATE  backend/app/infrastructure/persistence/migrations/versions/0038_oqi_h4_reference_tenancy.py
        Migration implementing §9 exactly. No other schema/table/column change.

MODIFY  backend/app/infrastructure/persistence/models/source_object.py
        Add ONLY UniqueConstraint("tenant_id", "source_object_id", name="uq_source_objects_tenant_pk")
        to __table_args__. No PK change, no other constraint change, no column change, no other file
        behavior change.

MODIFY  backend/app/infrastructure/persistence/models/oqi_integrity.py
        Replace ONLY the three named plain ForeignKey column declarations (§5.B/C/D) with table-level
        ForeignKeyConstraint composite declarations carrying the exact new names in §5. No column
        addition, no column deletion, no nullability change, no type change, no other table's shape
        changes, no new table.

MODIFY  backend/app/tests/test_oqi_h4_integrity_authorization_and_tenant_isolation.py
        Extend the existing T-series with the exact TI-01 through TI-36 adversarial acceptance matrix
        (§11 below) proving all three corrected boundaries reject cross-tenant rows and all legitimate
        same-tenant paths remain unaffected. This file is part of the still-unmerged, not-yet-frozen H4-I
        candidate (row 16 of the original H4 Artifact Authorization); extending it is the narrower,
        already-precedented choice over authorizing a new dedicated correction test file, independently
        confirmed by repository-wide search to require no other mechanical test-path change (migration-
        head assertions resolve dynamically via `ScriptDirectory.get_current_head()`; no file hardcodes a
        migration-count or exact revision-name list; no construction-site firewall test tracks
        `SourceObject`; no other file references any of the six constraint names touched by this
        amendment).
```

Repository-wide compatibility search performed and independently confirmed clean before freezing this
authorization: zero references to `0037_oqi_h4_impact_width` outside its own migration file; the six
mechanical `== 120` / `-eq 120` table-count assertions require no change (§8); zero other file references
any of the three old or three new constraint names; zero migration-exhaustive-list or revision-count
assertion exists anywhere in the test suite; `test_runtime_architecture.py`'s own construction-site firewall
does not track `SourceObject` at all. No path beyond the four above is authorized.

## 11. Frozen post-correction adversarial acceptance matrix (binding — TI-01 through TI-36)

```
TI-01  tenant A Reference Evaluation -> tenant A SourceObject                          -> ACCEPT
TI-02  tenant A Reference Evaluation -> tenant B SourceObject                          -> PG REJECT
TI-03  tenant A Reference Evaluation -> tenant A ResolutionRecord                       -> ACCEPT
TI-04  tenant A Reference Evaluation -> tenant B ResolutionRecord                       -> PG REJECT
TI-05  tenant A Reference Finding    -> tenant A SourceObject                           -> ACCEPT
TI-06  tenant A Reference Finding    -> tenant B SourceObject                           -> PG REJECT
TI-07  tenant A Evaluation -> tenant B SourceObject + tenant A ResolutionRecord          -> PG REJECT
TI-08  tenant A Evaluation -> tenant A SourceObject + tenant B ResolutionRecord          -> PG REJECT
TI-09  tenant A Evaluation -> tenant B SourceObject + tenant B ResolutionRecord          -> PG REJECT
TI-10  normal service Reference Integrity path                                          -> unchanged PASS
TI-11  UNRESOLVED -> ORPHAN_REFERENCE                                                    -> unchanged
TI-12  RESOLVED -> SATISFIED                                                             -> unchanged
TI-13  POSSIBLE -> NOT_EVALUABLE                                                         -> unchanged
TI-14  no outcome -> NOT_EVALUABLE                                                       -> unchanged
TI-15  RESOLVED/no-edge distinction (Reference SATISFIED, Structural MISSING, no orphan) -> unchanged
TI-16  Structural Integrity crown                                                        -> unchanged
TI-17  OQI4                                                                              -> unchanged
TI-18  OQI6                                                                              -> unchanged
TI-19  Coverage                                                                          -> unchanged
TI-20  Reliance                                                                          -> unchanged
TI-21  migration 0037->0038                                                              -> 120 tables
TI-22  migration 0038->0037                                                              -> 120 tables
TI-23  migration 0037->0038 again (idempotent re-upgrade)                                -> 120 tables
TI-24  whole-H4 migration 0033->0038                                                     -> 114->120
TI-25  whole-H4 downgrade 0038->0033                                                     -> 120->114
TI-26  whole-H4 re-upgrade 0033->0038                                                    -> 114->120
TI-27  whole-package mypy                                                                -> clean
TI-28  full backend regression, clean candidate                                          -> clean
TI-29  fresh Docker schema                                                               -> 0038 / 120
TI-30  Docker tenant A -> tenant B SourceObject attack                                   -> PG REJECT
TI-31  Docker tenant A -> tenant B ResolutionRecord attack                               -> PG REJECT
TI-32  Docker Reference Finding -> tenant B SourceObject attack                          -> PG REJECT
TI-33  Docker legitimate same-tenant paths                                               -> ACCEPT
TI-34  H1 crown                                                                          -> unchanged
TI-35  H2 crown                                                                          -> unchanged
TI-36  H3 crown                                                                          -> unchanged
```

Every REJECT above must be a genuine PostgreSQL `ForeignKeyViolation`/`IntegrityError`, never inspection of
DDL text, never a service-layer-only rejection substituting for the database proof. Every ACCEPT above must
be a genuine successful insert through the normal application/service path (TI-01/03/05/10) or an
intentionally-valid direct row (TI-33), not merely "no exception was raised by mistake."

## 12. Root invariant (binding, restated for zero ambiguity)

```
TENANT A REFERENCE INTEGRITY ROW
     |
     +-- tenant_id = A
     |
     +-- tenant-owned parent id = B-owned
                |
                v
           PostgreSQL
                |
                v
        FOREIGN KEY VIOLATION
```

without invoking any service code. The database is not a substitute for the service layer's own tenant
validation; the service layer is not a substitute for structural database enforcement. **GLOBAL ID
UNIQUENESS ≠ TENANT CONSISTENCY ENFORCEMENT.** **SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT.**
Both must hold simultaneously.

## 13. R1-I STOP conditions (binding, exhaustive)

H4-R1-I must STOP, preserve evidence, and return for renewed narrow governance rather than improvise, if
any of the following occurs:

```
 1. source_objects is found to contain a duplicate (tenant_id, source_object_id) pair.
 2. enterprise_entity_resolution_records lacks the expected uq_eer_records_tenant_pk.
 3. any parent candidate key beyond source_objects proves unexpectedly necessary.
 4. any fourth H4 Reference tenant-sensitive foreign key is discovered.
 5. any Structural or Reference evaluator semantic change is required.
 6. any OQI4 production code change is required.
 7. any OQI6 production code change is required.
 8. any Coverage/Reliance production semantic change is required.
 9. any remediation production semantic change is required.
10. any API change is required.
11. any frontend change is required.
12. any Keycloak/authority change is required.
13. any implementation path outside this amendment's four-path authorization is required.
14. any DELETE is required.
15. the additive 0038 migration cannot express the correction as specified.
16. downgrade cannot safely and fully restore the exact pre-0038 (0037) state.
17. PostgreSQL accepts any one of the TI-02/04/06/07/08/09/30/31/32 attacks after correction.
18. any legitimate same-tenant insert (TI-01/03/05/10/33) is rejected.
19. whole-package mypy fails as a result of this correction.
20. full clean-candidate regression fails as a result of this correction.
21. any H4 crown value changes semantically.
22. any H1/H2/H3 crown value regresses.
23. Docker proof differs materially from host proof.
24. any governance hash drifts (CDD-050, its original AA, the H3-I-R1/H3-VM-R1 amendments, or this
    document, once published).
25. candidate 42448ee, or any of the H4-G/H4-I history, requires rewriting.
```

## 14. H4-VM restart rule (binding, restated)

After H4-R1-I completes, H4-VM does not resume from its own prior stopping point. It restarts in full
against the new exact correction head, independently re-proving governance, the complete exact diff, the
full Artifact Authorization (original 36 rows plus this amendment's 4), source-level architecture, all
three corrected tenant boundaries, the previously-disclosed OQI4 `DirectImpactResult` and OQI6 `Any`-bridge
deviations, whole-package static verification, clean-candidate regression, real PostgreSQL, fresh Docker,
the exact GitHub PR head, CI, merge, and post-merge verification. No result from the prior, stopped
H4-VM run substitutes for proof against the new candidate identity.

## 15. Candidate preservation (binding)

`42448ee8014d9844db9c0161939f21595cb27061` is not amended, rebased, or squashed by this document or by
H4-R1-I. History remains: H3 main → H4-G (`db5b7d1`) → H4-I candidate (`42448ee`) → this governance
amendment → H4-R1-I correction commit (additive on top of `42448ee`) → restarted H4-VM.

## 16. Governance byte-integrity

Independently re-hashed immediately before this document was written and confirmed byte-identical to their
prior publication values, both in the working tree and inside the unmoved, unmerged candidate commit
`42448ee8014d9844db9c0161939f21595cb27061`:

```
da59e56997dfba01ab6e172e81505c9f8e96ab6b5ae339c8f575a036186cf4ab
  CDD-050-OQI-H4-Governed-Integrity.md
508cd1f0611e8f2e757e46fc91a6309f45b8549e56cebfe1226b5e26d99be502
  CDD-050-OQI-H4-Governed-Integrity-Artifact-Authorization.md
```

Neither file is modified by this amendment. This document and its own companion Artifact Authorization
content (§10) are the sole new governance artifacts this phase publishes.

## 17. Historical honesty (binding, disclosed without euphemism)

OQI-H4-VM correctly stopped pre-merge rather than repair the defect inside the already-stopped candidate.
OQI-H4-R1-DR correctly found a materially larger defect surface (three columns, not one) than OQI-H4-VM's
own initial report, through more rigorous adversarial methodology (isolated `SAVEPOINT`-scoped attacks
rather than shared-fixture sequential attacks, which OQI-H4-R1-DR's own draft script first demonstrated the
failure mode of before correcting itself). No implementation write against any of the four §10 paths has
occurred before this amendment's publication.

## 18. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 1 (frozen CDD-050 §12/§27 database-level tenant-isolation guarantee
                        violated on the exact adversarially-verified candidate; three columns, two tables;
                        normal service-layer path remains protective, so no currently-reachable production
                        exploit is demonstrated -- P1, not P0)
After this amendment:   P0 = 0, P1 = 0, P2 = 0, P3 = 0 (pending the four-path correction §10 authorizes and
                         its own fresh whole-package mypy / real-PostgreSQL adversarial / Docker / full
                         regression re-verification, per §11's frozen matrix)
```

## 19. Authorization

This amendment is approved and published as a standalone governance artifact, following the established
repository precedent (OQI-H1-CI, OQI-H3-I-R1, OQI-H3-VM-R1) of never silently rewriting an already-approved
Artifact Authorization in place, and never folding an out-of-scope correction into an already-stopped
candidate commit. Implementation against §10's exact four-path authorization is authorized only after this
document's own publication and hash computation — never before. CDD-050 remains FROZEN, unmodified, and
fully authoritative. OQI-H4 merge readiness is reauthorized to resume, under the identifier OQI-H4-R1, only
after H4-R1-I's own complete verification against §11's frozen matrix and a full H4-VM restart per §14.
