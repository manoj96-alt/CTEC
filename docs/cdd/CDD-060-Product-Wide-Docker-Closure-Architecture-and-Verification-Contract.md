# CDD-060 — Product-Wide Docker Closure: Architecture and Verification Contract

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN (Discovery + Governance only — no implementation performed by this document)
Phase: PRODUCT-WIDE-DOCKER-CLOSURE-DG
Classification: PRODUCT-WIDE DEPLOYMENT/RUNTIME CLOSURE GATE (cross-cutting; not owned by any single capability's own CDD lineage)

## 1. Purpose

This is the final product-wide technical closure gate for Noetva/CTEC after the complete OQI program
(OQI1-OQI7), OQI hardening (H1-H5), production explicit-evaluation orchestration (CDD-056/057), production
governed remediation orchestration (CDD-058), and REAL-ENTERPRISE-INGESTION (CDD-059 + R1/R2/R3, merged as
PR #193). It establishes whether the entire product can be built, started, migrated, exercised, and
verified from a genuinely fresh Docker environment with no hidden host-state dependency, and freezes the
exact contract the following `PRODUCT-WIDE-DOCKER-CLOSURE-VM` phase must prove.

This document is DISCOVER + GOVERN only. No product code, test, migration, or Docker configuration was
modified to produce it.

## 2. Authoritative baseline

Independently verified fresh at the start of this phase:

```
local origin/main:  0fd3886ea0947c60897def30ba59bc2430fd43db
GitHub main:        0fd3886ea0947c60897def30ba59bc2430fd43db
```

Equal, matches the expected post-REAL-ENTERPRISE-INGESTION baseline exactly. No drift.

Local checkout: branch `real-enterprise-ingestion/rest-connector` at `a9c3168...`, an ancestor of `main`
whose tree is byte-identical to `main`'s tree (established during VM-R3). Working tree carries one
pre-existing, unrelated, never-tracked directory, `docs/product/` (CEO/product-mastery reference material,
dated before this capability's own work began) — confirmed absent from git history, from `main`'s tree, and
from every PR diff this session has produced. It does not affect closure and is disclosed, not remediated,
here.

**PRODUCT-WIDE-DOCKER-CLOSURE-G-R1 reconciliation**: this branch was intentionally paused at this baseline
while Step 13 (POSTGRES-DATA-MODEL-CLOSURE) ran to completion on `main`. Step 13 merged via PR #194; new
authoritative main is `d3683fdf4933dfed608001d38cbb6689580815ca`, independently re-verified fresh
(local/remote/GitHub equal) at the start of G-R1. See §28 for the complete reconciliation and impact
matrix. This section's own baseline snapshot above is left unchanged as the historical record of what was
true when this document was originally frozen.

## 3. Governance-index precedent check

This repository carries two parallel governance systems: the per-capability `docs/cdd/CDD-XXX` lineage
(used continuously for OQI1-OQI7, H1-H5, orchestration, remediation, and REAL-ENTERPRISE-INGESTION), and a
heavier, formally versioned `architecture/` PAD/RFC system (`architecture/INDEX.md`, release manifests,
dependency matrices — currently at PAD-003, RFC-017, release v1.11/v1.12). None of the ~30 capability
phases merged since the last `architecture/INDEX.md` update (PAD-003, Gate F) registered themselves there,
including the prior Docker-wide closure (PR #180, "Docker-G/I/R1/R2/I-R/VM", which shipped
`DOCKER_SMOKE_TEST.md` and `.github/workflows/ci.yml`'s `containers` job directly, with no PAD/RFC and no
architecture-index entry). Following that direct, most-recent precedent: this document uses the CDD
numbering convention (next available: CDD-060) and does **not** register in `architecture/INDEX.md`.

## 4. Current Docker topology

Reconstructed from `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`,
`backend/docker-entrypoint.sh`, `keycloak/bootstrap-demo-user.sh`, `.dockerignore` (root + per-service), and
`.env.example` — read directly, not assumed from memory.

```
                         ┌─────────────────────────────┐
                         │  frontend (Next.js, :3000)  │
                         │  standalone build, non-root │
                         └───────────────┬─────────────┘
                                         │ depends_on: backend healthy
                                         ▼
   ┌────────────┐   depends_on:   ┌─────────────────────────────┐
   │  postgres  │◄── healthy ─────│  backend (FastAPI, :8000)   │
   │ 17-alpine  │                 │  entrypoint: migrate→seed→  │
   │ (no host   │                 │  serve; non-root            │
   │  port)     │                 └───────────────┬─────────────┘
   └────────────┘                                 │ (test-only, "ingestion-test" profile)
         ▲                                        ▼
         │                         ┌─────────────────────────────┐
         │                         │ connector-fixture (:8443,   │
         │                         │ internal only) — CDD-059    │
         │                         │ AA §8 in-Docker crown only  │
         │                         └─────────────────────────────┘
   ┌────────────┐  depends_on:    ┌─────────────────────────────┐
   │ keycloak   │◄── healthy ─────│ keycloak-bootstrap (one-shot│
   │ 26.0 :8081 │                 │ demo-user password set)     │
   │ (PAD-002,  │                 └─────────────────────────────┘
   │ dev/demo   │
   │ only)      │
   └────────────┘

   volumes: postgres_data (named, sole persistent volume)
   networks: single implicit Compose network (no custom network defined)
   published host ports: keycloak 8081, backend 8000, frontend 3000 (postgres publishes none)
```

- `postgres`: `postgres:17-alpine`, healthcheck `pg_isready`, no published host port (internal-only —
  correct least-exposure default).
- `keycloak`: `quay.io/keycloak/keycloak:26.0`, `start-dev --import-realm`, explicitly local/demo-only
  (PAD-002) — production CTEC authentication points at any real OIDC issuer via
  `CTEC_OIDC_ISSUER`/`CTEC_OIDC_AUDIENCE`/`CTEC_OIDC_JWKS_URL`, no code change required.
- `keycloak-bootstrap`: one-shot, `depends_on: keycloak: condition: service_healthy`, idempotent
  (`kcadm.sh set-password` overwrites, never duplicates).
- `backend`: builds from `./backend`, `depends_on: postgres: condition: service_healthy`, healthcheck hits
  `/health` (liveness only, not DB-readiness — a previously governed, disclosed, unchanged distinction).
  `CTEC_RUNTIME_HANDOFF_KEY` has no baked default and fails the whole `docker compose up` closed via
  Compose's own `:?` syntax if unset.
- `connector-fixture`: reuses the `backend` image, `profiles: ["ingestion-test"]` (never in the default
  graph), entrypoint overridden to the deterministic HTTP fixture server, no published host port, reachable
  only by Compose service name — exactly CDD-059 Artifact Authorization §8's own scope, unchanged.
- `frontend`: multi-stage build with `NEXT_PUBLIC_*` values passed as build `args` (baked at image-build
  time, not runtime-injectable — a real, disclosed Next.js/Docker constraint: changing the API origin
  requires a rebuild, not merely a new container run). `depends_on: backend: condition: service_healthy`.
  Its own healthcheck (`wget` against `localhost:3000` from inside the container) can never report healthy
  because Docker sets that container's `HOSTNAME` to its container ID and Next.js's standalone `server.js`
  binds to that value rather than `0.0.0.0` — a pre-existing, already-disclosed packaging quirk (unchanged
  since PR #180); real reachability must be proven from the host/another container, not from
  `docker compose ps`.

## 5. Build reproducibility — independently verified

- `backend/Dockerfile`: `python:3.12-slim`, `COPY pyproject.toml requirements.txt ./` then `COPY app`
  /`alembic`/`alembic.ini`/`docker-entrypoint.sh`, `pip install --no-cache-dir .`, non-root `ctec` user.
  No host venv, no bind mount, no dev/test dependency baked in (consistent with every prior phase's own
  observation that `pip install pytest httpx` had to be run ad hoc inside the container for verification).
- `frontend/Dockerfile`: `node:22-alpine` three-stage build (`dependencies` → `builder` → `runtime`),
  `npm install` from `package.json`/`package-lock.json*`, `npm run build` with `NEXT_PUBLIC_*` build args,
  standalone output (`/app/.next/standalone`, `/app/.next/static`, `/app/public`) copied into a minimal
  runtime stage, non-root `nextjs` user. No host `node_modules`/`.next` dependency.
- `.dockerignore` (root, `backend/`, `frontend/`) each correctly exclude `node_modules/`, `.next/`,
  `__pycache__/`, `.pytest_cache/`, `.venv/`/`venv/`, `.env`/`.env.*` (with `.env.example` explicitly
  re-included) — no host-state or secret leak into any build context.
- Single `docker-compose.yml` (no dev-only override file) is used identically by local development and by
  CI's own `containers` job — strong host/CI parity by construction, not by convention alone.
- No bind-mounted source anywhere; the only bind mounts are two read-only config files
  (`keycloak/ctec-realm.json`, `keycloak/bootstrap-demo-user.sh`).

**Conclusion: no hidden host-state dependency found in the build architecture.**

## 6. Runtime configuration contract (values, not secrets)

From `.env.example` and `docker-compose.yml`'s own inline comments (both read directly):

```
Required, fails closed if unset (no baked default):
  CTEC_RUNTIME_HANDOFF_KEY            backend — ontology/supplier-risk persistence layer key
  CTEC_KEYCLOAK_ADMIN_PASSWORD        keycloak/keycloak-bootstrap — local admin bootstrap only
  CTEC_DEMO_USER_PASSWORD             keycloak-bootstrap — local demo user only

Required only for the Supplier Risk submission path (Ontology Studio has no auth dependency),
empty-string default otherwise:
  CTEC_OIDC_ISSUER / CTEC_OIDC_AUDIENCE / CTEC_OIDC_JWKS_URL

Defaulted, safe for local/demo:
  CTEC_ENVIRONMENT (development), CTEC_LOG_LEVEL (INFO), CTEC_CORS_ORIGINS,
  CTEC_DATABASE_URL (compose-internal postgres), POSTGRES_DB/USER/PASSWORD (ctec/ctec/ctec)

Frontend build-time only (baked into the image, not runtime-injectable):
  NEXT_PUBLIC_CTEC_API_ORIGIN, NEXT_PUBLIC_OIDC_AUTHORITY/CLIENT_ID/REDIRECT_URI/
  POST_LOGOUT_REDIRECT_URI/SCOPE
```

`.env` is confirmed gitignored, never tracked, absent from all git history (`git log --all -- .env` is
empty). A repository-wide tracked-secret pattern scan (AWS access-key IDs, PEM private-key blocks, Slack
tokens) found nothing. **No tracked secret found.**

A new engineer can determine every required value from `.env.example` and `docker-compose.yml`'s own
comments alone — no undocumented required variable was found.

## 7. Database / migration closure — independently verified (third independent confirmation this program)

```
Alembic head:                 0046_oqi5_remediation_tenancy (single head, no branch point)
Fresh current-schema count:   126 (public schema, BASE TABLE, excludes alembic_version)
```

**PRODUCT-WIDE-DOCKER-CLOSURE-G-R1 correction**: at original DG freeze this read `0045_oqi_connector_ingestion`
(45 revisions). Step 13 added migration `0046_oqi5_remediation_tenancy` (46 revisions), independently
re-verified empty-database-to-head in a fresh container during G-R1 (single head, 126 tables unchanged, 271
FKs, all three of migration 0046's composite tenant-qualified FKs present). Table count is unchanged by
Step 13.

`backend/docker-entrypoint.sh` runs `python -m alembic upgrade head` — **dynamically resolved, not pinned
to a literal revision** — so a freshly built container always converges on whatever the repository's true
current head is, independent of any documentation staleness (see §11 finding). It then runs the idempotent
`OntologySeeder`/`BlueprintSeeder` (existing-row checks before any insert; Blueprint seed strictly after
Ontology seed commits, since it resolves `EntityType`/`RelationshipType` references by name) before starting
`uvicorn`. No manual SQL step, no developer-local data dependency, no destructive path (`alembic upgrade
head` only ever moves forward).

## 8. Authentication / authorization / tenant isolation

Provider-neutral OIDC/JWKS verifier; local Keycloak is dev/demo-only substrate (PAD-002). Real
Authorization Code + PKCE flow (`ctec-frontend` deliberately disables the direct-grant/ROPC flow — a real
security property, not a gap). Scope-based authorization confirmed via the live realm export
(`keycloak/ctec-realm.json`): 30 scopes covering every governed capability, including `oqi:read` (default),
`oqi-remediation:authorize`/`report-execution` (optional), `oqi-connector:configure`/`read`/`run`
(REAL-ENTERPRISE-INGESTION), `oqi-canonical-standard:configure`, `oqi-reference-evidence:configure`/
`verify`, `governed-agent:propose`, `governed-approval:decide`/`request`, and the pre-existing
ontology-modeling/supplier-risk/supply-chain-impact/entity-resolution/tool-execution scopes.

Tenant isolation is a deeply, repeatedly hardened invariant across this program's own recent history
(OQI6-R1/R2/R3, OQI4-R1, H4-R1 all added structural, tenant-qualified composite foreign keys after
adversarial real-Postgres cross-tenant tests found gaps) and is exercised by 413 real-PostgreSQL
`*_postgres.py` tests today (measured, §19). This is architecture the Docker closure gate must re-confirm
integrated, not redesign.

## 9. Ontology and evidence coverage

`SourceSystem` → `SourceObject` → `SourceField` → `FieldValueEvidence` (4-tuple identity, append-only,
`observed_at`/`received_at` distinction) feeds the existing OQI1-4 evaluators, which in turn drive ontology
entities/relationships (seeded via `OntologySeeder`/`BlueprintSeeder`) and their graph/visualization surface
at `/ontology/explorer` and `/ontology/modeling`. Lineage/provenance semantics (source-record reference,
observed-vs-received timestamps, OQI3's provenance-compound historical-replay rules) are unchanged and
already covered by the measured `test_oqi_*` suite (§19).

## 10. REAL-ENTERPRISE-INGESTION (CDD-059) — guarantees crossing the Docker boundary

All of the following were independently, freshly proven in Docker during VM-R2/VM-R3 (this session) and
must be **re-confirmed once more as part of the full integrated compose stack**, not re-derived from
scratch (§17 evidence-preservation matrix):

```
production/fixture EndpointSecurityPolicy boundary (structural, code-level, AST-proven)
fresh-per-attempt DNS resolution, full resolved-address-set validation
connection pinned to an already-validated candidate (validated address == connected address)
original hostname authoritative for TLS SNI / certificate verification / HTTP Host
ambient-proxy neutrality (no urllib.request in the transport)
evidence admission against pre-existing SourceSystem/SourceObject/SourceField configuration only
migration head 0046_oqi5_remediation_tenancy (G-R1: was 0045_oqi_connector_ingestion) / table count 126
```

**Confirmed scope boundary, not a defect**: REAL-ENTERPRISE-INGESTION has **zero frontend UI**. The
`/integrations` page (`frontend/app/integrations/page.tsx`) renders an older, unrelated static connector
catalog (`ontologyApi.getConnectors()`, CDD-033 §22 relocation of pre-existing CDD-030 MCP-era content) —
it is not wired to, and was never intended to expose, the CDD-059 Generic Governed REST Connector. Any
Docker-closure exercise of ingestion must use the real HTTP API directly (`POST
/api/v1/oqi/connectors/...`), never the `/integrations` screen.

## 11. OQI coverage — authoritative dimension list and a real, disclosed gap

Per `CDD-046-OQI-Hardening-Nine-Dimension-Architecture.md` (architecture-only; read in full), the named
target set is 9 dimensions: **COMPLETENESS, VALIDITY, CONSISTENCY** (pre-existing OQI1-4) plus 6 new:
**ACCURACY, UNIQUENESS, TIMELINESS, INTEGRITY, CONFORMITY, REASONABLENESS**, implemented across five
follow-on phases:

```
H1 (CDD-047)  Governed Quality Coverage + Reliance-coverage generalization (closes "1-of-9 evaluated
              still reads Supported")
H2 (CDD-048)  ACCURACY + REASONABLENESS + Reference Evidence + generalized QualityFindingOrigin
H3 (CDD-049)  CONFORMITY + CanonicalStandard
H4 (CDD-050 + H4-R1 CDD-050 tenant-isolation correction)  INTEGRITY
H5 (CDD-051)  TIMELINESS
```

**Independently verified against live code** (`backend/app/domain/oqi/quality_rule.py`'s own
`QualityDimension` enum): `{COMPLETENESS, VALIDITY, CONSISTENCY, ACCURACY, CONFORMITY, INTEGRITY,
TIMELINESS}` — 7 enum members. REASONABLENESS lives separately on `BusinessRule.dimension` by CDD-048's own
explicit design (§10/§14), bringing the true implemented count to **8 of the 9 CDD-046-named dimensions**.

**UNIQUENESS was never implemented** — no H-phase, no Artifact Authorization, no enum member, no prior
disclosure found anywhere in the governance chain. This is a real, previously-undisclosed product
**completeness** gap relative to CDD-046's own architecture. It is explicitly **out of scope for this
Docker-closure gate** — Step 13 verifies deployability/reproducibility of what exists, not feature parity
against an architecture document — and is recorded here only so the product-claim boundary (§25) does not
overstate coverage. No implementation of UNIQUENESS is authorized by this document.

## 12. Governed-agent coverage — two distinct, non-overlapping lineages

`CDD-037` (Gate V) is an older, separate lineage: one fixed-threshold, fully deterministic, non-AI agent
that may only *propose* (never decide) a human-approval request — confirms deterministic-by-default is a
pre-OQI convention, not new.

`CDD-043` (OQI5) is the actual specialist-agent framework OQI uses, structurally independent of Gate V.
Split I1 (deterministic foundation, zero AI, fully shippable and product-truth-authoritative alone) / I2
(optional real-model advisory layer). I2's topology: 2 parallel specialist `AgentRun`s → deterministic
code-only aggregation → 1 synthesis `AgentRun` → a deterministic `AgentRecommendationValidator` enforcing 23
binding invariants (rejects unknown IDs, disallowed types, omitted dissent, or an independently-proposed
value) → an `AgentRecommendation` that is advisory-only and never itself product truth. **I2 requires a
real model-provider API key and is explicitly excluded from this Docker closure's default scenario** — the
existing `DOCKER_SMOKE_TEST.md` precedent (and CDD-056 §21 / CDD-058 §11/§20, both of which explicitly
exclude agent-reasoning from their own production triggers) is followed here: the flagship scenario (§13)
exercises OQI5-I1 only, requires no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`, and I2 remains a disclosed,
separately-verified, non-required capability.

Exact `RemediationCase.status` states (CDD-043 §8, unchanged): `CANDIDATE_READY, AWAITING_AUTHORITY,
AUTHORIZED, EXTERNAL_EXECUTION_REPORTED, AWAITING_REEVALUATION, RESOLVED, STEWARD_INVESTIGATION,
NO_REMEDIATION`.

**Real, narrow, already-disclosed gap**: `POST /api/v1/oqi/findings/{finding_id}/remediation/prepare`
(CDD-058, scope `oqi-remediation:prepare`) makes the full remediation lifecycle reachable via direct API
call end-to-end, but **no frontend UI action exists to trigger it** — CDD-058 §29 states this explicitly
("FRONTEND CHANGE NOT REQUIRED FOR CORRECTNESS"). The existing `decide`/`report-execution` UI (already
wired: `remediation-panel.tsx`, `report-execution-dialog.tsx`) is unaffected and fully usable once a pending
authorization exists by any means. This narrows, but does not eliminate, the limitation
`DOCKER_SMOKE_TEST.md` currently (and now inaccurately) describes as "no live trigger... anywhere" — the
trigger exists at the API layer; only the UI affordance is still missing. This is disclosed, not
remediated, by this document.

## 13. Reliance semantics (CDD-044)

Exactly three closed states: `RELIANCE_SUPPORTED`, `RELIANCE_AT_RISK`, `RELIANCE_UNKNOWN` (no partial
state). `RELIANCE_SUPPORTED` requires zero open Findings, coverage-satisfied (H1's generalized coverage
policy), and no active `IMPACT_UNKNOWN`. "Explainable Trust" is the product/marketing name for the same
mechanism CDD-044 itself calls "Explainable Reliance" — one deterministic mechanism, two audiences.

## 14. Flagship / closure-critical frontend routes

Measured: 34 total route files (`find frontend/app -iname page.tsx`). Closure-critical for Step 13:
`/` (login/landing), `/auth/callback`, `/quality` (Command Center), `/quality/findings` (list),
`/quality/findings/[findingId]` (tabs: **Evidence, Ontology Impact, Business Impact, Reliance, Agent
Investigation, Remediation**), `/quality/evidence-fitness`, `/ontology/explorer`, `/ontology/modeling`.
`/integrations` is explicitly **not** part of the ingestion-closure scenario (§10). `/supplier-risk/*` and
`/data/*` remain pre-existing, unmodified flagship surfaces, in scope only for a basic reachability check,
not re-verification of their own already-closed capabilities.

## 15. Flagship end-to-end canonical scenario (frozen for VM)

Built entirely from capabilities directly confirmed to exist in the current codebase — nothing fabricated:

```
1.  Fresh boot: docker compose up -d (default graph: postgres, keycloak, keycloak-bootstrap, backend,
    frontend) + docker compose --profile ingestion-test up -d connector-fixture
2.  Seed governed foundation: existing entrypoint (ontology/blueprint, automatic) +
    `demo_oqi_seeder` (manual, idempotent, demo-tenant-scoped) for the pre-existing SAP/PLM disagreement
    baseline
3.  Real governed ingestion: authenticate a connector-scoped call (oqi-connector:configure/run),
    POST /api/v1/oqi/connectors (configure against https://connector-fixture:8443/), POST .../run
    -- proves the CDD-059 chain inside the FULL stack, not an isolated harness
4.  FieldValueEvidence admitted against pre-existing SourceField configuration (real Postgres row check)
5.  POST /api/v1/oqi/evaluate (CDD-056 explicit orchestration trigger) -- composes OQI1-4/OQI6/Reliance
    over both the seeded and the newly-ingested evidence
6.  Real login (Authorization Code + PKCE, ctec-demo-user) -> GET /quality (Command Center) reflects
    non-zero open_findings_count / reliance_at_risk_count
7.  GET /quality/findings -> open the seeded/ingested Finding -> step through Evidence, Ontology Impact,
    Business Impact, Reliance, Agent Investigation (I1 deterministic path only) tabs
8.  POST /findings/{id}/remediation/prepare (API-only, no UI button -- §12) -> pending RemediationAuthorization
9.  Human decision: click Decide Authorization in the Remediation tab (UI-wired) -> AUTHORIZED
10. Report execution: click Report Execution in the Remediation tab (UI-wired) -> EXTERNAL_EXECUTION_REPORTED
11. Re-evaluation: POST /api/v1/oqi/evaluate again -> AWAITING_REEVALUATION -> RESOLVED (only if fresh
    evidence genuinely changed the disagreement; otherwise the stepper must honestly remain at
    AWAITING_REEVALUATION -- never fake a resolution)
12. Dashboard/graph: re-check /quality and /quality/findings/[id] render the new state; open
    /ontology/explorer to confirm the ontology graph reflects the ingested SourceField's evidence
```

No step above requires a paid model-provider key. Step 3 is the one addition this scenario makes beyond
`DOCKER_SMOKE_TEST.md`'s existing (but stale) walkthrough, and is the part of the chain REAL-ENTERPRISE-
INGESTION exists to prove end-to-end inside the real product.

## 16. Restart / persistence contract

```
Boot #1:    fresh volumes -> migrate -> seed -> execute the full scenario (§15) through step 12
Stop/Start: docker compose stop && docker compose start (no volume deletion) -> re-verify: Postgres data,
            imported realm/demo user, ontology/blueprint seed, the demo Finding (not duplicated), the
            ingested connector configuration/evidence, and the remediation lifecycle state all survive
            intact; re-running the entrypoint's idempotent seeders and `demo_oqi_seeder` remains a safe
            no-op
Fresh reset: docker compose down -v --remove-orphans && docker compose up -d -> re-migrate to the same
            head/table count, re-import the same realm, reproduce the same scenario outcome from empty
            state -- proves reproducibility, not merely persistence
```

## 17. Evidence-preservation matrix

```
REAL-ENTERPRISE-INGESTION security architecture (SSRF/DNS-pinning/TLS/proxy)
    PARTIALLY PRESERVED -- code-level evidence (VM-R2/VM-R3, this program) stands; must be re-exercised
    once as part of the FULL integrated stack (§15 step 3), not re-derived from first principles.

OQI6/OQI4 structural tenant-isolation hardening
    PRESERVED -- unchanged since each correction merged; continuously re-proven by the measured 414
    real-Postgres tests on every CI `backend` run (G-R1: was 413; see §28).

OQI5 remediation authority chain tenant-isolation (migration 0046, added by Step 13)
    NEW SINCE DG, RE-RUN REQUIRED -- Case->Instruction->Authorization and Case->AgentRun now carry
    tenant-qualified composite FKs (previously a confirmed P1: zero DB-level tenant consistency).
    Adversarially proven against real PostgreSQL and, separately, inside an isolated Docker
    compose stack during Step 13's own VM-R5 -- both times the legitimate same-tenant chain
    persisted cleanly and every cross-tenant variant was rejected with `IntegrityError`. Final
    Docker VM must reconfirm this once more inside the FULL product-wide integrated stack (§27
    SECURITY gate), not merely trust Step 13's own isolated verification.

H1-H5 dimension implementations
    PRESERVED -- each closed its own independent VM; code unchanged since.

Production orchestration / remediation orchestration (CDD-056/058)
    RE-RUN REQUIRED at the integration level -- each closed its own narrow VM, but the `/evaluate` and
    `/remediation/prepare` routes have never been exercised together, against a fresh full-stack Docker
    boot, alongside Keycloak-issued real tokens and the frontend's own UI-driven decide/report-execution
    steps.

DOCKER_SMOKE_TEST.md's own literal contract
    NOT PRESERVED -- stale (migration head, table count, remediation-trigger disclosure; entirely
    predates ~15 capabilities merged since PR #180). This is the primary reason this phase exists.

Frontend critical OQI screens against a real, freshly-booted backend
    RE-RUN REQUIRED -- never verified since OQI7/OQI-UX/H1-H5/orchestration/remediation/ingestion all
    landed after PR #180's own last full Docker verification.
```

## 18. Host/Docker parity

CI's `backend`/`frontend` jobs run `pytest`/`vitest` directly on the GitHub Actions runner (Python 3.12 via
`actions/setup-python`, Node 22 via `actions/setup-node`), against a separate `postgres:17-alpine` **CI
service container** — not inside the actual production `backend`/`frontend` Docker images, and not via
`docker compose`. CI's `containers` job independently proves the built images boot, migrate, authenticate,
and serve correctly via real HTTP/DB checks, but the 2177/338 unit+integration test suites have never
executed *from inside* those images. This is a disclosed parity nuance, not a defect requiring correction —
the `containers` job's own checks are a different, still-real form of evidence for the same images.

## 19. Test inventory — measured, not estimated

```
Backend (pytest, backend/):
  Total collected                          2178  (G-R1: was 2177; re-collected fresh on new main)
  *_postgres.py (real-Postgres integration) 414  (37 files, unchanged; G-R1: was 413)
  test_oqi_*.py                             983  (41 files, unchanged)
  Architecture/dependency-boundary (5 files) 29  (test_domain_foundation.py, test_runtime_architecture.py,
                                                    test_execution_persistence_architecture.py,
                                                    test_integration_architecture.py,
                                                    test_supplier_risk_api_architecture.py)
  test_oqi_connector_ingestion_postgres.py   59  (CDD-059, unchanged)
  *remediation*.py (7 files, unchanged)     111  (G-R1: was 110 -- Step 13 added one adversarial test,
                                                    test_remediation_chain_tenant_integrity_enforced_by_
                                                    real_postgresql, to the existing
                                                    test_production_remediation_orchestration_postgres.py;
                                                    no new file)
  *orchestration*.py (4 files, unchanged)     61  (G-R1: was 60, same cause as above)
  Total test files                          185  (G-R1: corrected measurement; re-counted fresh via
                                                    `find app/tests -name "test_*.py"` -- Step 13 added no
                                                    new test file, so this is a DG-time counting
                                                    discrepancy, not a Step-13 effect)
  Static checks (not test counts): black --check, isort --check-only, ruff check, mypy app -- all
    independently re-confirmed clean on new main during Step 13's own VM-R5 (mypy 641/641 files)

Frontend (vitest, npm test -- --run):
  Test Files  42 passed, 1 known-fragile-locally (43)
  Tests       337 passed, 1 known-fragile-locally (338)
  Route/page files (find app -iname page.tsx)  34
  G-R1: Step 13 touched zero frontend files (confirmed: `git diff --stat` main..main is empty for
    `frontend/`) -- these figures are carried forward unchanged, not re-run in G-R1 (full frontend
    regression is reserved for the final VM's own REGRESSION gate, §27).

CI jobs (.github/workflows/ci.yml): exactly 3 -- backend, frontend, containers
```

**Known-fragile, non-blocking finding**: `frontend/tests/gate-x-runtime-architecture.test.tsx` scans
`git ls-files --others --exclude-standard` across the **whole repository** (not scoped to `frontend/`)
against its own frozen 29-item allowlist, so *any* stray untracked path anywhere in the repo (currently the
pre-existing, unrelated `docs/product/`) makes it fail locally. It passes in CI and in any genuinely fresh
checkout (no untracked files exist there). Classified P3 — a real test-design fragility, not a product
defect, since it has never actually failed in CI.

## 20. Failure-mode matrix (selected, not exhaustive)

```
Missing CTEC_RUNTIME_HANDOFF_KEY / CTEC_KEYCLOAK_ADMIN_PASSWORD / CTEC_DEMO_USER_PASSWORD
    -> docker compose up fails immediately and clearly via Compose's own `:?` syntax (design already fails
       closed; VM should confirm the exact message).
Invalid/prohibited connector destination (private/loopback/metadata)
    -> SSRFRejected, already proven (CDD-059 VM/VM-R1/VM-R2).
Connector DNS-rebinding attempt
    -> rejected via pinning, already proven (CDD-059 I-R2/VM-R2/VM-R3).
Unauthorized tenant access (cross-tenant Finding/evidence/connector read)
    -> already proven via real-Postgres adversarial tests; VM should reconfirm at least one via a real
       HTTP call inside the fresh Docker stack, not only at the repository/unit level.
Report-execution attempted without a prior AUTHORIZED case
    -> existing service-layer invariant rejects it; VM should exercise this as a real negative-path HTTP
       call, not merely trust the unit-test suite.
Restart after successful initialization (stop/start, not down -v)
    -> must remain healthy and lose no state (§16).
```

## 21. Severity register

```
P0 = 0
P1 = 0
P2 = 3
    - DOCKER_SMOKE_TEST.md is stale (wrong migration head/table count; outdated remediation-trigger
      disclosure; silent on ~15 capabilities merged since PR #180). Undermines the "reproducibly real,
      no developer-laptop-history dependency" standard this phase exists to enforce.
    - No product-wide fresh-Docker verification has been performed since PR #180 despite the OQI hardening
      program, production/remediation orchestration, and REAL-ENTERPRISE-INGESTION all merging since. Not
      itself a code defect -- the reason this phase (and the following VM) exists.
    - **PRODUCT-WIDE-DOCKER-CLOSURE-G-R3 finding**: `backend` cannot establish a trusted TLS connection to
      `connector-fixture` over the real Compose network -- confirmed empirically
      (`SSLCertVerificationError: self-signed certificate`) -- because the fixture's self-signed certificate
      is generated inside its own container at a randomized temp path with no volume or environment wiring
      to make it reachable/trusted by `backend`. This is the specific root cause of the item above for the
      REAL-ENTERPRISE-INGESTION portion of the flagship scenario specifically; not itself an exploitable
      security defect (verification correctly fails closed), but it blocks this phase's own required
      full-stack proof of CDD-059's guarantees. See §29 for root cause, architecture, and frozen correction.
P3 = 3
    - No frontend UI action for the `remediation/prepare` trigger (already correctly out of CDD-058's own
      scope; disclosed here for completeness, not remediated).
    - `gate-x-runtime-architecture.test.tsx`'s repo-wide (not frontend-scoped) untracked-file scan.
    - Backend/frontend test suites have never run from inside the actual production Docker images (a
      disclosed host/Docker parity nuance, not a defect).
```

## 22. Architecture decision

The current Docker architecture (multi-stage, non-root, no host-state dependency, single compose file
shared by dev and CI, fail-closed required secrets, dynamically-resolved migration head, idempotent
seeders) is **sufficient**. No redesign is authorized or required.

## 23. Implementation decision

```
IMPLEMENTATION REQUIRED
```

Narrowly: `DOCKER_SMOKE_TEST.md` is a tracked, product-facing operational runbook whose stated facts are
independently confirmed stale (§21 P2). Refreshing it is the one concrete, bounded defect this discovery
phase identified that a verification-only VM cannot itself correct (VM proves state; it does not rewrite
product documentation). No other path requires implementation: the Docker/build/config architecture is
sound (§5-§8), and the UNIQUENESS gap (§11) and the `remediation/prepare` UI gap (§12) are explicitly
out of this phase's scope, not defects this gate exists to fix.

## 24. Frozen I authorization — `PRODUCT-WIDE-DOCKER-CLOSURE-I`

```
CREATE = 0
MODIFY = 1
DELETE = 0
TOTAL  = 1
```

**Sole authorized path**: `DOCKER_SMOKE_TEST.md`

**Exact authorized semantic change** (nothing else):
1. Correct the migration-head expectation (§3 of that doc) from `0026_oqi6_reliance` to
   `0046_oqi5_remediation_tenancy` (**PRODUCT-WIDE-DOCKER-CLOSURE-G-R1 correction**: originally authorized
   as `0045_oqi_connector_ingestion` at DG time; Step 13 subsequently added migration 0046, so this is now
   the correct target -- also correct the identical stale head reference in that doc's own §17 clean-reset
   section, `0026_oqi6_reliance` -> `0046_oqi5_remediation_tenancy`, not called out separately at DG time
   because it is the same literal fact repeated twice in that document).
2. Correct the table-count expectation (§4 of that doc) from `100` to `126`, and its parenthetical note
   about `alembic_version` accordingly.
3. Replace the current, now-inaccurate §11 disclosed-limitation text ("no live trigger... anywhere") with
   an accurate statement: `POST /findings/{id}/remediation/prepare` (CDD-058) makes the trigger reachable
   via direct API call, but no frontend UI action exists for it yet (§12 of this document) — a narrower,
   still-real, disclosed gap.
4. Extend the walkthrough (additive steps only, no renumbering of the existing troubleshooting section) to
   cover the capabilities merged since PR #180 that Step 13's own flagship scenario (§15 of this document)
   exercises: the `connector-fixture` ingestion-test profile and a real connector configure/run call, the
   `POST /evaluate` explicit-orchestration trigger, and the `POST .../remediation/prepare` API-only trigger.

**Prohibited**: any change to `backend/`, `frontend/`, `docker-compose.yml`, either Dockerfile,
`.github/workflows/ci.yml`, any migration, any test, any governance artifact other than this one's own
publication, or creation of any new script/file. `PRODUCT-WIDE-DOCKER-CLOSURE-I` must not implement
UNIQUENESS, must not add a `remediation/prepare` UI button, and must not touch the
`gate-x-runtime-architecture.test.tsx` scan scope — all three remain explicitly deferred, out of this
phase's authorization.

## 25. Product-claim boundary

**Will be claimable once VM closes**: a clean Noetva environment can be reproducibly built and started from
the authoritative repository with Docker alone; migrates an empty database to the governed 126-table,
single-head schema; authenticates real users via a real Authorization Code + PKCE flow; enforces tenant
isolation; ingests governed real-source evidence via the Generic Governed REST Connector inside the real
Docker network (SSRF/DNS-pinning/TLS-identity intact); constructs and evaluates ontology/OQI state across 8
of 9 named quality dimensions; exercises the deterministic (I1) specialist-agent and remediation lifecycle
through real HTTP routes and, where UI-wired, a real browser; survives restart; and reproduces the same
outcome from a torn-down and recreated environment.

**Explicitly not claimed**: the UNIQUENESS quality dimension (never implemented); a browser-only path to
trigger `remediation/prepare` (API-only today); any frontend surface for the REAL-ENTERPRISE-INGESTION
connector (`/integrations` is unrelated, older content); the optional OQI5-I2 real-model advisory layer
(requires a model-provider key, explicitly outside this closure's default scenario); exact connector-run
provenance guarantees or vendor certification beyond the generic REST connector (carried forward from
CDD-059's own closure).

## 26. STOP-condition assessment

None of the 15 listed STOP conditions triggered: main did not move unexpectedly, no governance corruption,
no tracked secret, no cross-tenant exposure or authentication bypass found, no destructive migration
behavior, no security regression in REAL-ENTERPRISE-INGESTION or OQI authority boundaries, no evidence
integrity violation, no hidden implementation change in the working tree, no need for architectural
redesign, no contradiction of frozen prior claims, fixture/production behavior remains distinguishable, and
the safe authorization above is fully bounded (§24).

## 27. Final VM contract — required categories, commands, and evidence

`PRODUCT-WIDE-DOCKER-CLOSURE-VM` must independently prove, from genuinely clean state (no reused
containers/volumes/images; `docker compose down -v --remove-orphans` first if anything is running; a clean
git worktree at the exact `PRODUCT-WIDE-DOCKER-CLOSURE-I` head):

```
BUILD        docker compose build (+ --profile ingestion-test build connector-fixture) -- no --no-cache
             required unless a prior layer is suspected stale; both images build with no host dependency.
DATABASE     Fresh docker compose up -d postgres; confirm empty -> migrate (entrypoint) -> single head
             0046_oqi5_remediation_tenancy (G-R1: was 0045_oqi_connector_ingestion), table count 126, via
             the same query CI's `containers` job uses.
STARTUP      docker compose up -d; postgres/keycloak/backend report healthy via `docker compose ps` within
             ~90s; keycloak-bootstrap exits 0; frontend verified reachable via curl from the host (not its
             own healthcheck, per the disclosed §4 quirk).
SECURITY     Real Authorization Code + PKCE login; unauthenticated OQI request fails 401; a genuine
             cross-tenant read attempt fails; the REAL-ENTERPRISE-INGESTION SSRF/DNS-pinning/TLS crown
             (I-R2/VM-R2's own script, adapted to run against the FULL stack rather than an isolated
             namespace) still passes with connect() re-resolution counts == [0]. G-R1 addition: reconfirm
             migration 0046's remediation authority tenant-chain integrity (§17) inside the FULL integrated
             stack -- at least one cross-tenant Case->Instruction (or Instruction->Authorization, or
             Case->AgentRun) attempt via a real HTTP call rejected, and the legitimate same-tenant chain
             (prepare -> decide -> report-execution) still succeeds end-to-end.
PRODUCT      Execute the full flagship scenario, §15 steps 1-12, exactly as frozen, with no step skipped
             and no outcome asserted without direct evidence (real HTTP response bodies, real Postgres
             rows, a real rendered frontend screen).
PERSISTENCE  §16's stop/start cycle, verifying no state loss and no duplicate seeding.
REPRODUCIBILITY  §16's down -v / up cycle, reproducing the same migrated/seeded/scenario outcome from
             empty state.
REGRESSION   Full 2178 backend (G-R1: was 2177) + 338 frontend suites green in a clean checkout (the
             known-fragile gate-x-runtime-architecture.test.tsx test must be confirmed passing there, where
             no untracked file exists) -- do not accept a stale count; re-collect fresh.
DOCUMENTATION  DOCKER_SMOKE_TEST.md (post PRODUCT-WIDE-DOCKER-CLOSURE-I) is itself executed command-by-command
             and confirmed to match observed reality exactly.
```

VM may merge only if every category above is clean, following this repository's own established
normal-merge-workflow discipline (no force push, no branch-protection bypass, no emergency bypass).

## 28. PRODUCT-WIDE-DOCKER-CLOSURE-G-R1 reconciliation

Step 14 was intentionally paused at this document's original freeze (`a46096b41227c22e52cffffbd837372bcc865e28`)
while Step 13 (POSTGRES-DATA-MODEL-CLOSURE) ran to completion. Step 13 closed cleanly: merged via PR #194,
new authoritative main `d3683fdf4933dfed608001d38cbb6689580815ca`, migration head `0045_oqi_connector_ingestion`
-> `0046_oqi5_remediation_tenancy` (45 -> 46 revisions), 126 tables unchanged, 271 FKs certified, P0=0/P1=0
(the one confirmed P1 -- the remediation authority chain's zero tenant consistency -- closed by migration
0046), P2=4/P3=4 deferred by Step 13's own governance, zero remaining authoritative-ER factual blockers.
CDD-061 (`af68f9c11a2588150791e6ef640f23b8d1829a128ae7ae77e706d9a2b2888244`) and the final ER artifact
(`e92b93259331fa2e4f7d7afa83583ee2270b20164924db4c17be2a8f8034d66c`) are Step 13's own frozen evidence and
are not modified here.

**Primary G-R1 question**: does Step 13 materially invalidate the Docker architecture frozen above?
**Answer: NO.** Independently confirmed by diffing old main (`0fd3886`) against new main (`d3683fdf`)
restricted to every Docker-relevant path (`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`,
`backend/docker-entrypoint.sh`, all `.dockerignore` files, `.env.example`, `keycloak/`): **zero changes**.
Step 13's entire 6-path diff is confined to one migration file, two ORM model files, one test file, and two
documentation files -- none of which the Docker topology, build, or startup architecture depends on
structurally. `OntologySeeder`/`BlueprintSeeder` (the entrypoint's automatic seed) and `demo_oqi_seeder`
(the manual demo-showcase seed, whose own docstring already disclaims creating any `RemediationAuthorization`
or remediation-domain row) touch none of the tables migration 0046 changed -- confirmed by re-reading
`demo_oqi_seeder.py` and by an independent Docker-based verification below. No seed redesign is required.

**Step-13 impact matrix** (every row independently verified during G-R1, not assumed from Step 13's own
report):

| Area               | Step-13 impact                                                          |
|---------------------|--------------------------------------------------------------------------|
| Authoritative main  | New baseline `d3683fdf4933dfed608001d38cbb6689580815ca`                 |
| Migration head      | `0045_oqi_connector_ingestion` -> `0046_oqi5_remediation_tenancy`       |
| Revision count      | 45 -> 46                                                                 |
| Table count         | 126 -> 126, no change                                                    |
| FK count            | 271, certified (re-verified live)                                       |
| Docker topology     | No change (verified: zero diff on every Docker-relevant path)           |
| Dockerfiles         | No change                                                                |
| Compose             | No change                                                                |
| Seed                | Revalidated -- entrypoint seed + demo_oqi_seeder both proven compatible with 0046 in a fresh isolated Docker stack during G-R1 |
| Remediation         | Structurally stronger (migration 0046 closed the one confirmed P1); final VM must reconfirm this invariant inside the full integrated stack (§17, §27 SECURITY gate, amended above) |
| Auth                | No change                                                                |
| Connector           | No architecture change                                                  |
| OQI                 | No functional dimension change -- still 8/9 (UNIQUENESS not implemented, unchanged) |
| Persistence         | Revalidate (§16, unchanged contract)                                     |
| Restart             | Revalidate (§16, unchanged contract)                                     |
| Reproducibility     | Revalidate (§16, unchanged contract)                                     |
| Docker runbook      | Must be updated -- `DOCKER_SMOKE_TEST.md`'s migration-head target changes from the originally-authorized `0045_oqi_connector_ingestion` to `0046_oqi5_remediation_tenancy` (§24, amended above); everything else in the original I-authorization is unchanged |

**G-R1 Docker verification performed** (fresh, isolated, disjoint from Step 13's own Docker verification):
a standalone `docker run postgres:17-alpine` container was migrated empty -> head, independently confirming
single head `0046_oqi5_remediation_tenancy`, 126 tables, and all three of migration 0046's composite
tenant-qualified FKs (`fk_oqi_remediation_instructions_tenant_case`,
`fk_oqi_remediation_authorizations_tenant_instruction`, `fk_oqi_remediation_agent_runs_tenant_case`) present
and structurally correct.

**Implementation authorization revalidation**: re-examined `docker-compose.yml`, both Dockerfiles, both
`.dockerignore` files, `.env.example`, `backend/docker-entrypoint.sh`, `keycloak/` -- all confirmed
unchanged and still sufficient. `DOCKER_SMOKE_TEST.md` (re-read in full during G-R1) still contains exactly
the staleness DG originally found (§21 P2), now with one additional fact to correct: its migration-head
target must become `0046_oqi5_remediation_tenancy`, not `0045_oqi_connector_ingestion` (§24, amended above).
No other implementation file requires correction. **The frozen one-file authorization
(`CREATE=0/MODIFY=1/DELETE=0/TOTAL=1`, sole path `DOCKER_SMOKE_TEST.md`) remains sufficient and is
reaffirmed below with its corrected target.**

**Branch reconciliation**: this branch (`product-wide-docker-closure/step-13`, historically named but now
carrying Step-14 governance) was merged with new authoritative main via a plain, conflict-free
`git merge origin/main` (Step 13's 6-path diff and this branch's own CDD-060 commit touch entirely disjoint
files) -- no rebase, no force push, no history rewrite. The original freeze commit,
`a46096b41227c22e52cffffbd837372bcc865e28`, remains reachable and unmodified in this branch's history as
the merge's first parent; new main, `d3683fdf4933dfed608001d38cbb6689580815ca`, is the merge's second
parent. This reconciliation commit (documenting the CDD-060 text amendments above) is a separate, later
commit on top of that merge -- its own authored diff is `docs/cdd/CDD-060-...md` only.

## 29. PRODUCT-WIDE-DOCKER-CLOSURE-G-R3 — connector-fixture TLS trust architecture

`PRODUCT-WIDE-DOCKER-CLOSURE-I` correctly STOPPED after discovering that the real, full-stack path CDD-060
§15 step 3 and §10/§17 assumed (a real HTTP call from `backend` to `https://connector-fixture:8443/` over
the Compose network) cannot execute: it fails TLS certificate verification. This is a genuine, previously
undiscovered gap -- CDD-059's own VM-R2/VM-R3 evidence (§10, §17) proved the connector's security
guarantees exclusively via **in-process** test harnesses, never via the standalone `connector-fixture`
Compose service reached over the real network; that path had apparently never been exercised end-to-end
before this phase. Separately, a Keycloak scope gap (`oqi-remediation:prepare`, never wired into
`keycloak/ctec-realm.json`) was found and fixed in commit `afe76b1597ab4b87c2ed319894f2dd185766f7fa` --
unrelated to this finding, preserved, not reopened here.

### Independent reproduction

```
$ docker compose -p gr3repro up -d postgres backend --build
$ docker compose -p gr3repro --profile ingestion-test up -d connector-fixture
$ docker exec gr3repro-backend-1 python3 -c "
import ssl, socket
ctx = ssl.create_default_context()
with socket.create_connection(('connector-fixture', 8443), timeout=5) as sock:
    with ctx.wrap_socket(sock, server_hostname='connector-fixture') as ssock:
        print('CONNECTED OK', ssock.version())
"
FAILED: SSLCertVerificationError [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1010)
```

### Certificate/trust analysis (§7, §26 of the governing G-R3 charter)

```
$ docker exec gr3repro-backend-1 sh -c "echo | openssl s_client -connect connector-fixture:8443 -servername connector-fixture" | openssl x509 -noout -text
    Issuer: CN=ctec-connector-fixture.test        (self-signed: issuer == subject)
    Subject: CN=ctec-connector-fixture.test
    X509v3 Subject Alternative Name:
        DNS:localhost, IP Address:127.0.0.1, DNS:connector-fixture
```

Failure classification: **pure trust-chain failure** (`verify error:num=18:self-signed certificate`), not a
hostname problem -- the SAN already correctly includes `connector-fixture`, the exact name `backend`
resolves and connects to. Single self-signed leaf certificate, no separate CA cert (the fixture's own
`ca_bundle_path` property returns the leaf cert itself -- it is used, correctly, as its own trust anchor).
Confirmed via full-container recreation (`docker compose up -d --force-recreate connector-fixture`) that a
genuinely fresh cert (new serial, new random temp-directory path) is generated on every fresh process start
of that container -- any correction must tolerate this rotation without requiring a `backend` restart.
Confirmed no healthcheck currently exists on `connector-fixture` (`docker inspect` → `State.Health: null`).

### RestConnector trust mechanism (§9 of the charter)

`backend/app/infrastructure/connectors/rest_connector.py:415`: `ssl.create_default_context(cafile=test_ca_bundle)`
when `CTEC_CONNECTOR_TEST_CA_BUNDLE` is set, else the ordinary system-default context. Per Python's own `ssl`
module semantics, supplying `cafile` **replaces** the default trust store rather than extending it -- a real
consequence, pre-existing in the already-merged CDD-059 code (not introduced or changed by this phase):
leaving this variable set while configuring a genuine, non-fixture, publicly-CA-signed connector would cause
that real connection to fail closed (safe, not a vulnerability, but a real operational caveat to disclose).
Confirmed via `app/application/connector_ingestion_service.py:286` that `RestConnector` is constructed fresh
(via `connector_factory(...)`) on every `POST .../run` call, never cached long-lived -- meaning the CA bundle
file's content is read fresh at every connector run, not once at backend startup. This is the load-bearing
fact resolving the startup/readiness-race and cert-rotation questions below: no race exists at backend
*startup* (nothing there reads the CA), and rotation is self-healing (each run reads current file content).

### CDD-059 invariant preservation

Nothing in the selected design touches `RestConnector`'s SSRF validation, DNS-pinning/address-pinning,
hostname-authoritative SNI/HTTP Host, or ambient-proxy neutrality -- all of that logic is untouched;
`ssl.create_default_context()`'s own hostname verification (`check_hostname`) remains on throughout. The
design changes only *which* file supplies the trust anchor, under a boundary that defaults to fully inert.

### Candidate architectures considered

- **A -- shared named volume** (selected, refined below): `connector-fixture` writes its certificate (only)
  to a fixed path inside a Compose-managed named volume also mounted read-only into `backend`. Ephemeral,
  destroyed by `down -v`, self-healing across restarts since the CA is read fresh per connector run.
- **B -- checked-in static test certificate material**: rejected. Tracking a private key (even a test-only
  one) in the repository is unnecessary given (A) achieves the same goal with zero tracked key material,
  and introduces its own hygiene/expiration/rotation governance burden for no benefit.
- **C -- configurable fixture output directory**: adopted as the mechanism *within* A, not as an alternative
  to it -- the fixture's `__main__` entry gains an optional, additive-only environment variable
  (`CTEC_FIXTURE_CERT_DIR`) that, when set, copies the *already-generated* certificate (not the private key)
  to a fixed filename in that directory. The existing `DeterministicHttpFixtureServer` class, its
  constructor, and every in-process test that instantiates it directly are completely untouched -- the
  change is confined to the `if __name__ == "__main__":` guard, the one code path only Compose ever
  executes.

### Selected architecture

```
connector-fixture (profile: ingestion-test)
    │  generates its own ephemeral keypair + self-signed cert in its own
    │  private tempdir (UNCHANGED existing behavior)
    │
    │  ADDITIVE: if CTEC_FIXTURE_CERT_DIR is set, copies ONLY the certificate
    │  (never the private key) to <dir>/ca.pem
    ▼
named Compose volume `connector_fixture_ca` (ephemeral; destroyed by `down -v`)
    │  connector-fixture: mounted read-write
    │  backend:           mounted READ-ONLY, same path
    ▼
backend
    CTEC_CONNECTOR_TEST_CA_BUNDLE: ${CTEC_CONNECTOR_TEST_CA_BUNDLE:-}
    (defaults to EMPTY in the compose file itself -- inert for every ordinary
    `docker compose up`; the operator explicitly exports this variable, set to
    the exact shared-volume path, only when deliberately exercising the
    ingestion-test flow -- mirroring this repository's own existing
    `CTEC_RUNTIME_HANDOFF_KEY`-style required-secret opt-in convention, never
    auto-enabled)
```

### Private-key isolation (§15 of the charter)

The private key never leaves `connector-fixture`'s own container filesystem and is never placed in the
shared volume -- only `ca.pem` (the public certificate) is copied there. `backend` never needs, and never
receives, read access to any private key.

### Mount semantics

`connector_fixture_ca` (named, Compose-managed, ephemeral -- no host bind mount): read-write on
`connector-fixture`, read-only on `backend`. Removed by `docker compose down -v`, consistent with every
other ephemeral volume in this stack.

### Startup / readiness

No race requiring a new `depends_on` or healthcheck: the CA file is read by `backend` only at the moment an
operator calls `POST .../connectors/{id}/run` (proven above -- request-time, not startup-time), and CDD-060
§15's own flagship scenario already sequences "bring up `connector-fixture`" as an explicit, earlier,
numbered step before any connector configure/run call. **Explicit decision: no `connector-fixture`
healthcheck is added** -- the existing sequencing already resolves the practical race, and adding one is not
required by any correctness gap found. If VM independently discovers a real timing race, that finding would
warrant its own governance amendment.

### Restart / rotation / clean-stack behavior

Every fresh process start of `connector-fixture` (full recreate, or a plain container restart/`stop`+`start`)
generates a genuinely new self-signed certificate (independently confirmed: new serial, new temp path) and
would overwrite `ca.pem` at the same fixed shared-volume path. Since `backend` reads that file's content
fresh on every connector run rather than caching it, this is fully self-healing -- no `backend` restart is
ever required after a `connector-fixture` restart or recreation. `docker compose down -v --remove-orphans`
destroys the named volume along with everything else, so a clean rebuild reproduces the whole chain from
empty state exactly as the reproducibility contract (§16) already requires.

### Test/production boundary and residual risk (§11, §26)

The trust path is inert by construction (`backend`'s own compose-file default for the new variable is
empty) unless an operator explicitly exports `CTEC_CONNECTOR_TEST_CA_BUNDLE` pointed at the shared path --
identical in spirit to how `CTEC_RUNTIME_HANDOFF_KEY` is never baked in either. One residual, pre-existing
(not introduced by this design) operational caveat is disclosed rather than fixed: because `cafile=`
replaces rather than extends the system trust store, an operator who leaves this variable set while also
configuring a real, non-fixture, publicly-CA-signed connector would see that real connection fail closed
(safe, not silently insecure) -- `PRODUCT-WIDE-DOCKER-CLOSURE-I-R3`'s runbook text must instruct unsetting
this variable before/after the ingestion-test walkthrough for exactly this reason.

### Test-requirement decision

**No new automated regression test is authorized.** Existing connector tests
(`test_oqi_connector_ingestion_postgres.py`) all construct the fixture in-process and wire
`CTEC_CONNECTOR_TEST_CA_BUNDLE` directly in the test process -- they exercise `RestConnector`'s own trust
logic already and are unaffected by (and cannot regression-protect) this specific Compose-YAML/volume-wiring
class of defect, which has no analogue anywhere else in this repository's pytest-only test architecture. The
durable protection against recurrence is structural, not a new test: CI's existing `containers` job already
builds and boots this exact Compose topology (a malformed volume/service definition fails there loudly), and
`PRODUCT-WIDE-DOCKER-CLOSURE-VM` is itself explicitly required (§27, unchanged) to independently prove the
real full-stack connector path on every future Docker closure -- that is this program's own established
regression mechanism for Compose-level behavior, not a new pytest file.

### Frozen I-R3 authorization

```
CREATE = 0
MODIFY = 2
DELETE = 0
TOTAL  = 2
```

**Sole authorized paths**:
1. `docker-compose.yml` -- add the `connector_fixture_ca` named volume; mount it read-write into
   `connector-fixture` with `CTEC_FIXTURE_CERT_DIR` set to its fixed path; mount it read-only into `backend`
   at the same path, with `CTEC_CONNECTOR_TEST_CA_BUNDLE: ${CTEC_CONNECTOR_TEST_CA_BUNDLE:-}` (default empty).
2. `backend/app/tests/fixtures/deterministic_http_fixture_server.py` -- additive-only change confined to the
   `if __name__ == "__main__":` guard: when `CTEC_FIXTURE_CERT_DIR` is set, copy the already-generated
   certificate (via the existing `ca_bundle_path` property; never the private key) to a fixed filename in
   that directory after the server starts. Zero change to the `DeterministicHttpFixtureServer` class or any
   code path used by existing in-process tests.

**Prohibited**: any change to `DOCKER_SMOKE_TEST.md` (that remains `PRODUCT-WIDE-DOCKER-CLOSURE-I`'s own,
still-pending, authorization), any backend/frontend application code, any migration, any test file, the
Keycloak realm (already separately corrected), `.env.example` (documentation-only; not required for the fix
to function -- the runbook itself, when `I` resumes, is where the operator-facing `export
CTEC_CONNECTOR_TEST_CA_BUNDLE=...` instruction belongs), or any other CDD.

### I-R3 verification contract

```
TLS           backend trusts connector-fixture's certificate via the explicit shared-volume CA bundle;
              `openssl s_client`/equivalent shows a successful handshake, not a self-signed-certificate error.
HOSTNAME      connector-fixture's identity still verifies normally (SAN already correct; untouched).
FULL PATH     a real POST .../connectors (configure) + POST .../connectors/{id}/run, issued with a real
              Keycloak-obtained token, succeeds end-to-end against https://connector-fixture:8443/ -- no
              in-process substitute, no direct DB insertion, no verification bypass.
EVIDENCE      the resulting connector run produces real, queryable FieldValueEvidence rows.
SECURITY      existing SSRF/DNS-pinning/TLS connector test suite remains fully green (unchanged).
NEGATIVE      with CTEC_CONNECTOR_TEST_CA_BUNDLE unset/empty (the compose-file default), the same call fails
CONTROL       exactly as it does today (self-signed certificate error) -- proving the fix is additive, not a
              global verification weakening.
RESTART       after `docker compose restart connector-fixture` (or stop/start), the same full path succeeds
              again without any backend restart, using the newly-rotated certificate.
CLEAN STACK   `docker compose down -v --remove-orphans` followed by a fresh build/up reproduces the same
              working chain from empty state.
```

## 30. Exact next phase

```
PRODUCT-WIDE-DOCKER-CLOSURE-I-R3
```

Implements exactly the §29 frozen correction (`docker-compose.yml` + the fixture script's `__main__` guard,
nothing else). After I-R3 passes its own verification contract (§29), resume the original
`PRODUCT-WIDE-DOCKER-CLOSURE-I` to write `DOCKER_SMOKE_TEST.md` -- still entirely unauthorized to touch
either of I-R3's two files, preserving defect attribution and phase clarity.
