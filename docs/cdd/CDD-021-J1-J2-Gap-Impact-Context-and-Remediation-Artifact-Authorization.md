# CDD-021 — J1/J2 Gap Impact Context and Remediation Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `5b15fa94dd18b648fe0d675cbb397e32848a34b9`

## 1. Authority and scope

CDD-021 §26 defers the exhaustive per-file artifact-authorization record for its initial implementation
phase to a separate, subsequent, CDD-Template-v2.2-compliant document, explicitly mirroring CDD-020's own
I1 companion's exact format and governance-cycle discipline (CDD-021 §3, §26). This report is that record
for **J1 and J2 together** — Descriptive Gap Impact Context and Governed Remediation Recommendation, the
smallest implementation phase that establishes the governed application/domain capability CDD-021 §6-§24
defines. CDD-021 §24 explicitly authorizes governing both scopes under one companion, since neither is a
categorically separate artifact class the way H1/H2/H3 each were — J2 adds exactly one optional field to
the result type J1 already produces. This is a standalone companion to CDD-021, following the identical
companion precedent already used eight times across CDD-017, CDD-018, CDD-019, and CDD-020.

This record was produced through: J1/J2 artifact discovery (§3 below, no CDD-021 governance gap, no
unresolved architecture decision, four-artifact proposed surface); a Product Owner content review cycle
(five remediation cycles — P1-1, P1-2, the §5 citation P1, P1-3, and P1-5 — each resolved and verified
against regression) culminating in the Final Governance Publication Closure Review's P0 = 0, P1 = 0
verdict; and Product Owner approval, published alongside CDD-021's own transition to FROZEN state. No
implementation exists yet, and none is authorized by this record's approval alone — a separate, subsequent
Product Owner implementation authorization is still required before any file listed below is created or
modified (CDD-021 §26, restated).

## 2. J1/J2 objective (binding, restated from CDD-021 §1, §8, §9, §24)

For each `InformationElementCoverageResult` in an already-produced Gate I `SemanticCoverageEvaluationResult`,
derive: (J1) Affected Governed Context — the owning `ConceptRequirement`'s identity, governed
`entity_type_id`, and bounded governed relationship context, using only the same Approved `Blueprint`
object Gate I already retrieved; and (J2) for `UNMAPPED` results only, exactly one Remediation
Recommendation — `RemediationAction.REVIEW_SEMANTIC_MAPPING`. Neither J1 nor J2 calls H2, re-evaluates
Gate I, reads live source data, scores, or ranks.

## 3. Repository evidence inspected (binding, restated for the record)

- **Closest architectural precedent**: `SemanticCoverageEvaluationApplicationService`
  (`backend/app/application/semantic_coverage_evaluation.py`, CDD-020 I1) — the shape this CDD's service
  mirrors most closely in spirit (pure derivation over already-loaded data, no persistence, one public
  method, co-located frozen result types) — but with an important structural difference: I1 depends on two
  `Protocol`s and performs I/O (via those protocols) to produce its result; this CDD's service performs
  **no I/O of any kind** — it is a pure function over two already-in-memory objects (a
  `SemanticCoverageEvaluationResult` and a `Blueprint`), passed in by the caller, not resolved internally.
  No `Protocol` dependency is needed or authorized.
- **`Blueprint`/`ConceptRequirement`/`RelationshipRequirement` shape**: `backend/app/domain/blueprint/model.py`
  (frozen dataclasses) — confirmed by direct read this turn: `ConceptRequirement.entity_type_id` and
  `RelationshipRequirement.relationship_type_id`/`target_entity_type_id` are `Identifier` (UUID)
  references; **neither carries a human-readable name field** (unlike `InformationElementRequirement.element_name`,
  which does). This directly grounds CDD-021 §8's binding requirement that this CDD's own result types
  carry governed IDs only, never names.
- **`SemanticCoverageEvaluationResult`/`InformationElementCoverageResult` shape**: confirmed unmodified,
  read fresh this turn from `semantic_coverage_evaluation.py` — `InformationElementCoverageResult`
  (`information_element_requirement_id`, `obligation`, `status`, `resolution`) is the exact type this CDD's
  service receives one tuple of, per call, and wraps without modification.
- **No wiring artifact requires modification**: by the identical reasoning CDD-020's own I1 companion
  established (direct repository search proved none of `BlueprintApplicationService`,
  `BlueprintConformanceApplicationService`, or `SemanticMappingResolutionApplicationService` is wired into
  `dependency_container.py`/`app/main.py`), and since this CDD's service takes its inputs as plain
  constructor/method arguments rather than resolving any dependency itself, there is even less reason for
  any wiring change here than there was for I1.
- **Test-double convention**: not needed for this CDD's own unit tests in the way it was for I1/H2 — since
  this service performs no I/O, its unit tests construct plain `SemanticCoverageEvaluationResult`/
  `Blueprint` fixtures directly (matching `test_blueprint_conformance.py`'s and
  `test_semantic_coverage_evaluation.py`'s own fixture-construction style) rather than using fake
  `Protocol`-conforming doubles.
- **H3 fixture reuse for Postgres acceptance evidence**: `test_semantic_coverage_evaluation_postgres.py`
  (CDD-020 I1, unmodified) already establishes the exact pattern this CDD's own Postgres test reuses —
  composing the real, unmodified `BlueprintApplicationService` + `SemanticMappingResolutionApplicationService`
  + `SemanticCoverageEvaluationApplicationService` against the existing, unmodified H3 fixture
  (`BlueprintSeeder` + `DemoSemanticMappingSeeder`), then passing the resulting real
  `SemanticCoverageEvaluationResult` and `Blueprint` into this CDD's new service — reused by call only,
  touching zero CDD-019/CDD-020-owned file.
- **`AUTHORIZED_CHANGED_PATHS` mechanism**: `backend/app/tests/test_runtime_architecture.py` — confirmed
  unchanged mechanism (`assert changed <= AUTHORIZED_CHANGED_PATHS`), extended identically by every prior
  Gate G/H/I phase; this record extends it by exactly three new path strings.
- **Planning-candidate paths re-verified, not blindly carried forward**: the Governance Discovery &
  Authorization Planning report's three anticipated CREATE paths and one anticipated MODIFY path were each
  re-checked against actual current repository structure this turn; all four remain necessary and none
  duplicates an existing file (direct `test -e` / `grep` checks below, §4).

## 4. Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/application/gap_impact_remediation.py` | CREATE | CDD-021 §6-§24 | `GapImpactRemediationApplicationService`, taking no constructor dependencies (pure function service — no `Protocol`, no I/O). Exactly one public method: `derive(self, *, coverage_result: SemanticCoverageEvaluationResult, blueprint: Blueprint) -> tuple[GapImpactContext, ...]`. For each `InformationElementCoverageResult` in `coverage_result.information_element_results`: locate the owning `ConceptRequirement` in `blueprint.concept_requirements` whose `information_element_requirements` contains a matching `information_element_requirement_id` (raising `ValidationException` if none is found — CDD-021 §23); collect **bounded governed relationship context** as a tuple of `RelationshipContextEntry(relationship_type_id: UUID, direction: Direction, other_entity_type_id: UUID)` — one uniform shape regardless of direction (`Direction` a two-member `StrEnum`: `OUTGOING`, `INCOMING`) — built from: `(relationship_type_id, OUTGOING, target_entity_type_id)` for every `RelationshipRequirement` in that Concept's own `relationship_requirements` (this Concept is the declared source), plus, for every `RelationshipRequirement` anywhere else in the Blueprint whose `target_entity_type_id` equals this Concept's `entity_type_id` (this Concept is the declared target): `(relationship_type_id, INCOMING, other_entity_type_id)` where `other_entity_type_id` is that `RelationshipRequirement`'s *declaring* `ConceptRequirement`'s own `entity_type_id` — resolved by looking up that `RelationshipRequirement`'s `concept_requirement_id` among `blueprint.concept_requirements` (never this Concept's own `entity_type_id`, which would misidentify the relationship's other side); build `RemediationAction.REVIEW_SEMANTIC_MAPPING` if `coverage_result_element.status is CoverageStatus.UNMAPPED`, else `None`; wrap into one `GapImpactContext` per element (`coverage_result: InformationElementCoverageResult`, `concept_requirement_id: UUID`, `entity_type_id: UUID`, `relationship_context: tuple[RelationshipContextEntry, ...]`, `remediation_action: RemediationAction \| None`), sorted by `information_element_requirement_id` for determinism (mirroring CDD-020 I1's identical precedent). Also defines: `RemediationAction(StrEnum)` with exactly one member `REVIEW_SEMANTIC_MAPPING`; `RelationshipContextEntry` (frozen dataclass, slots, IDs only — no name field); `GapImpactContext` (frozen dataclass, slots). | No `Protocol`, no constructor-injected dependency, no import of `SemanticMappingResolutionApplicationService`, `BlueprintApplicationService`, or any persistence/ORM/HTTP module. No second call to Gate I's `evaluate(...)` or to H2's `resolve_approved_source_field(...)`. No human-readable name field (`element_name`, concept name, relationship name) on `RelationshipContextEntry` or `GapImpactContext`. No numeric score, percentage, severity, or ranking field anywhere. No second `RemediationAction` value. No `create`/`approve`/`retire` method. No caching or memoization across calls. | Application-service unit test (plain fixtures, no DB); Postgres acceptance test. |
| `backend/app/tests/test_gap_impact_remediation.py` | CREATE | CDD-021 §6-§24 | Unit tests using plain, directly-constructed `SemanticCoverageEvaluationResult`/`Blueprint`/`InformationElementCoverageResult`/`ConceptRequirement`/`RelationshipRequirement` fixtures (no PostgreSQL dependency, mirroring `test_blueprint_conformance.py`'s and `test_semantic_coverage_evaluation.py`'s fixture-construction style): **J1 evidence** — (1) Affected Governed Context is produced for every element regardless of `MAPPED`/`UNMAPPED` status; (2) `concept_requirement_id`/`entity_type_id` match the owning Concept exactly; (3) relationship context correctly includes both Concept-as-source and Concept-as-target `RelationshipRequirement`s from elsewhere in the Blueprint; (4) relationship context carries only IDs — asserted via `__dataclass_fields__`/attribute inspection that no name-typed field exists; (5) tenant identity is unread/untouched by this service (it never appears in any input/output type here — proven by asserting the service signature and result types carry no `tenant_id` field of their own, inheriting it structurally from the passed-in `coverage_result` only); (6) Blueprint identity/version are not re-derived or duplicated — this service's result never repeats `blueprint_id`/`blueprint_version_number`, deliberately wrapping the original `InformationElementCoverageResult` instead; (7) no H4/live-source behavior exists (module import-hygiene check, mirroring I1's precedent — no persistence/ORM/HTTP import); (8) no persistence exists (same import-hygiene check). **J2 evidence** — (9) `remediation_action is RemediationAction.REVIEW_SEMANTIC_MAPPING` if and only if status is `UNMAPPED`; (10) `remediation_action is None` for every `MAPPED` result — never populated, never defaulted; (11) exactly one `RemediationAction` value exists (enumerate `RemediationAction.__members__`); (12) no `SemanticMapping`/`SourceField` write call exists anywhere in the module (import-hygiene check); (13) no ranking/ordering field exists on `GapImpactContext` beyond the deterministic-sort key. **Shared evidence**: (14) owning-Concept-not-found raises `ValidationException` explicitly; (15) deterministic result ordering by `information_element_requirement_id`; (16) the service exposes no public method beyond `derive`; (17) the Risk Event Severity / Supplier Legal Name worked example (CDD-021's own worked example) is reproduced structurally using the H3 deterministic Blueprint's real Concept/RelationshipRequirement shape (`Risk Event` targeted by `Region --exposedTo--> Risk Event`), asserting the exact FACT-level fields CDD-021 §12 authorizes and none beyond them. | No PostgreSQL dependency. No test of `BlueprintApplicationService`'s, `SemanticMappingResolutionApplicationService`'s, or `SemanticCoverageEvaluationApplicationService`'s internal logic (covered elsewhere already). No test asserting a severity/score/rationale field (none exists). | Direct test execution. |
| `backend/app/tests/test_gap_impact_remediation_postgres.py` | CREATE | CDD-021 §16, §28 items 2, 8 | Postgres-backed acceptance evidence, composing the real, unmodified `BlueprintApplicationService` + `SemanticMappingResolutionApplicationService` + `SemanticCoverageEvaluationApplicationService` (exactly as CDD-020 I1's own Postgres test already does) against the existing, unmodified H3 fixture (`BlueprintSeeder` + `DemoSemanticMappingSeeder`, reused by call only), then passing the resulting real `SemanticCoverageEvaluationResult` and `Blueprint` into the new `GapImpactRemediationApplicationService.derive(...)`: (1) H3 acceptance — `Supplier Legal Name` yields `remediation_action is None` with correct `concept_requirement_id`/`entity_type_id` for the `Supplier` concept; `Risk Event Severity` yields `remediation_action is RemediationAction.REVIEW_SEMANTIC_MAPPING` with correct `concept_requirement_id`/`entity_type_id` for the `Risk Event` concept, and its relationship context includes the real, governed `Region --exposedTo--> Risk Event` `RelationshipRequirement` (proving §8's Concept-as-target derivation against real seeded data, not a synthetic fixture); (2) determinism — two sequential `derive(...)` calls with the same real inputs return equal results. | No test asserts against H4/live-source-value behavior. No test bypasses Gate I or H2 to query persistence directly. No modification to `BlueprintSeeder`, `DemoSemanticMappingSeeder`, or any file they depend on. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 mechanism, reused by every prior Gate G/H/I phase | Add exactly three new string entries to the existing `AUTHORIZED_CHANGED_PATHS` set: `"backend/app/application/gap_impact_remediation.py"`, `"backend/app/tests/test_gap_impact_remediation.py"`, `"backend/app/tests/test_gap_impact_remediation_postgres.py"`. | No other entry added, removed, or altered. No change to the subset-comparison logic itself. No wildcard, no directory-level entry. | Direct test execution. |

No other repository path is authorized. In particular: `semantic_coverage_evaluation.py`, `blueprint_service.py`,
`blueprint_conformance.py`, `semantic_mapping_resolution.py`, `semantic_mapping_repository.py`,
`blueprint_repository.py`, `blueprint_seed.py`, `demo_semantic_mapping_seeder.py`, any domain model file
(`domain/blueprint/model.py`, `domain/semantic_mapping/*`, `domain/integration/source_field.py`), any ORM
model file, any migration file, `dependency_container.py`, `app/main.py`, any API/router/schema file, any
frontend file, `supply_chain_impact_api.py` or any other CDD-015 artifact, `domain/ontology/*` or any other
Ask CTEC artifact, and any H4/Gate N/Gate P artifact are **not** authorized for modification.

## 5. Protected artifacts / architecture firewall table

| Protected artifact/class | Why protected | Enforcement in this record |
|---|---|---|
| `semantic_coverage_evaluation.py` (Gate I / I1) | Sole authoritative input; must never be re-implemented or duplicated | Not in CREATE/MODIFY list; §3 confirms no wiring change needed; unit tests assert no import of it beyond the type it exports |
| `semantic_mapping_resolution.py` (H2) | Sole semantic-resolution path; Gate J must never re-enter it | Not in CREATE/MODIFY list; import-hygiene tests assert absence |
| `blueprint_conformance.py` / `RequirementStatus` (CDD-018) | `NOT_EVALUATED` firewall | Not in CREATE/MODIFY list; never imported; no field of this CDD's result types references it |
| `blueprint_service.py`, `blueprint_repository.py`, `blueprint_seed.py` | Blueprint identity/version integrity | Not in CREATE/MODIFY list; this CDD's service takes a `Blueprint` object as a caller-supplied argument, never fetches its own |
| `supply_chain_impact_api.py` and any other CDD-015 artifact | Disambiguation firewall (CDD-021 §2, §17) — different "impact" concept entirely | Not in CREATE/MODIFY list; no import; no shared type; no shared vocabulary term used ambiguously in code |
| `domain/ontology/*`, `app/api/ontology/*` (Ask CTEC) | Gate P firewall | Not in CREATE/MODIFY list; no import |
| Any ORM model, migration file | Non-persistence firewall (CDD-021 §15, §26) | No such file in CREATE/MODIFY list |
| `dependency_container.py`, `app/main.py` | No wiring change needed or authorized | Not in CREATE/MODIFY list; §3 provides direct evidence |
| `InformationElementRequirement` evaluation / `RequirementStatus` value | `NOT_EVALUATED` firewall | Never read, never written, never referenced by any authorized artifact |

## 6. J1 acceptance criteria (binding)

1. `GapImpactRemediationApplicationService.derive(...)` produces exactly one `GapImpactContext` per
   `InformationElementCoverageResult` in the supplied `coverage_result`, for both `MAPPED` and `UNMAPPED`
   statuses, without re-invoking Gate I or H2.
2. `concept_requirement_id` and `entity_type_id` on each `GapImpactContext` exactly match the owning
   `ConceptRequirement` resolved from the supplied `Blueprint` — proven directly against the real H3
   Blueprint (`Supplier` for Supplier Legal Name, `Risk Event` for Risk Event Severity).
3. Tenant identity is never referenced, read, or duplicated by this service or its result types — the
   caller retains tenant identity via the original `coverage_result.tenant_id` (top-level, unmodified)
   they already hold; this service's pure-function derivation requires and stores no `tenant_id` field of
   its own anywhere on `GapImpactContext`.
4. Blueprint identity/version are not duplicated on this CDD's own result types — proven by
   `GapImpactContext`'s field set containing no `blueprint_id`/`blueprint_version_number`.
5. `relationship_context` on each `GapImpactContext` is bounded to only `RelationshipRequirement`s
   structurally connected (as source or target) to the owning Concept — proven against the real H3
   Blueprint (`Risk Event Severity`'s context includes exactly the `Region --exposedTo--> Risk Event`
   relationship, and no unrelated relationship).
6. `RelationshipContextEntry` carries exactly three fields — `relationship_type_id`, `direction`
   (`OUTGOING`/`INCOMING`), and `other_entity_type_id` — the same uniform shape for both directions, never
   a conditionally-different field set; no name field — proven via `__dataclass_fields__` inspection
   listing exactly those three fields for every entry regardless of direction.
7. No severity, score, percentage, or weighting field exists anywhere in `GapImpactContext` or
   `RelationshipContextEntry` — proven via `__dataclass_fields__` inspection listing the full, closed
   field set.
8. No H4/live-source behavior exists — proven via module import-hygiene test asserting the absence of any
   persistence, ORM, or HTTP-layer import.
9. No persistence exists — same import-hygiene test; no `INSERT`/`UPDATE`/`DELETE` call anywhere in the
   module.

## 7. J2 acceptance criteria (binding)

1. `RemediationAction.REVIEW_SEMANTIC_MAPPING` is the only member of `RemediationAction` — proven via
   `RemediationAction.__members__` enumeration equaling exactly one entry.
2. `remediation_action` is populated if and only if `coverage_result_element.status is CoverageStatus.UNMAPPED`
   — proven against the real H3 Blueprint (`Risk Event Severity` → populated; `Supplier Legal Name` →
   `None`).
3. `MAPPED` results are never given a non-`None` `remediation_action` — the same H3 proof, checked in both
   directions.
4. No candidate `SourceField` is identified, referenced, or invented anywhere in `GapImpactContext`,
   `RemediationAction`, or any test assertion — proven by the closed field set (item 7 above) containing
   no such field, and by the module import-hygiene test confirming no `SourceField`/`SemanticMapping`
   import exists.
5. No `SemanticMapping` write call (`create`/`approve`/`retire`) exists anywhere in the module — same
   import-hygiene test.
6. No workflow, task, or execution call exists anywhere in the module — confirmed by the module's own
   public-method-surface test (`derive` only).
7. No ranking, ordering, or priority field exists among remediation recommendations — with only one
   `RemediationAction` value possible, this is structurally guaranteed and directly confirmed by item 1.

## 8. Postgres acceptance evidence — composition proof

The Postgres test row in §4 composes, without modifying any of them: the real, unmodified
`BlueprintApplicationService` (CDD-017 G3) + the real, unmodified `SemanticMappingResolutionApplicationService`
(CDD-019 H2) + the real, unmodified `SemanticCoverageEvaluationApplicationService` (CDD-020 I1) → producing
a real `SemanticCoverageEvaluationResult` from the real, existing H3 fixture data → passed into the new
`GapImpactRemediationApplicationService.derive(...)`. The deterministic proof required: `Supplier Legal Name`
→ `MAPPED` (via H2's real resolution against the seeded `H3 Demo ERP`/`LFA1`/`LFA1-NAME1` mapping) → no
remediation; `Risk Event Severity` → `UNMAPPED` (via H2's real zero-match) → `REVIEW_SEMANTIC_MAPPING`
recommendation, with relationship context showing the real, governed `Region --exposedTo--> Risk Event`
`RelationshipRequirement`. This proves Gate J's own new derivation logic against real upstream data without
claiming or requiring any live-source-value conformance — the H3 fixture's `SourceField`/`SemanticMapping`
rows are governance metadata, never read for their (nonexistent) live values.

## 9. Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the four artifact paths authorized above without new Product Owner
authorization. If implementation discovers that any authorized artifact's Exclusions column cannot be
satisfied without touching an unlisted path (in particular: `dependency_container.py`, `app/main.py`,
`semantic_coverage_evaluation.py`, any H2/Blueprint/CDD-015/Ask-CTEC artifact, or any H4/Gate-N/Gate-P
concern), implementation MUST STOP and report the exact blocker rather than silently expanding scope.

## 10. Publication/approval state

This document is an **approved artifact-authorization companion**, published to `APPROVED ARTIFACT
AUTHORIZATION` state alongside CDD-021's own publication to FROZEN state, following the identical Product
Owner review-and-approval cycle every prior companion (CDD-017 G2/G3/G3.5, CDD-018 G4, CDD-019 H1/H2/H3,
CDD-020 I1) underwent — discovery (§3), a content review confirming P0 = 0, P1 = 0, and Product Owner
approval. Approval of this record governs exactly the artifact sandbox in §4 above; it does **not** itself
authorize implementation of any artifact listed there — a separate, subsequent Product Owner implementation
authorization remains required (§1, §9) before any file listed above is created or modified.
