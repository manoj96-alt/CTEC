# CDD-020 — I1 Semantic Coverage Evaluation Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `9beae9041090653008256467c4209d34f4ddbd91`

## 1. Authority and scope

CDD-020 §25 defers the exhaustive per-file artifact-authorization record for its initial implementation
phase to a separate, subsequent, CDD-Template-v2.2-compliant document, explicitly mirroring CDD-017's
G2/G3/G3.5, CDD-018's G4, and CDD-019's H1/H2/H3 companions' exact format and governance-cycle discipline
(CDD-020 §3, §25). This report is that record for **I1 only** — Semantic Coverage Evaluation, the smallest
implementation phase that establishes the governed application/domain capability CDD-020 §7-§13 defines.
It is a standalone companion to CDD-020, following the identical companion precedent already used seven
times across CDD-017, CDD-018, and CDD-019.

This record was produced through: I1 artifact discovery (§3 below, no CDD-020 governance gap, no
unresolved architecture decision, four-artifact proposed surface); a Product Owner review confirming
P0 = 0, P1 = 0, P2 = 0. No implementation exists yet, and none is authorized by this record's approval
alone — a separate, subsequent Product Owner implementation authorization is still required before any
file listed below is created or modified (CDD-020 §25, restated).

## 2. I1 objective (binding, restated from CDD-020 §1, §7)

For a given tenant and the Approved canonical Blueprint, determine, for every `InformationElementRequirement`,
whether the existing H2 `SemanticMappingResolutionApplicationService.resolve_approved_source_field(...)`
resolves an Approved `SemanticMapping` to governed `SourceField` evidence — classifying each requirement
`MAPPED` or `UNMAPPED` — while preserving that requirement's `obligation` unchanged and without touching
CDD-018's `NOT_EVALUATED` status in any way. I1 is not live data profiling, not H4, and not persisted.

## 3. Repository evidence inspected (binding, restated for the record)

- **Closest architectural precedent**: `BlueprintConformanceApplicationService`
  (`backend/app/application/blueprint_conformance.py`) — the only existing service with I1's exact shape:
  resolve an Approved Blueprint via a `BlueprintLookup`-shaped `Protocol`, iterate
  `concept.information_element_requirements`, produce one immutable result per requirement, aggregate into
  one immutable evaluation-result dataclass, all co-located in the same application-layer module (not the
  domain layer) — mirroring `RequirementStatus`/`RequirementResult`/`ConformanceResult`'s own co-location
  choice exactly. I1 follows this pattern precisely, substituting H2 resolution for context-store
  comparison and `MAPPED`/`UNMAPPED` for `SATISFIED`/`MISSING`/`NOT_EVALUATED`.
- **H2 dependency shape**: `SemanticMappingResolutionApplicationService.resolve_approved_source_field(
  information_element_requirement_id: UUID, tenant_id: str) -> SemanticMappingResolution | None`
  (`backend/app/application/semantic_mapping_resolution.py`, unmodified) — positional-argument signature,
  confirmed by direct read; I1 calls this exactly, never the repository layer beneath it.
- **`SemanticMappingResolution` shape**: frozen dataclass, exactly nine fields (`semantic_mapping_id`,
  `source_field_id`, `source_object_id`, `source_system_id`, `information_element_requirement_id`,
  `created_by`, `created_on`, `modified_by`, `modified_on`), defined in
  `backend/app/infrastructure/persistence/semantic_mapping_repository.py` (unmodified) — I1 reuses this
  type directly as its own MAPPED-case provenance field rather than duplicating any of its fields,
  satisfying CDD-020 §8's "use existing IDs/value objects where possible" and "do not duplicate SourceField
  metadata unnecessarily."
- **`InformationElementRequirement`/`Obligation` shape**: `backend/app/domain/blueprint/model.py` (frozen
  dataclass; `Obligation` is a `StrEnum` of `REQUIRED`/`CONDITIONAL`/`OPTIONAL`) — confirmed unmodified,
  read-only dependency.
- **No wiring artifact requires modification**: direct repository search (`grep` for
  `BlueprintApplicationService(`, `BlueprintConformanceApplicationService(`,
  `SemanticMappingResolutionApplicationService(`) proves none of these three precedent application
  services is instantiated in `backend/app/core/dependency_container.py`, `backend/app/main.py`, or any
  other composition-root file — each is constructed directly by its own tests and, for H2, by
  `demo_semantic_mapping_seeder.py`. This settles CDD-020 §21's "no API" stance structurally: I1 requires
  **zero** change to any dependency-injection/composition artifact, because none of its precedent siblings
  are wired into one either.
- **Test-double convention**: `test_semantic_mapping_resolution.py` and `test_blueprint_conformance.py`
  both use hand-written `Protocol`-conforming fake classes (no mocking framework), asserting exact
  argument pass-through and exact return-value/exception pass-through — no PostgreSQL dependency for
  orchestration-logic proof, since each real dependency (`BlueprintRepositoryImpl`,
  `SemanticMappingRepositoryImpl`) is already separately proven against Postgres elsewhere. I1's unit
  tests follow this identical convention.
- **H3 fixture reuse**: `test_demo_semantic_mapping_seeder_postgres.py` (CDD-019 H3, unmodified) already
  establishes the exact deterministic dataset I1's acceptance evidence needs (`BlueprintSeeder(session).load()`
  + `DemoSemanticMappingSeeder(session).seed()`, both existing and unmodified) and demonstrates the import
  paths (`CANONICAL_BLUEPRINT_NAME`, `BOOTSTRAP_DEMO_TENANT_ID`) I1's own new Postgres test reuses without
  modifying that file — keeping I1's artifact list entirely self-contained within CDD-020's own authority,
  touching zero CDD-019-owned file.
- **`AUTHORIZED_CHANGED_PATHS` mechanism**: `backend/app/tests/test_runtime_architecture.py` — confirmed
  unchanged mechanism (`assert changed <= AUTHORIZED_CHANGED_PATHS`), extended identically by every prior
  Gate G/H phase; I1 extends it by exactly three new path strings.

## 4. Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/application/semantic_coverage_evaluation.py` | CREATE | CDD-020 §7-§13 | `SemanticCoverageEvaluationApplicationService`, constructor-injected with `blueprint_service: BlueprintLookup` and `resolver: MappingResolver` (two locally-defined, structurally-typed `Protocol`s — no cross-import of `blueprint_conformance.py` or `semantic_mapping_resolution.py`'s classes). Exactly one public method: `evaluate(self, *, blueprint_name: str, tenant_id: str) -> SemanticCoverageEvaluationResult`. Resolves the Blueprint via `blueprint_service.get_approved_by_name(blueprint_name)`, raising `ValidationException` if `None` (mirroring `BlueprintConformanceApplicationService.evaluate`'s identical precedent); iterates every `concept.information_element_requirements` entry; for each, calls `resolver.resolve_approved_source_field(element.information_element_requirement_id.value, tenant_id)`; classifies `CoverageStatus.MAPPED` if the call returns non-`None`, else `CoverageStatus.UNMAPPED`; builds one `InformationElementCoverageResult` per element carrying `information_element_requirement_id`, `obligation` (passthrough, unmodified), `status`, and `resolution` (the exact `SemanticMappingResolution` returned, or `None`); returns one `SemanticCoverageEvaluationResult` (`blueprint_id`, `blueprint_version_number`, `tenant_id`, `evaluated_at`, `information_element_results` — sorted by `information_element_requirement_id`, mirroring `ConformanceResult`'s identical determinism precedent). Also defines: `CoverageStatus(StrEnum)` with exactly `MAPPED`/`UNMAPPED`; `InformationElementCoverageResult` (frozen dataclass, slots); `SemanticCoverageEvaluationResult` (frozen dataclass, slots); `BlueprintLookup`/`MappingResolver` (`Protocol`s). | No `overall_conformant`, score, percentage, count, or any aggregate field on `SemanticCoverageEvaluationResult`. No third `CoverageStatus` value. No field on `InformationElementCoverageResult` beyond the four named. No catching, suppressing, or converting any exception raised by `resolver`. No import of `BlueprintConformanceApplicationService`, `blueprint_conformance.py`'s types, or any persistence/ORM/HTTP module. No `create`/`approve`/`retire`/seed method. No source-value read. No caching or memoization across calls. | Application-service unit test (test-double `BlueprintLookup`/`MappingResolver`, no DB); Postgres acceptance test. |
| `backend/app/tests/test_semantic_coverage_evaluation.py` | CREATE | CDD-020 §7-§13 | Unit tests using hand-written `BlueprintLookup`/`MappingResolver`-conforming fakes (no PostgreSQL dependency, mirroring `test_semantic_mapping_resolution.py`'s and `test_blueprint_conformance.py`'s fake style exactly): (1) `MAPPED` classification — a fake resolver returning a constructed `SemanticMappingResolution` yields `status == MAPPED` with `resolution` identical to the returned object; (2) `UNMAPPED` classification — a fake resolver returning `None` yields `status == UNMAPPED` with `resolution is None`; (3) ambiguity/failure propagation — a fake resolver raising `ValidationException` propagates that exact exception unchanged, uncaught, unconverted; (4) obligation passthrough — each of `REQUIRED`/`CONDITIONAL`/`OPTIONAL` is preserved unchanged in the corresponding result; (5) all six `obligation`×`CoverageStatus` combinations are structurally representable with no special-casing (parametrized construction over a Blueprint fixture with six elements, one per combination); (6) `tenant_id` passed through unchanged to `resolver.resolve_approved_source_field`'s second positional argument, recorded and asserted via the fake's call log; (7) no mutation of the input `Blueprint`/`InformationElementRequirement` objects (identity/field equality asserted before and after `evaluate()`); (8) Blueprint-not-found raises `ValidationException` explicitly (mirrors `test_blueprint_not_found_raises_explicit_failure`'s exact precedent); (9) deterministic result ordering by `information_element_requirement_id` (mirrors `test_deterministic_result_ordering`'s exact precedent); (10) the service exposes no public method beyond `evaluate` (mirrors H2's `test_service_exposes_no_method_beyond_resolve_approved_source_field`'s exact precedent); (11) the module contains no persistence/ORM import and no HTTP-layer import (mirrors `test_service_module_contains_no_persistence_calls`/`test_service_module_references_no_http_layer_object`'s exact precedent). | No PostgreSQL dependency. No test of `BlueprintRepositoryImpl`'s or `SemanticMappingRepositoryImpl`'s internal query logic (covered elsewhere already). No test asserting an aggregate/score field (none exists). | Direct test execution. |
| `backend/app/tests/test_semantic_coverage_evaluation_postgres.py` | CREATE | CDD-020 §16, §27 items 2, 3, 8 | Postgres-backed acceptance evidence, composing the real, unmodified `BlueprintApplicationService(repository=BlueprintRepositoryImpl(session))` and the real, unmodified `SemanticMappingResolutionApplicationService(repository=SemanticMappingRepositoryImpl(session))` into the new `SemanticCoverageEvaluationApplicationService`, seeded via the existing, unmodified `BlueprintSeeder(session).load()` and `DemoSemanticMappingSeeder(session).seed()` (CDD-019 H3, reused by call only): (1) H3 acceptance — `evaluate(blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID)` classifies `Supplier Legal Name` (`obligation == REQUIRED`) as `MAPPED` with `resolution` provenance matching the seeded `H3 Demo ERP`/`LFA1`/`LFA1-NAME1` record exactly, and classifies `Risk Event Severity` (`obligation == CONDITIONAL`) as `UNMAPPED` with `resolution is None`; (2) tenant isolation — evaluating with a freshly-generated, non-demo `tenant_id` classifies both elements `UNMAPPED` (H3's demo-tenant data does not leak, mirroring `test_resolution_does_not_cross_tenant_boundaries`'s exact pattern); (3) determinism — two sequential `evaluate()` calls with identical arguments return equal results (mirrors `test_resolution_is_deterministic_across_repeated_calls`'s exact pattern). | No test asserts against H4/live-source-value behavior. No test bypasses `BlueprintApplicationService` or `SemanticMappingResolutionApplicationService` to query persistence directly. No modification to `BlueprintSeeder`, `DemoSemanticMappingSeeder`, or any file they depend on. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 mechanism, reused by every prior Gate G/H phase | Add exactly three new string entries to the existing `AUTHORIZED_CHANGED_PATHS` set: `"backend/app/application/semantic_coverage_evaluation.py"`, `"backend/app/tests/test_semantic_coverage_evaluation.py"`, `"backend/app/tests/test_semantic_coverage_evaluation_postgres.py"`. | No other entry added, removed, or altered. No change to the subset-comparison logic itself. No wildcard, no directory-level entry. | Direct test execution. |

No other repository path is authorized. In particular: `blueprint_service.py`, `blueprint_conformance.py`,
`semantic_mapping_resolution.py`, `semantic_mapping_repository.py`, `blueprint_repository.py`,
`blueprint_seed.py`, `demo_semantic_mapping_seeder.py`, any domain model file (`domain/blueprint/model.py`,
`domain/semantic_mapping/*`, `domain/integration/source_field.py`), any ORM model file, any migration
file, `dependency_container.py`, `app/main.py`, any API/router/schema file, any frontend file, and any
H3/H4 artifact are **not** authorized for modification.

## 5. Application/domain contract (binding)

`SemanticCoverageEvaluationApplicationService` performs no persistence of its own, matching every existing
application-service precedent in this repository. It depends on exactly two structurally-typed `Protocol`s
(`BlueprintLookup`, `MappingResolver`), never on a concrete repository or ORM class directly, mirroring
`BlueprintConformanceApplicationService`'s identical two-`Protocol` dependency shape. `CoverageStatus`,
`InformationElementCoverageResult`, and `SemanticCoverageEvaluationResult` are co-located in the same
module as the service that produces them, matching `RequirementStatus`/`RequirementResult`/
`ConformanceResult`'s identical co-location precedent — not placed in the domain layer, not placed in the
persistence layer.

## 6. `MAPPED`/`UNMAPPED` contract (binding, restated from CDD-020 §8-§9)

`status` is `CoverageStatus.MAPPED` if and only if `resolver.resolve_approved_source_field(...)` returns a
non-`None` `SemanticMappingResolution`; `CoverageStatus.UNMAPPED` if and only if it returns `None`. This
pairing is structural and MUST be tested directly: `resolution is not None` if and only if
`status is CoverageStatus.MAPPED`. No third `CoverageStatus` value exists or may be introduced by I1.
`resolution` is the exact object H2 returns, unmodified, unwrapped, un-transformed — never a
re-constructed or partial copy.

## 7. Obligation passthrough contract (binding, restated from CDD-020 §10)

`InformationElementCoverageResult.obligation` is set to `element.obligation` exactly, read once, never
compared against, branched on, or used to alter `status`'s computation in any way. All six
`obligation`×`CoverageStatus` combinations (`REQUIRED`+`MAPPED`, `REQUIRED`+`UNMAPPED`,
`CONDITIONAL`+`MAPPED`, `CONDITIONAL`+`UNMAPPED`, `OPTIONAL`+`MAPPED`, `OPTIONAL`+`UNMAPPED`) MUST be
producible with zero special-casing anywhere in `evaluate()`'s control flow — there is no
`if obligation is CONDITIONAL` branch anywhere in the authorized implementation.

## 8. `NOT_EVALUATED` firewall (binding, restated from CDD-020 §6)

I1 imports nothing from `blueprint_conformance.py`, calls no method on
`BlueprintConformanceApplicationService`, and produces no field, value, or side effect that touches
`RequirementStatus` or CDD-018's evaluation pipeline in any way. `InformationElementRequirement` evaluation
remains exactly `NOT_EVALUATED`, entirely untouched, for the full duration of this report's authority.
`CoverageStatus.MAPPED`/`UNMAPPED` and CDD-018's `NOT_EVALUATED` coexist as independent facts about the
same requirement; I1 never reads, writes, or references `RequirementStatus`.

## 9. H2 reuse / single-path contract (binding, restated from CDD-020 §13)

`resolver.resolve_approved_source_field(...)` — satisfied at runtime exclusively by the real, unmodified
`SemanticMappingResolutionApplicationService` — is the **sole** mapping-resolution call I1 performs. No
direct `SemanticMapping`/`SemanticMappingORM`/`SourceField`/`SourceFieldORM` query, no second resolution
mechanism, no Approved-filtering or tenant-filtering re-implementation, no candidate selection, no
field-name/label inference, no fallback or default mapping is authorized anywhere in
`semantic_coverage_evaluation.py`. H2's ambiguity-raise and zero-match-returns-`None` behaviors propagate
to I1's result unchanged (§10 below).

## 10. Tenant-isolation contract (binding, restated from CDD-020 §16)

`evaluate(*, blueprint_name, tenant_id)`'s `tenant_id` parameter is passed as the exact second positional
argument to every `resolver.resolve_approved_source_field(...)` call, once per `InformationElementRequirement`,
never batched, cached, or reused across a different `tenant_id`. I1 introduces no `tenant_id` column, no
tenant-scoped cache, and no cross-tenant aggregation of any kind — the existing
`SemanticMapping → SourceField → SourceObject → tenant_id` ownership chain, and H2's own proven
tenant-isolation guarantee, are inherited unmodified.

## 11. Failure/ambiguity contract (binding, restated from CDD-020 §23)

If `resolver.resolve_approved_source_field(...)` raises (H2's defensive ambiguity path), `evaluate()` MUST
NOT catch, suppress, or convert that exception into `CoverageStatus.UNMAPPED` or any other fallback result
— it propagates unchanged to the caller, exactly matching CDD-020 §23's binding instruction and H2's own
companion's identical precedent. This is a **must-test** behavior (Artifact 1's row, exclusion column).

## 12. Result lifecycle / non-persistence contract (binding, restated from CDD-020 §15, §25)

`SemanticCoverageEvaluationResult` and `InformationElementCoverageResult` are calculated on demand,
returned as plain immutable (`frozen=True, slots=True`) dataclasses, never written to any table,
repository, cache, or history store. `evaluate()` performs no `INSERT`/`UPDATE`/`DELETE` of any kind — no
artifact in this authorization introduces persistence, a migration, a new table, or a new column.

## 13. H3 acceptance evidence (binding target, restated from CDD-020 §27 item 2)

Against the existing, unmodified H3 deterministic dataset (`BlueprintSeeder` + `DemoSemanticMappingSeeder`,
both reused by call only):

| Element | `obligation` | H2 resolution | I1 `status` | CDD-018 status |
|---|---|---|---|---|
| `Supplier Legal Name` | `REQUIRED` | Approved mapping to `H3 Demo ERP`/`LFA1`/`LFA1-NAME1` | `MAPPED` | `NOT_EVALUATED` (unchanged, untouched by I1) |
| `Risk Event Severity` | `CONDITIONAL` | none | `UNMAPPED` | `NOT_EVALUATED` (unchanged, untouched by I1) |

`Risk Event Severity`'s `UNMAPPED` result means only a semantic/mapping coverage gap (CDD-020 §9, §10) —
never condition-active/inactive, never applicable/not-applicable, never source-data-absent, never
CDD-018-`MISSING`.

## 14. Security/API/frontend exclusions (binding, restated from CDD-020 §20-§21)

No public HTTP API, API schema, or FastAPI router. No authentication/authorization/Keycloak change. No
frontend, UI, or authoring surface of any kind. No dependency-injection/composition-root change (§3
above — proven unnecessary by direct repository evidence).

## 15. H4 exclusion (binding, restated from CDD-020 §18)

No live source-system connectivity, source-field value reading, completeness/presence judgment, freshness
evaluation, validity evaluation, distribution analysis, or data-quality evaluation of any kind is
authorized by any artifact in this report. `resolver.resolve_approved_source_field(...)`'s return value —
governed metadata identifying *that* a mapping exists, never the field's live value — is the only evidence
I1 ever touches.

## 16. Gate J/N/P boundary (binding, restated from CDD-020 §19)

No impact, severity, priority, or remediation-recommendation language. No trust/staleness/disconnection/
confidence overlay. No modification to, or authorization for, Ask CTEC or any other consumer to reference
this capability's output. I1 produces a classification result; it does not decide what any future
capability does with it.

## 17. Migration determination (binding)

**No migration is authorized or required.** I1 introduces zero schema change, zero new table, zero new
column, zero new index, zero new constraint. Every artifact above is either an application-layer Python
module or a test file.

## 18. Acceptance criteria

1. `evaluate()` classifies every `InformationElementRequirement` `MAPPED` or `UNMAPPED` strictly by
   delegating to `resolver.resolve_approved_source_field(...)`, with no independent resolution logic.
2. The H3 acceptance table in §13 above is proven against real PostgreSQL exactly as stated.
3. Cross-tenant classification is structurally impossible, proven against real PostgreSQL.
4. `InformationElementRequirement` evaluation status (CDD-018) is unchanged, unread, unwritten by any I1
   artifact.
5. No `Blueprint`, `ConceptRequirement`, `RelationshipRequirement`, `InformationElementRequirement`,
   `SourceField`, `SemanticMapping`, H2 resolver, or any of their repositories/application services is
   modified by any artifact in this report.
6. `SemanticCoverageEvaluationResult`/`InformationElementCoverageResult` carry no numeric score,
   percentage, impact, severity, or remediation field.
7. No HTTP endpoint, authentication check, or scope enforcement exists in any I1 artifact.
8. Resolving the same tenant/Blueprint pair against unchanged data twice yields an equal result
   (`evaluate()` called twice; results compare equal field-by-field).
9. `test_runtime_architecture.py`'s `AUTHORIZED_CHANGED_PATHS` subset-comparison test, and all other
   architecture-drift/dependency/secret checks, pass with zero unauthorized diff.

## 19. Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the four artifact paths authorized above without new Product Owner
authorization. If implementation discovers that any authorized artifact's Exclusions column cannot be
satisfied without touching an unlisted path (in particular: `dependency_container.py`, `app/main.py`,
`blueprint_conformance.py`, any Blueprint/H1/H2/H3 artifact, or any H4/Gate-J/N/P concern), implementation
MUST STOP and report the exact blocker rather than silently expanding scope.

## 20. Publication/approval state

This document is an **approved artifact-authorization companion**, published to `APPROVED ARTIFACT
AUTHORIZATION` state following the identical Product Owner review-and-approval cycle every prior companion
(CDD-017 G2/G3/G3.5, CDD-018 G4, CDD-019 H1/H2/H3) underwent — discovery (§3), a content review confirming
P0 = 0, P1 = 0, P2 = 0, and Product Owner approval. Approval of this record governs exactly the artifact
sandbox in §4 above; it does **not** itself authorize implementation of any artifact listed there — a
separate, subsequent Product Owner implementation authorization remains required (§1, §19) before any file
listed above is created or modified.
