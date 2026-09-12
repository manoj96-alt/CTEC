# CDD-068 — Azure DEV Private Database Bootstrap Correction

**Status:** FROZEN
**Originating phase:** AZURE-DEV-PRIVATE-DB-BOOTSTRAP-R6 (DRG → I → VM)
**Amends:** nothing frozen in place. Complements CDD-067 (`docs/cdd/CDD-067-Azure-DEV-Bootstrap-Two-Stage-Correction.md`, SHA-256 `5b2b19e86122f8db896012d97e5f08214773a7699da31b25c08c8833634e1e23`, PR #213, still open) by resolving the missing execution path for CDD-067's own Stage 1b (database role bootstrap), which R5 proved for real cannot be performed from an operator/Claude execution environment with no VNet route to the intentionally-private PostgreSQL server. CDD-067 is not reopened, not edited, and none of its statements are superseded — this artifact adds exactly one new governed mechanism it did not yet specify.

**Scope:** A single new, narrowly-scoped, ADMIN-authority Azure Container Apps Job — deployed into the *already-existing* private VNet/Container Apps Environment, with zero new network infrastructure — that performs the one-time (or credential-rotation-time) database role bootstrap `db-bootstrap/001_create_roles_and_grants.sql` already committed but never wired to any compute.

---

## 1. Authoritative baseline at freeze

Main SHA: `09acfeb77a258ff8a83a48a8fc4105279456f50a` — independently re-verified against `origin/main` and GitHub `main`. CDD-067 (PR #213, commit `1440275a1596c2845e5c65c4c1db6d33c0466ab7`) and its implementation (PR #214, commit `6e2185b1dddc69364ad4520063fb3416296eafb4`) both re-confirmed OPEN, unmerged, at their expected heads.

## 2. Real blocker evidence (re-confirmed, not assumed)

R5 independently proved (direct DNS/socket test from the operator/Claude execution environment): `noetva-dev-eus2-pg.postgres.database.azure.com` does not resolve and is not reachable outside the governed VNet. Freshly re-confirmed in this DRG: `az postgres flexible-server show` reports `network.publicNetworkAccess: "Disabled"`, `network.delegatedSubnetResourceId` pointing at `snet-postgres`, `network.privateDnsZoneArmResourceId` pointing at the linked private zone. **This must remain disabled — not a defect, the intended architecture.**

## 3. Real Azure network state (read-only, independently queried)

- VNet `noetva-dev-eus2-vnet`, address space `10.20.0.0/16`, exactly two subnets: `snet-container-apps` (`10.20.0.0/23`, delegated to `Microsoft.App/environments`) and `snet-postgres` (`10.20.2.0/24`, delegated to `Microsoft.DBforPostgreSQL/flexibleServers`) — **the same VNet**.
- **Zero NSGs exist** in `rg-noetva-dev` — no explicit rule restricts subnet-to-subnet traffic (Azure VNets permit all intra-VNet traffic by default absent an NSG).
- The private DNS zone `noetva-dev-eus2.postgres.database.azure.com` is linked to exactly this VNet (`noetva-dev-eus2-pg-dns-link`).
- ACR (`noetvadeveus2acr`) and Key Vault (`noetva-dev-eus2-kv`) both report `publicNetworkAccess: Enabled` — both already independently proven reachable from the operator/Claude execution environment in R5 (KV role read-back, secret-list call) and originally (image push design).

**Conclusion, proven not assumed:** the existing Container Apps Environment (`noetva-dev-eus2-cae`), being injected into `snet-container-apps` within the identical VNet the private DNS zone is linked to, **already has full private network reachability to PostgreSQL** — no Bastion, VPN, VM, or self-hosted runner is needed to obtain this reachability; it already exists for anything running inside that environment.

## 4. Existing migration Job architecture (inspected, not assumed)

`infra/azure/modules/container-apps-job-migration.bicep` + its wiring in `resources.bicep`: identity `id-migration` (RBAC: `AcrPull` + `Key Vault Secrets User` on the one migration-role secret only — confirmed in R5's real Azure inventory); image = `backendImageReference` (shares the backend digest, never separate); command = `alembic upgrade head` + the two production-required seeders (unchanged, `container-apps-job-migration.bicep`'s own `migrationScript`); its **only** Key Vault dependency is `ctec-database-url`-aliased `ctec-migration-database-url` (per CDD-067's Defect 3 correction), which itself depends on the `noetva_migrate` role already existing with a known password. **This Job cannot perform initial role creation** — it has no ADMIN-level Postgres credential, only ever connects as the already-provisioned `noetva_migrate` role, and its own prerequisite (the Key Vault secret) is exactly the thing CDD-067's Stage 1b needs bootstrapped first. **Confirmed: reusing it for bootstrap would recreate the circular dependency** (it needs a secret that needs it to not yet be needed) and would also blur separation of duties (an ADMIN-capable Job and a MIGRATE-role-only Job must remain structurally distinct, per this DRG's own explicit requirement not to conflate BOOTSTRAP/MIGRATION/APPLICATION credentials).

## 5. Part 15 bootstrap tooling analysis

`infra/azure/scripts/run_db_bootstrap.sh` (already committed, never wired to any compute): reads exactly `NOETVA_PG_HOST`, `NOETVA_PG_ADMIN_USER`, `NOETVA_PG_ADMIN_PASSWORD`, `NOETVA_PG_APP_PASSWORD`, `NOETVA_PG_MIGRATE_PASSWORD` from environment variables only (never a CLI argument, never a file); invokes `psql` with `PGSSLMODE=require`; explicitly disables shell tracing (`set +x`) around the one command touching secret values; never echoes a secret. `db-bootstrap/001_create_roles_and_grants.sql`: independently re-confirmed idempotent by its own header and the README's disclosed real-container test evidence ("re-run twice consecutively with no error"), uses `psql` variable substitution (`-v app_password=...`) rather than shell interpolation, creates exactly three authorities (`noetva_app` DML-only, `noetva_migrate` DDL+DML, admin/break-glass). **No correction to this SQL or script is required** — its only defect was never having anything to execute it with real VNet reachability. The backend/migration image (`python:3.12-slim` base) does **not** include `psql`/`postgresql-client` — confirmed via `backend/Dockerfile` — so no existing image can run this script as-is.

## 6. Options evaluated

- **Option A (adapt the existing migration Job):** rejected — §4 proves it lacks ADMIN authority and reusing it would blur bootstrap/migration separation of duties and reintroduce the exact circularity being resolved.
- **Option B (new, narrowly-scoped ephemeral-trigger Container Apps Job in the existing private environment):** **FROZEN.** Zero new network resource, zero new subnet, zero NSG change, zero new VNet peering — reuses the CAE's already-proven private reachability (§3) entirely. Job execution is billed only while actually running (`triggerType: Manual`, matching the existing migration Job's own pattern) — effectively zero idle cost, consistent with Noetva's dormant-cost posture.
- **Option C (Azure Bastion + management VM):** rejected — introduces permanent (or semi-permanent) compute and a new attack surface (an interactive VM with shell access) for a task that has no interactive requirement; meaningfully higher idle cost and operational/patching burden than a manually-triggered Job.
- **Option D (Point-to-Site VPN):** rejected — a VPN Gateway has a real, non-trivial fixed hourly cost even fully idle, and solves a broader "let any operator machine join the VNet" problem this narrow, well-defined one-time bootstrap task does not need.
- **Option E (self-hosted GitHub runner in the VNet):** rejected — requires a persistent listening process/compute (a VM or always-on container) purely to host CI, disproportionate to a task that runs once (or rarely, for rotation) and already has a governed direct-`az`-CLI human-bootstrap precedent (CDD-067 §17) for deployment actions.
- **Option F (Azure Container Instance):** rejected as unnecessary — the existing Container Apps Environment already provides exactly this private-network-reachable ephemeral-compute capability; introducing ACI would duplicate infrastructure the environment already offers.
- **Option G (Azure Cloud Shell with private networking):** rejected — Cloud Shell's own private-VNet integration (via a dedicated storage account + private endpoint + its own subnet) is materially more setup complexity and cost than a single Container Apps Job already running inside networking that exists, for equivalent capability.
- **Option H:** none identified as narrower than B.

## 7. Selected private execution mechanism

A new Azure Container Apps Job (Bicep module, analogous in shape to `container-apps-job-migration.bicep`), deployed into the existing `noetva-dev-eus2-cae`, gated behind a new boolean parameter `deployDbBootstrapJob` (default `false`) exactly mirroring CDD-067's `deployApplicationTier` gating pattern. It uses a new, small, Noetva-controlled, digest-pinned image (built from a new minimal Dockerfile, pushed to the existing `noetvadeveus2acr` — no public/third-party image, preserving CDD-067's invariant) containing `psql` (`postgresql-client`) plus the already-committed `run_db_bootstrap.sh` and `001_create_roles_and_grants.sql`, run unmodified.

## 8. Rejected alternatives and reasons

See §6. In one sentence: every rejected option either reintroduces the exact circularity/authority-blurring this correction exists to resolve (A), or trades a one-time, cheap, already-network-connected Job for new permanent or semi-permanent infrastructure with materially higher cost, complexity, or attack surface (C/D/E/F/G) — none of which the existing architecture requires, since §3 already proves the reachability exists without them.

## 9. Network placement

The bootstrap Job runs inside `noetva-dev-eus2-cae`, using the environment's existing infrastructure subnet (`snet-container-apps`), identical in kind to every other Container App/Job already there. No new subnet, no new delegation, no new private DNS zone/link, no NSG change, no public IP. `publicNetworkAccess: Disabled` on PostgreSQL is never touched.

## 10. Bootstrap authority model (exactly delineated, not conflated)

| # | Action | Authority |
|---|---|---|
| 1 | PostgreSQL administrator password reset | Human operator (or Claude on their behalf), via `az postgres flexible-server update --admin-password`, using the operator's own subscription-level RBAC — unchanged from CDD-067 §15 |
| 2 | Initial DB connection (bootstrap) | The new bootstrap Container Apps Job, using the ADMIN password delivered per §12 |
| 3 | Application-role (`noetva_app`) creation | The bootstrap Job, running `001_create_roles_and_grants.sql` as ADMIN |
| 4 | Migration-role (`noetva_migrate`) creation | The bootstrap Job, same script, same run |
| 5 | Password assignment (both roles) | The bootstrap Job, using operator-chosen values delivered per §12 |
| 6 | Schema/database initialization (`ctec` database) | Already created by the foundation stage (CDD-067, unchanged) — not this artifact's concern |
| 7 | `noetva-dev-tenant` bootstrap | The existing, unchanged migration Job's seeders / a later application-level step — outside this artifact's scope (§13/§16) |
| 8 | Key Vault secret creation (all six) | Human operator, `az keyvault secret set`, unchanged mechanism from CDD-067 §12 — using the same operator-chosen app/migrate passwords already used in step 5 |
| 9 | Normal future schema migrations | The existing, unchanged `noetva-dev-eus2-migrate` Job, using the `noetva_migrate` role via its Key-Vault-backed secret — §16 |

No authority is collapsed into one long-lived credential: the ADMIN password (steps 1-2) is bootstrap-scoped and discarded after use (§11); the application/migration passwords (steps 3-5, 8) are operator-chosen values used identically in two independent places (the bootstrap Job's inputs, and Key Vault's population) — not a shared secret store, not a cycle.

## 11. PostgreSQL admin-password lifecycle

1. Generate a fresh, cryptographically secure password (same method as CDD-067 §15/R5).
2. Reset it via `az postgres flexible-server update --admin-password` (unchanged, non-destructive, already-proven-safe operation).
3. Deliver it to the bootstrap Job **only** as a `@secure()` Bicep deployment parameter (never Key Vault, never a file, never a log) — the Job's Container Apps `secrets` block receives it as a plain (non-Key-Vault-backed) Container Apps secret, mapped to `NOETVA_PG_ADMIN_PASSWORD`.
4. Trigger the Job once (`az containerapp job start`).
5. **After a verified-successful run, the value is not persisted anywhere by this mechanism** — it is not written to Key Vault, not retained in source, not logged. It is treated as spent. A future break-glass need (or credential rotation) repeats steps 1-4 with a freshly generated value — identical, disclosed lifecycle to CDD-067 §15's existing precedent, extended consistently rather than introduced anew.
6. An operator who independently wants a durable break-glass credential in Key Vault (the already-governed `postgres-admin-password` secret, CDD-067 §12) may choose to also store the value **they personally generated and retained** — this artifact does not require or forbid that; it only guarantees the bootstrap mechanism itself never depends on such persistence existing.

## 12. Application/migration credential lifecycle

1. Operator chooses/generates `postgres-app-password` and `postgres-migrate-password` (fresh, cryptographically secure) — the *same* values are used in both of the following, never regenerated between them:
2. Delivered to the bootstrap Job as two more `@secure()` Bicep parameters → plain Container Apps secrets → `NOETVA_PG_APP_PASSWORD`/`NOETVA_PG_MIGRATE_PASSWORD`, exactly matching `run_db_bootstrap.sh`'s required environment variables.
3. The Job's SQL run sets these as the real passwords on the `noetva_app`/`noetva_migrate` PostgreSQL roles.
4. Independently, the operator (who chose these same values in step 1) populates Key Vault's `ctec-database-url` and `ctec-migration-database-url` (full connection strings assembled from these same passwords, CDD-067 §12, unchanged) via `az keyvault secret set`, exactly as CDD-067 already governs.

## 13. Key Vault bootstrap sequence (unchanged from CDD-067, now genuinely executable)

Unchanged from CDD-067 §12/§13 — this artifact does not alter which six secrets exist or their names/assembly formulas. It only supplies the previously-missing execution authority (§7) that makes populating them meaningful (real, working DB roles behind the connection strings) rather than merely present-but-non-functional.

## 14. Circular-dependency proof

The bootstrap Job's only inputs are: (a) the PostgreSQL host (a plain, non-secret Bicep output, `postgres.outputs.serverFqdn`), (b) the ADMIN password (delivered via Bicep secure parameter, §11 — requires nothing from Key Vault), (c) the two fresh app/migrate passwords (delivered identically, §12 — requires nothing from Key Vault). **Key Vault is never read by the bootstrap Job.** Key Vault population (§13) happens *after* the Job succeeds, using values the operator already independently holds (their own choice, not derived from anything the Job produced). There is no path in this design where A requires B and B requires A — confirmed by tracing every credential's origin to a source outside the cycle (Bicep deployment parameters and operator-chosen values, both external inputs, never Job output).

## 15. Exact DB bootstrap sequence (supersedes nothing in CDD-067 §13; fills in its Stage 1b)

1. Foundation stage already deployed and converging (CDD-067, R5-proven).
2. Operator resets the PostgreSQL admin password (§11 steps 1-2).
3. Operator generates `postgres-app-password`, `postgres-migrate-password` (§12 step 1).
4. Operator builds and pushes the new bootstrap image to `noetvadeveus2acr` (does not require VNet reachability — ACR is `publicNetworkAccess: Enabled` and already independently proven reachable).
5. Operator (still human-bootstrap authority, unchanged from CDD-067 §17) runs `az deployment sub create` with `deployDbBootstrapJob=true` and the three secure passwords (§11/§12) plus the real bootstrap image digest.
6. Operator triggers the Job (`az containerapp job start --name noetva-dev-eus2-db-bootstrap ...`).
7. Operator verifies the Job's execution log shows the script's own final success line (`"[run_db_bootstrap] roles and grants applied (no secret values were printed above)"`) and no secret value anywhere in the log.
8. Operator populates all six Key Vault secrets (§12 step 4, CDD-067 §12 unchanged).
9. Operator builds/pushes the real backend/frontend application images (CDD-067 §7/§13, unchanged).
10. Operator runs the application-tier deployment (`deployApplicationTier=true`, CDD-067, unchanged).
11. Operator triggers the *existing, unchanged* migration Job — schema migration + seeders.
12. Business-tenant (`noetva-dev-tenant`) bootstrap occurs at the application level (§16) — unchanged, outside this artifact.

This is now genuinely executable from zero — every step's inputs exist before it runs.

## 16. `noetva-dev-tenant` creation point

Unchanged from CDD-067's own scoping: occurs after schema migration (step 11 above), at the application level, via whatever governed application-tenant-bootstrap mechanism already exists (not created, modified, or newly specified by this artifact). **Never** the Entra directory tenant GUID (`8f9e2dee-5a5b-4b33-9044-4d11691899de`) — that remains strictly the Entra `tid`, categorically distinct from the Noetva business tenant, per CDD-064/065/066's already-frozen, unchanged distinction.

## 17. Future normal migration mechanism

**Unchanged, explicit, justified:** the existing `noetva-dev-eus2-migrate` Job (§4), using the `noetva_migrate` role via its Key-Vault-backed secret, remains the *sole* ongoing schema-migration path after this one-time (or rotation-time) bootstrap completes — triggered manually by the human operator today, and eligible to become GitHub-OIDC-triggered later exactly per CDD-067 §17's own already-frozen, unchanged human-bootstrap-then-GitHub-OIDC transition model. The new bootstrap Job introduced here is never used for ordinary migrations — it exists solely for initial role creation and any future full credential-rotation event, and is not part of the normal deployment cadence.

## 18. Failure/re-entry model

1. **Safe re-entry:** the bootstrap Job's underlying SQL is idempotent (§5) — re-triggering it (e.g. after a transient failure) is safe.
2. **No mandatory delete/recreate:** the Job resource itself, once deployed (`deployDbBootstrapJob=true`), may remain declared indefinitely at effectively zero idle cost; it is not required to be torn down between uses.
3. **No secret leakage:** unchanged discipline from `run_db_bootstrap.sh`'s own design (§5) — no secret is ever echoed, logged, or passed as a bare CLI argument.
4. **No resource drift:** the Job's image/parameters are declared in the same Bicep source tree as everything else — no separate, divergent definition path.
5. **Clear operator checkpoints:** §15's 12 steps, each independently verifiable before the next.
6. **Readback before continuation:** verify the Job's success log line (§15 step 7) before proceeding to Key Vault population; verify all six Key Vault secrets exist (CDD-067's own existing requirement) before the application-tier deployment.
7. **Bounded retry:** the same `ServerIsBusy`-class transient-conflict handling already demonstrated in R5 applies identically here if the Postgres server is mid-operation from a concurrent admin-password reset.

## 19. Cost/dormancy model

The bootstrap Job costs nothing while not actively executing (`triggerType: Manual`, billed only for actual run duration — typically well under a minute for this SQL). Declaring it in Bicep (even when `deployDbBootstrapJob=false` and therefore not created at all) adds zero cost. When `true` and the Job resource exists but is not running, it remains at the same near-zero idle cost as the existing migration Job already is. This is fully consistent with Noetva's dormant-by-default DEV cost posture and introduces no new recurring charge of any kind (unlike VM/Bastion/VPN-gateway alternatives, §6).

## 20. Security invariants (binding, all 7)

1. PostgreSQL `publicNetworkAccess` remains `Disabled` — never touched, never weakened.
2. No new subnet, NSG rule, VNet peering, or public IP is introduced.
3. No public or non-Noetva-controlled image is ever referenced — the new bootstrap image is Noetva-authored, digest-pinned, pushed to the existing private ACR, identical trust model to backend/frontend/migration images.
4. BOOTSTRAP, MIGRATION, and APPLICATION credentials remain structurally distinct — never the same Azure resource, never the same Key Vault secret, never the same Job definition.
5. No secret is ever committed, printed, logged, or passed as a bare CLI argument reachable via shell history or process listing.
6. The bootstrap Job never reads Key Vault (§14) — eliminating, not relocating, the circular dependency.
7. Human-bootstrap authority for this new Job's own deployment remains identical to CDD-067 §17's unchanged model — no premature GitHub OIDC transition.

## 21. Exact implementation paths

Evidence decides **Option D** (new bootstrap-job module genuinely required) — not "no source change," not "runbook-only." A new, small Dockerfile and Bicep module are genuinely necessary (§5, §6) since nothing existing has both `psql` and the required network placement without conflating authorities.

```
CREATE = 2
MODIFY = 7
DELETE = 0
TOTAL = 9
```

| # | Path | Type | Purpose |
|---|---|---|---|
| 1 | `infra/azure/db-bootstrap/Dockerfile` | CREATE | Minimal, Noetva-controlled image: `psql` (`postgresql-client`) + copies the already-committed `run_db_bootstrap.sh`/`001_create_roles_and_grants.sql`; no other tooling |
| 2 | `infra/azure/modules/container-apps-job-db-bootstrap.bicep` | CREATE | The new Job module — ADMIN-authority, structurally separate from `container-apps-job-migration.bicep`; declares exactly the 3 secure password parameters + host + admin user as Container Apps secrets/env vars, no Key Vault reference of any kind |
| 3 | `infra/azure/main.bicep` | MODIFY | New `deployDbBootstrapJob` boolean parameter (default `false`) + 3 new `@secure()` password parameters + 1 new bootstrap-image-reference parameter, pass-through only |
| 4 | `infra/azure/resources.bicep` | MODIFY | New parameters (mirrored from `main.bicep`); new conditional module instantiation for the bootstrap Job, gated `if (deployDbBootstrapJob)` |
| 5 | `infra/azure/environments/dev/main.parameters.json` | MODIFY | `"deployDbBootstrapJob": { "value": false }` — safe default; no real secret value committed |
| 6 | `infra/azure/environments/staging/main.parameters.json` | MODIFY | same |
| 7 | `infra/azure/environments/demo/main.parameters.json` | MODIFY | same |
| 8 | `infra/azure/environments/prod/main.parameters.json` | MODIFY | same |
| 9 | `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` | MODIFY | New Part documenting §15's exact sequence, superseding no existing Part, inserted between the existing Part 17 (Key Vault) and Part 23 (Pass 1) content already established by CDD-067 |

**Explicitly prohibited:** any `backend/*`, `frontend/*`, `keycloak/*`, `docker-compose.yml`, `.github/workflows/*` path; any CDD-063/064/065/066/067-governed value; the existing `container-apps-job-migration.bicep` (must remain untouched — its authority must not be broadened to also perform bootstrap); deletion of `db-bootstrap/001_create_roles_and_grants.sql` or `run_db_bootstrap.sh` (reused verbatim, not rewritten); deletion of any existing Azure resource.

## 22. Test requirements

1. Static check (extend `infra/azure/validation/static_architecture_checks.py`, an already-existing, already-authorized-category file — verify at implementation time whether this specific check needs a new assertion added there or is already structurally covered): the bootstrap Job module must declare zero `keyVaultSecretRefs` / zero Key Vault reference of any kind (proves §14 mechanically, not merely by inspection).
2. Static check: the bootstrap Job's identity must not receive `Key Vault Secrets Officer`/`Contributor`/`Owner` — only whatever minimal role (if any) it needs (likely `AcrPull` only, since it needs no Azure-side secret access at all under this design).
3. Static check: `deployDbBootstrapJob` must default to `false` in every committed environment parameter file.
4. Confirm the new Dockerfile does not install anything beyond `postgresql-client` and copy the two already-existing bootstrap files — no expanded surface.

## 23. Real-Azure VM requirements (binding, static verification alone is insufficient — proven by R5's own experience)

The implementation phase's VM must prove, from real Azure execution:
1. The bootstrap Job, once deployed and triggered, resolves `noetva-dev-eus2-pg.postgres.database.azure.com` to a private address (not a public one) — via its own execution log or an explicit `nslookup`/equivalent step in the script's own diagnostic output, or independently via Job execution success itself (a `psql` connection succeeding at all is proof of correct private DNS resolution + TCP reachability + TLS negotiation).
2. TCP port 5432 is reachable from inside the Job (implied by success of step 1, but must not be merely assumed from source review).
3. `psql` authenticates successfully as the ADMIN login using the delivered password.
4. `001_create_roles_and_grants.sql` completes without error; `noetva_app`/`noetva_migrate` roles independently confirmed to exist afterward (e.g., via a subsequent read-only query or the script's own success message).
5. No secret value appears anywhere in the Job's execution logs (`az containerapp job execution list`/logs, independently inspected).
6. PostgreSQL `publicNetworkAccess` independently re-confirmed still `Disabled` after this entire sequence.
7. The foundation stage (VNet, ACR, Key Vault, CAE, other identities) remains healthy and untouched throughout.
8. After Key Vault population (a separate, already-governed step), the application-tier deployment's prerequisites (CDD-067 §Application-Stage Preflight) become genuinely satisfiable — not claimed satisfied without this proof.

## 24. STOP conditions carried into implementation

Implementation must STOP (not silently repair) if: the bootstrap Job requires any Key Vault reference to function (would reintroduce the cycle §14 disproves); the bootstrap image cannot be built without a public base image incompatible with the digest-pinned/private-registry policy (a minimal Debian/Python base with `postgresql-client` installed via `apt-get` is expected to be trivially available and Noetva-buildable — if this proves false, STOP and report); any real Azure evidence contradicts §3's network-placement proof; the DB-bootstrap SQL requires modification to run correctly (it must not — §5 already found it correct); or the implementation path set grows beyond §21's exact 9 paths.

---

*This document authorizes governance only. It does not implement, deploy, or verify anything itself. It does not authorize any Azure, Entra, or GitHub-settings mutation, and does not authorize resetting the PostgreSQL admin password, populating Key Vault, building/pushing images, or deploying the application tier — all of those remain for the implementation phase, exactly as CDD-067 already established for its own scope.*
