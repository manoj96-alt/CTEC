# CDD-025 — Context Explanation Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `b849cc9e229b1556de288939db7f4f864cb5dfea`

## 1. Authority and scope

CDD-025 (FROZEN, PUBLISHED) authorizes Gate P — Blueprint Information-Element Context Explanation —
as an architecture, but does not itself authorize writing any code against it (CDD-025 §28: "a
separate, subsequent Artifact Authorization companion remains required after publication"). This
report is that companion, following the identical CDD-Template-v2.2-compliant format every prior
companion in this lineage used (CDD-022's own companion, CDD-024's own companion — both, like this
one, carrying no gate-letter prefix).

## 2. Objective (restated from CDD-025 §1)

Extend the existing Ask CTEC / Gate D capability with a deterministic explanation path for governed
Blueprint `InformationElementRequirement` context: resolve a question naming one Blueprint and one
Information Element, consume Gate N's already-composed result, render a fixed-template explanation.

## 3. Discovery findings (binding, restated for the record)

- Every candidate file is already a member of `test_runtime_architecture.py`'s
  `AUTHORIZED_CHANGED_PATHS` (added at Gate D0/D1) — confirmed by direct grep and by direct read of
  the exhaustive-allowlist test's pure path-membership semantics (`assert changed <=
  AUTHORIZED_CHANGED_PATHS`, no per-turn provenance tracking). **This authorization introduces zero
  new file paths and requires zero `AUTHORIZED_CHANGED_PATHS` modification.**
- `OntologyCopilotApiService` is constructed with only a `sessionmaker[Session]`; every dependency it
  uses is built ad hoc, per-request, inside `ask()` — confirmed by direct read (e.g.
  `InstitutionalRelationshipStore(session)`, constructed inline, never injected). Gate P's new
  orchestration (Blueprint, Gate I, H4, Gate N) follows the identical pattern; no
  `dependency_container.py` or `dependencies.py` change is required or authorized.
- `ontology_copilot` lives outside `test_domain_foundation.py`'s five scanned domain roots
  (`foundation`/`integration`/`operational`/`semantic`/`shared`) — confirmed unaffected, no change
  authorized.
- The existing Ask CTEC frontend (`frontend/app/ontology-studio/ask/_components/ask-ctec-workspace.tsx`)
  renders generically off the whole `AskResponse` object via a status-keyed sub-component, confirmed
  by direct read — no frontend file is authorized.
- **Zero-CREATE architecture justification (binding finding)**: placing Gate P's orchestration inside
  `ontology_copilot_api.py` does not create an inappropriate "god-service." Direct inspection of
  `backend/app/application/supply_chain_impact_api.py` (`SupplyChainImpactApiService`, 374 lines, 5
  public/private methods, exercised by five separate test files) confirms this repository already has
  an established, shipped precedent for a single `*_api.py` orchestrator spanning multiple
  domain/infrastructure concerns via the identical `sessionmaker[Session]`-only constructor plus
  ad-hoc per-request sub-service construction pattern `ontology_copilot_api.py` itself already uses at
  162 lines. Growing `ontology_copilot_api.py` to accommodate Gate P's four-service orchestration
  (Blueprint, Gate I, H4, Gate N) remains well within this repository's own established size and
  responsibility norms for this file class — a dedicated new
  `information_element_context_explanation.py` application module would be unnecessary abstraction,
  not required by, and inconsistent with, CDD-025 §6/§22's own explicit "extend the existing files"
  instruction.

## 4. Authorized artifacts

| Artifact and path | Action | Purpose | Exclusions |
|---|---|---|---|
| `backend/app/domain/ontology_copilot/intent.py` | MODIFY | Add exactly one new `SupportedIntent` value and one new fixed regex template parsing `(blueprint_name, information_element_name)` (CDD-025 §10). | No fuzzy matching, no NLP, no probabilistic interpretation. No change to the existing `PRODUCTS_DEPENDING_ON_SUPPLIER` pattern or `UnsupportedQuestionError` semantics. |
| `backend/app/domain/ontology_copilot/answer.py` | MODIFY | Add exactly one new template-only composition function implementing CDD-025 §12's exact approved vocabulary. | No free-text generation, no LLM, no inference. No change to the existing `compose_products_depending_on_supplier_answer` function. |
| `backend/app/application/ontology_copilot_api.py` | MODIFY | Add `GatePAskStatus` (CDD-025 §19, exactly the six named values), the new frozen/slotted result dataclass (CDD-025 §11, exactly the nine named fields), orchestration logic implementing CDD-025 §9's exact Step 0-4 sequence (Blueprint resolution, Gate I, H4, Gate N, in that order), and CDD-025 §10's exact Information-Element resolution/ambiguity rule (exact-string-equality match, `INFORMATION_ELEMENT_NOT_FOUND`/`INFORMATION_ELEMENT_AMBIGUOUS`, never a first-match selection). | No merge into the existing `AskStatus`/`AskResult` types. No direct import of `SemanticMapping`/`SourceField`/`FieldValueEvidence`/`SourceObservation` repository or domain modules. No import of `gap_impact_remediation.py`/`GapImpactContext`/`RemediationAction`. No new field beyond the exact nine (no `trust_score`, `confidence_score`, `readiness`, `risk_score`, or equivalent). No persistence, no `Protocol`, no new infrastructure dependency, no `datetime.now()`-owned timestamp beyond what Gate I/H4 already own internally. No modification to Gate I/H4/Gate N's own source files. |
| `backend/app/api/ontology_copilot/router.py` | MODIFY | Extend `_to_response` to map the new optional nested field from the application-layer result onto the response schema. | No new route. No new business/orchestration logic in the router — orchestration remains exclusively in `ontology_copilot_api.py`. No change to the existing `/ask` route's supplier-question behavior. |
| `backend/app/api/ontology_copilot/schemas.py` | MODIFY | Add exactly one new optional nested Pydantic model carrying the Gate P structured result fields. | No new top-level flat field on `AskResponse`. Must default to `None` for the existing intent (backward compatible, CDD-025 §25). No field beyond CDD-025 §11's exact nine. |
| `backend/app/tests/test_ontology_copilot_intent.py` | MODIFY | New parsing tests: supported phrasing, unsupported phrasing, whitespace/punctuation handling for the new intent. | No modification to existing supplier-question intent test assertions. |
| `backend/app/tests/test_ontology_copilot_answer.py` | MODIFY | New composition tests: all four `EvidenceAvailabilityStatus`/`None` cases, forbidden-vocabulary negative assertions (CDD-025 §12's prohibited-transformation list). | No modification to existing supplier-answer test assertions. |
| `backend/app/tests/test_ontology_copilot_api_postgres.py` | MODIFY | New orchestration tests against the real H3/CDD-022/H4 demo fixture, proving the A-N acceptance matrix (§11 below). | No new seeder file. No modification to existing supplier-question orchestration tests. |
| `backend/app/tests/test_ontology_copilot_router.py` | MODIFY | New response-schema-mapping tests; an explicit existing-intent backward-compatibility assertion (response shape unchanged for `PRODUCTS_DEPENDING_ON_SUPPLIER`). | No modification to existing router test assertions beyond adding the new coverage. |
| `backend/app/tests/test_ontology_copilot_full_stack_postgres.py` | MODIFY | Add **exactly one** new full-HTTP-stack Gate P acceptance scenario (real FastAPI router, real application service, real Postgres, real auth), proving the round trip for one deterministic Gate P question and confirming the existing supplier-question full-stack scenario remains unmodified and passing. | No broad full-stack test refactoring. No unrelated fixture redesign. No new persistence architecture. No unrelated Ask CTEC capability added. No second or third Gate P scenario added here — the full acceptance matrix (§11) is proven at the narrower `test_ontology_copilot_api_postgres.py`/`test_ontology_copilot_intent.py`/`test_ontology_copilot_answer.py` layers; this file carries exactly one bounded end-to-end proof, not exhaustive coverage. |

No other repository path is authorized. In particular: `backend/app/domain/ontology_copilot/traversal.py`,
`backend/app/api/ontology_copilot/dependencies.py`, `backend/app/core/dependency_container.py`,
`backend/app/tests/test_runtime_architecture.py`, `backend/app/tests/test_domain_foundation.py`,
`backend/app/tests/test_demo_ontology_copilot_seeder.py`, `backend/app/tests/test_demo_ontology_copilot_seeder_postgres.py`,
any Gate I/H4/Gate N source file (`semantic_coverage_evaluation.py`, `information_element_evidence_availability.py`,
`information_element_context_availability.py`), any Gate J file (`gap_impact_remediation.py`), any
Blueprint domain/persistence file, any migration file, `keycloak/ctec-realm.json`, any `frontend/*`
file, `docs/cdd/CDD-025-*`, `architecture/INDEX.md`, `architecture/released/*` are **not** authorized
for modification.

## 5. Protected artifacts / firewall table

| Protected artifact | Why protected | Enforcement in this record |
|---|---|---|
| `SemanticCoverageEvaluationApplicationService` (Gate I, CDD-020) | CDD-025 §7/§9 — consumed by call only | Not in CREATE/MODIFY list; called unmodified once per question |
| `InformationElementEvidenceAvailabilityApplicationService` (H4, CDD-023) | CDD-025 §7/§9 — consumed by call only | Not in CREATE/MODIFY list; called unmodified once per question |
| `InformationElementContextAvailabilityApplicationService` (Gate N, CDD-024) | CDD-025 §7 sole-composition-authority firewall | Not in CREATE/MODIFY list; called unmodified once per question; no second interpretation path |
| `GapImpactContext`/`RemediationAction`/`gap_impact_remediation.py` (Gate J, CDD-021) | CDD-025 §8 exclusion | Not in CREATE/MODIFY list; no import authorized |
| `SemanticMapping`/`SourceField`/`FieldValueEvidence`/`SourceObservation` | CDD-025 §9/§15 raw-evidence firewall | No import authorized anywhere in the sandbox |
| `Blueprint`/`ConceptRequirement`/`InformationElementRequirement`/`RelationshipRequirement`/`Obligation` | CDD-025 §10 — no new semantics | Read/passthrough only; not in CREATE/MODIFY list |
| `backend/app/tests/test_runtime_architecture.py` | Confirmed unaffected — zero new file paths introduced (§3) | Not in CREATE/MODIFY list |
| `backend/app/tests/test_domain_foundation.py` | Confirmed structurally unreachable (§3) | Not in CREATE/MODIFY list |
| `backend/app/core/dependency_container.py`, `backend/app/api/ontology_copilot/dependencies.py` | Confirmed unnecessary — existing wiring already sufficient (§3) | Not in CREATE/MODIFY list |
| `keycloak/ctec-realm.json` | Existing `ontology-copilot:ask` scope confirmed sufficient (endpoint-level, not per-intent) | Not in CREATE/MODIFY list |
| Any `frontend/*` file | Confirmed unnecessary — existing UI renders generically (§3) | Not in CREATE/MODIFY list |
| `architecture/INDEX.md`, `architecture/released/*` | Already published; implementation does not touch governance registration | Not in CREATE/MODIFY list |
| `docs/cdd/CDD-025-*` (parent + this companion) | FROZEN / DRAFT respectively; implementation does not amend governance | Not in CREATE/MODIFY list |

## 6. Gate N / Gate J / Gate K firewall (binding, restated)

**Gate N**: sole authoritative source of `(coverage_status, evidence_availability_status)`. Gate P may
orchestrate the existing governed Gate I/H4 calls required to produce Gate N's own input parameters,
but must not reimplement, approximate, or bypass any part of Gate N's composition-integrity contract
(CDD-024 §10), and must not construct a competing composed classification through any other path.

**Gate J**: zero consumption. No import of `gap_impact_remediation.py`, `GapImpactContext`, or
`RemediationAction` anywhere in the authorized artifact set.

**Gate K**: no artifact may introduce Decision Readiness, overall/Blueprint readiness, requirement
satisfaction, completeness, score, percentage, trust, confidence, freshness/staleness, correctness,
quality, risk, severity, priority, or cross-Information-Element-Requirement aggregation of any kind.
`Obligation` remains strict passthrough (CDD-025 §10, §16) — no conditional-applicability logic.

## 7. Raw evidence firewall (binding, restated)

Gate P must not independently interpret `SourceObservation`, `FieldValueEvidence`, or `SemanticMapping`
— it consumes only H4's and Gate N's already-governed classifications. No "latest," "best," "winning,"
"freshest," or "highest-confidence" evidence-selection or evidence-ranking logic of any kind is
authorized anywhere in the sandbox.

## 8. LLM / agent / MCP firewall (binding, absolute, restated)

No OpenAI/Anthropic/Gemini/other LLM provider integration, no model selector, no model registry, no
prompt construction, no RAG, no embeddings, no vector database, no probabilistic natural-language
generation, no agent framework, no autonomous tool invocation, no MCP client, no MCP server is
authorized anywhere in this artifact set.

## 9. Auth / tenant boundary (binding, restated)

No authentication infrastructure modification is authorized. The existing OIDC → `TrustedPrincipal` →
`tenant_id` → `ontology-copilot:ask` scope check → rate limiting → security audit chain is reused
verbatim and unmodified. The request payload must never become authoritative for tenant identity — the
new intent's parsed fields (`blueprint_name`, `information_element_name`) carry no tenant information
of any kind.

## 10. Persistence / migration / frontend (binding, restated)

Authorized Gate-P persistence artifacts: **NONE**. Authorized Gate-P migrations: **NONE**. Authorized
Gate-P frontend artifacts: **NONE** — the existing Ask CTEC user surface remains the frontend boundary
for this MVP (§3's discovery finding).

## 11. Acceptance / test obligations

Minimum matrix (mapped to the exact modified test file, per §4):
A. MAPPED + `EVIDENCE_PRESENT` explanation — `test_ontology_copilot_answer.py`, `test_ontology_copilot_api_postgres.py`.
B. UNMAPPED + `None` explanation — same.
C. `BLUEPRINT_NOT_FOUND` — `test_ontology_copilot_api_postgres.py`.
D. `INFORMATION_ELEMENT_NOT_FOUND` — same.
E. `INFORMATION_ELEMENT_AMBIGUOUS` — same.
F. `UNSUPPORTED_QUESTION` — `test_ontology_copilot_intent.py`.
G. Upstream integrity failure never becomes a semantic status — `test_ontology_copilot_api_postgres.py`.
H. Tenant isolation — same, mirroring the existing supplier-question tenant-isolation test.
I. Request tenant cannot override `TrustedPrincipal` tenant — same.
J. Existing supplier-question intent remains backward compatible — `test_ontology_copilot_router.py`, `test_ontology_copilot_answer.py`, `test_ontology_copilot_full_stack_postgres.py`.
K. Deterministic repeated output — `test_ontology_copilot_api_postgres.py`.
L. Forbidden vocabulary absent from rendered output — `test_ontology_copilot_answer.py`.
M. No Gate J dependency — `ast`-based import-hygiene assertion, mirroring H4's own precedent, in `test_ontology_copilot_intent.py` or `test_ontology_copilot_api_postgres.py`.
N. No Gate K aggregation — structural (single-result-per-question) assertion, same location.
Plus exactly one full-HTTP-stack Gate P scenario in `test_ontology_copilot_full_stack_postgres.py` (§4, narrowly bounded).

Full backend suite, `black`/`isort`/`ruff`/`mypy` clean. `test_domain_foundation.py` and
`test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists` MUST pass **unmodified** —
explicit proof, not assumption, that the zero-new-path finding (§3) held in practice.

## 12. Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the ten artifact paths authorized in §4 (all MODIFY, zero
CREATE) without new Product Owner authorization. If implementation discovers that any authorized
artifact's Exclusions column cannot be satisfied without touching an unlisted path — in particular
`test_runtime_architecture.py`, `dependency_container.py`, `dependencies.py`,
`test_domain_foundation.py`, any Gate I/H4/Gate N/Gate J file, any persistence/migration file, any
Keycloak file, or any `frontend/*` file — implementation MUST STOP and report the exact blocker rather
than silently expanding scope.

## 13. Approval state

**APPROVED ARTIFACT AUTHORIZATION.** Reached this state via discovery → drafting →
materialization → independent adversarial freeze review → remediation (one P1: the zero-CREATE /
no-god-service architectural justification demanded by the freeze-review authorization was not yet
recorded in §3, remediated by adding a discovery finding citing the `supply_chain_impact_api.py`
second-source precedent; one P2: §4's `ontology_copilot_api.py` row cited only CDD-025 §9 and omitted
§10's Information-Element resolution/ambiguity rule, which is also implemented in that same file,
remediated by adding the citation) → final freeze verification, with P0 = 0, P1 = 0, P2 = 0, matching
every prior companion's identical cycle in this lineage (CDD-017 G2/G3/G3.5, CDD-018 G4, CDD-019
H1/H2/H3, CDD-020 I1, CDD-021 J1/J2, CDD-022's own companion, CDD-023's H4 companion, CDD-024's own
companion). Approval of this record governs exactly the artifact sandbox in §4 above (exactly 10
MODIFY, 0 CREATE — unchanged by this freeze review); it does **not** itself authorize implementation
of any artifact listed there, and it does **not** itself authorize its own publication into
`architecture/INDEX.md` — both implementation and publication each remain separate, subsequent Product
Owner authorizations. Parent CDD-025 remains FROZEN and PUBLISHED, unchanged by this approval.
