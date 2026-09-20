# CDD-089 — Noetva Explainable Supply Chain Decision Intelligence Experience: I2 UX and Implementation Authorization

**Status:** Discovery + Resolution + Governance + exact path authorization. No implementation performed by this artifact. CDD-085/086/087/088 remain frozen, historical, byte-identical (re-verified: `4780bb04...`/`7ff109ab...`/`9124ca90...`/`aec12c2f...`). This artifact does not modify any of them — it authorizes a new phase (I2) built on top of I1-R1's now-proven domain model.

---

## 1. Authoritative state (verified before writing)

`main`=`0e2223d26697b53d84478780b814102c2bb571cb`. `product/wow-i4`=`9dbac52...` (PR #244, open, unaffected). `product/wow-i4-b1`@`3e81447042bf1210d512df41a4704e0438c6a6a` (I1-R1, PR #245, CI green, open, not merged, not deployed). Working tree clean.

## 2. I1-R1 implementation verification

Re-confirmed directly against the real, running application (FastAPI `TestClient` against a fresh, migrated, seeded real-PostgreSQL database — not mocked) at authoring time: the "recommended" scenario returns 3 real candidates with `single_source_exposure=True`, `governance_standing="HUMAN_APPROVAL_REQUIRED"`, exact `relevance_relationship="approvedSourceFor"`, and the exact B=Recommended/C=null(Unknown)/E=Rejected outcomes I1-R1's report claimed. I1-R1's own claims are independently reproduced, not merely trusted.

## 3. Existing R3 UX diagnosis

R3's live structure (unchanged by I1 — I1 touched zero frontend UI files): a risk banner, a dark "Impact Intelligence" hop-chain surface, a light-panel Evidence/Alternatives pair, and a dark "Governed Decision" hero. Diagnosed defects, confirmed by direct re-inspection of the current source:
- The hop-chain (`business-impact-panel.tsx`) still only shows Supplier→Material→Product→Facility→RevenueExposure — it has no visual concept of "potential alternative sources," because I1-R1's `approvedSourceFor` relationship did not exist when R3 shipped.
- `alternatives-panel.tsx` presents each candidate as an isolated card with no comparison structure — a reviewer must read three separate cards to notice B/C/E differ.
- `recommendation-panel.tsx`'s existing `GovernedConditions` checklist derives each candidate's qualification/capacity via `candidate.evidence.find(...)` — **this already silently depends on the exact API gap found in §7 below**: for an Unknown-outcome candidate, `evidence` is empty, so the checklist shows "Unknown" for qualification too, even when qualification is genuinely asserted `true` in the database. Not a false claim (Unknown is conservative), but an incomplete one — R3 has been unknowingly under-informing on this exact point since before I1 existed.
- No current-source-vs-potential-source visual distinction exists at all (R3 predates the concept).
- Excessive card stacking with large empty vertical space, already flagged by the operator across R1/R2/R3.

## 4. User mental model (frozen)

"I am investigating a governed supply-chain disruption. I want to understand what's at risk, why it matters, what Noetva found as potential replacements and *why each one entered consideration*, and what the deterministic policy concluded — with the human always in control." Not an admin dashboard; an investigation.

## 5. Frozen investigation narrative

Exactly the 15-point narrative in the governing prompt §3, each point already independently proven true against real data (§2): disruption → Supplier A is the current active (`supplies`) source of Material M → single-sourced → hop-grouped impact propagation to Product/Facility/RevenueExposure → `approvedSourceFor`-derived potential-source discovery → B (relevant, passing) / C (relevant, capacity unknown) / E (relevant, capacity explicitly failing) → D excluded (approved only for a different material, invisible per §7 disposition below) → Gate F evaluates each independently, no ranking → governed recommendation → human authority preserved.

## 6. Frozen information architecture

Six zones, one continuous scroll (no tabs fragmenting the story, per governing prompt §26):

**A. Decision Context** — existing scenario picker, unchanged (R1's compact segmented control already accepted).
**B. Current Sourcing Position** — new: a dedicated, visually solid "current source" statement, distinct from every "potential source" element below it.
**C. Impact Path / Business Exposure** — evolved hop-chain (unchanged data model, strengthened visual weight of the terminal Revenue Exposure node, one added real-entity-name sentence of context).
**D. Alternative Source Discovery** — new: a visually distinct "how Noetva found them" moment, using a dashed/potential-relationship connector style (never the solid style used for zone C's traced impact) to brand `approvedSourceFor` as a categorically different kind of relationship than `supplies`.
**E. Candidate Investigation** — the centerpiece: a real evidence matrix (§10 below) replacing the three isolated cards.
**F. Governed Decision** — existing pattern preserved (recommendation + human authority in one block), extended only with the corrected per-candidate condition data from §7's fix.

## 7. Above-the-fold design (1440×900 acceptance criterion)

Zones A–D (compact) plus the top of zone E must be visible without scrolling: scenario picker (short), current-source statement + single-source badge (one line), a horizontally compact impact chain (reduced vertical padding vs. R3), and the opening of the alternative-discovery moment with a real count ("3 potential sources identified for Demo Material"). Full per-candidate evidence and the Governed Decision block continue below the fold — matching the operator's own "detailed evidence may continue below" allowance.

## 8. Visual-anchor decision

**"Investigation Spine"**: one continuous, connected rail on the dark Observatory canvas running Current Source → Material → Business Exposure → Alternative Discovery → Candidates → Governed Decision. Reuses the exact `--obs-*` token connector language already established (R2/R3's hop-chain), extended with a second connector style: **solid** for traced-impact segments (Supplier→Material→Product→Facility→RevenueExposure, unchanged truth boundary — hop-grouped, never claimed item-to-item), **dashed** for the potential-relationship segment (Material→`approvedSourceFor`→candidates) — a structural, non-color way to distinguish "what happened" from "what Noetva looked for" (governing prompt §8's "not merely color" requirement). No new diagramming library; no force-directed graph; CSS-only, matching CDD-085/086's established "reuse tokens, not components" discipline.

## 9. Current-source presentation

A single, solid-treatment statement, structurally separated from the dashed candidate rail below it: "**[Supplier A name]** — currently supplies — **[Material name]**" with an adjacent "Single-source exposure: **True**" indicator. Both values already real API fields (`impact.supplier_name`, `impact.materials[].material_name`, `material.single_source_exposure`) — zero new data.

## 10. Impact/exposure presentation

Reuses R2/R3's hop-chain data model unchanged (`impact.products/facilities/revenue_exposures`, all real, already hop-grouped and disclaimed). Adds one real-entity-sourced sentence beneath the terminal Revenue Exposure node: "Revenue exposure associated with **[Product name]** via **[Facility name]**" — composed entirely from already-returned entity names, not a new derivation. The hop-grouping disclaimer remains legible, not micro-copy (R3's fix, reaffirmed).

## 11. Alternative-discovery presentation

A short, dashed-connector transition from the Material node into the candidate set, with adjacent real-data copy: "Noetva identified **N** potential source(s) for **[Material name]** through governed `approvedSourceFor` relationships" (N = `material.candidates.length`, real). No "AI search," "best," or ranking language anywhere near this zone.

## 12. Candidate-comparison / evidence pattern (centerpiece)

A real, semantic `<table>` (not a card grid) — rows are evidence fields, columns are candidates:

| Field | Candidate B | Candidate C | Candidate E |
|---|---|---|---|
| Relevance | approved potential source | approved potential source | approved potential source |
| Qualification | Pass | Pass *(requires §16 fix)* | Pass |
| Capacity | Pass | **Unknown** | **Fail** |
| Lead time | 21 days | 35 days | 45 days |
| Cost | $185,000 | $170,000 | $200,000 |
| Policy result | Recommended | *(no result — Unknown)* | Rejected |

Every row/value sourced from real, already-returned fields (`evidence[]` predicates, `outcome`) — **except** Candidate C's Qualification/Lead-time/Cost cells, which require §16's additive backend fix (currently returns empty `evidence[]` for any Unknown-outcome candidate — confirmed empirically, §16). Column header is a neutral entity reference (`Alternate Supplier (…last 8 chars)`, matching R1-R3's established, non-fabricating label convention) — no "#1"/"Top"/ranking language. Cell semantics: Pass (green, `--obs-verified`), Unknown (neutral gray, em-dash or "Unknown" text, never a color implying failure), Fail (coral, `--obs-conflict`) — text label always present, never color-only (accessibility, §24).

## 13. Candidate B / C / E individual presentation

Each candidate's reason/narrative/`Policy confidence` (existing, unchanged fields, R1-R3's established "Policy confidence" label reused) render beneath the matrix as expandable detail — see §14 (progressive disclosure). B: "Recommended: all four governed conditions are satisfied." C: no reason/narrative exist (DRM produced no record) — render the existing, already-accepted "Insufficient governed evidence... Noetva does not guess" framing, scoped per-candidate rather than page-level. E: "Rejected: candidate capacity is insufficient" — Gate F's own real, existing reason string, unchanged.

## 14. Supplier D exclusion disposition

**Option A (governing prompt §7's own stated preference), confirmed the only supportable choice**: the live API response for the recommended scenario contains exactly 3 candidates — D is never present, not filtered client-side. D remains **invisible in the normal product experience**. No frontend rediscovery logic, no new backend audit/exclusion-explanation endpoint. D's exclusion is proven only through the adversarial test suite (already proven, I1-R1 §17/§P) and the operator demo narration (§21), never rendered on-screen.

## 15. Policy-explanation pattern

Reuses and corrects R3's existing `GovernedConditions` mechanism (recommendation-panel.tsx) — the real Gate F four-condition policy (CDD-015 §11, unchanged) shown as five observable facts (3 material-level tri-states already correct today; 2 candidate-level, qualification/capacity, corrected by §16). No policy logic computed in React — every value is a direct read of an already-returned field; the backend's own `outcome`/`reason`/`narrative` remain the sole authoritative conclusion, unchanged.

## 16. Recommendation vs. authorization pattern

Unchanged from R1-R3, reaffirmed: the Governed Decision block (recommendation + exact human-authority sentence, one visual unit) remains structurally and visually separated from the candidate-evaluation zone above it by a real surface transition (light/dark or dark-canvas/dark-hero boundary), never mere proximity. No Approve/Reject/Execute/Switch-Supplier control exists or is proposed.

## 17. Provenance strategy

Progressive disclosure, matching the governing prompt §12's own suggestion: the matrix (§12) shows Pass/Unknown/Fail + the real value only; an expand affordance per candidate (or per cell) reveals `source_system_name` + `asserted_on` for that specific evidence item — avoiding a raw-database-inspector primary view while keeping every fact traceable.

## 18. API / data availability matrix

Directly re-verified against a live HTTP response (FastAPI `TestClient`, real PostgreSQL, not assumed):

| UI element | Availability |
|---|---|
| Current source name/material name | **Available directly** (`impact.supplier_name`, `impact.materials[].material_name`) |
| Single-source exposure | **Available directly** (`materials[].single_source_exposure`) |
| Impact hop entities (Product/Facility/RevenueExposure) | **Available directly** (`impact.products/facilities/revenue_exposures`) |
| $ exposure value | **Available directly** (candidate `evidence[]`, predicate `annualRevenueUsd`, only on candidates with a decision record — see below) |
| Candidate relevance relationship | **Available directly** (`candidates[].relevance_relationship`) |
| Candidate B (Recommended) full evidence | **Available directly** (`evidence[]` populated, decision record exists) |
| Candidate E (Rejected) full evidence | **Available directly** (`evidence[]` populated, decision record exists) |
| **Candidate C (Unknown) evidence — qualification/leadTime/cost** | **NOT AVAILABLE** — `evidence: []` for any candidate with no decision record, confirmed empirically (§16 below is the fix) |
| Governance standing / human authority | **Available directly** (`governance_standing`) |
| Policy reference/version | **Available directly** (`policy_reference`, `policy_version`) |
| Materiality threshold numeric value ($10M) | **Not available** (backend-config-only, never returned) — pre-existing, already-accepted limitation since R1; copy stays non-numeric ("exceeds the governed materiality threshold"), unchanged |
| Supplier D (excluded) | **Not available and correctly so** — never returned; §14 disposition (Option A) requires no exposure |

## 19. Backend additive-field decision (Option B, required)

**Confirmed necessary.** The materiality-threshold gap (§18) is pre-existing/already-accepted and needs no fix. The **Candidate-C evidence gap is new, material, and blocks the governing prompt's own explicit, repeated pass-standard requirement** ("What evidence is missing?" must be answerable from real backend data) — Option A (design around it) was evaluated and rejected: the only way to work around it without the fix is to have the frontend infer, by elimination, that the missing condition must be candidate-level once all three material-level conditions are known — this is exactly "calculating eligibility in React," explicitly forbidden (governing prompt §14).

**Root cause:** `router.py::_candidate_response` sources `evidence` exclusively via `projections.get(candidate.decision_record_identifier, ([], None, None, []))` — a record-keyed lookup that is empty whenever DRM produced no record (Unknown outcome). But `supply_chain_impact_api.py::_evaluate` already computes a full `CandidateEvidence` (via `krm.derive_candidate_evidence`, including real `assertion_ids` for qualification/capacity/leadTimeDays/costUsd) for **every** candidate, before calling DRM — this data is silently discarded today whenever DRM returns `None`.

**Exact, narrowest fix (frozen, not implemented here):**
1. `supply_chain_impact_api.py`: add one field to the domain `CandidateOutcome` dataclass — `evidence_assertion_ids: tuple[UUID, ...]` — populated from `candidate_evidence.assertion_ids` whenever `candidate_evidence is not None` (i.e., whenever a real candidate was evaluated), regardless of DRM's outcome.
2. `router.py::_candidate_response`: when `candidate.decision_record_identifier` is `None` (no record-based projection available), resolve evidence from `candidate.evidence_assertion_ids` via the **already-existing** `_evidence_items()` helper instead of the empty default — additive fallback only; the existing record-based path for Recommended/Rejected candidates is **untouched**, zero regression risk to already-passing behavior.
3. `schemas.py`: **no change** — `CandidateOutcomeResponse.evidence`'s type is already `list[EvidenceItemResponse]`; this is a population-logic fix, not a contract-shape change. Fully backward compatible.

This surfaces Candidate C's real, already-persisted `qualification`/`leadTimeDays`/`costUsd` assertions (confirmed present in PostgreSQL, I1-R1 §K) — `capacity` correctly continues to be absent (it never existed as an assertion for C), so the matrix's "Capacity: Unknown" cell remains exactly as truthful as it is today, now joined by correctly-populated Qualification/Lead-time/Cost cells instead of blank ones.

## 20. Synthetic-data sufficiency analysis

I1-R1's persisted PostgreSQL dataset already, truthfully proves every UX state this phase requires: Recommended (B), Unknown (C), Rejected (E), material-scoped exclusion (D, invisible per §14), multi-candidate (3 real candidates), single-source-exposure invariant, and the real $12M exposure chain. **No additional synthetic data is required for I2.**

## 21. Additional synthetic-data decision

None authorized or needed (§20).

## 22. Legacy secondary-navigation decision

Re-traced, unchanged from the R3 investigation: `secondaryNavItems` (`Home`/`Architecture`/`Dataset`/`Prototype`/`About`, `frontend/components/site-shell.tsx`) remains frozen "preserved exactly" across four independent governing artifacts (CDD-033 origin, CDD-062, CDD-079, CDD-084's explicit FORBIDDEN list). No new information changes this. **Deferred, explicitly** — not authorized for I2, not smuggled into implementation. `site-shell.tsx` remains FORBIDDEN (§28).

## 23. Interaction model

Minimum useful set: (1) select/focus a candidate column in the matrix (highlights that column, expands its reason/narrative beneath); (2) expand provenance per evidence row (§17); (3) scenario picker (existing, unchanged). No tabs. No "Switch Supplier," "Approve," or any action control. No interaction implies autonomous behavior.

## 24. Responsive behavior

1440px: Investigation Spine + full-width evidence table use available width confidently (no narrow floating column, addressing the operator's own "excessive unused space" finding). 1024px: table remains a real `<table>`, wrapped in `.table-wrap`/`overflow-x:auto` (the established Ontology Modeling precedent, CDD-085 §12.4/§15) — the table itself may scroll within its own bounded container, never the page. 390px: the table restructures into stacked per-candidate definition blocks (matching the existing evidence-list mobile-stack pattern already used in R3's evidence panel) — never a horizontally-scrolled table at this width, preserving CDD-085's "no horizontal page overflow" rule.

## 25. Accessibility requirements

Real `<table>` with `<caption>`/`<th scope="col">`/`<th scope="row">` for the evidence matrix (genuinely tabular data deserves genuine table semantics — a deliberate, narrow exception to CDD-085 §15's "no `<table>` exists in this route," justified exactly as Ontology Modeling's own proposal-queue table already was). Pass/Unknown/Fail always carry a text label, never color-only. Keyboard-navigable column focus/expansion. Existing `supply-chain-impact-accessibility.test.tsx` axe suite must continue to pass with zero violations against the new structure.

## 26. Motion rules

Restrained only: a brief highlight transition when a candidate column is focused/expanded; no pulsing, spinning, or "processing" motion of any kind (would imply live computation or autonomous reasoning, forbidden). No motion on page load beyond what already exists.

## 27. 60–90 second operator walkthrough (frozen, every sentence backed by §2's live-verified data)

"A disruption has affected Demo Supplier, the sole active supplier of Demo Material — Material M is genuinely single-sourced, confirmed by governed enterprise relationships, not an assumption. Noetva follows the same governed relationships to show the downstream business exposure: this material feeds Demo Product, assembled at Demo Facility, associated with $12,000,000 in revenue exposure — a real, asserted figure, not a computed estimate. Noetva then looks for suppliers with a governed, durable *approved-source* relationship to this specific material — three are found. This one has complete, passing evidence and Gate F recommends it. This one is genuinely relevant — it has an approved-source relationship to the material — but its capacity evidence was never asserted, so Noetva refuses to guess; the result stays honestly Unknown. This one is also relevant, but its capacity evidence explicitly fails the governed condition, so Gate F rejects it — with the real reason shown. Noetva explains its recommendation in full, but the decision authority stays with a human: no automatic action is ever taken."

## 28. Exact CREATE authorization

**None.** No new file — the evidence matrix is built inside the existing, already-authorized `evidence-panel.tsx`/`alternatives-panel.tsx` (or a merged treatment across them — the implementing agent may consolidate, since both already fall inside the same authorized file set); the Investigation Spine visual language extends the existing `business-impact-panel.tsx`/`risk-signal-panel.tsx`.

## 29. Exact MODIFY authorization

**Backend (3 unconditional):**
1. `backend/app/application/supply_chain_impact_api.py` — additive `evidence_assertion_ids` field + population (§19 item 1).
2. `backend/app/api/supply_chain_impact/router.py` — additive fallback evidence resolution (§19 item 2).
3. *(schemas.py explicitly NOT modified — §19 item 3 confirms no shape change.)*

**Frontend (7 unconditional, the same file set every prior round in this phase family has used — CDD-085's original ceiling, reaffirmed, never expanded):**
4. `frontend/app/supply-chain-impact/page.tsx`
5. `frontend/app/supply-chain-impact/_components/risk-signal-panel.tsx`
6. `frontend/app/supply-chain-impact/_components/business-impact-panel.tsx`
7. `frontend/app/supply-chain-impact/_components/evidence-panel.tsx`
8. `frontend/app/supply-chain-impact/_components/alternatives-panel.tsx`
9. `frontend/app/supply-chain-impact/_components/recommendation-panel.tsx`
10. `frontend/app/supply-chain-impact/_components/human-authority-banner.tsx`
11. `frontend/app/globals.css` (additive `.obs-sci-*` classes only, per CDD-085's own unbroken rule)

## 30. Exact DELETE authorization

**Zero.**

## 31. Conditional authorization (verify need before touching, exact enumerated set)

12. `backend/app/tests/test_gate_f_traversal_orchestration.py` — extend to assert Candidate C's `evidence` now contains qualification/leadTimeDays/costUsd (and still omits capacity).
13. `backend/app/tests/test_demo_gate_f_seeder_postgres.py` — extend the existing recommended-scenario evidence assertions if the new field changes what that test observes.
14. `frontend/tests/supply-chain-impact-workspace.test.tsx` — new/relocated assertions for the matrix structure, current-source statement, and Candidate C's now-populated evidence; no existing assertion weakened.
15. `frontend/tests/supply-chain-impact-accessibility.test.tsx` — touch only if axe surfaces a real new violation against the `<table>` structure.

## 32. Forbidden paths

`backend/app/integration/adapters/gate_f/drm.py`; `backend/app/integration/adapters/gate_f/krm.py` (evidence is *resolved*, not re-derived — `derive_candidate_evidence` itself is unmodified); `backend/app/infrastructure/persistence/ontology_seed.py`; `backend/app/infrastructure/persistence/demo_gate_f_seeder.py` (no new synthetic data authorized, §20); `frontend/components/site-shell.tsx`; any OQI file; any Ontology Explorer/Modeling file; any new API endpoint or route; any action control; any agent/LLM integration; `infra/**`; any Azure deploy action prior to operator visual acceptance.

```
I2: CREATE = 0, MODIFY ≤ 11 (unconditional: 2 backend + 8 frontend + 1 css) + ≤ 4 (conditional), DELETE = 0, TOTAL ≤ 15
```

## 33. Docker/build verification plan

Backend: full suite (including the real-PostgreSQL tier) green, including new Candidate-C evidence assertions; a fresh backend Docker image built from the exact committed candidate, run locally against real PostgreSQL, proving the live HTTP response now returns non-empty evidence for Candidate C. Frontend: `tsc`/`eslint`/`prettier`/full test suite/`next build` all clean; a fresh frontend Docker image built with the complete governed Azure build-arg set, inspected before deploy.

## 34. Azure visual acceptance plan

Deploy only the frontend (backend digest must remain the exact one I1-R1 proved unchanged, unless the §19 backend fix requires a new backend revision — it does, since it's a real backend behavior change; both frontend and backend get fresh revisions this round, backend digest changes only via the additive fix). Capture/inspect the primary Recommended scenario at 1440×900, 1024, and 390; inspect the Unknown and Rejected scenarios at least at 1440. Preserve `--wowi4b1r3` (frontend) and `--0000007` (backend) for rollback. **No merge until the operator visually accepts** — unit/integration tests alone are explicitly insufficient per the governing prompt §30.

## 35. Rollback strategy

Frontend: prior revision `--wowi4b1r3` retained, unchanged, redeployable at any time. Backend: prior revision `--0000007` (digest `sha256:4089026d...`) retained; the new backend revision is purely additive (§19's fallback only activates when the existing record-based path finds nothing) — a rollback to `--0000007` fully restores current behavior with no data migration involved (no schema change, no new table, no new relationship type in this phase).

## 36. Truth-contract audit

Every distinction in the governing prompt §35 is satisfied by construction and cross-referenced above: active source ≠ sourcing capability (§9 vs. §11), sourcing capability ≠ eligibility (§12/§19), relevant ≠ eligible ≠ recommended ≠ authorized (§12/§16), seeded facts ≠ seeded answer (§20, no new data needed), missing ≠ false / UNKNOWN ≠ failed / explicit false ≠ missing (§12's Pass/Unknown/Fail grammar), excluded ≠ failed (§14, D is invisible, never shown as "failed"), relationship-driven discovery ≠ ranking (§11/§12, no ranking column, no "best" language), relationship ≠ causation / hop grouping ≠ traced path (§10, disclaimer preserved), policy confidence ≠ AI confidence / deterministic policy ≠ agent reasoning (§15, unchanged Gate F), demo data ≠ customer data (unchanged tenant guard). Live agent reasoning: `NOT_INVOKED` — nothing in this artifact references or implies agentic capability.

## 37. Exact I2 implementation handoff

An implementing agent may proceed directly from §29–§32's path table: (1) apply the exact §19 backend fix (2 files, additive-only, zero regression to existing Recommended/Rejected evidence); (2) rebuild the 7 frontend files into the 6-zone architecture (§6) anchored by the Investigation Spine (§8), culminating in the real `<table>` evidence matrix (§12) fed by the now-complete Candidate C data; (3) run the full backend+frontend verification (§33); (4) build fresh Docker images for both; (5) deploy only to Azure DEV/DEMO; (6) STOP for mandatory operator visual acceptance at 1440/1024/390 before any merge. No further architectural decision is required — every UI element's data source, the one required backend change, the exact file set, and the visual/interaction/accessibility rules are frozen above.

## 38. Final disposition

UX architecture, data-gap analysis, and exact I2 path authorization frozen. One narrow, additive backend fix identified as required and precisely specified (not implemented). No synthetic data gap found. Legacy nav deferred, unchanged. No implementation performed by this artifact.

Safe to proceed to I2 implementation exactly as authorized above, when the operator directs it. Not safe to begin without applying §19's fix first — the centerpiece evidence matrix (§12) is truthfully incomplete without it.
