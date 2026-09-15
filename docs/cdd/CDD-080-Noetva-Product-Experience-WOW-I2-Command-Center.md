# CDD-080 — Noetva Product Experience WOW: I2 Command Center Discovery, Resolution, and Authorization

**Status:** FROZEN
**Originating phase:** NOETVA-PRODUCT-EXPERIENCE-WOW-I2-DRG (discover + resolve + govern only — no product UI implementation in this artifact)
**Amends:** nothing frozen. Builds directly on CDD-078 (Discovery + Resolution) and CDD-079 (Governance + WOW-I1 Authorization), both re-verified byte-identical before this artifact was written. Builds on the certified, merged WOW-I1 foundation (main `129ff833f3c1e0c73ca07a4fb37d715c5592e660`), not reopened.
**Scope:** discovery of the current Overview/Command-Center implementation and real-data availability, binding product-experience decisions for WOW-I2, and the exact WOW-I2 implementation authorization. WOW-I3/I4 remain named and sequenced but not authorized to implement here.

---

## 1. Governance baseline (verified, not assumed)

`origin/main` = `129ff833f3c1e0c73ca07a4fb37d715c5592e660` (fetched and re-verified at the start of this phase; matches the FINAL REPORT recorded at WOW-I1's own merge). PRs #235/#236/#237 confirmed `MERGED` with the exact merge-commit SHAs already on record. CDD-078 re-hashed: `5492ef570b0e9cf3e509eb25a220f944a74cb4824b236d7f101693e3d85ae15c`. CDD-079 re-hashed: `cb9792da6f6307a0d68d8e5c70ac92edb0f62337ddbf997b9082f19169fa7401`. Both byte-identical to their frozen values. No STOP condition triggered by this check.

## 2. Current Command Center / Overview truth map (discovery, evidence-based)

**Route and current source (`origin/main`):** `frontend/components/site-shell.tsx` nav entry `{ label: "Overview", href: "/overview" }`. `frontend/app/overview/page.tsx` (13 lines) renders `PageHeader` (title "Overview", description containing stale `"...CTEC activity..."` wording) plus `<OverviewCards />`. `frontend/app/overview/_components/overview-cards.tsx` (~95 lines, client component) fires `Promise.allSettled([supplierRiskApi.queue(), entityResolutionApi.queue(), ontologyModelingApi.listProposals(), ontologyApi.getConnectors()])` on mount and renders 4 real count cards (Supplier risk assessments → `/intelligence/supplier-risk`, Entity resolution cases → `/data/entity-resolution`, Ontology proposals → `/ontology/modeling`, Connector catalog → `/integrations`) plus a static 5th "Ask CTEC" card (→ `/intelligence/ask-ctec`). A per-source `unavailable` flag (from `Promise.allSettled`'s per-promise status) renders "Unavailable" rather than a fabricated `0` on failure — confirmed correct today, must not regress.

**Material finding — this is exactly the anti-pattern the governing prompt names:** four visually-equal operational-queue counts with no executive "what's at risk / why it matters" signal anywhere. Zero OQI, reliance, criticality, or Golden Thread data appears on `/overview` today. Zero WOW-I1 primitives are used (no `--obs-*` tokens, no `StatusIndicator`, no Lucide icon, no Sora/Manrope class) — the route is 100% unmigrated from the I1 foundation; only `PageHeader` (already-shared, untouched) is in use.

**Material finding — a real terminology collision, resolved in §7 below:** `frontend/app/quality/_components/command-center.tsx` is a real, already-shipped, already-named `CommandCenter` component — but it is rendered only by `frontend/app/quality/page.tsx`, answering the OQI-specific question "can I rely on my enterprise knowledge" via `oqiApi.commandCenter()` (`GET /api/v1/oqi/command-center`) and a `RelianceHero` sub-component. **"Overview" (the WOW-I2 target) and OQI's own "Command Center" component are two different, both currently-real things.** The internal product doc `docs/product/NOETVA-CEO-PRODUCT-MASTERY.md` (untracked local reference, not in the git tree) independently confirms the company's own usage treats "Overview" and "Command Center" as two distinct stops in the same 15-minute CEO walkthrough (lines ~620, ~626), not synonyms. CDD-079 §24 already froze "WOW-I2 — Enterprise Understanding Command Center" as this *phase's own name* — that naming is not reopened here — but the on-screen UI text decision is resolved explicitly in §7.

**Backend data backing OQI's `CommandCenter`/reusable by Overview:** `backend/app/application/oqi_product_experience_service.py` `CommandCenterRow` dataclass (lines 219–226, `origin/main`) — exactly 7 fields, all real tenant-scoped SQL-derived counts, zero score/percentage/composite field (enforced by two dedicated backend tests: `test_command_center_has_no_score_field_at_dataclass_level`, `test_command_center_response_has_no_score_or_monetary_field`): `reliance_supported_count`, `reliance_at_risk_count`, `reliance_unknown_count`, `critical_dependencies_at_risk_count`, `open_findings_count`, `active_agent_investigations_count`, `pending_human_authorizations_count`. Frontend contract mirrors this exactly (`frontend/lib/oqi/contracts.ts`), fetched via `oqiApi.commandCenter(signal)` → `GET /api/v1/oqi/command-center` (`frontend/lib/oqi/api-client.ts`).

**Findings list, for the "highest-priority open finding" signal:** `oqiApi.listFindings({ family?, status?, cursor?, limit? }, signal)` → `GET /api/v1/oqi/findings`, returns `FindingSummary[]` (`finding_id`, `finding_family`, `condition_label`, `status`, `first_seen_at`, `last_seen_at`, `affected_entity_id/type`, `highest_criticality`, `reliance_state`). No server-side sort-by-criticality parameter exists — a client-side sort of the returned page is required (§7 below), reusing the backend's own real, closed, four-value `Criticality` ordering (`backend/app/domain/oqi_business_impact/dependency.py`: `LOW < MEDIUM < HIGH < CRITICAL`, an explicit `criticality_sort_key` function whose own docstring forbids attaching quantitative/monetary meaning — mirrored client-side, not reinvented).

**Golden Thread availability:** the certified Country-of-Origin finding (`_QUALITY_CONDITION_ID = "oqi-demo-supplier-country-of-origin"`, `backend/app/infrastructure/persistence/demo_oqi_seeder.py`) is a normal row returned by the same `/api/v1/oqi/findings` endpoint like any other — Overview can truthfully surface it today as the current highest-criticality open finding in the seeded demo dataset, with **zero new backend work**, by generically selecting the top item from a real, unfiltered client-side sort — never by hardcoding this specific finding ID.

**Explicitly checked and confirmed NOT AVAILABLE as an Overview-suitable aggregate (narrower gaps closed by direct read this phase, not left as guesses):**
- Ontology-impact / business-impact / evidence-disagreement detail exist only per-finding (`GET /findings/{id}/ontology-impact`, `/business-impact`, `/evidence`) — no aggregate summary endpoint. Surfacing this on Overview would require an additional per-finding fetch beyond the executive-summary altitude this phase owns (see §7 exclusions).
- Supply-Chain Impact has **no aggregate/queryable summary at all** — `frontend/app/supply-chain-impact/page.tsx` is a fixed, three-scenario, evaluate-on-demand workspace (`DEMO_SCENARIOS`, `backend/app/infrastructure/persistence/demo_gate_f_seeder.py`), not a listable/countable resource. **NOT AVAILABLE** for any Overview aggregate signal.
- Governance's "state" is a static, hardcoded per-capability display (`frontend/app/governance/page.tsx`, two fixed `CapabilityStatusBadge` sections) — no aggregate governance-state query exists. **NOT AVAILABLE.**
- Context is a single-lookup tool (`ContextLookup`, one blueprint/element at a time) — no aggregate "how much context has evidence" signal exists. **NOT AVAILABLE.**
- Entities/relationships counts: no standalone aggregate count endpoint found outside the ontology-studio workspace APIs already used by the existing "Ontology proposals" card. **NOT AVAILABLE** as a new signal.

**Loading/error/empty/unauthorized states today:** `overview-cards.tsx` has exactly one state check (`if (!cards) return <EmptyState kind="loading" .../>`) — no distinct page-level error or unauthorized state; a 401 on any of the 4 sources silently renders that one card as "Unavailable" via `Promise.allSettled`, never surfaced as an auth condition. By contrast, `quality/_components/command-center.tsx` already has a real four-state model (`loading`/`loaded`/`unauthorized`/`error`) with materially better truth-contract copy ("Not authorized... does not indicate anything about the underlying Reliance state" / "...a technical failure, separate from the governed Reliance state") — this is the pattern WOW-I2 adopts (§7).

**Navigation map (all confirmed real, existing routes; zero dead links found today):** `/intelligence/supplier-risk`, `/data/entity-resolution`, `/ontology/modeling`, `/integrations`, `/intelligence/ask-ctec` — all exist. Additional routes confirmed to exist for WOW-I2's new links: `/quality/findings`, `/quality/findings?status=OPEN` (exact precedent already used by `quality/_components/command-center.tsx` for `open_findings_count`), `/quality/findings/[findingId]`, `/quality`.

**Accessibility today:** `RelianceHero` uses `role="group" aria-label="Enterprise knowledge reliance"` plus a decorative `aria-hidden="true"` color dot per cell (color is not the sole differentiator — the adjacent text label always carries the real state). `overview-cards.tsx` has zero `aria-*` attributes. Neither file declares more than one heading level per card; no `<h1>` conflict found (PageHeader supplies the page's one `<h1>`).

**Performance today:** exactly 4 parallel API calls via `Promise.allSettled` on Overview (no waterfall); OQI's own `CommandCenter` fires exactly 1. No chart/graph library imported by any Overview-adjacent file. Confirmed baseline dependencies (`frontend/package.json`, `origin/main`): `reactflow ^11.11.0` (in use), `cytoscape ^3.32.0` (present, zero import sites anywhere in `frontend/` — confirmed still unused), `lucide-react 1.46.0` (exact pin per CDD-079 §3), no charting library (`recharts`/`chart.js`/`d3`/`visx`) present. This is the "no new dependency" baseline WOW-I2 must respect.

**Tests today:** no dedicated Overview test file exists. Coverage lives entirely in `frontend/tests/gate-x-honesty.test.tsx` (imports `OverviewPage` directly from `@/app/overview/page`): (a) asserts all-4-sources-failed renders 4× "Unavailable" and zero fabricated "0"; (b) asserts a genuine successful-but-empty response is allowed to render a real "0" (only a *failed* fetch must never render "0"). `gate-x-navigation.test.tsx` only asserts the nav item's label/href, not page content. Both must keep passing (or be updated with equivalent replacement assertions, verified necessary before touching — same discipline CDD-079 §12 applied to `evidence-fitness-workspace.test.tsx` in I1).

**Legacy "CTEC" terminology, Overview-relevant scope only (full inventory performed; only the Overview-touching items are actioned here, per §41's ceiling):** `frontend/app/overview/page.tsx`'s `PageHeader` `description` prop reads *"Real, already-authorized CTEC activity across supplier risk, entity resolution, ontology governance, and connectors."* — classified **USER-VISIBLE BRAND DEBT**, and since this exact file is already an authorized WOW-I2 MODIFY path for the redesign, its wording is corrected in this phase (§12 table) as a zero-additional-risk, in-scope fix — not a product-wide rename. The "Ask CTEC" card's own label is **left unchanged** in WOW-I2: it is a stable, consistently-used label elsewhere in the product (the `/intelligence/ask-ctec` route it links to, and that route's own workspace heading, both still say "Ask CTEC") — changing only the Overview card's wording while its destination still says "Ask CTEC" would create a *new* inconsistency, not fix one. No other CTEC occurrence anywhere else in the product is touched by WOW-I2 (out of this phase's scope; full inventory preserved for a future, dedicated brand-migration phase to use).

## 3. WOW-I1 primitive reuse (confirmed exact APIs, from direct source read)

`StatusIndicator` (`frontend/components/design-system/status-indicator.tsx`) exports `ObservatoryStatus = "verified" | "conflict" | "attention" | "pending" | "unknown" | "deferred" | "not-invoked" | "not-exercised" | "unavailable" | "error"`, each rendered as label+shape+color. `EmptyState` (`frontend/components/design-system/empty-state.tsx`) exports `EmptyStateKind = "loading" | "empty" | "error" | "not-invoked" | "not-authorized" | "deferred" | "unavailable"`. **Both already cover every state WOW-I2 needs — zero modification to either file is required or authorized.** `PageHeader` (unmodified, no inline styling) continues to supply Overview's one `<h1>`. The `.observatory-shell`/`.observatory-header`/`.observatory-main`/`.panel` contract (WOW-I1/R1/R2, `frontend/app/globals.css` lines ~590–760) already gives any new Overview content the correct light-on-dark ambient default for free, as long as new panel-shaped content either lives inside an existing light-island selector or is itself dark-canvas-native (inherits correctly, same as `PageHeader`).

## 4. Real-data inventory — final classification table

| Signal | Classification | Evidence |
|---|---|---|
| Reliance Supported / At Risk / Unknown counts | **LIVE/API-AVAILABLE**, LIVE/UI-AVAILABLE (already on `/quality`) | `CommandCenterResponse.reliance_*_count` |
| Open findings count | **LIVE/API-AVAILABLE** | `CommandCenterResponse.open_findings_count` |
| Critical dependencies at risk count | **LIVE/API-AVAILABLE**, LIVE/UI-AVAILABLE (already on `/quality`) | `CommandCenterResponse.critical_dependencies_at_risk_count` |
| Active agent investigations count | **LIVE/API-AVAILABLE** (genuinely can be, and today is, real `0` — not fabricated) | `CommandCenterResponse.active_agent_investigations_count` |
| Pending human authorizations count | **LIVE/API-AVAILABLE** | `CommandCenterResponse.pending_human_authorizations_count` |
| Highest-priority open finding (incl. today's Golden Thread) | **DERIVABLE WITHOUT NEW SEMANTICS** (client-side sort of a real list, mirroring the backend's own closed criticality ordering) | `oqiApi.listFindings({status:"OPEN"})` + `Criticality` domain ordering |
| Per-finding ontology/business impact, evidence detail | LIVE/API-AVAILABLE **but per-finding only** — **DEFERRED from Overview** (crosses into investigation-workspace altitude, §7) | `/findings/{id}/ontology-impact` etc. |
| Supplier risk queue count | LIVE/API-AVAILABLE, **already used by current Overview** | `supplierRiskApi.queue()` |
| Entity resolution case count | LIVE/API-AVAILABLE, already used | `entityResolutionApi.queue()` |
| Ontology proposal count | LIVE/API-AVAILABLE, already used | `ontologyModelingApi.listProposals()` |
| Connector catalog / health | LIVE/API-AVAILABLE, already used, already truthful vocabulary (`health_status`, `maturity: "Demo Connected"\|"Skeleton Available"\|"Roadmap"`) | `ontologyApi.getConnectors()` |
| Supply-Chain Impact aggregate | **NOT AVAILABLE** (no aggregate endpoint exists; fixed 3-scenario workspace only) | `demo_gate_f_seeder.py`, `supply-chain-impact/page.tsx` |
| Governance aggregate state | **NOT AVAILABLE** (static per-capability page, no query) | `governance/page.tsx` |
| Context/evidence-availability aggregate | **NOT AVAILABLE** (single-lookup tool, no aggregate) | `context/page.tsx` |
| Entities/relationships aggregate count | **NOT AVAILABLE** (no standalone endpoint found) | — |
| Any trust score / confidence % / health score / ROI / trend | **NOT AVAILABLE, and not authorized to invent** | No such field exists on any real contract |

## 5. Mental model / lifecycle boundary (reaffirmed, not reopened)

The product mental model `CONNECT → UNDERSTAND → EVALUATE → REASON → GOVERN → IMPROVE → TRUST` (CDD-079 §2) remains architecture/storytelling language — WOW-I2 does not render it as a stepper or nav. The OQI governed lifecycle (`Detect → Evidence → Assess → Ontology Impact → Recommend/Reason → Human Authorization → Remediate → Re-evaluate → Resolve`) remains a wholly separate vocabulary. For today's certified Golden Thread finding specifically: Detect/Evidence/Assess/Ontology-Impact = real (`PROVEN`); Recommendation = `NOT_INVOKED`; Human Authorization = `NOT_EXERCISED`; Remediation = `NOT_INVOKED`; Re-evaluation = `NOT_APPLICABLE`; Resolution = `NOT_RESOLVED`; live agent reasoning = `NOT_INVOKED`. WOW-I2's spotlight card renders exactly this truth — a finding that is `OPEN`/`HIGH` criticality with no recommendation/authorization/remediation yet — never implying progress that hasn't occurred, using `StatusIndicator`'s existing `not-invoked`/`not-exercised` states verbatim, not a new stepper.

## 6. Three visual signatures (reaffirmed, not implemented here)

Evidence Rail, Conflict Lens, and Governed Decision Gate (CDD-079 §11) remain WOW-I3-owned. WOW-I2 consumes only the tokens they will later use (`conflict`, `attention`, `authority`, `verified`, etc.) — no signature-specific component is created in this phase. The spotlight card (§7) is a plain composition of `StatusIndicator` + text + a link, not a Conflict Lens implementation.

## 7. Resolved product-experience decisions (binding)

**A. Information hierarchy (5 levels, per the governing prompt's own frame, each mapped only to real, confirmed data):**
1. *Executive signal* — one hero numeral: `open_findings_count` (Display-tier Sora, the one hero-numeral use CDD-079 §7 already reserved for WOW-I2), paired with a compact eyebrow (e.g. "Open governed findings").
2. *Why* — a single "highest-priority open finding" spotlight: the top item from a client-side `Criticality`-sorted, `status="OPEN"` fetch of `oqiApi.listFindings`, rendering `condition_label`, `finding_family`, and a `StatusIndicator status="conflict"` for its `highest_criticality`.
3. *Impact* — the same spotlight's own already-returned `reliance_state` field, rendered via `StatusIndicator` (`verified`/`conflict`/`unknown` per its real value) — no additional per-finding ontology/business-impact fetch (deferred, §7-exclusions below).
4. *Governance* — a compact two-item rail: `pending_human_authorizations_count` (via `StatusIndicator status="attention"` when `>0`, else a calm real-zero state) and `active_agent_investigations_count` (via `StatusIndicator status="pending"` when `>0`, else real-zero) — not a Governed Decision Gate implementation.
5. *Explore* — the existing 5 cards (4 real operational-queue counts + Ask CTEC), visually migrated onto the dark/token foundation, hrefs unchanged.

**B. Hero concept:** the single Display-tier numeral (`open_findings_count`) described above — no gauge, no score, no composite "health" number. This is the full extent of "hero" for I2; no additional decorative hero graphic is authorized.

**C. Executive signal:** as (A)(1) — `open_findings_count`, real, zero-fabrication.

**D. Reliance/trust representation:** the three real `CommandCenterResponse` reliance counts, each via `StatusIndicator` (`verified`/`conflict`/`unknown`), replacing today's plain-colored-dot `RelianceHero`-style markup with the shared, already-accessible I1 primitive — not a new gauge.

**E. Attention representation:** the two-item rail in (A)(4). A real `0` renders as a real `0`, never omitted or dressed up — consistent with the existing `gate-x-honesty.test.tsx` precedent that a genuine empty/zero result must never be conflated with an unavailable/failed one.

**F. Golden Thread representation:** the generic "highest-priority open finding" spotlight in (A)(2) — never a hardcoded reference to this specific finding ID. In the current seeded demo dataset this generically surfaces the real Country-of-Origin finding; the same code would surface a different finding under different data with zero change, which is the correct, honest design (per the governing prompt §5's explicit prohibition on inference beyond what current product data proves).

**G. Ontology-impact preview:** **not implemented in I2.** Per-finding ontology/business-impact data requires a separate fetch beyond `FindingSummary`'s already-returned fields, which would pull Overview into finding-detail depth — explicitly out of scope (§15 of the governing prompt, "Command Center ≠ OQI Detail"). The spotlight's CTA link into `/quality/findings/{finding_id}` is where that depth is genuinely explored.

**H. Governed-action/human-attention representation:** the rail in (A)(4), linking to `/quality/findings` (the same real destination `quality/_components/command-center.tsx` already uses for these two exact fields) — not a new authorization-queue route (none exists), not a Governed Decision Gate.

**I. Navigation/CTA model (every destination independently confirmed to exist):**
- Spotlight card → `/quality/findings/{finding_id}` (only rendered when a real finding exists; a genuine zero-open-findings result renders `EmptyState kind="empty"`, never a dead or fabricated card).
- Reliance triplet → `/quality` (the real, deeper Reliance/Command-Center surface already answering this question in depth — not an invented query-string filter the API doesn't support).
- Hero numeral → `/quality/findings?status=OPEN` (exact existing precedent, reused verbatim from `quality/_components/command-center.tsx`).
- Attention rail (both items) → `/quality/findings` (same existing precedent).
- The 5 existing Explore cards → their current, unchanged, already-confirmed-real hrefs.

**J. Loading state:** `EmptyState kind="loading"` (existing, unmodified kind) while the new OQI-sourced fetches (`commandCenter()`, `listFindings(...)`) are in flight — combined with the existing 4-source loading state into one coherent panel-level loading treatment; the 4 legacy cards' own `Promise.allSettled` loading handling is preserved unchanged.

**K. Empty state:** a genuine `open_findings_count === 0` (or a genuinely empty findings list) renders `EmptyState kind="empty"` for the spotlight slot — a real, calm "no open findings" message, never fabricated content to fill the space.

**L. Error state:** `EmptyState kind="error"` on a real `OqiApiError` (non-401/403) from either OQI fetch, adopting `quality/_components/command-center.tsx`'s own truth-contract copy pattern ("...a technical failure, separate from the governed state") rather than inventing new wording.

**M. Unauthorized state:** `EmptyState kind="not-authorized"` (the WOW-I1-added kind, previously unused in Overview) on a `401`/`403` from either OQI fetch, adopting the same "...does not indicate anything about the underlying state" truth-contract language already proven on `/quality`. The 4 legacy operational-queue cards keep their existing, separate `Promise.allSettled`→"Unavailable" handling, unchanged — the two failure models are not merged.

**N. Responsive hierarchy (1440/1024/390):** DOM/paint order is fixed as (1) hero numeral + spotlight, (2) reliance triplet, (3) attention rail, (4) Explore grid — identical source order at every breakpoint, single-column stack at 390px (CSS reflow only, no conditional content removal), so the highest-priority signal is always first regardless of viewport, per the governing prompt's §7/§20 explicit requirement.

**O. Motion:** exactly one new, real, state-triggered use: the already-defined-but-unused `obs-conflict-ripple` keyframe (`frontend/app/globals.css`) applied as a one-shot reveal animation on the spotlight card when real finding data first arrives (not on every re-render, not looping) — via a new small class (§12) guarded by the existing global `prefers-reduced-motion` rule. No other new motion is authorized; the reliance triplet, attention rail, and Explore grid remain static.

**P. Accessibility:** the reliance triplet and attention rail each get a `role="group" aria-label="..."` container (matching the existing `RelianceHero` precedent); every `StatusIndicator` use already satisfies label+shape+color; heading hierarchy stays single `<h1>` (PageHeader) with `<h2>` for each of the four new sections; all links remain native, focusable `<Link>`s; `axe-core`/`vitest-axe` (already present, per CDD-079 §20) extended to cover the new component.

**Q. Performance:** exactly 2 additional real API calls (`oqiApi.commandCenter()`, `oqiApi.listFindings({status:"OPEN", limit: 50})`), both folded into the same parallel `Promise.allSettled` pattern already proven on this page (now 6 total sources, still zero waterfall). No new dependency; `criticality_sort_key`-equivalent client-side sort is a small, pure, in-memory operation over at most 50 rows.

**R. Website continuity:** reuses the shipped `--obs-*` tokens and the `.observatory-main`/`.panel` contract as-is. One new, narrowly-rationed elevated/glass surface class is authorized for the hero+spotlight region only — `.obs-intelligence-surface` (a `.layer-plane`-derived translucent/elevated treatment) — consistent with CDD-078 §3's explicit allowance that this treatment is rationed to "a small number of intelligence surfaces (Command Center, finding detail, ontology explorer)," never a default for every panel. It is not applied to the reliance triplet, attention rail, or Explore grid, which remain the existing flat `.panel` treatment.

**S. Terminology:** the page's `PageHeader` title remains **"Overview"** (nav label unchanged per the governing prompt §34); the visible UI text of this redesign **never displays the literal string "Command Center"** anywhere on screen, specifically to avoid colliding with the real, distinct, already-shipped `CommandCenter` component/feature on `/quality`. "WOW-I2 — Enterprise Understanding Command Center" remains the internal *phase name* only (CDD-079 §24, not reopened). The stale "...CTEC activity..." wording in `overview/page.tsx`'s description is corrected to real, Noetva-branded copy as part of this phase's own authorized edit to that exact file (§12); the "Ask CTEC" card label is explicitly left unchanged (reasoning in §2).

**T. Data-truth constraints:** no fabricated trend/percentage/score/ROI/confidence/agent-count/customer-activity value anywhere in this component, at any state (loading/loaded/empty/error/unauthorized) — every number rendered is a direct, unmodified pass-through of a real API field or a pure client-side sort of real API fields, exactly matching CDD-079 §23's real-data contract.

## 8. Explicit I3/I4 exclusions (not authorized here, per the governing prompt §39)

Not authorized in WOW-I2: OQI finding-detail redesign, Evidence Rail, Conflict Lens, Governed Decision Gate, ontology graph redesign, `/ontology-studio` route-consolidation (CDD-079 §15, still deferred to WOW-I3), Supply-Chain Impact redesign, Context/Integrations/Governance/Administration redesign. No tiny "shared-foundation correction" was found demonstrably required in any of these areas for Command Center integrity — none is touched.

## 9. WOW-I2 exact authorization table

Every path below is exact — no wildcard, no directory-level authorization.

| Path | Action | Purpose |
|---|---|---|
| `frontend/app/overview/_components/enterprise-understanding-panel.tsx` | CREATE | New Command-Center composition (page-specific, not a generic reusable primitive): hero numeral, spotlight, reliance triplet, attention rail — implements §7(A)–(T) above |
| `frontend/tests/overview-enterprise-understanding.test.tsx` | CREATE | Behavioral tests: real-data rendering, loading, empty (zero open findings), error, unauthorized, no-fabricated-metric assertion, criticality-sort correctness (synthetic multi-finding fixture), navigation hrefs, `StatusIndicator` label+shape+color usage, accessibility roles/labels |
| `frontend/app/overview/page.tsx` | MODIFY | Compose `<EnterpriseUnderstandingPanel />` above the existing `<OverviewCards />`; correct the stale "...CTEC activity..." `PageHeader` description wording (§7-S) |
| `frontend/app/overview/_components/overview-cards.tsx` | MODIFY | Visual migration only onto `--obs-*` tokens/`StatusIndicator` where applicable — the exact same 5 data sources and hrefs, unchanged |
| `frontend/app/globals.css` | MODIFY | Add, additively: `.obs-intelligence-surface` (rationed elevated/glass class, §7-R), a spotlight-entry animation class applying the existing `obs-conflict-ripple` keyframe (§7-O), and the hero-numeral Display-tier typography rule — no existing selector removed/renamed |
| `frontend/tests/gate-x-honesty.test.tsx` | MODIFY (only if required) | Update only if the `overview-cards.tsx` visual migration changes a selector this existing test depends on — verify first; do not modify if its existing assertions (by text content) already survive unchanged |

**Explicitly NOT authorized in WOW-I2:** `frontend/components/design-system/status-indicator.tsx`, `frontend/components/design-system/empty-state.tsx` (both already cover every state needed — zero change required or permitted), `frontend/components/design-system/page-header.tsx`, any backend file, any file under `frontend/app/quality/`, `frontend/app/ontology*/`, `frontend/app/supply-chain-impact/`, `frontend/app/context/`, `frontend/app/integrations/`, `frontend/app/governance/`, `frontend/app/administration/`, any second graph/chart/animation library, `frontend/tests/gate-x-navigation.test.tsx` (must continue passing unmodified).

## 10. CREATE/MODIFY/DELETE counts

CREATE = 2 (`enterprise-understanding-panel.tsx`, `overview-enterprise-understanding.test.tsx`). MODIFY = 4, with one (`gate-x-honesty.test.tsx`) conditional on actual need, verified before touching — ceiling MODIFY ≤ 4. DELETE = 0. TOTAL ≤ 6.

## 11. No new dependency (confirmed)

Zero new dependency required or authorized. Motion reuses an existing, already-defined-but-unused keyframe. Elevation reuses an existing, already-authorized (CDD-078 §3), previously-unbuilt "intelligence surface" treatment concept, expressed in plain CSS. Sorting is a pure in-memory operation over already-fetched data. `reactflow` is not touched; `cytoscape` remains unused and untouched.

## 12. Azure visual-acceptance contract for WOW-I2's own implementation phase (frozen in advance)

Minimum operator verification, once WOW-I2 is implemented and deployed to `app.noetva.ai`: the highest-priority governed open finding is identifiable within 5 seconds without opening Quality; the three Reliance counts are visible without opening Quality; every card/link resolves to a real, already-existing route (no dead CTA); human-authorization-pending state is visually and lexically distinct from "investigation in progress" and from "recommended"; no fabricated metric of any kind appears in any state (loading/loaded/empty/error/unauthorized); a genuine real zero renders as zero, an unavailable/failed source never renders as zero; supported/at-risk/unknown remain distinguishable without color alone; the page never displays the literal string "Command Center"; mobile (390px) shows the highest-priority signal first, not a shrunk desktop grid; no low-contrast text anywhere (re-verifying the exact `.observatory-main`/`.panel` contract WOW-I1/R1/R2 already established, not reopening it); the existing 5 Explore cards' behavior is unchanged; `gate-x-navigation.test.tsx` and `gate-x-honesty.test.tsx` (or its verified, equivalent replacement) both pass; Docker/local Keycloak preservation holds; backend/infra remain untouched. No phase may declare visual success from source/tests alone — Azure is the real visual acceptance environment (CDD-079 §25, reaffirmed).

## 13. Truth-contract preservation

Every distinction in the governing prompt's list (Implemented≠planned through remediation attempt≠successful remediation≠resolution) is preserved by every decision in §7 above — no section claims a capability, count, or state the real, source-verified evidence in §2/§4 doesn't support. In particular: `active_agent_investigations_count`/`pending_human_authorizations_count` being genuinely `0` for the certified Golden Thread finding is rendered as a true `0`, never omitted or implied otherwise; the spotlight never implies Recommendation/Authorization/Remediation has occurred for a finding where the real lifecycle state is `NOT_INVOKED`/`NOT_EXERCISED`.

## 14. STOP conditions evaluated

Real APIs support every proposed signal without fabrication (§4). No proposed executive signal requires a fabricated metric. The Golden Thread is surfaced only via a generic, real, unhardcoded selection over real data (§7-F). No implementation architecture here conflicts with CDD-079. No new backend semantics are required (§4/§11). No new dependency is required (§11). Current source state matched the expected post-I1 baseline exactly (§1) — no unexpected drift. CDD-078/CDD-079 hashes did not drift (§1). Command Center is implementable entirely within I1's shipped tokens/primitives and I2's own narrow additions, without crossing into I3/I4 territory (§8).

**No STOP condition is triggered. This governance artifact is authorized to freeze, and WOW-I2 implementation is authorized to the exact extent of §9/§10 above.**

## 15. Validation of this phase

Diff confirmed limited to this new file, `docs/cdd/CDD-080-Noetva-Product-Experience-WOW-I2-Command-Center.md`, only. `docs/cdd/README.md` and `architecture/INDEX.md` were checked for registration precedent: neither CDD-078 nor CDD-079's own freezing commits touched either file (confirmed via `git show --stat` on both commits), and `docs/cdd/README.md` itself states current architecture authority is determined solely by `architecture/INDEX.md`/the Architecture Release Manifest, with CDD records here explicitly excluded from that authority chain — this WOW governance series has never registered there and does not do so now, consistent with precedent. No frontend/backend implementation performed. No dependency installed. No Azure/Entra/Cloudflare/database mutation performed.
