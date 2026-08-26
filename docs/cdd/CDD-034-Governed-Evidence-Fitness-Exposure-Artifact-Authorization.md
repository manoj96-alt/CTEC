# CDD-034 — Governed Evidence Fitness Exposure — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `fb28bbca5bc2e70443f71390708ea0dbaa3fbc49`

## 1. Purpose

Enumerates exactly which repository artifacts CDD-034 implementation may create or modify to expose
Gate T's existing, unmodified Evidence Fitness computation through exactly one new REST endpoint — and
nothing more. This document alone does not authorize implementation; a separate, subsequent Product
Owner implementation authorization remains required.

This record was produced through: the Post-Gate-U/X cross-gate architecture and capability audit (A0),
Product Owner architecture decisions (A1), discovery and architecture definition (A2), governance
drafting (A3), independent final governance review (A4, finding two P1 contract-accuracy defects),
governance correction (A5, both resolved), governance publication and freeze (A6), Artifact
Authorization discovery of the exact physical surface (A7), Artifact Authorization drafting and
adversarial review (A8), and a further pre-publication discovery correction (A9-D1, adding the
repository's mechanically enforced runtime-architecture allowlist registration as an 11th
implementation file after confirming both Gate T's and Gate O's own Artifact Authorizations required
the identical registration for the identical reason).

## 2. Governing authorities

CDD-031 (FROZEN) remains the sole semantic authority for `EvidenceFitnessStatus`
(`FIT`/`STALE`/`CONFLICTING`), the `None` no-fitness result, the 7-day staleness threshold, conflict
comparison semantics, tenant isolation, determinism, and the zero-persistence guarantee — none of
which this Artifact Authorization or its implementation may reinterpret. The CDD-031 Evidence Fitness
Exposure Clarification and Remediation Report (APPROVED CLARIFICATION) is the sole permission
authority narrowing CDD-031 §22 to permit exactly the one endpoint CDD-034 defines. CDD-034 itself
(FROZEN) is the exposure/API contract authority this Artifact Authorization implements.

## 3. Implementation objective

Prove that Gate T's real, tested Evidence Fitness computation can be safely, truthfully exposed
through one new, narrow, read-only REST endpoint — via thin composition of already-existing,
unmodified Gate I/H4/Gate T application services — without inventing, duplicating, or reinterpreting
any of their semantics, and without weakening any frozen firewall established by CDD-029, CDD-031, or
the Clarification Report.

## 4. Authorized implementation slices (binding)

**Slice 1 — Composition.** The new application service and its unit + PostgreSQL-integration tests
(items 3, 8, 9). **Slice 2 — API exposure.** The new API package (router, schemas, dependencies) and
its router-level tests (items 4, 5, 6, 7, 10). **Slice 3 — Registration / architecture enforcement.**
The two narrow existing-file modifications required for the endpoint to exist and be authorizable,
plus the mechanically required registration of the new paths with the repository's own exhaustive
changed-path architecture test (items 1, 2, 11).

Total: 3 + 5 + 3 = 11 files. No implementation phase may introduce a fourth slice or reassign a file
to an unlisted slice without a new, separate Product Owner decision.

## 5. Exact authorized allowlist

**AUTHORIZED_CHANGE (existing files, MODIFY only — exact change described, nothing else in the file):**

1. `backend/app/main.py` — add exactly one import statement and one
   `app.include_router(information_element_evidence_fitness_router)` call, identical in shape to the
   existing 10 router registrations already in this file. No modification to
   `_STABLE_ERROR_CONTRACT_PATHS`, to any exception handler, to any other router registration, or to
   any other part of this file.
2. `keycloak/ctec-realm.json` — add exactly one new object to the top-level `clientScopes` array
   (`information-element-evidence-fitness:read`, mirroring `entity-resolution:read`'s exact shape) and
   exactly one new string to the `ctec-frontend` client's `defaultClientScopes` array. No modification
   to any other scope, client, or realm setting — specifically, no addition or modification of
   `information-element-context:read` (POST-U/X-DEBT-6, explicitly out of scope).
11. `backend/app/tests/test_runtime_architecture.py` — add exactly one new, additive, comment-labeled
    CDD-034 block to the existing `AUTHORIZED_CHANGED_PATHS` set, listing exactly the 8 CREATE paths
    (items 3–10 below), mirroring the existing Gate O block (lines 518–525 at this document's
    authority base) and Gate T block (lines 543–548) exactly. Mechanical verification against this
    document's authority base confirms `backend/app/main.py`, `keycloak/ctec-realm.json`, and this
    file's own path are already members of `AUTHORIZED_CHANGED_PATHS` (added generically, pre-existing
    at lines 111, 272, and 62 respectively) — so no other file requires this registration, and this
    block must not re-list them. No modification to any existing Gate O/Gate T/other block, to the
    `test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists` assertion logic, to
    `test_runtime_imports_only_standard_library_and_runtime_modules`, to
    `test_runtime_package_contains_only_authorized_top_level_files`, or to any other test in this
    file. No exclusion, skip, xfail, or conditional bypass of any kind.

**AUTHORIZED_NEW (CREATE only):**

3. `backend/app/application/information_element_evidence_fitness_resolution.py` — thin
   composition/exposure application service implementing CDD-034 §13's 11-step pipeline: generates the
   single UTC timestamp, resolves the Blueprint, evaluates Gate I coverage, performs the minimal
   Information-Element name-matching (§14's accepted duplication), short-circuits on `UNMAPPED` before
   ever constructing H4 or Gate T, otherwise invokes H4 then Gate T unmodified, and returns the four-
   field result. Zero new semantic classification logic.
4. `backend/app/api/information_element_evidence_fitness/__init__.py` — package marker, mirroring
   `backend/app/api/information_element_context/__init__.py` exactly. No logic.
5. `backend/app/api/information_element_evidence_fitness/router.py` — FastAPI router exposing exactly
   `POST /api/v1/information-element-evidence-fitness/resolve`, enforcing the
   `information-element-evidence-fitness:read` scope, mapping errors per CDD-034 §18. No second
   endpoint.
6. `backend/app/api/information_element_evidence_fitness/schemas.py` — closed (`extra="forbid"`)
   request/response Pydantic models matching CDD-034 §8-§9 exactly, including `source_field_id: UUID |
   None` and `fitness_status: Literal["FIT","STALE","CONFLICTING"] | None`.
7. `backend/app/api/information_element_evidence_fitness/dependencies.py` — DI wiring reusing the
   existing `Container.ontology_sessions` attribute exactly as
   `information_element_context/dependencies.py` does. No new `Container` field.
8. `backend/app/tests/test_information_element_evidence_fitness_resolution.py` — unit tests for item 3
   (see §17).
9. `backend/app/tests/test_information_element_evidence_fitness_resolution_postgres.py` — the same
   behaviors proven against real Postgres-backed `FieldValueEvidenceRepositoryImpl`.
10. `backend/app/tests/test_information_element_evidence_fitness_router.py` — router-level tests using
    a `FakeService` + `TestClient` dependency-override pattern identical to
    `test_information_element_context_router.py`, including explicit call-recording proof that H4 and
    Gate T are never reached for `UNMAPPED`.

```
AUTHORIZED_CHANGE = 3
AUTHORIZED_NEW    = 8
TOTAL IMPLEMENTATION SURFACE = 11
```

No 12th implementation path, no directory wildcard, and no file reassigned to an unlisted slice is
authorized under any circumstance without a new, separate Product Owner decision.

## 6. Read-only dependencies

`backend/app/application/semantic_coverage_evaluation.py` (Gate I),
`backend/app/application/information_element_evidence_availability.py` (H4),
`backend/app/application/source_evidence_fitness_evaluation.py` (Gate T),
`backend/app/infrastructure/persistence/field_value_evidence_repository.py`
(`FieldValueEvidenceRepositoryImpl`), `backend/app/application/blueprint_service.py`
(`BlueprintApplicationService`), `backend/app/core/dependency_container.py` (`Container`,
specifically its existing `ontology_sessions` attribute), `backend/app/api/supplier_risk/dependencies.py`
(`container`, `principal`), `backend/app/api/supplier_risk/authentication.py` (`TrustedPrincipal`) —
consumed by call only, never modified.

## 7. Explicitly forbidden files/domains (binding)

`backend/app/application/information_element_context_resolution.py` and every file under
`backend/app/api/information_element_context/` (Gate O — no import, no call, no modification beyond
read-only precedent study); `source_evidence_fitness_evaluation.py`,
`source_evidence_fitness_impact_remediation.py` (Gate T); `semantic_coverage_evaluation.py` (Gate I);
`information_element_evidence_availability.py` (H4); any file under `frontend/`; any migration file;
any modification to `_STABLE_ERROR_CONTRACT_PATHS`; any modification to
`information-element-context:read` in `keycloak/ctec-realm.json`; any new field on
`backend/app/core/dependency_container.py`'s `Container`; any existing block, assertion, or test
function within `backend/app/tests/test_runtime_architecture.py` other than the one additive CDD-034
block authorized in §5 item 11; CDD-031, the Clarification Report, CDD-034, and this Artifact
Authorization itself.

## 8. Route/endpoint authorization (binding)

```
POST /api/v1/information-element-evidence-fitness/resolve  — IMPLEMENT NOW (the only endpoint)
```

No other route under this or any related path is authorized.

## 9. Consumed-API/collaborator authorization (binding)

Only: `SemanticCoverageEvaluationApplicationService.evaluate(...)` (Gate I, unmodified),
`InformationElementEvidenceAvailabilityApplicationService.evaluate(...)` (H4, unmodified),
`SourceEvidenceFitnessEvaluationApplicationService.evaluate(...)` (Gate T, unmodified),
`BlueprintApplicationService.get_approved_by_name(...)` (unmodified),
`FieldValueEvidenceRepositoryImpl.get_by_source_field(...)` (unmodified, via H4/Gate T's own existing
Protocol contracts). No other application service, repository, or Gate O/F/U/S/V/Q capability may be
called by any file in this allowlist.

## 10. Backend/API expansion discipline (binding)

Exactly one new REST endpoint, authorized solely by the Clarification Report's narrow §22 supersession.
No second endpoint, no new query parameter beyond §8's two request fields, no new repository method
(the existing `get_by_source_field` suffices), no new migration.

## 11. Persistence / migration / authentication / Keycloak discipline (binding)

Zero new persistence of any domain result (CDD-031 §20 restated). Zero migration. Authentication reuses
Gate E's existing OIDC/`TrustedPrincipal` mechanism exactly. The sole authorized Keycloak change is item
2 in §5 — one new scope object and one client assignment, nothing else.

## 12. UNMAPPED short-circuit boundary (binding)

The new application service (item 3) must check `CoverageStatus` immediately after resolving the
matching `InformationElementCoverageResult` and, for `UNMAPPED`, return
`(requirement_id, source_field_id=None, fitness_status=None, evaluated_at)` **without constructing
either `InformationElementEvidenceAvailabilityApplicationService` or
`SourceEvidenceFitnessEvaluationApplicationService`**. Item 10 (router tests) must prove this via a
call-recording fake, not merely by inspecting the returned response shape.

## 13. Single-timestamp boundary (binding)

Exactly one `datetime.now(UTC)` call, at the very start of the application service's entry method,
before Blueprint resolution. That one value is used, unmodified, as both the returned `evaluated_at`
(every branch) and Gate T's `as_of` argument (`MAPPED` branch only). No second timestamp generation
anywhere in the implementation. No request field may ever accept a caller-supplied `as_of` or
`evaluated_at`.

## 14. Gate O firewall (binding)

Item 3 may reproduce, at most, the minimal Information-Element name-matching mechanics already
identified in A7 (§14 of CDD-034) — never by importing, calling, or modifying
`information_element_context_resolution.py` or any file under
`backend/app/api/information_element_context/`. No shared helper may be extracted from Gate O during
this implementation.

## 15. Gate F firewall (binding)

No Gate F file is imported, called, or referenced. No Supplier identifier appears in any request,
response, or internal type introduced by this allowlist.

## 16. Gate U / generalized-DQ / Gate S / Gate V / MCP firewall (binding)

No `what_if_simulation.py` dependency. No DQ Rule/Finding/Impact/Remediation type or route. No
approval workflow. No agent execution. No MCP invocation.

## 17. Test obligations (binding, minimum set)

`test_information_element_evidence_fitness_resolution.py` and its `_postgres.py` counterpart must
prove, at minimum: `UNMAPPED` → correct four-field result AND H4/Gate T never constructed (call-
recording, not inference); `MAPPED` + `NO_EVIDENCE`/`EVIDENCE_EMPTY` → real `source_field_id`, null
`fitness_status`; `MAPPED` + `EVIDENCE_PRESENT` → `FIT`/`STALE`/`CONFLICTING` propagated verbatim from
Gate T; exactly one timestamp generated, identical value in `evaluated_at` and Gate T's `as_of`; zero
write to any persistence store. `test_information_element_evidence_fitness_router.py` must prove, at
minimum: authentication required (401); `information-element-evidence-fitness:read` scope required
(403 without it, via a call-recording fake proving the service is never reached when under-scoped —
mirroring Gate O's own router test exactly); request schema rejects `tenant_id`/`as_of`/`evaluated_at`
(422); `BLUEPRINT_NOT_FOUND`/`INFORMATION_ELEMENT_NOT_FOUND`/`INFORMATION_ELEMENT_NAME_AMBIGUOUS` map
to their existing HTTP/detail-code shapes exactly. Plus: the complete existing Gate T, Gate O, Gate I,
H4, and Gate X test suites must pass unmodified, and the existing
`test_runtime_architecture.py` suite (including
`test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists`,
`test_runtime_imports_only_standard_library_and_runtime_modules`, and
`test_runtime_package_contains_only_authorized_top_level_files`) must continue to pass with its
existing assertion semantics wholly unweakened, extended only by the one additive block item 11
authorizes.

## 18. Implementation stop conditions

Implementation must STOP and return to Product Owner review if: `origin/main` moves from the approved
baseline before implementation-branch creation; CDD-031, the Clarification Report, or CDD-034 changes;
this Artifact Authorization changes; any §5 path proves insufficient; a 12th implementation file is
required; any §7 forbidden path proves necessary; persistence, a migration, a new backend endpoint
beyond §8, or a `dependency_container.py`/`_STABLE_ERROR_CONTRACT_PATHS` change becomes necessary; a
Gate O/T/I/H4/X modification appears necessary; POST-U/X-DEBT-6 remediation appears necessary; MCP
execution, human approval, or agent behavior appears necessary; the required §5 item 11 registration
block would need to weaken, skip, or bypass any existing assertion rather than purely add to
`AUTHORIZED_CHANGED_PATHS`. No exception for a "small harmless extra file." Total implementation
surface is exactly 11 files; no 12th is authorized under any circumstance without a new Product Owner
decision.

## 19. Acceptance criteria

1. `POST /api/v1/information-element-evidence-fitness/resolve` returns exactly the four fields in
   CDD-034 §9.
2. `UNMAPPED` returns HTTP 200 with `source_field_id: null`, `fitness_status: null`, and is proven
   (via call-recording test) never to invoke H4 or Gate T.
3. `MAPPED` null-fitness states (`NO_EVIDENCE`/`EVIDENCE_EMPTY`) return a real, non-null
   `source_field_id`.
4. `fitness_status` values are provably identical to what direct, unmodified invocation of Gate T's
   own `evaluate(...)` would produce for the same inputs.
5. `evaluated_at` is provably the same real timestamp passed to Gate T as `as_of`, in every `MAPPED`
   test case.
6. Zero write occurs to any persistence store, proven by test.
7. Gate T's, Gate O's, Gate I's, H4's, and Gate X's own existing test suites pass unmodified.
8. `test_runtime_architecture.py`'s existing assertions pass unweakened, extended only by the one
   additive CDD-034 block authorized in §5 item 11.
9. No file outside the exact 11-item allowlist is created or modified.
10. `information-element-evidence-fitness:read` is required and enforced; `information-element-context
    :read` is not added, modified, or referenced.
11. `tenant_id` is never accepted from request input.
12. `backend/app/main.py`'s `_STABLE_ERROR_CONTRACT_PATHS` is unchanged.

## 20. Implementation PR strategy

Recommend a single implementation PR covering all three slices together, given the total surface is
only 11 files and Slice 3 (registration) has no effect and cannot be independently tested without
Slices 1-2 already present — unlike Gate X's multi-PR product-surface rollout, this is a single,
tightly-coupled backend capability with no safe intermediate product state to split across PRs. A
combined PR remains subject to this repository's own exact-head merge-authorization discipline
identically.

## 21. Merge requirements

The implementation PR requires its own separate, explicit Product Owner exact-head merge
authorization — matching every prior gate's precedent in this lineage.

## 22. Closure criteria

All 11 authorized files present and correct; all 12 acceptance criteria in §19 pass; zero P0/P1 at
every implementation checkpoint; no unauthorized file ever enters a merge; the full existing test
suite (backend and frontend) remains green, including `test_runtime_architecture.py` unweakened.

## 23. Authorization

This Artifact Authorization is **approved for publication**, reached via A7 (exact-physical-surface
discovery) → A8 (drafting, adversarial review, Product Owner approval of the then-10-file surface) →
A9 pre-flight (discovering the mechanically required runtime-architecture allowlist registration) →
A9-D1 (Product Owner correction to the 11-file surface: 8 CREATE + 3 MODIFY) → this publication turn.
**Publication/freeze of this Artifact Authorization does NOT itself authorize implementation.** A
separate, subsequent Product Owner implementation authorization remains required before any file in
§5 may be created or modified — matching every prior gate's identical multi-step discipline in this
lineage (CDD-025 through CDD-031).
