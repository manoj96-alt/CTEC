# CDD-019 — H1 Source Field / Semantic Mapping Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `688c46c94f2b7f9148b42e58ff426e5fc9c948f7`

## Decision

CDD-019 §25 defers the exhaustive per-file artifact-authorization record for each of its H1-H3
implementation phases to a separate, subsequent, CDD-Template-v2.2-compliant document, mirroring
CDD-017's G2/G3/G3.5 and CDD-018's G4 companions' exact format — binding: "Implementation MUST NOT
proceed against §6-20's model without the applicable phase's separate, subsequent artifact-authorization
record existing first." This report is that record for **H1 only** — SourceField & SemanticMapping
Domain/Persistence Foundation. It is a standalone companion to CDD-019 (itself a standalone CDD, not a
CDD-017/CDD-018 companion), following the identical companion precedent already used four times across
CDD-017 and CDD-018.

This record was produced through: H1 artifact discovery; a Product Owner governance review that found
two P1 findings (SourceField physical-identity uniqueness was unspecified; the SemanticMapping
repository surface was insufficiently restricted against H2 leakage) and two P2 findings (migration
reversibility not made explicit; the partial-unique-index mechanism's novelty not flagged for explicit
evidence); a remediation pass closing all four; and a final revalidation confirming P0 = 0, P1 = 0,
P2 = 0. No implementation exists yet.

## Discovery findings (binding, restated for the record)

- **Repository/Unit-of-Work pattern**: `SourceField` and `SemanticMapping` follow `BlueprintRepository`'s
  bespoke `Protocol` + `Impl` pattern, **not** the generic `BaseRepository`/`REPOSITORY_TYPES`/
  `UnitOfWork`-registered pattern `SourceSystemRepository`/`SourceObjectRepository` use. Verified
  directly: `BaseRepository` (`base_repository.py`) is pure generic CRUD with no domain-object mapping
  and no custom query capability; CDD-019 §11's bidirectional-ambiguity-raising logic cannot be expressed
  through it. `BlueprintORM` is confirmed absent from `models/__init__.py`'s generated aggregator and
  `Blueprint` is confirmed absent from `REPOSITORY_TYPES` — the established precedent for a new,
  bespoke-governed capability needing custom write-time logic is to bypass the generic registry entirely,
  not register with it. This report follows that precedent; it does not modify `models/__init__.py`,
  `repositories/__init__.py`, or `unit_of_work.py`.
- **Migration-head stale-expectation precedent**: G2's own implementation (commit `1df0024`, "Gate G:
  update migration head test expectations") updated four hardcoded revision/table-count assertions when
  its migration (`0014`) became the new head — `test_persistence_integration.py`,
  `test_knowledge_engine.py`, `test_governance_engine.py`, `test_decision_engine.py`. G2's own companion
  did not list these files by name in its authorized-artifact table (a precedent gap). This report closes
  that gap by authorizing them explicitly, in advance, by name.
- **SourceField physical identity**: CDD-019 §7 characterizes `field_label` as "the field's identity
  within its object" — this is the physical-identity invariant a `UniqueConstraint(source_object_id, field_label)` makes durable; without it, "deterministic physical identity" (a property CDD-019 assumes)
  is not actually guaranteed by the originally-proposed schema. This report authorizes that constraint.
- **First use of a PostgreSQL partial unique index in this repository's schema**: no existing table uses
  `postgresql_where`-scoped indexing. The mechanism is standard, stable PostgreSQL/SQLAlchemy/Alembic
  functionality (confirmed: this repository has no SQLite test tier, so no cross-database portability
  concern exists), but because no prior evidence in this codebase proves it behaves as expected here, H1's
  closure evidence for this specific index **must** be a real-PostgreSQL test exercising its rejection
  behavior directly — an ORM-level or ambiguity-check-only unit test is not sufficient to close this
  criterion.

## Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/domain/integration/source_field.py` | CREATE | CDD-019 §7 | `SourceField` frozen dataclass: `source_field_id`, `source_object_id`, `field_label`, `lifecycle_state`, `governance_status`, `created_by`, `created_on`, `modified_by`, `modified_on`. | No `tenant_id` field (§7, §18). No `source_system_id` field (§7 — provenance reaches `SourceSystem` transitively through `source_object_id` alone). No schema/version field (§7 — inherited transitively from `SourceObject`, not duplicated). No `version_number`/`previous_version_id` (§13). No semantic/type/vocabulary field of any kind. | Domain unit test. |
| `backend/app/domain/integration/__init__.py` | MODIFY | CDD-019 §7 | Add `SourceField` to the existing `SourceObject`/`SourceSystem` export list. | No change to `SourceObject`/`SourceSystem` exports. | Import/boundary test. |
| `backend/app/domain/semantic_mapping/__init__.py` | CREATE | CDD-019 §8 | Package export surface, mirroring `domain/blueprint/__init__.py`'s pattern. | No additional export beyond `SemanticMapping` and any directly-supporting value type. | Import/boundary test. |
| `backend/app/domain/semantic_mapping/model.py` | CREATE | CDD-019 §8 | `SemanticMapping` frozen dataclass: `semantic_mapping_id`, `source_field_id`, `information_element_requirement_id`, `lifecycle_state`, `governance_status`, `created_by`, `created_on`, `modified_by`, `modified_on`. | No `tenant_id` field (§8, §18). No computation, expression, transformation, or condition field of any kind (§4, §12). No `information_element_definition_id` or any intermediate semantic-identity reference (§10). No `version_number`/`previous_version_id` (§13). | Domain unit test. |
| `backend/app/infrastructure/persistence/models/source_field.py` | CREATE | CDD-019 §7 | `SourceFieldORM(BaseEntity)`, table `source_fields`; FK `source_object_id → source_objects.source_object_id`; `UniqueConstraint("source_object_id", "field_label", name="uq_source_fields_object_label")` enforcing physical-field identity within one `SourceObject` (Discovery findings, above). | No `tenant_id` column. No registration in `models/__init__.py`'s generated aggregator (Discovery findings, above). No `version_number`/`previous_version_id` column. | Model unit test; Postgres integration test (see below). |
| `backend/app/infrastructure/persistence/models/semantic_mapping.py` | CREATE | CDD-019 §8, §10, §11 | `SemanticMappingORM(BaseEntity)`, table `semantic_mappings`; FK `source_field_id → source_fields.source_field_id`; FK `information_element_requirement_id → information_element_requirements.information_element_requirement_id`; partial unique index `(source_field_id) WHERE governance_status = 'Approved'` — the durable, database-enforced half of CDD-019 §11's source-side uniqueness rule. | No `tenant_id` column. No column, index, or constraint expressing the target-side `(information_element_requirement_id, tenant)` rule at the database level (§11 explicitly requires this be application-layer-enforced, since tenant is join-derived, not a stored column — a bare DB constraint here would be incorrect, not merely insufficient). No registration in `models/__init__.py`. No `version_number`/`previous_version_id` column. | Model unit test; Postgres integration test (see below). |
| `backend/app/infrastructure/persistence/migrations/versions/0015_source_field_semantic_mapping.py` (verify exact next-sequential number/name against the actual Alembic head at implementation time) | CREATE | CDD-019 §7, §8, §11 | `op.create_table` for `source_fields` and `semantic_mappings` with exactly the columns/FKs/constraints/index above; `down_revision` set to the actual current head (`"0014_blueprint_requirement"` as of this report). **Both `upgrade()` and `downgrade()` MUST be defined and functionally correct**, matching every existing migration in this repository (confirmed: zero exceptions found) — `downgrade()` must cleanly reverse both table creations and both new constraints. | No structural change to any existing table. No seed data inserted by the migration itself. No `tenant_id` column on either new table. | Migration upgrade test (`migrated_engine` fixture applies cleanly); `downgrade()` presence and structural correctness (execution not required to close H1, matching the established local precedent that no prior Gate G/H migration test exercises `alembic downgrade` execution). |
| `backend/app/infrastructure/persistence/source_field_repository.py` | CREATE | CDD-019 §7, §16 | `SourceFieldRepository` (`Protocol`) + `SourceFieldRepositoryImpl`, exposing **exactly two members**: `create(self, source_field: SourceField) -> None` and `get_by_id(self, source_field_id: UUID) -> SourceField \| None`. `get_by_id` is authorized strictly as an internal read needed by tests only, matching `BlueprintRepository.get_by_id`'s identical G2 precedent. | No `get_by_object_id`. No "list all." No resolution-shaped or criteria-based query method of any kind. No FastAPI router or schema. | Repository unit test; Postgres integration test. |
| `backend/app/infrastructure/persistence/semantic_mapping_repository.py` | CREATE | CDD-019 §8, §11, §16 | `SemanticMappingRepository` (`Protocol`) + `SemanticMappingRepositoryImpl`, exposing **exactly two members**: `create(self, semantic_mapping: SemanticMapping) -> None` and `get_by_id(self, semantic_mapping_id: UUID) -> SemanticMapping \| None`. `create()` internally enforces CDD-019 §11's **both** uniqueness rules before insert — (a) no existing `Approved` row shares the new row's `source_field_id`; (b) no existing `Approved` row shares the new row's `information_element_requirement_id` within the same tenant (resolved via a join through `source_field_id → source_object_id → tenant_id`) — raising `ValidationException` on either violation, mirroring `BlueprintRepository.get_approved_by_name`'s exact explicit-raise-on-ambiguity precedent. | **Binding, critical**: the ambiguity-check logic MUST be a private, non-`Protocol` implementation detail of `create()` alone — never a named public method, never independently callable, never exposed on the `Protocol`. In particular, this report does **not** authorize `resolve(...)`, `find_approved_mapping(...)`, `get_approved_for_source_field(...)`, `get_by_information_element_requirement(...)`, `check_ambiguity(...)`, or any equivalent externally callable resolution/query capability — that capability belongs exclusively to H2's own future, separately-authorized companion. No "list all." No FastAPI router or schema. | Repository unit test; Postgres integration test (see uniqueness cases below). |
| `backend/app/tests/test_source_field_persistence.py` | CREATE | CDD-019 §7 | Unit-level: domain dataclass validation; no `tenant_id` field present; `source_object_id` FK identity presence. | No PostgreSQL dependency. | Direct test execution. |
| `backend/app/tests/test_source_field_persistence_postgres.py` | CREATE | CDD-019 §7 | Postgres-backed: real FK constraint enforcement (invalid `source_object_id` rejected); round-trip `create`/`get_by_id`; **same `source_object_id` + same `field_label` → `IntegrityError`** (physical-identity uniqueness, Discovery findings above); **different `source_object_id`s + same `field_label` → both succeed** (proving the constraint is correctly scoped to the pair, not the label alone). | No test asserts against any resolution-shaped behavior. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_semantic_mapping_persistence.py` | CREATE | CDD-019 §8, §12 | Unit-level: domain dataclass validation; no `tenant_id` field present; structural absence of any transformation/expression/condition field. | No PostgreSQL dependency. | Direct test execution. |
| `backend/app/tests/test_semantic_mapping_persistence_postgres.py` | CREATE | CDD-019 §11, §18 | Postgres-backed: real FK constraint enforcement (invalid `source_field_id`/`information_element_requirement_id` rejected); round-trip `create`/`get_by_id`; and the seven bidirectional-uniqueness cases below, each proven against the real database. | No test asserts against any resolution-shaped behavior. No test exercises H2/H3/H4 concerns. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_persistence_integration.py` | MODIFY | Precedent commit `1df0024` | Update pinned `revision` string (`"0014_blueprint_requirement"` → the H1 migration's actual revision id) and `table_count` (`57` → `59`). | No other assertion changed. | Direct test execution. |
| `backend/app/tests/test_knowledge_engine.py` | MODIFY | Precedent commit `1df0024` | Update pinned `revision` string only, in `test_knowledge_migration_and_immutability`. | No other assertion changed. | Direct test execution. |
| `backend/app/tests/test_governance_engine.py` | MODIFY | Precedent commit `1df0024` | Update pinned `revision` string only, in `test_governance_migration_and_immutability`. | No other assertion changed. | Direct test execution. |
| `backend/app/tests/test_decision_engine.py` | MODIFY | Precedent commit `1df0024` | Update pinned `revision` string only, in `test_decision_migration_and_immutability`. | No other assertion changed. | Direct test execution. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 (mechanism origin), reused by every prior Gate G/H phase | Extend `AUTHORIZED_CHANGED_PATHS` with exactly the genuinely new paths in this table. | No assertion weakened. No wildcard path. No existing authorized path removed. | Direct test execution. |

No other repository path is authorized. All unlisted paths are READ-ONLY under this report. In
particular: `models/__init__.py`, `repositories/__init__.py`, and `unit_of_work.py` are **not**
authorized for modification (Discovery findings, above).

## Explicit exclusions (binding, restated from CDD-019)

No many-to-one, one-to-many, transformation, derivation, calculation, unit-conversion, conditional-
mapping, or expression-engine capability of any kind (§4, §9, §12). No `InformationElementDefinition` or
other intermediate semantic-identity object (§4, §10). No modification to `Blueprint`,
`ConceptRequirement`, `InformationElementRequirement`, the Blueprint domain model, the Blueprint ORM, any
Blueprint migration, `BlueprintRepository`, or `BlueprintApplicationService` (§4, §19). No modification to
`BlueprintConformanceApplicationService` or any other CDD-018 artifact (§4, §6, §20). No change to
`InformationElementRequirement` evaluation status — it remains `NOT_EVALUATED` (§4, §6, §20). No live
source-system connectivity, source-field value reading, or evidence-of-presence evaluation of any kind
(§4, §6, §20). No minting of a second Blueprint version, no Blueprint version re-parenting/versioning
mechanism implementation (§4, §19). No modification to `SourceSystem`, `SourceObject`, or their governing
RFC-015 physical model (§4, §7). No new ontology concept or relationship (§4, §17). No external HTTP
endpoint, API schema, or FastAPI router (§4, §21). No frontend or UI of any kind (§4, §21). No new
authentication or authorization scope (§4, §21). No modification to `assertions`, `Assertion.predicate`,
`SourceObservation`, `InstitutionalConcept`, `SemanticResolutionRecord`, Entity Resolution, Governance
Engine, Knowledge Engine, Decision Engine, Ask CTEC's traversal code, Gate F's DRM/GRM,
`runtime/orchestration.py`, or `runtime/recovery.py` (§4, §17, §18).

## Tenant-isolation requirement (binding)

Neither `SourceField` nor `SemanticMapping` carries a `tenant_id` column. Tenant identity is resolved
exclusively by walking `source_object_id → source_objects.tenant_id` (for `SourceField`) and
`source_field_id → source_object_id → tenant_id` (for `SemanticMapping`) — never stored redundantly,
never independently asserted. This is not merely a convention: it is the mechanism that makes cross-
tenant `SourceField`/`SemanticMapping` ownership **structurally unrepresentable**, not just rejected by a
checked constraint — there is no second, independently-stored tenant marker anywhere in either new table
that could ever disagree with `SourceObject`'s own (CDD-019 §18, restated). Every write-time uniqueness
check that requires tenant scope (the target-side rule below) MUST resolve tenant via this join at check
time, not via any stored value.

## SourceField physical identity (binding)

`UniqueConstraint(source_object_id, field_label)` on `source_fields`. Within one `SourceObject`, a
`field_label` identifies at most one `SourceField` row. The same `field_label` text under two *different*
`SourceObject`s (same or different tenant) is unrestricted — the constraint is scoped to the pair, never
to `field_label` alone, and never functions as a global or semantic identity of any kind (it says nothing
about what the field *means*, only that this exact string, under this exact physical object, names at
most one row).

## SemanticMapping bidirectional Approved uniqueness (binding, restated from CDD-019 §11)

Two symmetric rules, both scoped by governed ID, never by name:

- **Source-side** (durable, database-enforced): at most one `Approved` `SemanticMapping` row per
  `source_field_id` — enforced by the partial unique index on `semantic_mappings`.
- **Target-side** (application-layer-enforced, per CDD-019 §11's own binding acknowledgment that a bare
  database constraint is not possible here without duplicating `tenant_id`): at most one `Approved`
  `SemanticMapping` row per `(information_element_requirement_id, tenant)` pair, where tenant is resolved
  transitively at check time, not stored.

Both rules apply only to `governance_status = Approved` rows; `Draft`, `Retired`, and `Archived` rows are
never counted as competing mappings under either rule. Both are enforced inside
`SemanticMappingRepositoryImpl.create()`, raising `ValidationException` on violation — never a silent
first-match, last-write-wins, priority-ordering, or confidence-scored resolution.

## Determinism requirement (binding, restated from CDD-019 §22)

Creating the same `SourceField`/`SemanticMapping` state and reading it back via `get_by_id` MUST yield an
identical result on repeated read — guaranteed directly by the absence of any non-deterministic
transformation or computation in either object (§12) and by the write-time uniqueness rules above, which
guarantee at most one `Approved` answer can ever exist for either query direction once H2 is later
authorized to ask it.

## Failure semantics (binding, restated from CDD-019 §23)

If `SemanticMappingRepositoryImpl.create()`'s internal check finds an existing `Approved` row violating
either uniqueness rule, `create()` MUST raise `ValidationException` explicitly and MUST NOT insert the
new row — consistent with CDD-017 §7's, CDD-018 §22's, and CDD-019 §23's identical binding instructions
elsewhere in this governance family. An invalid FK reference (nonexistent `source_object_id`,
`source_field_id`, or `information_element_requirement_id`) MUST be rejected by the database layer
(`IntegrityError`), matching `test_invalid_entity_type_reference_is_rejected_at_the_database_layer`'s
exact established precedent.

## Evidence obligations

Real-PostgreSQL evidence is required, not assumed equivalent to unit-test/ORM-level evidence, for: FK
integrity on both new tables; the `SourceField` physical-identity uniqueness constraint (both the
rejection and the legitimate-reuse-across-objects case); the `SemanticMapping` source-side partial unique
index's actual rejection behavior (the first use of this schema pattern in this repository — Discovery
findings, above); the `SemanticMapping` target-side application-layer check's actual rejection behavior;
cross-tenant independence (equivalent mappings in two different tenants, both succeeding); and Draft/
Retired-plus-Approved history coexistence. Migration `upgrade()` correctness is required; `downgrade()`
presence and structural correctness is required, execution is not (matching established local precedent).

## Regression obligations

This phase introduces a new migration and two new tables, unlike every prior Gate H governance phase and
unlike G3/G3.5/G4 (none of which added a migration). The stale-expectation risk this creates is fully
enumerated and pre-authorized above (the four `revision`/`table_count`-pinning test files), closing the
exact precedent gap G2's own companion left open (commit `1df0024` existed but was never listed in
`CDD-017-G2-Persistence-Domain-Artifact-Authorization.md`).

## H2/H3/H4 exclusion (binding)

No artifact in this table performs, enables, or scaffolds: any mapping-resolution application service or
capability answering "given a tenant/source field, resolve its Approved `InformationElementRequirement`"
(H2 — reserved for its own future, separately-authorized companion); any deterministic demo/production
seed dataset or Gate H demonstration workflow (H3 — reserved for its own future, separately-authorized
companion); any live source-field value reading, connector integration, information-element completeness
evaluation, `SATISFIED`/`MISSING` evaluation, or `BlueprintConformanceApplicationService` modification
(H4 — entirely outside CDD-019's authority under any circumstance). `InformationElementRequirement`
evaluation remains exactly `NOT_EVALUATED`, unchanged, for the full duration of this report's authority.

## Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the eighteen artifact paths authorized above without new Product
Owner authorization. If implementation discovers that any authorized artifact's Exclusions column cannot
be satisfied without touching an unlisted path (in particular: `models/__init__.py`,
`repositories/__init__.py`, `unit_of_work.py`, any Blueprint artifact, any H2/H3/H4 concern, or any public
resolution-shaped repository method), implementation MUST STOP and report the exact blocker rather than
silently expanding scope.

## Authorization

Authorized by CTEC Product Owner Manoj Nair: this artifact-authorization record satisfies CDD-019 §25's
binding implementation precondition for exactly the H1 — SourceField & SemanticMapping Domain/Persistence
Foundation scope listed above, per the Gate H1 artifact discovery, Product Owner governance review (P1×2,
P2×2 findings), remediation, and final revalidation (P0=0, P1=0, P2=0). CDD-019 remains unchanged. No
implementation exists yet — a separate, subsequent Product Owner authorization is required before any
file listed above is created or modified. H2, H3, and H4 remain entirely outside this report's authority
and each requires its own, separate, future artifact-authorization companion (H2, H3) or CDD (H4).
