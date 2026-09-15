# CDD-079 — Noetva Product Experience WOW: Governance and WOW-I1 Authorization

**Status:** FROZEN
**Originating phase:** NOETVA-PRODUCT-EXPERIENCE-WOW-G (govern + freeze only — no product UI implementation in this artifact)
**Amends:** nothing frozen. Builds directly on CDD-078 (Discovery + Resolution), unchanged and reaffirmed. Builds on the certified Azure DEV/demo baseline and hardened runbook (CDD-067–077), neither reopened.
**Scope:** binding experience architecture, design-system contract, and the exact WOW-I1 (foundation) authorization. WOW-I2/I3/I4 are named and sequenced but explicitly **not** authorized to implement by this artifact.

---

## 1. North star (frozen)

The authenticated product identity: **Noetva Intelligence Observatory**. The transition `noetva.ai → authentication → app.noetva.ai` must read as one company, one visual DNA, one conceptual language — at higher density and operational purpose (UNDERSTAND + INVESTIGATE + GOVERN + ACT WITH AUTHORITY), never a cloned marketing layout.

## 2. Mental model (frozen, as directed)

**Product mental model:** `CONNECT → UNDERSTAND → EVALUATE → REASON → GOVERN → IMPROVE → TRUST`. This is architecture/storytelling/capability-organization language — never a literal 7-item nav, never a permanent on-screen stepper, and never conflated with the OQI governed lifecycle.

**Note on CDD-078's flagged discrepancy:** discovery found Noetva's own internal product doc using a differently-worded model (`CONNECT→RESOLVE→UNDERSTAND→VERIFY→REASON→GOVERN→TRUST`). This governance pass adopts the model given explicitly in this phase's own governing instruction (§2 above) as authoritative for product-experience purposes going forward — the internal doc's wording may reflect earlier/different phrasing and is not itself contradicted by this decision, but for UI/architecture purposes the model in this artifact is the one that binds. If the internal doc is later found to be the intended long-term canonical wording, that is a product-documentation correction to make separately, not a reason to reopen this artifact.

**OQI governed lifecycle (frozen, kept wholly distinct):** `Detect → Evidence → Assess → Ontology Impact → Recommend/Reason → Human Authorization → Remediate → Re-evaluate → Resolve`. Describes one governed quality/remediation process, not the product as a whole. No shared visual treatment, stepper, or iconography between the two models is authorized — they must remain legible as two different concepts even when appearing near each other (e.g., a Command Center summarizing OQI lifecycle state must not visually imply it's showing the product mental model, or vice versa).

## 3. Icon library (frozen: Lucide React)

Verified before freezing, not assumed: `frontend/package.json` (`origin/main`) has no icon library today. `lucide-react@1.46.0` (npm registry, checked live) declares `peerDependencies: {"react": "^16.5.1 || ^17.0.0 || ^18.0.0 || ^19.0.0"}` — compatible with the repo's real `react: ^19.1.0`; `sideEffects: false` confirms real per-icon tree-shaking under Next's bundler. **No incompatibility found — Lucide React is authorized**, added as an exact, justified new dependency in WOW-I1 (§8 below). Rules reaffirmed: one icon family for operational UI, icons never replace required text labels, status never depends on icon shape alone, no mixing arbitrary icon libraries, no custom icons unless a genuine Noetva-specific concept has no adequate Lucide glyph (to be judged in the phase that first needs such an icon, not pre-authorized here).

## 4. Website/product continuity (frozen)

Transfers as-is (real values, from CDD-078 §3, re-affirmed): OKLCH canvas/foreground/border token family, Sora (display/page/section titles), Manrope (body/label/metadata), IBM Plex Mono (dense data/IDs/numeric), `0.5rem` base radius, the `.layer-plane`/`.cinematic-grid`/`.observatory-ring` *concepts* (rationed — intelligence surfaces only, never a default for every panel), the named motion-keyframe *concepts* re-scoped to real state changes. Explicitly excluded from the product: Instrument Serif (marketing-only editorial accent), oversized marketing display type, landing-page whitespace density, decorative storytelling sections, CTA-persuasion copy voice, marketing-only ambient animation.

## 5. Design-system architecture (frozen)

**Foundation:** semantic colors (§6), typography (§7), spacing/radius/borders/shadows, motion (§9), focus, the existing three breakpoints (1440/1024/390), density tiers (§8).
**Primitives (new/modified only where WOW-I1 needs them — see §12 for the exact authorized set; the rest are named here as the target system, not all built now):** Button, IconButton, TextField, Select, Badge, StatusIndicator, Tooltip, Divider, Skeleton.
**Composition:** Panel, Card, Metric/Signal surface, PageHeader, SectionHeader, Tabs, Breadcrumbs, DataTable shell, EmptyState, ErrorState, Drawer/Dialog where justified.
**Noetva semantic primitives:** Evidence representation, Conflict representation, Reliance representation, Authority representation, Lifecycle representation, Source/provenance representation, Ontology-relationship representation — named here as the target system; substantial implementation belongs to WOW-I3 (§20), not I1.

No primitive is authorized to be over-built in I1 beyond what §12 lists — e.g., Select/TextArea/Checkbox/Radio/Tooltip/Skeleton are named for completeness of the target system but **not** created in I1 unless a current I1-scoped surface (shell, TextField migration) genuinely needs one; none does.

## 6. Semantic token contract (frozen)

Structural: `background`, `surface`, `surface-elevated`, `surface-interactive`, `border`, `border-strong`, `text-primary`, `text-secondary`, `text-muted`. Product-semantic (bound to meaning, never a raw color name in component code): `intelligence`, `ontology`, `evidence`, `verified`, `conflict`, `attention`, `pending`, `unknown`, `deferred`, `authority`, `recommendation`, `remediation`. Exact OKLCH values are sourced from the website's real tokens (CDD-078 §3) where a direct match exists (verified/emerald, conflict/coral, attention/amber, intelligence/cyan); `ontology` and `evidence` are assigned distinct accents (cobalt and violet respectively, per CDD-078 §20) so they never collide visually; `authority` and `remediation` are each given their own token, deliberately distinct from `conflict`/`attention`, so a human-approval checkpoint never reads as an alarm state. Tokens are introduced **additively** in `globals.css` alongside the existing light-mode variables (§13) — no existing token is renamed or removed in WOW-I1.

## 7. Typography (frozen)

Display: extremely limited use (Command Center hero numeral only, deferred to WOW-I2). Page Title / Section Title / Panel Title: Sora. Body / Dense Body / Label / Metadata: Manrope. Numeric/Signal, Code/Identifier (source-record references, finding IDs, migration heads, UUIDs): IBM Plex Mono. Fonts are loaded via `next/font/google` in `frontend/app/layout.tsx` (self-hosted, zero external runtime request, zero added render-blocking network call) — not a CSS `@import`, per the performance contract's preference for native capabilities.

## 8. Information density (frozen)

Command/Overview: moderate. Investigation/OQI/Ontology: high, structured. Table/Operations: compact. Administration: compact/conventional. Mobile: progressive disclosure. No single spacing scale applied uniformly — density tiers are a real token-level distinction, not a per-page ad hoc choice.

## 9. Motion (frozen)

Semantic, restrained, state-driven only. Reuses the real website keyframe concepts (`evidence-travel`, `conflict-ripple`, `node-halo`, `signal-flow`) scoped to genuine state changes (evidence loading, new disagreement detected, graph focus, lifecycle-stage transition) — never ambient, never implying autonomous action, never a substitute for `prefers-reduced-motion` (already respected globally; this must not regress). WOW-I1 establishes the keyframe definitions and reduced-motion guard in `globals.css`; substantial application to specific interactions is owned by the phase that touches that surface (I2/I3/I4).

## 10. Status semantics (frozen — a fourth, distinct vocabulary from two pre-existing ones)

Verified precisely (not assumed) that **two other status vocabularies already exist and must not be confused with this one**: (a) `CapabilityStatus` (`frontend/components/design-system/capability-status-badge.tsx`) — five states (`SUPPORTED_NOW`, `SUPPORTED_BUT_UI_MISSING`, `AVAILABLE_BUT_DISCONNECTED`, `PLANNED`, `FUTURE_GATE`) answering "is this feature exposed in this build," already correctly non-color-dependent (color+border-style+opacity) — **preserved completely unchanged, not touched by WOW-I1**; (b) the OQI governed-lifecycle stage states (`NOT_INVOKED`, `NOT_EXERCISED`, `NOT_APPLICABLE`, `NOT_RESOLVED`, etc.) — describe one specific finding's lifecycle progress, owned by WOW-I3.

This section instead freezes a **third, new, data/finding-state vocabulary**: `VERIFIED`/`HEALTHY`, `CONFLICT`/`AT RISK`, `ATTENTION`, `PENDING`, `UNKNOWN`, `DEFERRED`, `NOT INVOKED`, `NOT EXERCISED`, `UNAVAILABLE`, `ERROR` — for describing the state of a specific piece of governed data or evidence (not "is the feature built," not "which lifecycle stage"). Realized as a **new** component, `StatusIndicator` (§12), never a modification of `capability-status-badge.tsx`. Each state: label + shape/icon + color — never color alone, matching the existing `capability-status-badge` accessibility precedent.

## 11. Three visual signatures (frozen definitions; substantial implementation owned by WOW-I3)

**Evidence Rail:** source / observed value / context / provenance / freshness-authority-where-real, laid out so agreement/disagreement is visually obvious without reading prose. Must never render a source slot the real API didn't return (CDD-078 §13's fixed-slot-layout warning stands).
**Conflict Lens:** connects conflict → evidence → affected ontology object → reliance/impact, using the `conflict` token consistently across Evidence cards, the findings triage list, and Command Center tiles — never implying unsupported causation.
**Governed Decision Gate:** the single, reused checkpoint component for every human-authority boundary, using the `authority` token (never `conflict`/`attention`), distinguishing Recommendation / Authorization / Execution / Re-evaluation / Resolution as five visually and lexically separate states, never collapsed into two.

WOW-I1 creates no signature-specific component — only the tokens (`conflict`, `authority`, `evidence`, `verified`, etc., §6) these signatures will consume later.

## 12. WOW-I1 exact authorization table

Every path below is exact — no wildcard, no directory-level authorization.

| Path | Action | Purpose | Why required in I1 |
|---|---|---|---|
| `frontend/app/globals.css` | MODIFY | Add dark-first semantic tokens (§6) additively alongside existing light tokens; add motion keyframe definitions (§9, definitions only); reference new font CSS variables (§7) | Foundation every later phase depends on; must be additive to satisfy §13's migration-safety requirement |
| `frontend/app/layout.tsx` | MODIFY | Load Sora/Manrope/IBM Plex Mono via `next/font/google`; apply font CSS variables at the root | Typography foundation (§7); native-capability font loading per performance contract |
| `frontend/components/site-shell.tsx` | MODIFY | Apply the dark Observatory shell treatment; preserve the exact 9 `primaryNavItems` labels/hrefs/order and the existing `secondaryNavItems` unchanged | Global shell contract (§15 of the governing prompt); must not break `gate-x-navigation.test.tsx`, which is not itself modified |
| `frontend/components/design-system/text-field.tsx` | CREATE | New shared `TextField` primitive: visible boundary, hover, focus, disabled, error, label association, placeholder treatment, keyboard focus, accessible contrast | Systemic fix for the invisible-input defect (§8 of the governing prompt) — the actual deliverable, not a two-line patch |
| `frontend/components/design-system/status-indicator.tsx` | CREATE | New `StatusIndicator` primitive realizing §10's data/finding-state vocabulary (label+shape/icon+color, never color alone) | Foundational shared primitive later phases (I2 Command Center, I3 OQI) require; explicitly distinct from `capability-status-badge.tsx`, which is untouched |
| `frontend/components/design-system/empty-state.tsx` | MODIFY | Extend `EmptyStateKind` additively (new kinds alongside `loading`/`empty`/`error` — e.g. `not-invoked`, `not-authorized`, `deferred`, `unavailable`) | Accessibility contract (§25 of the governing prompt) requires distinct empty states; purely additive union-type change, zero existing call sites affected |
| `frontend/app/context/_components/context-lookup.tsx` | MODIFY | Migrate its 2 bare `<input>` elements to the new `TextField` primitive | Closes one of the 2 confirmed invisible-input occurrences (CDD-078 §6) |
| `frontend/app/quality/evidence-fitness/page.tsx` | MODIFY | Migrate its 2 bare `<input>` elements to the new `TextField` primitive | Closes the second of the 2 confirmed invisible-input occurrences |
| `frontend/package.json` | MODIFY | Add `lucide-react` as an exact, pinned dependency | Icon-library decision (§3) — the only new dependency authorized in I1 |
| `frontend/package-lock.json` | MODIFY | Lockfile update resulting from the above | Required consequence of the dependency addition; not a separate decision |
| `frontend/tests/text-field.test.tsx` | CREATE | Behavioral tests: renders visibly, focus/hover/disabled/error states, label association, keyboard operability | Proves the systemic fix actually closes the defect (§44 of the governing prompt) |
| `frontend/tests/status-indicator.test.tsx` | CREATE | Behavioral tests: each state renders label+icon+color, never color-only | Proves §10's accessibility requirement for the new primitive |
| `frontend/tests/site-shell.test.tsx` | MODIFY | Update assertions for the new shell's rendered structure/classes while preserving the existing nav-content assertions | Existing test (41 lines, confirmed present) must be updated to match new shell markup, not replaced |
| `frontend/tests/evidence-fitness-workspace.test.tsx` | MODIFY (only if required) | Update only if the `TextField` migration changes a selector this existing test depends on (e.g. a query keyed to the old bare-input markup) | Precautionary — verify first; do not modify if the existing test already queries by label/role in a way unaffected by the primitive swap |

**Explicitly NOT authorized in WOW-I1** (reserved for later phases per §15–§21 of the governing prompt): Command Center/Overview redesign, OQI finding-detail redesign, Ontology graph/route-consolidation work, Supply-Chain Impact redesign, Data/Integrations/Governance/Administration redesign, `capability-status-badge.tsx` (untouched — different concern, §10), any second graph engine, any animation/chart/state library, any CSS framework change.

**Not authorized to be touched at all:** `frontend/tests/gate-x-navigation.test.tsx` (must continue passing unmodified — proves I1 didn't rename/remove a capability), backend, Bicep, Docker, tests outside the frontend tree, any CDD file.

## 13. CREATE/MODIFY/DELETE counts

CREATE = 4 (`text-field.tsx`, `status-indicator.tsx`, `text-field.test.tsx`, `status-indicator.test.tsx`). MODIFY = 9, with one (`evidence-fitness-workspace.test.tsx`) conditional on actual need, verified before touching — ceiling MODIFY ≤ 9. DELETE = 0. TOTAL ≤ 13.

## 14. Global CSS migration safety (frozen requirement)

WOW-I1 must not replace `globals.css` wholesale. Required: every existing selector inventoried before editing; existing light-mode tokens preserved (not removed) until every consumer is migrated in later phases; new dark tokens introduced under a scoping mechanism that does not silently repaint every existing page (e.g., new tokens defined but the dark theme applied only via the shell/new primitives until each page is individually migrated in I2–I4 — never a single flag-day variable rename); `.form-grid`'s existing contract preserved exactly as-is (the new `TextField` is an addition, not a replacement of `.form-grid`); no accidental Preflight-related regression introduced for any page not touched by this phase's exact path list.

## 15. Ontology route decision (frozen — decision only, no deletion in G or I1)

Read-only analysis performed (not assumed): `frontend/app/ontology-studio/` is a **shared component/workspace library** (`_components/`, `lib/ontology-studio/api-client.ts`) that real, canonical, nav-linked pages import from — `/ontology/explorer` imports `StudioClient`, `/ontology/modeling` imports `OntologyModelingWorkspace`, `/data/entity-resolution` imports `EntityResolutionWorkspace`, `/intelligence/ask-ctec` imports `AskCtecWorkspace`, `/data` and `/integrations` both import `ConnectorCatalogPanel` — all from `ontology-studio/**`. This is correct, intentional shared-code architecture, not duplication to fix.

**However:** `frontend/app/ontology-studio/page.tsx`, `ontology-studio/ask/page.tsx`, `ontology-studio/entity-resolution/page.tsx`, and `ontology-studio/ontology-modeling/page.tsx` are themselves real, directly-navigable Next.js routes (confirmed via `git grep` across the entire `app/`/`components/` tree: zero in-app links or nav entries point to any of these four URLs). **Decision: these four `page.tsx` routes are orphaned — reachable only by typing the URL directly, serving no purpose distinct from the canonical, linked pages that already import the same underlying components.** Canonical, user-facing IA is confirmed as: `/ontology/explorer`, `/ontology/modeling`, `/data/entity-resolution`, `/intelligence/ask-ctec`. Resolution of the four orphaned routes (redirect to canonical, or removal) is **not authorized in this artifact or in WOW-I1** — it belongs to WOW-I3, the phase that owns Ontology, per the governing prompt's own instruction not to perform route deletion in G.

## 16. Command Center / OQI / Ontology / Supply-Chain Impact ownership (frozen, reaffirmed)

Command Center: WOW-I2 owns substantial transformation; I1 delivers only shell/token foundation. OQI: WOW-I3 owns substantial transformation (finding-detail workspace consolidation, Evidence Rail, Conflict Lens); certified lifecycle truth (§18 of the governing prompt) must be reflected exactly — no stage rendered as complete when the real backend state is `NOT_INVOKED`/`NOT_EXERCISED`/`NOT_APPLICABLE`/`NOT_RESOLVED`. Ontology: WOW-I3 owns substantial transformation and the route-duplication resolution (§15); `reactflow` remains the graph engine, `cytoscape` remains deferred/unused, consistent with CDD-078. Supply-Chain Impact: WOW-I4 owns substantial transformation; **no new top-level nav item** — improve discoverability via in-page cross-navigation from Intelligence/Supplier Risk context, never a 10th primary nav entry.

## 17. I4 pre-authorization requirement (frozen)

Before WOW-I4 is authorized to implement, a targeted read-only surface-depth verification of Data, Integrations, Governance, Administration, Context, Evidence Fitness, and remaining Intelligence surfaces must be performed — narrower than a new DR program, but real verification, not an assumption carried over from CDD-078's admittedly incomplete pass. This does not block WOW-I1, WOW-I2, or WOW-I3.

## 18. Integrations truth (frozen)

`GENERIC CONNECTOR CAPABILITY ≠ CONNECTED VENDOR ≠ VENDOR CERTIFICATION`. Future Integrations work (WOW-I4) must distinguish available-architecture / configured / connected / healthy / degraded / unavailable / deferred only where backed by real state — reusing the new `StatusIndicator` primitive (§10/§12), never a fabricated "Connected ✓" vendor tile.

## 19. Governance / Administration (frozen)

Governance: authority, policy, stewardship, decision rights, auditability, approval — operational, not a settings graveyard. Administration: clarity, density, predictability, configuration efficiency — deliberately not cinematic. This contrast is itself a frozen design decision, both owned by WOW-I4.

## 20. Accessibility contract (frozen)

Visible focus, full keyboard operation, semantic labels, accessible contrast, color-independent state (label+shape+color, never color alone — §10), reduced motion respected (already global, must not regress), proper input affordance, semantic heading hierarchy, accessible loading/error states. The invisible bare-input defect is closed in WOW-I1 (§12). Existing `axe-core`/`vitest-axe` dev dependencies (confirmed present) are the verification mechanism — extended, not replaced.

## 21. Performance contract (frozen)

No large decorative JS dependency beyond the one authorized addition (`lucide-react`, tree-shakeable, confirmed `sideEffects: false`). No new animation/chart/graph-engine library. Fonts via `next/font/google` (self-hosted, no added external request). Prefer CSS/native capabilities for motion (§9) over a JS animation library. Any dependency beyond `lucide-react` requires its own separate justification in whichever phase proposes it — none is pre-authorized here.

## 22. Responsive contract (frozen)

Preserve 1440/1024/390 as the governed viewport baseline. Desktop: full intelligence workspace. Laptop/tablet: reflowed. Mobile: progressive disclosure — dense Ontology/OQI surfaces are not required to reproduce desktop geometry literally on mobile, only to remain understandable and navigable.

## 23. Real-data contract (frozen)

No hardcoded decorative intelligence, fake metrics, fake graph nodes, fake findings, fake recommendations, fake evidence, fake agents, fake activity, fake approvals, fake impact — in WOW-I1 or any later phase. Representative seeded demo data (already real, Azure-verified this program) remains permitted when clearly identified as such.

## 24. Four implementation phases (frozen, reaffirmed from CDD-078, no collapse found necessary)

**WOW-I1** — Foundation + design system + global shell (this artifact's exact authorization, §12). **WOW-I2** — Enterprise Understanding Command Center. **WOW-I3** — OQI + Ontology signature experiences (including the route-duplication resolution, §15). **WOW-I4** — Remaining product surfaces + product-wide consistency (preceded by the §17 depth-verification requirement). No material architectural contradiction was found during this governance pass that would justify collapsing or expanding this boundary set.

## 25. Azure iteration contract (frozen)

For every implementation phase: implement → source tests → production build → Docker/preservation check → deploy to Azure DEV → real operator inspection at `https://app.noetva.ai` → targeted refinement if required → real-browser VM → merge. No phase may declare visual success from source/tests alone; Azure is the real visual acceptance environment, exactly as already established by the Azure closure program.

## 26. WOW-I1 Azure visual check (frozen, deferred to I1's own VM)

After WOW-I1 deployment, minimum operator verification: brand-consistent login transition, global shell renders, all 9 nav areas present with correct active-state, new typography visible, dark surfaces render with adequate contrast, the Context and Evidence Fitness inputs are now visibly usable, 1440/1024/390 all render without break, no legacy page becomes unreadable, no graph/table contrast regression, no loading/error-state regression. Command Center and OQI are explicitly **not** required to look transformed after I1.

## 27. Regression contract (frozen, reaffirmed)

Every implementation phase must preserve: authentication, authorization, business-tenant isolation, CORS, the Azure custom domain, OQI semantics, remediation authority, resolution gating, connector truth, supply-chain policy semantics, local Docker/Keycloak mode, frontend tests, backend contracts. WOW is a presentation/experience program — it must never silently change domain semantics.

## 28. Current Azure limitations (preserved, not reopened)

Azure: DEV/demo baseline, not customer-production certification. Lifecycle: proven in source only, not live-verified. Deployment: manually reproducible, not fully CI/CD-automated. GitHub OIDC/R14: deferred/optional. Key Vault `publicNetworkAccess: Enabled`: accepted DEV-tier posture. None of these are altered, revisited, or "fixed" by WOW.

## 29. Truth-contract preservation (frozen, reaffirmed in full)

Every distinction listed in the governing prompt (Implemented≠planned through Vision≠roadmap commitment, plus relationship≠causation through successful remediation≠resolution) is preserved by every decision in this artifact — no section above claims a capability the real, source-verified evidence doesn't support.

## 30. Governance validation

Diff confirmed limited to `docs/cdd/CDD-079-*.md` (this artifact) only — no frontend/backend/infra source touched by this governance phase itself. CDD-078 re-hashed and confirmed byte-identical (§ below). No Azure mutation. No dependency actually added yet (the `lucide-react` addition is *authorized*, to be performed in WOW-I1's own implementation phase, not this one).

## 31. STOP conditions evaluated

No material governance blocker found. Lucide React's compatibility was independently verified, not assumed. The ontology route situation was independently analyzed via real `git grep` link-graph evidence, not guessed — its resolution is correctly deferred to WOW-I3, not left unresolved. The I1 authorization table above is exact, path-by-path, with zero wildcard entries and DELETE=0.

**No STOP condition is triggered. This governance artifact is authorized to freeze.**
