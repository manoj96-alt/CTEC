# Entity Resolution Steward

Exposes Gate B's deterministic multi-attribute evidence and policy engine
(`app/domain/identity_resolution`) as a tenant-safe human stewardship
workflow inside Ontology Studio. This is not a new matching engine or
identity representation — the workspace and its API only read and act on
evidence/decisions the domain engine already computed.

## Steward API endpoints and required OIDC scopes

All routes are under `/api/v1/entity-resolution`, reuse the Supplier Risk
API's authentication (`Authorization: Bearer <OIDC access token>` →
`TrustedPrincipal`), and take the tenant id only from the verified token —
never from a request body or query parameter.

| Method & path | Required scope | Purpose |
|---|---|---|
| `GET /cases` | `entity-resolution:read` | List resolution cases in the steward queue, optionally filtered by `?outcome=` |
| `GET /cases/{understanding_key}` | `entity-resolution:read` | Case detail: evidence profile, source representations, prior decision |
| `GET /policies` | `entity-resolution:read` | List available resolution policies |
| `POST /cases/{understanding_key}/preview?policy_id=` | `entity-resolution:read` | Read-only: evaluate the domain `decide()` function against a candidate policy; never appends or mutates anything |
| `POST /cases/{understanding_key}/decisions` | `entity-resolution:decide` | Record a steward decision (`confirm_match` / `reject_match` / `mark_unresolved` / `block_conflict`) with a required rationale |

The frontend must never reimplement matching or decision logic — the
preview endpoint exists specifically so the workspace can show a policy's
effect before a steward commits to it, using the server as the single
source of truth.

### Stable error contract

| Status | Code | When |
|---|---|---|
| 401 | `AUTH_TOKEN_MISSING` / OIDC verification error code | Missing or invalid bearer token |
| 403 | `AUTHORIZATION_SCOPE_REQUIRED` | Token is valid but lacks the required scope |
| 404 | `RESOLUTION_CASE_NOT_FOUND` / `RESOLUTION_POLICY_NOT_FOUND` | Case or policy does not exist, **or belongs to another tenant** — the response is identical either way (tenant-safe nondisclosure; a caller cannot distinguish "doesn't exist" from "not yours") |
| 409 | `STALE_RESOLUTION_CASE` | The decision's `based_on_record_id` no longer matches the case's current history pointer — nothing is appended |
| 422 | `NO_EVIDENCE_PROFILE_TO_PREVIEW` / `NO_EVIDENCE_PROFILE_TO_DECIDE` / `OVERRIDE_NOT_PERMITTED` / `DECISION_NOT_PERMITTED` | Validation and policy-semantics failures, including the veto-bypass guard (`confirm_match` can never override a strong-identifier conflict) |
| 429 | `RATE_LIMITED` | Supplier Risk's shared per-tenant rate limiter rejected the request |
| 500 | `SOURCE_PROVENANCE_INCOMPLETE` | A referenced source object/system is missing — fails loudly rather than silently omitting provenance |

Every read and every decision (including rejected/stale ones) is recorded
through the same `SecurityAuditService` Supplier Risk uses, with
`endpoint_classification=ENTITY_RESOLUTION_STEWARD_API_V1`.

## OIDC prerequisites (local demo / any non-trivial deployment)

**Backend** (`CTEC_` prefix, set via `.env` or environment):

- `CTEC_OIDC_ISSUER`, `CTEC_OIDC_AUDIENCE`, `CTEC_OIDC_JWKS_URL` — required; the
  server refuses to start token verification without all three (no baked-in
  default).
- `CTEC_OIDC_TENANT_CLAIM` (default `tenant_id`), `CTEC_OIDC_SCOPE_CLAIM`
  (default `scope`) — the access token must carry `entity-resolution:read`
  and/or `entity-resolution:decide` in this claim for the corresponding
  routes to authorize.

**Frontend** (`NEXT_PUBLIC_` prefix, baked in at build time):

- `NEXT_PUBLIC_OIDC_AUTHORITY`, `NEXT_PUBLIC_OIDC_CLIENT_ID`,
  `NEXT_PUBLIC_OIDC_REDIRECT_URI`, `NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI`,
  `NEXT_PUBLIC_CTEC_API_ORIGIN` — required.
- `NEXT_PUBLIC_OIDC_SCOPE` — optional; defaults to
  `"openid profile supplier-risk:read entity-resolution:read entity-resolution:decide"`.
  Override only if your OIDC client is scoped more narrowly than this
  default — a steward who lacks `entity-resolution:decide` can still open
  the workspace and read cases, but every decision action will fail with
  `403 AUTHORIZATION_SCOPE_REQUIRED`.

No secrets, tokens, or client credentials are included here or should ever
be committed; the values above are configuration *names*, not values.

## Demo-only TSMC seeder

Verified by inspecting `backend/app/infrastructure/persistence/demo_entity_resolution_seeder.py`
directly (it takes no CLI flags — there is no `--help`; confirmed no
`argparse`/`click`/`sys.argv` usage in the module):

```bash
cd backend
CTEC_DATABASE_URL=<target-database-url> python -m app.infrastructure.persistence.demo_entity_resolution_seeder
```

This runs `DemoEntityResolutionSeeder(session).seed()` once inside a single
transaction against whatever database `CTEC_DATABASE_URL` (via
`app.core.config.get_settings()`) resolves to. It is **never** called from
`main.py`'s `lifespan()` or any other startup path — normal bootstrap does
not invoke it. This is structural, not just a convention: it is its own
standalone module with an `if __name__ == "__main__":` entrypoint, and
`app/tests/test_runtime_architecture.py` enforces the runtime's import
boundaries so application startup code cannot reach into
`app.infrastructure.persistence` seeder modules undetected.

`seed(tenant_id=...)` defaults to and only ever accepts
`BOOTSTRAP_DEMO_TENANT_ID` (`"ctec-demo-tenant"`); any other tenant id
raises `DemoTenantRequiredError` before anything is written
(`test_demo_entity_resolution_seeder.py`,
`test_demo_entity_resolution_seeder_postgres.py`). Every seeded id is
deterministic (`uuid5`, namespaced), and each write is preceded by an
existence check, so re-running the command against the same database is a
no-op the second time.

## The three persisted TSMC scenarios

These are **deterministic sample scenarios for demonstration purposes
only** — clearly-labeled fictional evidence (e.g. tax-registration values
prefixed `DEMO-TAX-REG-...`), not claims about the real company. They exist
to give the steward workspace non-empty, honest data to review locally,
covering the three outcomes the decision semantics distinguish:

| Case | Evidence | Outcome |
|---|---|---|
| A | A CRM and a Registry source representation for "TSMC", no strong identifier present on either | `Possible Resolution` / Medium confidence |
| B | Same pair, both carrying the same demo tax-registration id | `Resolved` / High confidence |
| C | Same pair, carrying two different demo tax-registration ids (CRM vs. Registry) | `Blocked Conflict` (no candidate entity attached — a conflicting strong identifier is a hard veto) |

## Known limitations and deferred work

- No three-or-more-steward concurrent load/stress test (single- and
  two-actor concurrency is covered; higher fan-out is deferred).
- No policy-administration UI — policies are read and previewed, not
  authored or edited, from the workspace.
- Demo seeding is explicit/manual and demo-tenant-only; it is not part of
  any automatic bootstrap path.
- No production connector currently creates stewardship cases — cases seen
  today come only from the demo seeder or direct test fixtures.
- No bulk merge/reject workflow — every decision is recorded one case at a
  time, each with its own required rationale.
