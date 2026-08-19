# CDD-017 — G3 Internal Blueprint Application Service Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `1d28e558afb9d74023ff94bca60037324f04206d`

## Decision

CDD-017 §17 and §19 defer the exhaustive per-file artifact-authorization record for Gate G's
implementation phases to separate, subsequent, CDD-Template-v2.2-compliant documents, mirroring
CDD-015 §33's exact format — binding: "Implementation MUST NOT proceed against §6's model without
that separate, subsequent artifact-authorization record existing first." This precondition applies
identically to each new implementation phase, not only the first (G2); this report is that record for
G3. It follows the same standalone-companion-document precedent already used for CDD-015 (three merged
companions: PR #69, PR #71, PR #73), for CDD-010/CDD-012 (the "-AUTHORIZATION"/"-ALLOWLIST" companion
pattern), and for this CDD's own G2 companion
(`CDD-017-G2-Persistence-Domain-Artifact-Authorization.md`, merged via PR #78): a standalone companion
document to an already-FROZEN CDD, not an edit to CDD-017 itself, and not a new architecture baseline.

This report authorizes exactly the artifact scope the Gate G G3 Artifact-Scope Discovery produced and
the Product Owner approved — no artifact added, removed, renamed, or expanded beyond that reviewed
scope. It introduces no new architecture: every artifact below traces to CDD-017's already-authorized
§3 ("a future, separately-implemented backend read *service* (not a public API)") and §14 (the
internal-read-surface boundary). G3 implements an internal application-layer consumption boundary over
the already-merged G2 persistence/domain capability only — no canonical seed content, no conformance
logic, no read API, no frontend, matching CDD-017 §13's seeding deferral and §14's read-surface
deferral exactly.

## Service location correction (binding, restated for the record)

G3's Product Owner discovery and decision sequence originally considered
`backend/app/domain/blueprint/service.py` as the service location. Architecture analysis established that, while technically
permitted by the currently enforced `test_domain_has_no_forbidden_dependencies_or_artifact_classes`
check (`backend/app/tests/test_domain_foundation.py`, scoped only to `domain/foundation`,
`domain/integration`, `domain/operational`, `domain/semantic`, `domain/shared` — not `domain/blueprint`
or any `*_engine`-family package), that location would have made Blueprint the first package in its
family to couple domain code to persistence/SQLAlchemy, breaking an unbroken, six-for-six convention
observed across every comparable capability (`decision_engine`, `governance_engine`,
`identity_resolution`, `semantic_resolution`, `assertion_engine`, `knowledge_engine`). The
Product Owner formally superseded that location and approved
`backend/app/application/blueprint_service.py` instead — matching the exact pattern already proven by
`backend/app/application/decision_engine.py` and `backend/app/application/governance_engine.py`
(both exist today with **no** corresponding `api/` package, conclusively establishing that an
`application/`-layer module does not itself imply or require an HTTP API). This is the authorized
location below; `backend/app/domain/blueprint/service.py` is NOT authorized by this report.

## Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/application/blueprint_service.py` | CREATE | CDD-017 §3, §14; Product Owner service-location decision (superseding the originally considered `domain/blueprint/service.py`) | `BlueprintApplicationService`: a thin orchestration class taking a `BlueprintRepository` dependency and exposing ID-based full-aggregate retrieval (Blueprint + its `ConceptRequirement`/`RelationshipRequirement`/`InformationElementRequirement` tree), matching `BlueprintRepository.get_by_id()`'s already-authorized return shape and `DecisionApplicationService`'s constructor-injection pattern exactly. | No `get_by_name` (no named canonical content exists yet — deferred to G3.5). No lifecycle/governance-status eligibility filtering (same reason). No HTTP schema, router, or FastAPI dependency of any kind (§14). No conformance/scoring/comparison method (§10). No seed/authoring method (§13). No tenant parameter or tenant-scoping logic of any kind (§9). No modification to `BlueprintRepository`, the Blueprint domain model, any ORM model, or any migration. | Unit test proving delegation to the repository's `get_by_id` and clean not-found propagation. |
| `backend/app/tests/test_blueprint_service.py` | CREATE | CDD-011/CDD-012 test-authorization precedent, applied to this capability, following the established one-file-per-capability naming convention (`test_decision_engine.py`, `test_governance_engine.py` each cover both their `domain/*` and `application/*` modules in one file; no `test_application_*.py`-style file exists anywhere in the repository) | Unit-level tests only: aggregate retrieval delegates correctly to a `BlueprintRepository`-protocol-conforming fake, not-found returns cleanly, no tenant parameter/logic present, no HTTP-layer object referenced, no conformance/scoring call present. | No PostgreSQL-dependent test (G2's own `test_blueprint_persistence_postgres.py` already proves `get_by_id` against real Postgres; re-proving that here would duplicate existing coverage without adding evidence value). | Direct test execution. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 (mechanism origin) + CDD-015 §35 (extension precedent, already reused by the G2 companion) | Extend `AUTHORIZED_CHANGED_PATHS` with exactly the two paths above, registering them under the existing architecture-drift guardrail. | No assertion weakened. No wildcard path. No existing authorized path removed. No bypass of any architecture check. | Direct test execution. |

No other repository path is authorized. All unlisted paths are READ-ONLY under this report — in
particular, `backend/app/domain/blueprint/__init__.py`, `backend/app/application/__init__.py`,
`backend/app/infrastructure/persistence/blueprint_repository.py`,
`backend/app/domain/blueprint/model.py`, and `backend/app/core/dependency_container.py` were each investigated during discovery and
found to require no modification (the first two follow no central re-export/registration pattern that
a new module would need to join; the repository and domain model already fully support the authorized
contract; no comparable application service is wired into the DI container today — both
`DecisionApplicationService` and `GovernanceApplicationService` are constructed directly wherever
needed, currently only in tests).

## Critical boundaries restated (binding, unchanged from CDD-017)

- **Repository/application separation**: `BlueprintApplicationService` is the only artifact authorized
  to import `BlueprintRepository`. It performs no persistence of its own — it delegates entirely to the
  already-authorized, unmodified G2 repository (CDD-017 §14; discovery §5-§7).
- **No canonical seed**: G3 MUST NOT create, seed, or author any canonical production Blueprint
  content. Canonical Blueprint Seed is G3.5's exclusive scope (CDD-017 §13).
- **No conformance/validation**: G3 MUST NOT compare an ontology against Blueprint requirements, report
  missing concepts/relationships/information elements, or calculate completeness, conformance, or
  satisfaction of any kind. Blueprint Conformance/Validation is G4's exclusive scope (CDD-017 §10).
- **No external surface**: G3 creates no HTTP endpoint, FastAPI router, API schema, `blueprint:read`
  scope, Keycloak change, or JWT/auth enforcement change of any kind (CDD-017 §14). Consequently this
  report requires no PAD, no new auth scope, no Keycloak modification, and no frontend change. The
  future existence of an external API remains separately governed and is not implied or reserved by
  this report or by `blueprint_service.py`'s location in `application/` (see "Service location
  correction" above).
- **Tenancy**: G3 introduces no `tenant_id` column, parameter, or tenant-specific Blueprint
  selection/configuration behavior of any kind, preserving CDD-017 §9's global/product-owned model.
- **Persistence/domain/migration untouched**: no modification to `BlueprintRepository`, the Blueprint
  domain model, any ORM model, or any migration. No new migration is authorized or required.
- **Ontology identity reuse, version model, declarative boundary, information-element boundary,
  obligation semantics**: all as already bound by CDD-017 §7, §8, §10, §11, §6/§20 and restated
  unchanged by the G2 companion — none reopened or affected by this report.

## G3.5 and G4 boundary (binding)

**Canonical Blueprint Seed belongs to G3.5**, not G3. G3 provides only the internal application
boundary that G3.5 will later be able to consume once real content exists; it seeds nothing itself.

**Blueprint Conformance/Validation belongs to G4**, not G3. G3 performs no comparison of any kind
between actual ontology/data and canonical Blueprint requirements.

## Authorization

Authorized by CTEC Product Owner Manoj Nair: this artifact-authorization record satisfies CDD-017
§17/§19's binding implementation precondition for exactly the internal application-service scope
listed above, per the Gate G G3 Artifact-Scope Discovery (final recommendation: A — G3 ARTIFACT SCOPE
READY FOR PRODUCT OWNER APPROVAL) and the Product Owner's approved replacement service-location
decision (superseding the originally considered `domain/blueprint/service.py`). CDD-017 itself remains
unchanged. No implementation exists yet — a separate, subsequent Product Owner authorization is
required before any file listed above is created or modified.
