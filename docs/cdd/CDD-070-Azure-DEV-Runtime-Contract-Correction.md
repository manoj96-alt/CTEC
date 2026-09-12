# CDD-070 — Azure DEV Runtime Contract Correction

**Status:** FROZEN
**Originating phase:** AZURE-DEV-RUNTIME-CONTRACT-R8 (DRG only in this artifact)
**Amends:** nothing frozen in place. Complements CDD-067/068/069 (all still open, PRs #213–#218) by correcting two application-runtime-contract defects discovered during real Azure execution of AZURE-DEV-MIGRATION-JOB-MONITORING-R7-I. Does not reopen, edit, or supersede any of them.

**Scope:** exactly two runtime-contract defects at the shared Azure Container Apps module boundary — (1) Key-Vault-secret-name reused as the literal container environment-variable name, and (2) a backend-only `/health` probe path hardcoded for every consumer of the shared Container App module. No other module, resource, or governance artifact is touched.

---

## 1. Authoritative baseline at freeze

Main SHA: `09acfeb77a258ff8a83a48a8fc4105279456f50a` — matches. Open PR stack, every head re-derived live from GitHub:

| PR | Branch | Head SHA | State |
|---|---|---|---|
| #213 | `azure/bootstrap-r5-g` | `14402751a596c2845e5c65c4c1db6d33c0466ab7` | OPEN |
| #214 | `azure/bootstrap-r5-i` | `6e2185b1dddc69364ad4520063fb3416296eafb4` | OPEN |
| #215 | `azure/private-db-bootstrap-r6-g` | `3263bca340df9af9582fa267f53455f428ca65da` | OPEN |
| #216 | `azure/private-db-bootstrap-r6-i` | `0e041403dcea8c42eec01175b6377bded41bbb59` | OPEN |
| #217 | `azure/migration-job-monitoring-r7-g` | `edf8434979ea39cdb160fc75a2e2ab733c106993` | OPEN |
| #218 | `azure/migration-job-monitoring-r7-i` | `6a55cf1463ad1fb892d5e83a02cb1134e3bee327` | OPEN |

CDD-067 SHA-256 (re-hashed): `5b2b19e86122f8db896012d97e5f08214773a7699da31b25c08c8833634e1e23` — matches. CDD-068: `5f98c59ee4992ba80fad7e1dee6f20d27f1b27931f4adbefafcae597a5817b3c` — matches. CDD-069: `58569430e47c81f0a84ccd890350b48a4073755188992ce6a1faf02b11a00aa6` — matches.

Cumulative candidate: `main`(`09acfeb7`) → R5-I(`6e2185b1`) → R6-I(`0e041403`) → R7-I(`6a55cf14`) is one linear chain (confirmed via `git merge-base`/`git log`). R8's implementation must be based on `6a55cf1463ad1fb892d5e83a02cb1134e3bee327`, not on bare `main`.

## 2. R7 monitoring closure — re-confirmed, not reopened

Read-only re-query of the real deployed alert resource: `metricName: Executions`, `dimensions[0].name: state`, `values: ["Failed"]`, `operator: GreaterThan`, `threshold: 0`, `timeAggregation: Total`, scope = `noetva-dev-eus2-migrate`, action group = `noetva-dev-eus2-ag-oncall` — all exactly as CDD-069 froze. This artifact does not modify `monitoring-alerts-only.bicep` or reopen CDD-069.

## 3. Defect 1 — real failure evidence and fully traced root cause

Real failure: the first-ever trigger of `noetva-dev-eus2-migrate` (`noetva-dev-eus2-migrate-po08p2r`) reached `Failed`. Logs: `sqlalchemy.exc.OperationalError: connection to server at "::1"/"127.0.0.1", port 5432 failed`. The real Key Vault secret `ctec-migration-database-url` was independently re-parsed (read-only, value never printed) and confirmed well-formed, pointing at the real host.

**Root cause, fully traced (not inferred from the Key Vault name alone):**

1. `infra/azure/modules/container-app.bicep` and `infra/azure/modules/container-apps-job-migration.bicep` both derive the container's environment-variable **name** directly from the Key-Vault-secret-reference item's own `name` field (`secretEnvVars = [for ref in keyVaultSecretRefs: { name: ref.name, secretRef: ref.name }]`). Real, read-only Azure inventory (env-var names only, no values) confirms this live: the backend Container App's two secret-derived env vars are literally named `ctec-database-url` and `ctec-runtime-handoff-key`; the migration Job's is literally named `ctec-database-url` — none are `CTEC_`-prefixed.
2. `backend/app/core/config.py`'s `Settings` (`SettingsConfigDict(env_prefix="CTEC_", case_sensitive=False, ...)`) requires the underscore-joined, `CTEC_`-prefixed name — `CTEC_DATABASE_URL`. A hyphenated variable never matches (independently verified locally: instantiating `Settings` with only `ctec-database-url` set in the environment yields `database_url is None`).
3. For the **migration Job**: `backend/alembic/env.py` contains `if settings.database_url: config.set_main_option("sqlalchemy.url", settings.database_url)` — a guard, not an unconditional assignment. With `settings.database_url` = `None`, this guard never fires, and Alembic silently falls back to its own static default already present in `backend/alembic.ini`: `sqlalchemy.url = postgresql+psycopg://ctec:ctec@localhost:5432/ctec`. This is the exact, fully-explained source of the observed `localhost`/`::1`/`127.0.0.1` connection attempt — not a guess, a directly read, static, pre-existing local-dev default that every environment variable layer failed to override.
4. For the **backend Container App**: `backend/app/core/dependency_container.py` guards every database-dependent capability behind `if settings.database_url:` — with the variable unset, the backend does not crash and does not attempt any connection; it silently runs with `ontology_sessions`/`entity_resolution_steward_api`/etc. left `None`, i.e. every database-backed capability is silently absent. This is a materially different failure mode from the migration Job's (silent degradation vs. an active failed connection) and is recorded as such — not conflated.
5. `ctec-runtime-handoff-key` → `backend/app/core/dependency_container.py`'s `if settings.runtime_handoff_key:` guard — same silent-degradation mechanism, gating `AuthenticatedHandoffProtector`/durable-execution wiring.

**Internal precedent proving the correct fix already exists in this codebase:** `infra/azure/modules/container-apps-job-db-bootstrap.bicep` (CDD-068, unaffected by this defect) already does exactly the right thing — its Container-Apps-secret names (`pg-admin-password`, `pg-app-password`, `pg-migrate-password`) are **explicitly different** from their consuming env-var names (`NOETVA_PG_ADMIN_PASSWORD`, `NOETVA_PG_APP_PASSWORD`, `NOETVA_PG_MIGRATE_PASSWORD` — note even the prefix differs, `pg-` vs `NOETVA_PG_`), via an explicit `env: [{ name: 'NOETVA_PG_ADMIN_PASSWORD', secretRef: 'pg-admin-password' }, ...]` array. This single module never had this defect, and proves the Bicep layer is entirely capable of an explicit secret-name/env-name split — this DRG does not invent a new pattern, it extends an already-working one to the two modules that lack it.

## 4. Complete Key Vault → Bicep → env → consumer matrix

| # | Key Vault secret | Bicep secret-ref item (today) | Container env-var name (today, real Azure) | Correct env-var name | Consumer / setting | Required? | Current mapping correct? |
|---|---|---|---|---|---|---|---|
| 1 | `ctec-database-url` | `{ name: 'ctec-database-url', keyVaultUrl: .../ctec-database-url }` (backend) | `ctec-database-url` | `CTEC_DATABASE_URL` | `Settings.database_url` → `dependency_container.py` (DB-backed APIs) | Required for DB-backed capability | **No** |
| 2 | `ctec-runtime-handoff-key` | `{ name: 'ctec-runtime-handoff-key', keyVaultUrl: .../ctec-runtime-handoff-key }` (backend) | `ctec-runtime-handoff-key` | `CTEC_RUNTIME_HANDOFF_KEY` | `Settings.runtime_handoff_key` → `AuthenticatedHandoffProtector` (32-byte AES key, urlsafe-base64) | Required for durable-execution handoff protection | **No** |
| 3 | `ctec-migration-database-url` | `{ name: 'ctec-database-url', keyVaultUrl: .../ctec-migration-database-url }` (migration Job) | `ctec-database-url` | `CTEC_DATABASE_URL` | `Settings.database_url` → inline `create_engine(...)` and `alembic/env.py` | Required | **No** |
| 4 | `postgres-admin-password` | not Bicep-wired (by design, CDD-067/068) | n/a | n/a | operator-only, intermediate record | n/a | correct as-is (no defect) |
| 5 | `postgres-app-password` | not Bicep-wired (by design) | n/a | n/a | operator-only, intermediate record | n/a | correct as-is |
| 6 | `postgres-migrate-password` | not Bicep-wired (by design) | n/a | n/a | operator-only, intermediate record | n/a | correct as-is |
| — | `pg-admin-password`/`pg-app-password`/`pg-migrate-password` (bootstrap Job, distinct Container-Apps secrets, not Key Vault) | explicit `{name, secretRef}` split already | `NOETVA_PG_ADMIN_PASSWORD` etc. | (same) | `run_db_bootstrap.sh` | Required | **Yes — precedent, untouched by this correction** |

Frontend Container App: `keyVaultSecretRefs: []` — zero secrets, zero exposure to Defect 1.

Non-secret env vars (`backendEnvVars` in `resources.bicep`, wired as plain `envVars`, never through the broken `secretEnvVars` path) — independently re-confirmed live and correct: `CTEC_ENVIRONMENT`, `CTEC_LOG_LEVEL`, `CTEC_CORS_ORIGINS`, `CTEC_OIDC_ISSUER`, `CTEC_OIDC_AUDIENCE`, `CTEC_OIDC_JWKS_URL`, `CTEC_OIDC_SCOPE_CLAIM`, `CTEC_OIDC_TENANT_CLAIM`, `CTEC_RUNTIME_HANDOFF_KEY_ID`. None of these are affected by Defect 1 or by its correction — they never pass through `secretEnvVars`.

## 5. Secret/env architectural contract (frozen)

**Key Vault secret identifier ≠ container environment-variable identifier, unless explicitly mapped.** Every `keyVaultSecretRefs` array item gains an explicit `envName` field alongside its existing `name` (the Container-Apps-secret / Key-Vault-reference name) and `keyVaultUrl`. The consuming modules (`container-app.bicep`, `container-apps-job-migration.bicep`) render the Container-Apps secret using `name`/`keyVaultUrl` exactly as today, and render the container's `env` entry using the new, separately-declared `envName` — never derived from `name` by any transformation, algorithmic or otherwise.

## 6. Algorithmic-conversion test (rejected, with evidence)

Tested whether `hyphenated-name → UPPERCASE_UNDERSCORE` mechanical conversion is safe as a general rule: applied to the two currently-broken secrets, it **would** happen to produce the right answer (`ctec-database-url` → `CTEC_DATABASE_URL`, `ctec-runtime-handoff-key` → `CTEC_RUNTIME_HANDOFF_KEY`). Applied to the bootstrap Job's own already-correct, already-precedented secrets, it does **not**: `pg-admin-password` mechanically converts to `PG_ADMIN_PASSWORD`, but the real, correct, already-working env-var name is `NOETVA_PG_ADMIN_PASSWORD` — a different prefix entirely, not a reversible transform of the secret name. This single counter-example inside Noetva's own codebase is sufficient to reject Option E (algorithmic conversion) for any general rule; explicit declaration (§5) is required.

## 7. Migration and backend expected env contract (traced, not assumed)

- Migration Job / Alembic: `CTEC_DATABASE_URL`, traced through `backend/alembic/env.py`'s `settings.database_url` guard to `backend/alembic.ini`'s static fallback (§3.3) and through the migration Job's own inline `create_engine(settings.database_url)` command.
- Backend: `CTEC_DATABASE_URL`, traced through `backend/app/infrastructure/persistence/database.py`'s `create_database_engine` (`ValueError` if unset) and `dependency_container.py`'s guard.
- Runtime handoff key: `CTEC_RUNTIME_HANDOFF_KEY`, traced through `dependency_container.py`'s `urlsafe_b64decode(settings.runtime_handoff_key)` call feeding `AuthenticatedHandoffProtector`, which requires a decoded key of length 16/24/32 bytes (`backend/app/runtime/persistence/crypto.py`) — the already-Key-Vault-stored value's contract (32-byte AES-256 key) is unaffected by this correction; only its delivery path is corrected.

## 8. Non-secret OIDC/environment regression check

Re-confirmed live (§4): all nine plain `CTEC_OIDC_*`/`CTEC_ENVIRONMENT`/`CTEC_LOG_LEVEL`/`CTEC_CORS_ORIGINS`/`CTEC_RUNTIME_HANDOFF_KEY_ID` env vars are wired through `backendEnvVars`/plain `envVars`, entirely independent of `keyVaultSecretRefs`/`secretEnvVars`. The §5 correction touches only the `secretEnvVars` rendering path and the two array literals in `resources.bicep` that carry Key Vault references — it cannot regress any of these nine values, and this artifact requires the implementing phase's static check (§17) to prove that non-regression structurally, not merely assert it.

## 9. Defect 2 — real failure evidence and root cause

Real failure: the frontend Container App reports `provisioningState: Succeeded`, and its own logs show the Next.js process reaching `✓ Ready` — but the revision never leaves `runningState: Activating`/`healthState: None`, and every external HTTPS request times out completely. Root cause, real-Azure-confirmed: `container-app.bicep` hardcodes both `Startup` and `Liveness` probes to `httpGet: { path: '/health', port: 3000 }` for **every** consumer of the module. This is correct for the backend, which genuinely has a `/health` route (`backend/app/api/health/router.py`, confirmed by source: an unconditional `{"status": "healthy"}`, no DB check, no auth — appropriate for exactly Startup+Liveness, nothing deeper). It is not correct for the frontend: `find frontend/app -iname "health*"` returns nothing — the Next.js application has no `/health` route of any kind. The platform's probe against a nonexistent route can never succeed, so the revision never reports healthy/routable regardless of the application's own internal readiness.

**This is precisely why ARM `provisioningState: Succeeded` must never be read as "revision healthy/routable."** `provisioningState` describes the ARM control-plane write; `runningState`/`healthState` on the revision, plus an actual external HTTPS probe, describe whether real traffic can reach the workload. Both must be checked in every future real-Azure VM closure — a requirement this artifact freezes for the implementation phase (§18).

## 10. Workload health/probe inventory

| Workload | Port | Existing route matching `/health`? | Auth required? | DB dependency? | Cross-service dependency? | Suitable for Startup? | Suitable for Liveness? |
|---|---|---|---|---|---|---|---|
| Backend (`noetva-dev-eus2-backend`) | 8000 | Yes (`backend/app/api/health/router.py`) | No | No | No | Yes | Yes |
| Migration Job (`noetva-dev-eus2-migrate`) | n/a (run-to-completion Job, no ingress/probes) | n/a | n/a | n/a | n/a | n/a | n/a |
| Bootstrap Job (`noetva-dev-eus2-db-bootstrap`) | n/a (run-to-completion Job, no ingress/probes) | n/a | n/a | n/a | n/a | n/a | n/a |
| Frontend (`noetva-dev-eus2-frontend`) | 3000 | **No** | No (once added, must remain no-auth) | No (once added, must not call the backend) | **Currently coupled via the shared hardcoded path; must become independent** | No, until corrected | No, until corrected |

Only Container Apps (backend, frontend) have ingress/probes at all; the two Container Apps Jobs are run-to-completion and out of scope for this section.

## 11. Startup / Liveness / Readiness semantics (frozen for Noetva DEV)

- **Startup**: the process has initialized enough to accept and correctly answer an HTTP request on its target port. Nothing more.
- **Liveness**: the process remains able to answer that same request; a failure here causes Azure to restart the container.
- **Readiness**: not currently used by either workload (Container Apps' `Readiness` probe type is not configured for backend or frontend today) — this artifact does not introduce one. `/health`'s existing, disclosed meaning (liveness-only, no DB check) is preserved exactly, not upgraded.

Both current uses (backend's `/health`, and the frontend route this artifact adds) are Startup+Liveness only, deliberately shallow, deliberately free of any dependency (database, another service, or authentication) that could cause one workload's outage to cascade into another's forced restart.

## 12. Selected frontend probe architecture

Two changes together (Option A + Option B from the governing prompt, combined — neither alone is sufficient):

1. **Parameterize `container-app.bicep`** with a new, required parameter `healthProbePath string` (no default — every module caller must state its own value explicitly, which is itself part of the fix: a future third consumer cannot silently inherit backend's assumption). Both `Startup` and `Liveness` probe blocks reference this parameter instead of the literal `'/health'`.
2. **Add a dedicated, frontend-local route**, `frontend/app/health/route.ts` — a Next.js Route Handler returning a static `200 { "status": "healthy" }` JSON response, with zero network calls (no fetch to the backend, no auth check, no cookie/session read). `resources.bicep`'s `backendApp` call passes `healthProbePath: '/health'` (unchanged value, now explicit rather than implicit); `frontendApp` passes `healthProbePath: '/health'` pointing at this new frontend-local route.

This satisfies every constraint the governing prompt raised: it works before Entra SPA redirect configuration, requires no login/access token/final domain/backend auth, and a backend outage can never cause the frontend's own liveness probe to fail (structurally impossible — the new route makes no calls to the backend).

## 13. Rejected probe alternatives

- **Option C (TCP probe):** rejected — a bare TCP-connect probe would pass the instant the Node.js process binds port 3000, before Next.js has necessarily finished initializing routes; the existing HTTP `httpGet` mechanism (already used for backend) is more meaningful and consistent, and Container Apps' `httpGet` probe type is already proven working (backend).
- **Option D (root `/`):** rejected as the *sole* mechanism — `/` in this frontend is the real landing/dashboard page, which may itself perform client-side data fetching, redirects, or auth-aware rendering later; using it as a health target risks exactly the coupling this correction exists to avoid, and its stability under future frontend changes is not guaranteed the way a purpose-built, deliberately inert route is.
- **Option E (`/administration`):** explicitly rejected — the governing prompt itself flags this, and source confirms why: `/administration`'s own health tile calls the **backend's** `/health` (`fetch(`${apiOrigin()}/health`)`, confirmed in `frontend/app/administration/page.tsx`). Using it as the frontend's own liveness target would make frontend liveness depend on backend availability — precisely the cross-service coupling §9/the "PREFERRED HEALTH PROPERTY" section require avoiding, since no deliberate governance decision calls for that coupling.

## 14. Migration re-entry safety (proven, not assumed)

The failed execution (`noetva-dev-eus2-migrate-po08p2r`) failed at the connection-establishment step of `alembic upgrade head` — the very first command in the Job's `set -e` script (§3.3) — before any SQL statement of any kind could be issued against any database (the connection itself never succeeded, to any host). The two seeder steps that follow in the same script never ran (aborted by `set -e` immediately after the first failure). **There is zero risk of partial or corrupted migration/seed state from this execution** — rerunning the Job after the Defect-1 correction is implemented is safe and starts from the real, untouched, pre-migration schema state. The failed execution record itself (`noetva-dev-eus2-migrate-po08p2r`, status `Failed`) is not deleted, hidden, or reset by this artifact or its implementation — it remains real, honest history.

**R7 monitoring interaction, disclosed honestly:** the corrected `Executions`/`state=Failed` alert may have already recorded this real failed execution in its metric history (its 5-minute evaluation window may have already opened and closed around the failure time). This is expected, correct behavior for a genuinely-failed execution — not a defect, and not something this artifact resets or suppresses.

## 15. Tenant-bootstrap ordering (unchanged, reaffirmed)

Migration success → schema verification → `noetva-dev-tenant` bootstrap remains the required order. This DRG does not authorize skipping ahead; the implementation phase must not bootstrap the tenant before a real, successful migration execution.

## 16. Combined-vs-split correction decision

**Combined into one CDD/implementation.** Both defects sit at the identical architectural boundary (the shared Container Apps Bicep modules), were discovered in the same real-execution certification, require no materially different authority (no new identity, no new network resource, no Key Vault change for either), and a combined fix is smaller in total surface than staging two separate phases through the same files twice. Splitting them would not reduce risk — it would only add a redundant DRG/I/VM cycle over the same three Bicep files.

## 17. Exact implementation paths (ceiling)

| # | Path | Change |
|---|---|---|
| 1 | `infra/azure/modules/container-app.bicep` | MODIFY — `secretEnvVars` uses an explicit `envName` field instead of `ref.name`; add required `healthProbePath` parameter; both probe blocks reference it instead of the literal `/health` |
| 2 | `infra/azure/modules/container-apps-job-migration.bicep` | MODIFY — identical `envName`-based `secretEnvVars` correction |
| 3 | `infra/azure/resources.bicep` | MODIFY — `backendSecretRefs` and the migration Job's `keyVaultSecretRefs` literal each gain an explicit `envName` field; `backendApp`/`frontendApp` module calls each gain an explicit `healthProbePath` argument |
| 4 | `frontend/app/health/route.ts` | CREATE — dependency-free, unauthenticated, static `200` health route |
| 5 | `frontend/tests/health-route.test.ts` (or the frontend's own established naming convention for a route test) | CREATE — proves the route returns `200` with zero network/backend calls |
| 6 | `infra/azure/validation/static_architecture_checks.py` | MODIFY — add the two structural regression checks (§18) |
| 7 | `infra/azure/README.md` | MODIFY — document the corrected secret/env contract and the health-probe parameterization |
| 8 | `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` | MODIFY — update the migration/backend build and Part 30/31 verification steps to require the real-Azure env-NAME and revision-health checks (§18) |

```
CREATE = 2
MODIFY = 6
DELETE = 0
TOTAL  = 8
```

No other path is authorized. In particular: `infra/azure/modules/container-apps-job-db-bootstrap.bicep` (already correct, §3 precedent), `infra/azure/modules/monitoring-alerts-only.bicep` (CDD-069, not reopened), the six Key Vault secret *values*, and Entra/Cloudflare/GitHub settings are all untouched.

## 18. Static regression requirements (both defects, structural not literal)

1. **Secret/env contract:** parse `backend/app/core/config.py`'s `Settings` fields and its `env_prefix`; for every `keyVaultSecretRefs`/`backendSecretRefs` literal item in `resources.bicep`, assert an `envName` field exists, matches the pattern `^CTEC_[A-Z0-9_]+$`, and corresponds to a real `Settings` field (`CTEC_` + fieldname.upper() must equal a declared field). This is a structural cross-file check, not a fixed-string grep — it would have caught the original defect (no `envName` field existed at all) and will catch a future mismatch even if the specific names change.
2. **Health probe contract:** assert `container-app.bicep` contains no literal `'/health'` (or any literal path) inside its `probes:` block — only a parameter reference; assert every module call site in `resources.bicep` that instantiates `container-app.bicep` explicitly supplies a `healthProbePath` argument. This fails if a shared module again hardcodes one consumer's assumption for all consumers, independent of what the specific path strings are.

Static checks remain necessary but not sufficient — real-Azure verification (§19) is mandatory before any PASS, exactly as CDD-069 established.

## 19. Real-Azure VM requirements (for the future implementation phase, not satisfied by this DRG)

1. Application-tier deployment reaches `provisioningState: Succeeded`.
2. Migration Job's real, live env-var **names** (read-only inventory, never values) include `CTEC_DATABASE_URL`.
3. No secret value exposed at any point (env-var names only, never `--query ...secrets...value`).
4. Migration Job triggered again; execution reaches `Succeeded`.
5. Migration genuinely connects to the real private PostgreSQL FQDN, never `localhost`/`127.0.0.1`/`::1` (verified via logs showing no connection-refused/localhost error, and/or a schema-existence check).
6. Alembic migration completes; both governed seeders complete.
7. Required application schema/tables exist (safe, narrow, already-governed verification mechanism only — no broadened DB authority).
8. `noetva-dev-tenant` bootstrap succeeds, idempotently, exactly once.
9. Backend's real, live env-var names include `CTEC_DATABASE_URL` and `CTEC_RUNTIME_HANDOFF_KEY`.
10. Backend's database-dependent path can actually connect (a safe, narrow, already-governed check — not a new broad DB probe).
11. Frontend revision reaches `healthState: Healthy`, leaves `Activating`.
12. Frontend HTTPS is externally reachable (a real HTTP request from outside the VNet succeeds).
13. Frontend's own `/health` route returns the expected success response.
14. Backend's `/health` semantics remain exactly as today (liveness-only, no DB check) — not silently upgraded.
15. PostgreSQL `publicNetworkAccess` remains `Disabled`.
16. No secret leakage (bounded audit, as every prior phase).
17. No authority-boundary regression (migration/backend/bootstrap authorities remain structurally distinct, exactly as CDD-068 froze).

## 20. Implementation-phase Azure mutation authorization (explicit, not left ambiguous)

After source implementation and CI both pass, R8-I **is** authorized to, in this exact order: redeploy the application tier (what-if first, then real), read back the corrected env-var names/probe configuration, trigger the normal migration Job, verify schema, bootstrap `noetva-dev-tenant`, verify backend database-dependent behavior, and verify frontend health/routability/HTTPS reachability. R8-I is **not** authorized to: mutate Entra, mutate Cloudflare, mutate GitHub repository/environment/OIDC settings, merge any PR, or delete any Azure resource — each of those remains a separate, independently governed future step.

## 21. Security invariants (unchanged, reaffirmed)

PostgreSQL `publicNetworkAccess` stays `Disabled`; no firewall/VM/Bastion/VPN/new NSG; no secret value ever appears in a Bicep output or a log; migration Job gains no ADMIN authority; backend gains no ADMIN authority; the bootstrap Job stays dormant/manual; migration retains migration-only authority; backend retains application-only authority; the Key Vault six-secret contract is preserved exactly (values untouched); digest-pinned private ACR images are preserved; OIDC scope/tenant-claim configuration is preserved (§8 non-regression).

## 22. STOP conditions (all evaluated during this DRG; none triggered)

- The secret/env consumer contract **can** be determined exactly (§4/§7, traced to real source, not assumed) — not triggered.
- The fix does **not** require renaming Key Vault values (§5/§17 — values untouched, only the Bicep-layer mapping changes) — not triggered.
- The fix does **not** expose secret values (§18/§19 — every check is name-only) — not triggered.
- Migration Job gains **no** ADMIN authority (§21) — not triggered.
- Backend gains **no** ADMIN authority (§21) — not triggered.
- The frontend probe requires **no** auth (§12 — a static, unauthenticated route) — not triggered.
- Frontend liveness does **not** depend on backend availability without deliberate governance — the opposite is deliberately chosen (§12/§13) — not triggered.
- The shared module correction **can** distinguish workloads truthfully (§12 — explicit required parameter, no default to silently inherit) — not triggered.
- Migration rerun **is** proven safe (§14 — connection failed before any SQL, zero partial state) — not triggered.
- The source path ceiling **is** bounded (§17 — 8 paths, all named) — not triggered.
- Real Azure evidence **supports** (does not contradict) the root causes and corrections in this artifact (§3/§9, all independently confirmed live) — not triggered.
- The correction does **not** require public PostgreSQL access or any destructive Azure recovery — not triggered.

No STOP condition fired. This correction is safe to freeze and hand to an implementation phase.

---

**Freeze evidence index:** all live-Azure evidence (real env-var names, real probe configuration, real alert criteria, real failed-execution status) was captured read-only during this DRG, values never retrieved except the one read-only, non-printed parse of `ctec-migration-database-url`'s structure (host/user/port/path/query only) already performed in R7-I and re-confirmed structurally sound here. `alembic.ini`'s static fallback and `container-apps-job-db-bootstrap.bicep`'s precedent were both confirmed directly from source, not assumed.
