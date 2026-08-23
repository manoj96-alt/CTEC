# GATE M — GOVERNED VISUAL ONTOLOGY MODELING (NET-NEW ONLY) — ARTIFACT AUTHORIZATION

Version: 1.1
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `2cdff957be398846a1d123bc6ec0c653fd07dc95`

## 1. Authority and scope

Implements CDD-028 (FROZEN, `docs/cdd/CDD-028-Governed-Visual-Ontology-Modeling-with-Proposal-Approval-and-Publication.md`, authority base above) in full, including its own §30 frontend-extension authorization. Backend and frontend are both authorized by this single Artifact Authorization.

## 2. Implementation objective

Prove: an authenticated `ontology-modeling:propose` principal can submit a net-new Concept or Relationship proposal; an authenticated `ontology-modeling:approve` principal can approve or durably reject it; an authenticated, independently-scoped `ontology-modeling:publish` principal can publish an Approved proposal into the canonical ontology as its initial representation — with zero canonical writes at any step before PUBLISH, and zero modification to `resolver.py` or any existing canonical table's columns or constraints — proven through a real, minimal, authenticated UI, not backend-only.

## 3. Exact artifact allowlist

CREATE (backend):
- `backend/app/domain/ontology_modeling/__init__.py`
- `backend/app/domain/ontology_modeling/proposal.py`
- `backend/app/infrastructure/persistence/models/ontology_change_proposal.py`
- `backend/app/infrastructure/persistence/migrations/versions/0017_ontology_change_proposal.py`
- `backend/app/infrastructure/persistence/ontology_change_proposal_repository.py`
- `backend/app/application/ontology_modeling_proposal_governance.py`
- `backend/app/api/ontology_modeling/__init__.py`
- `backend/app/api/ontology_modeling/router.py`
- `backend/app/api/ontology_modeling/schemas.py`
- `backend/app/api/ontology_modeling/dependencies.py`
- `backend/app/tests/test_ontology_modeling_proposal_governance.py`
- `backend/app/tests/test_ontology_modeling_proposal_lifecycle_postgres.py`
- `backend/app/tests/test_ontology_modeling_router.py`

CREATE (frontend):
- `frontend/lib/ontology-modeling/api-client.ts`
- `frontend/lib/ontology-modeling/contracts.ts`
- `frontend/app/ontology-studio/ontology-modeling/page.tsx`
- `frontend/app/ontology-studio/ontology-modeling/_components/ontology-modeling-workspace.tsx`
- `frontend/app/ontology-studio/ontology-modeling/_components/propose-form.tsx`
- `frontend/app/ontology-studio/ontology-modeling/_components/proposal-list.tsx`
- `frontend/app/ontology-studio/ontology-modeling/_components/decision-dialog.tsx`
- `frontend/app/ontology-studio/_components/ontology-modeling-link-card.tsx`
- `frontend/tests/ontology-modeling-workspace.test.tsx`

MODIFY:
- `backend/main.py` (exactly one new router-registration line: `app.include_router(ontology_modeling_router)`, mirroring the existing `entity_resolution`/`ontology_copilot` registration pattern; no other line changed)
- `backend/app/tests/test_runtime_architecture.py` (exactly the 13 backend CREATE paths above as new `AUTHORIZED_CHANGED_PATHS` entries; no other line changed)
- `frontend/app/ontology-studio/_components/studio-client.tsx` (exactly 2 new lines: one import — `import { OntologyModelingLinkCard } from "./ontology-modeling-link-card";` — and one render call — `<OntologyModelingLinkCard />` — inserted immediately adjacent to the existing `<EntityResolutionLinkCard />`/`<AskCtecLinkCard />` calls; no other line changed)

22 CREATE + 3 MODIFY total. No 23rd/4th artifact is authorized. No wildcard authorization of any kind. No change to `frontend/app/ontology-studio/_components/ontology-graph.tsx`, `frontend/lib/ontology-studio/{api-client,contracts}.ts`, or any Entity Resolution/Ask CTEC frontend file. No `dependency_container.py` change is authorized — the router constructs its repository/service per-request from the existing `Container`/`principal` dependencies, mirroring `entity_resolution`'s own `dependencies.py` pattern. No `resolver.py` change. No `entity_type_repository.py`/`relationship_type_repository.py` change. No `ontology_seed.py` change. No Keycloak/auth-configuration file change.

## 4. Module contracts (binding)

### 4.1 `backend/app/domain/ontology_modeling/proposal.py`

```python
class ProposalKind(StrEnum):
    CREATE_CONCEPT = "CreateConcept"
    CREATE_RELATIONSHIP = "CreateRelationship"

class ProposalStatus(StrEnum):
    PROPOSED = "Proposed"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PUBLISHED = "Published"

@dataclass(frozen=True, slots=True)
class OntologyChangeProposal:
    ontology_change_proposal_id: Identifier
    proposal_kind: ProposalKind
    status: ProposalStatus
    proposed_entity_type_name: str | None
    proposed_definition: str | None
    proposed_relationship_type_name: str | None
    proposed_source_entity_type_id: Identifier | None
    proposed_target_entity_type_id: Identifier | None
    proposed_by: str
    proposed_on: datetime
    approved_by: str | None
    approved_on: datetime | None
    rejected_by: str | None
    rejected_on: datetime | None
    rejection_reason: str | None
    published_by: str | None
    published_on: datetime | None
    published_entity_type_id: Identifier | None
    published_relationship_type_id: Identifier | None
```

`__post_init__` enforces: `proposal_kind == CREATE_CONCEPT` implies `proposed_entity_type_name` is a non-empty, at most 200-char string and `proposed_relationship_type_name`/`proposed_source_entity_type_id`/`proposed_target_entity_type_id` are all `None`; `proposal_kind == CREATE_RELATIONSHIP` implies the inverse (name/source/target set, concept fields `None`); `rejection_reason` (if not `None`) is at most 1000 chars; every `*_by` field, if not `None`, is a non-empty string (never an `Identifier`, never FK-shaped).

### 4.2 `backend/app/infrastructure/persistence/models/ontology_change_proposal.py`

Table `ontology_change_proposals`, columns exactly as in §4.1's fields, including two partial unique indexes: `uq_ontology_change_proposals_approved_concept_name` (`proposed_entity_type_name`, `WHERE proposal_kind='CreateConcept' AND status IN ('Approved','Published')`) and `uq_ontology_change_proposals_approved_relationship_name` (`proposed_relationship_type_name`, `WHERE proposal_kind='CreateRelationship' AND status IN ('Approved','Published')`). `proposed_source_entity_type_id`/`proposed_target_entity_type_id`/`published_entity_type_id`/`published_relationship_type_id` carry FKs *into* `entity_types`/`relationship_types` (read-only references — this does not modify those tables' own columns or constraints). No FK on any `*_by` column.

### 4.3 `backend/app/infrastructure/persistence/ontology_change_proposal_repository.py`

```python
class OntologyChangeProposalRepository(Protocol):
    def create(self, proposal: OntologyChangeProposal) -> None: ...
    def get_by_id(self, ontology_change_proposal_id: UUID) -> OntologyChangeProposal | None: ...
    def update_status(self, proposal: OntologyChangeProposal) -> None: ...
    def list(self, *, status: ProposalStatus | None = None) -> list[OntologyChangeProposal]: ...

class OntologyChangeProposalRepositoryImpl:
    def __init__(self, session: Session) -> None: ...
    # create/get_by_id/update_status/list against ontology_change_proposals only.
```

`update_status` performs a `SELECT ... FOR UPDATE` on the target row before writing (the row-level lock underpinning §14's concurrency guarantee) and asserts the transition is one of the five valid ones in §12, raising `ValidationException` otherwise.

### 4.4 `backend/app/application/ontology_modeling_proposal_governance.py`

```python
class OntologyModelingProposalGovernanceApplicationService:
    def __init__(self, *, session: Session,
                 proposal_repository: OntologyChangeProposalRepository) -> None: ...

    def propose_concept(self, *, principal: TrustedPrincipal, entity_type_name: str,
                         definition: str | None) -> OntologyChangeProposal: ...
    def propose_relationship(self, *, principal: TrustedPrincipal, relationship_type_name: str,
                              source_entity_type_id: UUID, target_entity_type_id: UUID
                              ) -> OntologyChangeProposal: ...
    def approve(self, *, principal: TrustedPrincipal,
                proposal: OntologyChangeProposal) -> OntologyChangeProposal: ...
    def reject(self, *, principal: TrustedPrincipal, proposal: OntologyChangeProposal,
               rejection_reason: str | None) -> OntologyChangeProposal: ...
    def publish(self, *, principal: TrustedPrincipal,
                proposal: OntologyChangeProposal) -> OntologyChangeProposal: ...
```

`propose_concept`/`propose_relationship` validate input shape and, for relationships, that both endpoint `EntityType` rows exist/`Active`/`Approved` at propose time (a non-binding, UX-quality pre-check — the binding check is `publish`'s own live re-validation); persist via `proposal_repository.create()` with `status=PROPOSED`, `proposed_by=principal.principal_id`. `approve`/`reject` require `proposal.status == PROPOSED`, transition via `update_status`. `publish` requires `proposal.status == APPROVED`; performs the exact transactional sequence in §13; writes canonical rows via direct `session.add()` calls constructing `EntityType`/`InstitutionalConcept`/`RelationshipType`/`OntologyRelationshipBinding` ORM instances with `created_by=BOOTSTRAP_SYSTEM_ENTITY_ID`, `version_number=1`, `previous_version_id=None`, `governance_status="Approved"` — never via `entity_type_repository.py`/`relationship_type_repository.py` (both remain unused) and never with `principal.principal_id` in any canonical FK column.

### 4.5 `backend/app/api/ontology_modeling/{router,schemas,dependencies}.py`

Six endpoints exactly as in §10. `dependencies.py` mirrors `entity_resolution/dependencies.py`'s `steward_api_service`-style per-request construction. `router.py` reuses the exact `_authorize(authenticated, scope, dependencies, correlation)` pattern of `entity_resolution/router.py` — `if scope in authenticated.scopes: return`, else `SecurityAuditService.record(...)` + `HTTPException(403, {"code": "AUTHORIZATION_SCOPE_REQUIRED"})`. No new authorization mechanism of any kind is introduced; only three new scope literals (`ontology-modeling:propose`, `ontology-modeling:approve`, `ontology-modeling:publish`) are referenced in code — their Keycloak/config registration is explicitly not performed by this Artifact Authorization (§10).

### 4.6 `frontend/lib/ontology-modeling/api-client.ts`

Mirrors `lib/entity-resolution/api-client.ts` exactly: `accessToken()`, `Authorization: Bearer`, `browserAuthConfig().apiOrigin + "/api/v1/ontology-modeling"` base, `OntologyModelingApiError extends Error` carrying an `ApiProblem`. Exposes exactly:
```typescript
export const ontologyModelingApi = {
  proposeConcept: (body: ProposeConceptBody) => Promise<ProposalDetail>,
  proposeRelationship: (body: ProposeRelationshipBody) => Promise<ProposalDetail>,
  listProposals: (status?: ProposalStatus) => Promise<ProposalDetail[]>,
  getProposal: (id: string) => Promise<ProposalDetail>,
  approve: (id: string) => Promise<ProposalDetail>,
  reject: (id: string, rejectionReason?: string) => Promise<ProposalDetail>,
  publish: (id: string) => Promise<ProposalDetail>,
};
```
No other method. No direct database or canonical-table access of any kind exists in this file, or in any frontend file — the browser has no persistence access whatsoever; every write is mediated exclusively through these seven calls, each hitting one of the six backend endpoints in §10.

### 4.7 `frontend/lib/ontology-modeling/contracts.ts`

TypeScript types mirroring the backend's `ProposalKind`/`ProposalStatus`/`OntologyChangeProposal` field names exactly (snake_case, matching `contracts.ts`'s existing repository convention) — `ProposeConceptBody { entity_type_name: string; definition?: string }`, `ProposeRelationshipBody { relationship_type_name: string; source_entity_type_id: string; target_entity_type_id: string }`, `ProposalDetail` mirroring §4.1's dataclass fields.

### 4.8 `frontend/app/ontology-studio/ontology-modeling/page.tsx`

```tsx
import { OntologyModelingWorkspace } from "./_components/ontology-modeling-workspace";
export default function Page() {
  return <div className="max-w-5xl"><OntologyModelingWorkspace /></div>;
}
```
Byte-for-byte structural mirror of `entity-resolution/page.tsx`.

### 4.9 `_components/ontology-modeling-workspace.tsx`

Top-level composition: fetches the existing, unmodified, read-only `ontologyApi.getOntology(...)` (from `lib/ontology-studio/api-client.ts`, imported by call only — not modified) to populate the Relationship-proposal source/target concept dropdowns and to render a small read-only reference view of the current ontology for context (VIEW, §12's first step); renders `<ProposeForm>`, `<ProposalList>`, and `<DecisionDialog>` (approve/reject/publish).

### 4.10 `_components/propose-form.tsx`

MODEL, deliberately form-based, not canvas-editing. A plain HTML form: a toggle between "New Concept" / "New Relationship"; for Concept, a name field (plus optional definition, informational only per CDD-028 §12's own "not a database-governed field" framing) and a client-side length check mirroring the backend's 200/2000-char bounds (UX sugar only — the backend re-validates authoritatively, per §4.1's `__post_init__`); for Relationship, a name field plus two `<select>` dropdowns populated from the already-loaded, read-only ontology (§4.9). Submitting calls `ontologyModelingApi.proposeConcept`/`proposeRelationship` (PROPOSE/SUBMIT, §12). No graph-canvas editing, no drag-and-drop node creation, no ReactFlow integration of any kind — deliberately, to satisfy CDD-028 §31's "no Palantir-scale visual modeling environment." `ontology-graph.tsx` itself is not imported or extended.

### 4.11 `_components/proposal-list.tsx`

REVIEW: a read-only table of proposals (`ontologyModelingApi.listProposals()`), showing `proposal_kind`, name, `status`, `proposed_by`, timestamps. No inline editing.

### 4.12 `_components/decision-dialog.tsx`

Mirrors `entity-resolution/_components/decision-dialog.tsx` structurally: a `<dialog>` per action (Approve / Reject / Publish), busy/error state, and — for Reject only — a bounded `rejection_reason` textarea (client-side length hint, backend-authoritative per CDD-028 §15). Approve/Publish dialogs carry no reason field. On a `409`-class `ApiProblem` (e.g. a name collision or an invalid-transition attempt caught server-side), the dialog surfaces the server's own message and prompts a list reload — generalizing the `STALE_RESOLUTION_CASE` UX pattern to Gate M's own fail-closed error codes (`PROPOSAL_ALREADY_APPROVED`, `CANONICAL_NAME_CONFLICT`, `AUTHORIZATION_SCOPE_REQUIRED`, etc.).

### 4.13 `_components/ontology-modeling-link-card.tsx`

A small card, structurally mirroring `entity-resolution-link-card.tsx`, linking to `/ontology-studio/ontology-modeling`.

## 5. Runtime architecture impact

None. No `runtime/orchestration.py`, `runtime/engine.py`, or `CapabilityStepPorts` change.

## 6. AI / agent firewall

No LLM, embeddings, RAG, vector database, agent framework, or MCP dependency may appear in any authorized artifact's imports, backend or frontend. Every operation in §4.4 is deterministic.

## 7. Human-authority boundary

PROPOSE/APPROVE/REJECT/PUBLISH each require a real, Gate-E-authenticated `TrustedPrincipal`. PUBLISH's authorization check is textually and structurally independent of APPROVE's (§10) — no code path allows an `ontology-modeling:approve`-scoped principal to publish without also holding `ontology-modeling:publish`. The frontend never determines authorization — it attempts an action and displays whatever the backend's independent `_authorize` check returns (§4.12).

## 8. Tenant boundary

No `tenant_id` parameter, column, or check appears anywhere in §4's contracts, backend or frontend.

## 9. Persistence/migration authorization

Exactly one migration (`0017_ontology_change_proposal.py`). It may: `CREATE TABLE ontology_change_proposals` with the exact columns in §4.2; create `proposalkind_t`/`proposalstatus_t` enum types; create the two partial unique indexes in §4.2; add the four FK constraints referencing `entity_types.entity_type_id`/`relationship_types.relationship_type_id` (read-only references). It may not: `ALTER` any column, index, constraint, or type on `entity_types`, `relationship_types`, `institutional_concepts`, or `ontology_relationship_bindings`. Migration-head chain: follows `0016_field_value_evidence.py`.

## 10. API authorization

Six endpoints:

| Method | Path | Scope | Source state | Result state | Canonical write? |
|---|---|---|---|---|---|
| POST | `/api/v1/ontology-modeling/proposals` | `ontology-modeling:propose` | — | `Proposed` | NO |
| GET | `/api/v1/ontology-modeling/proposals/{id}` | `:propose` OR `:approve` | any | unchanged | NO |
| GET | `/api/v1/ontology-modeling/proposals` | `:propose` OR `:approve` | any | unchanged | NO |
| POST | `/api/v1/ontology-modeling/proposals/{id}/approve` | `ontology-modeling:approve` | `Proposed` | `Approved` | NO |
| POST | `/api/v1/ontology-modeling/proposals/{id}/reject` | `ontology-modeling:approve` | `Proposed` | `Rejected` | NO |
| POST | `/api/v1/ontology-modeling/proposals/{id}/publish` | `ontology-modeling:publish` | `Approved` | `Published` | **YES — sole write** |

No PUT/PATCH/DELETE. This Artifact Authorization does not create, modify, or configure any Keycloak realm, client, or role — scope literals are referenced in application code only; test-identity wiring uses the existing test-fixture `TrustedPrincipal` construction pattern already used throughout the repository (a fabricated, test-local principal, never real Keycloak configuration).

## 11. Frontend authorization

Exactly the 9 CREATE + 1 MODIFY frontend artifacts in §3/§4.6-§4.13. The new `/ontology-studio/ontology-modeling` sub-route is fully self-contained (mirroring `entity-resolution/` and `ask/`'s own existing self-containment) and reuses `lib/ontology-studio/api-client.ts`'s existing `getOntology` call, unmodified, for VIEW/dropdown-population purposes only. No design-system expansion: reuses existing `<dialog>`, `.button`/`.secondary`, `.error-summary`, `.panel` classes already present in the codebase. No new dependency is added — ReactFlow is not used by any new frontend artifact.

## 12. State-transition contract

```
Proposed
    |
    | APPROVE                                    REJECT
    v                                              v
Approved                                      Rejected (terminal)
    |
    | PUBLISH
    v
Published (terminal)
```

Exactly five valid transitions: `Proposed→Approved`, `Proposed→Rejected`, `Approved→Published`. All others (`Proposed→Published`, `Rejected→Approved`, `Rejected→Published`, `Published→Published`, `Published→Rejected`, `Approved→Rejected`) raise `ValidationException` in the application service and surface as `409 CONFLICT` at the API layer. REVIEW is an action over a `Proposed` row, not a persisted state.

## 13. Publication transaction contract

Concept: one transaction — `SELECT ... FOR UPDATE` the proposal row; assert `status==APPROVED`; live re-`SELECT` `institutional_concepts`/`entity_types` for name collision, fail closed if found; `INSERT InstitutionalConcept` then `INSERT EntityType`; `UPDATE` proposal to `PUBLISHED` with attribution; commit. Relationship: same shape, additionally live-re-validating both endpoint `EntityType` rows (`Active`, `Approved`) before `INSERT RelationshipType` then `INSERT OntologyRelationshipBinding`. Any failure at any step rolls back the entire transaction — no partial canonical object, no partial proposal-status update, ever persists.

## 14. Concurrency/idempotency mechanism

Two partial unique indexes (§4.2/§9) prevent a second proposal from ever reaching `Approved` for an already-claimed name. `SELECT ... FOR UPDATE` on the proposal row (§4.3) serializes concurrent PUBLISH attempts on the same proposal. Live re-`SELECT` inside the PUBLISH transaction (§13) catches a canonical name claimed by a different, since-published proposal. All three mechanisms are H1-precedented (`uq_semantic_mappings_approved_source_field`, `pg_advisory_xact_lock`), none newly invented. A `409`-class response from a concurrent APPROVE/PUBLISH race is surfaced to the user via §4.12's stale/conflict UX, never silently retried or hidden.

## 15. Canonical attribution rule

Every canonical row written by §13: `created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID)`, never `principal.principal_id`. Every `OntologyChangeProposal` attribution field: `principal.principal_id` as a plain string, never wrapped in `Identifier`, never FK-constrained.

## 16. Test obligations

Backend: exactly the three CREATE test files in §3, covering: (1) create Concept proposal → no canonical mutation; (2) create Relationship proposal → no canonical mutation; (3) approve → no canonical mutation; (4) reject → durable rejection → no canonical mutation; (5) publish without approval → denied; (6) publish without publish authority → denied; (7) approved Concept publish → canonical object created; (8) approved Relationship publish → relationship + binding atomic; (9) duplicate Concept collision → fail closed; (10) duplicate Relationship collision → fail closed; (11) stale Relationship endpoint → fail closed; (12) concurrent publication → at most one success; (13) replay → no duplicate canonical object; (14) rejected proposal cannot publish; (15) published proposal cannot republish; (16) proposal actor provenance persisted; (17) canonical attribution remains valid; (18) canonical GET does not expose unpublished proposals; (19) frontend cannot directly write canonical ontology; (20) scope enforcement; (21) no existing-object modification path; (22) no downstream rewiring; (23) existing regression suite remains green.

Frontend: `frontend/tests/ontology-modeling-workspace.test.tsx`, mirroring `entity-resolution-workspace.test.tsx`'s own testing-library conventions, covering: propose-form renders and submits both Concept and Relationship payloads; proposal list renders fetched proposals; approve/reject/publish dialogs call the correct API method with the correct id; a `403`/`409` response renders the expected error/stale UX; no canonical-mutation call of any kind is ever made directly from a test or from any component (asserted via mocking `ontologyModelingApi` and confirming no `fetch` call targets any path outside `/api/v1/ontology-modeling/*`).

`backend/app/tests/test_runtime_architecture.py`'s 13-entry modification is the sole allowlist gate; no equivalent frontend-side allowlist gate exists in this repository.

## 17. CI obligations

`black --check`, `isort --check-only`, `ruff check`, `mypy app` (whole-app), and `pytest` (full suite) must all pass on every backend artifact; the existing frontend CI job's own lint/typecheck/test commands (unmodified by this AA) must pass on every new frontend artifact — before any PR is opened.

## 18. P0/P1/P2 acceptance criteria

P0 = 0 required: no canonical write outside `publish()`; no `principal_id` in any `enterprise_entities`-FK or `entity_types`/`relationship_types`-FK column; no modification to `resolver.py`, canonical table columns, or canonical uniqueness constraints; no 23rd/4th unauthorized artifact; no Keycloak/auth-config file touched; no Gate L/H/I/J/K/N/P production file imported or modified, backend or frontend; no Palantir-scale/canvas-editing scope creep; no design-system/dependency expansion.
P1 = 0 required: no endpoint beyond the six in §10; no table beyond the one in §9; no frontend artifact beyond the 9 CREATE + 1 MODIFY in §3; full test coverage of §16's areas.
P2: naming/ergonomics findings only, non-blocking.

## 19. STOP conditions

If implementation discovers any authorized artifact cannot be completed without touching an unlisted path — in particular `resolver.py`, `entity_type_repository.py`, `relationship_type_repository.py`, `ontology_seed.py`, `dependency_container.py`, any Keycloak config file, `ontology-graph.tsx`, `lib/ontology-studio/{api-client,contracts}.ts`, or any Entity Resolution/Ask CTEC frontend file — implementation MUST STOP and report the exact blocker.

## 20. Non-claims

This Artifact Authorization does not authorize: graph-canvas editing of any kind; any modification to `ontology-graph.tsx`; any new frontend dependency (ReactFlow or otherwise); any Keycloak/auth-configuration change; any modification to `resolver.py` or any canonical table's schema; any existing-object modification/rename/replace/retire/delete capability; any AI/agent/MCP capability; any Gate L deferred capability (real model-provider integration, durable per-human approver provenance on `SemanticMapping`, `TrustedPrincipal`-subject-to-`SemanticMapping` durable linkage, OIDC-subject-to-`EnterpriseEntity` mapping, generic governance actor model, `SemanticMapping` rejection-disposition persistence, correlation/reference-identifier persistence); any downstream wiring of a Published object into Blueprint, H1-H4, Gate I/J/K/L/N/P.

## 21. Approval state

**APPROVED ARTIFACT AUTHORIZATION.** Reached this state via Gate M3 discovery/drafting → Gate M3-R1 (an interpretive backend-only reading, later superseded) → Gate M3-R2 (the corrected, self-contained backend+frontend materialization, per the explicit Product Owner M3-D1 decision that the frontend is included) → Product Owner approval of the complete Gate M3-R2 v1.1 content, with P0=0/P1=0/P2=0 confirmed at that review. Approval of this record governs exactly the twenty-two-artifact-create, three-artifact-modify sandbox in §3 above; it does **not** itself authorize implementation of any artifact listed there — implementation remains a separate, subsequent Product Owner authorization, matching every prior companion's identical binding precondition in this lineage. Parent CDD-028 remains FROZEN and PUBLISHED, unchanged by this approval.
