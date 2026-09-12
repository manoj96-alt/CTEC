# Noetva Azure Production Architecture — Deployment Foundation

This directory implements (as reviewable, non-deployed code) the architecture frozen in `NOETVA-AZURE-PRODUCTION-ARCHITECTURE-D0`, extended by `NOETVA-AZURE-COST-LIFECYCLE-G-R2`/`I-R2` with a governed, cost-aware start/stop lifecycle for DEV/STAGING/DEMO. **Nothing in this directory has been deployed.** No Azure resource exists as a result of any phase to date. See the I0-R1 and I-R2 final reports for the complete audit trail.

## CEO / operator runbook (Noetva I-R2 Section 36)

Normal demo operation never requires the Azure Portal. Everything below is a GitHub Actions "Run workflow" click, under this repository's **Actions** tab:

| I want to... | Workflow | What to fill in |
|---|---|---|
| **Start Noetva Demo** | `Start Noetva Environment` | `environment = demo`, optional `ttlHours` (default 4) |
| **Stop Noetva Demo** | `Stop Noetva Environment` | `environment = demo` |
| **Extend Noetva Demo** | `Extend Noetva Environment` | `environment = demo`, `additionalHours` |
| **Hold Noetva Demo** (e.g. for a long workshop) | `Hold Noetva Environment` | `environment = demo`, `holdUntilUtc` (an absolute time — no permanent hold exists) |
| **Check Noetva Demo Status** | `Check Noetva Environment Status` | `environment = demo` |
| **Check Noetva Monthly Cost** | Azure Portal → Cost Management (no GitHub workflow needed — see G-R2's cost model for what to expect) |

The same five workflows work identically for `dev`/`staging`. `production` is never a selectable option in any of them — it structurally cannot be targeted by this automation.

A forgotten demo shuts itself down on its own: the TTL expires (default 4h), and the nightly sweep (`Noetva Nightly Lifecycle Sweep`, 08:00 UTC daily) catches anything TTL didn't. A separate `Noetva PostgreSQL Restart Monitor` runs daily specifically to catch Azure's own documented 7-day auto-restart behavior and safely re-stop a database that came back on its own.

## Status legend used throughout this document

- **IMPLEMENTED AS CODE** — a real, compiled, validated file exists in this directory.
- **CONFIGURED BUT NOT DEPLOYED** — the Bicep/parameter file fully specifies the resource; `az deployment` has never been run against it.
- **REQUIRES AZURE EXECUTION** — can only be verified once a real Azure resource exists.
- **REQUIRES MANUAL FOUNDER/ADMIN INPUT** — a real-world value only a human can supply (see Manual Input Register below).
- **DEFERRED** — intentionally out of scope for this phase, with a stated reason.

## Layout

```
infra/azure/
  main.bicep                          -- subscription-scoped entry point (creates the RG)
  resources.bicep                     -- resource-group-scoped composition of everything
  modules/                            -- one file per resource concern
  environments/{dev,staging,prod,demo}/main.parameters.json
  db-bootstrap/                       -- PostgreSQL role/grant SQL, adversarially tested locally
  validation/                         -- static + connector-security checks, runnable with no Azure dependency
  scripts/                            -- operator wrapper scripts (never print secret values)
.github/workflows/azure-deploy.yml    -- manual-only deployment workflow, OIDC federation, gated on CI
```

No competing/duplicate infrastructure tree was created — the repository's existing `deployment/` directory (Docker-only, `compose/`+`docker/` subfolders, both empty `.gitkeep` placeholders) and `scripts/`/`tools/` (governance/CDD tooling) were left untouched; this is a new, additive `infra/azure/` tree.

## D0 assumption re-verification (Section 7)

Every load-bearing D0 fact was re-read directly from this worktree's files before any code was written, not assumed from memory:

| Fact | Re-verified how | Result |
|---|---|---|
| Next.js standalone frontend | `frontend/next.config.ts` (`output: "standalone"`), `frontend/Dockerfile` | Confirmed |
| FastAPI/uvicorn backend, single process | `backend/docker-entrypoint.sh` final line | Confirmed |
| PostgreSQL 17 | `docker-compose.yml` `image: postgres:17-alpine` | Confirmed |
| No persistent application filesystem | grep for file writes in `backend/app` (excl. tests) | Confirmed, none found |
| Provider-neutral OIDC | `backend/app/core/config.py`, `backend/app/api/supplier_risk/authentication.py`, `frontend/lib/auth/config.ts` | Confirmed |
| DB composite-FK tenant isolation | migration `0038` read directly | Confirmed |
| Migration-at-startup entrypoint behavior | `backend/docker-entrypoint.sh` | Confirmed |
| DB pool defaults (5 / +10 overflow) | `backend/app/core/config.py` | Confirmed |
| Connector SSRF/metadata-address hardening | `backend/app/infrastructure/connectors/rest_connector.py` | Confirmed, and re-tested live (see AL) |
| Health endpoint is liveness-only | `backend/app/api/health/router.py` | Confirmed |

No material D0 assumption was found false. No STOP condition triggered at this gate.

## Runtime component inventory — production-safety classification of every seeder (Section P)

`docker-entrypoint.sh` runs exactly two seeders on every container start today: `OntologySeeder` and `BlueprintSeeder`. Both are classified **PRODUCTION REQUIRED**, evidence-based, not assumed:

| Seeder | Classification | Evidence |
|---|---|---|
| `OntologySeeder` (`ontology_seed.py`) | **PRODUCTION REQUIRED** | Seeds the canonical, tenant-independent governed vocabulary (EntityType/RelationshipType/InstitutionalConcept) every tenant needs to function at all. Deterministic (`uuid5`), idempotent by its own docstring. |
| `BlueprintSeeder` (`blueprint_seed.py`) | **PRODUCTION REQUIRED** | Seeds the canonical Supply Chain Blueprint, references only the already-governed ontology, fails explicitly rather than silently skipping on a missing reference. Deterministic, idempotent. |
| `demo_oqi_seeder.py` | **DEMO DATA — NOT SAFE FOR PRODUCTION** | Its own docstring: *"Never invoked by normal production bootstrap... Refuses to seed any tenant other than the labeled demo tenant."* Not called by `docker-entrypoint.sh`; CI invokes it as a separate, explicit step. |
| `demo_ontology_copilot_seeder.py`, `demo_field_value_evidence_seeder.py`, `demo_gate_f_seeder.py`, `demo_semantic_mapping_seeder.py`, `demo_entity_resolution_seeder.py` | **DEMO DATA — NOT SAFE FOR PRODUCTION** | Named and precedent-referenced identically to `demo_oqi_seeder.py` (its docstring explicitly says it follows `demo_gate_f_seeder.py`'s exact precedent). |

**Consequence for the migration Job** (`modules/container-apps-job-migration.bicep`): its command runs `alembic upgrade head` + `OntologySeeder` + `BlueprintSeeder` only — an exact, truncated reproduction of `docker-entrypoint.sh`'s own first two phases. No `demo_*` seeder is ever wired into any environment's automatic migration path, including DEMO's own environment (which the operator would seed manually and deliberately, matching every `demo_*` seeder's own designed invocation model).

## Full 46-migration safety review (Section R) — empirically verified, not just read

Every migration was reviewed; risk patterns (`DROP`, `RENAME`, `alter_column`, `add_column` with `nullable=False`, raw `op.execute`, `create_index`) were triaged across all 46 files and the flagged ones read in full. Beyond static review, **all 46 migrations were actually run, twice, against a real local PostgreSQL 17 container** — once to prove the chain applies cleanly at all, and a second time connected as the exact `noetva_migrate` role this architecture defines, to prove that role has sufficient (and only sufficient) privilege for the entire chain. Both runs produced exactly 126 tables (matching the product's own CI expectation) and left `alembic_version` at `0046_oqi5_remediation_tenancy`.

**Classification: ROLLING COMPATIBLE for the deployment scenario these 46 migrations will actually face** — replay, in full, against a fresh/empty Azure Flexible Server database during initial provisioning. No `DROP`/`RENAME` was found outside of a migration's own `downgrade()` cleanup path; every `add_column(..., nullable=False)` uses the safe `server_default`-then-drop, or data-driven fail-closed backfill (see `0011`, `0012`), or a constant fallback default (`0030`) pattern — never a bare NOT NULL against a populated table. `0037`'s `VARCHAR(8)`→`VARCHAR(16)` widen is a metadata-only operation in PostgreSQL (no rewrite). The tenant-isolation FK migrations (`0038`, `0041`–`0044`, `0046`) use single-phase `ADD CONSTRAINT` (not `NOT VALID`+`VALIDATE`) — harmless against the empty tables these 46 migrations will actually run against at initial deployment, but **flagged as forward-looking discipline for any future migration (0047+)** that adds a similar constraint to an already-populated production table: use `NOT VALID` + a separate `VALIDATE CONSTRAINT` to avoid a blocking table-level lock at scale.

### Real defect found and fixed: `pgcrypto` extension

Running the chain as `noetva_migrate` (a plain, non-superuser login) failed on migration `0001` with `permission denied to create extension "pgcrypto"` — `gen_random_uuid()`, used as the default for nearly every UUID primary key, requires it. This is now handled as a narrow, disclosed, one-time exception (see `db-bootstrap/001_create_roles_and_grants.sql` and `modules/postgresql.bicep`'s `azure.extensions` allow-list configuration, independently confirmed against current Microsoft documentation) — the ADMIN authority creates the extension once per environment; `noetva_migrate` and `noetva_app` never need or receive that privilege.

## Database role bootstrap — adversarially verified locally (Section 21/N)

`db-bootstrap/001_create_roles_and_grants.sql` was tested against a real PostgreSQL 17 container, iterated until correct:

- An initial draft used `:'app_password'` psql-variable substitution inside a `DO $do$...$do$` block — **failed** (`syntax error at or near ":"`), because psql's variable substitution does not reach inside dollar-quoted text. Fixed by creating the role with no password inside the `DO` block and setting the real password via a plain top-level `ALTER ROLE`, outside any dollar-quoting.
- Re-run twice consecutively with no error — confirmed idempotent.
- `db-bootstrap/002_validate_role_privileges.sql` was run for real as `noetva_app` against the fully-migrated 126-table schema: `CREATE TABLE` → **permission denied for schema public**; `ALTER`/`DROP` on an existing table → **must be owner of table** (both correctly rejected); a real `SELECT` → succeeds. A live-INSERT probe of the tenant-isolation FK was replaced with a `pg_constraint` catalog check (a live INSERT would have failed for an unrelated, non-tenant FK on an unseeded database, which would have looked like a false failure) — confirmed all 4 sampled composite tenant-qualified FKs exist with the correct `(tenant_id, entity_id)` column pairs.
- Confirmed empirically, not just by design: `noetva_app` automatically receives `SELECT`/`INSERT`/`UPDATE`/`DELETE` on every table `noetva_migrate` creates, with zero manual re-grant step, via `ALTER DEFAULT PRIVILEGES`.

## Entra External ID — tenant_id claim mechanism (Section 27, hard gate)

Independently verified against current Microsoft documentation (`custom-extension-tokenissuancestart-configuration`, external-tenant tab present and current): a **custom authentication extension** on the **`TokenIssuanceStart`** event, attached to the **resource (API) application registration** — not merely the client/SPA app — **can** inject a custom claim (mapped to any `JwtClaimType` name, including exactly `tenant_id`) into the **access token** the backend actually validates. This is real, current, and applies to external tenants. **Not a STOP.**

**Newly disclosed prerequisite, not hidden:** the mechanism requires a real, callable HTTPS endpoint (Microsoft's own guide backs it with an Azure Function) that computes and returns the tenant_id value for the authenticating user at token-issuance time — this endpoint, and the underlying question of *where the user→tenant mapping itself is sourced from* (today there is exactly one hardcoded demo tenant; no real multi-customer user-to-tenant directory exists yet), is genuinely new infrastructure this R1 phase does **not** build. It is out of this phase's authorized artifact ledger (Section E) and must be scoped as its own small, explicit piece of work before the first non-demo Entra-authenticated tenant can be onboarded. This is disclosed here precisely so it is never silently assumed solved.

## Frontend build-time OIDC vs. immutable-digest promotion (Section 28/W) — resolved, no application change

`frontend/Dockerfile` bakes `NEXT_PUBLIC_OIDC_*` into the compiled JS bundle via Docker build `ARG`s (re-confirmed directly against the file). Since `redirect_uri` (and often `client_id`) necessarily differs by environment hostname, **the same frontend image cannot be byte-for-byte promoted across DEV→STAGING→PROD**, directly conflicting with a naive reading of "promote the same digest everywhere."

**Resolution (Option A from D0's three choices — no code change):** the **backend** image (whose OIDC config is entirely runtime/env-var driven, confirmed in `config.py`) is still built once and promoted as the same digest across environments, exactly as D0 intended. The **frontend** is instead built once **per environment**, from the identical git commit SHA, each build producing its own immutable, digest-pinned, git-SHA-traceable image (see `.github/workflows/azure-deploy.yml`'s `build-and-push` job: the frontend image tag includes `-${{ inputs.environment }}`). This is a build-pipeline/promotion-model refinement only — zero lines of frontend or backend source were touched to reach this resolution.

## Manual Input Register (Section 52) — required before any real Azure execution

| Item | Why it can't be invented here |
|---|---|
| Azure subscription ID | No Azure session is authenticated in this phase (`az account show` → not logged in, confirmed) |
| Real Azure AD/Entra tenant ID | Founder-controlled, doesn't exist in this repository |
| Real Entra External ID (CIAM) tenant, its custom domain, and the `TokenIssuanceStart` custom-extension backing Function | Requires the founder to provision a real Entra External ID tenant and decide the user→tenant sourcing design (see above) |
| Production domain name(s) for `app.<domain>`/`api.<domain>` | D0/I0-R1 explicitly must not invent a production domain |
| `alertEmail` (on-call recipient) | Not in this repository |
| `postgresAdminPassword`, `NOETVA_PG_APP_PASSWORD`, `NOETVA_PG_MIGRATE_PASSWORD` | Must be generated and stored in Key Vault by an operator, never committed |
| GitHub Environment protection rules (required reviewers) for `dev`/`staging`/`production`/`demo` | A GitHub repository setting; this phase does not mutate GitHub settings (Section 41 also applies: GitHub secret scanning is currently **disabled** on this repo per the GitHub API, and enabling it is the same category of out-of-scope GitHub-setting mutation) |
| `NOETVA_CICD_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `NOETVA_ACR_*`, `NOETVA_OIDC_*` GitHub Actions variables | Populated only after the identities/registry actually exist |
| Desired Azure region, if overriding the frozen default (`eastus2`) | Only the founder can supply real customer-geography requirements |
| `NOETVA_LIFECYCLE_CLIENT_ID`, `NOETVA_LIFECYCLE_STORAGE_ACCOUNT` GitHub Actions variables (I-R2) | Populated only after `lifecycle-main.bicep` is deployed and its outputs are known |
| Budget `monthlyAmount` + `contactEmail` for `modules/budget.bicep`, per environment (I-R2 Section 28) | No real Azure pricing evidence exists yet; the module has no default and refuses to compile a fabricated number |
| `NOETVA_PG_ADMIN_PASSWORD` GitHub secret used by lifecycle workflows' DB-session-safety check (I-R2 Section 24) | Same admin credential class as R1's `postgresAdminPassword` — generated and stored by an operator, never committed |
| **Deployment order** (I-R2 Section 9/11): `lifecycle-main.bicep` must be deployed AFTER `main.bicep` has already created `rg-noetva-dev`/`rg-noetva-staging`/`rg-noetva-demo` | Its role assignments target those resource groups by name via cross-scope modules, which requires the target to already exist — disclosed explicitly in `lifecycle-main.bicep`'s own parameter description, not hidden |
| **Lifecycle identity federation** (Noetva R4-DRG D2 / R4-I): `lifecycle-main.bicep`'s `githubEnvironmentNames` parameter (default `['dev', 'staging', 'demo']`) drives one federated credential per name under the single shared `id-lifecycle` identity — deploy it once with this default; do not override it to a single shared name (e.g. `'lifecycle'`), which would produce a federated-credential subject that matches none of the real lifecycle workflows' GitHub Environment contexts | Corrects a root-caused defect: the identity previously received exactly one credential, scoped to a GitHub Environment no workflow actually runs under, so `azure/login@v2` could never have succeeded for any real lifecycle workflow run |

## Known residual risks (disclosed, not hidden)

1. ~~Alert metric names/dimensions in `modules/monitoring-alerts-only.bicep` were not independently re-verified against a real deployed resource.~~ **RESOLVED (CDD-069).** The real AZURE-DEV-APPLICATION-TIER-R7-EXECUTION deployment independently proved `storage_percent`/`active_connections` (PostgreSQL) correct (both alerts deployed successfully), and proved `JobExecutionCount`/`executionStatus` (the original migration-Job alert) wrong — `Microsoft.App/jobs` exposes no such metric, and Azure rejected it with `BadRequest`. CDD-069 (`docs/cdd/CDD-069-Azure-DEV-Migration-Job-Monitoring-Correction.md`) queried the real deployed resource's own metric definitions and corrected the migration-Job alert to the real metric `Executions` with dimension `state` (value `Failed`), independently corroborated against Microsoft's published `JobExecutionRunningState` REST API enum. Bicep's compiler still does not validate metric-name strings — this item is closed by real-Azure evidence, not by Bicep tooling.
2. `/health` remains liveness-only (no DB check), matching today's Docker behavior exactly (Noetva D0 Section K/BR) — used for the backend Container App's liveness and startup probes. A DB-aware `/ready` endpoint is explicitly **NOT IMPLEMENTED** here — that would be an application code change, outside this phase's authorization, and is not silently added.
3. ~~The Key Vault secret-reference `name` was reused as the literal container environment-variable name, and the shared Container App module hardcoded the backend's `/health` path for every consumer.~~ **RESOLVED (CDD-070).** Real Azure execution proved both defects: the migration Job's first real trigger failed connecting to `localhost` (traced to Alembic's own static `alembic.ini` fallback firing because `CTEC_DATABASE_URL` was never actually set — the container only ever received the literal, un-prefixed `ctec-database-url`), and the frontend Container App never left `Activating` because its probe targeted a `/health` route that only ever existed on the backend. `modules/container-app.bicep` and `modules/container-apps-job-migration.bicep` now render each secret's container environment-variable name from an explicit, separately-declared `envName` field (never derived from the Key Vault/Container-Apps secret name algorithmically — `container-apps-job-db-bootstrap.bicep`'s own pre-existing `NOETVA_PG_*` naming already proved this explicit pattern necessary and correct). `container-app.bicep`'s `healthProbePath` is now a required parameter with no default; the frontend has its own truthful, dependency-free route at `frontend/app/health/route.ts`, and the backend continues using its own unchanged `/health`. See `docs/cdd/CDD-070-Azure-DEV-Runtime-Contract-Correction.md` for full evidence.
4. ~~The two live Azure Key Vault PostgreSQL DSNs (`ctec-database-url`, `ctec-migration-database-url`) used a bare `postgresql://` scheme.~~ **RESOLVED (CDD-071).** A real migration execution reached `ModuleNotFoundError: No module named 'psycopg2'` — SQLAlchemy resolves a bare `postgresql://` scheme to the legacy `psycopg2` dialect, but this project depends only on `psycopg[binary]>=3.2,<4` (`backend/pyproject.toml`) and references `psycopg2` nowhere. Every other DSN producer in this repository (`docker-compose.yml`, `.github/workflows/ci.yml`, `backend/alembic.ini`, and this very deployment guide's own Part 17 command) already used the correct, driver-qualified `postgresql+psycopg://` scheme — only the two live secret *values* deviated, introduced when they were manually populated during an earlier real-Azure bootstrap phase, not a defect in any documented procedure. Corrected via a pure scheme-prefix replacement on the existing Key Vault values (username/password/host/port/database/query untouched). See `docs/cdd/CDD-071-Azure-DEV-PostgreSQL-DSN-Driver-Correction.md` for full evidence.
5. The Entra `tenant_id` custom-claims-provider backing Function and the underlying user→tenant sourcing design (above) are real, disclosed prerequisites, not solved by this phase.
6. ACR "immutable tags" are achieved procedurally (git-SHA tagging discipline + content-addressed digests), not via a separate ARM policy resource — no such declarative property was found/verified to exist, and one was not fabricated (see `modules/acr.bicep`'s comment history).
7. **Lifecycle state persistence (Noetva R4-DRG D1 / R4-I).** `lifecycle_table_write`/`lifecycle_table_insert` were previously defined but never invoked by any workflow — every lifecycle state transition (Start/Stop/Extend/Hold, and the restart-monitor's bounded-recheck memory) is now durably persisted through the governed `lifecycle_apply_transition`/`lifecycle_persist_metadata` wrappers, proven end-to-end against a fake Azure Table Storage backend (`validation/lifecycle_static_checks.py`'s orchestration checks) with no real Azure dependency. `lifecycle_table_read`'s exact distinction between a genuinely-missing row (safe, expected on first-ever Start) and every other read failure (fail closed) relies on Azure's documented `ResourceNotFound` error signal — the exact error text this fallback matches against has not yet been reconfirmed against a live Storage Table; do so at first real Azure execution, per Section 32's local-vs-Azure-runtime distinction.
