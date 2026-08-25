# CDD-033 — Enterprise UX / Governed Product Experience — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `7bdc2ec9221a7377ec6e23d83c6f175b46763fdb`

## 1. Purpose

Enumerates exactly which repository artifacts Gate X implementation may create or modify to satisfy frozen
CDD-033 — and nothing more. This document alone does not authorize implementation; a separate, subsequent
Product Owner implementation authorization remains required.

This record was produced through: discovery against the actual repository (Gate X5 — fresh inspection of the
existing frontend architecture, the existing frontend test suite, and the exact real contract of the Gate O
Information-Element Context API and the Ontology API, confirming Context Explorer's data sources precisely
rather than assuming them), an adversarial review finding one genuine structural gap (Evidence Fitness and
generalized Data Quality sharing one page with only prose/visual separation, not structural separation) and
a Product Owner decision resolving it (X-AA-D1 — Evidence Fitness receives its own dedicated route), and a
final re-verification confirming P0=0/P1=0/P2=0 after incorporation.

## 2. Governing CDD

CDD-033 (FROZEN, `docs/cdd/CDD-033-Enterprise-UX-Governed-Product-Experience.md`). X-D1 through X-D6 binding
and unmodified. X-AA-D1 (this document's own Product Owner decision) binding and incorporated throughout.

## 3. Implementation objective

Prove that CTEC's existing, real capabilities can be presented as one coherent, honest, enterprise-grade
product experience — through frontend-only consolidation, relocation, and a small number of new,
zero-backend-capability presentation surfaces — without inventing, bridging, or implying any backend
capability that does not exist, and without weakening any frozen firewall established by CDD-030, CDD-031,
or CDD-032.

## 4. Authorized implementation slices (binding)

**Slice 1** — Enterprise shell + information architecture. **Slice 2** — Existing live-workspace relocation
(zero logic change). **Slice 3** — Context Explorer (net-new, consumes existing APIs only). **Slice 4** —
QUALITY domain (Ontology Model Completeness rename; Evidence Fitness dedicated route per X-AA-D1;
generalized-DQ planned placeholders). **Slice 5** — INTELLIGENCE reorganization + standalone Simulation
presentation. **Slice 6** — INTEGRATIONS / GOVERNANCE / ADMINISTRATION landing pages. **Slice 7** — shared
design-system components (minimal, only as justified by Slices 1-6). **Slice 8** — tests, including the new
frontend runtime-architecture firewall test.

No implementation phase may introduce a ninth slice or reassign a file to an unlisted slice without a new,
separate Product Owner decision.

## 5. Exact authorized allowlist

**AUTHORIZED_CHANGE (existing files, MODIFY only — exact change described, nothing else in the file):**

1. `frontend/components/site-shell.tsx` — replace the existing flat 7-link navigation with the grouped
   enterprise information architecture (CDD-033 §8-§9). Existing links (Home, Architecture, Dataset,
   Prototype, About) are preserved; only the grouping/structure changes.
2. `frontend/app/ontology-studio/_components/quality-panel.tsx` — rename user-facing copy from generic
   "Quality" to **"Ontology Model Completeness"** (CDD-033 §16, X-D4). The underlying `QualityScore`
   type/data/logic is unmodified — presentation label only.

**AUTHORIZED_NEW (CREATE only):**

3. `frontend/app/overview/page.tsx` — real-data-only Overview (CDD-033 §11, X-D3)
4. `frontend/app/overview/_components/overview-cards.tsx` — client-side composition of existing API data only
5. `frontend/app/data/page.tsx` — DATA domain landing (Sources, relocated static catalog) (§12)
6. `frontend/app/data/entity-resolution/page.tsx` — thin relocation wrapper for the existing Entity
   Resolution workspace, zero logic change (§10, §12)
7. `frontend/app/ontology/explorer/page.tsx` — thin relocation wrapper for the existing Ontology Studio
   workspace, zero logic change (§10, §13)
8. `frontend/app/ontology/modeling/page.tsx` — thin relocation wrapper for the existing Ontology Modeling
   workspace, zero logic change (§10, §13)
9. `frontend/app/context/page.tsx` — Context Explorer (§14)
10. `frontend/app/context/_components/context-lookup.tsx` — Blueprint/Information-Element picker and
    resolve-call presentation
11. `frontend/lib/context/contracts.ts` — TypeScript types mirroring the existing, unmodified Gate O
    `ResolveResponse` schema exactly (`blueprint_id`, `blueprint_version_number`,
    `information_element_requirement_id`, `information_element_name`, `obligation`, `coverage_status`,
    `evidence_availability_status`)
12. `frontend/lib/context/api-client.ts` — calls the existing, unmodified
    `POST /api/v1/information-element-context/resolve` endpoint exactly as published; no new endpoint, no
    new query parameter
13. `frontend/lib/context/context-provider.tsx` — lightweight, frontend-only, identifiers-only
    cross-workspace context model (§25, §34)
14. `frontend/app/quality/page.tsx` — QUALITY domain landing: status cards only (a status/link card for
    Evidence Fitness; visibly-disabled PLANNED cards for Rules/Findings/Impact/Remediation) — **no capability
    detail of any kind lives on this page** (§15, §18, X-D2, X-AA-D1)
15. `frontend/app/quality/evidence-fitness/page.tsx` — dedicated Evidence Fitness capability/governance/
    status presentation page (§15, §17, X-D2, **X-AA-D1**) — see §12 of this document for its binding
    content boundary
16. `frontend/app/intelligence/page.tsx` — INTELLIGENCE domain landing (§19)
17. `frontend/app/intelligence/ask-ctec/page.tsx` — thin relocation wrapper for the existing Ask CTEC
    workspace, zero logic change (§10, §19)
18. `frontend/app/intelligence/decisions/page.tsx` — frontend-only aggregation of existing Gate F execution
    history (§19)
19. `frontend/app/intelligence/supplier-risk/page.tsx` — thin relocation wrapper for the existing Supplier
    Risk / Supply Chain Impact workspaces, zero logic change (§10, §19, §20)
20. `frontend/app/simulation/page.tsx` — standalone What-if Simulation presentation, capability/status/
    documentation only (§21, X-D1)
21. `frontend/app/integrations/page.tsx` — INTEGRATIONS landing: relocated static connector catalog +
    descriptive-only, non-interactive MCP mention (§22)
22. `frontend/app/governance/page.tsx` — GOVERNANCE landing: relocated ontology-modeling proposal governance
    view + descriptive-only note that runtime approval does not exist (§23)
23. `frontend/app/administration/page.tsx` — ADMINISTRATION landing: `/health` liveness status only +
    descriptive-only note that user/role management is delegated to the identity provider (§24)
24. `frontend/components/design-system/page-header.tsx` — shared page header used by every new page in this
    allowlist (§30-32)
25. `frontend/components/design-system/capability-status-badge.tsx` — renders the CDD-033 §7 status taxonomy
    (SUPPORTED NOW / PLANNED / etc.) truthfully and consistently everywhere it is used — the primary
    structural tool for honoring §7 and §46
26. `frontend/components/design-system/empty-state.tsx` — shared empty/error/loading state pattern (§32)
27. `frontend/tests/gate-x-navigation.test.tsx` — asserts the rendered navigation matches CDD-033 §8 exactly
28. `frontend/tests/gate-x-honesty.test.tsx` — asserts, for every navigation item, that rendered content
    matches its declared §7 status; explicitly includes assertions that `/quality` never renders capability
    detail and `/quality/evidence-fitness` never renders a live query result (§46, X-AA-D1)
29. `frontend/tests/gate-x-runtime-architecture.test.tsx` — frontend file-boundary enforcement mirroring the
    backend's own `AUTHORIZED_CHANGED_PATHS` discipline, scoped to exactly this §5 allowlist (§47)

```
AUTHORIZED_CHANGE = 2
AUTHORIZED_NEW    = 27
TOTAL IMPLEMENTATION SURFACE = 29
```

No 30th implementation path, no directory wildcard, and no file reassigned to an unlisted slice is
authorized under any circumstance without a new, separate Product Owner decision.

## 6. Read-only dependencies

`frontend/lib/supplier-risk/*`, `frontend/lib/entity-resolution/*`, `frontend/lib/ontology-modeling/*`,
`frontend/lib/ontology-copilot/*`, `frontend/lib/ontology-studio/contracts.ts` (except the `QualityScore`
presentation label, per §5 item 2), `frontend/lib/auth/*`, every existing workspace `_components/*` file not
itself listed in §5 — consumed by import only, never modified.

## 7. Explicitly forbidden files/domains (binding)

Every path under `backend/`; every migration; `keycloak/*`; any file under a hypothetical
`frontend/app/blueprints/*`, `frontend/app/evidence/*`, `frontend/app/mappings/*`,
`frontend/app/quality/rules/*`, `frontend/app/quality/findings/*`, `frontend/app/quality/impact/*`,
`frontend/app/approvals/*`, `frontend/app/users/*`, `frontend/app/apis/*`; any interactive MCP-execution
component; any file implementing or importing across a Gate F ↔ Gate H–U bridge; any new Gate T, Gate U, or
Gate Q API route (backend file or frontend proxy of any kind); `backend/app/application/what_if_simulation.py`
and its tests; `backend/app/application/source_evidence_fitness_evaluation.py`,
`backend/app/application/source_evidence_fitness_impact_remediation.py`, and their tests;
`backend/app/application/mcp_client.py`, `backend/app/application/mcp_connector_catalog.py`;
`backend/app/application/supply_chain_impact_api.py` and every Gate F production file; CDD-030, CDD-031,
CDD-032, CDD-033, and this Artifact Authorization itself.

## 8. Route authorization (binding)

```
/overview                          — IMPLEMENT NOW
/data                              — IMPLEMENT NOW (Sources landing)
/data/entity-resolution            — REHOME EXISTING
/ontology/explorer                 — REHOME EXISTING
/ontology/modeling                 — REHOME EXISTING
/context                           — IMPLEMENT NOW
/quality                           — IMPLEMENT NOW (status cards only, no capability detail)
/quality/evidence-fitness          — IMPLEMENT NOW (X-AA-D1; capability/status only)
/quality/rules                     — PLANNED, NO ACTIVE ROUTE
/quality/findings                  — PLANNED, NO ACTIVE ROUTE
/quality/impact                    — PLANNED, NO ACTIVE ROUTE
/intelligence/ask-ctec             — REHOME EXISTING
/intelligence/decisions            — IMPLEMENT NOW
/intelligence/supplier-risk        — REHOME EXISTING
/simulation                        — IMPLEMENT NOW (status/documentation only)
/integrations                      — IMPLEMENT NOW (static + descriptive-only)
/governance                        — IMPLEMENT NOW (relocated + descriptive-only)
/administration                    — IMPLEMENT NOW (liveness status only)
```

No other route under the CDD-033 §8 information architecture is authorized. Blueprints, standalone Semantic
Mappings, standalone Evidence, Approvals, Users & Access, and interactive APIs/MCP surfaces are **NOT
SUPPORTED / MUST NOT APPEAR** — omitted entirely, not even as disabled placeholders, since no CDD-033 clause
authorizes even a placeholder for them.

## 9. API-consumption authorization (binding)

Only: `POST /api/v1/information-element-context/resolve` (Gate O, CDD-029, unmodified); `GET
/api/v1/ontology` and `GET /api/v1/ontology/{ontology_id}` (existing Ontology API, unmodified); the existing
Supplier Risk / Gate F API; the existing Entity Resolution API; the existing Ontology Modeling API; the
existing Ask CTEC API; the existing `GET /health` endpoint. No other endpoint — existing or new — may be
called by any file in this allowlist.

## 10. Backend/API expansion prohibition (binding, X-D6)

No file under `backend/` may be created or modified by any Gate X implementation phase deriving from this
document. No new REST endpoint, no new query parameter on an existing endpoint, no new repository method, no
new migration. The sole authorized backend interaction is unmodified consumption of the six endpoints named
in §9.

## 11. Persistence / migration / authentication / Keycloak prohibition (binding)

Zero new persistence. Zero migration. Zero new authentication mechanism. Zero Keycloak configuration change
— Gate X reuses Gate E's existing OIDC session flow exactly as each relocated workspace already consumes it.

## 12. Evidence Fitness structural boundary (binding, X-AA-D1)

`frontend/app/quality/evidence-fitness/page.tsx` is capability/governance/status presentation only. It
**must not**: query Gate T runtime internals; expose or create any new Gate T API (backend file or frontend
proxy); fabricate `FIT`/`STALE`/`CONFLICTING` records; fabricate evidence or fitness results; imply
generalized Data Quality; implement DQ rules, findings, remediation, or scoring. It **may** truthfully
explain the `FIT`/`STALE`/`CONFLICTING` vocabulary as Gate T's own governed semantics (CDD-031), while
explicitly and visibly stating that live Evidence Fitness evaluation is not exposed through any authorized
Gate X frontend contract. `frontend/app/quality/page.tsx` hosts only status cards for Evidence Fitness
(linking to this page) and the visibly-disabled Generalized DQ PLANNED cards — it never itself contains
capability detail for either, satisfying X-D2's "structurally distinguish" requirement through route
separation, not prose alone.

## 13. Gate F ↔ Gate H–U bridge prohibition (binding, X-D5)

No file in this allowlist may import from, call, or structurally join `backend/app/application/
supply_chain_impact_api.py` (or any other Gate F production file) together with any Gate H→I→H4→N/O→J/K→T→U
production file, type, or API response. The frontend context model (§5 item 13) may carry an identifier such
as a Supplier ID alongside an Information Element ID, but must never use that co-presence to imply, fetch, or
render a joined result that the backend does not actually produce.

## 14. Generalized Data Quality prohibition (binding, X-D2)

No `DQRule`, `DQFinding`, `DQImpact`, DQ-remediation, or DQ-scoring type, component, or route may be created
with live or seeded data anywhere in this allowlist. `/quality/rules`, `/quality/findings`, and
`/quality/impact` have **no active route** (§8) — the only permitted representation is a visibly-disabled
"Planned" card on the `/quality` landing page itself.

## 15. MCP execution / human approval / agent execution prohibition (binding)

No interactive MCP surface (discovery ≠ execution, CDD-030 §6/§21/§26). No "Approve"/"Reject" action or
approval queue (Gate S does not exist). No agent planner, memory, or orchestration surface (Gate V does not
exist).

## 16. Future Gate W/Y/Z boundary

Not referenced, not designed toward, by any file in this allowlist.

## 17. Test obligations

`frontend/tests/gate-x-navigation.test.tsx`, `frontend/tests/gate-x-honesty.test.tsx`,
`frontend/tests/gate-x-runtime-architecture.test.tsx` (all §5 items 27-29) plus every existing relocated
workspace's own pre-existing test file, updated only for its new route path with zero assertion-logic
change. `gate-x-honesty.test.tsx` is the load-bearing defense against CDD-033's own two founding findings
(the Gate F/H–U disconnection and the Quality naming collision) ever regressing — it must assert, at
minimum: `/quality` renders no capability detail; `/quality/evidence-fitness` renders no live query result;
no Supplier-Risk-domain route implies Gate T/Gate U integration; `/simulation` always displays the
SIMULATION/HYPOTHETICAL/NON-AUTHORITATIVE/NO-PERSISTENCE/NO-EXECUTION marker set; `/integrations` never
offers an MCP execution affordance; no Overview card renders fabricated data.

## 18. Accessibility / responsive / loading-error-empty obligations

Every new page and shared component (§5 items 3-26) uses semantic landmarks and `aria-label` on navigation
elements, matching or exceeding `site-shell.tsx`'s existing coverage; renders usably at standard
desktop/tablet breakpoints consistent with existing `max-w-*`/flex-wrap patterns; and presents explicit
loading, error, and empty states via `empty-state.tsx` (§5 item 26) or each relocated workspace's own
existing state handling.

## 19. Implementation stop conditions

Implementation must STOP and return to Product Owner review if: `origin/main` moves from the approved
baseline before implementation-branch creation; CDD-033 changes; this Artifact Authorization changes; any §5
path proves insufficient; a 30th implementation file is required; any §7 forbidden path appears necessary;
persistence, migration, a new backend endpoint, authentication, or Keycloak change becomes necessary; any
route beyond §8 is required; any API beyond §9 is required; a Gate F↔H–U join appears necessary to satisfy
an acceptance criterion; generalized DQ live data appears necessary; MCP execution, human approval, or agent
behavior appears necessary. No exception for a "small harmless extra file." Total implementation surface is
exactly 29 files; no 30th is authorized under any circumstance without a new Product Owner decision.

## 20. Acceptance criteria (restated from CDD-033 §49, binding here)

1. Rendered top-level navigation matches CDD-033 §8 exactly.
2. Every relocated workspace's pre-existing functional tests pass unmodified at its new route.
3. No QUALITY-domain surface uses the bare word "Quality" for Ontology Model Completeness.
4. `/quality/evidence-fitness` never shows live query data.
5. `/quality/rules`, `/quality/findings`, `/quality/impact` show no non-placeholder content and have no
   active route.
6. `/simulation` never omits the SIMULATION/HYPOTHETICAL/NON-AUTHORITATIVE/NO-PERSISTENCE/NO-EXECUTION
   marker set.
7. No Supplier-Risk-domain surface implies Gate T/Gate U integration.
8. `/integrations` offers no MCP execution affordance.
9. No Approvals/Agent surface appears anywhere.
10. No file outside §5's 29-item allowlist enters any implementation PR diff.
11. Every existing deep-link continues to resolve post-relocation.
12. Authentication/authorization behavior is unchanged for every relocated route.

## 21. Implementation PR strategy

One PR per slice (up to 8 PRs) is recommended, mirroring this lineage's own established discipline of small,
independently reviewable governed increments; a single combined PR remains permissible if repository
precedent for frontend work at implementation-authorization time favors it. Exact strategy is fixed at Gate
X8 (implementation authorization), not by this document.

## 22. Merge requirements

Each Gate X implementation PR requires its own separate, explicit Product Owner exact-head merge
authorization — matching every backend gate's own precedent in this lineage (Gate T7/T8, Gate U4/U5/U6/U7,
Gate X4).

## 23. Gate X closure criteria

All authorized slices merged and verified; §20's 12 acceptance criteria all pass; zero P0/P1 at every
implementation checkpoint; no unauthorized file ever entered a merge; `gate-x-runtime-architecture.test.tsx`
passing on every merge commit.

## 24. Authorization

This Artifact Authorization is **approved for publication**, reached via Gate X5 (discovery, drafting, and
adversarial review), a Product Owner decision (X-AA-D1 — Evidence Fitness receives its own dedicated route,
resolving the one P1 finding from initial review), a final Gate X5 re-verification (P0=0/P1=0/P2=0), and
this Gate X6 publication-preparation turn. **Publication/freeze of this Artifact Authorization does NOT
itself authorize Gate X implementation.** A separate, subsequent Product Owner implementation authorization
(Gate X8, following the established Gate X7 merge-authorization step) is required before any file in §5 may
be created or modified — matching every prior CDD's identical multi-step discipline in this lineage.
