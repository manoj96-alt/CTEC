# CDD-017 — G2 Persistence and Domain Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `f2e9b60100d721ecc890d8a45cf87ecea0d0c0fe`

## Decision

CDD-017 §17 and §19 defer the exhaustive per-file artifact-authorization record for Gate G's
persistence/domain implementation to a separate, subsequent, CDD-Template-v2.2-compliant document,
mirroring CDD-015 §33's exact format — binding: "Implementation MUST NOT proceed against §6's model
without that separate, subsequent artifact-authorization record existing first." This report is that
record. It follows the same standalone-companion-document precedent already used for CDD-015 (three
merged companions: PR #69, PR #71, PR #73) and for CDD-010/CDD-012 (the "-AUTHORIZATION"/"-ALLOWLIST"
companion pattern, e.g. `CDD-010-CDD-012-REPLAY-REMEDIATION-AUTHORIZATION.md`,
`CDD-010-TRUSTED-ADMISSION-INTEGRATION-ALLOWLIST.md`): a standalone companion document to an
already-FROZEN CDD, not an edit to CDD-017 itself, and not a new architecture baseline.

This report authorizes exactly the artifact scope the Gate G G1.5 Artifact Authorization
Traceability Review produced and the Product Owner approved — no artifact added, removed, renamed,
or expanded beyond that reviewed table. It introduces no new architecture: every artifact below
traces to CDD-017's already-authorized §6-9 domain model. G2 implements persistence and domain
objects only — no read API, no seed of canonical production content, no frontend, no UI, matching
CDD-017 §14's explicit read-surface deferral and §13's explicit seeding deferral.

**Post-approval artifact-authorization-gap remediation (this revision)**: implementation against the
original 8-artifact table below surfaced a real, narrow test-fixture collision during downstream
CDD-019 H3 PostgreSQL integration evidence — see the final Discovery finding, below — closed by adding
exactly one MODIFY row for an already-authorized file. No other row in this document was altered by
this remediation; the original 8 artifacts, and every binding requirement in every other section, are
unchanged. No implementation exists yet under this revision — a separate, subsequent Product Owner
authorization is required before the newly authorized file is modified.

## Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/infrastructure/persistence/migrations/versions/0014_blueprint_requirement_contract.py` | CREATE | CDD-017 §6, §7, §9 | Create `blueprints`, `concept_requirements`, `relationship_requirements`, `information_element_requirements` tables with exactly the columns/FKs the CDD-017 §6 domain model and §7 ontology-identity-reuse boundary establish — no `tenant_id` column (§9). | No structural change to any existing table. No `unique=True` on `blueprint_name` (§8 honest precedent caveat). No seed data inserted by the migration itself (§13 — seeding is a separate future phase). No "supersede"/re-parenting logic (open question, deferred — see Remaining Risks). | Migration upgrade/downgrade test; backward-compatibility check (no existing table altered). |
| `backend/app/infrastructure/persistence/models/blueprint.py` | CREATE | CDD-017 §6 | ORM models: `BlueprintORM`, `ConceptRequirementORM`, `RelationshipRequirementORM`, `InformationElementRequirementORM`, reusing the existing `lifecycle_state`/`governance_status` `Enum` column pattern (matching `entity_type.py`/`institutional_concept.py` exactly) plus a new `obligation` `Enum("REQUIRED","CONDITIONAL","OPTIONAL", name="blueprintobligation_t")` column, applying the identical existing enum-column mechanism to the closed vocabulary CDD-017 §6/§20 authorize. | No new lifecycle/governance-status enum (§12). No `tenant_id` field (§9). No type/validation column on `InformationElementRequirement` (§11). | Model unit test. |
| `backend/app/domain/blueprint/__init__.py` | CREATE | CDD-017 §6 | Package export surface, mirroring `domain/decision_engine/__init__.py`'s import-and-re-export pattern. | No `service.py`/`configuration.py` (no domain service logic is authorized for G2 — persistence is repository-owned). | Import/boundary test. |
| `backend/app/domain/blueprint/model.py` | CREATE | CDD-017 §6-9 | Domain-layer dataclasses (`Blueprint`, `ConceptRequirement`, `RelationshipRequirement`, `InformationElementRequirement`) and the `Obligation` `StrEnum` (`REQUIRED`/`CONDITIONAL`/`OPTIONAL`), matching the existing `GateFOutcomeReason(StrEnum)`-style convention. | No generalized `Requirement` supertype (§6, Decision 1B). No type system on `InformationElementRequirement` (§11). | Domain unit test. |
| `backend/app/infrastructure/persistence/blueprint_repository.py` | CREATE | CDD-017 §6, §14 | Minimal repository: `create(...)` (persist a `Blueprint` and its child requirements in one transaction) and `get_by_id(...)` (internal read, needed by tests only) — no other method. | No `get_by_name`. No "list all." No "create new version from existing"/re-parenting method (open question, explicitly deferred). No FastAPI router or schema (§14, §16). No conformance/scoring method (§10). | Repository unit + Postgres integration tests. |
| `backend/app/tests/test_blueprint_migration.py` | CREATE | CDD-011/CDD-012 migration-test precedent, applied to this schema | Migration correctness; upgrade/downgrade; confirms no existing table/column altered. | — | Direct test execution. |
| `backend/app/tests/test_blueprint_persistence.py` | CREATE | CDD-017 §6-9 | Unit-level tests: ontology-reference validation (real `entity_type_id`/`relationship_type_id` required), no `tenant_id` anywhere, requirement-ID field presence, no naive name-uniqueness constraint. | No multi-version/re-parenting test (open question — out of scope until resolved). | Direct test execution. |
| `backend/app/tests/test_blueprint_persistence_postgres.py` | CREATE | CDD-017 §6-9 | Postgres-backed: real FK constraint enforcement (invalid ontology reference rejected at the DB layer). | Same exclusion as above — single-version scope only. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_blueprint_persistence_postgres.py` (row 9, this revision) | MODIFY | CDD-017 §6-9 (unchanged); remediation discovered via CDD-019 H3 downstream PostgreSQL evidence | In `test_blueprint_with_concept_relationship_and_information_element_requirements_round_trips` only: replace the synthetic test Blueprint's `blueprint_name` literal — currently the production canonical name `"CTEC Semiconductor Supply Chain Blueprint"` — with a randomized, collision-free, clearly-non-canonical test name generated exactly as `f"G2 Blueprint Round-Trip Test Blueprint {uuid4()}"` — mandatory: matching this same file's own established `get_approved_by_name`-safe convention already used by every G4-authored test in this file; a fixed/static literal is NOT authorized. The generated value must be stored in a local variable and the corresponding assertion updated to compare against that same stored value. | No other line, assertion, or test function in this file may change. No change to `BlueprintSeeder`, `BlueprintApplicationService`, `BlueprintRepositoryImpl`, the `Blueprint` domain model, the `Blueprint` ORM model, any migration, any constraint, or `get_approved_by_name(...)`. No change to the production canonical Blueprint's identity or name. No weakening of `test_get_approved_by_name_raises_when_multiple_approved_matches_exist` or any other ambiguity-protection test in this file. | Direct test execution: the corrected test must pass unmodified in every other respect; `test_blueprint_seed.py`, `test_blueprint_service.py`, and every other G3/G3.5/G4 Blueprint test must continue passing unaffected; the remediation PR's own CI logs must be directly inspected (not inferred from an overall green check) to positively confirm zero occurrences of the `"Multiple Approved Blueprint rows found"` error anywhere in that run; and the full backend suite, including every CDD-019 H1/H2 test, must be independently re-confirmed passing in that same CI run — proving the corrected fixture coexists safely with the real, canonically-seeded Blueprint in the cumulative PostgreSQL environment, not merely that the isolated G2 test itself passes in the abstract. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 (mechanism origin) + CDD-015 §35 (extension precedent — not CDD-017 directly) | Extend `AUTHORIZED_CHANGED_PATHS` with the exact paths in this table, registering them under the existing architecture-drift guardrail. | No assertion weakened. No wildcard path. No existing authorized path removed. No bypass of architecture checks. | Direct test execution. |

No other repository path is authorized. All unlisted paths are READ-ONLY under this report.

## Critical boundaries restated (binding, unchanged from CDD-017)

- **Ontology identity reuse**: `ConceptRequirement.entity_type_id`, `RelationshipRequirement.relationship_type_id`/`target_entity_type_id` reference existing `entity_types`/`relationship_types` rows exclusively. No parallel ontology, no duplicated concept or relationship identity, no new vocabulary (CDD-017 §7). If implementation discovers a missing concept/relationship, it MUST STOP and report — not authorized here.
- **Tenancy**: canonical Blueprint persistence is global/product-owned. No `tenant_id` column on any of the four new tables (CDD-017 §9).
- **Version model**: `Blueprint` itself is the versioned, immutable-once-Approved definition, connected across versions via its own `previous_version_id` self-FK — no separate `BlueprintVersion` table (CDD-017 §6, §8). This report authorizes only single-version create/read behavior; the version re-parenting question CDD-017 §8 leaves open (how child requirement rows behave when a second version is minted) is explicitly NOT resolved or implemented here.
- **Declarative boundary**: everything authorized here stores declarations only. No runtime conformance engine, no tenant conformance scoring, no decision-execution gating, no Entity Resolution gating, no Ask CTEC gating, no source-completeness enforcement (CDD-017 §10).
- **Information element boundary**: `InformationElementRequirement` is authorized exactly as CDD-017 §11 defines it — `element_name` + `description` + `obligation` only, no type system, no validation rule, no live binding to `assertions.predicate`.
- **Obligation semantics**: `REQUIRED`/`CONDITIONAL`/`OPTIONAL` is a closed, three-value, purely declarative vocabulary (CDD-017 §6, §20). It authorizes no runtime meaning or enforcement.
- **No read API, no UI**: no `api/blueprint/` package, no FastAPI router, no HTTP schema, no frontend file, no Blueprint authoring/viewer UI (CDD-017 §14, §16). A `blueprint:read` scope and any external read surface require their own, separately authorized PAD amendment — not authorized here.
- **No production seed**: no canonical production Blueprint content is inserted by any artifact in this table (CDD-017 §13). Test fixtures created by the test files above are explicitly test data, not canonical seed content.
- **No runtime behavior change**: no modification to Gate F's DRM/GRM, `runtime/orchestration.py`, `runtime/recovery.py`, Ask CTEC's traversal code, Entity Resolution, authentication, or authorization (CDD-017 §4, §22).

## Discovery finding — test-fixture collision remediation (this revision)

Discovered via downstream evidence, not a G2 defect. `test_blueprint_with_concept_relationship_and_information_element_requirements_round_trips`
persists a synthetic, non-canonical Blueprint using the exact literal production canonical Blueprint
name (`"CTEC Semiconductor Supply Chain Blueprint"`) with a random `uuid4()` identifier, committed to
the shared, session-scoped PostgreSQL CI database. This was harmless at G2's own authorization time —
no code path queried Blueprint by name. Gate H's H2 companion (CDD-019) later introduced
`BlueprintApplicationService.get_approved_by_name`, and every one of *that* companion's own new
Postgres tests correctly used randomized, collision-free names — but this pre-existing G2 test's
literal name was never revisited, since G2 itself never called `get_approved_by_name`. CDD-019's H3
companion is the first-ever caller of `get_approved_by_name` with the literal canonical name against
the full, cumulative CI database (its own governed, correct, unmodified use of the mechanism the
H2/H3 companions mandate), and correctly surfaces the resulting ambiguity — proving
`get_approved_by_name`'s ambiguity protection works exactly as CDD-018 §13 requires, not a defect in
it. **H3 exposed this pre-existing G2 gap; H3 does not own, and is not authorized to perform, this
remediation** — H3's implementation PR remains entirely unmodified by this amendment, and no
workaround of any kind is authorized within H3's own artifacts for this collision. This amendment
authorizes exactly one corrective change (row 9, above), closing the gap without altering G2's,
CDD-017's, or CDD-019's architecture in any way.

## Remaining risks (recorded, not resolved by this report)

**P1 — version re-parenting.** CDD-017 §8 states child `*_requirement_id` values are "preserved across a Blueprint row's version chain," without specifying whether this means in-place FK re-pointing on the same physical row or another mechanism, when a second `Blueprint` version is minted. This report deliberately excludes any "supersede"/re-parenting capability from G2's authorized scope (see Exclusions column above), so the open question does not block this authorization. It must be resolved by explicit Product Owner/architecture decision before any future phase mints a second Blueprint version.

## Authorization

Authorized by CTEC Product Owner Manoj Nair: this artifact-authorization record satisfies CDD-017
§17/§19's binding implementation precondition for exactly the persistence/domain scope listed above,
per the Gate G G1.5 Artifact Authorization Traceability Review (final recommendation: A — ARTIFACT
SCOPE READY FOR PRODUCT OWNER APPROVAL). CDD-017 itself remains unchanged. No implementation exists
yet — a separate, subsequent Product Owner authorization is required before any file listed above is
created or modified. **For row 9 only** (this revision): authorized per a dedicated governance
discovery, a Product Owner content review (P1×2 findings), a remediation closing both P1s, and a
final Product Owner re-review confirming P0 = 0, P1 = 0, P2 = 1 (accepted as-is) — narrowly closing a
test-fixture-collision gap discovered via CDD-019 H3 downstream evidence. No other row in this
document was altered by this revision. CDD-019 and its H1/H2/H3 companions remain entirely unchanged
and do not own this remediation.
