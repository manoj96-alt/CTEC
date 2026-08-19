# CDD-018 — G4 Blueprint Conformance Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `c4c011a984a86450a36d36130f6932bda118f414`

## Decision

CDD-018 §25 defers the exhaustive per-file artifact-authorization record for its own implementation
phase to a separate, subsequent, CDD-Template-v2.2-compliant document, mirroring CDD-015 §33's and
CDD-017's own G2/G3/G3.5 companions' exact format — binding: "Implementation MUST NOT proceed against
§6-16's model without that separate, subsequent artifact-authorization record existing first." This
report is that record. It is a standalone companion to CDD-018 (itself a standalone CDD, not a CDD-017
companion — CDD-017 remains unchanged), following the identical companion precedent already used four
times in this Gate.

This report authorizes exactly the artifact scope discovered against CDD-018's already-authorized
architecture (§6-16) — no artifact added, removed, renamed, or expanded beyond what that architecture
requires. It introduces no new architecture of its own: every artifact below implements CDD-018's
already-frozen semantics. G4 implements structural conformance evaluation only — no persistence, no
external API, no frontend, no source-to-Blueprint mapping, matching CDD-018 §15's ephemeral-evaluation
decision and §19-§20's exclusions exactly.

## Discovery findings (binding, restated for the record)

**Tenant-context read mechanism**: discovery found
`backend/app/infrastructure/persistence/institutional_relationship_store.py`
(`InstitutionalRelationshipStore`) — an existing, tenant-scoped, read-only query class over exactly
`enterprise_entities`/`institutional_relationships`, already consumed by Ask CTEC (Gate D). Its query
methods, however, match entities/relationships **by name** (`entity_type_name`, `relationship_type_name`)
for Ask CTEC's own traversal needs, and its return types (`GraphEntity`/`GraphEdge`) belong to
`app.domain.ontology_copilot.traversal` — Gate D's own domain vocabulary. CDD-018 §8/§9 requires matching
by `entity_type_id`/`relationship_type_id` — the same governed identity `ConceptRequirement`/
`RelationshipRequirement` already carry — not by name. Reusing `InstitutionalRelationshipStore` directly
would require an ID→name translation step nowhere else required, and would couple Blueprint Conformance
(Gate G) to Ask CTEC's own domain vocabulary (Gate D) — neither is architecturally necessary. Reusing
this repository's own established convention instead — a new, narrow, dedicated read-only store,
following `InstitutionalRelationshipStore`'s exact shape and tenant-scoping discipline but returning
ID-keyed results — is therefore the correct minimal answer, not an invented one. The two
`BaseRepository`-derived generated repositories (`EnterpriseEntityRepository`,
`InstitutionalRelationshipRepository`) are explicitly marked "Generated persistence-only repository. Do
not add business logic." and expose no filtering at all (`BaseRepository.list()` has no `WHERE` clause
of any kind) — confirming, by the same precedent that already led to `InstitutionalRelationshipStore`'s
own creation, that a new dedicated store is the established pattern for this need, not a modification to
either generated repository.

**Blueprint resolution mechanism (corrected)**: an earlier draft of this report proposed resolving the
canonical Blueprint by recomputing `BlueprintSeeder._stable_id("blueprint", CANONICAL_BLUEPRINT_NAME)`
and calling `BlueprintApplicationService.get_by_id()` directly. **The Product Owner rejected this
design**: `BlueprintSeeder` is bootstrap/seed infrastructure; a runtime evaluation service depending on
its internal identity-derivation algorithm as its production Blueprint-discovery mechanism would make
seed implementation detail into a load-bearing runtime contract, and would create an
`application/` → infrastructure-seed dependency this repository has never had elsewhere. CDD-018 §13
itself does not describe a caller-supplied-identity contract — it describes an internally-resolved
lookup ("The canonical Blueprint is resolved by `blueprint_name` plus `governance_status = Approved`
filtering"), confirming that a caller-supplied `blueprint_id` shortcut is not what CDD-018 actually
governs. Re-investigation confirmed that **no existing `BlueprintRepository`/`BlueprintApplicationService`
method performs this exact resolution today** (only `get_by_id` exists; `get_by_name` was explicitly
excluded from G2's own authorized scope, pending exactly this future need). The corrected design adds a
narrow new method — `get_approved_by_name(blueprint_name)` — to both `BlueprintRepository` and
`BlueprintApplicationService`, implementing CDD-018 §13's resolution rule directly (query
`blueprint_name` + `governance_status = Approved`; return `None` on zero matches; raise explicitly on
more than one match, per CDD-018 §13's own "Precision clarification"). `BlueprintConformanceApplicationService`
receives the `blueprint_name` to evaluate as an explicit input from its own caller (an
application-composition concern outside CDD-018's scope, not hardcoded or imported from
`blueprint_seed.py`) and resolves it exclusively through this corrected chain:

```
BlueprintConformanceApplicationService
        |
        v
BlueprintApplicationService.get_approved_by_name(blueprint_name)
        |
        v
BlueprintRepository.get_approved_by_name(blueprint_name)
```

No import of `BlueprintSeeder`, `blueprint_seed.py`, or any seed/bootstrap module appears anywhere in
`application/blueprint_conformance.py`. This adds two artifacts to the authorized scope
(`blueprint_repository.py`, `application/blueprint_service.py` — both MODIFY) beyond the original
four-artifact draft; the Product Owner explicitly authorized this expansion as necessary for correct
architecture.

**Result model placement**: matches CDD-018 §14's explicit "application/-layer component" commitment.
Following `application/decision_engine.py`'s own established precedent (Pydantic/dataclass request,
response, and event types co-located in the same file as the orchestrating `DecisionApplicationService`
class), the result model (`RequirementStatus`, `RequirementResult`, `ConformanceResult`) is co-located
in the same new `application/blueprint_conformance.py` file as the orchestrating service — no separate
`domain/blueprint_conformance/` package is introduced, consistent with CDD-018 §5's own instruction to
avoid over-modeling a capability with no independent domain-service behavior beyond the comparison logic
itself.

## Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/infrastructure/persistence/blueprint_repository.py` | MODIFY | CDD-018 §13 (Blueprint version-selection rule) | Add `get_approved_by_name(blueprint_name: str) -> Blueprint \| None` to both `BlueprintRepository` (`Protocol`) and `BlueprintRepositoryImpl`: queries `blueprints` for `blueprint_name` matching and `governance_status = Approved`; returns `None` on zero matches; raises `ValidationException` on more than one match (CDD-018 §13's own "Precision clarification" — explicit failure, no arbitrary selection). | No change to `create()` or `get_by_id()`. No new query parameter beyond `blueprint_name`. No `tenant_id` involvement of any kind (Blueprint remains global, CDD-017 §9). No change to any other method's behavior. | Postgres integration test: single-Approved-match success, zero-match returns `None`, multiple-Approved-match raises explicitly. |
| `backend/app/application/blueprint_service.py` | MODIFY | CDD-018 §13 | Add `get_approved_by_name(blueprint_name: str) -> Blueprint \| None` to `BlueprintApplicationService`: a thin delegation to `BlueprintRepository.get_approved_by_name()`, mirroring the existing `get_by_id()` method's exact one-line-delegation shape. | No change to `get_by_id()` or the constructor. No new dependency. No business logic beyond delegation (matching the existing method's own minimalism). | Unit test using a `BlueprintRepository`-protocol-conforming fake, mirroring `test_blueprint_service.py`'s existing `test_get_by_id_delegates_to_the_repository` pattern exactly. |
| `backend/app/infrastructure/persistence/blueprint_conformance_context_store.py` | CREATE | CDD-018 §7 (tenant-context input contract) | `BlueprintConformanceContextStore`: tenant-scoped, read-only queries returning, for a given `tenant_id`: the set of distinct `entity_type_id` values present in that tenant's `enterprise_entities`, and the set of distinct `(relationship_type_id, from_entity_type_id, to_entity_type_id)` triples present in that tenant's `institutional_relationships` — sufficient to answer CDD-018 §8/§9's SATISFIED/MISSING questions by ID, not name. Follows `institutional_relationship_store.py`'s exact tenant-scoping and read-only discipline. | No mutation of any kind. No cross-tenant query (every query scoped by the caller-supplied `tenant_id`, following RFC-016's existing convention). No modification to `EnterpriseEntityRepository`, `InstitutionalRelationshipRepository`, `InstitutionalRelationshipStore`, or any ORM model. No name-based matching. No `assertions` table access of any kind (CDD-018 §6/§20). | Postgres integration test proving correct tenant scoping and correct ID-based type resolution. |
| `backend/app/application/blueprint_conformance.py` | CREATE | CDD-018 §8-§14 | `RequirementStatus` (`StrEnum`: `SATISFIED`/`MISSING`/`NOT_EVALUATED`), `RequirementResult`, `ConformanceResult` dataclasses (CDD-018 §11), and `BlueprintConformanceApplicationService` — given a `blueprint_name` and `tenant_id`, resolves the Blueprint via the corrected `BlueprintApplicationService.get_approved_by_name()` chain (no `BlueprintSeeder`/seed-module dependency of any kind), evaluates every `ConceptRequirement`/`RelationshipRequirement` against `BlueprintConformanceContextStore` output per CDD-018 §8/§9, reports every `InformationElementRequirement` as `NOT_EVALUATED` per CDD-018 §10, and derives the overall structural-conformance result per CDD-018 §11. | No `InformationElementRequirement` evaluation against real data of any kind. No source-system field inspection or mapping. No condition-expression model for `CONDITIONAL`. No numeric score. No persistence (no `session.add`/`commit`/`flush` call anywhere in this file). No modification to the Blueprint domain model, the Blueprint ORM, or any migration. No import of `blueprint_seed.py`, `BlueprintSeeder`, or any seed/bootstrap module (binding — Product Owner correction). No FastAPI import, no Pydantic import, no HTTP-layer object of any kind (matching G3's own `test_service_references_no_http_layer_object` precedent). | Unit tests using fake/stub `BlueprintApplicationService`-conforming and `BlueprintConformanceContextStore`-conforming test doubles — no PostgreSQL dependency for the orchestration/comparison logic itself. |
| `backend/app/tests/test_blueprint_conformance.py` | CREATE | CDD-011/CDD-012 test-authorization precedent, applied to this capability, following the established one-file-per-capability naming convention already used by `test_blueprint_service.py`/`test_decision_engine.py` | Evidence for: `ConceptRequirement` `SATISFIED`; `ConceptRequirement` `MISSING`; `RelationshipRequirement` `SATISFIED`; `RelationshipRequirement` `MISSING`; ontology-vocabulary existence alone does not satisfy a requirement; every `InformationElementRequirement` reports `NOT_EVALUATED`; a `REQUIRED` `InformationElementRequirement`'s `NOT_EVALUATED` status does not fail the overall structural result; `CONDITIONAL` requires no activation-expression engine; structurally-conformant overall result; structurally-non-conformant overall result; tenant isolation (a second tenant's context never affects or leaks into the first tenant's evaluation — proven at the `BlueprintConformanceContextStore` level, PostgreSQL-backed); deterministic result ordering across repeated evaluations; Blueprint-resolution determinism; non-conformance (`MISSING`) is a returned result, never an exception; evaluation failure (Blueprint unresolvable or ambiguous) is a raised exception, never a fabricated result; explainability evidence present and non-empty for every `MISSING`/`NOT_EVALUATED` result; no persistence side effect occurs (asserted directly against the test double's call log); no import of `blueprint_seed.py`/`BlueprintSeeder` anywhere in `application/blueprint_conformance.py` (source-scan test, matching G3's own architecture-boundary test precedent). | No test asserts against `assertions.predicate` or any source-system field name. | Direct test execution; PostgreSQL-dependent portions require `CTEC_TEST_DATABASE_URL`, following the established local-skip / CI-execute pattern; orchestration/comparison-logic portions require no database. |
| `backend/app/tests/test_blueprint_service.py` | MODIFY | CDD-018 §13 | Add unit-test evidence for `BlueprintApplicationService.get_approved_by_name()`'s delegation, mirroring the existing `get_by_id` delegation tests exactly. | No change to any existing test. No weakened assertion. | Direct test execution. |
| `backend/app/tests/test_blueprint_persistence_postgres.py` | MODIFY | CDD-018 §13 | Add Postgres-backed evidence for `BlueprintRepository.get_approved_by_name()`: single-match success, zero-match `None`, multiple-Approved-match explicit failure. | No change to any existing test. No weakened assertion. | Direct test execution (PostgreSQL-dependent). |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 (mechanism origin) + CDD-015 §35 (extension precedent, already reused by the G2/G3/G3.5 companions) | Extend `AUTHORIZED_CHANGED_PATHS` with exactly the three genuinely new paths above (`blueprint_conformance_context_store.py`, `application/blueprint_conformance.py`, `test_blueprint_conformance.py`). The other five modified paths in this table are already present in `AUTHORIZED_CHANGED_PATHS` from the G2/G3 companions and require no allowlist change (confirmed by direct inspection). | No assertion weakened. No wildcard path. No existing authorized path removed. No bypass of any architecture check. | Direct test execution. |

No other repository path is authorized. All unlisted paths are READ-ONLY under this report — in
particular, the Blueprint domain model, the Blueprint ORM, any Blueprint migration, `blueprint_seed.py`
(read from only insofar as its `CANONICAL_BLUEPRINT_NAME`/content conventions inform test fixtures —
never imported by production `application/blueprint_conformance.py` code), `EnterpriseEntityRepository`,
`InstitutionalRelationshipRepository`, `InstitutionalRelationshipStore`, CDD-017, CDD-018, and all four
prior companions are each confirmed unmodified by this authorization.

## Explicit exclusions (binding, restated from CDD-018)

- No `InformationElementRequirement` evaluated against real data, for any obligation value.
- No source-system field mapping, semantic interpretation, or profiling of any kind (Gate H's exclusive
  concern; no Gate H artifact of any kind is authorized by this report).
- No condition-expression or activation model for `CONDITIONAL` obligations.
- No numeric completeness/conformance score.
- No persistence of conformance results — no migration, no ORM, no conformance repository, no
  evaluation-history table.
- No FastAPI router, HTTP schema, or any API surface.
- No frontend, UI, or authoring surface.
- No new authentication or authorization scope, no Keycloak change.
- No modification to the Blueprint domain model, the Blueprint ORM, or any Blueprint migration.
- No `application/` → seed/bootstrap-infrastructure dependency of any kind (binding, Product Owner
  correction) — `blueprint_seed.py`/`BlueprintSeeder` remain exclusively bootstrap infrastructure.
- No modification to Entity Resolution, Governance Engine, Knowledge Engine, Decision Engine, Gate F's
  DRM/GRM, `runtime/orchestration.py`, `runtime/recovery.py`, or Ask CTEC's traversal code
  (`InstitutionalRelationshipStore` is read, never modified).

## Tenant-isolation requirement (binding)

Every query `BlueprintConformanceContextStore` issues MUST be scoped by exactly one caller-supplied
`tenant_id`, following the identical convention `institutional_relationship_store.py` already
establishes and RFC-016's tenant-qualified composite foreign keys already structurally enforce. No
evaluation may span or aggregate more than one tenant's context. No requirement result or its evidence
may reference or reveal an entity or relationship belonging to any tenant other than the one being
evaluated (CDD-018 §18). `get_approved_by_name()` involves no tenant scoping of any kind, since the
Blueprint definition itself remains global (CDD-017 §9).

## Structural-conformance semantics (binding, restated verbatim from CDD-018)

A `ConceptRequirement` is `SATISFIED` when at least one `enterprise_entities` row exists for the
evaluated tenant with `entity_type_id` matching the requirement's referenced entity type; `MISSING` when
no such row exists and the requirement's `obligation` is `REQUIRED` (CDD-018 §8). A
`RelationshipRequirement` is `SATISFIED` only when an actual `institutional_relationships` row exists for
the tenant with matching `relationship_type_id`, where the row's `from_entity_id` resolves to an
`enterprise_entities` row of the requirement's source concept's `entity_type_id`, and `to_entity_id`
resolves to one of the requirement's `target_entity_type_id`; `MISSING` when no such row exists and the
requirement's `obligation` is `REQUIRED` (CDD-018 §9). Ontology vocabulary existence alone (`EntityType`/
`RelationshipType` rows existing) is explicitly insufficient for either. The overall structural-
conformance result is a simple aggregate only: whether every `REQUIRED` `ConceptRequirement` and
`RelationshipRequirement` is `SATISFIED`, or whether one or more is `MISSING` (CDD-018 §11, quoted
verbatim — not inferred).

## InformationElementRequirement NOT_EVALUATED rule (binding, restated from CDD-018)

Every `InformationElementRequirement`, for every `obligation` value, reports `NOT_EVALUATED` and never
enters the overall structural-conformance aggregate (CDD-018 §10, §11).

## Explainability requirement (binding, restated from CDD-018)

Every requirement result carries plain-text evidence: for `MISSING`, the entity/relationship type name
and evaluated tenant context; for `NOT_EVALUATED`, a statement that evaluation is deferred to a future,
separately-governed capability (CDD-018 §12).

## Determinism requirement (binding, restated from CDD-018)

Repeated evaluation of the same Blueprint version against unchanged tenant context MUST yield identical
results, including stable, deterministic ordering of result collections; only the `evaluated_at`
metadata timestamp may differ and carries no semantic weight (CDD-018 §21).

## Failure semantics (binding, restated from CDD-018)

Non-conformance (`MISSING`) is a valid, successfully-returned result — never an exception. Evaluation
failure (the canonical Blueprint cannot be resolved by name, or name-plus-`Approved` resolution would be
ambiguous) MUST raise an explicit exception, never a fabricated or empty result (CDD-018 §22).

## Evidence obligations

Sixteen CDD-018 obligations, mapped to `test_blueprint_conformance.py` exactly as enumerated in that
artifact's row above, plus the two additional obligations for `get_approved_by_name()` mapped to
`test_blueprint_service.py`/`test_blueprint_persistence_postgres.py`. Eleven of the sixteen conformance
obligations are provable without PostgreSQL (orchestration/comparison logic against test doubles);
tenant isolation and real-store correctness require PostgreSQL, following the established local-skip /
CI-execute pattern used throughout G2/G3/G3.5.

## Regression obligations

No stale-expectation risk identified: this phase introduces no migration and no new table (CDD-018 §15
— ephemeral only), so `test_persistence_integration.py`'s `table_count == 57` and the three
`*_migration_and_immutability` tests' pinned Alembic head remain unaffected — confirmed by direct search
of the current test suite for any hardcoded inventory of `application/` modules, migration counts, or
service lists that this phase's new files would stale (none found beyond the runtime-architecture
allowlist itself, which this report's final artifact row already addresses).

## Gate H exclusion (binding)

No artifact in this table performs, enables, or scaffolds any source-system field mapping or
`InformationElementRequirement`-to-real-data resolution. Source-to-Blueprint Semantic Mapping remains
entirely unauthorized and out of scope for this report, matching CDD-018 §6/§20 exactly.

## Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the eight artifact paths authorized above without new Product
Owner authorization. If implementation discovers that any authorized artifact's Exclusions column
cannot be satisfied without touching an unlisted path (in particular: the Blueprint domain model/ORM,
any migration, any `application/` → seed/bootstrap dependency, or any Gate H concern), implementation
MUST STOP and report the exact blocker rather than silently expanding scope.

## Authorization

Authorized by CTEC Product Owner Manoj Nair: this artifact-authorization record satisfies CDD-018
§25's binding implementation precondition for exactly the structural-conformance-evaluation scope
listed above, per the Gate G G4 Artifact Discovery and the Product Owner's Blueprint-resolution
correction (P1 finding, resolved). CDD-018 and CDD-017 both remain unchanged. No implementation exists
yet — a separate, subsequent Product Owner authorization is required before any file listed above is
created or modified.
