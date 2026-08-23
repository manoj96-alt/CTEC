# CDD-027 — AI-Assisted Semantic Mapping Candidate Discovery — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `6ac52b7ca0d8b62adf4a34fc4d368de88a14e093`

## 1. Authority and scope

CDD-027 (FROZEN, PUBLISHED) authorizes Gate L's architecture but not implementation (§33: "a separate,
subsequent Artifact Authorization companion remains required before any file is created or modified").
This is that companion, covering the complete backend-only, provider-neutral, no-API, no-frontend MVP
core: candidate discovery → deterministic validation → Proposed materialization → human approval/rejection.
A real AI/model-provider adapter, an HTTP API, and a frontend are each explicitly deferred to a separate,
later Artifact Authorization.

This record was produced through: discovery against the actual repository (Gate L4), independent
Product Owner review resolving two open interpretive questions as Decisions L4-D1 and L4-D2 (Gate L4.5),
and Product Owner approval of both — L4-D1 (a test-local deterministic fake implementation of the
candidate-provider port is authorized within this companion; a real SDK-backed adapter is not) and
L4-D2 (no new persistence/migration is authorized; existing `SemanticMapping` fields satisfy CDD-027
§15's origin-distinction and generation-timestamp requirements, with the correlation-identifier and
rejection-disposition-record requirements explicitly, honestly deferred rather than silently claimed).

## 2. Implementation objective

Prove, entirely at the backend application-service layer using a deterministic test-only fake standing in
for any real AI provider, that: (a) a candidate can only be selected from a CTEC-supplied, tenant-bounded
`SourceField` universe; (b) deterministic validation gates every path to persistence; (c) only the
existing, unmodified Gate H1 `create()` method may materialize governed state; (d) only an authenticated
`TrustedPrincipal` action can produce an `Approved` row; (e) a `Proposed` row is never mutated.

## 3. Exact artifact allowlist

CREATE:
- `backend/app/application/semantic_mapping_candidate_discovery.py`
- `backend/app/application/semantic_mapping_proposal_governance.py`
- `backend/app/tests/test_semantic_mapping_candidate_discovery.py`
- `backend/app/tests/test_semantic_mapping_proposal_governance.py`
- `backend/app/tests/test_semantic_mapping_proposal_lifecycle_postgres.py`

MODIFY:
- `backend/app/tests/test_runtime_architecture.py` (exactly 5 new `AUTHORIZED_CHANGED_PATHS` entries,
  no other line changed)

No sixth artifact is authorized. No wildcard authorization of any kind (`backend/**`,
`application/**`, `tests/**`, or any directory-level grant) exists in this document. No
`dependency_container.py` change. No new seeder — the existing H3 `DemoSemanticMappingSeeder`/
`BlueprintSeeder` chain is reused by call only in the Postgres test.

## 4. Module contracts (binding)

### 4.1 `semantic_mapping_candidate_discovery.py`

- `SemanticMappingCandidateProvider(Protocol)`: `discover(self, *, context: CandidateDiscoveryContext) ->
  CandidateSelection | None` — the sole port.
- `CandidateSourceField`, frozen dataclass: `source_field_id: UUID`, `field_label: str`,
  `source_object_id: UUID`, `source_object_name: str`, `source_system_id: UUID`, `source_system_name: str`.
- `CandidateDiscoveryContext`, frozen dataclass: `information_element_requirement_id: UUID`,
  `element_name: str`, `description: str`, `obligation: Obligation`,
  `candidate_source_fields: tuple[CandidateSourceField, ...]`.
- `CandidateSelection`, frozen dataclass: exactly `source_field_id: UUID` — no
  `information_element_requirement_id` echo field, no confidence, rank, or explanation field. The target
  requirement is owned exclusively by CTEC via `CandidateDiscoveryContext` and is never redefinable by
  any provider implementation.
- `SemanticMappingCandidateUniverseService`: no `__init__` beyond an injected `Session`/repository
  dependency (constructor-injected, H2-pattern); one method building a `CandidateDiscoveryContext` for
  one tenant + one `GapImpactContext`-identified target `InformationElementRequirement`, querying only
  `SourceFieldORM`/`SourceObjectORM`/`SourceSystemORM` (read-only, zero mutation), scoped by
  `TrustedPrincipal.tenant_id`, excluding any `SourceField` already the source of an `Approved`
  `SemanticMapping`, ordered by `source_field_id`.

**Per Decision L4-D1**: a deterministic, test-only fake implementation of `SemanticMappingCandidateProvider`
is authorized, confined entirely to `test_semantic_mapping_candidate_discovery.py` (test-local scope
only); no production-adjacent implementation of this Protocol exists anywhere in this authorized
artifact set, and no real, SDK/credential-backed adapter is authorized by this document.

**Forbidden imports**: `gap_impact_remediation`'s own service class (context is supplied by the caller,
never re-derived); any Gate I/H2 service class; `FieldValueEvidence`/`field_value_evidence_repository`;
`ontology_copilot_api`; any SQLAlchemy write operation; any AI/LLM SDK.

### 4.2 `semantic_mapping_proposal_governance.py`

- `SemanticMappingProposalGovernanceApplicationService`: constructor-injected with the existing,
  unmodified `SemanticMappingRepository`/`SourceFieldRepository`/`BlueprintRepository` (or their existing
  Impl classes) — no new repository class.
- `materialize_proposal(self, *, candidate: CandidateSelection, context: CandidateDiscoveryContext,
  candidate_universe: tuple[CandidateSourceField, ...]) -> SemanticMapping`: implements CDD-027 §11's
  seven validation items in order; on success, calls the existing `SemanticMappingRepository.create()`
  with `governance_status=GovernanceStatus.PROPOSED` and `created_by=<fixed system-service Identifier,
  exact constant TBD, following `app.core.bootstrap`'s own existing pattern>`; raises
  `ValidationException` on any validation failure, before constructing any `SemanticMapping`. Multiple
  `Proposed` rows for the same `source_field_id`/`information_element_requirement_id` pair are permitted
  (no dedup rule, per CDD-027 §13).
- `approve(self, *, proposed: SemanticMapping, principal: TrustedPrincipal) -> SemanticMapping`: calls
  the same, unmodified `create()` with `governance_status=GovernanceStatus.APPROVED`,
  `created_by=Identifier(principal.principal_id)`, referencing the same `source_field_id`/
  `information_element_requirement_id` as `proposed`. Never mutates `proposed`. A conflicting or stale
  state at call time fails closed via H1's own existing, unmodified uniqueness/concurrency mechanism
  (including its `pg_advisory_xact_lock`-backed target-side check).
- `reject(self, *, proposed: SemanticMapping, principal: TrustedPrincipal) -> None`: performs no
  repository call of any kind. Exists only to name the second authorized human action explicitly. No
  `GovernanceStatus` value is assigned or changed.

**Forbidden imports**: any AI/LLM SDK; `SemanticMappingCandidateProvider` or any port-implementing class
(this module never calls the provider — it only consumes an already-produced `CandidateSelection`);
`gap_impact_remediation`'s service class; Gate I/H2 service classes; `ontology_copilot_api`;
`dependency_container`.

## 5. Runtime architecture impact

Add exactly these 5 entries to `AUTHORIZED_CHANGED_PATHS`:
```
"backend/app/application/semantic_mapping_candidate_discovery.py",
"backend/app/application/semantic_mapping_proposal_governance.py",
"backend/app/tests/test_semantic_mapping_candidate_discovery.py",
"backend/app/tests/test_semantic_mapping_proposal_governance.py",
"backend/app/tests/test_semantic_mapping_proposal_lifecycle_postgres.py",
```
No other line changes. No wildcard.

## 6. Provider boundary (binding)

No SDK, provider selection, or credential configuration anywhere in this authorized artifact set. The
sole authorized implementation of `SemanticMappingCandidateProvider` is the test-local deterministic
fake (§4.1, Decision L4-D1). A real external model call of any kind is explicitly **deferred / not
authorized** by this document.

## 7. Human-authority boundary (binding)

Only `approve()`, called with a real `TrustedPrincipal`, may produce an `Approved` row. No code path from
`SemanticMappingCandidateProvider` or `materialize_proposal()` can reach `governance_status=APPROVED`,
set `created_by` to anything but a fixed system identity, or select tenant.

## 8. Tenant boundary (binding)

`SemanticMappingCandidateUniverseService` and both `approve()`/`reject()` require `TrustedPrincipal` (or
an equivalent already-verified tenant string, never a request-body/model-supplied value) for every
tenant-scoped operation. The AI/provider boundary never receives, determines, or can override tenant
scope.

## 9. Persistence/migration authorization

**NONE.** No new table, column, or migration is authorized. `created_by`'s fixed system-service
`Identifier` value (an existing or minimally-extended constant following `app.core.bootstrap`'s own
established pattern) satisfies CDD-027 §15's origin/`proposal_source` distinction; the `Proposed` row's
own existing `created_on` field satisfies §15's generation-timestamp requirement. Per Decision L4-D2,
this Artifact Authorization explicitly does **not** satisfy §15's correlation/reference-identifier
requirement or any durable disposition record for a *rejected* proposal (rejection, per §13, creates no
row and requires no record) — both are deferred to a follow-up Artifact Authorization once a genuine
consumer for a correlation identifier exists. This is a disclosed, narrowed scope, not a silent gap.

## 10. API authorization

**NONE.**

## 11. Frontend authorization

**NONE.**

## 12. Test obligations

Full matrix: tenant-bounded universe proof; Approved-mapped `SourceField` exclusion; empty-universe/
abstention path; malformed/out-of-universe candidate rejection; cross-tenant candidate rejection; stale/
conflicting-candidate rejection via H1's live invariant; confidence-independence of validation
(structurally trivial, no such field exists); successful `Proposed` materialization; provider/port
import-hygiene (cannot reach the repository); AI cannot construct `Approved` (import-hygiene); human
approval creates a byte-unchanged-afterward `Proposed` row plus a new `Approved` row; Approved-uniqueness
conflict fails closed; concurrent approval race fails closed; rejection performs no write; no raw
`FieldValueEvidence` in any assembled context (import-hygiene); Gate I/H2 never called by any Gate L code
path (import-hygiene); `test_domain_foundation.py` and `test_runtime_architecture.py` unaffected/passing.

## 13. CI obligations

Full backend suite must remain green; `black`/`isort`/`ruff`/`mypy` clean; coverage on both new
application modules should reach the same 100%-line/100%-branch standard set by every prior gate in this
lineage.

## 14. P0/P1/P2 acceptance criteria

Implementation may proceed to freeze only at P0=0/P1=0/P2=0 against the adversarial categories
established during discovery (Gate L4/L4.5): AI cannot become semantic authority; AI cannot bypass human
approval; no cross-tenant leakage; no frozen-authority contradiction; no duplication/replacement of
existing authority; no unnecessary persistence/API/frontend; no confidence-as-correctness; no
non-determinism leaking into governed state; no Gate O/Q/M scope absorption.

## 15. STOP conditions

If implementation discovers any authorized artifact cannot be completed without touching an unlisted
path — in particular `dependency_container.py`, any migration, `source_field_repository.py`,
`semantic_mapping_repository.py`, or any Gate H/I/J/N/P/K production file — implementation MUST STOP and
report the exact blocker.

## 16. Non-claims

This Artifact Authorization does not authorize: any real AI/model-provider integration, SDK, or
credential; any API; any frontend; any new persistence/migration; any modification to H1/H2, Gate
I/J/N/P/K, Blueprint, or ontology-concept production files; any new `GovernanceStatus` value; any mutation
of a `Proposed` row; any correlation-identifier or rejection-disposition persistence (explicitly deferred,
§9).

## 17. Approval state

**APPROVED ARTIFACT AUTHORIZATION.** Reached this state via Gate L4 discovery/drafting → Gate L4.5
independent review, identifying two open interpretive questions and resolving them as Decisions L4-D1
and L4-D2 → Product Owner approval of both decisions and of this fully integrated candidate, with
P0=0/P1=0/P2=0 confirmed at every review stage. Approval of this record governs exactly the six-artifact
sandbox in §3 above; it does **not** itself authorize implementation of any artifact listed there —
implementation remains a separate, subsequent Product Owner authorization, matching every prior
companion's identical binding precondition in this lineage. Parent CDD-027 remains FROZEN and PUBLISHED,
unchanged by this approval.
