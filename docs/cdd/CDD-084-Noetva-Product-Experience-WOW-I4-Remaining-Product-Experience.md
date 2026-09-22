# CDD-084 — Noetva Product Experience WOW-I4: Remaining Product Experience (Discovery + I4-A Authorization)

**Status:** FROZEN
**Originating phase:** NOETVA-PRODUCT-EXPERIENCE-WOW-I4-DRG (Discover → Resolve → Govern; implementation not begun by this artifact)
**Amends:** nothing frozen in place. Complements CDD-033 (Enterprise UX IA + the separate Gate-X Artifact-Authorization-Gate-X-Runtime-Architecture-Findings-Route-Correction), CDD-078/079/080 (WOW foundation, I1, I2), CDD-081/082 (WOW-I3-A OQI), CDD-083 (WOW-I3-B Ontology). WOW-I3-A and WOW-I3-B remain PASS + MERGED + CLOSED and are **not reopened**.

**Scope of this artifact:** complete discovery of the remaining authenticated product surfaces, a full route×capability×experience matrix, a complete legacy-brand audit, a root-page architectural decision, and **explicit implementation authorization for exactly the first bounded slice ("I4-A": global Noetva branding correction + root-page wordmark restructure)**. All other identified work ("I4-B" and beyond) is recorded but **NOT authorized** by this artifact and requires its own future governance freeze.

---

## 1. Purpose

Complete discovery for the remaining Noetva product surfaces outside the already-accepted OQI (WOW-I3-A) and Ontology (WOW-I3-B) experiences, per the North Star: the authenticated `app.noetva.ai` experience must feel like the operational counterpart of the Noetva public site — precise, technical, calm, premium, evidence-centric — never a marketing site, and never branded as the legacy product name "CTEC."

## 2. Authoritative main

`0e2223d26697b53d84478780b814102c2bb571cb` (post WOW-I3-B merge, commit `0e2223d`) — confirmed via local fetch, `git ls-remote`, and the GitHub API during the WOW-I3-B-VM phase immediately preceding this one, and re-confirmed unchanged at the start of this discovery phase.

## 3. Predecessor governance, re-hashed and confirmed byte-identical

| Artifact | SHA-256 |
|---|---|
| CDD-033 (Artifact-Authorization-Gate-X-Runtime-Architecture-Findings-Route-Correction) | `61576536c7a6336bc0e410b0e05575204c31d4d8b628c85491ce43b9c820d735` |
| CDD-078 | `5492ef570b0e9cf3e509eb25a220f944a74cb4824b236d7f101693e3d85ae15c` |
| CDD-079 | `cb9792da6f6307a0d68d8e5c70ac92edb0f62337ddbf997b9082f19169fa7401` |
| CDD-080 | `81e26e5710620448765f1f30e21ec01799eec532fa02ff4e6190006782dcb1a4` |
| CDD-081 | `549cc792d0e30e6aafe459de537f1ff34aada0f3886ccdfdec9d69ced411ce2f` |
| CDD-082 | `815e18d4609c28e070824bab6d606991959abadc92f7aee34e1fc4842bf3eeb2` |
| CDD-083 | `aa49a1f1e7d2a1e20239db2fec313ee79a2a5d9b2fbd17201e8ae7d095ef2d32` |

## 4. Route inventory (complete, as built)

Confirmed via `next build` route output plus `frontend/components/site-shell.tsx` nav wiring. The 9 canonical primary-nav domains (frozen by CDD-033 §8, re-verified unchanged by `frontend/tests/gate-x-navigation.test.tsx`): Overview, Data, Ontology, Context, Quality, Intelligence, Integrations, Governance, Administration.

| Route | Nav grouping |
|---|---|
| `/overview` | Primary — Overview |
| `/data`, `/data/entity-resolution` | Primary — Data |
| `/ontology/explorer`, `/ontology/modeling`, `/ontology-studio` (+ `ask`, `entity-resolution`, `ontology-modeling`) | Primary — Ontology (WOW-I3-B, accepted/closed) |
| `/context` | Primary — Context |
| `/quality`, `/quality/evidence-fitness`, `/quality/findings`, `/quality/findings/[findingId]` | Primary — Quality (WOW-I3-A, accepted/closed) |
| `/intelligence`, `/intelligence/ask-ctec`, `/intelligence/decisions`, `/intelligence/supplier-risk` | Primary — Intelligence |
| `/integrations` | Primary — Integrations |
| `/governance` | Primary — Governance |
| `/administration` | Primary — Administration |
| `/`, `/about`, `/architecture`, `/dataset`, `/prototype` | Secondary utility nav (CDD-033 §5 item 1, preserved as-is — not a canonical domain) |
| `/simulation` | Reachable only as an `AVAILABLE_BUT_DISCONNECTED` card from `/intelligence` |
| `/supplier-risk`, `/supplier-risk/new`, `/supplier-risk/executions/[id]`, `.../attempts/[id]` | Reachable from `/intelligence/supplier-risk` and Ontology's `ActivationCard` |
| `/supply-chain-impact` | Reachable from `/intelligence/supplier-risk` |
| `/demo/supplier-risk` | Reachable only from the legacy Home CTA, `/prototype`, `/dataset` — **not linked from any of the 9 canonical areas** |
| `/auth/callback` | System (auth redirect target) |
| `/health` | System (API route, unauthenticated liveness) |

No 10th nav domain, no removed/renamed/reordered domain — CDD-033's contract is unmodified and unmodified by this artifact.

## 5. Route × capability × experience matrix (summary; full per-route detail held in discovery notes)

Classification key: **A** Strong/Preserve · **B** Polish · **C** Material UX hardening · **D** Legacy/migrate · **E** Duplicate/resolve · **F** Orphaned/investigate · **G** Defer.

| Route | Real vs demo data | Classification | Note |
|---|---|---|---|
| `/overview` | Real (live `Promise.allSettled` across OQI/supplier-risk/entity-resolution/ontology-modeling/connectors) | **A** | Exemplary no-fabrication discipline; one branding fix only |
| `/data` | Real (`ontologyApi.getConnectors()`) | **B** | Thin but coherent |
| `/data/entity-resolution` | Real | **E** | Same component as `/ontology-studio/entity-resolution` (pre-existing pattern, see §7) |
| `/context` | Real (`contextApi.resolve()`) | **B** | No idle-state example/guidance copy |
| `/intelligence` | N/A (static launcher) | **C** | 4 undifferentiated cards, no description copy — real comprehension gap |
| `/intelligence/ask-ctec` | Real, 401-aware | **E** + branding | Same component as `/ontology-studio/ask`; heaviest single-component CTEC concentration (7 occurrences) |
| `/intelligence/decisions` | Real | **A** | Honest, explicitly documented as frontend-only aggregation |
| `/intelligence/supplier-risk` | N/A (link-through) | **B** | Bare heading instead of `PageHeader`; one branding line |
| `/integrations` | Real (`ontologyApi.getConnectors()`, same data as `/data`) | **B** | No maturity-tier legend; triplicated data source (see §7) |
| `/governance` | N/A (static links) | **B** | Exemplary honesty (zero decorative approval controls, matches frozen Gate-X honesty test); one branding fix |
| `/administration` | Real (`/health` liveness only) | **G** | Thinness is *correct* given zero real backend user/tenant/role capability exists yet — building more UI would fabricate capability; branding fix only |
| `/simulation` | N/A (documentation-only, deliberate) | **A** | Exemplary anti-fabrication discipline; one branding fix |
| `/supplier-risk` + children | Real (live backend) | **A/B** | Correctly wrapped tables, coherent; one page-title branding fix |
| `/supply-chain-impact` | Real (live Gate F API, 3 fixed seeded scenarios per CDD-016 §6 — by design, not a defect) | **C** (branding only) | Heaviest branding concentration: "CTEC recommendation" is the literal section label over every recommendation shown; "CTEC recommends. A human decides." is the core governance statement |
| `/demo/supplier-risk` | Pure frontend-scripted, zero backend calls | **F** | Unlinked from canonical nav; narratively overlaps the now-real `/supplier-risk` + `/supply-chain-impact`; fate unresolved (see §9) |
| `/`, `/about`, `/architecture`, `/dataset`, `/prototype` | N/A (static) | **D** | Legacy pre-Observatory cluster; see §8 root-page decision |

## 6. Legacy "CTEC" brand audit (complete)

**USER-VISIBLE — MUST MIGRATE** (~30 occurrences, ~21 non-test files): `frontend/app/layout.tsx` (meta description), the 4 `_components/home/*` sections, `about/page.tsx`, `administration/page.tsx`, `governance/page.tsx`, `integrations/page.tsx`, `intelligence/page.tsx` ("Ask CTEC" card name), `intelligence/supplier-risk/page.tsx`, `simulation/page.tsx`, `supplier-risk/new/page.tsx` (page `<title>`), `ontology-studio/_components/ask-ctec-link-card.tsx`, `ontology-studio/ask/_components/ask-ctec-workspace.tsx` (7 occurrences — h1, `aria-label`, button/error copy — rendered at both `/intelligence/ask-ctec` and `/ontology-studio/ask`), `overview/_components/overview-cards.tsx` ("Ask CTEC" card), `quality/findings/[findingId]/_components/report-execution-dialog.tsx` (one line, text-only, inside an otherwise-protected surface — see §12), `supply-chain-impact/_components/human-authority-banner.tsx`, `supply-chain-impact/_components/recommendation-panel.tsx` (`aria-label` ×2 + eyebrow ×2 + body ×2), `supply-chain-impact/page.tsx`, `components/supplier-risk/assessment-form.tsx`.

**TECHNICAL INTERNAL — SAFE TO RETAIN (not migrated by I4-A):** `lib/auth/browser-session.ts` (`ctec-auth-lifecycle` channel name, `ctec-auth-bounded-renewal` key), `app/auth/callback/page.tsx` (`ctec-auth-callback-consumed-` prefix), scattered code comments.

**BUILD/DEPLOYMENT CONTRACT — FORBIDDEN to rename in I4:** `NEXT_PUBLIC_CTEC_API_ORIGIN` — the literal env var / Docker build-arg name used in every `az acr build` invocation and Dockerfile across this entire session; renaming has real CI/CD blast radius outside I4's frontend-content scope.

**API CONTRACT — FORBIDDEN, backend-owned, out of I4 scope entirely:** the `ctec:` JSON-LD namespace prefix (`backend/app/api/ontology/router.py`) and `urn:ctec:oqi:*` UUID5 namespace seeds (~9 backend OQI domain files) — the frontend only echoes these verbatim (already truthful pass-through); changing them frontend-side would misrepresent the real backend response, and changing them backend-side is out of scope for a frontend product-experience phase.

**HISTORICAL/GOVERNANCE — untouched:** all `docs/cdd/**` prose (including this artifact's own predecessor citations of "CTEC").

**TEST FIXTURE files referencing "CTEC"** (enumerated, exact set — grep-confirmed): `frontend/tests/about-page.test.tsx`, `ask-ctec-workspace.test.tsx`, `auth-callback-diagnostics.test.tsx`, `browser-session-signout.test.ts`, `browser-session.test.ts`, `gate-x-honesty.test.tsx`, `health-route.test.ts`, `ontology-studio.test.tsx`, `oqi-remediation-actions.test.tsx`, `supply-chain-impact-workspace.test.tsx`. Not all of these assert rendered text (several reference the technical-internal channel name or the `NEXT_PUBLIC_CTEC_API_ORIGIN` env var, which are not migrated) — see §11 for the conditional authorization.

## 7. Duplicate/overlap findings (recorded, not resolved by I4-A)

- `/data/entity-resolution` and `/ontology-studio/entity-resolution` render the identical `EntityResolutionWorkspace` component at two URLs.
- `/intelligence/ask-ctec` and `/ontology-studio/ask` render the identical `AskCtecWorkspace` component at two URLs.
- The connector catalog (`ConnectorCatalogPanel` + `ontologyApi.getConnectors()`) renders independently at three separate top-level locations (`/data`, `/integrations`, and inside Ontology's `StudioClient`) with no cross-reference between them.
- `/ontology/modeling` vs `/ontology-studio/ontology-modeling` remains recorded (CDD-083 §6) and is **not** revisited here.

These are the same class of problem CDD-083 explicitly declined to resolve for the ontology-modeling pair ("recorded as an observation... out of this artifact's narrow scope"). Applying the same discipline: **recorded, not resolved by I4-A.** Resolving any of these requires a canonical-URL decision that is a genuine "route ownership is ambiguous" STOP condition per the governing prompt — deferred to I4-B or later, pending explicit product direction.

## 8. Root-page (`/`) diagnosis and resolution

**What `/` currently is:** a 6-section, pre-Observatory, zero-`--obs-*`-token marketing landing page (`Hero`, `Journey`, `SupplierRiskExample`, `Capabilities`, `Explainability`, `Cta`), backed by a real, currently-passing 8-test suite (`frontend/tests/home-page.test.tsx`) tied to its exact copy.

**Reachability (not orphaned):** two live inbound links — (1) the header brand wordmark (`site-shell.tsx:74`, `<Link className="observatory-wordmark" href="/">`) present on **every authenticated page**, and (2) an explicit `{ label: "Home", href: "/" }` entry in `secondaryNavItems`, itself frozen verbatim by CDD-033 §5 item 1 ("Preserved exactly... not part of the Gate X domain grouping").

**The defect:** the header wordmark — the universal, always-available "return to my base" gesture in every enterprise SaaS product — currently returns the authenticated user to marketing copy, not to their operational home (`/overview`). This directly contradicts this artifact's own North Star ("the authenticated application must NOT look like a marketing website") at the single most-used navigation affordance in the entire product.

**Resolution (RESTRUCTURE, evidence-backed):** repoint the header wordmark's `href` from `/` to `/overview`. Retain `/` itself unchanged in reachability and structure — it remains reachable via the CDD-033-frozen secondary "Home" utility link, unmodified. `/` receives **only** the same content-level branding migration as every other page in §6 (CTEC→Noetva text), **not** a visual/structural/Observatory-token redesign — that remains explicitly deferred to I4-B (§10), keeping this decision minimal and low-risk. This does not touch `secondaryNavItems`, its order, or its labels, and does not touch the 9-domain primary nav — verified safe against `frontend/tests/gate-x-navigation.test.tsx` by direct inspection (its assertions scope to `getByRole("navigation", { name: "Primary" })` only; the wordmark link is outside that landmark and is not asserted by that test at all).

## 9. Explicitly unresolved questions (recorded, blocking only I4-B, not I4-A)

1. Connector-catalog triplication (§7) — no canonical location decided.
2. `/data/entity-resolution` vs `/ontology-studio/entity-resolution`, and `/intelligence/ask-ctec` vs `/ontology-studio/ask` — no canonical-URL decision made (consistent with CDD-083 precedent).
3. `/demo/supplier-risk`'s fate — retain as a distinct narrative walkthrough, redirect into the real `/supplier-risk` + `/supply-chain-impact` pair, or remove — no product decision made; flagged because it now narratively overlaps live, backend-real workflows in a way that could confuse a viewer about what is real vs. staged.
4. Whether `/administration` should ever grow real tenant/user/role management UI — blocked entirely on real backend capability that does not yet exist; not a frontend decision.
5. Connector maturity-tier definitions (the backend's own honest tier definitions in `backend/app/domain/ontology/connector_catalog.py`) are never surfaced to the user — whether/how to add a legend is deferred.

None of these block freezing or implementing I4-A, which touches none of the files these questions concern.

## 10. I4 implementation architecture: split into I4-A (authorized here) and I4-B (deferred)

Discovery found one work item that is fully evidence-backed, has zero open product questions, is narrowly and mechanically scoped (content substitution + one link target, no structural/visual redesign), and directly addresses the highest-visibility truth/branding risk found (the flagship Supply Chain Impact demo panel literally reads "CTEC recommendation"): **the global Noetva branding correction + root-page wordmark restructure.** This is **I4-A**, authorized below.

Everything else discovered (§9's unresolved questions, Intelligence landing card depth, Context idle-state guidance, connector legend, table-wrapper CSS fixes, and any Observatory-token/design-system migration of the legacy `/`, `/about`, `/architecture`, `/dataset`, `/prototype` cluster) is **I4-B and beyond** — genuinely separate product/architecture work requiring its own discovery-informed governance freeze after I4-A ships and is operator-accepted. **Not authorized by this artifact.**

## 11. I4-A exact path authorization (ceiling)

**AUTHORIZED_CREATE (1):**
1. `frontend/tests/gate-x-brand.test.tsx` — a new, permanent regression guard (mirroring the `gate-x-runtime-architecture.test.tsx` pattern) asserting the migrated components/strings render "Noetva," never "CTEC," for the specific instances fixed below.

**AUTHORIZED_MODIFY (22, branding-text-and-one-link-target only — no structural/visual/layout change in any of these):**
2. `frontend/app/layout.tsx` (meta description)
3. `frontend/app/_components/home/hero-section.tsx`
4. `frontend/app/_components/home/supplier-risk-example.tsx`
5. `frontend/app/_components/home/capabilities-section.tsx`
6. `frontend/app/_components/home/explainability-section.tsx`
7. `frontend/app/about/page.tsx`
8. `frontend/app/administration/page.tsx`
9. `frontend/app/governance/page.tsx`
10. `frontend/app/integrations/page.tsx`
11. `frontend/app/intelligence/page.tsx` ("Ask CTEC" → "Ask Noetva" card label only)
12. `frontend/app/intelligence/supplier-risk/page.tsx`
13. `frontend/app/simulation/page.tsx`
14. `frontend/app/supplier-risk/new/page.tsx` (page `<title>` metadata only)
15. `frontend/app/ontology-studio/_components/ask-ctec-link-card.tsx` (rendered label text only — **not** the file name)
16. `frontend/app/ontology-studio/ask/_components/ask-ctec-workspace.tsx` (h1/`aria-label`/button/error copy only — **not** the file name, component name, or either route path)
17. `frontend/app/overview/_components/overview-cards.tsx` ("Ask CTEC" card label only)
18. `frontend/app/quality/findings/[findingId]/_components/report-execution-dialog.tsx` — **narrow named exception inside an otherwise-protected OQI surface**: exactly one line of copy text, zero layout/behavior/structural change. This is a content correction, not the "visual redesign" CDD-083/this artifact's §4-protection forbids.
19. `frontend/app/supply-chain-impact/_components/human-authority-banner.tsx`
20. `frontend/app/supply-chain-impact/_components/recommendation-panel.tsx` (`aria-label` + eyebrow + body copy only)
21. `frontend/app/supply-chain-impact/page.tsx`
22. `frontend/components/supplier-risk/assessment-form.tsx`
23. `frontend/components/site-shell.tsx` — **exactly one attribute**: the brand wordmark's `href` (`/` → `/overview`). The primary 9-domain nav array and `secondaryNavItems` (including their order and every label) must remain byte-identical otherwise — verify with a diff before/after.

**AUTHORIZED_MODIFY (conditional, exact enumerated set, verify need per-file before touching — do not expand without a new discovery pass):**
24. Any of: `frontend/tests/about-page.test.tsx`, `ask-ctec-workspace.test.tsx`, `gate-x-honesty.test.tsx`, `ontology-studio.test.tsx`, `oqi-remediation-actions.test.tsx`, `supply-chain-impact-workspace.test.tsx`, `home-page.test.tsx` — touched **only** where an existing assertion literally depends on now-migrated rendered CTEC text, changed to match the new truthful text. `auth-callback-diagnostics.test.tsx`, `browser-session-signout.test.ts`, `browser-session.test.ts`, `health-route.test.ts` reference only the technical-internal identifiers or the `NEXT_PUBLIC_CTEC_API_ORIGIN` env var (both explicitly not migrated, §6) and are expected to need **no** change — confirm, do not assume.

**FORBIDDEN (explicit):** any backend file; `infra/**`; renaming `NEXT_PUBLIC_CTEC_API_ORIGIN` anywhere; the `ctec:` JSON-LD prefix or `urn:ctec:oqi:*` seeds; any route-path/URL segment rename (`/intelligence/ask-ctec`, `/ontology-studio/ask`, `/ontology-studio/entity-resolution`, etc. keep their exact current paths); any component/file rename (`ask-ctec-workspace.tsx`, `AskCtecWorkspace`, etc.); the `secondaryNavItems` array or the 9-domain primary nav array in `site-shell.tsx` beyond the one wordmark `href`; any structural, layout, or Observatory-token/visual change to `/`, `/about`, `/architecture`, `/dataset`, `/prototype`; any file under `frontend/app/quality/**` other than the one narrow line authorized in item 18; any file under `frontend/app/ontology-studio/**`/`frontend/app/ontology/**` other than items 15–16; resolving any §7 duplication; touching `/demo/supplier-risk`.

```
CREATE = 1
MODIFY ≤ 22 (unconditional) + ≤ 7 (conditional, exact enumerated set)
DELETE = 0
TOTAL ≤ 30
```

## 12. Protected surfaces (reaffirmed, unchanged)

WOW-I3-A OQI and WOW-I3-B Ontology surfaces remain closed to redesign per this artifact's own governing prompt §4. The single exception is item 18 above (one line of copy inside `report-execution-dialog.tsx`) — a content-only correction, explicitly not a redesign, not a layout change, and not touching any Conflict Lens / Evidence Rail / Explainable Reliance / Agent Investigation / Remediation / Ontology graph surface.

## 13. Test/verification requirements

Full frontend suite, `tsc --noEmit`, `eslint --max-warnings=0`, `prettier --check .`, `next build`, Gate-X (honesty/navigation/runtime-architecture — the runtime-architecture allowlist will need `site-shell.tsx` reconfirmed as already-authorized, which it is per CDD-033 §5), the new `gate-x-brand.test.tsx`, Docker build with the complete governed build-arg set (`NEXT_PUBLIC_OIDC_API_RESOURCE_URI` included), pre-deploy image inspection confirming migrated strings present and zero remaining "CTEC" in the specific files touched, zero diff under `backend/`, `infra/`, and every OQI/Ontology path not explicitly authorized above.

## 14. Azure / operator acceptance requirements

Deploy to the existing Azure DEV/DEMO frontend only (no infra/Entra/Cloudflare/PostgreSQL/Key Vault/backend/demo-data mutation). Live smoke: `/`, `/overview` (confirm wordmark now lands here), `/supply-chain-impact` (confirm "Noetva recommendation" / "Noetva recommends. A human decides." render), `/intelligence`, `/ontology-studio/ask` and `/intelligence/ask-ctec` (confirm "Ask Noetva"), `/quality`, `/quality/findings`, `/ontology/explorer`, backend `/health`, protected endpoint unauthenticated → 401. Because this changes user-visible text across many surfaces, **operator visual acceptance is required before merge**, per the established "Claude changes the product, Azure proves the product, operator acceptance closes the visual decision" discipline used throughout WOW-I3.

## 15. Explicit exclusions/deferments

WOW-I4-B (all items in §9 and §10) is not authorized here. The deferred OQI Explainability + Actionability follow-up (CDD-083 §11, reaffirmed, still not actioned) remains untouched. No backend, infra, Entra, PostgreSQL, Key Vault, or Cloudflare change is authorized or expected. No new top-level navigation item is authorized. No route path is renamed.

---

No unresolved architectural question blocks the I4-A boundary authorized above. I4-B's open questions (§9) do not require resolution before I4-A implementation begins.

Safe to proceed to I4-A implementation exactly as authorized above.
