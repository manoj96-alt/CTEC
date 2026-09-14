# CDD-072 — Azure DEV Key Vault Secret Refresh Correction

**Status:** FROZEN
**Originating phase:** AZURE-DEV-KEYVAULT-SECRET-REFRESH-R10 (DRG only in this artifact)
**Amends:** nothing frozen in place. Complements CDD-067/068/069/070/071 (all still open, PRs #213–#222) by establishing the deterministic operational mechanism that makes the already-correct current Key Vault secret versions (frozen by CDD-071) actually reach the normal migration Job and the backend Container App. Does not reopen, edit, or supersede any of them, and does not reopen the PostgreSQL DSN architecture itself.

**Scope:** the Azure-operational refresh mechanism for versionless Key-Vault-backed secret references consumed by the normal migration Job and the backend Container App. No source file, no Bicep module, no Key Vault value, and no database authority is in scope.

---

## 1. Authoritative baseline at freeze

Main SHA: `09acfeb77a258ff8a83a48a8fc4105279456f50a` — matches. Open PR stack, every head re-derived live:

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
| #221 | `azure/postgres-dsn-r9-g` | `6e45f3b5d3783439409eb1fe2fa70d38207861bd` | OPEN |
| #222 | `azure/postgres-dsn-r9-i` | `3444d35989c37eee3f57e6b98e65b3103284159b` | OPEN |

CDD-067 SHA-256: `5b2b19e86122f8db896012d97e5f08214773a7699da31b25c08c8833634e1e23` — matches. CDD-068: `5f98c59ee4992ba80fad7e1dee6f20d27f1b27931f4adbefafcae597a5817b3c` — matches. CDD-069: `58569430e47c81f0a84ccd890350b48a4073755188992ce6a1faf02b11a00aa6` — matches. CDD-070: `aaa11e5a4e0827ff2e8ecd8724e0ca93d653ba4c8c8afa56ca0fd4cc3b47fccc` — matches. CDD-071: `18dae1f04fc23f81878491acd0aca882655a2756d0805d31a4057e80ddd9ba04` — matches.

Cumulative candidate: `main`→R5-I→R6-I→R7-I→R8-I→R9-I is one linear chain, confirmed. R10's implementation reasons against `3444d35989c37eee3f57e6b98e65b3103284159b`, with **zero further source changes authorized or required** (§17).

## 2. Real R9 failure evidence (re-stated, not reopened)

The third migration execution, `noetva-dev-eus2-migrate-6e8ys7s`, failed identically to the second (`ModuleNotFoundError: No module named 'psycopg2'`, same dialect module path) — **after** CDD-071's Key Vault correction had already been written and independently verified live and correct. This proves the defect is not the DSN value; it is the *refresh/materialization* path between a new Key Vault secret version and the resource that consumes it.

## 3. Proof the current Key Vault values are already correct (not reopened)

Independently re-confirmed, read-only, without printing either value: the current/latest version of `ctec-database-url` (`.../944a683c4e344cef80d03e3b3fdc0e6a`, created `2026-09-12T21:27:50Z`) and `ctec-migration-database-url` (`.../d9eacbb339db4aafb39717ef067410d0`, created `2026-09-12T21:27:54Z`) are exactly the versions CDD-071's implementation created. No new version exists or is needed. **The canonical DSN architecture (`postgresql+psycopg://`, psycopg v3, no source normalization, no image rebuild) stands exactly as CDD-071 froze it.**

## 4. Container Apps *Job* Key Vault refresh semantics (documented, and by absence)

Microsoft's own "Manage secrets in Azure Container Apps" reference (fetched directly, in full) documents secret rotation exclusively in terms of **revisions**: *"Secrets are scoped to an application, outside of any specific revision... An updated or deleted secret doesn't automatically affect existing revisions... When a secret is updated... deploy a new revision [or] restart an existing revision."* The one explicit rotation clause — *"the app automatically retrieves the latest version within 30 minutes... any active revisions that reference the secret in an environment variable is automatically restarted"* — is written entirely in revision-and-restart terms. **Container Apps Jobs have no "revision" concept and no restart primitive at all** — confirmed directly against the real Azure CLI surface: `az containerapp job --help` exposes only `create | delete | list | show | start | stop | update` (plus `execution`/`identity`/`logs`/`registry`/`replica`/`secret` subgroups) — no `restart`, no `revision` subgroup of any kind. The document's own "Permissions for managing secrets" section separately confirms Jobs are a genuinely distinct secret model (`Microsoft.App/jobs/listSecrets/action`, distinct built-in roles from container apps) — not merely an omission, a structurally different resource. **Conclusion: the documented 30-minute-auto-refresh-plus-restart mechanism is a Container-App-revision-specific behavior with no proven Job equivalent; real R9 evidence (§2) is consistent with Jobs not automatically re-resolving a versionless Key Vault reference at each fresh execution.**

## 5. Container *App* (non-Job) Key Vault refresh semantics, further caveated by real-world evidence

The same document states the 30-minute/auto-restart behavior for ordinary Container Apps. However, a real, publicly reported defect — [microsoft/azure-container-apps#856](https://github.com/microsoft/azure-container-apps/issues/856), "Change of Secrets in Key Vault are not reflected in Azure Container Apps after the active revision is restarted" — shows this mechanism is **not reliable even for its documented case**: a user found that restarting the active revision did *not* pick up a new secret version, and the workaround that actually worked was to *redeploy through the pipeline* (i.e., a full declarative template redeployment), not a mere restart. **This directly means CDD-070's stated assumption (revision restart gives immediate, guaranteed pickup) cannot be relied upon as fully deterministic** — R9's backend restart (§ CDD-071 report, item U) completed successfully and the backend reported healthy afterward, but this DRG treats whether it actually refreshed the DSN as **unproven**, not confirmed, consistent with the real GitHub evidence that restart alone is not guaranteed.

## 6. Real resource reference form (read-only, confirmed)

Both the backend Container App's and the migration Job's Key Vault secret entries use the versionless form `https://noetva-dev-eus2-kv.vault.azure.net/secrets/<name>` — no `<32-digit-hex-version-id>` suffix — confirmed directly from each resource's live `properties.configuration.secrets[].keyVaultUrl` (names/URLs only, no values). This matches `container-app.bicep`/`container-apps-job-migration.bicep`'s own Bicep construction (`'${keyVault.outputs.keyVaultUri}secrets/<name>'`), unmodified by CDD-070/071 and not touched by this artifact.

## 7. Cache/materialization model (evidence-based, not speculative)

No Microsoft documentation states Container Apps Jobs re-resolve Key Vault references at every fresh execution; the only documented resolution/refresh point for *any* Container Apps resource type is tied to the resource's own template/revision reconciliation (ARM-level create/update), not to an ephemeral execution/replica start. Real R9 evidence (§2) is consistent with this: the Job's secret value appears to be materialized once, at the Job resource's own last template reconciliation (its most recent `az deployment sub create` in R9-I, which itself pre-dated the Key Vault correction), and reused unchanged across fresh executions until the Job resource's template is itself reconciled again.

## 8. Job refresh options evaluated

- **Option A — wait for documented automatic refresh:** rejected as the sole mechanism — no documentation establishes this applies to Jobs at all (§4); waiting an undocumented, unproven interval is not deterministic.
- **Option B — explicit Job update/revision/template update using the same declarative configuration:** a real, existing Azure CLI primitive exists for this (`az containerapp job update`, e.g. re-supplying the same `--image` value) — a genuine ARM PATCH that reprocesses the Job's template. Viable, but narrower in scope than Option C and not the mechanism the one real, documented community fix (§5) actually used.
- **Option C — full application-tier Bicep redeployment with unchanged logical configuration:** **SELECTED.** This is exactly the mechanism the one real, documented, working fix for this class of defect used (§5, "redeploy through the pipeline") — a declarative, idempotent, already-proven-safe-in-this-engagement operation (every phase in this arc has already run this exact `az deployment sub create` with `deployApplicationTier=true` and reviewed it via `what-if` first), reprocessing every resource's template — including the migration Job's and the backend's secret arrays — in one bounded, observable action.
- **Option D — targeted no-op Job update (Option B), if documented to force re-resolution:** not separately selected — no documentation confirms it forces secret re-resolution specifically (only the community fix in §5 is confirmed to work, and that was a full redeploy); using the same broader, already-proven mechanism (C) for both Job and backend is simpler and no less safe.
- **Option E — recreate/delete the Job:** **rejected outright**, per this DRG's own explicit prohibition and because it is unnecessary — nothing here requires destroying and recreating a governed resource.
- **Option F:** none identified as more directly evidenced than C.

## 9. Rejected Job refresh mechanisms

Options A, D, and E, per §8. Option B (targeted `az containerapp job update`) is not rejected as unsafe, only as strictly narrower than Option C for no proven additional benefit — Option C already reprocesses the Job's template as a subset of its own effect.

## 10. Backend refresh options evaluated

- **Option A — revision restart:** already attempted in R9-I; completed successfully, but per §5's real-world evidence this is **not proven reliable** for Key Vault secret refresh specifically. Not solely relied upon going forward.
- **Option B — new revision:** would require a template-level change to force a new revision (Container Apps documentation: *"New revisions don't get generated through adding, removing, or changing secrets"* — a secret change alone does not trigger one). Achievable via a trivial no-op parameter nudge, but Option D achieves the same effect with a mechanism already proven necessary for the Job.
- **Option C — Container App configuration update:** equivalent in kind to Option B; not separately selected.
- **Option D — application-tier Bicep reapply:** **SELECTED**, for the same reason as the Job (§8/§5) — this is the one mechanism with a real, documented, working precedent, and is being performed anyway for the Job's sake, so applying it to both resources in the same redeploy is the smallest total operation.
- **Option E — wait for automatic refresh:** rejected as non-deterministic, per §5.
- **Option F:** none more directly evidenced.

## 11. Rejected backend refresh mechanisms

Options A (alone, insufficiently proven per §5), B/C (narrower, no added benefit over D), E (non-deterministic), per §10.

## 12. Can refresh freshness be proven before triggering execution?

**No — stated honestly, not assumed away.** Key Vault secret *values* are opaque to Bicep/ARM's own diffing (`what-if` cannot show a difference in a value it never displays or compares); a redeploy with fully unchanged logical parameters will show the same benign zero-substantive-change `what-if` result already established safe in every prior phase, regardless of whether the underlying secret materialization actually refreshes. There is no non-destructive, non-migration-triggering way to directly observe the Job's internally cached secret value. **The strongest available proof is the redeploy itself (the one real, documented, working mechanism, §5/§8) plus exactly one controlled migration execution afterward, whose logs directly reveal which DSN was actually used** (a `psycopg2` `ModuleNotFoundError` means stale; a real connection attempt to the private PostgreSQL host means fresh) — this is frozen as the real-Azure VM proof (§20), not a static/pre-execution guarantee.

## 13. Version-pinning considered and rejected as the general solution

Pinning the Key Vault secret references to a specific version GUID would trivially guarantee determinism for *this one* update, but was evaluated and **rejected as the general architecture**: it would require a Bicep-level change (adding a version-tracking parameter or hardcoding a version GUID) every time any of these secrets rotates in the future — directly conflicting with Noetva's own established start/stop dormancy model (secrets may need rotation across a stop/start cycle without a source change) and with CDD-067/068's own intent that `postgres-app-password`/`postgres-migrate-password`-derived values remain operator-rotatable without a source PR each time. The versionless reference is the architecturally correct choice; what was missing was not version-pinning but the deterministic *refresh-triggering operation*, now frozen (§8/§10).

## 14. Future secret-rotation operational contract (frozen, durable)

**For any future rotation of a versionless Key-Vault-backed secret consumed by the normal migration Job or the backend Container App** (database credentials, `ctec-runtime-handoff-key`, or any future addition following the same `keyVaultSecretRefs`/`secretEnvVars` pattern): after writing the new Key Vault secret version, the operator/session **must** perform a full application-tier Bicep redeployment (`what-if` first, then real, exactly as every phase in this arc already does) before triggering any workload that depends on the rotated value. A mere revision restart or a wait is **not** sufficient and must not be relied upon alone, per the real evidence in §5. This is now the durable Noetva Azure operational rule for this class of change — not merely a one-time fix for this DSN correction.

## 15. Backend scale-to-zero verification mechanism (frozen)

R9 could not complete `az containerapp exec`-based DB verification because the backend's replica (at `backendMinReplicas: 0`) scaled back down before `exec` could attach, twice, even immediately after waking it with an HTTP request. **Selected mechanism:** since the application-tier redeploy (§10) is already required for the refresh itself, that same redeploy temporarily sets the already-existing, already-governed `backendMinReplicas` parameter from its current value (`0`) to `1` — guaranteeing at least one replica is always running for the duration of the verification window — then a second, immediately-following redeploy restores it to `0`, with explicit before/after confirmation. This introduces **zero new parameters, zero new mechanism, and zero permanent cost increase**: `backendMinReplicas` is an existing top-level parameter, already `0` for every non-prod environment, and this is a bounded, two-redeploy operation, not a permanent configuration change. No new debug endpoint, no OIDC weakening, no exposure of database state — verification reuses the backend's own already-existing `create_database_engine`/`database_is_healthy` functions via `az containerapp exec`, exactly as CDD-071 §22 already froze.

## 16. Lifecycle/dormancy impact

Zero. The `backendMinReplicas=1` window is temporary and explicitly restored to `0` within the same governed operation, verified restored (§20 item 19). No VM/Bastion/VPN is introduced. No recurring cost results — Container Apps billing while `minReplicas=1` only accrues for the bounded verification window, not indefinitely, and this artifact requires that window be as short as the verification itself takes.

## 17. Source-change requirement: NONE

This artifact requires **zero source modifications** — no Bicep module, no application code, no dependency, no Dockerfile, no documentation content beyond this CDD itself. The mechanism is exactly two invocations of the already-existing, already-governed `az deployment sub create` (same command every prior phase has used), differing only in the already-existing `backendMinReplicas` parameter's value (temporarily `1`, then restored to `0`), plus the already-existing `az containerapp job start` and `az containerapp exec` CLI commands. This is a pure Azure-operational correction.

## 18. Exact implementation paths

None. `CREATE=0, MODIFY=0, DELETE=0, TOTAL=0` for source. (No static regression architecture is required either — there is no source behavior to regress; the "regression" this artifact guards against is purely operational and is addressed by freezing the durable rule in §14, which the deployment guide's own already-existing Part 23/30/31 redeploy-first discipline already structurally enforces for every future phase in this arc.)

## 19. Migration re-entry safety (third execution also proven pre-SQL)

`noetva-dev-eus2-migrate-6e8ys7s`, like both prior failures, failed at Python DBAPI-import time inside `create_engine()`, strictly before any SQL or network activity — confirmed by the identical traceback shape and file path as the second failure. **A fourth execution, after the deterministic redeploy-based refresh (§8/§10), is safe** — all three prior failures are proven to have issued zero SQL against any database; there is no partial or conflicting state of any kind to account for. All three failed executions remain preserved, untouched, by this artifact.

## 20. Real-Azure VM requirements (for the future implementation phase, not satisfied by this DRG)

1. The current, already-correct Key Vault versions (§3) remain unchanged; no new version is created.
2. Application-tier redeployment (`what-if` first) performed with `backendMinReplicas` temporarily `1`, all other parameters unchanged from the last known-good deployment.
3. Migration Job authority re-confirmed unchanged (`ctec-migration-database-url`, `id-migration`, no ADMIN reference) after the redeploy.
4. Migration Job's env-var name confirmed still `CTEC_DATABASE_URL`.
5. Exactly one new (fourth) migration execution triggered — no automatic further retry regardless of outcome.
6. Fourth execution reaches `Succeeded`.
7. Its logs show the `psycopg` (v3) dialect module loading, not `psycopg2`.
8. No `ModuleNotFoundError: No module named 'psycopg2'`.
9. No `localhost`/`127.0.0.1`/`::1` connection attempt.
10. `alembic upgrade head` completes; both governed seeders complete.
11. Required application schema independently verified to exist.
12. `noetva-dev-tenant` bootstrapped, idempotently, exactly once.
13. Backend DB verification (CDD-071 §22 mechanism, via `az containerapp exec` during the temporary `minReplicas=1` window) succeeds: engine construction succeeds, `database_is_healthy` returns true, using the application-only (`noetva_app`) authority — no ADMIN, no DDL.
14. The temporary `backendMinReplicas=1` is explicitly reverted to `0` via a second redeploy, and confirmed restored.
15. Frontend remains `Healthy` and externally reachable at `/health` throughout (regression check, no frontend change made).
16. R7's alert remains unmodified and correctly configured; its history (now potentially including a successful execution) is not manipulated.
17. PostgreSQL `publicNetworkAccess` remains `Disabled`.
18. No secret leakage across any step (bounded audit, as every prior phase).
19. No Azure resource deletion of any kind.

## 21. Security invariants (unchanged, reaffirmed)

PostgreSQL `publicNetworkAccess` stays `Disabled`; no firewall/VM/Bastion/VPN/new NSG; no ADMIN authority anywhere; bootstrap Job stays dormant; migration/application authority remain structurally separate; all six Key Vault secret names and their current correct versions are preserved (no new version, no deletion); digest-pinned images are unchanged (no rebuild — nothing here touches an image); `linux/amd64` compatibility is preserved by extension; OIDC `scp`/`noetva_tenant_id` claim configuration is untouched by a parameter-identical redeploy.

## 22. Implementation-phase Azure mutation authorization (explicit)

R10-I **is** authorized to: perform the application-tier redeployment described in §10/§15 (temporarily `backendMinReplicas=1`, then a second redeploy restoring `0`); trigger exactly one new (fourth) normal migration execution; verify schema; bootstrap `noetva-dev-tenant`; perform backend DB verification via `az containerapp exec` during the temporary window. R10-I is **not** authorized to: create any new Key Vault secret version; change any DSN value; make any source, dependency, or image change; mutate Entra, Cloudflare, or GitHub repository/environment/OIDC settings; merge any PR; or delete any Azure resource.

## 23. STOP conditions (all evaluated during this DRG; none triggered)

- Microsoft/real-Azure evidence **can** establish a deterministic refresh method (§5/§8 — the community-confirmed "redeploy through the pipeline" fix) — not triggered.
- The refresh does **not** require deleting/recreating any governed resource (§8, Option E explicitly rejected) — not triggered.
- The refresh does **not** require changing the already-correct DSNs (§3, untouched) — not triggered.
- The refresh does **not** require installing `psycopg2` — not triggered.
- The refresh does **not** require public PostgreSQL access — not triggered.
- The refresh does **not** broaden database authority (§21) — not triggered.
- Backend verification does **not** require permanent `minReplicas > 0` — the window is explicitly temporary and restored (§15/§20 item 14) — not triggered.
- The fourth migration execution **is** proven safe (§19 — all three prior failures strictly pre-SQL) — not triggered.
- Secret freshness **is** addressed deterministically, with the honest caveat that it can only be proven by the redeploy-plus-one-execution sequence itself, not in advance (§12) — not triggered.
- The source path ceiling **is** bounded — it is zero (§17/§18) — not triggered.
- Real evidence does **not** contradict CDD-071's canonical DSN contract (§3, reaffirmed) — not triggered.

No STOP condition fired. This correction is safe to freeze and hand to an implementation phase.

---

**Freeze evidence index:** the Container Apps secret-management reference was fetched and read in full directly from Microsoft Learn; the real-world revision-restart unreliability was confirmed via a live, public GitHub issue on `microsoft/azure-container-apps`; the absence of a Job-level restart primitive was confirmed directly against the real, installed Azure CLI's own `az containerapp job --help` output; the current Key Vault version metadata was read live, non-secretly, immediately before writing this artifact.
