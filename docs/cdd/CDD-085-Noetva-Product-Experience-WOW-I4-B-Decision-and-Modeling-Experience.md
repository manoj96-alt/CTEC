# CDD-085 — Noetva Product Experience WOW-I4-B: Decision and Modeling Experience (Discovery + I4-B1 Authorization)

**Status:** FROZEN
**Originating phase:** NOETVA-PRODUCT-EXPERIENCE-WOW-I4-B-DRG (Discover → Resolve → Govern; implementation not begun by this artifact)
**Amends:** nothing frozen in place. Complements CDD-015/016 (Supply Chain Impact), CDD-028 (Ontology Modeling), CDD-033/078/079/080/081/082/083/084 (WOW program). WOW-I3-A and WOW-I3-B remain PASS + MERGED + CLOSED and are **not reopened**. WOW-I4-A (PR #244, `9dbac52`) remains open, deployed, and awaiting operator acceptance — **not discarded, not rewritten, treated as this artifact's baseline**.

**Scope of this artifact:** complete discovery of the two operator-flagged deficient surfaces (Supply Chain Impact; Ontology Modeling), their real data/API/governance contracts, a frozen target visual/information architecture for each, and **explicit implementation authorization for exactly the first bounded slice ("I4-B1": Supply Chain Impact)**. I4-B2 (Ontology Modeling) is fully governed below but its implementation is sequenced to begin only after I4-B1 completes its own deploy → VM → operator-acceptance cycle, per §16.

---

## 1. Purpose

The operator visually reviewed the deployed WOW-I4-A candidate and accepted the Noetva branding migration, Overview, Intelligence/Supplier Risk landing, and the (already-frozen, unmodified) Ontology Explorer. Two surfaces were flagged as below the Noetva Intelligence Observatory bar: Supply Chain Impact, and Ontology Studio / Governed Visual Ontology Modeling. This artifact discovers the exact real truth behind both and freezes a narrowly-scoped, evidence-backed redesign authorization — presentational restructuring of real, already-fetched data, never new capability, never a broadened claim.

## 2. Authoritative baseline

`main` = `0e2223d26697b53d84478780b814102c2bb571cb` — confirmed via local fetch, `git ls-remote`, and the GitHub API at the start of this phase. `product/wow-i4` @ `9dbac52922336950a07e539b2995ac0fe557fb20` (the WOW-I4-A candidate) — confirmed identically. PR #244: `OPEN`, `mergeable: MERGEABLE`, not merged, not touched by this artifact.

## 3. Predecessor governance, re-hashed and confirmed byte-identical

| Artifact | SHA-256 |
|---|---|
| CDD-015 (Governed Supply Chain Impact and Mitigation Decision) | `9280dea25a7fe47486041638ad080bdac8349de425dd0616f57d289f408ac3de` |
| CDD-016 (Governed Supplier Risk Frontend Experience) | `42df983368eec1580b8c6ba39f9ccc96327421a49a4780375c3a444d8200df90` |
| CDD-028 (Governed Visual Ontology Modeling with Proposal Approval and Publication) | `0a350a4296473961353710a76ecf359667ea9effb92072e3d154beecd69d3704` |
| CDD-028 (Artifact Authorization) | `c20e21d2359e7104be3066914b5c275e0d4ea84ded1ccbcdd451801ac5d35e89` |
| CDD-028 (Keycloak Scope Defect Authorization) | `01b71fc1a1f4be24e94af242f8a3f11387184955227e5c0d1b8aaf4b8d2ce5c3` |
| CDD-028 (Ontology Modeling Read-Authority Amendment) | `70053583e4e22bab0a4acb94f8f3b709d6c00f2cf0ae8f8c15c8dd40451b2c52` |
| CDD-033 (Artifact-Authorization-Gate-X) | `61576536c7a6336bc0e410b0e05575204c31d4d8b628c85491ce43b9c820d735` |
| CDD-078 | `5492ef570b0e9cf3e509eb25a220f944a74cb4824b236d7f101693e3d85ae15c` |
| CDD-079 | `cb9792da6f6307a0d68d8e5c70ac92edb0f62337ddbf997b9082f19169fa7401` |
| CDD-080 | `81e26e5710620448765f1f30e21ec01799eec532fa02ff4e6190006782dcb1a4` |
| CDD-081 | `549cc792d0e30e6aafe459de537f1ff34aada0f3886ccdfdec9d69ced411ce2f` |
| CDD-082 | `815e18d4609c28e070824bab6d606991959abadc92f7aee34e1fc4842bf3eeb2` |
| CDD-083 | `aa49a1f1e7d2a1e20239db2fec313ee79a2a5d9b2fbd17201e8ae7d095ef2d32` |
| CDD-084 | `c1e527d9b7643e82207df2d15e79d372d03fe6106acb1eb945536ff6419afdf8` |

## 4. Supply Chain Impact — route/component/API architecture

Single route `frontend/app/supply-chain-impact/page.tsx` (193 lines), a `WorkspaceState` union (`idle|loading|unauthenticated|forbidden|unavailable|result`) driving 3 fixed real-UUID demo scenario buttons (CDD-016 §6, a documented, bounded limitation — no general "list suppliers" endpoint exists), each triggering a real `POST /api/v1/supply-chain-impact/evaluations` re-fetch (`supplyChainImpactApi.evaluate`, request body `extra="forbid"`, accepts only `supplier_entity_id`). On result, 6 child panels render in fixed vertical order: `risk-signal-panel.tsx` → `business-impact-panel.tsx` → `evidence-panel.tsx` → `alternatives-panel.tsx` → `recommendation-panel.tsx` → `human-authority-banner.tsx`. `frontend/lib/supply-chain-impact/{contracts,api-client}.ts` mirrors `backend/app/api/supply_chain_impact/schemas.py` field-for-field, zero drift.

## 5. Supply Chain Impact — real-data contract (verified field-by-field)

- **Dependency data is real but hop-grouped, not edge-level.** `backend/app/application/supply_chain_impact_api.py` (`_traverse_impact`) performs a real ontology-graph traversal (Supplier→Material→{Product via BOM, or direct}→Facility, and →Revenue Exposure), matching the exact WOW-I3-B ontology relationships. The exposed `ImpactSummaryResponse`, however, deduplicates `materials`/`products`/`facilities`/`revenue_exposures` into flat arrays merged across all materials — **no per-material→per-product edge is present in the contract exposed to the frontend**. CDD-016 §11 already pre-authorizes exactly a "simple, static Supplier → Material → BOM → Product → Facility chain rendering, built entirely from `impact.{materials,products,facilities}`... explanatory visualization only" — a hop-grouped visualization is therefore **already governed**; a per-edge-traced visualization would not be truthful and is **not authorized**.
- **`confidence` is deterministic policy confidence, never AI confidence.** `backend/app/domain/decision_engine/model.py` (`DecisionConfidenceLevel`: High/Medium/Low) computed by a fixed-threshold classifier (`service.py`, `score >= high_threshold` → HIGH) — zero LLM/ML in this path. The current bare "Confidence: High" label is a real comprehension risk (readable as probabilistic AI confidence) — §7 below freezes its correction.
- **`outcome`** (`RECOMMENDED`/`CANDIDATE`/`REJECTED`, or absent → `undefined`) is produced by Gate F's DRM, a deterministic 4-condition AND policy (high-severity ∧ single-sourced ∧ revenue-material ∧ qualified-capable-alternate). An absent outcome (all-Unknown-none-False) is the real, truthful "Insufficient governed evidence" state already rendered.
- **`governance_standing`** has exactly one real value, `HUMAN_APPROVAL_REQUIRED` — no "auto-approved" state exists in the system today; the current binary show/hide of `HumanAuthorityBanner` is already state-space-exhaustive.
- **Alternatives** real fields: `qualification`, `capacity`, `leadTimeDays`, `costUsd` (each sourced from that candidate's own `evidence[]` by predicate). **No score/ranking field exists** — none may be fabricated or implied via visual ordering beyond the order the API returns.
- **Evidence** real fields: `source_system_name`, `predicate`, `value`, `asserted_on` — the complete shape.
- Zero `--obs-*` Observatory tokens anywhere in this route today; it predates the WOW-I1 visual migration entirely (architecturally identical in age to the legacy cluster branding-migrated, not visually migrated, in I4-A).
- No `<table>` in this route (all `<ul>`/`<ol>`/`<dl>`) — lower structural responsive risk than table-heavy surfaces.

## 6. Supply Chain Impact — UX root-cause diagnosis

The information architecture is sound and complete (Signal → Impact → Evidence → Options → Recommendation → Human Decision maps cleanly onto the 6 real panels). The defect is purely presentational: 6 panels of identical `.panel`/`eyebrow`/`h2` visual weight, no dominant anchor, the dependency chain rendered as an undifferentiated flat list rather than a hop-grouped structure, evidence as a bare `<ul>` rather than scannable evidence objects, and zero Observatory-token visual language — making it look like a formatted API response rather than a governed decision workspace, exactly as the operator observed.

## 7. Supply Chain Impact — frozen target experience (I4-B1)

Four visual/structural sections, same real data, same panel components' underlying fields, restructured:

1. **Decision Context** — the existing 3-scenario picker, restyled onto `.obs-*` tokens; behavior unchanged (real re-fetch, unchanged request shape).
2. **Signal + Impact** — `RiskSignalPanel` and a redesigned `BusinessImpactPanel` presented as a paired unit. The dependency chain becomes a **hop-grouped** visualization: columns for Supplier → Materials → Products → Facilities/Revenue Exposure, built from `impact.{materials,products,facilities,revenue_exposures}` exactly as today, connected by a **CSS-only** visual connector between hop-groups (no new graph/diagram library — reuses the existing `--obs-intelligence` cyan and `.mono` machine-ID-demotion tokens already established by Ontology Explorer, applied as tokens only, not by importing any Explorer component). A visible caption states plainly that grouping reflects relationship hops, not a specific traced item-to-item path — truthful given §5's contract limitation.
3. **Evidence + Alternatives** — `EvidencePanel` becomes scannable evidence objects (source, predicate, value, timestamp) instead of a bare list. `AlternativesPanel` becomes comparable cards using only the 4 real fields (`qualification`/`capacity`/`leadTimeDays`/`costUsd`); no ranking, score, or ordering claim beyond the API's own return order.
4. **Governed Decision** — `RecommendationPanel` and `HumanAuthorityBanner` merge into one visually dominant unit (the page's primary anchor, per §8), using the frozen, rationed `.obs-intelligence-surface` treatment (CDD-078 §3) — the same treatment already used for Overview's hero and Ontology's orientation region. The `confidence` label changes from bare "Confidence: High" to **"Policy confidence: High"** (or equivalent qualifying wording) to correctly convey deterministic-policy semantics, never probabilistic AI. Outcome value (`RECOMMENDED`/`CANDIDATE`/`REJECTED`) does **not** drive outcome-dependent color-coding in this phase — reusing OQI's verified/conflict color vocabulary here would risk conflating this deterministic-policy outcome with OQI's distinct "governed evidence quality" semantic; the unit uses the neutral `--obs-intelligence` anchor treatment regardless of outcome value.

No panel is removed. No field is added. No new fetch, endpoint, or client-side computation of a business conclusion is introduced — the existing test's own governed assertion ("no business conclusion is computed client-side: only backend-returned outcome/reason/narrative/confidence are ever rendered") remains true by construction.

## 8. Recommendation + human-authority visual contract

The Governed Decision unit (§7.4) is the page's dominant visual anchor — confirmed against real capability, not assumed: CDD-016's entire purpose is producing exactly this governed recommendation with mandatory human authority, and it is the single fact a CEO/VC/executive needs in 10 seconds. Within the unit, ordering is fixed: **recommendation first, human-authority statement immediately beneath it, in the same visual block** — never separated, never re-ordered, never smaller/less prominent than the recommendation itself. The exact governed text "Noetva recommends. A human decides. No action is taken automatically." (already migrated in I4-A) is preserved verbatim. No Approve/Reject/Override/Execute/Switch-Supplier/Write-Back control is added — confirmed forbidden by CDD-016 §23 and the existing test's explicit "zero action buttons" assertion, both untouched.

## 9. Ontology Modeling — route/component/API architecture

`frontend/app/ontology/modeling/page.tsx` and `frontend/app/ontology-studio/ontology-modeling/page.tsx` are confirmed byte-identical thin wrappers, both rendering `<OntologyModelingWorkspace />` (`frontend/app/ontology-studio/ontology-modeling/_components/ontology-modeling-workspace.tsx`, with `propose-form.tsx`, `proposal-list.tsx`, `decision-dialog.tsx`). `/ontology/modeling` is linked from `governance/page.tsx`; `/ontology-studio/ontology-modeling` is linked from `ontology-modeling-link-card.tsx` (unconditionally rendered inside `StudioClient`) — both genuinely live, non-orphaned entry points. `frontend/lib/ontology-modeling/{contracts,api-client}.ts` mirrors `backend/app/api/ontology_modeling/schemas.py` exactly. Six real endpoints: `POST /proposals`, `GET /proposals`, `GET /proposals/{id}`, `POST /proposals/{id}/approve`, `POST /proposals/{id}/reject`, `POST /proposals/{id}/publish`.

## 10. Actual proposal/governance lifecycle (verified against `ontology_modeling_proposal_governance.py`, not assumed)

`ProposalStatus = "Proposed" | "Approved" | "Rejected" | "Published"` — **exactly four real, persisted states**:

```
Proposed --APPROVE--> Approved --PUBLISH--> Published (terminal)
Proposed --REJECT-->  Rejected (terminal)
```

`publish()` (gated on status `Approved`) is the sole path that writes real rows into `entity_types`/`institutional_concepts`/`relationship_types`/`ontology_relationship_bindings` — a published proposal becomes a genuine canonical ontology object, indistinguishable from seed data, and would appear in Ontology Explorer. CDD-028 §13 is explicit and binding: **"REVIEW is an action a human performs over a `Proposed` row (reading it), not a persisted state."** No redesign may render "Review" as a 5th system state or status chip — only the 4 real `status` values may ever be shown as state. Approve and Reject share one scope (`ontology-modeling:approve`); Publish is independently scope-checked (a successful approve never implies publish authority) — both already real, live, tested actions inside `DecisionDialog`, not aspirational.

Reconciled against `gate-x-honesty.test.tsx`'s "Governance never exposes an Approve/Reject action" assertion: that test scopes only the `/governance` landing page's own "Runtime human approval" section (a distinct, explicitly-not-available OQI/supply-chain concept) — it makes no claim about the Ontology Modeling workspace, which is a separate, real, tested capability. No contradiction.

## 11. Route-duplication resolution

`/ontology/modeling` and `/ontology-studio/ontology-modeling` remain **both live, both unmodified in this phase** — per explicit instruction, no automatic redirect. Canonical-ownership determination for a future phase: `/ontology/modeling` sits under the `/ontology/*` namespace as a sibling of the accepted, canonical `/ontology/explorer`, matching the same "Ontology owns UNDERSTAND-and-MODEL" domain framing already established; `/ontology-studio/ontology-modeling` follows the same legacy `/ontology-studio/*` naming already retired for the bare index (CDD-083 §3's redirect precedent). **Recommended eventual resolution** (not authorized here): canonicalize onto `/ontology/modeling`, redirect the `/ontology-studio/ontology-modeling` child the same way the bare `/ontology-studio` index was redirected — deferred to a future governance freeze once I4-B1/I4-B2 are accepted.

## 12. Ontology Modeling — frozen target experience (I4-B2)

1. **Governed change lifecycle indicator** — a small, Observatory-styled stepper/status strip showing exactly the 4 real states (Proposed → Approved → Published, with Rejected as the alternate terminal branch from Proposed) driven strictly by each proposal's real `status` field. No "Review" state rendered. Reuses `--obs-intelligence`/`.status-tag`/`.mono` tokens already established elsewhere — no new component library.
2. **Proposal Composer** — the existing real Concept/Relationship toggle and real dropdown-sourced Source/Target selectors, restyled onto Observatory tokens; no new field, no cardinality invented.
3. **Proposal Preview** — a new, purely client-side, non-canonical preview reflecting only the data the user has already typed into the open form (echo, not a fetch) — a draft node for a Concept proposal, or `[Source] --relationship--> [Target]` for a Relationship proposal. Unmistakably labeled **"PROPOSAL PREVIEW — NOT YET PART OF THE GOVERNED ONTOLOGY"**, and visually distinct from Ontology Explorer's canonical/verified node treatment (dashed border, muted/pending tone — never the same solid `--obs-intelligence` selected-node treatment Explorer uses, so it can never be mistaken for a real, published graph). Renders nothing before the user has typed a name (or selected both endpoints for a relationship) — never a placeholder guess.
4. **Proposal Queue** — the existing table wrapped in a proper `.table-wrap`/`overflow-x` container (fixing the one real responsive risk found), status rendered via `.status-tag` per the real 4-value enum. The bare `"No proposals yet."` empty state is replaced with the existing `EmptyState` design-system component, explaining truthfully (from §10's real lifecycle only): what a proposal is, that an authorized reviewer must approve or reject it, that publish is a separate, independently-authorized step, and that no canonical ontology mutation has occurred yet.
5. `DecisionDialog`'s existing approve/reject/publish behavior (busy/error/409-conflict/403-scope handling) is preserved exactly — visual restyling only, zero behavior change.

## 13. Proposal-preview decision

Approved as described in §12.3: technically achievable and truthful (a live echo of the user's own already-entered form state, never fetched or inferred data), explicitly and unmistakably labeled as non-canonical, visually distinct from Explorer's real-node treatment. This is the only new UI element authorized across both I4-B1 and I4-B2 that does not already exist as a rendering of a real field — it renders zero facts the user did not just type themselves.

## 14. Empty/loading/error-state decisions

Supply Chain Impact: existing idle/loading/401/403/unavailable states (§5) are restyled onto Observatory tokens with no textual or behavioral change — the existing test suite's exact assertions on this behavior remain the acceptance bar. Ontology Modeling: the proposal-queue empty state is upgraded per §12.4; loading/error/403/409 states inside `DecisionDialog` are restyled only, not rewritten.

## 15. Responsive strategy

Supply Chain Impact: no `<table>` exists in this route; the new hop-grouped dependency visualization must reflow to a single stacked column below a defined breakpoint (matching the established `760px` convention already used elsewhere in `globals.css`), never causing horizontal page overflow. Ontology Modeling: the proposal table gets an explicit `.table-wrap`/`overflow-x:auto` wrapper (the one concrete risk found); the composer's Source/Target relationship fields must stack, not compress, below `760px`.

## 16. Accessibility strategy

Supply Chain Impact already has a dedicated `axe`-based accessibility test (`supply-chain-impact-accessibility.test.tsx`) exercising all 6 panels with real fixture data — restructured markup must continue to pass this test unmodified in its assertions (structure may change, WCAG 2.2 AA conformance may not regress). Ontology Modeling has no dedicated axe test today; verify need for one alongside the workspace test update per §19. Both surfaces: preserve existing labels/roles exactly where behavior is unchanged; the new proposal-preview element must carry an explicit `aria-label` naming it a preview, and the hop-grouped dependency visualization must have a non-visual (e.g. definition-list or ARIA-described) fallback so screen-reader users get the same real information a sighted user gets from the columns, consistent with the accessible-fallback discipline already established for Ontology Explorer's graph.

## 17. Visual hierarchy / token strategy

Both surfaces adopt the same `--obs-*` token vocabulary and hierarchy vocabulary already frozen in CDD-079/CDD-084: PAGE (eyebrow/title/explanation), SECTION (semantic eyebrow/title/concise explanation), and a new DECISION OBJECT vocabulary for the Governed Decision unit (recommendation / rationale-basis / policy / human authority) and GOVERNANCE OBJECT vocabulary for the Ontology Modeling lifecycle (proposal state / authority / permitted next action). Uppercase/letter-spacing remains reserved for eyebrows, compact semantic category labels, and small state chips — never normal prose or section headings, matching the existing established convention.

## 18. Explicit truth-contract protections

Every rule in the governing prompt's §10 list is preserved. Specifically reaffirmed for this artifact: the dependency visualization is hop-grouped, never per-edge (§5/§7.2); `confidence` is relabeled to state its real deterministic-policy meaning, never implied as AI confidence (§5/§7.4); alternatives carry no invented score/ranking (§5/§7.3); the recommendation/human-authority ordering and exact governed sentence are preserved verbatim, never implying autonomous execution (§8); the Ontology Modeling lifecycle renders only the 4 real persisted states, never a fabricated "Review" state (§10/§12.1); the proposal preview is unmistakably labeled non-canonical and renders only the user's own just-entered data (§12.3/§13); publish's real meaning (a genuine canonical-ontology write) is neither overstated nor understated. The Golden Thread (`SAP=US` / `PLM=MX`, no Supplier Portal, no Specification-missing claim) is not touched by either surface and is not broadened. Live agent reasoning remains `NOT_INVOKED`; the deterministic Gate F DRM/GRM basis for Supply Chain Impact's recommendation is not re-framed as agentic.

## 19. Explicit rejected/fabricated concepts

Rejected, with reason: a per-material→per-product traced edge in the dependency visualization (not in the exposed API contract, §5); any alternatives score/ranking/percentage (no such field exists); any outcome-dependent color-coding reusing OQI's verified/conflict semantic (risks conflating two distinct meanings, §7.4); rendering "Review" as a 5th Ontology Modeling state (CDD-028 §13 explicitly forbids treating it as persisted); any new Approve/Reject/Execute-style control on Supply Chain Impact (forbidden by CDD-016 §23, reaffirmed); resolving the `/ontology/modeling` vs `/ontology-studio/ontology-modeling` duplication in this phase (explicitly deferred, §11); touching `/demo/supplier-risk` (forbidden, CDD-015 §27); any redesign, reopening, or visual change to Ontology Explorer itself (frozen, operator-accepted).

## 20. Exact authorized path accounting

### I4-B1 — Supply Chain Impact (AUTHORIZED FOR IMPLEMENTATION NOW)

**AUTHORIZED_CREATE (≤1):**
1. `frontend/tests/supply-chain-impact-decision-unit.test.tsx` — new, narrowly-scoped coverage proving the hop-grouped dependency visualization and the merged Governed Decision unit render correctly from real fixture data, with no fabricated per-edge claim and no outcome-dependent color assertion. Create only if the existing two test files cannot be extended cleanly to cover this net-new structure — verify need before creating.

**AUTHORIZED_MODIFY (7 unconditional):**
2. `frontend/app/supply-chain-impact/page.tsx`
3. `frontend/app/supply-chain-impact/_components/risk-signal-panel.tsx`
4. `frontend/app/supply-chain-impact/_components/business-impact-panel.tsx`
5. `frontend/app/supply-chain-impact/_components/evidence-panel.tsx`
6. `frontend/app/supply-chain-impact/_components/alternatives-panel.tsx`
7. `frontend/app/supply-chain-impact/_components/recommendation-panel.tsx`
8. `frontend/app/supply-chain-impact/_components/human-authority-banner.tsx`

**AUTHORIZED_MODIFY (1 unconditional, additive CSS only):**
9. `frontend/app/globals.css` — new `.obs-sci-*` classes only; no existing token renamed/reassigned.

**AUTHORIZED_MODIFY (conditional, exact enumerated set, verify need before touching):**
10. `frontend/tests/supply-chain-impact-workspace.test.tsx` — touch only where restructured markup requires an assertion to target new DOM structure; no assertion may be weakened or removed, only relocated to match new structure.
11. `frontend/tests/supply-chain-impact-accessibility.test.tsx` — touch only if axe surfaces a real new violation to fix; never touch to suppress a finding.

**FORBIDDEN (I4-B1):** any backend file; `infra/**`; any file under `frontend/app/quality/**`; any file under `frontend/app/ontology/**`/`frontend/app/ontology-studio/**`; `frontend/app/demo/supplier-risk/**`; any new API endpoint, field, or client-side business-conclusion computation; any approve/reject/execute control; any dependency/graph library.

```
I4-B1: CREATE ≤ 1, MODIFY ≤ 8 (unconditional) + ≤ 2 (conditional), DELETE = 0, TOTAL ≤ 11
```

### I4-B2 — Ontology Modeling (GOVERNED NOW, IMPLEMENTATION SEQUENCED AFTER I4-B1 ACCEPTANCE)

**AUTHORIZED_CREATE (1):**
1. `frontend/app/ontology-studio/ontology-modeling/_components/proposal-preview.tsx` — the new, client-side-only, non-canonical proposal preview (§12.3/§13).

**AUTHORIZED_MODIFY (4 unconditional):**
2. `frontend/app/ontology-studio/ontology-modeling/_components/ontology-modeling-workspace.tsx`
3. `frontend/app/ontology-studio/ontology-modeling/_components/propose-form.tsx`
4. `frontend/app/ontology-studio/ontology-modeling/_components/proposal-list.tsx`
5. `frontend/app/ontology-studio/ontology-modeling/_components/decision-dialog.tsx` (visual restyle only — zero behavior/state-transition change)

**AUTHORIZED_MODIFY (1 unconditional, additive CSS only):**
6. `frontend/app/globals.css` — new `.obs-om-*` classes only.

**AUTHORIZED_MODIFY (conditional):**
7. `frontend/tests/ontology-modeling-workspace.test.tsx` — extend for the lifecycle indicator, preview, and new empty state; no existing assertion weakened.
8. A new dedicated accessibility test for this workspace — create only if discovery at implementation time confirms none exists and the surface's new interactive elements (preview, lifecycle indicator) warrant one.

**FORBIDDEN (I4-B2):** everything forbidden for I4-B1 above, plus: `frontend/app/ontology/modeling/page.tsx` and `frontend/app/ontology-studio/ontology-modeling/page.tsx` (thin wrappers, route-duplication resolution deferred, §11); any change to `approve()`/`reject()`/`publish()` request/response shape or authorization scope; rendering any 5th lifecycle state; any Ontology Explorer file.

```
I4-B2: CREATE = 1, MODIFY ≤ 5 (unconditional) + ≤ 2 (conditional), DELETE = 0, TOTAL ≤ 8
```

## 21. Test authorization

Both subphases: full frontend suite, targeted new/updated tests per §20, Gate-X (honesty/navigation/runtime-architecture/brand), `tsc --noEmit`, `eslint --max-warnings=0`, `prettier --check .`, `next build`. Supply Chain Impact's existing `axe`-based accessibility test must continue passing with zero WCAG regression. No test may be weakened, deleted, or have an assertion removed merely to make the suite pass.

## 22. Docker verification plan

Both subphases: build via `az acr build` from the clean committed candidate using the complete governed build-argument set (unchanged from every prior phase this session); pull and inspect the resulting bundle before deployment for the intended new markers (hop-grouped dependency structure markers / lifecycle-indicator and preview markers as applicable), continued absence of `localhost:8000` and the Microsoft Graph resource ID, and continued presence of the resource-qualified auth scope and the I4-A Noetva branding markers (never regressed).

## 23. Azure visual-acceptance plan

Both subphases: deploy only the frontend candidate to the existing Azure DEV/DEMO Container App, preserving the exact certified backend digest and making zero infra/Entra/PostgreSQL/Key Vault/Cloudflare change. Live smoke of the modified route plus the full existing smoke set (auth, OQI, Ontology Explorer, other I4-A-migrated routes) to prove zero regression. **Operator visual acceptance is required before merge of either subphase**, per the established "Claude changes the product, Azure proves the product, operator acceptance closes the visual decision" discipline. I4-B1 and I4-B2 each get their own independent acceptance checkpoint — I4-B2 implementation does not begin until I4-B1 is deployed and reviewed.

## 24. Rollback plan

Standard Container Apps revision rollback: the prior healthy revision is retained at 0% traffic through every deploy in this session and can be restored by a single traffic-split change; no database, Entra, or infra state is touched by either subphase, so rollback is purely a frontend revision-traffic change.

## 25. CEO/VC 10-second comprehension test

Supply Chain Impact target: "Noetva connects governed evidence to business impact, evaluates real alternatives, produces a governed recommendation, and keeps the human as the decision authority." Ontology Modeling target: "Noetva lets enterprises evolve the ontology through a governed proposal and authorization process rather than allowing uncontrolled schema changes." Both are comprehension targets for the visual design to achieve through real, already-existing data — not license to add literal marketing copy.

## 26. Git topology recommendation

WOW-I4-A (`product/wow-i4` @ `9dbac52`, PR #244) remains open and unmerged, and several I4-B1 files (`recommendation-panel.tsx`, `human-authority-banner.tsx`, `supply-chain-impact/page.tsx`) were already touched by I4-A's branding migration. I4-B1 (and later I4-B2) **must stack on top of the current `product/wow-i4` head**, not branch from `main`, to inherit the Noetva branding fix and avoid reintroducing "CTEC" text or creating an avoidable merge conflict. Recommended branch: `product/wow-i4-b1`, created from `product/wow-i4` @ `9dbac52`, targeting `product/wow-i4` (not `main`) as its PR base — mirroring the exact child-branch-before-parent topology already used successfully for PR #242 → `product/wow-i3-drg` → `main` in WOW-I3-A.

## 27. I4-A preservation

I4-A's candidate (`9dbac52`) is treated as this artifact's unmodified baseline throughout. No file authorized above overlaps with an I4-A-authorized-only concern (site-shell wordmark, the legacy-cluster branding files, the Ask-workflow files) except where a file is legitimately touched by both phases for different reasons (branding text in I4-A; visual restructuring in I4-B1) — in those cases, I4-B1's diff must be reviewed to confirm the I4-A branding text is preserved, not reverted. PR #244 stays open and unmerged; no implementation commit is created by this artifact.

## 28. Explicit exclusions/deferments

The route-duplication resolution (§11), a dedicated Ontology Modeling accessibility test's necessity, and I4-B2's implementation start are all deferred past this artifact. The deferred OQI Explainability + Actionability follow-up (CDD-083 §11) remains untouched and unaddressed. No backend, infra, Entra, PostgreSQL, Key Vault, or Cloudflare change is authorized or expected in either subphase.

## 29. STOP conditions (evaluated, none triggered)

Route ownership for both surfaces is unambiguous (§4, §9). Both surfaces' product purpose is established directly from code (§5, §10). No proposed UI element lacks backend support (the preview is pure client-side echo; every panel field is real). No branding change here alters an API contract. No navigation change is proposed. Truth status for every field discussed is directly verified, not assumed. No accepted OQI/Ontology surface requires redesign — Ontology Explorer is untouched; the one OQI-protected file touched by I4-A (`report-execution-dialog.tsx`) is not touched again here. Implementation scope is tightly, exactly authorized for I4-B1, with I4-B2 equally exactly authorized but explicitly sequenced later.

---

No unresolved architectural question blocks the I4-B1 boundary authorized above. I4-B2 is fully governed and ready, sequenced to begin only after I4-B1's own operator acceptance.

Safe to proceed to I4-B1 implementation exactly as authorized above.
