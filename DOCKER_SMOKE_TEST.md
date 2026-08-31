# Docker Smoke Test — Governed OQI Demo Environment

Every command below was independently executed against a genuinely fresh local stack during
Docker-I and produced the stated result. Run from a machine with Docker + Docker Compose
installed; no registry access or paid model API key is required for any step in this document.

## Prerequisites

```bash
# Required, no baked-in default (see docker-compose.yml comments for how to generate
# CTEC_RUNTIME_HANDOFF_KEY):
export CTEC_RUNTIME_HANDOFF_KEY=<your own base64 value>
export CTEC_KEYCLOAK_ADMIN_PASSWORD=<a local-only admin password>
export CTEC_DEMO_USER_PASSWORD=<a local-only demo-user password>
```

None of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or any other model-provider credential is
required anywhere in this document. The OQI product is fully deterministic; Anthropic is never
instantiated on any route this checklist exercises.

## 1. Fresh build

```bash
docker compose build
```

Expect: both `backend` and `frontend` images build successfully.

## 2. Fresh boot (no reused state)

```bash
docker compose up -d
```

Expect: `postgres`, `keycloak`, and `backend` report `healthy` via `docker compose ps` within
~60 seconds; `keycloak-bootstrap` runs once and exits `0`.

> **Frontend health note:** `docker-compose.yml`'s own `frontend` healthcheck runs `wget
> http://localhost:3000` *inside* the container. Docker automatically sets that container's
> `HOSTNAME` environment variable to its own container ID, and Next.js's standalone
> `server.js` binds to that value rather than `0.0.0.0` — so the container-internal healthcheck
> can never pass, even though the service is genuinely reachable on its published port from any
> real external caller (browser, `curl` from the host, another container). This is a real,
> pre-existing packaging quirk, unrelated to OQI/Keycloak, and is out of scope for this
> document to fix. Verify frontend reachability from the host instead:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
# expect: 200
```

## 3. Migration head

```bash
docker compose exec -e PGPASSWORD=ctec postgres psql -U ctec -d ctec -tAc \
  "SELECT version_num FROM alembic_version"
# expect: 0026_oqi6_reliance
```

## 4. Table count

```bash
docker compose exec -e PGPASSWORD=ctec postgres psql -U ctec -d ctec -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' AND table_name != 'alembic_version'"
# expect: 100 (alembic_version itself is a 101st table -- migration bookkeeping, not product schema)
```

## 5. Backend liveness

```bash
curl -s http://localhost:8000/health
# expect: {"status":"healthy"} -- process liveness only, not a readiness/DB check
```

## 6. Keycloak realm and OQI scope classification

```bash
admin_token=$(curl -s -X POST http://localhost:8081/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli" -d "grant_type=password" \
  -d "username=admin" -d "password=$CTEC_KEYCLOAK_ADMIN_PASSWORD" | jq -r .access_token)
client_uuid=$(curl -s -H "Authorization: Bearer $admin_token" \
  "http://localhost:8081/admin/realms/CTEC/clients?clientId=ctec-frontend" | jq -r '.[0].id')
curl -s -H "Authorization: Bearer $admin_token" \
  "http://localhost:8081/admin/realms/CTEC/clients/$client_uuid/default-client-scopes" | jq -r '.[].name'
curl -s -H "Authorization: Bearer $admin_token" \
  "http://localhost:8081/admin/realms/CTEC/clients/$client_uuid/optional-client-scopes" | jq -r '.[].name'
```

Expect: `oqi:read` appears in the **default** list (issued to every session automatically);
`oqi-remediation:authorize` and `oqi-remediation:report-execution` appear in the **optional**
list (issued only when explicitly requested — matching the frontend's own OIDC config).

## 7. Unauthenticated OQI request fails closed

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/oqi/command-center
# expect: 401
```

## 8. Authenticated OQI read — real governed login flow

`ctec-frontend` deliberately disables the Resource Owner Password Credentials grant (a real
security property, not a gap) — obtaining a real token requires the same Authorization Code +
PKCE flow a real browser performs. The commands below simulate exactly that flow, never a
shortcut grant type:

```bash
VERIFIER=$(openssl rand -base64 96 | tr -dc 'A-Za-z0-9' | cut -c1-64)
CHALLENGE=$(printf '%s' "$VERIFIER" | openssl dgst -sha256 -binary | openssl base64 | tr '+/' '-_' | tr -d '=')
COOKIES=$(mktemp)
SCOPE="openid profile oqi:read oqi-remediation:authorize oqi-remediation:report-execution"

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

curl -s -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8000/api/v1/oqi/command-center
# expect: HTTP 200 with real reliance_*/open_findings_count fields (all 0 before step 9)
```

Decode the token to confirm all three OQI scopes were genuinely issued:

```bash
PAYLOAD=$(printf '%s' "$ACCESS_TOKEN" | cut -d. -f2 | tr '_-' '/+')
PAD=$(( (4 - ${#PAYLOAD} % 4) % 4 )); for _ in $(seq 1 "$PAD" 2>/dev/null || true); do PAYLOAD="${PAYLOAD}="; done
printf '%s' "$PAYLOAD" | base64 -d | jq -r .scope
# expect: contains oqi:read, oqi-remediation:authorize, oqi-remediation:report-execution
```

## 9. Deterministic OQI demo-showcase foundation

```bash
docker compose exec backend python -m app.infrastructure.persistence.demo_oqi_seeder
```

Expect a summary line ending `reliance_state='RELIANCE_AT_RISK'`. This seeds only raw,
disagreeing multi-source evidence (a demo supplier's Country of Origin: SAP says "US", PLM says
"MX") and governed configuration (the quality rule, the business process/dependency) — it never
directly inserts a Finding, an ontology-impact row, a business-impact row, or a Reliance state.
Those are all produced by calling the real, unmodified OQI2/OQI4/OQI6 evaluators against that
seeded evidence. Re-running this command is safe — idempotent, and scoped to the demo tenant
only (`ctec-demo-tenant`).

Re-check the Command Center — the counts now reflect the real derived state:

```bash
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8000/api/v1/oqi/command-center
# expect: open_findings_count: 1, reliance_at_risk_count: 1
```

## 10. OQI Command Center navigation

Open `http://localhost:3000/quality` in a real browser, sign in as `ctec-demo-user`
(`$CTEC_DEMO_USER_PASSWORD`), and confirm the Command Center renders the same real counts from
step 9 (Reliance Supported / At Risk / Unknown, Open Findings, Critical Dependencies At Risk).
Click through to **Findings**, open the seeded finding, and step through its tabs: Evidence
(SAP "US" vs. PLM "MX", neither ever labeled "correct" — majority/authority is never truth),
Ontology Impact, Business Impact, Explainable Reliance, Agent Investigation, Remediation.

## 11. Human authorization walkthrough

**Human Authorization ≠ the Agent Recommendation.** A recommendation, if one has been produced,
is always rendered as a distinct, separately-labeled block — never as something already
approved. Approving is a genuine action a human takes explicitly in the browser; nothing in this
document or the demo seeder pre-approves, pre-decides, or otherwise fakes a human authorization.

> **Current limitation, disclosed, not a Docker defect:** as of this Docker-I phase, the
> product has no live trigger — no API route, no browser action — that moves a Finding from
> "evaluated" to "has a pending `RemediationAuthorization` ready to decide." OQI5's candidate
> extraction / instruction / authorization-request pipeline exists and is fully tested at the
> service layer, but is not yet wired to any HTTP route or UI action. Until a future,
> separately-governed product phase adds that trigger, the **Decide Authorization** button in
> the Remediation tab has nothing to act on in a freshly-seeded environment. This is a real,
> disclosed product-integration gap, not something Docker packaging can or should paper over.

## 12. Report-execution walkthrough

Once a pending authorization exists and is approved (see the limitation above), **Report
Execution** in the Remediation tab is a confirm-only action with no input fields. It means: *"I
am reporting that an externally authorized remediation has already been executed."* It does
**not** mean CTEC performed that execution — CTEC has no source-system write-back capability
anywhere, and the confirmation copy says so explicitly.

## 13. Fresh-evidence / re-evaluation truth boundary

Reporting execution never, by itself, causes the Finding to read "Resolved," the Reliance state
to become "Supported," or any other terminal claim. The product's own remediation lifecycle
stepper renders exactly this distinction: *Authorized → Externally Reported → Awaiting
Re-evaluation → Resolved* are four separate, honestly-labeled states — resolution requires fresh
source evidence to arrive and the real, deterministic OQI evaluator to re-run against it. Nothing
in this environment, seeded or otherwise, shortcuts that boundary.

## 14. Stop

```bash
docker compose stop
```

## 15. Restart (persistence)

```bash
docker compose start
# or: docker compose up -d
```

Verified directly during Docker-I: Postgres data, the imported Keycloak realm/demo user, and the
demo showcase foundation (still exactly 1 seeded Finding, not duplicated) all survive a full
`stop`/`start` cycle intact. Re-running the seeder after restart remains a safe no-op.

## 16. Isolated service restart

```bash
docker compose restart postgres   # backend recovers; a fresh authenticated OQI read still succeeds
docker compose restart keycloak   # a fresh login/token flow still succeeds afterward
```

Both were verified directly during Docker-I against a real running stack.

## 17. Clean reset

```bash
docker compose down -v --remove-orphans
docker compose up -d
```

Removes all volumes (Postgres data, nothing else is a named volume) and re-provisions a
genuinely fresh environment — verified directly: the schema re-migrates to `0026_oqi6_reliance`
with the same 100-table count, and Keycloak re-imports the same realm.

## Troubleshooting

- **`frontend` never shows `healthy` in `docker compose ps`.** Expected — see the note in step
  2. Check reachability with `curl http://localhost:3000` instead.
- **Login form action extraction (step 8) returns nothing.** Keycloak's login page HTML
  structure only changes across major Keycloak version upgrades; if this repository's pinned
  `quay.io/keycloak/keycloak:26.0` image changes, re-inspect the page source for the
  `login-actions/authenticate` form action.
- **`REMEDIATION_*` errors when clicking Decide/Report Execution.** Expected in a freshly-seeded
  environment — see step 11's disclosed limitation.
- **`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` not set.** Expected and required to stay unset for this
  entire checklist — nothing here should ever ask for one.
- **Credentials in logs.** `docker compose logs | grep -iE "password|secret"` should show no
  actual secret *values* — only environment-variable *names*, which is expected and fine.
