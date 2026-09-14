# CDD-071 — Azure DEV PostgreSQL DSN Driver Correction

**Status:** FROZEN
**Originating phase:** AZURE-DEV-POSTGRES-DSN-R9 (DRG only in this artifact)
**Amends:** nothing frozen in place. Complements CDD-067/068/069/070 (all still open, PRs #213–#220) by correcting a PostgreSQL DSN/DBAPI defect discovered during real Azure execution of AZURE-DEV-RUNTIME-CONTRACT-R8-I, after CDD-070's env-var-mapping correction made the real DSN actually reach the application for the first time. Does not reopen, edit, or supersede any of them.

**Scope:** the PostgreSQL connection-string **scheme** stored in exactly two live Azure Key Vault secret values (`ctec-database-url`, `ctec-migration-database-url`), plus one narrow documentation-content regression check. No application source, no Bicep module, no dependency, and no other secret is in scope.

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
| #219 | `azure/runtime-contract-r8-g` | `3507215c51d1820d44ab7cbc2fba15a070f8ae19` | OPEN |
| #220 | `azure/runtime-contract-r8-i` | `08a64b05917474cfa43c8ffdea022f231e9b4542` | OPEN |

CDD-067 SHA-256: `5b2b19e86122f8db896012d97e5f08214773a7699da31b25c08c8833634e1e23` — matches. CDD-068: `5f98c59ee4992ba80fad7e1dee6f20d27f1b27931f4adbefafcae597a5817b3c` — matches. CDD-069: `58569430e47c81f0a84ccd890350b48a4073755188992ce6a1faf02b11a00aa6` — matches. CDD-070: `aaa11e5a4e0827ff2e8ecd8724e0ca93d653ba4c8c8afa56ca0fd4cc3b47fccc` — matches.

Cumulative candidate: `main`→R5-I→R6-I→R7-I→R8-I is one linear chain, confirmed via `git merge-base`/`git log`. R9's implementation must reason against `08a64b05917474cfa43c8ffdea022f231e9b4542`.

## 2. R8 operational closure — re-confirmed, not reopened

Both R8/CDD-070 defects are independently re-confirmed fixed and remain so: real backend env names include `CTEC_DATABASE_URL`/`CTEC_RUNTIME_HANDOFF_KEY` (the broken hyphenated names are gone); the frontend revision is `Healthy`/`RunningAtMaxScale` (or `ScaledToZero` when idle) and its own `/health` route returns real external `200`. This artifact does not touch `container-app.bicep`, `container-apps-job-migration.bicep`, `resources.bicep`, or the frontend health route.

## 3. Real failure evidence (R9)

The second governed normal migration execution, `noetva-dev-eus2-migrate-y1wu6sa`, reached `Failed` with:

```
File ".../sqlalchemy/dialects/postgresql/psycopg2.py", line 697, in import_dbapi
    import psycopg2
ModuleNotFoundError: No module named 'psycopg2'
```

This is a materially different failure from the first execution (`noetva-dev-eus2-migrate-po08p2r`, which attempted `localhost`/`127.0.0.1`/`::1` before CDD-070). The traceback itself proves `CTEC_DATABASE_URL` was correctly delivered this time (Alembic's `env.py` guard fired and set `sqlalchemy.url` from it) — the failure occurs entirely at Python import time, before any TCP/TLS/authentication activity, because SQLAlchemy resolved the DSN's bare `postgresql://` scheme to the legacy `psycopg2` dialect module, and only `psycopg` (v3) is installed.

## 4. Product-wide PostgreSQL connection inventory (real, not assumed)

Searched the full cumulative candidate for every DSN producer/consumer. Result — **every authoritative source in this repository already uses the driver-qualified `postgresql+psycopg://` scheme**, with the sole exception of the two live Azure Key Vault values:

| Location | Scheme used |
|---|---|
| `docker-compose.yml` (local dev default `CTEC_DATABASE_URL`) | `postgresql+psycopg://` |
| `DOCKER_SMOKE_TEST.md` | `postgresql+psycopg://` |
| `backend/alembic.ini` (static/local fallback) | `postgresql+psycopg://` |
| `docs/cdd/CDD-059-...md` (prior, already-frozen CI/migration governance) | `postgresql+psycopg://` |
| `.github/workflows/ci.yml` (`CTEC_TEST_DATABASE_URL`, `CTEC_DATABASE_URL`) | `postgresql+psycopg://` |
| `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`, Part 17's own `az keyvault secret set` command for `ctec-database-url` (and the equivalent for `ctec-migration-database-url`) | `postgresql+psycopg://` **(already correct, as written)** |
| Live Azure Key Vault `ctec-database-url` | bare `postgresql://` **(defect)** |
| Live Azure Key Vault `ctec-migration-database-url` | bare `postgresql://` **(defect)** |

**Root cause of the Azure DSN producer (§9):** the deployment guide's own documented command was never wrong. During the earlier real-Azure bootstrap work (R6), the two live secret values were populated by direct operator/session `az keyvault secret set` invocations that used a bare `postgresql://` scheme instead of copying the guide's own already-correct `postgresql+psycopg://` command exactly. This is a one-time execution deviation from an already-correct, already-published procedure — not a defect in the procedure itself, and not a defect anywhere in source.

## 5. Producer→consumer matrix

| Context | Producer | Scheme | Consumer | SQLAlchemy API | Expected DBAPI | Installed DBAPI | Sync/async | Tested? | Working? | Canonical? |
|---|---|---|---|---|---|---|---|---|---|---|
| Local dev (Docker Compose) | `docker-compose.yml` default | `+psycopg` | Backend `create_database_engine` | `create_engine` | psycopg v3 | psycopg v3 | sync | Yes (smoke test doc) | Yes | Yes |
| CI | `.github/workflows/ci.yml` | `+psycopg` | Backend test suite, Alembic | `create_engine` | psycopg v3 | psycopg v3 | sync | Yes (real CI, passing) | Yes | Yes |
| Alembic static fallback | `backend/alembic.ini` | `+psycopg` | `alembic upgrade head` (local, no env override) | `create_engine` (via `engine_from_config`) | psycopg v3 | psycopg v3 | sync | Indirectly (CI) | Yes | Yes |
| Azure normal migration Job | live KV `ctec-migration-database-url` | bare (defect) | `alembic upgrade head` + inline seeders | `create_engine` | psycopg2 (wrong) | psycopg v3 only | sync | Real Azure (this session) | **No** | No |
| Azure backend Container App | live KV `ctec-database-url` | bare (defect) | `dependency_container.py` / `database.py` | `create_engine` | psycopg2 (wrong) | psycopg v3 only | sync | Not yet exercised for real | **No (structurally proven, §8)** | No |
| Azure bootstrap Job (CDD-068) | plain Bicep `@secure()` params, not a Key Vault DSN at all | n/a — raw `psql` via `run_db_bootstrap.sh`, not SQLAlchemy | `psql` CLI | n/a | n/a | n/a | n/a | Yes (real Azure, R6) | Yes | Out of scope — different mechanism entirely, unaffected |

## 6. Dependency inventory (traced, not inferred from one build log)

`backend/pyproject.toml`: `"psycopg[binary]>=3.2,<4"`, `"sqlalchemy>=2.0,<3"`, `"alembic>=1.14,<2"`. Zero references to `psycopg2` or `psycopg2-binary` anywhere in `backend/` (confirmed by repository-wide search). `asyncpg` is not declared or referenced anywhere. Locally installed and confirmed: `psycopg 3.3.4`, `sqlalchemy 2.0.43`, `alembic 1.18.4`; `import psycopg2` fails locally with the identical `ModuleNotFoundError` observed in the real Azure log. **`psycopg2` was never an intended dependency of this codebase at any point** — its absence in the real Azure image is not an oversight, it is the project's explicit, versioned intent.

## 7. SQLAlchemy dialect semantics (locally verified, matches real Azure evidence exactly)

```python
from sqlalchemy import make_url
make_url('postgresql://user:pass@host/db').get_dialect().__module__
# -> 'sqlalchemy.dialects.postgresql.psycopg2'
make_url('postgresql+psycopg://user:pass@host/db').get_dialect().__module__
# -> 'sqlalchemy.dialects.postgresql.psycopg'
```

This is the exact, deterministic mechanism SQLAlchemy 2.0.x uses to select a DBAPI from a URL scheme string alone — it precisely reproduces the real Azure traceback's own file path (`sqlalchemy/dialects/postgresql/psycopg2.py`). `postgresql+psycopg://` unambiguously selects the `psycopg` (v3) dialect; there is no ambiguity to resolve.

## 8. Alembic and backend canonical driver contract (traced through both, structurally identical)

- **Alembic:** `backend/alembic/env.py`'s `if settings.database_url: config.set_main_option("sqlalchemy.url", settings.database_url)`, feeding `engine_from_config(...)` → `create_engine(url, **options)` — synchronous SQLAlchemy 2.0 engine construction, dialect resolved purely from the URL scheme (§7).
- **Backend:** `backend/app/infrastructure/persistence/database.py`'s `create_database_engine` calls the identical `create_engine(settings.database_url, ...)` — the same synchronous SQLAlchemy 2.0 API, the same dialect-resolution rule.

**This structurally proves (not merely infers) that a bare `postgresql://` value in `ctec-database-url` would break the backend's real database-dependent path identically to how it broke migration** — the dialect-selection mechanism is a pure function of the URL scheme string, applied identically by both call sites; there is no backend-specific or migration-specific branch anywhere in this path. The R8 report's classification of this as "inferred" is now resolved to **structurally proven**.

## 9. Azure DSN producer (traced to its exact origin)

Confirmed by direct comparison (§4): the deployment guide's Part 17 already instructs `az keyvault secret set ... --name ctec-database-url --value "postgresql+psycopg://noetva_app:<postgres-app-password>@...` and the equivalent for `ctec-migration-database-url` — both already correct, unedited by any phase in this arc. The live Key Vault values diverge from this already-correct instruction only because of how they were actually populated during R6's real bootstrap execution. **No documentation or source correction is required to prevent recreating this defect on a future environment** — the existing, authoritative procedure, if followed exactly as written, already produces the correct scheme.

## 10. Options evaluated

- **Option A — canonical driver-qualified DSN (`postgresql+psycopg://`):** **SELECTED**, on overwhelming, multi-source precedent (§4/§5) — this is not a new design decision, it is re-affirming the scheme already used successfully in local dev, CI, Alembic's own static fallback, and the deployment guide's own text.
- **Option B — source-level normalization** (rewrite bare `postgresql://` to `+psycopg` inside application code): **rejected**. Given the producer (§9) requires no fix, this would be pure hidden magic solving a problem that does not exist at the source layer — it would silently mask a future genuine operator mistake instead of surfacing it, and no other DSN in this codebase needs such a rewrite (§4).
- **Option C — engine-level driver selection** (force the DBAPI independently of the URL): **rejected** as redundant complexity layered on top of Option A for no benefit — the URL scheme is already the correct, standard, portable place to express this.
- **Option D — install `psycopg2`/`psycopg2-binary`:** **rejected** — directly contradicts the project's own explicit, versioned dependency declaration (`psycopg[binary]>=3.2,<4`, §6), would introduce a second, redundant, unused legacy driver with no basis anywhere in the existing codebase, and would only paper over the real defect (the DSN scheme) rather than correct it.
- **Option E — Key-Vault-only value correction:** justified here specifically because §9 proves the producer needs no fix — this is not "patching a symptom while leaving a broken producer behind," because there is no broken producer. Combined with Option A, this is the complete, sufficient, smallest correction.

## 11. Password / URL-encoding findings (adversarially checked)

The correction is a **pure scheme-prefix string replacement** — `postgresql://` → `postgresql+psycopg://` on the existing secret value — touching no other character of the string. Independently re-confirmed (read-only, values never printed): both live DSNs already parse correctly via `urllib.parse.urlsplit` into the expected `scheme`/`hostname`/`port`/`username`/`path`/`query`, with exactly one literal `@` separating userinfo from host (checked in R7-I) — proving the existing password-encoding (`urllib.parse.quote(..., safe='')`, applied when these values were originally constructed in R6) is already correct and RFC 3986-valid. A prefix-only replacement cannot alter or reintroduce any encoding defect in the untouched remainder of the string — there is no latent encoding risk to resolve.

## 12. TLS/SSL findings

Both DSNs' query string is `sslmode=require` (confirmed present, non-secret, read-only). Independently confirmed (Microsoft/psycopg ecosystem): psycopg v3 maintains libpq-compatible connection parameters, including `sslmode`, with identical semantics to psycopg2 — the scheme change affects only DBAPI selection, not any TLS/certificate/query-parameter behavior. `require_secure_transport` on the PostgreSQL Flexible Server itself (already governed, unmodified) is untouched. No weakening of TLS or private-networking posture results from this correction.

## 13. The two Key Vault values, kept distinct

`ctec-database-url` (application role, `noetva_app`, DML-only) and `ctec-migration-database-url` (migration role, `noetva_migrate`, DDL+DML) both require the identical scheme correction, applied independently to each value — their distinct usernames, privileges, and underlying passwords are otherwise completely untouched. Neither is renamed, collapsed, or cross-substituted.

## 14. Intermediate password secrets, unaffected

`postgres-app-password`/`postgres-migrate-password` (and `postgres-admin-password`) remain exactly what CDD-067/068 froze: intermediate, operator-facing records, never directly Bicep-consumed. This correction does not read, derive from, or regenerate them — the corrected DSN values are produced by taking the *existing* live DSN strings and replacing only their scheme prefix, not by reconstructing them from these intermediate secrets. CDD-067/068's governance stands unchanged; no evidence here requires revisiting it.

## 15. Exact Key Vault secret-value impact (governed explicitly, values never disclosed)

**Authorized:** create a new Key Vault **version** of `ctec-database-url` and of `ctec-migration-database-url`, each equal to the current live value with only its leading `postgresql://` replaced by `postgresql+psycopg://` — no other character changed. The update procedure must: read the existing value only into a local, unprinted variable within one bounded operation; perform the substitution in-process (never re-typing or reconstructing the password); write the result via `az keyvault secret set` (which creates a new version, never overwrites/deletes the prior one); verify the write by parsing only the new version's non-secret structural properties (scheme, hostname, port, path, query-parameter **names**) — never the userinfo. No other secret name is touched.

## 16. Key Vault version/rollback model

`az keyvault secret set` against an existing secret name always creates a new version; Azure Key Vault never deletes or disables a prior version as a side effect of this operation (confirmed: this is Key Vault's fundamental versioning behavior, not a soft-delete-adjacent one-way action). The prior (defective-scheme) version remains listable via `az keyvault secret list-versions` and recoverable if ever needed — this correction requires no purge, no explicit version disable, and introduces no rollback risk beyond "point the reference back," which the versionless reference already makes trivial (the newest version is always what resolves).

## 17. Backend secret-refresh behavior (real Azure documentation, not assumed)

Confirmed (Microsoft Learn, "Manage secrets in Azure Container Apps"): with a **versionless** Key Vault secret URI — which is exactly what `container-app.bicep`'s `keyVaultUrl: '${keyVault.outputs.keyVaultUri}secrets/<name>'` construction already uses, unmodified by this artifact — Container Apps automatically detects a new secret version and restarts any active revision referencing it in an environment variable **within 30 minutes**; for immediate pickup, the documented mechanism is to either explicitly restart the existing active revision, or deploy a trivial new revision. New revisions are **not** generated merely by a secret changing — an explicit restart or redeploy action is required for immediate effect.

## 18. Migration Job secret-refresh behavior

Each Container Apps Job **execution** is a fresh container instantiation with no persistent "revision" concept analogous to a Container App — secret references are resolved at that fresh start. Triggering one new migration execution after the Key Vault values are corrected is expected to resolve the corrected secret without any separate redeploy step. This is the natural, lower-risk case (no explicit restart action is even needed) and is the first thing the real-Azure VM phase must prove or refute with direct evidence.

## 19. Image rebuild decision

**No image rebuild for either backend or frontend.** This correction is a Key Vault value change plus one documentation-content regression test — zero application source, zero Dockerfile, zero dependency file is touched. The existing, already-verified `linux/amd64` digest-pinned images (`sha256:3c7e46ac...` backend, `sha256:0d82d2ad...` frontend) remain valid and unchanged.

## 20. Migration re-entry safety (both prior failures proven pre-SQL)

- `noetva-dev-eus2-migrate-po08p2r` (R7/R8): failed at TCP connection establishment, before any SQL.
- `noetva-dev-eus2-migrate-y1wu6sa` (R8): failed at Python DBAPI import time, inside `create_engine()`, before any TCP connection attempt of any kind — strictly earlier in the sequence than the first failure.

Neither execution could have issued a single SQL statement against any database. **A third execution, after this correction, starts from the real, completely untouched, pre-migration schema state** — safe, with zero risk of partial or conflicting state from either prior attempt. Both failed executions remain preserved; this artifact does not delete or reset them.

## 21. R7 alert preservation

The corrected `noetva-dev-eus2-alert-migration-job-failed` (CDD-069, unmodified) now has two real failed executions in its observation history. This artifact does not suppress, reset, or reconfigure it in any way. A third, successful execution will naturally produce a `state=Failed` count of zero in its own evaluation window, which — per the alert's already-frozen semantics (CDD-069 §8) — resolves the condition on its own; no manual alert manipulation is authorized or needed.

## 22. Backend DB-connectivity verification architecture (narrowest governed mechanism, no OIDC weakening)

`GET /health` remains intentionally shallow (CDD-070 §11, unchanged) and is not sufficient proof. No unauthenticated, DB-dependent backend HTTP endpoint exists (by design — every DB-backed capability sits behind the OIDC-protected API surface), and this artifact does not authorize creating one. The narrowest available, already-existing, non-HTTP mechanism: `az containerapp exec` into the backend's running replica (using the Container App's own already-granted identity and already-resolved environment — no new endpoint, no new credential, no bypass of any auth boundary) to invoke the backend's own already-existing `create_database_engine`/`database_is_healthy` functions (`backend/app/infrastructure/persistence/database.py`) directly — proving real engine construction (correct scheme/driver) and a real `SELECT 1` round-trip (correct private-network path, correct TLS, correct `noetva_app` role authority) without exercising any business table, any OIDC-protected route, or any interactive login. Full authenticated business-workflow proof remains explicitly classified as pending Entra configuration — a separate, later, already-anticipated phase.

## 23. Tenant-bootstrap ordering (unchanged, reaffirmed)

Migration success → schema verification → `noetva-dev-tenant` bootstrap remains required, in that order. Not performed during this DRG.

## 24. Exact implementation paths (ceiling)

| # | Path | Change |
|---|---|---|
| 1 | `infra/azure/validation/static_architecture_checks.py` | MODIFY — add a regression check asserting every `az keyvault secret set ... --name ctec-database-url`/`ctec-migration-database-url` example command in the deployment guide uses `postgresql+psycopg://`, never bare `postgresql://` |
| 2 | `infra/azure/README.md` | MODIFY — record this defect/correction in "Known residual risks," matching the CDD-069/070 precedent of documenting real-Azure-discovered-and-closed items |

```
CREATE = 0
MODIFY = 2
DELETE = 0
TOTAL  = 2
```

No Bicep module, no backend/frontend source, no dependency file, no Dockerfile is authorized. The deployment guide itself needs no correction (§9 — it is already correct) and is therefore **not** in this ceiling.

**Separately, explicitly governed (not a "source path"):** exactly two Key Vault secret-value updates, per §15 — `ctec-database-url` and `ctec-migration-database-url`, scheme-prefix-only.

## 25. Static regression architecture

A literal grep for the correct scheme string in the deployment guide's own example commands is appropriate here specifically because there is no executable "producer" script to structurally validate (§9) — the producer is documentation text, and the regression this must prevent is a future *editor* of that documentation reintroducing a bare `postgresql://` example. The check additionally re-confirms (already covered by CDD-070's existing check, re-verified not re-authored) that `backend/app/core/config.py` still declares a `database_url` field reachable via `CTEC_` + fieldname, so the two checks together continue to prove the full chain: documented-producer-correctness (this artifact) plus wiring-correctness (CDD-070, unchanged). Real-Azure verification (§26) remains mandatory regardless — a static check on documentation text cannot prove what Azure actually stores or what SQLAlchemy actually resolves at runtime.

## 26. Real-Azure VM requirements (for the future implementation phase, not satisfied by this DRG)

1. Key Vault value update performed for both `ctec-database-url` and `ctec-migration-database-url`, per §15 — no value ever printed.
2. Each corrected value's scheme independently confirmed `postgresql+psycopg` via read-only structural parsing (never credentials).
3. Host remains the real Azure PostgreSQL FQDN (`noetva-dev-eus2-pg.postgres.database.azure.com`) for both.
4. Application (`noetva_app`) and migration (`noetva_migrate`) usernames remain distinct in their respective DSNs.
5. `sslmode=require` (or equivalent) preserved in both.
6. Required secret refresh completed — migration Job needs no explicit action (§18); backend Container App explicitly restarted or redeployed to pick up the new version within the immediate window (§17), not left to the 30-minute automatic window if verification is being performed live.
7. Migration Job's real env-var name remains `CTEC_DATABASE_URL` (CDD-070, re-confirmed unregressed).
8. A third normal migration execution triggered; reaches `Succeeded`.
9. No `ModuleNotFoundError: No module named 'psycopg2'` in its logs.
10. No `localhost`/`127.0.0.1`/`::1` connection attempt in its logs.
11. `alembic upgrade head` completes; both governed seeders complete.
12. Required application schema/tables independently confirmed to exist.
13. `noetva-dev-tenant` bootstrapped, idempotently, exactly once.
14. Backend real database connectivity proven via §22's mechanism — engine construction succeeds, `SELECT 1` succeeds — without touching business data or bypassing OIDC.
15. Application authority remains non-DDL/non-ADMIN throughout (`noetva_app` is DML-only by construction, unchanged).
16. PostgreSQL `publicNetworkAccess` remains `Disabled`.
17. Frontend R8 health remains `Healthy` and externally reachable (regression check).
18. R7's alert remains correctly configured, unmodified, and is observed to naturally reflect the new successful execution.
19. No secret leakage (bounded audit, as every prior phase).
20. No Azure deletion of any kind.

## 27. Security invariants (unchanged, reaffirmed)

PostgreSQL `publicNetworkAccess` stays `Disabled`; no public firewall/VM/Bastion/VPN/new NSG; no ADMIN credential in migration or backend; bootstrap Job stays dormant; migration and application authority remain structurally separate; Key Vault RBAC is unchanged (no new role, no new identity); digest pinning and `linux/amd64` compatibility are preserved (no rebuild, §19); OIDC `scp`/`noetva_tenant_id` claim configuration is untouched.

## 28. Implementation-phase Azure mutation authorization (explicit)

R9-I **is** authorized to: modify the two paths in §24; create new Key Vault secret **versions** (never delete/overwrite in place, never disable prior versions) for `ctec-database-url` and `ctec-migration-database-url` exactly as §15 describes; restart or redeploy the backend Container App if required for immediate secret pickup; trigger one new normal migration Job execution; verify schema; bootstrap `noetva-dev-tenant`; perform backend DB verification per §22. R9-I is **not** authorized to: mutate Entra, mutate Cloudflare, mutate GitHub repository/environment/OIDC settings, merge any PR, or delete any Azure resource.

## 29. STOP conditions (all evaluated during this DRG; none triggered)

- The canonical intended DBAPI **can** be established (§6/§7 — `psycopg` v3, unambiguously, by explicit project dependency declaration) — not triggered.
- Backend and migration do **not** require incompatible drivers — both use the identical `create_engine` call path (§8) — not triggered.
- Safe DSN construction **is** established — pure prefix replacement, adversarially checked (§11) — not triggered.
- Password URL encoding is **not** unsafe/unresolved — proven already-correct and untouched by this change (§11) — not triggered.
- TLS semantics are **not** weakened (§12) — not triggered.
- The solution does **not** require ADMIN authority broadening — not triggered.
- The solution does **not** require public PostgreSQL access — not triggered.
- The solution does **not** require deleting any failed execution (§20/§21) — not triggered.
- Key Vault mutation **can** be performed without secret exposure (§15 — read-into-variable, in-process substitution, never printed) — not triggered.
- Migration re-entry **is** proven safe (§20 — both failures occurred strictly pre-SQL) — not triggered.
- The source path ceiling **is** bounded (§24 — 2 paths, both MODIFY, zero new resource/dependency) — not triggered.
- Real Azure evidence **supports** (does not contradict) this architecture — every claim in §4 through §8 is independently, locally, and/or real-Azure verified, not assumed — not triggered.

No STOP condition fired. This correction is safe to freeze and hand to an implementation phase.

---

**Freeze evidence index:** the SQLAlchemy dialect-resolution behavior (§7) and the dependency inventory (§6) were verified directly against the locally-installed package versions matching the real Azure image; the product-wide DSN inventory (§4) was a real repository-wide search, not a sample; the Key-Vault-secret-refresh behavior (§17) was confirmed against Microsoft's own published Container Apps documentation; the psycopg v3 / libpq `sslmode` compatibility (§12) was confirmed against publicly available psycopg/PostgreSQL documentation. No live secret value was printed, retrieved for display, or reconstructed from scratch at any point in this DRG — only parsed, read-only, for its non-secret structural fields.
