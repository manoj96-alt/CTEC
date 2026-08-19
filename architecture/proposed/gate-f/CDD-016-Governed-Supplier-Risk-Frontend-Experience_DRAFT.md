# CDD-016 — Governed Supplier-Risk Frontend Experience (DRAFT)

Version: 1.0
Status: DRAFT — staged in `architecture/proposed/gate-f/` pending Product Owner review and a
separate publication authorization (commit, PR, merge), following the exact staging pattern already
used for the CDD-015 Deterministic Demo Data and Read-Projection Clarification draft (F-I4.0).
Authority base: `49c764ba2cdc65cbfd4f5ff611d2670f79d1e1dc`

## 1. Objective and business outcome

Make the already-governed Gate F supply-chain impact capability (CDD-015, PAD-003, RFC-017; F-I1
through F-I4, all merged) visible to an authenticated customer/user through a new, dedicated,
authenticated production frontend surface. This is the "future implementation CDD" CDD-015 §22
explicitly anticipated and explicitly deferred — no backend, API, business-policy, or ontology
authority is introduced or altered here. The objective is presentation and user intent only, never a
second business-decision authority (binding, restated throughout).

## 2. Governing authorities

Current frozen: PAD-002 (Local Development Identity Provider and Demo Persona Authorization
Boundary), PAD-003 (Gate F Impact and Mitigation Access Boundary), CDD-015 (Governed Supply Chain
Impact and Mitigation Decision) plus its three merged companion clarifications (PR #69 policy, PR #71
runtime composition, PR #73 deterministic demo data and read projections), RFC-017 (Gate F Supply
Chain Semantic Vocabulary Authorization). This CDD cites all of the above unchanged; it modifies none
of them. It follows the CDD-014 (Supplier Risk Business Workflow and User Experience) precedent
exactly: a frontend CDD that consumes an already-frozen backend/API contract (there, CDD-013;
here, CDD-015 §21/§32) and cites the existing identity/security PAD (there and here, PAD-002)
without amending it.

## 3. In scope

- One new, authenticated frontend route presenting the Gate F business story: risk signal → affected
  supplier → why it matters (materials/products/facilities/revenue exposure) → evidence → candidate
  alternatives → CTEC's governed recommendation → human-authority boundary.
- A typed Gate F frontend API client (`lib/supply-chain-impact/{api-client.ts,contracts.ts}`),
  mirroring the existing `lib/ontology-copilot/*` and `lib/supplier-risk/*` clients exactly: reuses
  the existing OIDC bearer-token session (`lib/auth/browser-session.ts`) unmodified, no new
  authentication mechanism.
- Presentation of the F-I4 primary RECOMMENDED+HUMAN_APPROVAL_REQUIRED scenario, the UNKNOWN
  scenario, and the REJECTED scenario, each reached by calling the existing, unmodified
  `POST /api/v1/supply-chain-impact/evaluations` and `GET /api/v1/supply-chain-impact/evaluations/
  {id}` endpoints with the three deterministic demo Supplier entity ids the F-I4 seeder already
  mints (documented, not re-derived — see §17).
- Presentation-only formatting: currency, timestamps, sort order, labels/icons, section
  collapse/expand. No business conclusion is computed, inferred, or overridden client-side.

## 4. Out of scope (binding, restated from CDD-015 §6/§27, RFC-017 §8, and PR #73's non-goals)

Backend business-policy changes; new Gate F evaluation semantics; new persistence; migrations; new
ontology vocabulary; new relationships; new Keycloak scope; a new persona (the existing demo persona
already holds both required scopes — see §9); approval workflow; Approve/Reject controls; override;
execution/write-back; ERP mutation; supplier-switch execution; Supply Chain Blueprint;
Source-to-Blueprint Semantic Mapping; Profiling + Gap Engine; Gap Impact + Remediation Engine;
generalized Decision Requirements/Readiness; AI ontology discovery; visual ontology modeling; what-if
simulation; Azure/production-SaaS hardening. Modification of `/demo/supplier-risk` or its calculation
logic (`frontend/lib/demo/*`) — remains explicitly out of scope per CDD-015 §27, unchanged and
untouched by this CDD; this CDD builds an entirely new, separate route (§14).

## 5. Second-authority problem (why this CDD is necessary)

The existing `/demo/supplier-risk` prototype (`frontend/lib/demo/decision-rules.ts`,
`scenario-facts.ts`) is a complete, independent, browser-side reimplementation of Gate F's decision
policy, including a duplicated `MATERIALITY_THRESHOLD_USD = 10_000_000` constant, computed entirely
client-side with no call to any governed backend. It is REFERENCE/BEHAVIORAL PROTOTYPE —
NON-AUTHORITATIVE (CDD-015 §23) and remains untouched. This CDD's governed route calls the real
`SupplyChainImpactApiService` (via the F-I3 API) for every fact and every conclusion; it introduces
no parallel calculation of severity, single-source status, revenue materiality, qualification,
capacity, lead time, cost, recommendation, or governance outcome anywhere in frontend code. Every
value in §14's information architecture is a direct projection of an API response field (§7), never
a client-side derivation of a business fact.

## 6. F-I3/F-I4 API sufficiency (verified directly against the merged `schemas.py`)

| UI need | Status | Source field |
|---|---|---|
| Supplier identity | AVAILABLE NOW | `impact.supplier_name` / `supplier_entity_id` |
| High-severity disruption | AVAILABLE NOW | `materials[].high_severity_disruption` (bool\|null) |
| Single-source exposure | AVAILABLE NOW | `materials[].single_source_exposure` (bool\|null) |
| Revenue materiality (boolean) | AVAILABLE NOW | `materials[].revenue_materiality` (bool\|null) |
| Materials/products/facilities/revenue-exposure lists | AVAILABLE NOW | `impact.{materials,products,facilities,revenue_exposures}` |
| Actual revenue dollar amount, actual severity label, actual qualification/capacity/lead-time/cost values | AVAILABLE NOW, via evidence | `evidence[].{predicate,value}` (F-I4 projection #2) |
| Recommendation outcome/reason | AVAILABLE NOW | `candidates[].{outcome,reason}` |
| Structured reasons / narrative / confidence | AVAILABLE NOW | `candidates[].{structured_reasons,narrative,confidence}` (F-I4 projection #1) |
| Evidence source/predicate/value/timestamp | AVAILABLE NOW | `evidence[].{source_system_name,predicate,value,asserted_on}` |
| Governance standing / HUMAN_APPROVAL_REQUIRED | AVAILABLE NOW | `governance_standing`, read-side `governance.human_approval_required` |
| Policy identity | AVAILABLE NOW | `policy_reference`, `policy_version` |
| **Alternate supplier's human-readable name** | **NOT AVAILABLE** | Only `alternate_supplier_entity_id` (UUID) is exposed; no name field exists anywhere in the response |
| **A "list evaluable/at-risk suppliers" or "list existing Decision Evaluations" endpoint** | **NOT AVAILABLE** | Neither `router.py` endpoint supports listing; a caller must already know a `supplier_entity_id` or `decision_evaluation_id` |

**Both gaps are presentation-layer limitations, not business-authority gaps, and neither blocks F-I5:**

- The candidate label falls back to a short, non-authoritative display form of the entity id (e.g.
  the last 8 hex characters, styled as a badge) rather than a name — this fabricates nothing and
  asserts nothing about the candidate's identity beyond what the API already returned.
- The three F-I4 deterministic scenario entry points are known, fixed, and documented (the seeder
  mints them via deterministic `uuid5` values — `backend/app/infrastructure/persistence/
  demo_gate_f_seeder.py`); the frontend route decision-links directly to those three, exactly as the
  existing Ask CTEC demo experience surfaces its own fixed "TSMC" scenario without a generic listing
  endpoint. A general "list suppliers" endpoint is a reasonable **future, separately-authorized**
  extension (would require its own narrow CDD-015 companion clarification, following the F-I4
  precedent) — **not authorized or required here**.

**No backend or API contract change is required by this CDD.** F-I5 requires zero backend
implementation changes (§13).

## 7. Frontend API client

`frontend/lib/supply-chain-impact/api-client.ts` + `contracts.ts`, mirroring
`lib/ontology-copilot/api-client.ts`/`contracts.ts` exactly:

- Types mirror `backend/app/api/supply_chain_impact/schemas.py` field-for-field. No field is ever
  generated client-side.
- Reuses `accessToken()` (`lib/auth/browser-session.ts`) for the bearer token; no new token storage,
  no new Keycloak client, no new login flow.
- `evaluate(supplierEntityId: string)` → `POST /api/v1/supply-chain-impact/evaluations`, body
  `{ supplier_entity_id }` only — no tenant, no governed fact, no recommendation, no governance
  outcome field exists on the request type, matching the backend's `extra="forbid"` contract exactly.
- `read(decisionEvaluationId: string)` → `GET /api/v1/supply-chain-impact/evaluations/{id}`.
- Explicit typed error surface distinguishing 401 (not authenticated), 403 (missing scope), 404 (not
  found / cross-tenant, indistinguishable per CDD-015 §19/§25), and network/5xx failure — never
  collapsed into one generic "error" bucket, so the UI (§20) can render each state distinctly.

## 8. Authentication

Unchanged from Gate E. `signIn()`/`completeSignIn()`/`signOut()`/`accessToken()`/
`observeSessionLoss()` (`lib/auth/browser-session.ts`) reused verbatim; the existing global
`components/session-controls.tsx` reused verbatim (no per-route session UI). Logout terminates the
local session and Keycloak SSO exactly as it already does for `/supplier-risk` and
`/ontology-studio/ask`; a subsequent protected Gate F call re-requires authentication — no new
session-lifecycle behavior.

## 9. Authorization

Both required scopes (`supply-chain-impact:read`, `supply-chain-impact:evaluate`) are already granted
to the existing single demo persona (`ctec-demo-user`), confirmed directly in the current
`keycloak/ctec-realm.json` `defaultClientScopes` (F-I3/PAD-003 §9). **No new persona and no Keycloak
change of any kind is required or authorized by this CDD.** `entity-resolution:decide` remains absent
from that persona's grants, unaffected by this CDD (§13).

Distinct frontend states (never conflated, per PAD-003 §4a's independent-scope model): unauthenticated
→ 401 → sign-in prompt; authenticated without `:read` → 403 on the read call only; authenticated
without `:evaluate` → 403 on the evaluate call only (a read-only persona can still view a
previously-evaluated scenario); authenticated with both → full experience; expired/invalid session →
401 → re-authenticate; server/network failure → distinct "service unavailable" state, never rendered
as a business UNKNOWN.

## 10. UNKNOWN, evidence, recommendation, and human-authority presentation

- **UNKNOWN**: rendered as its own explicit state ("CTEC cannot safely recommend an action because
  required governed evidence is unavailable"), using only wording the backend's actual null/absent
  fields justify — never displayed as "No," "Rejected," "Safe," "Zero," or "Not material." A `null`
  `outcome`/`reason`/`decision_record_identifier` triple is the only trigger for this state.
- **Evidence**: `evidence[]` rendered as a source/fact/timestamp list per condition — directly
  answers "why should I trust this."
- **Recommendation**: `structured_reasons`/`narrative`/`confidence` rendered verbatim from the API;
  no client-side rewriting, summarization, or LLM call of any kind.
- **Human authority**: `HUMAN_APPROVAL_REQUIRED` rendered as a status/badge with explanatory text
  only. No Approve/Reject/Override/Execute/Switch-Supplier/Write-Back control exists anywhere in this
  route — the UI states "CTEC recommends. A human decides," and stops there, exactly as CDD-015 §14
  requires of the capability itself.

## 11. Ontology dependency visualization

A simple, static Supplier → Material → BOM → Product → Facility chain rendering, built entirely from
`impact.{materials,products,facilities}` (already returned, already traversed server-side). No new
graph engine, no interactive graph layout beyond what the existing `ontology-explorer-stage.tsx`-style
static rendering already does elsewhere in this codebase — explanatory visualization only, not visual
ontology modeling (excluded, §4).

## 12. Ask CTEC relationship

Excluded from this CDD (Option C of the three considered). Supplier-risk remains a dedicated governed
experience; no hand-off into Ask CTEC's free-text interface is built. This keeps scope minimal and
introduces no new AI-authority surface. A future, separately-authorized increment could add an
optional "ask a follow-up in Ask CTEC" link — not proposed here.

## 13. Backend and Keycloak artifact check

**Zero backend implementation changes required.** Verified directly against §6: every UI element is
either already available or resolvable via a presentation-only fallback. No `gate_f/*.py`,
`configuration.py`, `supply_chain_impact_api.py`, `router.py`, or `schemas.py` change is authorized or
needed by this CDD. **Zero Keycloak changes required**, verified directly (§9) against the current
`keycloak/ctec-realm.json`.

## 14. Route strategy and mock removal

**New, separate route — Option C exactly** (create a new governed route; do not migrate, do not
preserve-and-replace, do not remove the legacy route): `frontend/app/supply-chain-impact/page.tsx`.
CDD-015 §27 forbids modifying `/demo/supplier-risk` or its calculation logic; a new route is the only
option consistent with that binding text. Existing mock/static supplier-risk authority
(`frontend/lib/demo/{scenario-facts,decision-rules,mapping-definitions}.ts`,
`frontend/app/demo/supplier-risk/**`) is **RETAINED AS VISUAL FALLBACK / REFERENCE PROTOTYPE, unmodified,
unlinked from the new governed route** — it remains reachable only at its existing `/demo/
supplier-risk` URL, never presented as, or confused with, the new governed experience. This CDD
creates exactly one new, additional, clearly-labeled authoritative customer demo path; it does not
touch, retitle, or delete the existing one.

## 15. Authorized business artifacts

None authorized. This CDD presents existing governed records and outcomes only (CDD-014 §6 precedent).

## 16. Authorized external contracts

READ-ONLY authority: the existing, unmodified F-I3/F-I4 Gate F API contract
(`backend/app/api/supply_chain_impact/{router,schemas}.py` as merged in PR #72/#74). This CDD may
implement only the published contract. No field, endpoint, scope, or authentication behavior may be
invented in frontend code.

## 17. Authorized persistence artifacts

None authorized. No browser storage of bearer tokens, complete API responses, or governed evidence
beyond ordinary in-memory component state for the current page view. Only non-sensitive UI
preferences (if any) may be retained after security review — none are proposed here.

## 18. Authorized configuration artifacts

None beyond what already exists. No new environment variable, API origin, or OIDC client setting —
the existing frontend OIDC/API configuration is reused unchanged.

## 19. Authorized implementation and test artifacts

| Artifact and path | Action | Purpose |
|---|---|---|
| `frontend/app/supply-chain-impact/page.tsx` | CREATE | Route entry point; renders the three known F-I4 demo scenario entry points and the selected scenario's governed result. |
| `frontend/app/supply-chain-impact/_components/risk-signal-panel.tsx` | CREATE | Supplier identity, risk severity/evidence (§10 information architecture item 1). |
| `frontend/app/supply-chain-impact/_components/business-impact-panel.tsx` | CREATE | Materials/products/facilities/revenue exposure (item 2), plus the dependency-chain visualization (§11). |
| `frontend/app/supply-chain-impact/_components/evidence-panel.tsx` | CREATE | Evidence list rendering (item 3, §10). |
| `frontend/app/supply-chain-impact/_components/alternatives-panel.tsx` | CREATE | Candidate supplier/qualification/capacity/lead-time/cost (item 4). |
| `frontend/app/supply-chain-impact/_components/recommendation-panel.tsx` | CREATE | Recommendation/structured reasons/narrative/confidence (item 5). |
| `frontend/app/supply-chain-impact/_components/human-authority-banner.tsx` | CREATE | HUMAN_APPROVAL_REQUIRED presentation (item 6, §10) — no action controls. |
| `frontend/lib/supply-chain-impact/api-client.ts` | CREATE | Typed API client (§7). |
| `frontend/lib/supply-chain-impact/contracts.ts` | CREATE | Types mirroring `schemas.py` exactly (§7). |
| `frontend/tests/supply-chain-impact-api-client.test.ts` | CREATE | API client unit tests (already CDD-015 §35-listed path). |
| `frontend/tests/supply-chain-impact-accessibility.test.tsx` | CREATE | WCAG 2.2 AA automated checks (already CDD-015 §35-listed path). |
| `frontend/tests/supply-chain-impact-workspace.test.tsx` | CREATE | Component/state tests: RECOMMENDED, UNKNOWN, REJECTED, HUMAN_APPROVAL_REQUIRED, 401, 403, read-only persona, evaluate-capable persona, loading, API failure, evidence/structured-reasons/narrative/confidence rendering, no client-side business computation. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Extend the architecture-drift allowlist with the paths above (mechanism only — no assertion weakened, no exception added beyond listing these exact new paths). |

No other repository path is authorized. No directory wildcard, no "related files" clause. All
unlisted paths are READ-ONLY under this CDD.

**`DEMO_RUNBOOK.md` is explicitly NOT authorized by this CDD.** Making the Gate F demo sequence
reproducible end-to-end (start infrastructure → seed F-I4 data → authenticate → open the governed
route → observe RECOMMENDED/UNKNOWN → logout → verify reauthentication) is deferred to a future,
separately-authorized Gate F closure ("F-CLOSE") phase, exactly as F-I4 deferred its own
`DEMO_RUNBOOK.md` update. This keeps this CDD's own scope to frontend implementation only.

## 20. Acceptance criteria

1. Every rendered business conclusion (severity, single-source, materiality, qualification, capacity,
   recommendation, governance standing) is a direct projection of an API response field — never a
   client-side inference, threshold comparison, or recomputation.
2. UNKNOWN is visually and textually distinct from REJECTED, RECOMMENDED, 401, 403, and backend
   failure — five to six semantically distinct states, never conflated.
3. No Approve/Reject/Override/Execute/Switch-Supplier/Write-Back control exists anywhere in the
   route.
4. No token, complete API response, or governed evidence enters persistent browser storage, URLs,
   logs, or unsafe rendered HTML.
5. Cross-tenant/nonexistent evaluation lookups render identically (no existence leak), matching the
   backend's own 404 behavior.
6. Logout terminates the session; a subsequent protected call re-requires authentication.
7. WCAG 2.2 AA automated checks pass.
8. Frontend unit, component, and contract tests pass together with all existing protected checks.
9. `/demo/supplier-risk` remains byte-for-byte unmodified.
10. Architecture-drift, dependency, secret, and API-schema checks pass with zero unauthorized diff.

## 21. Rollback

Frontend-only: revert this CDD's implementation merge; restores the preceding route set. No backend
data rollback, API downgrade, migration, or destructive action is authorized or implicated.

## 22. Architecture drift check

This CDD introduces no business entity, canonical attribute, canonical relationship, business rule,
RFC exception, architecture bypass, unapproved technology, backend change, Keycloak change, or
persistence change. Implementation must stop if satisfying any part of this CDD requires such a
change.

## 23. Non-claims

This CDD does not authorize any backend, API, Keycloak, persistence, or business-policy change; any
approval, rejection, or execution capability; any modification to `/demo/supplier-risk`; any of the
six protected future platform capabilities (Supply Chain Blueprint, Source-to-Blueprint Semantic
Mapping, Profiling + Gap Engine, Gap Impact + Remediation Engine, Decision Requirements, Decision
Readiness); or a general "list suppliers"/"list Decision Evaluations" API endpoint (§6 — a plausible
future, separately-authorized extension, not authorized here).

## 24. Numbered architecture baseline determination

**No new numbered architecture baseline is required.** Resolved directly from repository precedent,
not assumed: `architecture/released/v1.6/README.md` (read directly) states baseline v1.6 was
"Bounded CDD-013 business-facing API and CDD-014 browser-session clarification," yet CDD-014 itself
(`docs/cdd/CDD-014-Supplier-Risk-Business-Workflow-and-User-Experience-DRAFT.md`) is registered in
`architecture/INDEX.md`'s non-baseline-tracked "Governed implementation work orders" table — the
identical mechanism already used for CDD-011, CDD-012, CDD-013, and CDD-015 — not as a
baseline-tracked, checksum-verified artifact in its own right. What v1.6 actually froze as new,
baseline-tracked authority was **BSP-001** (Supplier Risk Browser Authentication and Session
Profile v1.0) — a genuinely new PAD-tier security-architecture document, because at that point in
the project's history no governed browser-session pattern yet existed for CDD-014 to cite. **CDD-016
has no analogous need**: `lib/auth/browser-session.ts` and PAD-002's OIDC/session boundary are
already FROZEN, already-established authority, already reused unchanged by two existing authenticated
frontend routes (`/supplier-risk`, `/ontology-studio/ask`). CDD-016 introduces no new security
pattern requiring its own PAD-tier document, so it has nothing analogous to BSP-001 to trigger a
baseline bump. CDD-016 therefore follows the plain CDD-011/012/013/015 pattern exactly: publication
via `architecture/INDEX.md`'s governed-implementation-work-order row only, confirmed structurally
exempt from `scripts/verify_architecture_release.py`'s baseline/checksum checks (that table carries
no Status/Current/Authority columns and no `released/v1.\d+/` location, identical to every prior CDD
entry there).

## 25. Authorization

Not yet authorized. Staged as a governance DRAFT for Product Owner review, per explicit instruction
for this discovery/drafting phase. Publication (commit, PR, merge) requires a separate, later, explicit
Product Owner authorization.
