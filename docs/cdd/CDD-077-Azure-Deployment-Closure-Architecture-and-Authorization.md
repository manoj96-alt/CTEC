# CDD-077 — Azure Deployment Closure Architecture and Authorization

**Status:** FROZEN
**Originating phase:** AZURE-DEPLOYMENT-CLOSURE-DRG (discover + resolve + govern only in this artifact)
**Amends:** nothing frozen in place. Builds on CDD-067 through CDD-076 (all reaffirmed unchanged, all real-Azure verified for their own scope). Authorizes the architecture and exact ceilings for the closure program's future implementation phases; performs zero mutation itself.
**Scope:** custom-domain binding for `app.noetva.ai`, its OIDC/CORS consequences, the DEV demo-seed tenant defect, Golden Thread readiness, GitHub deployment/OIDC disposition, and lifecycle/cost posture. Explicitly excludes global runbook hardening and Product Experience WOW (both separately deferred, §24-25).

---

## 1. Authoritative starting state

`origin/main` = `09acfeb77a258ff8a83a48a8fc4105279456f50a` (fresh fetch, matches expected). Full Azure PR stack `#213`–`#230` re-verified: all `OPEN`, `mergedAt: null`. Authoritative candidate ancestry for any further Azure work: `azure/entra-audience-r11r3-i` @ `6ef2007f1f0cbe5ee95c5f11404c5e37fd669d67` (PR #230), which itself contains the full prior chain back through CDD-067. CDD-067 through CDD-076 re-hashed at their governing commits — all ten byte-identical to previously recorded values (no drift). CDD-077 is confirmed the next unused CDD number repo-wide.

## 2. Live Azure topology (fresh, read-only)

Resource group `rg-noetva-dev` contains every expected resource: `noetvadeveus2acr`, `noetva-dev-eus2-kv`, `noetva-dev-eus2-pg`, `noetva-dev-eus2-vnet`, `noetva-dev-eus2-cae`, `noetva-dev-eus2-log`, backend/frontend Container Apps, 3 managed identities (frontend/backend/migration; a 4th, `id-cicd`, is CI/CD-scoped), db-bootstrap/migrate Jobs, an availability-suppression resource, an action group, 3 metric alerts (pg-storage sev1, pg-connections sev2, migration-job-failed sev0), and a $50/month budget.

**Backend** (`noetva-dev-eus2-backend`): image `sha256:3c7e46ac8751faaeb687a3c3bc11a85ff34a52ec9798375be9b2fa69e4a5f6bc`, single active revision `--0000005`, `Healthy`/`Provisioned`, 100% traffic, `activeRevisionsMode: Single`, `minReplicas:0`/`maxReplicas:1`. Ingress: external, FQDN `noetva-dev-eus2-backend.politeglacier-6315242f.eastus2.azurecontainerapps.io`, port 8000, `corsPolicy: null` (CORS enforced only at the FastAPI application layer via `CTEC_CORS_ORIGINS`, never at ingress). `CTEC_OIDC_AUDIENCE=3a880f13-985d-4a71-be05-20f97b9bcfa3` confirmed live (CDD-076 correction holds).

**Frontend** (`noetva-dev-eus2-frontend`): image `sha256:b4d52a9e96721ddd00cac62977f7d88ced3b17360a1b583b2ed7e1c32fa031d4`, single active revision `--0000003`, `Healthy`/`Provisioned`, `minReplicas:0`/`maxReplicas:1`, `corsPolicy: null`, **`customDomains: null`** — clean slate, no prior custom-domain attempt to reconcile.

**PostgreSQL** (`noetva-dev-eus2-pg`): `state: Ready`, `Standard_B1ms`/Burstable, PG17, 32 GiB Premium_LRS (autoGrow disabled), 7-day retention, HA disabled, **`publicNetworkAccess: Disabled`**, private via delegated subnet + private DNS zone (link `Succeeded`). Migration job: latest execution **Succeeded**; 3 earlier same-day failures are historical (already resolved in a prior phase), not a live concern.

**Key Vault** (`noetva-dev-eus2-kv`): RBAC-authorized, 6 secrets (names only, values never read): `ctec-database-url`, `ctec-migration-database-url`, `ctec-runtime-handoff-key`, `postgres-admin-password`, `postgres-app-password`, `postgres-migrate-password`. **`publicNetworkAccess: Enabled`** — flagged for the record as a pre-existing DEV-tier posture predating this phase; not evaluated for materiality here and not a closure blocker (out of this phase's discovered-defect scope; carried forward as a noted item, not silently dropped).

**Monitoring:** Log Analytics workspace healthy, 30-day retention, diagnostic setting wired to the Container Apps Environment, all 3 alerts `Enabled`, action group present.

**Lifecycle/cost automation:** a complete, real state machine already exists in source (`infra/azure/lifecycle/*`, `infra/azure/lifecycle-main.bicep` + 4 modules, 7 GitHub workflows: start/stop/status/extend/hold/nightly-sweep/restart-monitor) — confirmed genuinely calling `az postgres flexible-server stop/start` (real compute-cost avoidance, not cosmetic), with a `DemoReadinessResult` classification (`READY`/`FAILED_START`/`DEMO_DATA_NOT_READY`) directly relevant to §7 below. This exists only on the unmerged candidate branch. **Not zero-cost when dormant**: Postgres storage/backups, ACR storage, Key Vault, Log Analytics retention, VNet/private-DNS-zone, and 4 managed identities all persist and can carry small standing costs regardless of stop state — "near-zero compute cost," never "zero cost."

## 3. Authenticated DEV chain — preservation baseline

CDD-073/074/075/076's authenticated chain (Microsoft External ID → real token → correct audience/issuer/tenant/scope → backend authorization → PostgreSQL-backed processing) is reaffirmed intact by the live topology above — no redesign proposed or required. Fail-closed authentication/authorization remains invariant throughout this document; nothing in §4-§9 below touches `backend/app/api/supplier_risk/authentication.py`'s comparison logic.

## 4. Custom-domain architecture — `app.noetva.ai`

`app.noetva.ai` is a subdomain (not apex) bound to the frontend Container App. Required DNS records, per current Microsoft Learn documentation ("Custom Domain Names and Free Managed Certificates in Container Apps," fetched live):

```
CNAME  app          -> noetva-dev-eus2-frontend.politeglacier-6315242f.eastus2.azurecontainerapps.io
TXT    asuid.app    -> <customDomainVerificationId, read via `az containerapp show`>
```

No A record — that pattern is only for apex domains.

**Critical, non-negotiable constraint (direct Microsoft quote):** *"Establish a CNAME record for subdomains that maps directly to the container app's generated domain name. Mapping to an intermediate CNAME value blocks certificate issuance and renewal. Examples of CNAME values are traffic managers, Cloudflare, and similar services."* And: *"To ensure that the certificate issuance and subsequent renewals proceed successfully, all requirements must be met at all times when the managed certificate is assigned."* **The `app` CNAME must remain Cloudflare "DNS only" (grey-cloud) permanently — not just during initial validation.** Flipping proxy mode on later silently breaks the next renewal.

**CAA:** same source — *"If any CAA domain record exists on the root domain, you must explicitly allow DigiCert as a certificate issuer by creating a CAA domain record with the value `0 issue digicert.com`. Without this setting, the certificate issuance and renewal fail."* Azure's managed certificate is DigiCert-issued. Whether `noetva.ai`'s zone carries an existing CAA record is not yet verified (Cloudflare zone was not read in this DRG) — **R12-I's first step must check this before requesting the managed certificate**, and add the DigiCert permission only if a CAA record already exists (never remove an existing CAA record).

**Renewal:** fully automatic, contingent on the above holding continuously — no operator action once correctly configured.

**Apex/www:** confirmed architecturally untouched — adding `app`/`asuid.app` is purely additive; nothing here reads, modifies, or interacts with the existing `@`/`www` records for the marketing site.

## 5. `api.noetva.ai` — not authorized, not required

The application has no cookie/session-domain dependency: the access token is held only in memory (`WebStorageStateStore({ store: memoryStore() })`), attached via `Authorization: Bearer`, with `credentials: "omit"` on every fetch (confirmed, unchanged since R11). CORS-mediated cross-origin fetch to the existing Container Apps backend FQDN already works today and continues to work regardless of the frontend's hostname. A custom `api.noetva.ai` would be purely cosmetic, would double the DNS/cert/CAA surface requiring the same permanent Cloudflare-DNS-only discipline, and solves no real problem. **Not authorized by this artifact. Deferred indefinitely**, consistent with §4's own "prefer the smallest architecture" instruction.

## 6. OIDC redirect/callback impact — exact current state and required change

Live Graph read (frontend app `ee9c1b49-...`, object `ed5926b9-...`): exactly **one** `spa.redirectUris` entry (the current Azure FQDN + `/auth/callback`), one `web.logoutUrl` (bare current FQDN, no path), `web.redirectUris` empty.

Source confirms all frontend OIDC values (`NEXT_PUBLIC_OIDC_REDIRECT_URI`, `NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI`, `NEXT_PUBLIC_OIDC_AUTHORITY`, `NEXT_PUBLIC_OIDC_CLIENT_ID`, `NEXT_PUBLIC_CTEC_API_ORIGIN`, `NEXT_PUBLIC_OIDC_API_RESOURCE_URI`, `NEXT_PUBLIC_OIDC_SCOPE`) are **build-time only** (`frontend/Dockerfile` `ARG`→`ENV` in the builder stage, consumed by `next build`) — never runtime container env vars. **A hostname cutover therefore requires a new frontend image build with new `--build-arg` values, not merely a Container App env-var patch** (unlike CDD-076's backend-only correction).

No hardcoded absolute URLs exist anywhere in the frontend's auth logic (`browser-session.ts`, `auth/callback/page.tsx` — confirmed clean, all relative/env-driven via `safeReturnPath()`). The only hardcoded FQDN references anywhere in frontend source are three literal strings in `frontend/tests/browser-session.test.ts` used purely as mock config fixtures — cosmetic test-data drift if left stale, not a functional defect, not required reading for correctness.

**Required change (R12-I):** add exactly one new `spa.redirectUris` entry (`https://app.noetva.ai/auth/callback`) and update `web.logoutUrl` to the new origin. **Smallest secure configuration decision, frozen here:** retain the existing Azure Container Apps FQDN redirect URI as a documented operational fallback during the cutover window (both are Noetva-controlled, legitimate origins; removing it prematurely risks locking out in-flight testing with no compensating security benefit, since Entra's redirect-URI allowlist is exact-match, not pattern-based). Its removal is deferred to a follow-up cleanup once `app.noetva.ai` is proven stable in production use — not blocking closure, and must be tracked, not forgotten. R12-I must independently confirm via Graph schema whether `web.logoutUrl`/`postLogoutRedirectUris` accepts multiple values before deciding whether the old logout URL can also be retained in parallel.

## 7. CORS impact — exact current state and required change

`backend/app/core/config.py`: `cors_origins: list[str]` (no wildcard default). `backend/app/main.py`: standard `CORSMiddleware(allow_origins=settings.cors_origins)` — no wildcard anywhere in source. `CTEC_CORS_ORIGINS` is a JSON-array-string env var, **already supporting multiple explicit origins with zero source change** — confirmed via pydantic-settings list parsing. Live current value: `["https://noetva-dev-eus2-frontend...azurecontainerapps.io"]` (single entry). Bicep: `infra/azure/resources.bicep` param `corsOrigins` → `CTEC_OIDC_...` wait, → `CTEC_CORS_ORIGINS` (line ~253); `environments/dev/main.parameters.json` placeholder `REPLACE_WITH_DEV_FRONTEND_ORIGIN`.

**Required change (R12-I):** append `https://app.noetva.ai` to the array value — **additive, not a replacement**, for the same fallback-during-cutover reasoning as §6. No source change. No wildcard, ever.

## 8. Custom-domain IaC — currently nonexistent, must be created

`infra/azure/resources.bicep`'s `frontendHostname` parameter is **purely informational** — it flows only to an output, wired to no real resource. **Zero Bicep resources for Container Apps custom domains or managed certificates exist anywhere in `infra/azure/` today.** R12-I must add new IaC (a `customDomains`/managed-certificate binding resource under the frontend Container App, or a small dedicated module) so the eventual live binding is source-represented, not CLI-only drift — directly serving closure criterion §13(25) below.

## 9. DEV demo-seed root cause — tenant mismatch, not a missing run

`backend/app/infrastructure/persistence/demo_gate_f_seeder.py` (and five siblings: `demo_field_value_evidence_seeder.py`, `demo_ontology_copilot_seeder.py`, `demo_entity_resolution_seeder.py`, `demo_oqi_seeder.py`, `demo_semantic_mapping_seeder.py`) are all idempotent (deterministic `uuid5` IDs + existence checks), manual-CLI-only (never invoked by production bootstrap, migration, or db-bootstrap Jobs — confirmed absent from those code paths), and all hardcode/enforce a single target tenant: `BOOTSTRAP_DEMO_TENANT_ID = "ctec-demo-tenant"` (`backend/app/core/bootstrap.py`), raising `DemoTenantRequiredError` for any other value.

**The real, governed, CDD-075-frozen DEV business tenant is `noetva-dev-tenant`** — a different literal string. Given this codebase's tenant-isolation enforcement (every read/write scoped by `authenticated.tenant_id`), **even running these seeders exactly as they exist today against the real Azure Postgres would not fix visibility** — their data would live under `ctec-demo-tenant`, permanently invisible to any session authenticated as `noetva-dev-tenant`. This is the actual root cause of R11-R3's observed 404s: a tenant-literal mismatch between demo-data architecture and the real governed DEV tenant, not merely "seeder never ran." The deployment guide never mentions any seeder — this was always an undocumented manual step, never a documented-then-skipped one.

**Disposition:** the correct direction is to make the seeded data reachable under `noetva-dev-tenant` (the real, already-governed tenant) — **never** to alter the real CIAM user's tenant-extension value to match the seeder's default, which would reopen CDD-075. The exact mechanism (whether the seeders already accept a tenant override via CLI argument, or require a narrow, explicit, environment-gated source change to `DemoTenantRequiredError`'s enforcement) was **not yet confirmed** in this DRG — R13 must begin with a read-only confirmation step before any source or database mutation (§21).

## 10. Golden Thread readiness

The exact governed scenario (SAP=US / PLM=MX country-of-origin conflict, `SUP-DEMO-001`/`P-DEMO-001`/`SHIP-DEMO-001`) **is genuinely modeled** in `demo_oqi_seeder.py` — real `FieldValueEvidenceORM` rows (SAP asserting `"US"`, PLM asserting `"MX"`), a real `QualityRule` (`CROSS_SOURCE_VALUE_CONFLICT`), and a real `ComparisonSubjectCorrespondence` — but exists **only** under `ctec-demo-tenant`, subject to the identical §9 mismatch. Two sub-claims from the original narrative (a third "Supplier portal" source, and a "missing Specification" element) were **not confirmed present** in the portion of the seeder read — flagged as unconfirmed, not assumed true. Whether the five downstream capabilities (OQI findings populated, ontology impact represented, remediation-lifecycle data, deterministic agent recommendation, re-evaluation/resolution demonstrability) are truthfully exercisable was **not fully investigated** in this DRG — R13 must verify each claim individually against real APIs once the tenant mismatch is resolved, per the truth contract (§13 below): no claim in the eventual demo walkthrough may be asserted without a real, freshly-observed API result behind it.

## 11. GitHub deployment/OIDC readiness

All 8 Azure-touching workflows (`azure-deploy.yml` + 6 lifecycle workflows) use genuine OIDC/workload-identity federation (`azure/login@v2`, `client-id`/`tenant-id`/`subscription-id` only, `permissions: id-token: write`, **zero client secrets**), split across two least-privilege identities (`id-cicd` for deploy, `id-lifecycle` for lifecycle control, the latter's custom role explicitly excluding `Microsoft.Authorization/*`/ACR/Key-Vault-data-plane actions). GitHub Environments `dev`/`staging`/`demo` exist with zero protection rules. Branch protection, secret scanning, and push protection are unchanged from prior known state.

**Live reality is only half-deployed:** `id-cicd` exists live with a real federated credential matching GitHub's `dev` environment exactly — but **`id-lifecycle` was never deployed to Azure** (Bicep-only, unapplied), and **every GitHub Actions variable the workflows read is unset** (`vars.NOETVA_CICD_CLIENT_ID`, tenant/subscription IDs, ACR name, etc.) — so even `azure-deploy.yml`, despite `id-cicd` being ready, would fail at the `azure/login` step today. **Verdict: not currently reproducible end-to-end from GitHub Actions.** Manual, operator-driven `az` CLI bootstrap remains the only working deployment path.

**Disposition:** full GitHub OIDC wiring is architecturally sound and could be completed in a future phase, but is **not required for Azure closure** as defined in §13 — per this program's own closure criterion allowing "GitHub deployment path is reproducible or explicitly classified as remaining bootstrap." **Explicitly classified here as remaining bootstrap, deferred (R14, optional, not sequenced before closure).** This is a deliberate, recorded decision, not silent drift.

## 12. Product truth-contract reaffirmation

All distinctions enumerated in the governing prompt (Implemented ≠ planned, API-only ≠ UI capability, CODE EXISTS ≠ USER-ACCESSIBLE CAPABILITY, etc.) apply without exception to the eventual Golden Thread walkthrough. Concretely: no page, capability, or data point may be presented in a demo unless independently, freshly verified against a real API response in R13's own verification step — the existing pattern already established through CDD-034/CDD-066/R11's own investigations (distinguishing route-exists from UI-exists from production-proven) continues unchanged. **SIMPLIFY THE STORY, NEVER SIMPLIFY THE TRUTH.**

## 13. Final Azure closure acceptance criteria (frozen)

Closure requires all of the following, each independently verified (not assumed) at the final adversarial VM:

1. `app.noetva.ai` resolves and serves the frontend. 2. HTTPS certificate valid (Azure-managed, DigiCert). 3. `noetva.ai`/`www.noetva.ai` unaffected (diffed, not merely assumed). 4. Real External ID sign-in works from `app.noetva.ai`. 5. Callback (`/auth/callback`) works from the new origin. 6. Logout works. 7. Real access token still targets the backend correctly (`aud` unaffected by hostname change). 8. Backend audience/issuer/tenant/scope validation remains fail-closed (re-run the full CDD-076 negative suite against the new origin). 9. Browser CORS works from `app.noetva.ai` (no wildcard). 10. PostgreSQL remains private. 11. Key Vault references remain healthy. 12. Migration state current. 13. Governed demo seeds exist **under `noetva-dev-tenant`**. 14. Golden Thread is executable end-to-end with real, freshly-verified API results. 15. OQI evidence remains truthful throughout. 16. Human-authorization boundaries intact (no remediation auto-executes). 17. Remediation-attempted is never conflated with resolved. 18. Start/wake procedure works (real Postgres start + backend/frontend scale-up + health). 19. Stop/dormant procedure works (real Postgres stop). 20. Monitoring operational. 21. Real browser verification succeeds end-to-end. 22. Baseline mobile/responsive smoke (not a redesign — just "does it render usably," deferred detail to Product Experience WOW). 23. No unexpected console/network errors materially affect the workflow. 24. Image digests and revisions recorded (frontend digest **will** change at R12; backend will not). 25. All closure changes are source/IaC represented (§8) — no unexplained drift. 26. Full Docker/CI regression green. 27. GitHub deployment path explicitly classified per §11 (remaining bootstrap — acceptable, already decided).

## 14. Security invariants (unchanged, reaffirmed)

Fail-closed audience/issuer/tenant/scope validation (CDD-073–076) is untouched by every item in this artifact. No wildcard CORS, ever. No Cloudflare proxy on the `app` custom-domain record, permanently (§4). No removal of an existing CAA record. No weakening of PostgreSQL's private-only posture. No secret disclosure. No long-lived Azure credential introduced for GitHub (§11 stays OIDC-only or stays manual).

## 15. Explicit no-touch surfaces

`noetva.ai`/`www.noetva.ai` DNS records (any type). Any existing Cloudflare CAA record (only additive `digicert.com` permission if one exists). The old Azure Container Apps frontend FQDN's Entra redirect URI (retained, not removed, per §6). Backend `authentication.py`/`dependencies.py` comparison logic. The replacement CIAM user (`ec691e10-...`) and its tenant extension. The old malformed DEV user (`c1d19303-...`). Any production/prod Bicep environment file. Key Vault secret values. Database rows outside the explicit, tenant-corrected demo-seed write authorized for R13 (§21).

## 16. CREATE/MODIFY/DELETE ceiling — this DRG phase (R-Closure-G)

CREATE = 1 (`docs/cdd/CDD-077-Azure-Deployment-Closure-Architecture-and-Authorization.md`). MODIFY = 0. DELETE = 0. **Zero Azure, Cloudflare, Entra, GitHub-settings, or database mutation performed or authorized by this phase itself.**

## 17. Authorized ceiling for R12 (custom domain + OIDC + CORS)

**Repository/IaC:** MODIFY `infra/azure/resources.bicep` (add custom-domain/managed-certificate resource under the frontend Container App; correct CORS-origin parameter description if needed); CREATE ≤1 new Bicep module file only if the binding resource is cleaner as its own module (implementer's judgment, not both a sprawling inline addition and a new file); MODIFY `infra/azure/environments/dev/main.parameters.json` (frontend hostname / CORS-origin / redirect-URI-related values); MODIFY `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` narrowly (the frontend build-arg section + a new custom-domain binding section) — **not a full rewrite** (§23). Ceiling: CREATE ≤1, MODIFY ≤4.

**Azure:** `az containerapp hostname add`/bind the managed certificate for `app.noetva.ai` on `noetva-dev-eus2-frontend`; rebuild and push a new frontend image with updated `NEXT_PUBLIC_*` build args (this **will** change the frontend digest — expected, authorized); deploy the new revision; update `CTEC_OIDC_ISSUER`/audience are untouched (backend not touched for OIDC values), only `CTEC_CORS_ORIGINS` env var on the backend (additive, §7).

**Cloudflare:** ADD `CNAME app` (DNS-only) and `TXT asuid.app`; ADD `CAA 0 issue digicert.com` **only if** a CAA record already exists on the zone. No other record touched.

**Entra:** ADD one `spa.redirectUris` entry (`https://app.noetva.ai/auth/callback`); update/add `web.logoutUrl`/post-logout redirect per confirmed schema capability (§6). No other app-registration change.

**Database:** NONE.

## 18. Authorized ceiling for R13 (demo-seed tenant correction + Golden Thread verification)

**R13 Step 0 (read-only, required before any mutation):** read the exact CLI/function signature of all 6 seeders to confirm whether a tenant override already exists; read whether `DemoTenantRequiredError`'s enforcement is a hardcoded constant or an overridable guard.

**If an existing override mechanism is confirmed:** Database — run the affected seeder(s) once, manually, targeting `tenant_id="noetva-dev-tenant"`, against the real Azure DEV Postgres only. No source change. No other environment. No non-demo data touched.

**If no override mechanism exists:** Repository — MODIFY the minimum necessary lines in the affected seeder(s)/`bootstrap.py` to accept an explicit, non-default tenant parameter, preserving the existing safety rail against accidental cross-tenant seeding (the guard must remain fail-closed for any tenant not explicitly passed) — ceiling MODIFY ≤3 files, CREATE=0, DELETE=0 for this sub-step. Then perform the same single, manual, DEV-only seeding run.

**Verification:** re-run the four protected-capability real-browser checks (findings, context, evidence-fitness, supply-chain-impact) expecting real populated results where the Golden Thread applies; independently verify each of the five downstream claims in §10 truthfully before including it in any walkthrough narrative.

## 19. R14 — GitHub OIDC/lifecycle full wiring (explicitly deferred, optional)

Not authorized by this artifact. Not sequenced before closure (§11, §13-27). If picked up later: deploy `id-lifecycle`'s federated credential live, set the identified missing GitHub Actions variables. No ceiling frozen here — requires its own governance when scheduled.

## 20. Implementation sequence (frozen)

R12 (custom domain + OIDC + CORS) → R13 (demo-seed tenant correction + Golden Thread verification) → Final adversarial VM (§13's full criteria list, real-browser, from `app.noetva.ai`) → closure sign-off. R14 remains optional/unscheduled. No merge of any PR (#213-#230 or any future closure PR) without separate explicit authorization, at any point in this sequence.

## 21. Post-implementation VM plan (frozen, for the Final adversarial VM)

Execute every item in §13 in order, each with real evidence (not inference): DNS resolution, cert validity, marketing-site diff, real login from the new origin, real callback, real logout, token audience unaffected, full CDD-076 negative suite re-run against the new origin, CORS from the new origin (no wildcard), Postgres/Key Vault/migration preservation, Golden Thread walkthrough with fresh API evidence for every claim, start/stop lifecycle exercise, monitoring check, CI green, digest/revision record, source/IaC-drift check, GitHub-deployment disposition restated.

## 22. Fail-closed STOP conditions (evaluated for this DRG)

Authoritative main/candidate established (§1) — not triggered. Azure PR ancestry consistent (§1) — not triggered. No frozen governance artifact modified — not triggered. Live Azure state matches prior closure assumptions in every material respect (§2), Key Vault's public network access noted but not newly contradicting anything R11-R3 relied on — not triggered. Custom-domain architecture requires no security weakening (§4-5, standard DNS-only + optional CAA addition) — not triggered. Entra redirect architecture fully proven via live read (§6) — not triggered. No wildcard CORS needed anywhere (§7) — not triggered. Demo-seed operation is proven idempotent by source; the tenant-override mechanism is unconfirmed but requires only a read-only step to resolve, not an unsafe operation — not triggered. Golden Thread requires no fabrication — real data already exists, just tenant-mismatched (§9-10) — not triggered. Demo data targets `noetva-dev-tenant`, the real governed DEV tenant this environment already exists to serve — not "an environment not authorized for demo data" — not triggered. PostgreSQL private-access invariant untouched — not triggered. No secret exposure anywhere in this discovery — not triggered. GitHub deployment gaps require no unjustified long-lived credential; the sound OIDC design is simply incompletely deployed — not triggered, and explicitly not required for closure (§11). No lifecycle behavior risking data loss identified — not triggered. No production/marketing DNS record requires disturbance (§4) — not triggered. Scope is precisely frozen into R12/R13/R14 boundaries, each independently bounded — not triggered.

**No STOP condition is triggered. This governance artifact is authorized to freeze.**

## 23. Explicitly deferred — global runbook hardening

Per standing user decision, no global rewrite or "finalization" of `NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` is authorized here. R12's own narrow guide correction (§17) is the only exception, matching the same narrow-fix precedent already used throughout CDD-074/075/076. The guide is not, and must not be described as, final.

## 24. Explicitly deferred — Product Experience WOW

The bare-`<input>`-visibility defect on `/context` and `/quality/evidence-fitness` (Tailwind Preflight stripping unstyled native input chrome — `frontend/app/globals.css`, `frontend/app/context/_components/context-lookup.tsx`, `frontend/app/quality/evidence-fitness/page.tsx`) is reaffirmed as a real, independent frontend defect, explicitly out of scope for this closure program, recorded as an input to the future NOETVA-PRODUCT-EXPERIENCE-WOW initiative. No visual/product redesign is authorized by this artifact.
