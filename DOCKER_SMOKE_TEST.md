# Docker Smoke Test — Governed OQI Demo Environment

Every command below was independently executed against a genuinely fresh local stack built from
this exact candidate during Product-Wide Docker Closure (Docker-I) and produced the stated
result, including a full `down -v --remove-orphans` clean-rebuild reproducibility pass. Run from
a machine with Docker + Docker Compose installed; no registry access or paid model API key is
required for any step in this document. The OQI product is fully deterministic; no
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or other model-provider credential is instantiated on any
route this checklist exercises.

This flagship scenario walks the complete governed OQI lifecycle end to end: raw multi-source
evidence lands via a real, tenant-scoped connector run; a real evaluation call turns that evidence
into a Finding; a human steward prepares and authorizes remediation candidates; execution is
reported and the case is re-evaluated; and the tenant-isolation invariants underneath all of it
are proven directly against real PostgreSQL. Two invariants are demonstrated live, not merely
asserted: **recommendation ≠ authorization** (a produced candidate is never pre-approved) and
**remediation ≠ resolution** (reporting execution never, by itself, resolves a Finding).

## Prerequisites

```bash
# Required, no baked-in default (see docker-compose.yml comments for how to generate
# CTEC_RUNTIME_HANDOFF_KEY):
export CTEC_RUNTIME_HANDOFF_KEY=<your own base64 value>
# python3 -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
export CTEC_KEYCLOAK_ADMIN_PASSWORD=<a local-only admin password>
export CTEC_DEMO_USER_PASSWORD=<a local-only demo-user password>

# Also required for real OIDC login/JWT verification to activate at all (backend responds
# 503 AUTH_VERIFIER_UNAVAILABLE without these). Point at this stack's own bundled Keycloak:
export CTEC_OIDC_ISSUER=http://localhost:8081/realms/CTEC
export CTEC_OIDC_AUDIENCE=ctec-supplier-risk-api
export CTEC_OIDC_JWKS_URL=http://keycloak:8080/realms/CTEC/protocol/openid-connect/certs
```

## 1. Fresh build and fresh boot

```bash
docker compose build
docker compose up -d
```

Expect: both `backend` and `frontend` images build successfully; `postgres`, `keycloak`, and
`backend` report `healthy` via `docker compose ps` within ~60 seconds; `keycloak-bootstrap` runs
once and exits `0`.

> **Frontend health note:** `docker-compose.yml`'s own `frontend` healthcheck runs `wget
> http://localhost:3000` *inside* the container. Docker automatically sets that container's
> `HOSTNAME` environment variable to its own container ID, and Next.js's standalone
> `server.js` binds to that value rather than `0.0.0.0` — so the container-internal healthcheck
> can never pass, even though the service is genuinely reachable on its published port from any
> real external caller (browser, `curl` from the host, another container). This is a real,
> pre-existing packaging quirk, unrelated to OQI/Keycloak, and is out of scope for this document
> to fix. Verify frontend reachability from the host instead:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
# expect: 200
```

## 2. Migration head, schema size, and demo-showcase seed

```bash
docker compose exec -e PGPASSWORD=ctec postgres psql -U ctec -d ctec -tAc \
  "SELECT version_num FROM alembic_version"
# expect: 0046_oqi5_remediation_tenancy

docker compose exec -e PGPASSWORD=ctec postgres psql -U ctec -d ctec -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' AND table_name != 'alembic_version'"
# expect: 126 (alembic_version itself is migration bookkeeping, not product schema)

docker compose exec backend python -m app.infrastructure.persistence.demo_oqi_seeder
```

Expect a summary line ending `reliance_state='RELIANCE_AT_RISK'`. This seeds only raw,
disagreeing multi-source evidence (a demo supplier's Country of Origin: SAP says "US", PLM says
"MX") and governed configuration (quality rules, business processes/dependencies) — it never
directly inserts a Finding, an ontology-impact row, a business-impact row, or a Reliance state.
Those are produced by calling the real, unmodified OQI evaluators against that seeded evidence.
Re-running this command is safe — idempotent, scoped to `ctec-demo-tenant` only.

## 3. Governed connector ingestion — production rejection, then a governed functional proof

CDD-059's `ProductionEndpointSecurityPolicy` unconditionally rejects any connector endpoint that
resolves to a private-network address — a deliberate, non-negotiable SSRF protection with zero
production exceptions (proven statically by `test_crown_h_production_construction_cannot_activate_fixture_policy`).
This step proves that rejection is real, then proves the full connector chain works using the
one mechanism CDD-059 itself authorizes for functional verification: an ad hoc VM/CI script (never
a repository path) that substitutes the test-only `FixtureEndpointSecurityPolicy` (CDD-059
Artifact Authorization I-R1 §6.4).

```bash
docker compose --profile ingestion-test up -d connector-fixture
```

### 3a. Real production API — must reject

```bash
SAP_SYSTEM=$(docker compose exec -e PGPASSWORD=ctec postgres psql -U ctec -d ctec -tAc \
  "SELECT source_system_id FROM source_systems WHERE source_system_name='SAP ERP (demo)'" | tr -d '[:space:]')

curl -s -w "\nhttp:%{http_code}\n" -X POST "http://localhost:8000/api/v1/oqi/connectors" \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
  -d "{\"source_system_id\":\"$SAP_SYSTEM\",\"display_name\":\"Docker smoke test\",\"connector_type\":\"GENERIC_REST\",\"endpoint_url\":\"https://connector-fixture:8443/\",\"auth_mechanism\":\"API_KEY\",\"auth_header_name\":\"X-API-Key\",\"credential_env_var_name\":\"UNUSED\",\"pagination_style\":\"NONE\"}"
# expect: HTTP 422 {"detail":{"code":"CONNECTOR_ENDPOINT_REJECTED"}}
```

(`$ACCESS_TOKEN` here needs `oqi-connector:configure`; see step 5 for the real login flow that
issues it.) This is **expected and correct** — it proves the production security boundary is
live, not a defect to work around.

### 3b. Governed ad hoc verification script — real functional proof

Save as e.g. `/tmp/step3b.py` on the **host**, then `docker cp` it into `backend` and run it there
(it needs the real `ConnectorIngestionService` and database session, so it must execute inside the
backend container's Python environment). This file is never committed to the repository —
CDD-059 §6.4 authorizes exactly this kind of ad hoc, non-repository verification script.

```python
"""Ad hoc VM/CI verification script (CDD-059 Artifact Authorization I-R1
§6.4) -- not a repository path, never committed. Proves the real CDD-059
connector chain against the standalone connector-fixture Compose service."""
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.application.connector_ingestion_service import ConnectorIngestionService
from app.infrastructure.connectors.rest_connector import _resolve_and_validate, ValidatedEndpoint


class FixtureEndpointSecurityPolicy:
    """Verbatim per CDD-059 Artifact Authorization I-R1 §6.2/§6.4."""
    def __init__(self, *, allowed_addresses):
        self._allowed_addresses = allowed_addresses

    def validate(self, url: str) -> ValidatedEndpoint:
        return _resolve_and_validate(url, allowed_addresses=self._allowed_addresses)


# Resolve the fixture's current container IP (changes across --force-recreate):
import socket
fixture_ip = socket.gethostbyname("connector-fixture")

settings = get_settings()
engine = create_engine(settings.database_url)
factory = sessionmaker(engine)

TENANT = "ctec-demo-tenant"
# Derive real seeded IDs rather than hardcoding them:
with engine.connect() as conn:
    from sqlalchemy import text
    SAP_SYSTEM = conn.execute(text(
        "SELECT source_system_id FROM source_systems WHERE source_system_name='SAP ERP (demo)'"
    )).scalar_one()
    MFG_FIELD = conn.execute(text(
        "SELECT source_field_id FROM source_fields WHERE field_label='Manufacturing Country'"
    )).scalar_one()

with factory() as session:
    svc = ConnectorIngestionService(
        session,
        endpoint_security_policy=FixtureEndpointSecurityPolicy(allowed_addresses=frozenset({fixture_ip})),
    )
    cfg = svc.configure_connector(
        tenant_id=TENANT, source_system_id=SAP_SYSTEM,
        display_name="Docker Smoke Test Step 3b connector", connector_type="GENERIC_REST",
        endpoint_url="https://connector-fixture:8443/", auth_mechanism="API_KEY",
        auth_header_name="X-API-Key", credential_env_var_name="DOCKER_SMOKE_UNUSED_CRED",
        pagination_style="NONE", created_by="docker-smoke-test-step3b",
    )
    session.commit()
    print("CONFIGURE OK, connector_id=", cfg.connector_id)

    svc.add_field_mapping(
        tenant_id=TENANT, connector_id=cfg.connector_id, external_field_path="id",
        source_field_id=MFG_FIELD, is_external_record_id=True, created_by="docker-smoke-test-step3b",
    )
    session.commit()
    svc.add_field_mapping(
        tenant_id=TENANT, connector_id=cfg.connector_id, external_field_path="lead_time_days",
        source_field_id=MFG_FIELD, is_external_record_id=False, created_by="docker-smoke-test-step3b",
    )
    session.commit()

    run = svc.run_connector(tenant_id=TENANT, connector_id=cfg.connector_id, correlation_id=None,
                             triggered_by="docker-smoke-test-step3b")
    session.commit()
    print("RUN RESULT:", run)
```

```bash
docker cp /tmp/step3b.py $(docker compose ps -q backend):/tmp/step3b.py

# TLS negative control -- without the fixture's CA bundle, the connection must fail closed:
docker compose exec backend python3 /tmp/step3b.py
# expect: SSLCertVerificationError (self-signed cert not yet trusted)

# TLS positive control -- with the shared, backend-mounted, read-only CA bundle:
docker compose exec -e CTEC_CONNECTOR_TEST_CA_BUNDLE=/shared/fixture-ca/ca.pem backend python3 /tmp/step3b.py
# expect: CONFIGURE OK, connector_id=<uuid>
# expect: RUN RESULT: RunResult(..., status='SUCCEEDED', fetched_records=2, accepted_records=2,
#         rejected_records=0, duplicate_records=0, evidence_written=2, ...)
```

`CTEC_CONNECTOR_TEST_CA_BUNDLE` is empty by default on `backend` — ordinary `docker compose up`
is completely unaffected by this mechanism; it only activates when an operator explicitly sets it,
exactly as done above.

## 4. OQI evaluation — scope-gated production trigger, negative and positive controls

`POST /api/v1/oqi/evaluate` is gated on the `oqi-evaluation:trigger` scope. This is the real,
explicit CDD-056 production evaluation trigger — distinct from the demo seeder in step 2, which
calls evaluators *internally* at seed time and never goes through this HTTP route.

> **Which findings come from where:** the seeded SAP/PLM Country-of-Origin Finding (OQI1/OQI2,
> step 5's continuity thread) is produced entirely inside `demo_oqi_seeder` at seed time. The only
> demo quality rule reachable through this real HTTP `/evaluate` route is the H3
> conformity/consistency rule below (`information_element_requirement_id` here is a UUID, a
> different concept from `quality_rules.information_element_requirement_id`, which is a
> `character varying(200)` business key like `"ier-country-of-origin"`). This is a real, current
> product boundary, not a Docker-packaging gap.

```bash
BUSINESS_PROCESS=$(docker compose exec -e PGPASSWORD=ctec postgres psql -U ctec -d ctec -tAc \
  "SELECT process_id FROM oqi_business_processes WHERE tenant_id='ctec-demo-tenant' AND name='Supplier Qualification (Demo)'" | tr -d '[:space:]')

# Negative control -- token without oqi-evaluation:trigger:
curl -s -w "\nhttp:%{http_code}\n" -X POST "http://localhost:8000/api/v1/oqi/evaluate" \
  -H "Authorization: Bearer $ACCESS_TOKEN_NO_EVAL_SCOPE" -H "Content-Type: application/json" \
  -d "{\"information_element_requirement_id\":\"1828808b-ba9a-599b-9af8-c5158201f70b\",\"source_record_reference\":\"SUP-DEMO-001\",\"business_process_id\":\"$BUSINESS_PROCESS\",\"business_process_version\":1}"
# expect: HTTP 403 {"detail":{"code":"AUTHORIZATION_SCOPE_REQUIRED"}}

# Positive control -- token with oqi-evaluation:trigger:
curl -s -w "\nhttp:%{http_code}\n" -X POST "http://localhost:8000/api/v1/oqi/evaluate" \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
  -d "{\"information_element_requirement_id\":\"1828808b-ba9a-599b-9af8-c5158201f70b\",\"source_record_reference\":\"SUP-DEMO-001\",\"business_process_id\":\"$BUSINESS_PROCESS\",\"business_process_version\":1}"
# expect: HTTP 202 with a real, differentiated result, e.g.:
#   {"dimensions":[...{"dimension":"CONFORMITY","status":"FAILED",...}...],
#    "business_impact":[{"dependency_id":"...","status":"EVALUATED","outcome":"BUSINESS_IMPACT_IDENTIFIED"}],
#    "reliance":{"status":"EVALUATED","state":"RELIANCE_AT_RISK"}}
```

## 5. Authenticated reads and the evidence → Finding chain

`ctec-frontend` deliberately disables the Resource Owner Password Credentials grant (a real
security property) — obtaining a real token requires the same Authorization Code + PKCE flow a
real browser performs. The commands below simulate exactly that flow, never a shortcut grant type:

```bash
VERIFIER=$(openssl rand -base64 96 | tr -dc 'A-Za-z0-9' | cut -c1-64)
CHALLENGE=$(printf '%s' "$VERIFIER" | openssl dgst -sha256 -binary | openssl base64 | tr '+/' '-_' | tr -d '=')
COOKIES=$(mktemp)
SCOPE="openid profile oqi:read oqi-connector:configure oqi-connector:run oqi-evaluation:trigger oqi-remediation:prepare oqi-remediation:authorize oqi-remediation:report-execution"

AUTH_PAGE=$(curl -s -c "$COOKIES" -G "http://localhost:8081/realms/CTEC/protocol/openid-connect/auth" \
  --data-urlencode "client_id=ctec-frontend" --data-urlencode "response_type=code" \
  --data-urlencode "scope=$SCOPE" --data-urlencode "redirect_uri=http://localhost:3000/auth/callback" \
  --data-urlencode "code_challenge=$CHALLENGE" --data-urlencode "code_challenge_method=S256")
ACTION=$(printf '%s' "$AUTH_PAGE" | grep -o 'action="[^"]*login-actions/authenticate[^"]*"' | head -1 \
  | sed -e 's/^action="//' -e 's/"$//' -e 's/\&amp;/\&/g')

LOGIN_RESPONSE=$(curl -s -i -c "$COOKIES" -b "$COOKIES" \
  --data-urlencode "username=ctec-demo-user" --data-urlencode "password=$CTEC_DEMO_USER_PASSWORD" "$ACTION")
CODE=$(printf '%s' "$LOGIN_RESPONSE" | tr -d '\r' | grep -i '^location:' | grep -o 'code=[^&[:space:]]*' | head -1 | cut -d= -f2)

TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8081/realms/CTEC/protocol/openid-connect/token" \
  --data-urlencode "grant_type=authorization_code" --data-urlencode "client_id=ctec-frontend" \
  --data-urlencode "code=$CODE" --data-urlencode "redirect_uri=http://localhost:3000/auth/callback" \
  --data-urlencode "code_verifier=$VERIFIER")
ACCESS_TOKEN=$(printf '%s' "$TOKEN_RESPONSE" | jq -r .access_token)
rm -f "$COOKIES"
```

Unauthenticated requests fail closed:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/oqi/command-center
# expect: 401
```

Walk the real evidence → Finding chain for the seeded Country-of-Origin finding
(`condition_label="oqi-demo-supplier-country-of-origin"`, a deterministic id, unchanged across
every clean rebuild):

```bash
curl -s "http://localhost:8000/api/v1/oqi/findings?tenant_id=ctec-demo-tenant" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.items[] | select(.condition_label=="oqi-demo-supplier-country-of-origin")'
# expect: finding_id 8af76740-a069-50da-972f-e25d7a61110d, finding_family OQI2, highest_criticality
# HIGH, reliance_state RELIANCE_AT_RISK

FINDING_ID=8af76740-a069-50da-972f-e25d7a61110d
for path in "" "/evidence" "/ontology-impact" "/business-impact" "/reliance" "/agent-investigation"; do
  echo "=== $path ==="
  curl -s "http://localhost:8000/api/v1/oqi/findings/$FINDING_ID$path" -H "Authorization: Bearer $ACCESS_TOKEN"
done
```

Expect: evidence shows the real disagreement (SAP "US" vs. PLM "MX", neither ever labeled
"correct" — majority/authority is never truth); ontology-impact `IMPACTED`; business-impact
`BUSINESS_IMPACT_IDENTIFIED` against "Supplier Qualification (Demo)"; reliance history with
multiple entries; agent-investigation empty/`NOT_INVOKED` (this baseline scenario never requires
the OQI5-I2 investigation agent).

## 6. Command Center and UI walkthrough

```bash
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8000/api/v1/oqi/command-center
# expect: HTTP 200 with real open_findings_count/reliance_at_risk_count fields
```

Open `http://localhost:3000/quality` in a real browser, sign in as `ctec-demo-user`
(`$CTEC_DEMO_USER_PASSWORD`), and confirm the Command Center renders the same real counts. Click
through to **Findings**, open the Country-of-Origin finding, and step through its tabs: Evidence,
Ontology Impact, Business Impact, Explainable Reliance, Agent Investigation, Remediation. Also
confirm each of these routes returns 200: `/`, `/quality`, `/quality/findings`,
`/ontology/explorer`, `/ontology/modeling`.

## 7. Remediation prepare — human/steward-triggered, scope-gated, never automatic

**Human Authorization ≠ the Agent Recommendation.** A recommendation, if one is produced, is
always rendered as a distinct, separately-labeled block — never as something already approved.
`prepare_remediation` is never invoked automatically after evaluation; it requires an explicit,
authenticated, scope-gated call.

```bash
# Negative control -- token without oqi-remediation:prepare:
curl -s -w "\nhttp:%{http_code}\n" -X POST "http://localhost:8000/api/v1/oqi/findings/$FINDING_ID/remediation/prepare" \
  -H "Authorization: Bearer $ACCESS_TOKEN_NO_PREPARE_SCOPE" -H "Content-Type: application/json" -d '{}'
# expect: HTTP 403 {"detail":{"code":"AUTHORIZATION_SCOPE_REQUIRED"}}

# Positive control:
curl -s -X POST "http://localhost:8000/api/v1/oqi/findings/$FINDING_ID/remediation/prepare" \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" -d '{}'
# expect: HTTP 202 with 2 candidates (US / MX), 2 instructions, 2 pending authorizations,
#         "agent_reasoning_status":"NOT_INVOKED"
```

## 8. Governed remediation lifecycle — decide, report, automatic reevaluation

```bash
AUTH_ID=<one authorization_id from step 7's response>

curl -s -X POST "http://localhost:8000/api/v1/oqi/remediation/authorizations/$AUTH_ID/decide" \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
  -d '{"approve":true,"decided_by":"docker-smoke-test"}'
# expect: {"case_status":"APPROVED"}

curl -s -X POST "http://localhost:8000/api/v1/oqi/remediation/authorizations/$AUTH_ID/report-execution" \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" -d '{}'
# expect: {"case_status":"EXTERNAL_EXECUTION_REPORTED"}
```

**Report Execution** is a confirm-only action: it means *"an externally authorized remediation has
already been executed"* — CTEC has no source-system write-back capability anywhere. This same call
internally triggers `ProductionRemediationOrchestrationService.reevaluate_after_execution` right
after committing the execution report (reevaluation failure never crashes this response). Confirm
the **remediation ≠ resolution** invariant directly — since no new source evidence has actually
arrived, the case correctly stays at `EXTERNAL_EXECUTION_REPORTED` rather than falsely advancing:

```bash
curl -s "http://localhost:8000/api/v1/oqi/findings/$FINDING_ID/remediation" -H "Authorization: Bearer $ACCESS_TOKEN"
# expect: case_status still EXTERNAL_EXECUTION_REPORTED, not RESOLVED
```

The product's own remediation lifecycle stepper renders this as four separate, honestly-labeled
states: *Authorized → Externally Reported → Awaiting Re-evaluation → Resolved.* Resolution
requires fresh source evidence to arrive and the real evaluator to re-run against it — nothing in
this environment shortcuts that boundary.

## 9. 0046 tenant-integrity crown — real PostgreSQL, real cross-tenant proof

> **Operator warning, learned directly during this phase's own execution:** the test suite below
> performs a full migration teardown/rebuild against whatever `CTEC_TEST_DATABASE_URL` points at.
> **Never point it at this stack's live `ctec` database** — doing so wipes every seeded/derived
> demo row down to a bare `alembic_version` table. Always create and use a genuinely separate
> database, as shown below.

```bash
docker compose exec -e PGPASSWORD=ctec postgres psql -U ctec -d postgres \
  -c "CREATE DATABASE ctec_isolated_test OWNER ctec;"

# The runtime image ships no test dependencies (production image, by design). Install them
# non-persistently into the running container for this verification only:
docker compose exec --user root backend pip install --no-cache-dir 'pytest>=8.3,<9' 'pytest-cov>=6,<7' 'httpx>=0.28,<1'

docker compose exec -e CTEC_TEST_DATABASE_URL="postgresql+psycopg://ctec:ctec@postgres:5432/ctec_isolated_test" \
  backend python -m pytest app/tests/test_production_remediation_orchestration_postgres.py -q --no-cov
# expect: 14 passed, including test_prepare_cross_tenant_finding_not_found,
#   test_concurrent_prepare_across_tenants_does_not_cross_contaminate,
#   test_reevaluate_cross_tenant_authorization_returns_none, and
#   test_remediation_chain_tenant_integrity_enforced_by_real_postgresql

docker compose exec -e PGPASSWORD=ctec postgres psql -U ctec -d postgres -c "DROP DATABASE ctec_isolated_test;"
```

## 10. Persistence, isolated restarts, and certificate rotation

```bash
docker compose stop && docker compose start
```

Verified directly: Postgres data, the imported Keycloak realm/demo user, and the demo showcase
foundation all survive a full `stop`/`start` cycle intact; re-running the seeder afterward remains
a safe no-op; Command Center counts are unchanged.

```bash
docker compose restart postgres   # backend recovers; a fresh authenticated OQI read still succeeds
docker compose restart keycloak   # a fresh login/token flow still succeeds afterward
```

```bash
docker compose --profile ingestion-test up -d --force-recreate connector-fixture
```

Verified directly: the fixture's self-signed certificate serial changes on recreate, `backend`
does **not** need to be restarted, and step 3b's TLS positive-control proof succeeds again
immediately (after updating the fixture's IP the script resolves via `socket.gethostbyname`).

## 11. Clean reset and reproducibility

```bash
docker compose --profile ingestion-test down -v --remove-orphans
docker compose up -d
docker compose --profile ingestion-test up -d connector-fixture
```

Removes all named volumes (`postgres_data`, `connector_fixture_ca`) and re-provisions a genuinely
fresh environment — verified directly: the schema re-migrates to `0046_oqi5_remediation_tenancy`
with the same 126-table count, Keycloak re-imports the same realm, and re-running the demo seeder
reproduces the same deterministic `reliance_state='RELIANCE_AT_RISK'` outcome from empty state.

## Known limitations (disclosed, not Docker defects)

- **`EXECUTION_RECOVERY_OPERATOR` role gap (supplier-risk, pre-existing, out of Step-14 scope):**
  `app/api/supplier_risk/router.py` gates a recovery action on a Keycloak *role* the realm never
  defines (`"roles": {}`) — a role gap, not a scope gap, predating Step 14 and out of its
  re-verification scope. Recorded for completeness; no correction authorized here.
- **UNIQUENESS dimension:** not yet implemented; every evaluation response reports it as
  `NOT_EVALUABLE`, honestly, never as a false pass.
- **Step 13 residual findings:** 4 P2 + 4 P3 findings remain deliberately deferred (see CDD's own
  Step-13 closure record) — none block this Docker closure.
- **No PostgreSQL Row-Level Security:** tenant isolation is enforced entirely at the application
  layer (proven live in step 9), not via database-native RLS policies.

## Troubleshooting

- **`frontend` never shows `healthy` in `docker compose ps`.** Expected — see the note in step 1.
  Check reachability with `curl http://localhost:3000` instead.
- **Login form action extraction (step 5) returns nothing.** Keycloak's login page HTML structure
  only changes across major Keycloak version upgrades; if this repository's pinned
  `quay.io/keycloak/keycloak:26.0` image changes, re-inspect the page source for the
  `login-actions/authenticate` form action.
- **Step 3a returns anything other than `422 CONNECTOR_ENDPOINT_REJECTED`.** That would mean the
  production SSRF protection has regressed — this is the one result in this document that must
  never change to a success.
- **`503 AUTH_VERIFIER_UNAVAILABLE`.** `CTEC_OIDC_ISSUER`/`CTEC_OIDC_AUDIENCE`/`CTEC_OIDC_JWKS_URL`
  are unset — see Prerequisites.
- **Tenant-integrity crown test (step 9) appears to hang or the live demo data disappears.** You
  pointed `CTEC_TEST_DATABASE_URL` at the live `ctec` database — see the operator warning in step
  9. Recover with `docker compose up -d --force-recreate backend` (re-runs migrations
  idempotently) followed by re-running the demo seeder.
- **`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` not set.** Expected and required to stay unset for this
  entire checklist — nothing here should ever ask for one.
- **Credentials in logs.** `docker compose logs | grep -iE "password|secret"` should show no
  actual secret *values* — only environment-variable *names*, which is expected and fine.
