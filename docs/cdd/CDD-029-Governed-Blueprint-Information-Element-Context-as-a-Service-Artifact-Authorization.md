# CDD-029 — Governed Blueprint Information-Element Context-as-a-Service — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `39327e90225ec84fe1a3034065fc68e7e34bf68e`

## 1. Authority and scope

CDD-029 (FROZEN, PUBLISHED at `39327e90225ec84fe1a3034065fc68e7e34bf68e`) authorizes Gate O's architecture but
not implementation (§32: "a separate, subsequent Artifact Authorization companion remains required before any
file is created or modified"). This is that companion. It enumerates exactly which repository artifacts Gate O
implementation may create or modify to satisfy frozen CDD-029 — and nothing more. This document alone does not
authorize implementation; a separate, subsequent Product Owner implementation authorization remains required.

This record was produced through: discovery against the actual repository (Gate O5, which traced every proposed
artifact to a concrete precedent — `ontology_modeling`'s package shape and session-dependency pattern,
`ontology_copilot`'s closed-model precedent, `entity_resolution`'s HTTP-status precedents, and confirmed by
`git log` that neither `keycloak/ctec-realm.json` nor `dependency_container.py` needed touching for Gate M's own
comparable scope introduction), Product Owner review resolving two interpretive refinements (Gate O6,
demoting Gate P from normative dependency to non-normative precedent, and reframing the internal Python
result encoding as authorized-but-not-independently-frozen), and explicit Product Owner approval of the
revised draft, P0=0/P1=0/P2=0 at every stage (O5 and O6).

## 2. Implementation objective

Prove, at a new, standalone application-service and API layer, that an authenticated, tenant-scoped,
non-Ask-CTEC consumer can retrieve the already-governed context (Gate I semantic coverage + H4 evidence
availability, composed by Gate N) for one Blueprint `InformationElementRequirement`, through a deterministic,
structured, machine-addressable contract — while the entire reused chain (`BlueprintApplicationService`,
`SemanticCoverageEvaluationApplicationService`, `InformationElementEvidenceAvailabilityApplicationService`,
`InformationElementContextAvailabilityApplicationService`) remains completely unmodified, and while Ask CTEC
(Gate P) remains completely unmodified and unconsumed.

## 3. Exact artifact allowlist

CREATE:
- `backend/app/application/information_element_context_resolution.py`
- `backend/app/api/information_element_context/__init__.py`
- `backend/app/api/information_element_context/router.py`
- `backend/app/api/information_element_context/schemas.py`
- `backend/app/api/information_element_context/dependencies.py`
- `backend/app/tests/test_information_element_context_resolution.py`
- `backend/app/tests/test_information_element_context_resolution_postgres.py`
- `backend/app/tests/test_information_element_context_router.py`

MODIFY (exact change only, nothing else in either file):
- `backend/app/main.py` — exactly one import of the new router and exactly one
  `app.include_router(information_element_context_router)` call, inserted alongside the existing router
  registrations. `_STABLE_ERROR_CONTRACT_PATHS` is explicitly **not** authorized to change.
- `backend/app/tests/test_runtime_architecture.py` — exactly one new, additive, comment-labeled Gate O block
  in `AUTHORIZED_CHANGED_PATHS` listing exactly the 8 CREATE paths above. No unrelated architecture-test
  refactoring.

```
AUTHORIZED_NEW  = 8
AUTHORIZED_CHANGE = 2
TOTAL IMPLEMENTATION SURFACE = 10
```

No 11th implementation path is authorized under any circumstance without a new, separate Product Owner
decision. There is no exception for a small, mechanical, convenient, formatting-only, test-only,
configuration-only, or otherwise "harmless" additional file.

## 4. Explicitly not required / not authorized

`backend/app/core/dependency_container.py` must remain unchanged — the existing `Container.ontology_sessions`
attribute (already reused by `ontology_modeling`, itself unrelated to Gate O) is sufficient; no new `Container`
field is added or read beyond that one, already-present attribute. `keycloak/ctec-realm.json` must remain
unchanged — direct inspection confirms Gate M's own three new scope literals
(`ontology-modeling:propose/approve/publish`) were introduced without any realm-file change, and production
`OidcJwtVerifier` trusts validated token scopes without consulting this file at runtime. `backend/app/tests/
conftest.py` must remain unchanged — the existing `migrated_engine` fixture, already consumed unmodified by
`ontology_modeling`'s own Postgres test, suffices; Gate O's Postgres test defines any further fixtures locally.
`architecture/INDEX.md` is not part of the 10-file implementation surface (§3) — its own registration of this
Artifact Authorization is a governance-publication concern, performed once, in this document's own publication
commit, not an implementation authorization, and must not be read as authorizing any future implementation
change to that file.

## 5. Module contracts

**Application-service dependency boundary** (Gate O6 refinement — binding): *The Gate O application service
shall reuse the existing governed Blueprint, Gate I, H4, and Gate N application boundaries without modifying or
reimplementing their semantic authority. Dependency construction shall follow existing repository conventions
and remain entirely within the authorized Gate O artifacts.* `InformationElementContextResolutionApplicationService`
(in `information_element_context_resolution.py`): constructor accepting a database session; a `resolve` method
accepting the authenticated `TrustedPrincipal`, a Blueprint name, and an Information Element name, returning an
authorized internal typed result (§ below). It depends on the existing, unmodified `BlueprintApplicationService`,
`SemanticCoverageEvaluationApplicationService` (Gate I), `InformationElementEvidenceAvailabilityApplicationService`
(H4), `InformationElementContextAvailabilityApplicationService` (Gate N), and their existing read repositories
— constructed however existing repository convention for this dependency chain requires, entirely within this
one authorized file. Gate P's own orchestration code (`ontology_copilot_api.py`) is **non-normative** precedent
only, showing the pattern is safe and possible — it is never imported, depended upon, or treated as the
required shape of Gate O's own internals, and Gate P itself is never modified.

**Internal result representation** (Gate O6 refinement — binding): *Gate O may implement an internal typed
resolution result containing exactly the outcome information necessary to implement CDD-029. It must not
introduce additional externally observable semantic states or response fields.* The authorized outcome set is
exactly: `RESOLVED`, `BLUEPRINT_NOT_FOUND`, `INFORMATION_ELEMENT_NOT_FOUND`, `INFORMATION_ELEMENT_NAME_AMBIGUOUS`,
`UPSTREAM_INTEGRITY_FAILURE` — this set, and CDD-029's own §15 HTTP-mapping table, are what is frozen; no
particular Python encoding of it (e.g. a `StrEnum` + frozen `dataclass`, or an equivalent alternative confined
to this one authorized file) is itself independently frozen architecture.

**Router** (`backend/app/api/information_element_context/router.py`): `POST
/api/v1/information-element-context/resolve`, scope `information-element-context:read` enforced before the
service is constructed, reusing the existing `TrustedPrincipal`/`principal`/`container`/`correlation_id`
dependencies and the existing `_authorize`/`SecurityAuditService`-audit-on-denial pattern (no shared
authorization refactor; no modification to any existing router). The five outcomes map to CDD-029 §15's exact,
frozen HTTP table: `RESOLVED` → 200 with the response below and no `status` field; `BLUEPRINT_NOT_FOUND` → 404;
`INFORMATION_ELEMENT_NOT_FOUND` → 404; `INFORMATION_ELEMENT_NAME_AMBIGUOUS` → 422; `UPSTREAM_INTEGRITY_FAILURE`
→ 500. This HTTP mapping is not reopened by this Artifact Authorization.

**Schemas** (`backend/app/api/information_element_context/schemas.py`): a locally-defined closed request model
(`extra="forbid"`, not imported from `ontology_copilot.schemas`) with exactly `blueprint_name: str` and
`information_element_name: str` — no `tenant_id`, no optional field. A response model with exactly the seven
CDD-029 §12 governed fields (`blueprint_id`, `blueprint_version_number`, `information_element_requirement_id`,
`information_element_name`, `obligation`, `coverage_status`, `evidence_availability_status`) and no `status`
field, no raw evidence, no tenant data, no confidence/trust/readiness/remediation field.

**Dependencies** (`backend/app/api/information_element_context/dependencies.py`): a yield-based session
dependency reusing `Container.ontology_sessions` (no `Container` change; `HTTPException(503, ...)` if unset,
mirroring `ontology_modeling_session`'s own unavailability handling) that performs **no `session.commit()`
call** — Gate O is read-only — plus a service-construction dependency.

## 6. Persistence / migration / frontend / provider / MCP

Migration: **NONE**. New persistence: **NONE**. Persistence-model modification: **NONE**.
Repository/schema modification: **NONE**. Existing read repositories may be consumed unchanged. Frontend:
**NONE**. Real model provider: **NOT AUTHORIZED**. LLM invocation: **NOT AUTHORIZED**. Embeddings/vector
DB/RAG: **NOT AUTHORIZED**. Agent reasoning: **NOT AUTHORIZED**. MCP: **NOT AUTHORIZED**. Gate Q: **NOT
AUTHORIZED**. Connector framework: **NOT AUTHORIZED**. Ask CTEC modification: **NONE**.

## 7. Forbidden implementation areas

No modification is authorized to: `backend/app/application/ontology_copilot_api.py` or any Ask CTEC API/
frontend file; `backend/app/application/blueprint_service.py`; `backend/app/application/
semantic_coverage_evaluation.py` (Gate I); `backend/app/application/information_element_evidence_availability.py`
(H4); `backend/app/application/information_element_context_availability.py` (Gate N); any Gate I/H4/Gate N/
Gate P repository, ORM model, or test file; Gate J (`gap_impact_remediation.py`) and its files; Gate K
(`information_element_decision_prerequisite_assessment.py`) and its files; any Gate M `ontology_modeling` file;
any migration file; any `frontend/*` file; any frozen CDD or existing Artifact Authorization; released
architecture. If implementation discovers a genuine need to touch any of these: **STOP** — return to Product
Owner review; this Artifact Authorization does not expand to accommodate it.

## 8. Test obligations

The three CREATE test files (§3) must collectively prove CDD-029 §25/§26 in full, at minimum: `MAPPED`+
`AVAILABLE`; `MAPPED`+`UNAVAILABLE`; `UNMAPPED`; Blueprint not found; Information Element not found;
Information Element name ambiguity (422, distinct from integrity failure); upstream integrity failure (500,
both trigger sites — duplicate Approved Blueprint name, and a Gate N/Gate I inconsistency); determinism (two
equivalent calls, byte-identical result); Gate I/H4/Gate N passthrough proven bit-for-bit against directly-
called Gate I/H4 results; tenant isolation (a Tenant-A caller requesting a globally-defined element whose only
mapping belongs to Tenant B receives `UNMAPPED`, never a leaked `MAPPED`); zero writes (row counts unchanged
before/after); 401; 403 (`AUTHORIZATION_SCOPE_REQUIRED`); 404 (both reasons); 422 (both reasons — closed-schema
rejection and name ambiguity); 500; a request body containing `tenant_id` rejected by the closed schema; the
exact seven-field successful response; absence of a successful `status` field; no raw evidence leakage. No
fourth Gate O test file. No `conftest.py` modification.

## 9. Implementation stop conditions

Implementation must STOP and return to Product Owner review if: `origin/main` moves from the subsequently
approved implementation baseline before implementation branch creation; CDD-029 changes; this Artifact
Authorization changes; any §3 path proves insufficient; an 11th implementation file is required; any §7
forbidden file appears necessary; persistence, migration, frontend, model/provider, or MCP/Gate Q work becomes
necessary; the API endpoint, scope literal, request contract, response contract, or HTTP mapping would need to
change; semantic authority would need to change; CI cannot pass without scope expansion; a branch-protection
bypass would be required. No exception for a "small harmless extra file."

## 10. Publication / implementation boundary

**Publication/freeze of this Artifact Authorization does NOT itself authorize Gate O implementation.** After
this document is published: CDD-029 remains FROZEN, this Artifact Authorization becomes APPROVED/FROZEN, and
Gate O implementation remains **NOT STARTED**. A separate, subsequent Product Owner implementation
authorization is required before any file in §3 may be created or modified — matching every prior gate's
identical multi-step discipline in this lineage (CDD-025, CDD-026, CDD-027, CDD-028).
