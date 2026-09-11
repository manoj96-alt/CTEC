# CDD-062 Artifact Authorization Companion — Product-Wide UX Hardening

**Status:** APPROVED ARTIFACT AUTHORIZATION
**Version:** 1.0
**Governed via:** `PRODUCT-WIDE-UX-DR` (complete, PASS WITH FINDINGS) → `PRODUCT-WIDE-UX-G` (this document,
complete) → `PRODUCT-WIDE-UX-I` (authorized by this document) → `PRODUCT-WIDE-UX-VM` — the same
discovery/governance/implementation/verification sequence precedent as `CDD-045-Artifact-Authorization-OQI-UX-Lifecycle-Closure.md`,
applied here to a product-wide presentation-hardening scope rather than a new CDD number.
**Extends:** `CDD-033-Enterprise-UX-Governed-Product-Experience.md` (nine-area IA, capability-status
taxonomy, truth firewalls), `CDD-045-Ontology-Quality-Intelligence-Flagship-Explainable-Product-Experience-Artifact-Authorization.md`
(UI Truth Table, §29), `CDD-045-Artifact-Authorization-OQI-UX-Lifecycle-Closure.md` (`RemediationCaseStatus`
8-state stepper semantics), `CDD-014-ACCESSIBILITY-AND-RESPONSIVE-DESIGN-SPECIFICATION.md` (WCAG 2.2 AA
bar). **Does not reopen, amend, or edit any of the above in place.** Zero historical frozen artifact is
modified by this document or by the implementation phase it authorizes.

**Precedent-referenced governance hashes** (SHA-256, computed against `main@c767ffa95314d2a6e06a390abbe74953d924a8ef`,
re-verified at the start of this G phase, not assumed carried over from DR):

```
220f2e41ecc641b64ee38ead504be96037a7e4ef45b6ddb61e681d1d3c600243  docs/cdd/CDD-033-Enterprise-UX-Governed-Product-Experience.md
5dd2d76a0ac46079833be69086ea4356d4907888b73d205e365ae9901de895c7  docs/cdd/CDD-033-Enterprise-UX-Governed-Product-Experience-Artifact-Authorization.md
44fd13ec08eda34f31ed2c522edbb8e8e80ded4347d48138c5be0d2b8be43e24  docs/cdd/CDD-045-Ontology-Quality-Intelligence-Flagship-Explainable-Product-Experience-Artifact-Authorization.md
3b6bcc4493eb0ee5141e0b53bd497dc1978320a407c4c9ff1c5123a93c8421bf  docs/cdd/CDD-045-Artifact-Authorization-OQI-UX-Lifecycle-Closure.md
2e2ce41f182210af1553e0a6c9bf37ac1ede6a8f4e3f7a860587a784c5663a63  docs/cdd/CDD-014-INFORMATION-ARCHITECTURE-AND-ROUTE-MAP.md (superseded for IA purposes by CDD-033; retained for historical record)
869b24c56d66bcf82f5901051d5ae1cd8789a8e6539714a2eaf62f4403824478  docs/cdd/CDD-014-ACCESSIBILITY-AND-RESPONSIVE-DESIGN-SPECIFICATION.md
81af53b0edb8e2b0f12f8b3e784df2aecd5ff2dea3b494435624b00903db30aa  docs/cdd/CDD-046-OQI-Hardening-Nine-Dimension-Architecture.md
```

If any of the above hashes differ at implementation time, STOP and re-govern before proceeding — the
implementation phase must not silently absorb a governance drift.

## 1. Scope

Product-wide presentation hardening ahead of the Noetva 2-minute showcase recording. Ten narrow,
independent, low-risk corrections (§6 below). **No product capability is added, removed, or changed.** No
backend, API, database, or dependency change. No frontend product *behavior* changes except the addition of
one pathname-aware active-nav-state computation (pure derived UI state, no data mutation).

## 2. Non-negotiable truth contract (restated, binding on the implementation phase)

`IMPLEMENTED ≠ PLANNED` · `API-ONLY ≠ UI CAPABILITY` · `AGENT RECOMMENDATION ≠ AUTHORIZATION` ·
`REMEDIATION ≠ RESOLUTION` · `GENERIC CONNECTOR CAPABILITY ≠ VENDOR CERTIFICATION` ·
`DEFERRED CAPABILITY ≠ PRODUCT CAPABILITY` · `CODE EXISTS ≠ USER-ACCESSIBLE CAPABILITY` ·
`ROUTE EXISTS ≠ PRODUCTION-PROVEN WORKFLOW` · `TEST EXISTS ≠ UI EXISTS` ·
`UI ELEMENT EXISTS ≠ BACKEND WORKFLOW EXISTS` · `CONFIGURABLE ≠ PRECONFIGURED` ·
`ARCHITECTURAL EXTENSIBILITY ≠ IMPLEMENTED INTEGRATION` · `DEMO DATA ≠ REAL ENTERPRISE DATA` ·
`DOCKER-VERIFIED ≠ AZURE-PRODUCTION-DEPLOYED` · `DESIGNED SECURITY ≠ EXTERNALLY CERTIFIED SECURITY` ·
`TECHNICAL POSSIBILITY ≠ COMMERCIAL AVAILABILITY` · `PRODUCT ARCHITECTURE ≠ CUSTOMER ADOPTION` ·
`POTENTIAL ROI ≠ PROVEN CUSTOMER ROI` · `POTENTIAL IMPACT ≠ VERIFIED CONSEQUENCE` ·
`RECOMMENDATION ≠ CERTAINTY` · `RECOMMENDATION ≠ AUTHORIZATION` ·
`REMEDIATION ATTEMPT ≠ SUCCESSFUL REMEDIATION` · `SUCCESSFUL REMEDIATION ≠ RESOLUTION`.
No touched file's copy, markup, or test may create a new violation of any distinction above.

## 3. Branding freeze

**Decision (product owner, §1.1 of the governing G prompt):** user-facing brand is **Noetva**. Internal
technical identifiers are preserved unconditionally.

**Path-by-path audit result** (every repository-wide occurrence of the literal token `CTEC` under
`frontend/`, 22 files, classified):

| Classification | Files | Disposition |
|---|---|---|
| `USER_VISIBLE_BRAND` — persistent global chrome | `frontend/app/layout.tsx` (title metadata), `frontend/components/site-shell.tsx` (header link text, footer text) | **Authorized to change, this phase** |
| `USER_VISIBLE_BRAND` — page-body copy, not persistent chrome | `frontend/app/intelligence/page.tsx`, `frontend/app/intelligence/supplier-risk/page.tsx`, `frontend/app/supply-chain-impact/page.tsx` + 2 `_components`, `frontend/app/simulation/page.tsx`, `frontend/app/about/page.tsx`, `frontend/app/ontology-studio/ask/_components/ask-ctec-workspace.tsx`, `frontend/app/ontology-studio/_components/ask-ctec-link-card.tsx`, `frontend/app/_components/home/*` (4 files), `frontend/app/integrations/page.tsx`, `frontend/app/governance/page.tsx`, `frontend/app/overview/_components/overview-cards.tsx`, `frontend/app/overview/page.tsx`, `frontend/app/supplier-risk/new/page.tsx`, `frontend/components/supplier-risk/assessment-form.tsx`, `frontend/app/quality/findings/[findingId]/_components/report-execution-dialog.tsx` | **Not authorized this phase.** Confirmed, evidenced, genuine brand-copy occurrences — explicitly deferred to a separately-scoped future pass (§9), not silently dropped. Rationale: this is qualitatively larger, more diffuse, individual-sentence-judgment work (16 files, dozens of sentences, including a named feature label "Ask CTEC") than the three-string persistent-chrome fix, and touching it now would violate the "smallest coherent change" boundary this freeze is bound by. |
| `INTERNAL_IDENTIFIER` | `frontend/app/administration/page.tsx` (`NEXT_PUBLIC_CTEC_API_ORIGIN` env var name) | **Never change** |
| `TECHNICAL_CONFIG` | any OIDC client id (`ctec-frontend`), database name (`ctec`), GitHub repository name (`manoj96-alt/CTEC`), Docker/Compose service or image identifiers | **Never change — none of these live in an authorized path anyway** |
| `HISTORICAL_GOVERNANCE` | every `docs/cdd/*.md` reference to CTEC (the product's historical/internal name throughout its own governance record) | **Never change** — rewriting governance history is explicitly prohibited |
| `TEST_EXPECTATION` | any test asserting literal "CTEC" text (none found asserting the *brand* string specifically in the two authorized files; `gate-x-*.test.tsx` assert route/label/href structure, not the brand string) | **Preserved** — re-verify at I/VM that no test breaks |

**Exact frozen replacement strings** (verbatim, for the two authorized files only):

`frontend/app/layout.tsx`:
```
title: { default: "Noetva", template: "%s · Noetva" }
```
The `description` metadata field (`"Cognitive Twin Enterprise Core"`) is explicitly **excluded** from this
authorization — it is not rendered on-screen (SEO/social-preview metadata only), and changing it is not
necessary to satisfy the MUST-FIX finding. Left untouched.

`frontend/components/site-shell.tsx`:
- Header brand link text: `CTEC` → `Noetva` (line 39 content only; the `href="/"` and styling classes are
  unchanged).
- Footer text: `CTEC · Enterprise Cognitive Operating Model prototype` → `Noetva — Governed Enterprise
  Understanding` (§4 below governs the second half of this change).
- The secondary-nav item labeled `"Prototype"` (`href="/prototype"`, line 28) is a **distinct, named utility
  route**, preserved exactly per its own existing governance (`Artifact Authorization §5 item 1`) — it is
  not touched by, and not the same string as, the footer's self-description addressed in §4.

## 4. "Prototype" wording freeze

**Decision (product owner, §1.2):** the footer must not describe Noetva as a "prototype." Frozen exact
replacement: **`Noetva — Governed Enterprise Understanding`**.

This is not an invented marketing phrase — it is quoted directly from the product's own already-articulated
positioning (the identical phrase framed the entire `PRODUCT-WIDE-UX-DR` phase's own north star). It makes
no claim of production status, customer deployment, certification, or autonomy — it is a descriptive
identity statement, squarely inside the truth contract in §2. No alternative wording considered
(`production certified`, `enterprise proven`, `customer deployed`, `AI autonomous`, `production ready`,
`generally available`) is used or implied anywhere in this authorization.

## 5. Capability status — visual freeze

**The taxonomy itself is unchanged and non-renamable**: `SUPPORTED_NOW`, `SUPPORTED_BUT_UI_MISSING`,
`AVAILABLE_BUT_DISCONNECTED`, `PLANNED`, `FUTURE_GATE` (plus the still-unbadged, still-omitted "not
supported" non-category). **All five `STATUS_LABEL` strings in
`frontend/components/design-system/capability-status-badge.tsx` remain byte-identical.** Only the
component's visual treatment changes, keyed off the already-existing `data-status` attribute (no new prop,
no new taxonomy value).

Frozen mapping — text (unchanged) + color + border-style + opacity, so no two states are distinguishable by
color alone and no state maps color to a "good/bad" judgment about a roadmap decision:

| Status | Label (unchanged) | Color token | Border style | Opacity |
|---|---|---|---|---|
| `SUPPORTED_NOW` | "Supported now" | `var(--success)` (existing) | solid | 1 |
| `SUPPORTED_BUT_UI_MISSING` | "Supported, UI pending" | `var(--attention)` (new, §6) | solid | 1 |
| `AVAILABLE_BUT_DISCONNECTED` | "Available, not yet connected" | `var(--pending)` (new, §6) | dashed | 1 |
| `PLANNED` | "Planned" | `var(--muted)` (existing) | dotted | 1 |
| `FUTURE_GATE` | "Future capability" | `var(--muted)` (existing) | dotted | 0.7 |

`--accent`/`--accent-strong` (the product's primary interactive/action color, used for buttons and links)
are deliberately **not** reused here, to avoid a badge visually implying "this is clickable" or "this is the
primary action." `--danger` is deliberately **not** used for any capability state — none of these five states
represents a failure.

## 6. Semantic token freeze

Two new CSS custom properties only, added to the existing `:root` block in `frontend/app/globals.css`:

```css
--attention: #b45309;  /* identical value already hardcoded once, in .conditions -- now named, not new */
--pending: #64748b;    /* new: a cool slate, distinct from --muted's warmer gray and --accent's teal */
```

`.conditions { border-left: 4px solid #b45309; }` is updated to `border-left: 4px solid var(--attention);`
— same rendered color, now tokenized. No other hardcoded color in `globals.css` is touched. No new design-
token architecture, no CSS framework, no component library is introduced.

## 7. Remediation stepper — visual freeze

**Preserved exactly, byte-for-byte:** the `LINEAR_STEPS` 6-state array and its order, the
`SIDE_STATE_LABEL` 2-state map, the `isRejected` composite-state check
(`case_status === "AWAITING_AUTHORITY" && authorization?.status === "REJECTED"`), the `currentIndex`/
`isPast`/`isCurrent` derivation, and every existing label string. **`RemediationCaseStatus`, backend status
transitions, authorization semantics, rejection semantics, re-evaluation semantics, and resolution semantics
are not modified in any way** — this file only ever reads `remediation.case_status`/
`remediation.authorization?.status`, exactly as today.

Visual model authorized:
- Each linear step gains a small, decorative, `aria-hidden="true"` marker (a filled circle for past/current
  steps, a hollow circle for future steps — CSS/markup only, no new dependency, no icon library) immediately
  before its existing label text. The label text itself is untouched.
- The literal `" ->"` string currently appended to each non-last step's rendered text is **removed** and
  replaced with a pure-CSS connector (a `::after` line/border between list items) — this is a genuine
  accessibility improvement (a screen reader currently reads "arrow" between every step; it will no longer
  do so) alongside the visual upgrade, not a separate, unauthorized change.
- The existing `aria-current="step"` attribute on the current step is preserved.
- `REJECTED` continues to render as its own, structurally separate `role="group"` block (as today) — never
  inserted into the linear `<ol>`, never given a step index.
- No animation. No fake/interpolated progress between real states. Presentation only; the component remains
  a pure function of `remediation.case_status`/`remediation.authorization?.status`.

## 8. Active navigation — freeze

**The nine primary navigation labels, order, and destinations in `frontend/components/site-shell.tsx` are
unchanged** — this authorization adds pathname-aware active-state styling only, via a new `usePathname()`
call (already available; `next/navigation` is an existing dependency of this Next.js app, not a new one).

Frozen matching rule: a primary nav item is active when the current pathname is an **exact match or a
path-prefix match** of its `href`. Concretely: `/quality/findings/<id>` matches `Quality`'s href `/quality`
(prefix match) and stays active; `/ontology/explorer` and any future path nested under `/ontology/` match
`Ontology`'s href `/ontology/explorer` **by the `/ontology/` prefix**, not by exact string equality (so a
governed future child route like `/ontology/modeling` also correctly activates `Ontology` — re-verified:
`/ontology/modeling` already exists as a real route today, so this is not a hypothetical case). Exactly one
primary item may be active at a time — the prefix-matching order is evaluated so that the **longest matching
href wins**, preventing two items from ever both matching the same pathname. The active item receives
`aria-current="page"`. No breadcrumb, no global search is introduced (explicitly deferred, §9).

## 9. Explicit deferrals

Out of scope for `PRODUCT-WIDE-UX-I`, not authorized, not touched:

- The 16 page-body `CTEC` brand-copy files listed in §3's second row.
- **Context outbound navigation (originally DR's UX-06).** Re-verified directly: `ContextIdentifiersProvider`
  (`frontend/lib/context/context-provider.tsx`) already captures `blueprintId`/
  `informationElementRequirementId` from a successful resolve call and is explicitly documented as
  "cross-workspace" infrastructure (CDD-033 §25/§34) — but it has **zero consumers** anywhere in the
  codebase, and the Ontology Explorer route (`studio-client.tsx`/`ontology-graph.tsx`) has **no mechanism**
  (no URL param, no prop, no identifier-based fetch) to accept an external identifier and deterministically
  select/highlight a specific entity. Per the governing G prompt's explicit instruction, this STOPS here: a
  link would necessarily drop the user on a generic, unfiltered graph with no preserved entity context — a
  misleading link. Wiring this correctly requires new Ontology Explorer behavior (accepting and resolving an
  identifier) that is itself a scoped design decision, not a same-cycle link addition. **Deferred, not
  authorized, no path touched for this item.**
- Breadcrumbs, global search.
- The duplicate `/ontology/explorer` ↔ `/ontology-studio` route (confirmed CDD-033-intentional; not changed).
- Ontology graph layout-algorithm change, on-canvas edge highlighting, new graph library, new graph data.
- A new shared Stepper framework, new component library, new CSS framework, new state-management framework.
- Any backend, API, database change. Agent activation. OQI dimension-model UI redesign. Governance or
  Administration capability expansion. Connector redesign.
- The Docker frontend healthcheck's container-internal `wget`/`HOSTNAME` binding behavior — confirmed
  pre-existing, disclosed, unrelated to product UX, out of scope.
- "Product 10482" data fabrication — re-confirmed this G phase (direct repository-wide grep, zero hits for
  `10482` or `Golden Thread` as user-facing/product strings anywhere; the one incidental match,
  `golden_thread_finding_exists`, is an unrelated internal Python variable name inside the Azure lifecycle
  demo-readiness evaluator, not OQI/frontend content). **Principle frozen: video narrative must follow
  certified product data** (`SUP-DEMO-001`/`P-DEMO-001`/`SHIP-DEMO-001`, re-confirmed present in
  `backend/app/infrastructure/persistence/demo_oqi_seeder.py`) — no seeded identifier is invented or altered
  to match an older storyboard.
- Video production, Azure deployment.

## 10. UX-14 disposition — CLOSED / NO DEFECT

Re-inspected `frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx` directly. When
the backend returns an authorization with `is_stale: true`, the panel already renders an explicit,
`role="alert"`, bold-text warning ("Stale — this authorization no longer matches the current Finding state
and cannot be used") — this is real, existing, correct, honest behavior, not a defect requiring
implementation. **CLOSED.**

One secondary, unauthorized-for-this-cycle observation, disclosed rather than silently omitted: the
`canDecide` check (`authorization.status === "PENDING"`) does not additionally check `!is_stale`, so the
Decide dialog can remain visually present alongside the staleness warning. This creates no governance
violation — `remediation-panel.tsx`'s own governing comment, re-verified, states the backend independently
re-verifies scope/tenant/state on every call regardless of frontend conditions, so a decide attempt against
a stale authorization is refused server-side regardless of button visibility. Tightening `canDecide` to also
require `!is_stale` is a legitimate, small, future polish candidate — **not authorized in this freeze.**

## 11. Raw status normalization — freeze

**Re-verified UX-12 directly.** Two distinct backend enum families render as unstyled label/value text
today, neither of which is the capability-status taxonomy:
- `ontology-graph.tsx`: `concept.lifecycle_state`, `concept.governance_status`.
- `context-lookup.tsx`: `result.coverage_status`, `result.evidence_availability_status`.

Per the governing prompt's explicit instruction, these must **not** be forced through
`CapabilityStatusBadge` (a different, unrelated taxonomy). Authorized instead: one small, new, generic CSS
class, `.status-tag`, added to `globals.css` — a neutral pill treatment (bordered, uppercase, small text,
using only existing `--line`/`--muted` tokens, no color implying success/failure/lifecycle-stage semantics
those enums don't carry) — applied by wrapping each raw value in a `<span className="status-tag">` in the
two files above. **The rendered text of every value is unchanged.** This is a visual normalization only, not
a taxonomy consolidation, exactly as instructed.

## 12. Loading-state normalization — freeze

- `frontend/app/data/page.tsx` line 61: `<p>Loading…</p>` → `<EmptyState kind="loading" title="Loading
  connector catalog" />` (new import of the existing `frontend/components/design-system/empty-state.tsx`;
  no new component created).
- `frontend/app/intelligence/decisions/page.tsx` line 41: `<p>Loading…</p>` → `<RouteState title="Loading"
  message="Loading decisions…" />`, reusing the component this exact file **already imports** for its error
  state (`frontend/components/supplier-risk/route-state.tsx`) — not `EmptyState`, since this page already
  has an established, correct pattern of its own and forcing the design-system component in here would be
  an unnecessary cross-feature-boundary change for zero additional benefit.

No new loading component is created. No other page's loading state is touched.

## 13. Ontology legend — freeze

**Static legend only**, authorized inside `frontend/app/ontology-studio/_components/ontology-graph.tsx`.
Re-verified the component directly: exactly two visual semantics currently exist in the graph and nothing
else — (a) a node's border is `2px solid var(--accent-strong)` when selected vs. `1px solid var(--line)`
otherwise, and (b) every edge is a single uniform style (`stroke: var(--muted)`) carrying its relationship
name as an inline label. The legend explains exactly these two facts and nothing invented: a small,
static key reading "Selected concept" (with a sample of the selected-node border treatment) and "Governed
relationship" (with a sample edge/line). No new semantic category, no new interaction, no layout change, no
edge highlighting, no new graph library. ReactFlow remains the frozen graph library; Cytoscape remains
unused and untouched.

## 14. Zero backend/Docker/dependency change

Re-verified directly: none of the ten corrections in this authorization requires a change to any file under
`backend/`, `infra/`, `.github/workflows/`, `keycloak/`, `docker-compose.yml`, any Dockerfile, `package.json`,
or `requirements.txt`. No dependency is added, upgraded, or removed. `frontend/lib/oqi/contracts.ts`'s
`RemediationResponse` type and every other API contract type are read-only inputs to this authorization, not
touched by it.

## 15. Exact authorized product paths (frozen)

```
CREATE (0)

MODIFY (9)
frontend/app/layout.tsx
frontend/components/site-shell.tsx
frontend/components/design-system/capability-status-badge.tsx
frontend/app/globals.css
frontend/app/quality/findings/[findingId]/_components/remediation-stepper.tsx
frontend/app/ontology-studio/_components/ontology-graph.tsx
frontend/app/context/_components/context-lookup.tsx   -- §11 (status-tag) ONLY; §9's outbound-link item is NOT authorized for this file
frontend/app/data/page.tsx
frontend/app/intelligence/decisions/page.tsx

DELETE (0)

TOTAL = 9
```

No implementation path beyond these nine may be touched. No wildcard, no directory-level authorization, no
"and related files."

## 16. Exact test authorization

**MODIFY, justified by the frozen changes above:**

```
frontend/tests/ontology-studio.test.tsx        -- extend for the new legend; assert existing graph
                                                   node-select/edge-render behavior unchanged
frontend/tests/oqi-remediation-actions.test.tsx -- extend for the new stepper markup; assert all 6 linear
                                                   + 2 side-states + the REJECTED composite still render
                                                   correctly; assert case_status/authorization.status
                                                   continue to drive rendering exclusively
```

**MUST remain semantically intact, re-verify at VM, do not weaken:**

```
frontend/tests/gate-x-navigation.test.tsx        -- exact nav label/href/order assertions
frontend/tests/gate-x-honesty.test.tsx           -- Governance/Administration/Integrations honesty assertions
frontend/tests/gate-x-runtime-architecture.test.tsx -- its AUTHORIZED_CHANGED_PATHS set already contains
    frontend/app/data/page.tsx, frontend/app/context/_components/context-lookup.tsx, and
    frontend/app/intelligence/decisions/page.tsx from a prior, unrelated phase. It does NOT contain
    frontend/app/layout.tsx, frontend/components/site-shell.tsx,
    frontend/components/design-system/capability-status-badge.tsx, frontend/app/globals.css,
    frontend/app/quality/findings/[findingId]/_components/remediation-stepper.tsx, or
    frontend/app/ontology-studio/_components/ontology-graph.tsx. Modifying those six will very likely
    reproduce the same known, already-diagnosed frozen-allowlist false positive documented throughout this
    program's history (it diffs the *working tree*, not a committed baseline, and fails by construction for
    any file outside its old allowlist until the candidate is committed to a clean checkout matching CI).
    This is an EXPECTED, PRE-DIAGNOSED symptom, not a new defect -- VM must reproduce and re-confirm this
    exact root cause, not attempt to edit this file to force it green.
```

**No new test file is authorized.** Coverage for the new `capability-status-badge.tsx` visual states,
`globals.css` tokens, `layout.tsx`/`site-shell.tsx` brand strings, active-nav behavior, and the two
loading-state swaps is expected to be added as extensions inside the two MODIFY-authorized test files above
plus manual/browser verification at VM (per §17) — if implementation determines a genuinely new test file is
unavoidable, it must STOP and return to governance rather than silently create one.

Accessibility: re-run `vitest-axe` (or the project's equivalent existing accessibility check) against every
touched component. Non-color differentiation (border-style/opacity for the badge; icon+text for the
stepper) must be verified present, not merely color.

## 17. Docker/browser VM requirements

The eventual VM phase must include, at minimum: a fresh exact-candidate worktree; frontend
format/lint/typecheck/build; the complete existing frontend regression suite (including the three
"must-remain-intact" files above, with the `gate-x-runtime-architecture.test.tsx` finding reproduced and
explained, not silently patched); the two new/extended UX test files; relevant backend regression (to prove
zero cross-layer breakage, even though no backend file is touched); a fresh Docker build and fresh Docker
runtime; and — because this authorization is entirely visual/presentational — **actual browser verification
is mandatory, not optional**, explicitly inspecting: Noetva branding (title bar and footer) with the word
"prototype" absent from the footer; active-nav-state on at least one nested route (`/quality/findings/<id>`
keeping "Quality" active); all five capability-status visual treatments side by side; the remediation
stepper across a representative sample of its states including the `REJECTED` branch; the ontology legend;
both normalized loading states; the `.status-tag` treatment in both files; and the UX-14 rendering
(confirm the staleness warning still renders correctly with the new stepper markup alongside it). No merge
on source/test evidence alone.

## 18. STOP conditions carried into implementation

Implementation must STOP and return to governance, not improvise, if: any of the nine paths in §15 cannot
achieve its frozen behavior without touching a tenth path; any change would require a backend/API/schema
change; any change would alter a label string in §5's frozen mapping or any state in §7's frozen stepper
data; the `gate-x-navigation.test.tsx`/`gate-x-honesty.test.tsx` assertions would need to change; or any new
material defect is discovered in the course of implementation. A STOP is a valid, expected result, not a
failure of process.

## 19. Governance index

No `docs/cdd/` index file exists in this repository (confirmed by direct search this phase) — none is
created or updated.
