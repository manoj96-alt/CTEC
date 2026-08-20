# CDD-019 — H2 Semantic Mapping Resolution Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `25cac548e7826419c8beb23288ec95fb3d22c15c`

## Decision

CDD-019 §25 defers the exhaustive per-file artifact-authorization record for each of its H1-H3
implementation phases to a separate, subsequent, CDD-Template-v2.2-compliant document, mirroring
CDD-017's G2/G3/G3.5 and CDD-018's G4 companions' exact format, and mirroring H1's own companion for
this same CDD-019. This report is that record for **H2 only** — Internal Mapping Resolution Service. It
is a standalone companion to CDD-019, following the identical companion precedent already used five
times across CDD-017, CDD-018, and CDD-019 H1.

This record was produced through: H2 artifact discovery (verdict A, no CDD-019 governance gap, no
unresolved architecture decision, 6-artifact proposed surface); a Product Owner content review that
found one P1 (an unauthorized `governance_status` field on the proposed result type) and one
non-blocking P2 (repository method argument-order observation); a remediation closing the P1 by removing
exactly the one unauthorized field; and a final Product Owner re-review confirming P0 = 0, P1 = 0, P2 = 1
(accepted as-is). No implementation exists yet.

## Discovery findings (binding, restated for the record)

- **Repository/Protocol pattern**: `SemanticMappingRepository`'s `Protocol` was deliberately frozen to
  `create`/`get_by_id` in H1, with H1's own companion explicitly naming and declining to authorize
  `get_by_information_element_requirement(...)` and other resolution-shaped methods, reserving that
  capability for H2's own future, separately-authorized companion — this report is that authorization.
- **Architectural pattern chosen**: governed `Protocol` expansion (one new method on
  `SemanticMappingRepository`) plus a thin, constructor-injected application service delegating to it —
  the only pattern this codebase has used for "a later phase needs a new read capability over an earlier
  phase's data" (`BlueprintRepository.get_approved_by_name`, G4). A separate resolver bypassing the
  repository layer was considered and rejected: it would duplicate `SemanticMappingRepositoryImpl`'s
  existing join logic and violate the single-source-of-truth-per-table discipline.
- **Result-type placement**: `SemanticMappingResolution`, a frozen dataclass, is defined inside
  `semantic_mapping_repository.py` (the persistence layer that performs the join producing it) rather
  than the domain layer — mirroring `blueprint_conformance.py`'s precedent of co-locating purpose-built
  result dataclasses (`RequirementResult`, `ConformanceResult`) with the service/layer that produces
  them, not the domain model.
- **Field-scope correction (P1 remediation)**: the originally proposed `SemanticMappingResolution`
  included `governance_status`, found during Product Owner review to be ungrounded in CDD-019 §14's
  literal text and redundant by construction (the method's own contract guarantees every returned row is
  `Approved`). Removed. The authorized field set below is final.

## Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/infrastructure/persistence/semantic_mapping_repository.py` | MODIFY | CDD-019 §14, §16 | Add exactly one new `Protocol` method: `get_approved_by_information_element_requirement(self, information_element_requirement_id: UUID, tenant_id: str) -> SemanticMappingResolution \| None`, implemented via one query joining `SemanticMappingORM → SourceFieldORM → SourceObjectORM`, filtered on `information_element_requirement_id`, `governance_status == Approved`, and `SourceObjectORM.tenant_id`. Add a frozen dataclass `SemanticMappingResolution` exposing **exactly** these nine fields: `semantic_mapping_id`, `source_field_id`, `source_object_id`, `source_system_id`, `information_element_requirement_id`, `created_by`, `created_on`, `modified_by`, `modified_on`. | No `find(...)`, `search(...)`, arbitrary status filter, list-all, or arbitrary-combination lookup method. No `governance_status`, confidence, ranking, transformation, semantic-inference, source-value, satisfaction-status, or Blueprint-Conformance field on `SemanticMappingResolution`. No change to `create`'s or `get_by_id`'s existing signature or behavior. No `UnitOfWork`/`REPOSITORY_TYPES` registration. Zero-match → `None`. Defensive ambiguity (>1 matching row) → raise `ValidationException`, never silent first/newest/oldest/highest-ranked selection. | Repository unit test; Postgres integration test. |
| `backend/app/application/semantic_mapping_resolution.py` | CREATE | CDD-019 §14 | `SemanticMappingResolutionApplicationService`, constructor-injected with `repository: SemanticMappingRepository` (direct import, matching `BlueprintApplicationService`'s shape). Exactly one public method: `resolve_approved_source_field(self, information_element_requirement_id: UUID, tenant_id: str) -> SemanticMappingResolution \| None` — a one-line delegation to the repository method above, with no additional logic. | No API/router/schema import. No orchestration of other application services. No `create`/`approve`/`retire`/seed method. No source-value read. No requirement-satisfaction evaluation. No `BlueprintConformanceApplicationService` import or call. | Application-service unit test (test-double repository, no DB). |
| `backend/app/tests/test_semantic_mapping_persistence.py` | MODIFY | CDD-019 §14 | Add one structural test asserting `SemanticMappingResolution.__dataclass_fields__` equals exactly the nine authorized field names above. | No PostgreSQL dependency. No assertion referencing `governance_status` or any other unauthorized field. | Direct test execution. |
| `backend/app/tests/test_semantic_mapping_persistence_postgres.py` | MODIFY | CDD-019 §14, §11, §18 | Postgres-backed cases proving: (1) an Approved mapping resolves with correct provenance; (2) a Draft-only mapping does not resolve (`None`); (3) a Retired-only mapping does not resolve (`None`); (4) zero mappings for a requirement returns `None`; (5) tenant isolation — an Approved mapping under tenant A is not returned when resolving with tenant B's id (`None`, not an exception); (6) ambiguity defense — using the same raw-ORM-bypass technique H1 used to prove the partial unique index, two Approved rows for the same requirement/tenant cause `ValidationException`; (7) determinism — two sequential calls with identical arguments return equal results. | No test asserts against `governance_status` or any other unauthorized field. No test exercises H3/H4 concerns. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_semantic_mapping_resolution.py` | CREATE | CDD-019 §14 | Application-service tests using a test-double repository (no DB): the service delegates with the exact arguments passed; returns exactly what the repository returns, unmodified, including `None`; propagates a repository-raised `ValidationException` unchanged; exposes no method beyond `resolve_approved_source_field`. | No PostgreSQL dependency. No test of repository-internal query logic (covered by the artifact above). | Direct test execution. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 mechanism, reused by every prior Gate G/H phase | Add exactly two new string entries to the existing `AUTHORIZED_CHANGED_PATHS` set: `"backend/app/application/semantic_mapping_resolution.py"` and `"backend/app/tests/test_semantic_mapping_resolution.py"`. | No other entry added, removed, or altered. No change to the subset-comparison logic itself. No wildcard, no directory-level entry. | Direct test execution. |

No other repository path is authorized. All unlisted paths are READ-ONLY under this report. In
particular: `domain/semantic_mapping/model.py`, `domain/integration/source_field.py`,
`source_field_repository.py`, any ORM model file, any migration file, `models/__init__.py`,
`repositories/__init__.py`, `unit_of_work.py`, any Blueprint or Blueprint Conformance artifact, and any
H3/H4 artifact are **not** authorized for modification.

## Explicit exclusions (binding, restated from CDD-019)

No public HTTP API, API schema, or FastAPI router (§14, §21). No authentication/authorization change
(§14, §21). No `BlueprintConformanceApplicationService` integration of any kind (§14). No modification to
`Blueprint`, `ConceptRequirement`, `InformationElementRequirement`, the Blueprint domain model, the
Blueprint ORM, any Blueprint migration, `BlueprintRepository`, or `BlueprintApplicationService`. No
change to `InformationElementRequirement` evaluation status — it remains `NOT_EVALUATED`. No live
source-system connectivity, source-field value reading, or evidence-of-presence evaluation of any kind.
No mapping seeder, seeded `SemanticMapping`, demo topology, or deterministic demonstration data (H3 —
reserved). No modification to `SourceField`, `SemanticMapping`, their domain models, ORM models, or
migration (H1 — closed and frozen). No new ontology concept or relationship. No frontend or UI of any
kind.

## Tenant-isolation requirement (binding)

Tenant identity is resolved exclusively by walking `SemanticMapping.source_field_id →
SourceField.source_object_id → SourceObject.tenant_id`, inside the new query's own join — never stored
redundantly on `SemanticMapping` or `SourceField` (neither has a `tenant_id` column), never independently
asserted, never accepted as a value that overrides the join-derived result. A resolution request whose
`tenant_id` does not match the resolved mapping's actual tenant returns `None` — non-resolution, not an
exception, not a cross-tenant fallback of any kind.

## Resolution semantics (binding, restated from CDD-019 §14)

- **Approved-only**: only `governance_status = Approved` `SemanticMapping` rows are eligible; `Draft`,
  `Retired`, and `Archived` rows are never returned, never counted, regardless of any other field.
- **Zero-match**: no eligible row → `None`. A valid, successful outcome, never an exception (CDD-018
  §22 precedent, restated).
- **Ambiguity**: more than one eligible row (structurally excluded by H1's write-time enforcement;
  defensive only) → raise `ValidationException` explicitly. Never a silent first/newest/oldest/
  highest-ranked/arbitrary-row selection.
- **Determinism**: identical input yields an identical result on repeated calls, guaranteed by H1's
  write-time uniqueness rules, not by any ranking or scoring (none exists, none authorized).
- **Read-only**: no artifact in this authorization performs, triggers, or enables any
  `INSERT`/`UPDATE`/`DELETE`.

## Failure semantics (binding, restated from CDD-019 §23)

If the new repository method's query returns more than one row, it MUST raise `ValidationException`
explicitly and MUST NOT return any of the matched rows — consistent with CDD-017 §7's, CDD-018 §22's,
CDD-019 §23's, and the H1 companion's identical binding instructions. This is a defensive path only: H1's
`_raise_if_ambiguous` (source-side DB partial index + target-side advisory-lock-guarded application
check) already makes true ambiguity structurally unreachable through `create()`.

## Evidence obligations

Real-PostgreSQL evidence is required for: Approved-mapping resolution correctness (provenance fields
match seeded data exactly); Draft-exclusion; Retired-exclusion; zero-match; tenant isolation (two
distinct tenant fixtures); the defensive ambiguity path (via raw-ORM bypass, mirroring H1's own precedent
for proving DB-level enforcement); and deterministic repeated-call equality. Application-service
delegation evidence (argument pass-through, return-value pass-through, exception pass-through,
exact-method-surface check) does not require PostgreSQL — a test-double repository is sufficient and
preferred, avoiding unnecessary evidence duplication across layers.

## Regression obligations

This phase introduces no migration and no schema change, unlike H1. The sole regression surface is
`semantic_mapping_repository.py`'s existing `create`/`get_by_id` behavior, which this report requires
remain provably unchanged (pre-existing test assertions in `test_semantic_mapping_persistence*.py` must
continue passing unmodified in every respect other than the additions authorized above).

## H1 contract preservation (binding)

Explicitly protected, unmodified by this authorization: `SourceField` physical identity
(`UniqueConstraint(source_object_id, field_label)`); `SemanticMapping` lifecycle states; Approved
bidirectional 1:1 (source-side DB partial index and target-side advisory-lock-guarded application check);
the tenant-isolation mechanism; `create()`'s exact behavior and signature; `get_by_id()`'s exact behavior
and signature; the H1 schema (both tables, all columns, all constraints, both indexes); the H1 migration.
This authorization is strictly additive: one new method, zero changes to any existing method, column,
constraint, index, or migration.

## H3/H4 exclusion (binding)

No artifact in this table performs, enables, or scaffolds: any mapping seeder, seeded `SemanticMapping`,
demo topology, or deterministic demonstration workflow (H3 — reserved for its own future, separately-
authorized companion); any live source-field value reading, connector integration, information-element
completeness evaluation, `SATISFIED`/`MISSING` evaluation, or `BlueprintConformanceApplicationService`
modification (H4 — entirely outside CDD-019's authority under any circumstance).
`InformationElementRequirement` evaluation remains exactly `NOT_EVALUATED`, unchanged, for the full
duration of this report's authority.

## Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the six artifact paths authorized above without new Product Owner
authorization. If implementation discovers that any authorized artifact's Exclusions column cannot be
satisfied without touching an unlisted path (in particular: `models/__init__.py`,
`repositories/__init__.py`, `unit_of_work.py`, any Blueprint/Blueprint-Conformance artifact, any H3/H4
concern, or any additional repository/service method), implementation MUST STOP and report the exact
blocker rather than silently expanding scope.

## Authorization

Authorized by CTEC Product Owner Manoj Nair: this artifact-authorization record satisfies CDD-019 §25's
binding implementation precondition for exactly the H2 — Internal Mapping Resolution Service scope listed
above, per the Gate H2 artifact discovery (verdict A), a Product Owner content review (P1×1, P2×1
findings), a remediation closing the sole P1, and a final Product Owner re-review confirming P0 = 0,
P1 = 0, P2 = 1 (accepted as-is). CDD-019 remains unchanged. No implementation exists yet — a separate,
subsequent Product Owner authorization is required before any file listed above is created or modified.
H3 and H4 remain entirely outside this report's authority and require their own future, separately-
authorized companions.
