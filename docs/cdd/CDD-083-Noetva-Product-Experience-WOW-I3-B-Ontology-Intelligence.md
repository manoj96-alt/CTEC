# CDD-083 — Noetva Product Experience WOW-I3-B: Ontology Intelligence

**Status:** FROZEN
**Originating phase:** NOETVA-PRODUCT-EXPERIENCE-WOW-I3-B (DR/reverification + governance, this artifact; implementation follows in the same phase)
**Amends:** nothing frozen in place. Complements CDD-078/079/080 (WOW foundation, Overview), CDD-081 (WOW-I3-A OQI, including its corrected orphan-route finding, reverified below), CDD-082 (auth). WOW-I3-A remains PASS + MERGED + CLOSED and is not reopened.

**Scope:** the canonical Ontology Explorer experience (`frontend/app/ontology-studio/_components/studio-overview.tsx`, `.../ontology-graph.tsx`), the orphaned `/ontology-studio` bare index route, and additive Observatory CSS. No backend change. No OQI (`frontend/app/quality/**`) change.

---

## 1. Authoritative baseline (independently re-verified, not assumed)

`main` = `bb95a18b4007c90e97ee049c324e802b22024fdc` → after WOW-I3-A merge, `c1c3a59148f291f5797b4f8d82f9a0f668d13864` — confirmed identically via local `git fetch`/`rev-parse` and the GitHub API (`repos/manoj96-alt/CTEC/git/refs/heads/main`). PR #241 and #242 both `MERGED`. Azure frontend: revision `noetva-dev-eus2-frontend--0000017`, digest `sha256:fb026c7dc156de60c31b20cadfa23704542477ace457cc42244c22eb54b79423`, confirmed unchanged. Backend digest `sha256:4089026d29eb50f5395efee9e31a0e054ceb7a90b586930cc9bfb383c8339edb`, confirmed unchanged.

Predecessor governance re-hashed, byte-identical:

| Artifact | SHA-256 |
|---|---|
| CDD-078 | `5492ef570b0e9cf3e509eb25a220f944a74cb4824b236d7f101693e3d85ae15c` |
| CDD-079 | `cb9792da6f6307a0d68d8e5c70ac92edb0f62337ddbf997b9082f19169fa7401` |
| CDD-080 | `81e26e5710620448765f1f30e21ec01799eec532fa02ff4e6190006782dcb1a4` |
| CDD-081 | `549cc792d0e30e6aafe459de537f1ff34aada0f3886ccdfdec9d69ced411ce2f` |
| CDD-082 | `815e18d4609c28e070824bab6d606991959abadc92f7aee34e1fc4842bf3eeb2` |

## 2. Ontology architecture, independently rediscovered (two parallel read-only investigations, cross-checked)

`frontend/components/site-shell.tsx:33` — global nav's only "Ontology" entry: `href="/ontology/explorer"`. No separate "Ontology Studio" global nav entry exists.

Real route/component map:
- `/ontology/explorer` (`frontend/app/ontology/explorer/page.tsx`) — thin wrapper rendering `<StudioClient />`. **This is the canonical, linked entry point.**
- `/ontology/modeling` (`frontend/app/ontology/modeling/page.tsx`) — thin wrapper rendering `<OntologyModelingWorkspace />`; genuinely linked from `governance/page.tsx` and `overview-cards.tsx` — not orphaned.
- `/ontology-studio` (`frontend/app/ontology-studio/page.tsx`) — renders the exact same `<StudioClient />` as `/ontology/explorer`. **Confirmed orphaned**: exhaustive grep of `frontend/app` and `frontend/components` for `href="/ontology-studio"` (closing quote, excluding child paths) returns zero hits.
- `/ontology-studio/ask`, `/ontology-studio/entity-resolution`, `/ontology-studio/ontology-modeling` — each reachable via a real `<Link>` in `AskCtecLinkCard`/`EntityResolutionLinkCard`/`OntologyModelingLinkCard`, all three unconditionally rendered by `StudioClient` (which `/ontology/explorer` renders) — **confirmed not orphaned**, reaffirming CDD-081's correction of CDD-079's original all-four-orphaned claim.
- Observation (non-goal, not resolved by this artifact): `/ontology/modeling` and `/ontology-studio/ontology-modeling` are two live, separately-linked URLs rendering the same `OntologyModelingWorkspace` component. This is pre-existing architectural duplication, not an orphan problem, and out of scope here.

`StudioClient` (`frontend/app/ontology-studio/_components/studio-client.tsx`) render order: `StudioOverview` → 3 link cards → `ConnectorCatalogPanel` → `OntologyGraph` → `QualityPanel` → `ApiExportPanel` → `ActivationCard`. Loading/error/empty states are bespoke `.panel`-based (not the shared `EmptyState` component), with exact governed strings `"Loading ontology from the published Ontology Service…"` (`role="status"`), `"Ontology service unavailable"` + real backend message + Retry button (`role="alert"`), and `"No ontology data is available yet"`.

Contracts (`frontend/lib/ontology-studio/contracts.ts`, spot-checked field-for-field against `backend/app/api/ontology/schemas.py` — no drift): `Concept{entity_type_id, name, definition, definition_source, lifecycle_state, governance_status, version_number, discovery_label}`; `Relationship{relationship_type_id, name, source_concept, target_concept, lifecycle_state, governance_status, discovery_label}`. `name` is the real human-readable label for both; `entity_type_id`/`relationship_type_id` are machine identifiers. No cardinality field exists anywhere in the contract — none is invented here.

`discovery_label` (`"curated"` | `"unknown"`, computed by `backend/app/domain/ontology/resolver.py:58-63`) is a real, truthful provenance signal — whether a concept/relationship is in the curated seed definitions vs. auto-discovered — currently rendered **nowhere** in any component. This directly answers the product objective "what does Noetva actually know versus merely visualize" and is promoted in §5 below.

`OntologyDetail.quality` (`QualityScore`: `overall_score`, `method`, `dimensions[]`, `passed_checks`, `failed_checks`) is the ontology service's own **structural/model-completeness** score (`backend/app/domain/ontology/quality_score.py`) — a real, different, already-shipped concept from OQI data-quality findings. Already surfaced via `QualityPanel` and `StudioOverview`'s stat grid; untouched by this artifact; never conflated with OQI.

Accessible/legend claim (CDD-081) **reconfirmed true**: `OntologyGraph` already renders an unconditional `<ul>` fallback (`{source} — {name} → {target}` per relationship, independent of graph render state) and the canvas container carries `role="img"` + `aria-label="Ontology concept and relationship graph"`. The `.graph-legend`/`.graph-legend-item`/`.graph-legend-swatch--selected|unselected|edge` (CDD-062 §13) legend is non-color-dependent (border width/style, not color alone) and used **only** by this component (grep-confirmed, no other consumer).

No OQI/DQ/trust annotation exists on any ontology node today — reconfirmed; CDD-081's rejection of a fabricated reverse OQI→Ontology mapping remains correct and is not revisited.

Existing test coverage: `frontend/tests/ontology-studio.test.tsx` (337 lines, imports `StudioClient` directly, not `page.tsx`) already covers loading/error/empty states, data load, connector maturity (verbatim, never upgraded), the relationship fallback list, node selection → detail panel, the legend, `status-tag` rendering, API export, activation link, and the four "Integration pattern" (never "live integration") labels. `frontend/tests/gate-x-navigation.test.tsx` asserts only the global nav's `Ontology → /ontology/explorer` entry — unaffected by anything in this artifact. `frontend/tests/gate-x-runtime-architecture.test.tsx:112-123` asserts, via `existsSync` only (not content), that all four `ontology-studio/**/page.tsx` files continue to exist on disk — independently confirmed this is a file-existence check only, so a redirect implementation in `ontology-studio/page.tsx` (file kept, content changed) satisfies it.

## 3. Route-orphan resolution

Per CDD-081's own frozen direction ("a trivial redirect rather than creating a competing Ontology landing experience") and the reverification above: `frontend/app/ontology-studio/page.tsx` becomes a server-side `redirect("/ontology/explorer")` (Next.js `next/navigation`). The file is **not deleted** (satisfies Gate-X's existence check); its content changes from rendering `<StudioClient />` to a one-line redirect. This resolves the only genuinely orphaned route by canonicalizing it onto the already-linked, identical experience — no competing "Ontology" vs. "Ontology Studio" top-level concept is created.

## 4. Product mental-model boundary (reaffirmed, not re-litigated)

Ontology owns UNDERSTAND ("what does the enterprise know, how is it connected"); OQI owns EVALUATE/REASON/GOVERN/IMPROVE/TRUST ("can I rely on it"). This artifact does not import, reference, or duplicate any OQI concept, count, or state into the Ontology surface.

## 5. UX decisions (exact)

1. **Orientation region** (`StudioOverview`) migrates from a light `.panel` to the frozen, rationed `.obs-intelligence-surface` (CDD-078 §3) — the same dark-canvas treatment already used for Overview's hero/spotlight — extending its real, designed use to a second, genuinely orientation-shaped surface. Eyebrow text changes from "Ontology Studio" to "Ontology" (matching the actual canonical nav label; no test asserts the old string). Every currently-rendered real field (`ontology.name`, `.description`, `.ontology_id`, `.version`, `.status`, concept/relationship counts, quality score %, connector count, activation applications) is preserved verbatim — presentation-only re-styling to dark-canvas-appropriate tokens (`--obs-text-primary`/`--obs-text-secondary`/`--obs-text-muted`), no field added or removed. `ontology_id` gets the existing `.mono` demotion class (machine-identifier-first-if-truthful-label-exists policy) — same treatment as, not identical wording to, prior WOW phases' machine-ID demotion.
2. **Knowledge graph region** (`OntologyGraph`) — the outer `<section>` and legend remain the existing light `.panel` (the established two-surface contract is not altered), but the graph **canvas** itself (the ReactFlow container div) gets a dark, Observatory-native background, giving the flagship visual genuine depth without a wholesale page-level dark-mode flip. Node selection border changes from `--accent-strong` (teal) to `--obs-intelligence` (cyan) — matching the app-wide "cyan = selection/intelligence" semantic (CDD-079 §6) instead of a legacy pre-Observatory accent; the legend's matching `--selected` swatch token is updated identically so the legend stays truthful to what the graph actually shows. Edge stroke moves from `--muted` to `--obs-border-strong`, a token semantically designed for structural connector lines. Every exact governed string ("Selected concept", "Unselected concept", "Governed relationship", the accessible fallback line format, `role="img"`/`aria-label`, `.status-tag` class on lifecycle/governance values) is preserved verbatim.
3. **Context/inspection region** (the existing per-node detail panel inside `OntologyGraph`) — real `discovery_label` is promoted: a small `.status-tag`-style badge reading "Curated" (label→"curated") or "Auto-discovered" (label→"unknown") is added next to the selected concept's name, using only the real, already-fetched, currently-unrendered field — answering "what does Noetva actually know vs. merely visualize" truthfully. No new field is invented; no field that doesn't exist (cardinality, confidence, trust) is added.
4. **No new region, tab, or navigation item is introduced.** Global nav (9 areas) is unchanged. `JourneyIndicator`'s existing "Connect → Discover → Model → Validate → Publish → Activate" sequence (a real, distinct, already-shipped data-onboarding concept, not the WOW program's own CONNECT→UNDERSTAND→...→TRUST framing) is preserved unmodified in logic and wording — only inherits the new ambient dark-canvas text color correctly.

## 6. Explicit rejected/fabricated concepts (STOP conditions evaluated, none triggered)

- No OQI finding count, DQ badge, "at risk" node coloring, trust/confidence score, or reverse OQI→Ontology mapping is added to any node or edge — no governed backend relationship for this exists (reaffirming CDD-081).
- No cardinality field is invented (none exists in the real contract).
- No fabricated "Enterprise Knowledge Graph" marketing subtitle is added alongside the real `ontology.description` field — the real field is used as-is.
- `/ontology/modeling` vs. `/ontology-studio/ontology-modeling` duplication is recorded as an observation, not resolved — resolving it is out of this artifact's narrow scope.
- The ontology's own real `QualityScore` (structural completeness) is not renamed, reframed, or blended with OQI language anywhere.

## 7. Exact path authorization (ceiling)

**AUTHORIZED_CREATE (1):**
1. `frontend/tests/ontology-studio-redirect.test.tsx` — regression proving the bare `/ontology-studio` index redirects to `/ontology/explorer`, the file still exists, and no other route/behavior changes.

**AUTHORIZED_MODIFY (4 unconditional):**
2. `frontend/app/ontology-studio/page.tsx` — replace `<StudioClient />` render with `redirect("/ontology/explorer")`.
3. `frontend/app/ontology-studio/_components/studio-overview.tsx` — visual migration to `.obs-intelligence-surface`, per §5.1.
4. `frontend/app/ontology-studio/_components/ontology-graph.tsx` — canvas/selection/edge visual migration and `discovery_label` promotion, per §5.2–5.3.
5. `frontend/app/globals.css` — additive Observatory-scoped CSS only (new `.obs-ontology-*` classes, one token-value change to the existing `.graph-legend-swatch--selected` rule); no existing token renamed/reassigned.

**AUTHORIZED_MODIFY (1 conditional, verify need before touching):**
6. `frontend/tests/ontology-studio.test.tsx` — add coverage for `discovery_label` rendering and the updated selection border token; touch only if the visual migration changes any currently-passing assertion (expected: no, since all exact text/roles/classes are preserved — verify, don't assume).

**FORBIDDEN (explicit):** any file under `frontend/app/quality/`, any backend file, `frontend/components/site-shell.tsx` (no nav change), `frontend/app/ontology/explorer/page.tsx` / `frontend/app/ontology/modeling/page.tsx` (thin wrappers, unchanged), `frontend/app/ontology-studio/_components/{connector-catalog-panel,quality-panel,api-export-panel,activation-card,*-link-card}.tsx` (out of the three-region scope), any second graph/visualization library, `frontend/tests/gate-x-*.test.tsx` (unless independently verified necessary — not expected).

```
CREATE = 1
MODIFY ≤ 5 (1 conditional)
DELETE = 0
TOTAL ≤ 6
```

## 8. Test/verification requirements

Full frontend suite, `tsc --noEmit`, `eslint --max-warnings=0`, `prettier --check .`, `next build`, Gate-X (honesty/navigation/runtime-architecture), Docker build with the complete governed build-arg set (including `NEXT_PUBLIC_OIDC_API_RESOURCE_URI`), pre-deploy image inspection for the intended Ontology markers, zero backend/infra diff, zero OQI diff, zero Overview/Home diff, frozen governance hashes unchanged.

## 9. Responsive/accessibility acceptance

1440/1024/390px verified structurally (no horizontal clipping, graph canvas maintains a sane minimum height, legend and accessible fallback list remain present and readable at all widths); keyboard/focus and the existing non-color-dependent legend/`role="img"`/`aria-label`/accessible fallback list are preserved exactly, not re-implemented.

## 10. Rollback

Prior Azure revision (`--0000017`) retained at 0% traffic. No infrastructure, Entra, PostgreSQL, Key Vault, Cloudflare, or demo-data mutation authorized or expected.

## 11. Known OQI follow-up (recorded, not actioned here)

Per operator review of WOW-I3-A: Business Impact "HIGH" lacks visible rationale; Ontology Impact may lack sufficient human meaning; Reliance rationale could be more prominent; Agent Investigation NOT_INVOKED is truthful but minimally actionable; Remediation empty state under-explains lifecycle position. Recorded as **OQI EXPLAINABILITY + ACTIONABILITY FOLLOW-UP**, deferred to a separately governed phase after the current WOW boundary closes. Not touched in WOW-I3-B.

---

No STOP condition fired. Safe to proceed to implementation exactly as authorized above.
