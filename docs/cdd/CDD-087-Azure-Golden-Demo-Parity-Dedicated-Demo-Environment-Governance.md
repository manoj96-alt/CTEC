# CDD-087 — Azure Golden Demo Parity: Dedicated Demo Environment Governance

Version: 1.0 FROZEN
Status: FROZEN (governance only — no implementation authorized directly by this document beyond what its
own embedded Artifact Authorization, §20/§21, names)
Implementation state: NOT STARTED
Precedent phases (same program): `AZURE-GOLDEN-DEMO-PARITY-DR`, `AZURE-GOLDEN-DEMO-PARITY-DR-R1`,
`AZURE-GOLDEN-DEMO-PARITY-DR-R2`, concluding `READY FOR AZURE-GOLDEN-DEMO-PARITY-G`. This document resolves
DR/DR-R1/DR-R2's open architecture decisions and freezes them as binding governance. It does not reopen any
DR-series discovery; every fact those phases established (deployed-image provenance, schema/migration state,
CIAM configuration, IaC topology, seeder idempotency contract) is treated here as given, re-cited only where
a freeze decision depends on it.

**Publication note**: per this phase's own explicit instruction, this is the single governance artifact for
the program — architecture freeze and Artifact Authorization are combined in one document rather than the
CDD/companion-AA two-file split used elsewhere in this repository (CDD-084, CDD-085, CDD-086). No second file
is authorized by this phase.

## 1. Authoritative baseline

```
Local HEAD (unrelated branch): 1b456a6d7f1c42603d2f892925652ee13a96d567  (postgres-data-model-closure/step-13)
origin/main:                   171a398af6d4af6bd2149ff69879f4cdc178ed3e
GitHub main (independently re-verified via gh api):  171a398af6d4af6bd2149ff69879f4cdc178ed3e
Working tree exception:        untracked docs/product/ (pre-existing, unrelated CEO/architecture reference
                                 material — NOETVA_CEO_Product_Mastery_*, NOETVA-DETAILED-TECHNICAL-
                                 ARCHITECTURE.md, etc. — confirmed by direct listing; untouched by this phase)
Highest existing CDD on origin/main:  CDD-086  →  this document is CDD-087
Governance branch:             azure/golden-demo-parity-g (new, from origin/main, clean worktree)
```

Main has not moved since DR-R2. No DR-R2 conclusion is reopened; this document freezes them and closes two
further architecture gaps DR-R2 left implicit (exact Container Apps Job mechanism for restore invocation;
exact uniqueness-table mutation boundary — see §7/§8 below, which **narrows** DR-R2's assumption after direct
evidence).

**Numbering note**: two unrelated, unmerged branches in this repository's broader history each independently
claimed a "CDD-087" title (`Backend-Mypy-Baseline-Closure-Architecture...`, `Noetva-Material-Aware-
Alternative-Supplier-Discovery-I1...`); neither is an ancestor of `origin/main` (`git merge-base --is-ancestor`
returns false for both), and `origin/main`'s own CDD sequence — the authoritative source per this phase's own
§1 — has no CDD-087. Per this repository's established practice of resolving numbering at merge time (a
later-merging PR renumbers if a collision has landed first), this document claims CDD-087 as the correct next
number in `origin/main`'s own truth. If either other branch merges into main before this document's own PR,
this document must be renumbered before merge — not before.

## 2. Mission (binding, restated)

Freeze the exact architecture, safety contracts, Artifact Authorization, Azure Resource Authorization,
operator prerequisites, implementation sequence, and VM acceptance contract for a dedicated, isolated Azure
Golden Demo environment (`demo.noetva.ai`) — without inventing anything not already evidenced by direct
repository/Azure/CIAM truth, and without weakening any existing governed invariant (most materially: CDD-084
§21/§25's own "no DELETE is ever authorized on any `oqi_uniqueness_*` table" rule, discovered in this phase
to directly bound what a Golden restore mechanism may do — see §8).

## 3. Environment-role freeze

```
app.noetva.ai   -- development / ordinary evolving product showcase.
                   Must NOT become the deterministic Golden Demo environment. Ordinary product development
                   continues against it unconstrained by Golden-story determinism.

demo.noetva.ai  -- isolated, deterministic, resettable CEO/VC Golden Demo environment.
                   Purpose: CEO demos, VC demos, appropriate customer demonstrations, product screenshots,
                   presentation recording, Golden browser-crown certification.
                   Its deterministic state changes only through the governed restore mechanism (§7-§10) or a
                   governed redeploy (§17) -- never through ad hoc manual product use.
```

No existing `rg-noetva-dev` or `app.noetva.ai` resource is repurposed by anything this document authorizes.

## 4. Azure topology freeze

The dedicated topology is exactly the one already represented by `infra/azure/main.bicep` /
`infra/azure/resources.bicep` / `infra/azure/modules/*.bicep`, parameterized per environment via
`infra/azure/environments/demo/main.parameters.json` (`namePrefix: "noetva-demo-eus2"`). Deploying it creates,
inside a new `rg-noetva-demo` resource group: a Container Apps Environment; frontend and backend Container
Apps; the existing migration Job pattern (`container-apps-job-migration.bicep`); the existing db-bootstrap Job
pattern (`container-apps-job-db-bootstrap.bicep`); a **new** Golden-restore Job (§7); an ACR; a Key Vault; a
PostgreSQL Flexible Server (private-network-only, mirroring dev's own `publicNetworkAccess: Disabled`); the
private VNet/DNS this requires; managed identities; Log Analytics; alerts; a managed certificate/custom-domain
binding for `demo.noetva.ai`. No existing `rg-noetva-dev` resource is modified.

## 5. Database isolation freeze

A **dedicated** PostgreSQL Flexible Server for demo — never the existing dev server, never a shared server
with a separate database, never a shared schema. Reason (hard safety boundary, restated): Golden restore must
be structurally incapable of affecting `app.noetva.ai`'s data. The frozen restore safety predicate's Check 3
(§9) enforces this at the application layer; dedicated infrastructure enforces it at the topology layer —
both are required, neither substitutes for the other.

## 6. Existing `demo-reset` boundary freeze

`database_cli.py`'s existing `demo_reset()`/`_assert_demo_reset_allowed()` (host allowlist
`{localhost, 127.0.0.1, postgres}`, gated by `CTEC_DEMO_RESET_ALLOWED=true`) remains **completely unchanged**
by this program. Specifically frozen as forbidden:

- No Azure hostname is added to `_DEMO_RESET_ALLOWED_HOSTS`.
- `CTEC_DEMO_RESET_ALLOWED`'s semantics are not weakened, widened, or given an Azure-recognizing branch.
- `demo_reset()`'s own downgrade-base/upgrade-head/reseed-everything behavior is never invoked against Azure.
- `demo-reset` is not reinterpreted, documented, or repurposed as "the Azure reset mechanism" anywhere.

`demo-reset` remains local/container-test safety-scoped behavior, full stop. Azure Golden restoration is a
**separate**, purpose-built mechanism (§7-§10), sharing no allowlist, no flag, and no destructive schema
rebuild with `demo-reset`.

## 7. `golden-demo-restore` command and invocation mechanism freeze

**Command name** (frozen, following `database_cli.py`'s existing `argparse` kebab-case subcommand
convention — `migrate`, `reset-db`, `seed`, `demo-reset`, `demo-verify`): `golden-demo-restore`.

**Purpose**: restore only the deterministic Golden fixture's *mutable remediation-lifecycle decision state*
to its certified starting condition, then re-invoke the existing, unmodified `DemoOqiSeeder.seed()` so
context/evidence/evaluation state is freshly (idempotently) present.

**It must NOT**: downgrade schema; rebuild schema; delete migration history; reset any tenant other than
`ctec-demo-tenant`; touch any database other than the dedicated demo PostgreSQL server; broaden `demo-reset`'s
allowlist; mutate any `oqi_uniqueness_*` table (§8); mutate any tenant's data but the Golden tenant's.

**Invocation mechanism** (frozen, discovered from direct evidence, not invented): `azure-deploy.yml`'s
existing `migrate` job does **not** invoke `database_cli.py` as a CLI at all — the migration Container Apps
Job (`container-apps-job-migration.bicep`) overrides the backend image's `command` with an inline
`/bin/sh -c` script (`python -m alembic upgrade head`, then inline `python -c` seeder calls). `db-bootstrap`
follows the identical dedicated-Job pattern, gated by its own independent `deployDbBootstrapJob` boolean,
wired in `resources.bicep` alongside — not nested inside — `deployApplicationTier`.

Golden restore mirrors this exact, already-established pattern rather than inventing a new one: a **third**
dedicated Container Apps Job, `noetva-demo-eus2-golden-restore`, defined by a new Bicep module
`infra/azure/modules/container-apps-job-golden-restore.bicep` (structurally identical to
`container-apps-job-migration.bicep` — same image, `triggerType: Manual`, same managed-identity/ACR-pull
shape), gated by a new, independent boolean parameter `deployGoldenRestoreJob` (default `false`), wired in
`resources.bicep`/`main.bicep` exactly the way `deployDbBootstrapJob` already is. Unlike the migration Job's
ad hoc inline Python (justified there because migration/idempotent-production-seeder logic is simple), the
restore Job's script is exactly two CLI invocations, because the restore logic itself (5-check predicate,
scoped transactional delete, reseed) is complex enough to deserve real, tested Python in `database_cli.py`
rather than duplicated Bicep-embedded shell:

```
set -e
python -m app.infrastructure.persistence.database_cli golden-demo-restore
python -m app.infrastructure.persistence.database_cli demo-verify
```

Both commands share the container's existing `CTEC_DATABASE_URL` env var. **No new Key Vault secret is
required**: the Job reuses the existing `ctec-database-url` secret (the same `noetva_app`-role connection
string the backend/frontend Container Apps already use), per §11's "no new DB role" freeze — it must **not**
reuse `ctec-migration-database-url` (the `noetva_migrate`/admin-adjacent role the migration Job alone uses).

## 8. Exact restore table/order freeze — and a correction to the governing prompt's own assumption

Direct evidence (`git show origin/main:backend/app/infrastructure/persistence/models/oqi_uniqueness.py`'s own
module docstring): *"No DELETE is ever authorized on any table here (CDD-084 §21/§25) — every table is either
an immutable append-only ledger or a versioned, retire-only policy envelope."* This is an existing, frozen,
superior-precedence governance invariant this program has no authority to reopen or override.

This directly narrows the governing prompt's own assumption (its §8) that restore must clean up "the exact
uniqueness steward-adjudication persistence" for the Aurora X1/AURORA X1 pair. It must not, and cannot without
violating CDD-084. The correct, evidence-based resolution:

- `demo_oqi_seeder.py` **never writes** to `oqi_uniqueness_adjudications` (confirmed by direct code read —
  `_seed_h6_context`'s own docstring: *"Zero UniquenessPolicy, blocking, or adjudication change"*). The
  Aurora X1/AURORA X1 uniqueness candidate is produced purely by `OqiUniquenessEvaluationService`'s real
  evaluation logic, idempotently, from the seeded `Product` entities — never from an adjudication action.
- The certified Golden browser-crown path (independently re-verified this session's own
  `NOETVA-DEMO-READINESS-VM` 45-step crown) **never invokes adjudication** on this candidate — P20/P21 of the
  CEO/VC contract (§19) require it to remain candidate-only throughout the certified story.
- Therefore: **as long as the governed Golden path is what actually runs**, no `oqi_uniqueness_*` row ever
  needs restoring, because none of them is ever mutated by the story. Golden restore's scope correctly
  excludes all five `oqi_uniqueness_*` tables entirely — not because deletion was unnecessary to discover, but
  because CDD-084 forbids it and the Golden path never requires it.
- **Residual risk, explicitly frozen as a Material Risk (§26)**: if an operator manually exercises the
  adjudicate action against this specific candidate pair outside the certified script (e.g., exploring the
  UI during a live demo), the resulting `oqi_uniqueness_adjudications` row is permanent and irrevocable by
  design (CDD-084's own invariant) — golden-demo-restore cannot and must not attempt to undo it. This is a
  presenter-discipline constraint, documented in the operator runbook (§18 item 9 addendum below), not a code
  defect.

**Frozen restore DELETE scope — exactly four tables, exactly this order** (child before parent, matching
existing FK constraints in `oqi_remediation.py`, all scoped to `tenant_id = 'ctec-demo-tenant'`):

```
1. DELETE FROM oqi_remediation_authorizations WHERE tenant_id = 'ctec-demo-tenant';
   (FK: fk_oqi_remediation_authorizations_tenant_instruction, fk_oqi_remediation_authorizations_case_id)

2. DELETE FROM oqi_remediation_instructions WHERE tenant_id = 'ctec-demo-tenant';
   (FK: fk_oqi_remediation_instructions_tenant_case, fk_oqi_remediation_instructions_candidate_id)

3. DELETE FROM oqi_remediation_candidates
   WHERE case_id IN (SELECT case_id FROM oqi_remediation_cases WHERE tenant_id = 'ctec-demo-tenant');
   (this table has no tenant_id column of its own -- scoped via its case_id -> oqi_remediation_cases FK,
    fk_oqi_remediation_candidates_case_id; confirmed by direct schema read, not assumed)

4. DELETE FROM oqi_remediation_cases WHERE tenant_id = 'ctec-demo-tenant';
```

No other table is in scope. `oqi_remediation.py`'s own module docstring confirms exhaustiveness: *"Four
tables... No existing OQI1/2/3/4, Gate S, or Gate V table is altered."* There is no separate
external-execution-report table — `external_execution_claimed`/`external_execution_claimed_on` are plain
columns on `oqi_remediation_cases` itself, cleared by row deletion, requiring no extra step.

After the four deletes: re-invoke `DemoOqiSeeder(session).seed(tenant_id="ctec-demo-tenant")` unchanged.

## 9. Safety predicate freeze

All five checks must pass, in this order, before the first `DELETE`. Any single failure: zero mutation,
non-zero exit, an explicit diagnostic naming which check failed, no partial cleanup.

```
CHECK 1 -- Explicit opt-in
    os.environ.get("CTEC_GOLDEN_DEMO_RESTORE_ALLOWED") == "true"
    else: refuse.

CHECK 2 -- Application-declared environment
    settings.environment == "demo"
    (requires the environment Literal widening authorized in §11)
    else: refuse.

CHECK 3 -- Database host identity
    make_url(settings.database_url).host == the governed dedicated demo PostgreSQL FQDN,
    compared against a NEW, dedicated constant private to this command
    (e.g. _GOLDEN_RESTORE_ALLOWED_HOST -- exact name decided at implementation time; it must be a distinct
    name/constant from _DEMO_RESET_ALLOWED_HOSTS, never appended to it, per §6).
    else: refuse.

CHECK 4 -- Migration head
    the database's own alembic_version.version_num == "0048_oqi_remediation_mutex"
    (independently re-verified this phase: this is the exact `revision =` string literal in
    backend/app/infrastructure/persistence/migrations/versions/
    0048_oqi_remediation_authorization_mutual_exclusion.py -- the filename's own longer slug is not the
    stored value; the stored value is the short revision id)
    else: refuse.

CHECK 5 -- Foreign-tenant absence
    before any DELETE: zero rows exist in any of the four oqi_remediation_* tables (§8) for any tenant_id
    other than "ctec-demo-tenant"
    else: refuse (do not silently skip foreign rows -- refuse the whole operation, since a database that is
    not exactly what it should be is not safe to restore blindly).
```

## 10. Transactionality freeze

Predicate verification (Checks 1-5) → scoped four-table cleanup (§8) → `DemoOqiSeeder.seed()` re-invocation
must not leave a partially-reset Golden environment if any step fails partway.

Both the cleanup and the reseed already run inside SQLAlchemy `Session`-scoped units of work in this
codebase's own established pattern (`demo_reset()` itself commits once at the end of its own multi-step
sequence, per direct code read). Golden restore is frozen to follow the identical discipline: **one
`Session`, one final `commit()`**, wrapping predicate-verified cleanup and reseed together; any exception
before that single commit leaves the database entirely unchanged (a rolled-back transaction), never
partially cleaned. No cross-transaction two-phase behavior is authorized or needed — the existing
single-session/single-commit pattern already used by `demo_reset()` is the narrowest sufficient mechanism, so
implementation must reuse it exactly rather than inventing a new transactional-boundary abstraction.

## 11. DB privilege freeze

Golden restore runs as the existing `noetva_app` role — the same role the backend/frontend Container Apps
already use via the existing `ctec-database-url` Key Vault secret. Per `infra/azure/README.md`'s own,
adversarially-verified grant model, `noetva_app` already has `SELECT`/`INSERT`/`UPDATE`/`DELETE` on every
table `noetva_migrate` creates, via `ALTER DEFAULT PRIVILEGES` — sufficient for §8's DELETE and for
`DemoOqiSeeder`'s own INSERTs. No DDL/schema-owner/migration-owner/admin privilege is added. **No new
database role is authorized by this document.**

## 12. Environment configuration freeze

`backend/app/core/config.py`'s `environment: Literal["development", "test", "production"] = "development"`
(exact current field, line 13) is widened to:

```python
environment: Literal["development", "test", "staging", "demo", "production"] = "development"
```

covering all four Bicep-governed environments (`dev`/`staging`/`demo`/`prod`, per `main.bicep`'s own
`@allowed(['dev','staging','prod','demo'])` for `environmentName` — note `environment` here is the
backend's *own* runtime label, populated from `CTEC_ENVIRONMENT`, independently confirmed non-branching at
its only two read-sites: `backend/app/api/config/router.py:15` (`PublicConfigResponse(environment=...)`) and
`backend/app/main.py:43` (a structured log line) — re-confirmed this phase, both still purely descriptive.
No third read-site was introduced anywhere in `backend/app/` between DR-R2 and this phase (origin/main
unchanged).

`environment == "demo"` is used exactly once by new code: Check 2 of the restore safety predicate (§9). It is
a safety assertion and descriptive configuration value — **never** an authentication or authorization bypass.
No branch anywhere in `backend/app/api/supplier_risk/authentication.py` or any authorization-decision path
may key off `settings.environment`.

## 13. `demo-verify` contract — governance decision

DR-R2 found the existing `demo_verify()` reusable (correct tenant constant, correct DB-only coupling) but
incomplete for three CEO/VC-central facts. **Frozen: the stronger contract.** `demo-verify` is extended so a
single, authoritative read-only command verifies every Golden starting-state invariant needed before a
presentation, rather than shipping an Azure Golden environment whose readiness gate is known-incomplete.

Required assertions (frozen, at minimum — existing eight plus these three, using the exact enum/string values
already independently verified live in this session's own `NOETVA-DEMO-READINESS-VM` certification, not
invented here):

```
(existing, unchanged)     Golden Supplier name = "Meridian Cell Components"
(existing, unchanged)     SAP evidence = US, PLM evidence = MX
(existing, unchanged)     Finding OPEN (the SAP/PLM Country-of-Origin disagreement)
(existing, unchanged)     H6 Aurora X1/AURORA X1 candidate pair present
(existing, unchanged)     uniqueness adjudication absent for that pair
(existing, unchanged)     [remaining pre-existing assertions, unchanged]
(NEW)                     Business Impact = HIGH
(NEW)                     Reliance state = RELIANCE_AT_RISK
(NEW)                     Ask Noetva dependency-graph support exists (Meridian Cell Components -> Aurora X1
                          traversal is answerable through real ontology data, not merely that the seed rows
                          exist)
```

Plus, restated as still-required (already covered by the existing function, re-confirmed present, not new):
Aurora X1 ontology chain (Meridian → Battery Cell → BOM → Aurora X1); Agent Investigation not invoked;
remediation begins in its certified initial (pre-restore-target) state; uniqueness candidate exists and is
not adjudicated/merged.

`demo-verify` remains strictly **read-only**. Any mismatch: non-zero exit, naming the specific failed
assertion. This governance decision means `database_cli.py`'s single MODIFY (§20) carries both
`golden-demo-restore` and the strengthened `demo_verify()` — no additional file is authorized or required.

## 14. Restore lifecycle freeze

```
INITIAL PROVISIONING
  infra provision (Bicep) -> db-bootstrap Job -> migrate Job -> golden-demo-restore Job
    -> demo-verify (chained inside the same Job, §7) -> health checks -> browser crown

PRE-DEMO (repeatable, the normal operating rhythm)
  explicit golden-demo-restore Job invocation (via the governed workflow, §15)
    -> demo-verify (chained) -> application health check -> authentication pre-flight -> CEO/VC demo

ROUTINE CODE DEPLOYMENT (azure-deploy.yml, unmodified by this program)
  build -> migrate -> deploy
  -- does NOT invoke golden-demo-restore. An ordinary code push to demo must never silently destroy an
     in-progress or freshly-presented Golden state.
```

## 15. Restore workflow freeze

A **new**, dedicated GitHub Actions workflow, following this repository's exact existing naming convention
(`azure-deploy.yml`, `azure-lifecycle-{extend,hold,nightly-sweep,restart-monitor,start,status,stop}.yml`):

```
.github/workflows/azure-golden-demo-restore.yml
```

Frozen behavior: `workflow_dispatch`-only trigger, with **no free-text environment input** — it must accept
no environment parameter at all (or, if the underlying `az` calls need a parameter for uniformity with other
workflows' structure, a single fixed literal `demo` with no other permitted value enforced in the workflow
YAML itself, never user-suppliable) — dev/staging/prod must be structurally unreachable, not merely
discouraged. Steps: GitHub OIDC login (`azure/login@v2`, mirroring `azure-deploy.yml`'s own `migrate` job
exactly); start the `noetva-demo-eus2-golden-restore` Job (`az containerapp job start`); poll
`az containerapp job execution list` for `Succeeded`/`Failed` (identical wait-loop shape to `azure-deploy.
yml`'s own migration-job wait step); surface pass/fail as the workflow's own exit status. No dispatch of this
workflow is ever wired to run automatically from any other workflow or on any push/schedule trigger.

## 16. CIAM architecture freeze

Reuse the existing Azure AD CIAM (Entra External ID) directory — the same tenant already serving dev
(`8f9e2dee-5a5b-4b33-9044-4d11691899de`). **No new CIAM tenant.** Create, dedicated to demo:

- one frontend SPA app registration
- one backend API app registration (exposing the same three delegated scopes as dev, §17)

No existing dev app registration is modified.

## 17. Two-principal freeze

Exactly two governed demo identities:

```
Demo Steward   (requester)  -- distinct Entra user object, distinct `sub`
Demo Approver  (authorizer) -- distinct Entra user object, distinct `sub`
```

Both carry the identical `noetva_tenant_id = ctec-demo-tenant` claim and the identical delegated-scope set.
The `requested_by != decided_by` invariant — enforced today by `OqiRemediationService`'s own application-level
comparison, independently proven this session's own VM certification (two real Keycloak principals) — is what
prevents self-authorization. This program does **not** introduce any UI-only or scope-only substitute for it.

## 18. CIAM tenant claim and JWT contract freeze

**Mechanism** (demo-only, frozen): a native Entra External ID custom **directory/user attribute** plus a
**claims-mapping policy**, emitting `noetva_tenant_id = ctec-demo-tenant` for both demo users. Zero code, zero
new Azure Function, zero new infra resource beyond the two user objects, the attribute, and the policy.

This is conclusively **not** how `TokenIssuanceStart` (documented at exactly two prose locations in
`infra/azure/README.md`, zero code/infra anywhere in the repository — re-confirmed this phase via repo-wide
grep) works, and this mechanism is **explicitly bounded as demo-only** — it must never be documented or
represented as Noetva's production multi-tenant onboarding architecture. Production onboarding remains
expected to use a genuine `TokenIssuanceStart`+Function mapping (or a separately governed successor); building
that Function is explicitly **not** authorized by this program.

**JWT contract** (frozen, matches dev's own live, working, non-placeholder configuration exactly):

```
iss                = the governed Azure AD CIAM issuer (demo's own app registrations, same tenant as dev)
aud                = the dedicated demo backend API app registration's client id
sub                = the authenticated demo principal (Steward or Approver)
scp                = delegated scopes (§19)
noetva_tenant_id   = ctec-demo-tenant
```

Existing fail-closed backend behavior (`backend/app/api/supplier_risk/authentication.py`'s `_principal()`,
re-confirmed unchanged this phase) remains fully authoritative and requires zero modification: missing/blank
`sub` → `AUTH_PRINCIPAL_MISSING`; missing/blank tenant claim → `AUTH_TENANT_MISSING_OR_AMBIGUOUS`; no fallback,
no default tenant, ever. Wrong issuer/audience/signature/key-source and absent required scope fail closed
through this same existing, unmodified mechanism (issuer/audience/JWKS validation and scope-authorization
checks already exercised, unmodified, by every certification this whole program has run).

## 19. Remediation scope freeze

Exactly the three scope names already present in code (`backend/app/api/oqi/router.py`,
`backend/app/api/oqi/dependencies.py`'s own docstring) — re-confirmed this phase, not invented:

```
oqi-remediation:prepare
oqi-remediation:authorize
oqi-remediation:report-execution
```

Both demo principals receive the identical scope set. Delivery is the standard Entra "exposed API scope on
the backend registration + delegated permission granted to the frontend SPA registration + consent for the
two demo users" model — no custom code path, matching the already-live, provider-agnostic `scp`-claim parsing
this backend already performs.

## 20. Migration freeze

Certified target: `0048_oqi_remediation_mutex` (the exact `revision =` string; independently re-derived this
phase by reading every migration file's own `revision`/`down_revision` literals in sequence — not merely
trusting the highest filename number). Chain, most-recent five:

```
0044_oqi4_r1_current_tenancy -> 0045_oqi_connector_ingestion -> 0046_oqi5_remediation_tenancy
  -> 0047_oqi_h6_uniqueness -> 0048_oqi_remediation_mutex   (head)
```

Migration execution uses the existing `migrate` Container Apps Job and `noetva_migrate` role, unmodified. No
alternative migration mechanism is authorized by this program.

## 21. Deployment/provenance freeze

Frontend and backend must originate from the same governed source SHA for a given deployment. Initial Golden
deployment target: `171a398af6d4af6bd2149ff69879f4cdc178ed3e`, unless main moves through a separately
reviewed/governed implementation-commit sequence before I3 (§25) executes — in which case the VM (§27) must
record whatever the actual deployed SHA is, never assume this one silently. Provenance chain required at VM
time: source SHA → image tag → immutable digest → Azure Container App revision, for both frontend and
backend, with the digests as the load-bearing identity (not timestamps).

## 22. First-run deployment risk freeze

`azure-deploy.yml` has zero recorded runs, for any environment (`gh api .../actions/workflows/353737742/runs
--jq '.total_count'` → `0`, independently re-confirmed by DR-R1, not reopened here). Its first invocation
against demo must not be treated as routine. Before the first real deployment: static workflow YAML review;
GitHub Environment `demo` variable/secret completeness check; OIDC federation verification (a real, harmless
`az account show` via the workflow's own login step, before any mutating step); target-resource existence
verification (`rg-noetva-demo`, the exact Container App/Job names); ACR reachability check. During the actual
first run: capture every job's output. Any partial migration/deployment failure → **STOP**, do not manually
patch forward without a separately governed correction. Frontend/backend digest skew is a material failure,
not a warning.

Additionally, **`az bicep build`** (or `az deployment sub what-if`) against every new/modified `.bicep` file
must be run and its output captured as part of I1's own static validation (§25) — this repository's CI
currently runs no Bicep validation at all (re-confirmed this phase, `ci.yml` has zero `bicep`/`az deployment`
references), so this check has no existing CI gate to rely on and must be performed explicitly, manually,
before any `az deployment` command is ever issued against `rg-noetva-demo`.

## 23. DNS/TLS freeze

Public hostname: `demo.noetva.ai`. DNS itself is confirmed (DR/DR-R1, not reopened) to have no IaC
representation anywhere in this repository — it is, and remains, a manual operator prerequisite (§24 item 8),
exactly as `app.noetva.ai`'s own DNS record already is. Required, in order: DNS record creation → Container
Apps custom-domain hostname binding → Azure-issued managed certificate → TLS validation. No production/dev DNS
record is altered by anything this document authorizes.

## 24. Secrets/GitHub Environment freeze

Dedicated demo Key Vault holds: PostgreSQL admin password; `noetva_app` password (backing `ctec-database-url`,
reused by both the application containers and the new golden-restore Job, §7); `noetva_migrate` password
(backing `ctec-migration-database-url`, migration Job only). No new secret category is introduced by
golden-demo-restore — it deliberately reuses an existing secret. Secrets are never committed, never printed,
never copied from dev "for convenience." GitHub Actions authentication continues via OIDC federation, not
stored Azure client secrets, matching every existing workflow.

GitHub Environment `demo` already exists as an empty shell (`gh api .../environments/demo/variables` and
`/secrets` both independently re-confirmed empty by DR-R1, not reopened). Populate only the exact variables
the existing `azure-deploy.yml` and the new `azure-golden-demo-restore.yml` actually reference by name
(`NOETVA_CICD_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, and whatever `NOETVA_ACR_*`/`NOETVA_OIDC_
*` names the workflows already use verbatim for other environments) — no invented alias, no new variable name
not already dictated by the workflow YAML itself. Dev/staging/prod GitHub Environments are not touched.

## 25. Cost/lifecycle freeze

`frontendMinReplicas = 0`, `backendMinReplicas = 0` (already the demo parameters file's own values, confirmed
by DR-R1, not reopened). Operating model: start before a presentation, verify, demonstrate, stop afterward.
The existing nightly sweep lifecycle automation remains the safety net for any environment left running
unintentionally. Presentation reliability is never compromised to save a few minutes of Container Apps runtime
cost — if there is ever a real tension between "cheaper" and "will not embarrass someone in front of a CEO or
VC," reliability wins, unconditionally.

## 26. CEO/VC Golden contract freeze

The final demo environment must prove, in one continuous, real, Azure-hosted session:

```
P1  Exact deployment provenance known (source SHA, both digests, both revisions).
P2  Schema at governed head (0048_oqi_remediation_mutex).
P3  Meridian Cell Components present.
P4  Aurora X1 Battery Cell / BOM / Product present.
P5  Ontology: Meridian -> Battery Cell -> BOM -> Aurora X1.
P6  SAP = US.
P7  PLM = MX.
P8  Finding OPEN.
P9  Business Impact HIGH.
P10 RELIANCE_AT_RISK.
P11 Agent Investigation honestly shows not invoked.
P12 Remediation begins in certified initial state.
P13 Prepare produces expected candidates.
P14 Requester cannot self-authorize.
P15 Distinct Approver can authorize.
P16 Exactly one candidate becomes APPROVED.
P17 Sibling becomes SUPERSEDED.
P18 Execution report accepted exactly once.
P19 Re-evaluation leaves Finding OPEN while source evidence still disagrees.
P20 Aurora X1 / AURORA X1 remains candidate-only.
P21 No automatic uniqueness merge.
P22 Ask Noetva "Which products depend on Meridian Cell Components?" -> Aurora X1, via real ontology traversal.
P23 Real Azure AD CIAM authentication used.
P24 Two distinct CIAM principals used.
P25 Tenant isolation proven.
P26 app.noetva.ai remains untouched.
```

## 27. Trust invariants freeze

No implementation authorized by this document, or any later phase in this program, may weaken:

```
MAJORITY != TRUTH        AUTHORITY != TRUTH        CANDIDATE != TRUTH
AGENT != FACT            RECOMMENDATION != AUTHORIZATION      REMEDIATION != RESOLUTION
UNKNOWN != LOW            SUPERSEDED != REJECTED
```

Applies uniformly to backend, frontend, seed data, restore behavior, CIAM, browser crown, and CEO/VC-facing
screenshots — none of these get a "demo exception."

## 28. Exact Repository Artifact Authorization

```
CREATE = 4    MODIFY = 4    VERIFY ONLY = 9 (named set, not exhaustive of everything read this program)   DELETE = 0
```

### CREATE (4)

| # | Path | Purpose |
|---|---|---|
| 1 | `infra/azure/modules/container-apps-job-golden-restore.bicep` | New dedicated Container Apps Job, structurally mirroring `container-apps-job-migration.bicep` exactly (same image, `triggerType: Manual`, same managed-identity/ACR-pull shape); command overridden to `set -e; python -m app.infrastructure.persistence.database_cli golden-demo-restore; python -m app.infrastructure.persistence.database_cli demo-verify` (§7). Reuses the existing `ctec-database-url` Key Vault secret reference — no new secret. |
| 2 | `.github/workflows/azure-golden-demo-restore.yml` | New `workflow_dispatch`-only workflow (§15): OIDC login, start the golden-restore Job, poll for completion, surface pass/fail. No environment input accepts anything but a structurally-fixed `demo` target. |
| 3 | `backend/app/tests/test_database_cli.py` | Unit-level tests (no live Postgres) for the golden-demo-restore safety predicate's pure-logic checks: explicit opt-in env var, `environment == "demo"` check, host-constant comparison, and refusal behavior/exit codes/diagnostic messages for each — mirroring this repository's own unit/`_postgres`-suffix test-file split convention (e.g. `test_bootstrap.py` / no Postgres counterpart needed there; here, paired with row 4 below). Named after the module under test (`database_cli.py`), matching the dominant `test_<module>.py` convention (`test_bootstrap.py`, `test_seed_loader.py`, `test_blueprint_service.py`) — no existing test file for `database_cli.py` exists today (independently re-confirmed this phase), so this establishes, rather than follows, the file's own first test-naming precedent. |
| 4 | `backend/app/tests/test_database_cli_postgres.py` | Real-PostgreSQL integration tests: migration-head check (Check 4) against a real `alembic_version` row; foreign-tenant-absence refusal (Check 5) against seeded foreign-tenant rows; successful scoped four-table delete + reseed against a real, previously-"progressed" Golden fixture (candidate APPROVED/SUPERSEDED/report-executed state), asserting exact post-restore row state; repeated restore (run twice, assert identical end state, no duplication); transactionality (force a mid-operation failure, assert zero partial mutation); the three new `demo-verify` assertions (Business Impact HIGH, RELIANCE_AT_RISK, Ask Noetva dependency-graph support) plus a negative case for each. |

### MODIFY (4)

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/infrastructure/persistence/database_cli.py` | Add the `golden-demo-restore` subcommand (argparse wiring + `golden_demo_restore()` function implementing §7-§10/§9's exact 5-check predicate, §8's exact 4-table scoped delete, then `DemoOqiSeeder(session).seed(tenant_id=BOOTSTRAP_DEMO_TENANT_ID)`, single-session/single-commit per §10). Extend `demo_verify()` with the three new assertions (§13). No change to `demo_reset()`, `_assert_demo_reset_allowed()`, `_DEMO_RESET_ALLOWED_HOSTS`, `migrate()`, `reset_database()`, or `seed()`. |
| 2 | `backend/app/core/config.py` | Widen `environment: Literal["development", "test", "production"]` to `Literal["development", "test", "staging", "demo", "production"]` (§12). No other field changes. No new branch anywhere keyed off the new values outside `golden-demo-restore`'s own Check 2. |
| 3 | `infra/azure/resources.bicep` | Add `deployGoldenRestoreJob bool = false` parameter (mirroring `deployDbBootstrapJob`'s exact independent-gating pattern); wire a new `module goldenRestoreJob 'modules/container-apps-job-golden-restore.bicep' = if (deployGoldenRestoreJob) { ... }` block alongside (not nested inside) the existing `dbBootstrapJob`/`migrationJob` module blocks; add a corresponding output. No existing module's gating condition, parameter, or output is altered. |
| 4 | `infra/azure/main.bicep` | Add the matching `deployGoldenRestoreJob bool = false` parameter and pass-through to the `resources.bicep` module call, mirroring `deployDbBootstrapJob`'s exact existing pass-through. No other parameter/output changes. |

### VERIFY ONLY (named set; every file this program has read to ground its own decisions — re-verification
before implementation begins is still required, since origin/main may move between this freeze and I1)

| # | Path |
|---|---|
| 1 | `.github/workflows/azure-deploy.yml` |
| 2 | `infra/azure/modules/container-apps-job-migration.bicep` |
| 3 | `infra/azure/modules/container-apps-job-db-bootstrap.bicep` |
| 4 | `infra/azure/environments/demo/main.parameters.json` |
| 5 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` |
| 6 | `backend/app/infrastructure/persistence/models/oqi_remediation.py` |
| 7 | `backend/app/infrastructure/persistence/models/oqi_uniqueness.py` |
| 8 | `backend/app/api/supplier_risk/authentication.py` |
| 9 | `backend/app/infrastructure/persistence/migrations/versions/0048_oqi_remediation_authorization_mutual_exclusion.py` |

### DELETE

None.

## 29. Exact Azure Resource Authorization

```
CREATE:
  rg-noetva-demo, and inside it: Container Apps Environment; frontend Container App; backend Container App;
    migration Job (existing pattern); db-bootstrap Job (existing pattern); golden-restore Job (NEW, §7);
    ACR; Key Vault; PostgreSQL Flexible Server (private-network-only); VNet/private DNS; managed identities;
    Log Analytics; alerts.
  demo.noetva.ai managed certificate + custom-domain binding.
  CIAM: demo frontend SPA app registration; demo backend API app registration; Demo Steward user; Demo
    Approver user; one custom directory attribute; one claims-mapping policy (§16-§18).
  GitHub: populate existing, currently-empty "demo" Environment variables/secrets (§24) -- the Environment
    shell itself already exists and is not "created" by this authorization, only populated.

MODIFY existing dev (rg-noetva-dev, its CIAM app registrations, app.noetva.ai):
  NONE.

VERIFY ONLY:
  existing CIAM directory (8f9e2dee-5a5b-4b33-9044-4d11691899de); rg-noetva-dev; app.noetva.ai; the live
  dev Container Apps' own non-secret env vars (already read this program, re-verify unchanged before I2/I3).

DELETE:
  NONE.
```

## 30. Manual operator prerequisites

In order:

```
1. Generate demo DB secret values (PostgreSQL admin, noetva_app, noetva_migrate passwords).
2. Store them via the governed Key Vault/db-bootstrap mechanism (mirroring dev's own established procedure,
   infra/azure/README.md).
3. Create/configure the demo CIAM app registrations (frontend SPA, backend API).
4. Create the two demo CIAM users (Demo Steward, Demo Approver).
5. Configure the custom directory attribute + claims-mapping policy (noetva_tenant_id = ctec-demo-tenant,
   both users) -- explicitly demo-only, never documented as the production mechanism (§18).
6. Configure the three delegated scopes (§19) + consent for both users.
7. Populate GitHub Environment "demo" variables/secrets (§24) -- exact names from workflow YAML, no aliases.
8. Configure demo.noetva.ai DNS (manual -- no IaC exists for DNS anywhere in this repository, dev included).
9. Complete Container Apps managed-certificate validation/custom-domain binding.

Operational addendum (§8's residual risk): whoever presents from demo.noetva.ai must never manually invoke
the uniqueness-adjudication action against the Aurora X1/AURORA X1 candidate pair outside the certified
browser-crown script. Doing so permanently adjudicates that pair (CDD-084's own append-only-ledger design;
golden-demo-restore cannot and must not reverse it) and breaks repeatability for that specific story beat.
```

No secret value appears anywhere in this document.

## 31. Implementation phase freeze

```
I1 -- CODE + STATIC INFRA PREPARATION
   golden-demo-restore + strengthened demo-verify (database_cli.py)
   environment Literal widening (config.py)
   backend/app/tests/test_database_cli.py + test_database_cli_postgres.py
   demo parameters file real-value population (infra/azure/environments/demo/main.parameters.json)
   new Bicep module (container-apps-job-golden-restore.bicep) + resources.bicep/main.bicep wiring
   new restore workflow (azure-golden-demo-restore.yml)
   static validation: az bicep build on every new/modified .bicep file (§22); workflow YAML lint

I2 -- AZURE FOUNDATION + IDENTITY
   rg-noetva-demo resource deployment (Bicep apply)
   Key Vault secret population
   CIAM registrations/users/claims-mapping policy/scopes/consent
   GitHub Environment "demo" population
   DNS/TLS

I3 -- BUILD + MIGRATE + SEED + DEPLOY
   build the exact governed source SHA (§21)
   db-bootstrap -> migrate -> golden-demo-restore (first invocation) -> demo-verify -> deploy -> health

VM -- ADVERSARIAL AZURE GOLDEN CERTIFICATION (§32)
```

This three-phase split is frozen because it separates code/infra-definition changes (I1, fully reviewable via
normal PR diff, zero Azure mutation) from actual Azure/CIAM mutation (I2) from build/data/deploy execution
(I3) — mixing code review with live infrastructure mutation in one PR/session is exactly the kind of
casual conflation §33 of the governing prompt warns against.

## 32. VM acceptance contract freeze

The final VM phase must independently prove, without trusting any prior phase's own report:

```
SOURCE:       exact governed diff == this document's own CREATE/MODIFY set (§28), governance hash unchanged,
              no unauthorized file touched.
TESTS:        backend regression, frontend regression, the two new restore/verify test files (§28 CREATE 3-4),
              IaC validation (az bicep build), workflow YAML validation.
AZURE:        correct resource group, zero rg-noetva-dev mutation, correct dedicated PostgreSQL server,
              correct Key Vault, correct Container Apps/Jobs, correct CIAM apps/users, correct DNS/TLS.
PROVENANCE:   exact Git SHA, exact frontend digest, exact backend digest, exact Azure revisions.
DATABASE:     migration at 0048_oqi_remediation_mutex; golden-demo-restore succeeds; demo-verify succeeds;
              REPEATED restore succeeds (run it twice in the same session with no state drift); foreign-
              tenant safety (Check 5) fails closed when tested adversarially.
AUTH:         real CIAM login for both Demo Steward and Demo Approver; same noetva_tenant_id, different sub;
              correct scopes; self-authorization rejected.
BROWSER CROWN: the complete Golden story (§26 P1-P26), executed live against demo.noetva.ai.
ISOLATION:    app.noetva.ai unchanged; rg-noetva-dev unchanged; dev database unchanged.
RESET REPEATABILITY (mandatory): after completing the entire Golden story once, run golden-demo-restore
              again, prove the initial Golden state is restored exactly, then re-run the beginning of the
              browser crown and confirm it behaves identically to the first run.
```

## 33. Material risks

```
1. azure-deploy.yml remains completely unexercised (0 runs, every environment) -- its first real run against
   demo carries genuine first-run risk regardless of how carefully this document freezes the target.
2. The environment Literal widening is a real backend code change requiring its own full regression pass
   (mypy + full test suite) before I3 can rely on it -- not a zero-risk documentation change.
3. Entra claims-mapping policies are configured per-app-registration. If a future engineer copies the demo
   app registration's configuration as a template for a real customer's registration, the static-attribute
   mechanism could leak into a context expecting the real TokenIssuanceStart mechanism unless the demo-only
   boundary (§18) is explicitly called out in whatever operator runbook documents the demo app registration.
4. The Aurora X1/AURORA X1 uniqueness-adjudication residual risk (§8/§30 addendum): an accidental manual
   adjudication during a live demo is irreversible by design and requires presenter discipline, not a code
   safeguard, to avoid.
5. This document's own CDD-087 numbering may collide with either of two unrelated, unmerged branches that
   independently claimed the same number (§1) -- resolved at merge time per this repository's established
   practice, not resolved here.
```

## 34. Process attestation (this phase)

```
forks used = 0
subagents used = 0
delegated writers = 0
product-code writes = 0
Azure writes = 0
database writes = 0
CIAM writes = 0
deployment mutations = 0
repository writes = 1 (this document only)
```

Every fact this document freezes was independently re-derived this phase via `git show origin/main:<path>` /
`git ls-tree` / `git log` / `git merge-base` / `gh api` reads against the authoritative baseline (§1) — no
prior phase's conclusion was trusted without re-verification, and two of DR-R2's own implicit assumptions
were corrected after direct evidence (§7's exact Job-based invocation mechanism, replacing an unstated
assumption of a bare CLI call; §8's exclusion of all `oqi_uniqueness_*` tables from restore's DELETE scope,
replacing an assumption that they needed cleanup).

## 35. Final status

**READY FOR AZURE-GOLDEN-DEMO-PARITY-I1**

Every item enumerated in the governing prompt's own §35 fail-closed STOP list is closed with a specific,
evidence-grounded answer in this document: exact restore tables (§8), exact uniqueness persistence boundary
and its governing constraint (§8), exact test paths (§28 CREATE 3-4), exact restore workflow path (§15),
exact Azure resource topology including the golden-restore Job (§4/§7/§29), exact CIAM claim mechanism (§18),
exact scope names (§19), exact manual prerequisites (§30), exact implementation phase boundary (§31). No
placeholder, "maybe," "possibly," or "TBD" appears in any authorization table above.
