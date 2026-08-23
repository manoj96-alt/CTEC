# CDD-029 — Governed Blueprint Information-Element Context-as-a-Service

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: RFC-010 (FROZEN, Canonical Enterprise Ontology Boundary — §2-3, this CDD introduces no
cognitive capability and touches no canonical entity, §7 below), RFC-013 (FROZEN, Governance Authority and
Evaluation Separation — this CDD is pure Governance Evaluation exposure, never Governance Authority, §14
below), RFC-015 (FROZEN, Tenant Ownership Physical Model Authorization — tenant origin exclusively from
`TrustedPrincipal.tenant_id`, §8 below), CDD-017/CDD-018 (FROZEN, Blueprint/Blueprint Conformance, unchanged,
the reused target-resolution authority), CDD-019 (FROZEN, Gate H H1-H4, unchanged, the reused mapping/evidence
substrate), CDD-020 (FROZEN, Gate I, unchanged, the sole coverage authority, §7 below), CDD-021 (FROZEN, Gate J,
unchanged, explicitly not consumed), CDD-023 (FROZEN, H4, unchanged, the sole evidence-availability authority,
§7 below), CDD-024 (FROZEN, Gate N, unchanged, the sole context-composition authority, §7 below), CDD-025
(FROZEN, Gate P, unchanged, explicitly not modified or refactored, §19 below), CDD-026 (FROZEN, Gate K,
unchanged, explicitly not consumed), CDD-027 (FROZEN, Gate L, unchanged, §22's own "public/external service
contract" phrase is this CDD's own originating clue, cited not reinterpreted), CDD-028 (FROZEN, Gate M,
unchanged, entirely unrelated capability)
Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via discovery (Gate O0, which established
that neither "Gate O" nor "Context-as-a-Service" had any prior governed reservation — confirmed by exhaustive
repository search, mirroring CDD-026 §18's own precedent disclaimer for "Gate O") → Product Owner
architecture-decision resolution (Gate O1, resolving O-PO-1, O-PO-2, O-D-1 through O-D-12, and two P2
decisions, with P0=0/P1=0/P2=0) → drafting (Gate O2) → Product Owner CDD review and contract-normalization
decision resolution (Gate O3, resolving O3-D1 through O3-D13, including the endpoint/method/scope/package/
request/response/status-taxonomy/HTTP-mapping literals and the integrity-vs-ambiguity correction) → this Gate
O4 publication turn. No implementation exists, and none is authorized by this frozen document — a separate,
subsequent Artifact Authorization companion remains required before any file is created or modified.

## 1. Objective and business outcome

Allow an authenticated, tenant-scoped, non-Ask-CTEC consumer to retrieve the already-governed context
(semantic coverage + evidence availability) for one Blueprint `InformationElementRequirement`, through a
deterministic, structured, machine-addressable contract — without duplicating, reinterpreting, or gaining
authority over Gate I's coverage determination, H4's evidence-availability determination, or Gate N's
composition of the two.

## 2. Governing authorities

(restated per header; RFC-010/013/015 govern this CDD's constitutional boundaries; CDD-017/018/019/020/023/024
govern the reused resolution/coverage/evidence/composition chain this CDD orchestrates by call only; CDD-021/025/
026/027/028 govern adjacent, explicitly unconsumed or unmodified capabilities)

## 3. Why this CDD requires its own governance

Gate O0 confirmed neither "Gate O" nor "Context-as-a-Service" has ever been defined by any prior authority —
only negative firewall mentions exist (CDD-026 §18, CDD-027 §22/§5, CDD-028 §280/§301). CDD-027 §22 itself
draws the exact distinction this CDD now resolves: an "internal application-layer interface" (what CDD-027's
own provider port is) versus "a public/external service contract" (what this CDD authorizes). No prior CDD
authorizes any consumer-independent, non-Ask-CTEC access path to the Blueprint→Gate I→H4→Gate N chain — a new,
standalone CDD is the only textually honest instrument, identical reasoning to every prior standalone CDD in
this lineage.

## 4. In scope

A new, standalone application service ("the Context Service," exact module name reserved for Artifact
Authorization per the Gate O1 P2 naming decision) that orchestrates, by call only: `BlueprintApplicationService.
get_approved_by_name` → `SemanticCoverageEvaluationApplicationService.evaluate` (Gate I) →
`InformationElementEvidenceAvailabilityApplicationService.evaluate` (H4) →
`InformationElementContextAvailabilityApplicationService.compose` (Gate N) — resolving exactly one
`InformationElementRequirement`, identified by Blueprint name + element name, per invocation. A new, dedicated,
structured API endpoint exposing that service, authenticated via Gate E's existing `TrustedPrincipal`, gated by
one new, dedicated authorization scope (§10, exact literal frozen at Gate O3). A deterministic,
non-natural-language response contract (§12). An explicit, closed failure taxonomy (§15) cleanly separating
domain semantic outcomes from service/request failures.

## 5. Architecture (binding — encodes O-D-1)

```
Machine Consumer
    |
    v
Gate O Context API  (new, dedicated scope, structured request/response, no NL parsing)
    |
    v
Gate O Context Application Service  (new, tenant-aware, deterministic, fail-closed, read-only)
    |
    v
BlueprintApplicationService  (existing, unmodified)
    |
    v
Gate I -- Semantic Coverage  (existing, unmodified)
    |
    v
H4 -- Evidence Availability  (existing, unmodified)
    |
    v
Gate N -- Context Composition  (existing, unmodified)
```

The API is the **sole external boundary**; it is forbidden from letting a consumer reach Gate I/H4/Gate N
directly, and equally forbidden from routing through Ask CTEC's NL parsing (§19). Both the application service
and the API layer are new; every layer below them is reused, unmodified, exactly as CDD-025's own precedent
established for Gate P.

## 6. Out of scope (binding)

Any modification to `ontology_copilot_api.py`, its router, or its schemas (§19). Any modification to
`semantic_coverage_evaluation.py`, `information_element_evidence_availability.py`,
`information_element_context_availability.py`, or `blueprint_service.py` (§7). Any consumption of Gate J's or
Gate K's output (§20). Any new ontology concept, canonical mutation, or Blueprint authoring (RFC-010, CDD-017
§4). Any real AI/model/agent/MCP capability (§21-§22). Any new persistence, migration, cache, or durable
context-request/result record (§17). Any frontend artifact (§23). Any synthesized semantic state beyond what
Gate I/H4/Gate N already produce (§13). Any Artifact Authorization content — reserved for a separate,
subsequent Gate O5 turn.

## 7. Semantic-authority boundary (binding, load-bearing)

Gate I (CDD-020) remains the **sole authority** for `CoverageStatus` (`MAPPED`/`UNMAPPED`). H4 (CDD-023) remains
the **sole authority** for `EvidenceAvailabilityStatus` (`AVAILABLE`/`UNAVAILABLE`, `None` when not applicable).
Gate N (CDD-024) remains the **sole authority** for composing the two into
`InformationElementContextAvailabilityResult`. This CDD's application service passes every one of these values
through **unmodified** — it may not recompute, override, default, or reinterpret any of them. This CDD's own
authority is limited exclusively to: target resolution (which Blueprint/element), orchestration sequencing,
tenant/authorization enforcement, transport-contract shaping, and service/request failure semantics (§15).

## 8. Tenant boundary (binding)

`tenant_id` originates exclusively from `TrustedPrincipal.tenant_id` (RFC-015), passed into Gate I's own
`evaluate(tenant_id=...)` call exactly as Gate P already does — never a request field, never inferred, never
defaulted. Blueprint identity itself remains tenant-neutral (CDD-017 — Blueprints are enterprise-global);
tenant enforcement applies specifically at the Gate I coverage-resolution step, identical to existing
Ask CTEC behavior. No new tenant-scoping mechanism is introduced.

A caller from Tenant A requesting a legitimate, globally-defined `InformationElementRequirement` whose only
existing semantic mapping belongs to Tenant B receives Tenant A's own legitimate, tenant-scoped governed
result — `coverage_status = UNMAPPED`. This is the correct Gate I semantic outcome, not a failure, and it must
not leak that Tenant B holds a mapping. The request contract (§11) never accepts a `tenant_id` field, closing
off any possibility of a caller inspecting another tenant's mapping directly (Gate O3, O3-D11).

## 9. Application-service responsibility ("the Context Service")

Exact module/class name reserved for Artifact Authorization (Gate O1 P2 decision — "Information Element
Context"-flavored naming preferred over generic "context"). Responsibilities: resolve the target Blueprint by
name (fail closed on not-found/ambiguous/integrity-violation, mirroring Gate P's own defended edge case at
`ontology_copilot_api.py::_ask_information_element_context_explanation`); resolve the target
`InformationElementRequirement` by name within that Blueprint (fail closed on not-found/ambiguous, §15); invoke
Gate I, then H4, then Gate N, in that fixed order, exactly once each; return a closed, typed result. Performs
no persistence write of any kind. Takes a `TrustedPrincipal` as an explicit parameter — never resolves identity
itself.

## 10. API responsibility (frozen at Gate O3)

**Frozen literals (Gate O3, O3-D1 through O3-D4):**
- Endpoint: `POST /api/v1/information-element-context/resolve`
- HTTP method: `POST` — the request is a multi-field structured payload (Blueprint name + element name), not a
  single path-addressable resource id; "the request is a payload, not a command," mirroring
  `POST /api/v1/ontology-copilot/ask`'s own documented rationale. **POST transport semantics do not change Gate
  O's read-only domain semantics. No database write is authorized merely because POST is used.**
- Scope literal: `information-element-context:read` — following the existing `<capability-area>:<verb>`
  convention (`entity-resolution:read`, `ontology-copilot:ask`, `ontology-modeling:propose`), using `:read` to
  match `entity-resolution:read`'s own precedent for a pure, non-mutating capability. This scope is dedicated
  and distinct from `ontology-copilot:ask` — it is never reused.
- API package boundary: `backend/app/api/information_element_context/` (mirrors `ontology_modeling`'s own
  self-contained package shape). This freezes the package boundary only; individual file names remain reserved
  for Artifact Authorization.

Router-level behavior (binding, independent of the literals above): reuses Gate E's `TrustedPrincipal`/
`principal` dependency and the exact `_authorize(authenticated, scope, dependencies, correlation)` +
`SecurityAuditService` audit-on-denial pattern already used by `entity_resolution`/`ontology_modeling` routers
— no new authentication or authorization mechanism (§14). The authorization check occurs **before** Blueprint
resolution, before Gate I, before H4, and before Gate N — an under-scoped or unauthenticated caller never
causes any downstream composition to execute.

## 11. Request contract (frozen at Gate O3)

Exactly two required fields: `blueprint_name` (string), `information_element_name` (string). No `tenant_id`
field (§8 — tenant comes from the authenticated principal, never the request body). No optional fields — none
are authorized for Gate O v1. A closed schema (`extra="forbid"`, mirroring `AskRequest`'s own `ClosedModel`
precedent, or the repository-equivalent closed-model mechanism).

## 12. Response contract — minimum governed context (frozen at Gate O3)

Every field traced to an existing authority (Gate O1 O-D-7's own requirement):

| Field | Authority | Included? |
|---|---|---|
| `blueprint_id`, `blueprint_version_number` | Blueprint/Gate G (CDD-017) | YES — precedented by Gate P's own `InformationElementContextExplanationResult` |
| `information_element_requirement_id`, `information_element_name` | Blueprint (CDD-017) | YES |
| `obligation` | Blueprint (CDD-017) | YES — already authoritative and already exposed by Gate P |
| `coverage_status` | Gate I (CDD-020) | YES — passed through unmodified |
| `evidence_availability_status` | H4 (CDD-023) | YES — passed through unmodified, `None` when not applicable |

**No `status` field is included on a successful (HTTP 200) response.** This redundant transport-decoration
field was proposed at Gate O2 and removed at Gate O3 (O3-D10): HTTP 200 already signals a valid governed
resolution, and `coverage_status`/`evidence_availability_status` already fully express the semantic outcome. A
service/request `status`-style value is used only as the `detail.code` of a non-200 response (§15) — it never
appears in a success payload.

**Explicitly excluded, no traceable authority or explicitly out of scope**: raw source observations/payloads,
evidence record ids, internal database ids, confidence/trust/freshness scores, remediation content, Gate J
output, Gate K output, model-generated explanation text (§6, §20).

## 13. Forbidden synthesized semantic states (binding, restated from Gate O1 O-D-5)

This CDD does not define, and no implementation of it may introduce, `PARTIALLY_MAPPED`, `LOW_CONFIDENCE`,
`HIGH_CONFIDENCE`, `TRUSTED`, `UNTRUSTED`, `READY`, `NOT_READY`, `FRESH`, or `STALE`, or any other value not
already produced by Gate I/H4/Gate N — unless a future, separately-governed capability explicitly authorizes
it.

## 14. Authorization semantics (binding)

A real, Gate-E-authenticated `TrustedPrincipal` holding the `information-element-context:read` scope (§10) is
required for every call. No new authentication mechanism (RFC-013's Governance Evaluation/Governance Authority
separation is preserved: this CDD only *evaluates and exposes* already-governed state, it never *grants*
anything). Authorization is checked **before** any downstream composition call executes.

## 15. Failure taxonomy (frozen at Gate O3, O3-D7/O3-D8)

**Domain semantic outcomes** (never a failure, always HTTP 200, no `status` field — §12): `MAPPED` +
`AVAILABLE`; `MAPPED` + `UNAVAILABLE`; `UNMAPPED` (evidence status `None`, non-applicable).

**Service/request status codes**, used exclusively as `HTTPException(..., detail={"code": ...})` values on
non-200 responses:

| Code | HTTP | Trigger | Precedent |
|---|---|---|---|
| (Gate E auth failure) | 401 | Missing/invalid authentication | `supplier_risk/dependencies.py` |
| `AUTHORIZATION_SCOPE_REQUIRED` | 403 | Authenticated principal lacks `information-element-context:read` | `entity_resolution/router.py`, `ontology_modeling/router.py` |
| (framework validation) | 422 | Malformed/closed-schema request; router never invokes the service | repo-wide FastAPI convention |
| `BLUEPRINT_NOT_FOUND` | 404 | Blueprint name resolves to zero Approved Blueprints | `entity_resolution/router.py` (`RESOLUTION_CASE_NOT_FOUND`), `ontology_modeling/router.py` (`PROPOSAL_NOT_FOUND`) |
| `INFORMATION_ELEMENT_NOT_FOUND` | 404 | Blueprint resolves uniquely; element name matches zero requirements within it | same as above |
| `INFORMATION_ELEMENT_NAME_AMBIGUOUS` | 422 | Blueprint resolves uniquely; element name matches **more than one** requirement within it | `entity_resolution/router.py` 422 usage for "the request as given cannot be deterministically actioned" |
| `UPSTREAM_INTEGRITY_FAILURE` | 500 | More than one Approved Blueprint shares the requested name, or Gate I/H4/Gate N raise/produce an internal inconsistency for an otherwise validly-resolved target | `entity_resolution/router.py`'s own `SOURCE_PROVENANCE_INCOMPLETE → 500` — the directly analogous governed-data-integrity precedent (Gate P itself never uses a non-200 status for anything, so it supplies no usable HTTP-code precedent here) |

**The integrity/ambiguity distinction (binding, Gate O3 finding)**: `INFORMATION_ELEMENT_NAME_AMBIGUOUS` is
kept **structurally distinct** from `UPSTREAM_INTEGRITY_FAILURE`, not folded into it. Direct inspection of
Gate P's own `ontology_copilot_api.py::_ask_information_element_context_explanation` shows these have different
root causes: multiple Approved Blueprints sharing a name is caught as a `ValidationException` raised by
`BlueprintApplicationService.get_approved_by_name` itself — `BlueprintRepositoryImpl`'s own enforced invariant
being violated by the governed data, a genuine integrity failure (500). Multiple `InformationElementRequirement`s
sharing a name within one uniquely-resolved Blueprint is detected by an ordinary multi-match check with no
`ValidationException` and no repository/domain uniqueness constraint involved — Blueprint's own domain model
does not guarantee element-name uniqueness across `concept_requirements`, so two different Concepts may
legitimately each define an element with the same name. This is an under-specified request given Gate O's own
two-field contract, not corrupted governed data, and is therefore mapped to 422, not 500.

**Binding rule**: an authorization failure must never be represented as `UNMAPPED`, `UNAVAILABLE`, or "not
found" — no concealment semantics are authorized by this CDD.

## 16. Determinism boundary (binding, restated from Gate O1 O-D-4)

Given equivalent authoritative database state, tenant, Blueprint target, InformationElementRequirement target,
and authorization state, this service produces byte-identical semantic output on every call. No randomness, no
model generation, no probabilistic scoring, no inferred confidence/trust, no nondeterministic timestamp inside
the semantic result. This is a governed retrieval/composition capability, never a cognitive one (RFC-010).

## 17. Persistence / migration boundary (binding, restated from Gate O1 O-D-3/O-D-12)

**Zero new persistence.** No table, no migration, no cache, no context-request record, no context-result
record, no durable execution state, no generated identifier minted merely for storage. Every read this CDD's
service performs flows through the existing, unmodified `BlueprintRepositoryImpl`/Gate I/H4 read paths.
Authorization-denial audit logging, if implemented, reuses the **existing, already-governed**
`SecurityAuditService`/`ApiSecurityAuditRepository` (CDD-013) exactly as `entity_resolution`/`ontology_modeling`
already do — this is reuse of existing governed infrastructure, not a new Gate O persistence authority, and
must be described as such, never conflated with a violation of this section.

## 18. Existing read-path preservation (binding)

`BlueprintApplicationService`, `SemanticCoverageEvaluationApplicationService`, `InformationElementEvidence
AvailabilityApplicationService`, `InformationElementContextAvailabilityApplicationService`, and every ORM/
repository they depend on remain **completely unmodified**. This CDD's service calls them exactly as Gate P
already does — proving, by construction, that a second, independent caller of this exact chain does not require
touching any of it.

## 19. Ask CTEC firewall (binding, restated from Gate O1, reconfirmed Gate O3 O3-D13)

`ontology_copilot_api.py`, `backend/app/api/ontology_copilot/{router,schemas}.py`, and every Ask CTEC frontend
file remain untouched. Gate P is not refactored to consume this CDD's service during this gate. The resulting
orchestration-logic duplication between Gate P's own `_ask_information_element_context_explanation` and this
CDD's new service is an explicit, Product-Owner-accepted tradeoff, not a defect this CDD is authorized to
resolve. Any future deduplication requires separate, explicit authorization.

## 20. Gate J / Gate K exclusion (binding)

This CDD's service never calls `GapImpactRemediationApplicationService` (Gate J) or
`InformationElementDecisionPrerequisiteAssessmentApplicationService` (Gate K), and no Gate J/K field appears in
the response contract (§12) — restated from, not a departure from, Gate N's own existing "does not consume Gate
J's output" scope and Gate K's own existing position as a *consumer* of Gate N, never a peer of it.

## 21. MCP / Gate Q firewall (binding, restated from Gate O1 O-D-9)

No MCP server, client, tool, connector framework, agent protocol, or tool-discovery mechanism is authorized.
Gate Q remains entirely separate, unscoped, ungoverned. This CDD's own structured contract is a plausible
*future* target for Gate Q to consume — that compatibility is a beneficial side effect, never an acceptance
criterion of this CDD.

## 22. Model / provider firewall (binding, restated from Gate O1 O-D-10)

No real LLM provider, model selection, prompt construction, embeddings, vector retrieval, RAG, agent reasoning,
or provider credential is authorized anywhere in this CDD's scope.

## 23. Frontend boundary (binding)

None. No frontend file is authorized by this CDD.

## 24. Security invariants (binding, summary)

No cross-tenant exposure (§8). No unauthorized composition call (§14). No authorization-failure concealment
(§15). No canonical ontology mutation of any kind (this CDD is entirely read-only, touching no `entity_types`/
`relationship_types`/`institutional_concepts`/`ontology_relationship_bindings`/`semantic_mappings`/`source_
fields` row). No new authentication surface (§14, RFC-013).

## 25. Test obligations

Positive: `MAPPED`+`AVAILABLE`; `MAPPED`+`UNAVAILABLE`; `UNMAPPED`. Resolution failures: Blueprint not found;
InformationElementRequirement not found; InformationElementRequirement name ambiguous (422, distinct from
integrity failure); governed-data integrity violation (500). Authorization: missing principal; missing required
scope; correct scope succeeds; a cross-tenant target (an InformationElementRequirement whose only mapped
`SourceField` belongs to a different tenant) resolves as `UNMAPPED` for the calling tenant, never leaks the
other tenant's `MAPPED` state; authorization is proven to fail *before* any Gate I call executes (mirroring
Gate L/M's own `_require_principal`-first discipline). Determinism: two equivalent calls yield byte-identical
results; no timestamp/id varies inside the semantic payload. Contract integrity: Gate I's `coverage_status` and
H4's `evidence_availability_status` are proven passed through unmodified (bit-for-bit equality with directly-
called Gate I/H4 results in the same test); no Gate J/K field ever appears; no raw evidence value ever appears;
no `status` field ever appears on a 200 response. API-level: valid request, malformed request (422), unauthorized
(401/403), not-found mapping (404), ambiguous-name mapping (422), integrity-failure mapping (500) — mirroring
the exact test-file shape (`test_<service>.py` unit, `test_<service>_postgres.py` integration,
`test_<router>.py` API) this repository has used for every prior gate.

## 26. Acceptance criteria

1. A request for a MAPPED, evidenced InformationElementRequirement returns `coverage_status`/`evidence_
   availability_status` identical to what Gate I/H4 would independently produce for the same input.
2. A request for an UNMAPPED InformationElementRequirement returns `coverage_status=UNMAPPED`,
   `evidence_availability_status=None`.
3. An unauthenticated or under-scoped request is rejected before Blueprint resolution begins.
4. No test or code path allows this CDD's service to write to any canonical or Gate-N-composed persistence.
5. `ontology_copilot_api.py`, Gate I/H4/Gate N production files, and every canonical ORM model pass unmodified,
   with zero behavior change, both before and after this CDD's implementation.
6. Repeated identical requests against unchanged database state produce byte-identical responses.
7. A request whose element name matches more than one requirement within a uniquely-resolved Blueprint returns
   HTTP 422 with `INFORMATION_ELEMENT_NAME_AMBIGUOUS`, never HTTP 404 and never HTTP 500.

## 27. Non-claims

This CDD does not claim: durable per-human provenance of any kind (Gate L's own deferred non-claim, unrelated
here); real model-provider integration; MCP compatibility beyond incidental contract shape; that Ask CTEC and
this CDD's service share implementation (they deliberately do not, §19); that this CDD resolves Gate J/K
output into context (§20); that any new ontology authority is created (§6, RFC-010).

## 28. Artifact Authorization boundary

Deferred to Artifact Authorization: exact module/file names; exact request/response DTO types; exact test
filenames; exact `AUTHORIZED_CHANGED_PATHS` entries; the exact 401 code literal (existing precedent already
varies per module — e.g. `AUTH_TOKEN_MISSING` vs `AUTH_REQUIRED` — and this CDD does not introduce a new
inconsistency by leaving it to Artifact Authorization).

## 29. Rollback

Reverting this CDD's eventual implementation removes exactly one new application-service file, one new API
package, and their tests. No existing file requires rollback, because none is modified.

## 30. Compatibility

Fully additive. No existing frozen CDD's acceptance criteria, test, or production code path is affected —
confirmed by §18's construction argument (every dependency is called, never modified) and §19's explicit
Ask CTEC preservation.

## 31. Numbered architecture baseline determination

No new numbered architecture baseline is required, following the identical, repeatedly-proven method every
CDD since CDD-016 has used: this CDD introduces no new RFC-tier or PAD-tier document, cites RFC-010/013/015
and CDD-017/019/020/023/024 unchanged, and is registered via `architecture/INDEX.md`'s existing "Governed
implementation work orders" table alone.

## 32. Authorization

This document reached FROZEN status via: Gate O0 discovery (P0=0/P1=0/P2=0) → Gate O1 Product Owner
architecture-decision resolution (O-PO-1, O-PO-2, O-D-1 through O-D-12, two P2 decisions) → Gate O2 CDD
drafting (P0=0/P1=0/P2=0) → Gate O3 Product Owner CDD review and contract normalization (O3-D1 through O3-D13,
P0=0/P1=0/P2=0) → Gate O4 publication authorization, under which this document is published and frozen.

**Implementation remains unauthorized.** A separate, subsequent Artifact Authorization (Gate O5) is required
before any file governed by this CDD may be created or modified, matching every prior CDD's identical
multi-step discipline in this lineage.
