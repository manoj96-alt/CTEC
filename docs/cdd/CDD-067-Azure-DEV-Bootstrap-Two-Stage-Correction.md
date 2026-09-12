# CDD-067 — Azure DEV Bootstrap Two-Stage Correction

**Status:** FROZEN
**Originating phase:** AZURE-DEV-BOOTSTRAP-R5 (DRG → I → VM)
**Scope:** Corrects two real, first-time-discovered Azure bootstrap defects (an invalid placeholder image reference, and a Key-Vault-secret/Container-App circular dependency) plus one previously-undetected Bicep/documentation naming mismatch, all found only by a genuine `az deployment sub create` attempt against real Azure — none was catchable by Bicep build, lint, or `what-if`. Governs the corrected two-stage (`foundation` / `application`) Pass-1 bootstrap sequence, the exact secret inventory, and the safe convergence path from the current, real, partially-deployed `rg-noetva-dev`.

---

## 1. Authoritative baseline at freeze

Main SHA: `09acfeb77a258ff8a83a48a8fc4105279456f50a` — independently re-verified against `origin/main` and GitHub `main`, unchanged since the failed deployment attempt.

## 2. Real Azure failure evidence (the actual, not hypothetical, trigger for this artifact)

Deployment `noetva-dev-pass1-20260912T084734`, subscription `2aca2d95-0ac5-4dd6-b081-3822ee294a70` ("Noetva NonProd"), tenant `f111b68a-49a0-4fca-b249-cb774d866c18`, region `eastus2`, resource group `rg-noetva-dev`, ran against this exact source SHA and **failed**. Independently re-confirmed via `az deployment operation group list --resource-group rg-noetva-dev --name noetva-dev-resources`: three sub-deployments failed — `frontend-app`, `backend-app`, `migration-job`.

**Verbatim ARM error, frontend-app:**
> `InvalidParameterValueInContainerTemplate` — *"Field 'template.containers.noetva-dev-eus2-frontend.image' is invalid... could not parse reference: REPLACE_AT_DEPLOY_TIME_WITH_DIGEST_REFERENCE."*

**Verbatim ARM error, backend-app:**
> *"Unable to fetch secret 'ctec-database-url' using Managed identity .../id-backend... Unable to fetch secret 'ctec-runtime-handoff-key' using Managed identity .../id-backend."*

**Verbatim ARM error, migration-job:**
> *"Unable to fetch secret 'ctec-database-url' using Managed identity .../id-migration."*

## 3. Real Azure partial-state inventory (independently re-queried, not assumed)

| Resource | State |
|---|---|
| `rg-noetva-dev` | `Succeeded` |
| `noetva-dev-eus2-vnet` (+ both delegated subnets) | `Succeeded` |
| Private DNS zone + VNet link | `Succeeded` |
| `noetva-dev-eus2-pg` (PostgreSQL Flexible Server, v17) | `Ready` |
| `noetvadeveus2acr` | `Succeeded` |
| `noetva-dev-eus2-kv` | `Succeeded`, currently **zero secrets** |
| `noetva-dev-eus2-cae` (Container Apps Environment) | `Succeeded` |
| `noetva-dev-eus2-log` (Log Analytics) | `Succeeded` |
| `id-frontend`, `id-backend`, `id-cicd`, `id-migration` | all exist (`id-lifecycle` correctly absent — separate deployment) |
| Role assignments (6, independently re-queried): 3× `AcrPull` (frontend/backend/migration), 2× `Key Vault Secrets User` (backend/migration), 1× `Contributor` on the RG (cicd) | all **present and correct** |
| `noetva-dev-eus2-availability-suppression` | exists |
| `noetva-dev-eus2-frontend` (Container App) | **`Failed`** |
| `noetva-dev-eus2-backend` (Container App) | **`Failed`** |
| `noetva-dev-eus2-migrate` (migration Job) | **does not exist** |
| 3 metric alerts + action group | **do not exist** (deployment aborted before reaching them) |

**Additional finding, not previously reported:** the human bootstrap operator (`azure-admin@noetva.ai`, subscription Owner) currently receives `Forbidden`/`ForbiddenByRbac` attempting to read Key Vault secret metadata (`Microsoft.KeyVault/vaults/secrets/readMetadata/action`) on `noetva-dev-eus2-kv` — Owner does not itself carry Key Vault **data-plane** RBAC roles under `enableRbacAuthorization: true`. The operator must self-assign (or be assigned) **Key Vault Secrets Officer** on this vault before Part 17's secret-population step can succeed — this is a third, related timing gap, not previously documented.

## 4. Defect 1 root cause — invalid placeholder image reference

`infra/azure/modules/container-app.bicep` and `container-apps-job-migration.bicep` both declare `imageReference` as a plain `string` parameter with no ARM-level format validation (only a `@description` comment stating it "MUST be a digest"). Azure Container Apps/Jobs validate that `template.containers[].image` is a syntactically parseable container image reference **at real provisioning time** — a literal placeholder string (`REPLACE_AT_DEPLOY_TIME_WITH_DIGEST_REFERENCE`) is rejected outright; the resource never reaches even an unhealthy running state. **The deployment guide's Part 23 claim — that placeholder-image Container Apps "will not actually run correctly yet, and that's expected" — is empirically false.** They do not provision at all, and their failure aborts the entire subscription-scope deployment (Bicep's nested-deployment model propagates a child failure to the parent).

## 5. Defect 2 root cause — Key Vault / Container App circular dependency

`resources.bicep`'s `backendApp` and `migrationJob` modules both declare `keyVaultSecretRefs` resolved via managed identity at container/job creation time (`container-app.bicep`/`container-apps-job-migration.bicep`: `secrets: keyVaultSecrets` in the `configuration` block, unconditionally populated whenever `keyVaultSecretRefs` is non-empty). Container Apps/Jobs validate that every declared Key-Vault-backed secret **actually resolves** at provisioning time — there is no lazy/deferred resolution. But the same Pass-1 deployment creates the Key Vault (`keyVault` module) with zero secrets in it, and nothing in `main.bicep`/`resources.bicep`/the guide's Part 23 step populates real secret values into that vault before the backend/migration resources that need them are created in the **same** deployment. RBAC for the app identities was independently confirmed already correct (§3) — this is purely a **secret-existence** ordering gap, not an access gap.

## 6. Defect 3 (newly discovered) — Key Vault secret name mismatch

`resources.bicep` line 286 (migration Job's `keyVaultSecretRefs`):
```bicep
{ name: 'ctec-database-url', keyVaultUrl: '${keyVault.outputs.keyVaultUri}secrets/postgres-migration-role-password' }
```
references a Key Vault secret named **`postgres-migration-role-password`**. The deployment guide's Part 17 secret table documents exactly 5 secrets — `postgres-admin-password`, `postgres-app-password`, `postgres-migrate-password`, `ctec-database-url`, `ctec-runtime-handoff-key` — and its own `az keyvault secret set` commands create a secret named **`postgres-migrate-password`**, never `postgres-migration-role-password`. These two strings do not match; independently confirmed via `grep` that `postgres-migration-role-password` appears nowhere in the documented secret inventory. Additionally, `postgres-migrate-password` (as documented) is a bare password, but the migration Job's container-side secret name is `ctec-database-url` — the same name the backend uses for its **full connection string** (`postgresql+psycopg://noetva_app:<password>@<host>/ctec`), meaning the migration Job in fact needs its own full connection string built from the `noetva_migrate` role's credentials, which Part 17 never names or documents at all. **This is a genuine, previously-undiscovered gap: a 6th Key Vault secret is required and was never specified.**

## 7. Complete bootstrap dependency DAG

```
resource group (ARM/Bicep, subscription-scope)
 ├─ managed identities (id-frontend, id-backend, id-cicd, id-migration)      [ARM/Bicep]
 ├─ network (VNet, subnets, private DNS)                                     [ARM/Bicep]
 ├─ Log Analytics workspace                                                  [ARM/Bicep]
 ├─ Key Vault (empty)                                                        [ARM/Bicep]
 ├─ ACR (empty)                                                              [ARM/Bicep]
 ├─ PostgreSQL Flexible Server (admin password = deploy-time secure param)   [ARM/Bicep]
 ├─ Container Apps Environment                                               [ARM/Bicep, depends on network]
 ├─ role assignments (AcrPull ×3, KV Secrets User ×2, Contributor ×1)        [ARM/Bicep, depends on identities+ACR+KV]
 │                                                                            ── FOUNDATION BOUNDARY ──
 ├─ operator: self-grant "Key Vault Secrets Officer" on the vault             [operator/manual]
 ├─ operator: generate postgres-app-password, postgres-migrate-password,
 │            ctec-runtime-handoff-key (postgres-admin-password already
 │            exists from foundation stage, or is reset — §12)               [operator/manual]
 ├─ operator: run db-bootstrap SQL (creates noetva_app/noetva_migrate roles,
 │            connected as ADMIN, using the just-generated passwords)         [operator/manual, runtime dependency on PG being Ready]
 ├─ operator: populate Key Vault (postgres-admin-password, postgres-app-password,
 │            postgres-migrate-password, ctec-database-url,
 │            ctec-migration-database-url [new, §6], ctec-runtime-handoff-key) [operator/manual, requires KV Secrets Officer]
 ├─ operator: build + push real backend image to ACR (now it exists)          [operator/manual or GitHub OIDC — human for first bootstrap]
 ├─ operator: build + push real frontend image to ACR (interim redirect URI,
 │            rebuilt again once real FQDN is known — unchanged two-pass design) [operator/manual]
 │                                                                            ── APPLICATION BOUNDARY ──
 ├─ backend Container App (real digest image + now-resolvable KV secrets)     [ARM/Bicep, depends on foundation + real image + real secrets]
 ├─ migration Job (same backend digest + now-resolvable migration secret)     [ARM/Bicep, depends on foundation + real image + real secret]
 ├─ frontend Container App (real digest image)                               [ARM/Bicep, depends on foundation + real image]
 ├─ monitoring alerts + action group (depend on migrationJob.outputs.jobId)   [ARM/Bicep, depends on migration Job existing]
 │                                                                            ── POST-DEPLOYMENT ──
 ├─ operator: trigger migration Job manually, verify migration head           [operator/manual, post-deployment]
 ├─ operator: retrieve real frontend/backend FQDNs                            [post-deployment, Azure-generated]
 ├─ operator: register Entra SPA redirect URI using the real FQDN             [operator/manual, Entra mutation — separate phase]
 ├─ operator: rebuild frontend image with real redirect URI, redeploy         [operator/manual — existing Part 26-31 flow, unchanged]
 ├─ business-tenant row (`noetva-dev-tenant`) created via governed bootstrap  [post-deployment, application-level, unchanged by this artifact]
 └─ GitHub OIDC federation + variables, transition to azure-deploy.yml for
    ALL SUBSEQUENT (non-bootstrap) deployments                               [operator/manual one-time; GitHub OIDC thereafter — unchanged existing design, §14]
```

## 8. Image-bootstrap architecture options evaluated

- **Option A (public placeholder image):** rejected. Noetva's architecture is digest-pinned, private-ACR-only by explicit design (`container-app.bicep`: *"MUST be a digest, never a mutable tag, never `latest`"*; README's ACR immutable-tagging discipline). Introducing any public image — even transiently — is a supply-chain-trust regression with no compensating control, and is unnecessary given Option C/D below fully avoids it.
- **Option B (build/push real images before Container Apps are created):** correct in spirit, necessary, but insufficient alone — still requires *something* to gate Container App creation until the real image exists, i.e., it requires either C or D as its enabling mechanism.
- **Option C (make Container Apps/Job conditional) + Option D (explicit foundation/application staging):** **FROZEN, combined.** A single new boolean parameter, `deployApplicationTier` (default `false`), gates the `backendApp`, `migrationJob`, `frontendApp`, and `monitoringAlerts` modules in `resources.bicep` (the existing `lifecycleAlertSuppression` module already uses this exact `if (...)` conditional-module pattern — this is idiomatic, not novel, for this codebase). Foundation resources (identities, network, monitoring workspace, Key Vault, ACR, PostgreSQL, Container Apps Environment, role assignments, lifecycle-alert-suppression) always deploy unconditionally. The **same** `main.bicep`/`resources.bicep` entry point is invoked twice: once with `deployApplicationTier=false` (foundation — safe to re-run now, idempotently, against the current partial state), once with `deployApplicationTier=true` and real, digest-pinned image references (application tier — only after real images and real Key Vault secrets exist). This never references a public/untrusted image at any point — the first and only image ever referenced is the real, digest-pinned Noetva image.
- **Option E (bootstrap image copied into private ACR):** rejected as unnecessary — Option C+D means no bootstrap/placeholder image of any kind, real or copied, is ever required.
- **Option F:** not identified as superior to C+D.

## 9. Frozen image-bootstrap decision

Add `param deployApplicationTier bool = false` to both `main.bicep` and `resources.bicep`, propagated identically to how every other pass-through parameter already flows. Gate exactly these four existing module declarations with `if (deployApplicationTier)`: `backendApp`, `migrationJob`, `frontendApp`, `monitoringAlerts`. No other module gains a condition. The four environment parameter files each gain exactly one new key, `"deployApplicationTier": { "value": false }` — the safe, foundation-only default; the operator overrides it to `true` via the same `--parameters deployApplicationTier=true` CLI-override mechanism already established for `postgresAdminPassword`/`alertEmail`/`oidcIssuer` in R5's own predecessor phase, for the second (application-tier) invocation only.

## 10. Digest-pinning preservation (proven, not asserted)

- Final governed form, unchanged from existing `@description` comments: `<acr-login-server>/<repo>@sha256:<digest>` — e.g. `noetvadeveus2acr.azurecr.io/noetva/backend@sha256:<digest>`.
- Migration Job **shares the backend image** — independently confirmed (`resources.bicep` line 281: `imageReference: backendImageReference` passed to `migrationJob`) — never a separate migration image, never a separate digest.
- Frontend uses its own, environment-specific image/digest (CDD/README Section 28/W, unchanged, not reopened here).
- **Who builds the first image, where, when:** the human bootstrap operator, locally (via the existing `docker build`/`docker push` steps already in Part 26/27, run against the ACR that now exists after the foundation stage), using `az acr login` with their own already-established Owner-derived credentials — not GitHub OIDC, for this first bootstrap image (§14). ACR must exist (foundation stage complete) before any image can be pushed to it — this ordering was already implicit in Part 23/26 and is now made an explicit, enforced stage boundary rather than an assumption.
- No digest-pinning requirement is weakened anywhere by this correction — the opposite: the corrected sequence makes it *impossible* to reach the point of creating a Container App with anything other than a real, digest-pinned image, closing the exact gap that let a placeholder string reach ARM in the first place.

## 11. Secret-bootstrap architecture options evaluated

- **Option A (foundation creates Key Vault; human populates; application follows):** **FROZEN.** Directly enabled by, and unified with, the same `deployApplicationTier` staging from §9 — no second, separate mechanism is needed. The human operator populates Key Vault (§3's newly-discovered RBAC gap notwithstanding — see §12) in the gap between the two `az deployment` invocations, using the exact same generated values that also feed the DB-bootstrap SQL step.
- **Option B (Bicep creates Key Vault secret *resources* directly from secure deployment parameters):** rejected — this would require passing `postgres-app-password`/`postgres-migrate-password`/`ctec-runtime-handoff-key` as Bicep parameters at foundation-deployment time, before the DB roles they belong to even exist (the DB-bootstrap SQL step, which creates `noetva_app`/`noetva_migrate` and sets their passwords, must run *after* Postgres exists but the passwords must be decided *before* that SQL runs — Option A's ordering already handles this correctly; Option B would not remove any dependency, only relocate where the value is typed, while pulling secret material through Bicep deployment parameters/history unnecessarily for values that don't need to be ARM-deployment-time inputs at all).
- **Option C (separate dedicated secrets/bootstrap Bicep stage):** unnecessary — Key Vault is already created in the foundation stage; no additional Bicep stage is needed solely for secret population, since `az keyvault secret set` (imperative CLI, per existing Part 17) is the correct, already-governed mechanism and requires no Bicep resource of its own.
- **Option D (application resources conditional until Key Vault populated):** this is exactly what §9's `deployApplicationTier` gate already achieves — not a separate option, the same one.
- **Option E:** none identified as safer/narrower.

## 12. Frozen secret-bootstrap decision

**Six** Key Vault secrets are required (five previously documented, one newly discovered):

| Secret name | Source | Consumed by |
|---|---|---|
| `postgres-admin-password` | Human-generated at foundation-deployment time (deploy parameter); **must be reset** post-facto for this specific partial environment (§17 — the value generated during the failed attempt is not recoverable) | Human operator only (break-glass) |
| `postgres-app-password` | Human-generated, fed to db-bootstrap SQL | Backend Container App (assembled into `ctec-database-url`) |
| `postgres-migrate-password` | Human-generated, fed to db-bootstrap SQL | Assembled into the new `ctec-migration-database-url` secret (below) — never referenced directly by any Container App/Job |
| `ctec-database-url` | Human-assembled: `postgresql+psycopg://noetva_app:<postgres-app-password>@noetva-dev-eus2-pg.postgres.database.azure.com/ctec` | Backend Container App |
| **`ctec-migration-database-url`** *(new, corrects Defect 3)* | Human-assembled: `postgresql+psycopg://noetva_migrate:<postgres-migrate-password>@noetva-dev-eus2-pg.postgres.database.azure.com/ctec` | Migration Job (`resources.bicep` line 286's `keyVaultUrl` corrected to reference this exact name, replacing the mismatched `postgres-migration-role-password`) |
| `ctec-runtime-handoff-key` | Human-generated (32-byte random, base64url) | Backend Container App |

No second circular dependency is introduced: all six are populated by the operator, imperatively, via `az keyvault secret set`, entirely outside Bicep — no secret value ever becomes a Bicep deployment parameter except `postgresAdminPassword` (which was already `@secure()` and deploy-time-only, unchanged).

## 13. Database bootstrap order (derived, proven executable from zero)

1. PostgreSQL Flexible Server created (foundation stage), admin password set via secure Bicep parameter at creation time — **the only secret that must exist before any Bicep deployment runs.**
2. `ctec` database created (already part of the `postgres` module, foundation stage — independently confirmed present in the what-if's resource list, `Microsoft.DBforPostgreSQL/flexibleServers/noetva-dev-eus2-pg/databases/ctec`).
3. Operator connects as ADMIN (using the password from step 1) and runs `db-bootstrap/001_create_roles_and_grants.sql`, creating `noetva_app`/`noetva_migrate` with newly-chosen passwords (this is the *first* point either of those two passwords is decided — they cannot be decided earlier, since the roles don't exist yet).
4. Operator assembles and populates all six Key Vault secrets (§12).
5. Operator builds/pushes real images; runs the application-tier deployment (`deployApplicationTier=true`) — creates backend/frontend Container Apps and the migration Job for the first time, all three now resolving real secrets and real images.
6. Operator manually triggers the migration Job (`az containerapp job start`) — this is the first and only point schema migration + the two production-required seeders run.
7. Business-tenant row (`noetva-dev-tenant`) bootstrap — unchanged, application-level, outside this artifact's scope, occurs after step 6.
8. Backend Container App startup (already gated to `uvicorn`-only, no migration authority, unchanged) — safe at any point after step 5, since it depends only on the schema already existing is **not** actually required for the backend to *start* (health-check is liveness-only, per existing design), but is required for the backend to be *functionally correct*.

**This order is now genuinely executable from zero** — every step's inputs are available before it runs; no circularity remains.

## 14. Key Vault / RBAC ordering

- `id-backend`/`id-migration`'s `Key Vault Secrets User` role assignments already succeed at **foundation** stage (§3, §7 — independent of the human operator's own access, and independent of whether secrets exist yet — RBAC and secret-existence are orthogonal, confirmed by the real partial state: RBAC present, secrets absent, and that combination is exactly what caused the observed failure, not an RBAC problem).
- The **human operator** additionally needs `Key Vault Secrets Officer` (write access) on this vault to perform §12's population step — not automatically granted by subscription Owner under `enableRbacAuthorization: true`. This must be an explicit, one-time, narrowly-scoped (vault-only) self-assignment by the operator (who has `Microsoft.Authorization/roleAssignments/write` via Owner) — frozen as an explicit corrected-guide step (§21), not a silent assumption.
- **RBAC propagation timing risk:** Azure RBAC role assignments typically propagate within seconds to a few minutes; the corrected sequence's natural human-paced gap between foundation deployment and application-tier deployment (during which the operator manually runs DB bootstrap and builds images) is itself a more-than-sufficient bounded wait — no additional explicit retry/sleep mechanism is required, but the corrected guide must state this propagation possibility explicitly (a `403`/`Forbidden` reading a freshly-assigned role within the first minute is expected transient behavior, not a defect, and should prompt a short wait-and-retry, not escalation).

## 15. PostgreSQL admin-password recoverability status

**NOT SAFELY RECOVERABLE.** The password was generated inside a single Bash tool invocation's local shell variable (`PG_ADMIN_PW=$(python3 -c ...)`), used directly in the `az deployment` command within that same invocation, then explicitly `unset`. It was never echoed, never written to any file, never included in any log this session produced, and the background process that held it has since exited. No artifact — this transcript, any temp file, any Azure-side record (ARM redacts `@secure()` parameters from all deployment history and operation logs) — contains it. **Value classification: genuinely, permanently gone.**

**Governed recovery required (not performed in this DRG):** `az postgres flexible-server update --name noetva-dev-eus2-pg --resource-group rg-noetva-dev --admin-password <new-value>` — a standard, safe, **non-destructive** Azure operation that rotates the credential in place with no data loss and no resource recreation. This reset must be the first action of the implementation phase's foundation-stage re-run (or performed standalone before it), using a freshly-generated password via the identical secure-generation method, before Part 15's DB-bootstrap SQL can proceed.

## 16. Partial-state convergence decision

Re-running the foundation-stage deployment (`deployApplicationTier=false`) against the current partial `rg-noetva-dev` is expected to **converge safely**: every foundation resource (VNet, private DNS, Log Analytics, Key Vault, ACR, PostgreSQL, Container Apps Environment, role assignments) already matches its Bicep-declared desired state exactly (same names, same properties, same tags — nothing in the frozen correction changes any foundation resource's shape), so ARM's default incremental deployment mode will report these as unchanged, not attempt replacement or deletion. The frontend/backend Container Apps (currently `Failed`) and the migration Job (currently absent) are **not** included in this foundation-only redeploy (gated `false`) — they remain untouched (Failed-but-inert, or absent) until the application-tier pass explicitly re-declares them with real inputs, at which point ARM will create them correctly for the first time (the Job) or replace the failed revision with a working one (the Container Apps) — neither is a delete-and-recreate of the *resource group* or any *foundation* resource. `rg-noetva-identity-dev` and all other pre-existing subscription resources remain entirely outside this template's scope and are unaffected. **No destructive action is required or authorized to converge.**

## 17. Human-bootstrap vs. GitHub-OIDC authority boundary

**Unchanged from the existing, already-governed design (Part 23's own stated rationale) — not reinvented.** Both the corrected foundation-stage and application-stage deployments remain **human-bootstrap-only**, performed via `az deployment sub create` (subscription-scoped) using the operator's own Owner credential — `id-cicd`, even though it now exists in partial state, is deliberately scoped to `Contributor` on `rg-noetva-dev` only (§3, confirmed) and cannot perform a subscription-scoped deployment; using it here would also skip the very GitHub-variable-population step (`NOETVA_CICD_CLIENT_ID`, Part 24/25) that legitimizes its later use. GitHub OIDC becomes authoritative **only** for the already-existing, unchanged Part 26-onward flow (`azure-deploy.yml`'s `az containerapp update --image` calls, resource-group-scoped, for all ordinary subsequent image updates) — exactly as already designed, now simply reconfirmed to extend cleanly to the two-stage corrected bootstrap without inventing a second, competing bootstrap mechanism.

## 18. Two-pass FQDN / auth sequence (preserved, integrated with the new stage split)

Unchanged in substance from the existing design, now correctly sequenced against the new foundation/application split:
1. Foundation stage (no FQDN yet, no images yet).
2. Operator builds an initial real frontend image (real digest, but necessarily an interim/placeholder `NEXT_PUBLIC_OIDC_REDIRECT_URI` value baked in, since no FQDN exists yet — this was already true under the old single-pass design and is not newly introduced by this correction).
3. Application-tier stage creates the real frontend Container App — **this is the first point a real FQDN exists.**
4. Operator retrieves the real FQDN, derives `https://<FQDN>/auth/callback` (never invented ahead of this point), registers it as the Entra SPA redirect URI (a separate, explicitly Entra-mutating phase, not part of this artifact), and rebuilds/redeploys the frontend image with the real values — identical to the existing, unmodified Part 24-31 sequence.
No hostname is ever invented at any stage; the placeholder-redirect interim build is pre-existing, disclosed, unchanged design, not a new gap this artifact introduces.

## 19. Failure-recovery model (frozen as a reusable governed pattern)

1. **Safe re-entry:** the foundation-stage deployment is idempotent and safely re-runnable at any time (§16).
2. **No mandatory delete/recreate:** never required by this model; Part 53's destructive-delete path remains separate, unchanged, and unauthorized here.
3. **No secret leakage:** all secret generation/storage continues to use the existing governed mechanisms (`az keyvault secret set`, never printed/committed/logged) — unchanged.
4. **No resource drift:** the two-stage split uses the identical Bicep source for both invocations (one parameter differs), so there is no risk of the two stages diverging into different declared states over time.
5. **Clear operator checkpoints:** foundation deployment succeeds → operator resets admin password (§15) → operator runs DB bootstrap → operator populates Key Vault → operator builds/pushes images → application-tier deployment → operator triggers migration Job → operator captures FQDNs.
6. **Readback before continuation:** each checkpoint above should be independently verified (e.g., `az keyvault secret list` names-only, `az postgres flexible-server show` state, image digest confirmation) before proceeding to the next, mirroring this DRG's own verification discipline.
7. **Bounded retry for eventual consistency:** RBAC self-assignment propagation (§14) — a short wait-and-retry is expected and normal, not a failure signal.

## 20. Guide statements requiring correction

`docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md`:
- **Part 17:** add the sixth secret, `ctec-migration-database-url` (exact assembly formula, §12), to the secret table and the `az keyvault secret set` command block; add the explicit `Key Vault Secrets Officer` self-assignment step (§14) before the population commands; correct the erroneous premise that Key Vault population can happen "now" independent of the two-stage split — it must happen strictly between the foundation and application deployments.
- **Part 23:** remove/correct the false claim that placeholder-image Container Apps "will not actually run correctly yet, and that's expected" (§4 disproves this); replace the single `az deployment sub create` command with the two explicit, ordered invocations (`deployApplicationTier=false` then `=true`), with Parts 15/17/26/27 now explicitly sequenced **between** them rather than positioned before Part 23 in reading order but actually intended for "whenever Key Vault exists."
- **Part 15/17 sequencing:** clarify these are not merely "read before Part 23" background sections but **mandatory, ordered actions that occur between the two Pass-1 sub-deployments.**
- **Part 55 (Master checklist), item Q:** split "Pass 1: `main.bicep` deployment succeeded" into two explicit checked items (foundation, application).

No other part of the guide is implicated — Parts 6-14, 16, 18-22, 24-25, 28-57 remain accurate and unchanged.

## 21. Test / verification architecture

Static-only tests cannot have caught either defect (both are real-ARM-provisioning-time behaviors, invisible to `bicep build`/lint, confirmed empirically by this very DRG). Freeze:
1. A repository-level static check (backend/frontend test suite equivalent, or a dedicated `infra/azure/validation/*` script) asserting that no committed environment parameter file's `backendImageReference`/`frontendImageReference` value is the literal placeholder string when `deployApplicationTier` would be `true` for that file — i.e., a placeholder is only ever valid alongside `deployApplicationTier: false`.
2. A static check that every `keyVaultSecretRefs` name referenced anywhere in `resources.bicep` has a corresponding, exact-string-matching entry in the deployment guide's Part 17 secret table (would have caught Defect 3 mechanically).
3. **Real-Azure VM requirement (binding):** the implementation phase's VM/verification step **must** perform a real `az deployment sub create` with `deployApplicationTier=false` against the actual partial `rg-noetva-dev` (proving safe convergence, §16) — a `what-if` alone is insufficient, since `what-if` already passed cleanly before the real failure and cannot simulate Container-Apps-level image/secret resolution. The application-tier deployment must likewise be really executed (not merely what-if'd) before this correction may be declared operationally closed.
4. Confirm DEV/staging/demo/prod parameter-contract consistency: the new `deployApplicationTier` key must be added to all four environment files, defaulting `false` in every one (staging/demo/prod bootstrap follows the identical two-stage model the first time each is deployed).

## 22. Docker / application non-regression

This artifact touches only `infra/azure/*` Bicep files, the four environment parameter files, and the deployment guide. It does not touch `backend/`, `frontend/`, `keycloak/`, `docker-compose.yml`, or any CDD-063/064/065/066-governed value, file, or behavior. Local Docker/Keycloak development is entirely unaffected.

## 23. Security invariants (binding, all 8)

1. No public or non-Noetva-controlled image is ever referenced, even transiently.
2. Digest pinning is never weakened — the corrected sequence makes it structurally impossible to create a Container App with a non-digest image reference.
3. Migration Job continues to share the backend image exactly (never a separate, unaccounted-for image).
4. No secret value is ever a Bicep deployment parameter except `postgresAdminPassword` (unchanged, already `@secure()`).
5. RBAC additions are limited to exactly what §14 specifies (app-identity roles unchanged/already-correct; one narrowly-scoped human self-assignment) — no broad grant, no subscription-wide role for any runtime identity.
6. Human-bootstrap vs. GitHub-OIDC authority boundary is preserved unchanged (§17) — no premature transition to GitHub OIDC.
7. No current partial Azure state (§3) may be deleted during implementation without separate, explicit governance.
8. `CTEC_OIDC_SCOPE_CLAIM=scp`, `CTEC_OIDC_TENANT_CLAIM=noetva_tenant_id`, and the CDD-066 frontend scope contract are unaffected and unreferenced by this correction.

## 24. Exact authorized implementation paths

```
CREATE = 0
MODIFY = 7
DELETE = 0
```

| # | Path | Change |
|---|---|---|
| 1 | `infra/azure/main.bicep` | add `deployApplicationTier` parameter, pass through |
| 2 | `infra/azure/resources.bicep` | add `deployApplicationTier` parameter; gate `backendApp`/`migrationJob`/`frontendApp`/`monitoringAlerts` with `if (deployApplicationTier)`; correct the migration Job's Key Vault secret reference from `postgres-migration-role-password` to `ctec-migration-database-url` |
| 3 | `infra/azure/environments/dev/main.parameters.json` | add `"deployApplicationTier": { "value": false }` |
| 4 | `infra/azure/environments/staging/main.parameters.json` | same |
| 5 | `infra/azure/environments/demo/main.parameters.json` | same |
| 6 | `infra/azure/environments/prod/main.parameters.json` | same |
| 7 | `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` | Parts 15/17/23/55 corrections per §20 |

**Explicitly prohibited:** any `backend/*`, `frontend/*`, `keycloak/*`, `docker-compose.yml`, `.github/workflows/*` path; any CDD-063/064/065/066-governed value; any new Bicep module file (the conditional-parameter approach, §9, makes a new file unnecessary); deletion of any existing file.

## 25. STOP conditions carried into implementation

Implementation must itself STOP (not silently repair) if: the foundation-stage what-if/real-redeploy shows anything other than clean convergence against the current partial state; the application-tier what-if shows any unexpected DELETE; the Key Vault Secrets Officer self-assignment fails or is denied; the corrected migration secret reference still fails to resolve after population; any step requires deleting `rg-noetva-dev` or any resource within it; or real Azure evidence contradicts any statement frozen in this artifact.

---

*This document authorizes governance only. It does not implement, deploy, or verify anything itself. It does not authorize deleting any current partial Azure state (§16, §19, §25).*
