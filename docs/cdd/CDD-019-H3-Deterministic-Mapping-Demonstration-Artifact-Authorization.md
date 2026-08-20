# CDD-019 — H3 Deterministic Mapping Demonstration Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `c2cd3b5ae662e6fe55d883775c4e7d0ae4291966`

## Decision

CDD-019 §25 defers the exhaustive per-file artifact-authorization record for each of its H1-H3
implementation phases to a separate, subsequent, CDD-Template-v2.2-compliant document, mirroring
CDD-017's G2/G3/G3.5 and CDD-018's G4 companions' exact format, and mirroring H1's and H2's own
companions for this same CDD-019. This report is that record for **H3 only** — Deterministic Mapping
Demonstration. It is a standalone companion to CDD-019, following the identical companion precedent
already used six times across CDD-017, CDD-018, and CDD-019 H1/H2.

This record was produced through: H3 artifact discovery (verdict A, no CDD-019 governance gap, no
unresolved architecture decision, 4-artifact proposed surface); a Product Owner content review that
found zero P0/P1 findings and one non-blocking P2 (literal-string drafting preference); and a final,
independent adversarial re-review confirming P0 = 0, P1 = 0, and that the P2 does not represent an
authorization ambiguity (the literal strings are already frozen with binding force). No implementation
exists yet.

## Discovery findings (binding, restated for the record)

- **Seeder pattern chosen**: a new, narrowly-scoped, tenant-refusing demo seeder module, matching
  `demo_gate_f_seeder.py`'s and `demo_entity_resolution_seeder.py`'s established shape exactly — not an
  extension of `BlueprintSeeder` (Blueprint is global-canonical; H3's data is tenant/source-specific, per
  CDD-019 §15's own explicit distinction), and not a bare test-inlined fixture (would use
  non-deterministic `uuid4()`, structurally unable to satisfy §22's binding idempotency requirement).
- **Ownership**: the seeder creates its own new `SourceSystem`/`SourceObject`, verified not to overlap
  Gate F's or Entity Resolution's existing demo systems by name or deterministic ID. `SourceField`/
  `SemanticMapping` creation goes through the real, unmodified H1 repositories. `"Supplier Legal Name"`/
  `"Risk Event Severity"` are referenced by name via the existing, unmodified
  `BlueprintApplicationService.get_approved_by_name()`, never created or modified.
- **No production wiring**: confirmed `app/main.py` references no demo seeder of any kind; the CLI
  entrypoint (`if __name__ == "__main__":`) is self-contained within the seeder module itself, matching
  every existing `demo_*` seeder precedent.
- **Literal-string treatment**: the exact deterministic dataset below (§ below) is binding, frozen text —
  not example or representative language. A conforming implementation may not substitute different
  literal values; doing so would produce an unauthorized record.

## Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/infrastructure/persistence/demo_semantic_mapping_seeder.py` | CREATE | CDD-019 §15, §22 | `DemoSemanticMappingSeeder`, refusing every tenant except `BOOTSTRAP_DEMO_TENANT_ID` (raising a dedicated `DemoTenantRequiredError`, mirroring `DemoGateFSeeder`'s identical precedent). Deterministically (`uuid5` under `BOOTSTRAP_SEED_NAMESPACE`) and idempotently creates exactly: one `SourceSystem` (`"H3 Demo ERP"`), one `SourceObject` (`"LFA1"`), one `SourceField` (`field_label = "LFA1-NAME1"`, via `SourceFieldRepositoryImpl.create()`), and one Approved `SemanticMapping` from that field to the existing `"Supplier Legal Name"` `InformationElementRequirement` (resolved by name via `BlueprintApplicationService.get_approved_by_name`, never created), via `SemanticMappingRepositoryImpl.create()`. Calls `BlueprintSeeder(session).load()` first as a prerequisite (idempotent, unmodified). Includes a manual `if __name__ == "__main__":` CLI entrypoint, never referenced by `app.main.lifespan` or any other production code path. | No modification to `BlueprintSeeder`, `BlueprintRepository`, or `BlueprintApplicationService`. No modification to `SourceFieldRepository`/`SemanticMappingRepository`. No second `SemanticMapping` created. No mapping to `"Risk Event Severity"` (deliberately left unmapped — the missing-mapping proof). No live source-system connection, connector, or scheduled ingestion of any kind. | Unit test; Postgres integration test. |
| `backend/app/tests/test_demo_semantic_mapping_seeder.py` | CREATE | CDD-019 §15, §18 | Unit-level: parametrized non-demo-tenant refusal (mirrors `test_demo_gate_f_seeder.py`'s exact style). | No PostgreSQL dependency. No behavioral test beyond tenant refusal (covered by the Postgres file instead). | Direct test execution. |
| `backend/app/tests/test_demo_semantic_mapping_seeder_postgres.py` | CREATE | CDD-019 §15, §22, §27 items 2, 7, 10, 11 | Postgres-backed: (1) idempotency — seeding twice yields an identical summary and creates nothing new the second time; (2) successful resolution — `resolve_approved_source_field` (or the repository method it delegates to) with the demo tenant and `"Supplier Legal Name"`'s real ID returns a `SemanticMappingResolution` matching the seeded field's provenance; (3) missing-mapping — the same call with `"Risk Event Severity"`'s real ID returns `None`; (4) tenant isolation — two freshly-generated, non-demo tenant IDs, mirroring `test_context_store_tenant_isolation`'s exact pattern, prove no cross-tenant resolution; (5) ambiguity prevention — a second `SemanticMappingRepositoryImpl.create()` attempt for the seeded field/element/tenant raises `ValidationException`; (6) deterministic resolution identity — two resolution calls with identical arguments return equal results. | No test asserts against H4/Gate-I-shaped behavior. No test bypasses the real H1/H2 mechanisms. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 mechanism, reused by every prior Gate G/H phase | Add exactly three new string entries to the existing `AUTHORIZED_CHANGED_PATHS` set: the seeder path and both new test paths above. | No other entry added, removed, or altered. No wildcard, no directory-level entry. | Direct test execution. |

No other repository path is authorized. In particular: `blueprint_seed.py`, `blueprint_repository.py`,
`application/blueprint_service.py`, `semantic_mapping_repository.py`,
`application/semantic_mapping_resolution.py`, `source_field_repository.py`, any ORM model file, any
migration file, `demo_gate_f_seeder.py`, `demo_entity_resolution_seeder.py`, `seed_loader.py`,
`app/main.py`, and any Blueprint or Blueprint Conformance artifact are **not** authorized for
modification.

## Explicit exclusions (binding, restated from CDD-019)

No live source-system connectivity, connector, or scheduled ingestion of any kind (§6, §15, §20). No
modification to `Blueprint`, `ConceptRequirement`, `InformationElementRequirement`, `BlueprintRepository`,
or `BlueprintApplicationService` (§4, §19). No modification to `BlueprintConformanceApplicationService`
(§4, §6, §20). No change to `InformationElementRequirement` evaluation status — it remains
`NOT_EVALUATED` (§4, §6, §20). No modification to `SourceField`, `SemanticMapping`, their domain models,
ORM models, migration, or repositories (H1/H2 — closed and frozen). No profiling, completeness,
freshness, gap-detection, null-rate analysis, gap classification, trust scoring, or source-value-
comparison logic of any kind (Gate I — entirely outside this CDD's authority). No new API, frontend, or
authentication/authorization scope (§21).

## Deterministic data set (binding, frozen)

Exactly four new rows: one `SourceSystem` (`"H3 Demo ERP"`), one `SourceObject` (`"LFA1"`), one
`SourceField` (`"LFA1-NAME1"`), one Approved `SemanticMapping` (to `"Supplier Legal Name"`). All under
`BOOTSTRAP_DEMO_TENANT_ID`, all `uuid5`-derived under `BOOTSTRAP_SEED_NAMESPACE`. **No other record is
authorized.** `"Risk Event Severity"` remains referenced-only, never mapped — this absence is itself the
required missing-mapping proof, not an oversight to be filled in.

| Record type | Deterministic ID/key | Tenant | Parent/reference | State |
|---|---|---|---|---|
| `SourceSystem` | `uuid5(BOOTSTRAP_SEED_NAMESPACE, "H3-DEMO-MAPPING-V1:source-system:H3 Demo ERP")` | `BOOTSTRAP_DEMO_TENANT_ID` | none | Active/Approved |
| `SourceObject` | `uuid5(..., "source-object:LFA1")` | `BOOTSTRAP_DEMO_TENANT_ID` | above `SourceSystem` | Active/Approved |
| `SourceField` | `uuid5(..., "source-field:LFA1-NAME1")` | inherited via `SourceObject` | above `SourceObject` | Active/Approved |
| `SemanticMapping` | `uuid5(..., "semantic-mapping:LFA1-NAME1")` | inherited via `SourceField` | targets `"Supplier Legal Name"`'s real, existing `information_element_requirement_id` | Active/**Approved** |

## Semantic mapping set (binding, frozen)

| SourceSystem | SourceObject | SourceField | InformationElementRequirement | Status |
|---|---|---|---|---|
| `H3 Demo ERP` | `LFA1` | `LFA1-NAME1` | `Supplier Legal Name` | **Approved** |

Exactly one mapping is ever authorized. It trivially satisfies both of CDD-019 §11's uniqueness rules —
nothing else in this authorization references either `LFA1-NAME1`'s `source_field_id` or `Supplier Legal
Name`'s `information_element_requirement_id`.

## Approved-status requirement (binding)

The seeded `SemanticMapping` MUST be created with `governance_status = Approved` — required to
demonstrate H2's Approved-only resolution path per CDD-019 §14/§15. No lifecycle-transition method, no
Retire/re-Approve capability, no generic governance-status-manipulation capability is authorized. H3 may
seed exactly the governed state its deterministic scenario requires; it does not create a new governance
workflow.

## H2 resolver reuse requirement (binding)

All resolution evidence MUST be produced by calling the existing, unmodified
`SemanticMappingResolutionApplicationService.resolve_approved_source_field(...)` (or the
`SemanticMappingRepository.get_approved_by_information_element_requirement(...)` method it delegates to)
— no second resolution mechanism, no direct ad hoc persistence query as an alternative path, is
authorized. `SemanticMappingResolution` remains exactly nine fields; `governance_status` remains absent
from it. Zero-match and ambiguity semantics are consumed exactly as merged, never redefined.

## H1/H2 preservation (binding)

`SourceField` physical identity, `SourceField` uniqueness (`UniqueConstraint(source_object_id,
field_label)`), `SemanticMapping` identity, `SemanticMapping` lifecycle, the Approved bidirectional 1:1
mechanism (both the source-side partial unique index and the target-side advisory-lock-guarded
application check), `create()`/`get_by_id()` behavior and signatures, `SemanticMappingResolution`'s
nine-field contract, and `get_approved_by_information_element_requirement`'s signature/behavior are all
unmodified by this authorization. H3 creates deterministic governed data using H1's existing persistence
model; it does not modify H1 in any way.

## H4 / Gate I exclusion (binding)

No live source-value reading, external connector, data-presence evaluation, freshness evaluation,
`SATISFIED`/`MISSING` determination, or `BlueprintConformanceApplicationService` modification of any kind
is authorized. No profiling, completeness calculation, null-rate analysis, gap detection, gap
classification, or trust scoring of any kind is authorized — that capability belongs to a future Gate I,
entirely outside this CDD's authority. `InformationElementRequirement` evaluation remains exactly
`NOT_EVALUATED` for the full duration of this report's authority.

## Schema / migration firewall (binding)

No ORM change, no migration, no new table, column, index, or constraint is authorized. H3 operates
entirely over H1's existing persisted schema (`source_systems`, `source_objects`, `source_fields`,
`semantic_mappings`), all unmodified.

## Seed repeatability requirement (binding)

Re-running the seeder against an already-seeded database MUST create nothing new — matching
`BlueprintSeeder`'s and `DemoGateFSeeder`'s identical, established idempotency precedent (deterministic
`uuid5`-derived identity, existence-checked before insert). No duplicate `SourceField` or `SemanticMapping`
may ever result from repeat execution.

## Evidence obligations

Real-PostgreSQL evidence is required for all six proof points enumerated in the
`test_demo_semantic_mapping_seeder_postgres.py` row's Purpose column above: idempotency, successful
resolution, missing-mapping, tenant isolation, ambiguity prevention, and deterministic resolution
identity. Unit-level evidence (`test_demo_semantic_mapping_seeder.py`) covers non-demo-tenant refusal
only — no PostgreSQL dependency required for that check.

## Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the four artifact paths authorized above without new Product Owner
authorization. If implementation discovers that any authorized artifact's Exclusions column cannot be
satisfied without touching an unlisted path (in particular: `app/main.py`, `unit_of_work.py`,
`repositories/__init__.py`, any Blueprint artifact, any H1/H2 artifact, or any H4/Gate-I concern),
implementation MUST STOP and report the exact blocker rather than silently expanding scope.

## Authorization

Authorized by CTEC Product Owner Manoj Nair: this artifact-authorization record satisfies CDD-019 §25's
binding implementation precondition for exactly the H3 — Deterministic Mapping Demonstration scope listed
above, per the Gate H3 artifact discovery (verdict A), a Product Owner content review (P0 = 0, P1 = 0,
P2 = 1), and a final, independent adversarial re-review confirming P0 = 0, P1 = 0, and that the P2 does
not represent an authorization ambiguity. CDD-019 remains unchanged. No implementation exists yet — a
separate, subsequent Product Owner authorization is required before any file listed above is created or
modified. H4 and Gate I remain entirely outside this report's authority and require their own, separate,
future governance cycles.
