# CDD-059 Artifact Authorization — Production Governed Enterprise REST Ingestion

Version: 1.0 FROZEN
Status: FROZEN
Governs: CDD-059 (FROZEN)

## 1. Authorization structure

One combined document, one exact path set — this capability has no multi-phase gate structure (unlike OQI5's
own I1/I2 split): DR (`Real-Enterprise-Ingestion-DR`) and G (this document) both independently concluded a
single implementation phase is correct, since Production Evaluation is never touched and no second genuine
architectural boundary exists. Every path below is authorized for `Real-Enterprise-Ingestion-I` immediately;
none is gated behind a separate future closure.

## 2. Exact implementation-path authorization (binding — a maximum permitted write set)

```
CREATE = 16
MODIFY = 12
DELETE = 0
TOTAL  = 28
```

| # | Action | Path | Purpose |
|---|---|---|---|
| 1 | CREATE | `backend/app/domain/integration/enterprise_connector.py` | `EnterpriseConnector` Protocol, `ConnectorRecord` (CDD-059 §8), deterministic external-record-identity validation. Consumes nothing from `oqi_*` domain packages — reusable transport-neutral contract only. |
| 2 | CREATE | `backend/app/infrastructure/connectors/__init__.py` | package marker |
| 3 | CREATE | `backend/app/infrastructure/connectors/rest_connector.py` | `RestConnector`: stdlib `urllib.request` only; SSRF policy (§32); TLS-verify-on always; pagination (§35); retry/backoff (§24); resource bounds (§33); closed error taxonomy (§25). No vendor-specific branching of any kind. |
| 4 | CREATE | `backend/app/application/connector_ingestion_service.py` | `ConnectorIngestionService`: trusted tenant orchestration, mapping application, two-hop `SourceField` tenant proof (§39), datatype normalization (§17), record-level accept/reject (§23), per-page transaction boundary (§21), run accounting (§14/§37). Never invokes `/evaluate`. |
| 5 | CREATE | `backend/app/infrastructure/persistence/models/oqi_connector.py` | ORM: `OqiConnectorConfigurationORM`, `OqiConnectorFieldMappingORM`, `OqiConnectorRunORM` — exact shape per CDD-059 §12-§14/§40. |
| 6 | CREATE | `backend/app/infrastructure/persistence/oqi_connector_repository.py` | repository: configuration/mapping/run CRUD (configuration: create/read/list/disable, never delete, §12), all reads/writes tenant-scoped at the query. |
| 7 | CREATE | `backend/app/infrastructure/persistence/migrations/versions/0045_oqi_connector_ingestion.py` | migration creating the 3 tables in §5 above, with the exact composite tenant-qualified FKs frozen in CDD-059 §40. `revision = "0045_oqi_connector_ingestion"` (28 characters — verified safe under the 32-character `alembic_version.version_num` bound, §6 below). |
| 8 | CREATE | `backend/app/api/oqi_connector/__init__.py` | package marker |
| 9 | CREATE | `backend/app/api/oqi_connector/schemas.py` | `ConfigureConnectorRequest`/`Response`, `ConfigureFieldMappingRequest`/`Response`, `RunConnectorResponse`, `ConnectorRunSummaryResponse` — every request schema `ConfigDict(extra="forbid")`, no `tenant_id` field anywhere, credential value never a request OR response field (§31/§50). |
| 10 | CREATE | `backend/app/api/oqi_connector/router.py` | Exactly 5 routes (§ AU of the governing G report): configure connector, list/read connector, disable connector, configure field mapping, run connector, read run detail/history — scoped per §41. |
| 11 | CREATE | `backend/app/api/oqi_connector/dependencies.py` | `authorize`-pattern reuse (imports the existing `app.api.oqi.dependencies.authorize`/`SecurityAuditService` wiring rather than duplicating it), connector-scoped `_record_success`/`_record_denied` mirroring CDD-058's own precedent exactly. |
| 12 | CREATE | `backend/app/tests/test_oqi_connector_ingestion_postgres.py` | The primary real-Postgres adversarial suite: domain contract, SSRF policy (every prohibited range), tenant-proof (real PostgreSQL structural attacks per §40, real API cross-tenant attacks per the governing report's cross-tenant matrix), mapping validation, retry/pagination logic, idempotence/replay, duplicate accounting invariant (§37), and the full real-network crown suite (positive/multi-source/update/replay/out-of-order/malformed-record/network-failure/scale — CDD-059 §51), using the in-process fixture server (item 14) over genuine loopback sockets for host/CI runs. |
| 13 | CREATE | `backend/app/tests/fixtures/__init__.py` | package marker (new package — `app/tests/fixtures/` does not yet exist) |
| 14 | CREATE | `backend/app/tests/fixtures/deterministic_http_fixture_server.py` | Deterministic, stdlib-only (`http.server`) HTTP fixture — importable in-process for host tests (item 12) AND runnable standalone (`__main__`) as the Docker-Compose fixture service (item 15 below). Supports the exact scripted modes named in CDD-059's governing report (§AZ/§BB-§BJ): normal/paginated response, independent Source-A/Source-B instances, updated value, replay, out-of-order timestamp, malformed record, malformed JSON, 429, 500, timeout, mid-pagination failure, single-hop redirect (to prove redirect-following is rejected, never to prove it works). |
| 15 | CREATE | `docs/cdd/CDD-059-Production-Governed-Enterprise-REST-Ingestion.md` | this phase's own governing CDD (already frozen, §K of the governing G report) |
| 16 | CREATE | `docs/cdd/CDD-059-Production-Governed-Enterprise-REST-Ingestion-Artifact-Authorization.md` | this document |
| 17 | MODIFY | `docker-compose.yml` | Exactly one new service entry (the fixture server from item 14, run via its `__main__` guard), added under a profile that is never part of the default `backend`/`frontend`/`postgres`/`keycloak` production graph and is never started by `docker-entrypoint.sh`. No existing service definition changes. |
| 18 | MODIFY | `backend/app/core/dependency_container.py` | Narrow, additive: wire `OqiConnectorRepositoryImpl`/`ConnectorIngestionService` into `Container`/`build_container()`, mirroring the existing `security_audit`/`ontology_sessions` construction pattern exactly. No existing field removed or restructured. |
| 19 | MODIFY | `backend/app/main.py` | Exactly one new line: `app.include_router(oqi_connector_router)`, mirroring every existing router-registration line exactly. No existing line changed. |
| 20 | MODIFY | `keycloak/ctec-realm.json` | Exactly three new client-scope entries — `oqi-connector:read`, `oqi-connector:configure`, `oqi-connector:run` — added to the client-scopes list and the client's default/optional-scope assignment, mirroring the exact existing structure already used for `oqi-remediation:authorize`/`oqi-remediation:report-execution` (CDD-058's own realm entries) byte-for-byte in shape. This explicitly closes the registration gap for THIS phase's own new scopes from day one — it does **not** retroactively register the pre-existing, unrelated `oqi-remediation:prepare` P3 gap (CDD-059 §54; that item remains carried forward to OQI-H7, untouched, never conflated with this narrow addition). |
| 21 | MODIFY | `backend/app/tests/test_oqi_evaluation_orchestration_postgres.py` | Mechanical only: the hardcoded `assert len(tables) == 123` literal becomes `== 126` (§6 below). No other line changes. |
| 22 | MODIFY | `backend/app/tests/test_oqi_remediation_agent_i2.py` | Mechanical only: identical `123` -> `126` table-count-literal bump. No other line changes. |
| 23 | MODIFY | `backend/app/tests/test_production_remediation_orchestration_postgres.py` | Mechanical only: identical `123` -> `126` table-count-literal bump. No other line changes. |
| 24 | MODIFY | `backend/app/tests/test_oqi_business_impact.py` | Mechanical only: identical `123` -> `126` table-count-literal bump. No other line changes. |
| 25 | MODIFY | `backend/app/tests/test_oqi_business_rule_postgres.py` | Mechanical only: identical `123` -> `126` table-count-literal bump. No other line changes. |
| 26 | MODIFY | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | Mechanical only: identical `123` -> `126` table-count-literal bump. No other line changes. |
| 27 | MODIFY | `backend/app/tests/test_persistence_integration.py` | Mechanical only: identical `123` -> `126` table-count-literal bump. No other line changes. |
| 28 | MODIFY | `backend/app/tests/test_oqi_remediation_i1.py` | Mechanical only: identical `123` -> `126` table-count-literal bump. No other line changes. |

No path beyond these 28 is authorized. No frontend path (`frontend/` CREATE=0, MODIFY=0, DELETE=0). No path
touching `oqi_evaluation_orchestration_service.py`, its router/schemas, any of the 9 dimension evaluators, OQI4,
OQI6, Reliance, OQI5/remediation, `SourceSystem`/`SourceObject`/`SourceField`/`FieldValueEvidence` domain or
ORM files, `oqi_cross_source_correspondence_repository.py`, `semantic_mapping_repository.py`, or
`model_provider/provider.py`.

## 3. Explicit prohibitions (binding, exhaustive)

No file under `backend/app/domain/oqi*`, `backend/app/application/oqi_evaluation_orchestration_service.py`,
`backend/app/application/oqi_business_impact_service.py`, `backend/app/application/oqi_remediation_service.py`,
`backend/app/application/production_remediation_orchestration_service.py`, `backend/app/api/oqi/` (the
*existing* OQI7 router/schemas/dependencies — this phase's own new API lives entirely under the *new*
`backend/app/api/oqi_connector/` package instead), any migration other than `0045_oqi_connector_ingestion`, any
ORM model file other than `oqi_connector.py`, any frontend file, `backend/Dockerfile`, `frontend/Dockerfile`,
`backend/docker-entrypoint.sh`, CDD-019/022/039/040/041/056/058 or any of their own Artifact Authorizations. No
DELETE of any kind. No opportunistic cleanup. No refactor of `FieldValueEvidenceRepositoryImpl`,
`SourceFieldRepositoryImpl`, or any existing OQI evaluator beyond the 8 named, exact, single-literal
table-count-bump edits.

## 4. Implementation branch (binding)

```
real-enterprise-ingestion/rest-connector
```
Mirrors the exact `<phase-slug>/<descriptive-aspect>` convention of every prior phase
(`production-remediation/orchestration`, `production-orchestration/explicit-evaluation-trigger`,
`oqi5/remediation-foundation`).

## 5. Migration-head mechanical regression — confirmed moot (binding finding)

Independently re-verified directly against `CDD-055`'s own governance record (§25 of that document): the
historical "hardcoded migration-head literal" mechanical-bump burden CDD-043 §5 once required (a named list of
files needing a literal revision-string update on every new migration) **no longer applies** — every migration-
head assertion in the current test suite resolves dynamically via `ScriptDirectory.get_current_head()`, a fix
already in place before CDD-055 and carried forward unchanged through CDD-056/057/058, none of which required
this class of bump. `0045_oqi_connector_ingestion` therefore requires **zero** migration-head-literal file
edits. The **separate, still-real** table-count-literal class (items 21-28 above) is the only mechanical
regression this migration causes, and is fully enumerated and pre-authorized above — not left implicit.

## 6. Revision-identifier and enum-width verification (performed at governance time, per OQI2/OQI5 lesson)

```
Revision string "0045_oqi_connector_ingestion" = 28 characters -- safe under the 32-character
    alembic_version.version_num bound (verified by direct character count, not estimated).
```
```
oqi_connector_configurations.connector_type   longest value "GENERIC_REST"           (12 chars) -> String(32) safe
oqi_connector_configurations.auth_mechanism    longest value "BEARER_TOKEN"          (12 chars) -> String(32) safe
oqi_connector_configurations.pagination_style  longest value "CURSOR"                 (6 chars) -> String(16) safe
oqi_connector_configurations.status            longest value "DISABLED"               (8 chars) -> String(16) safe
oqi_connector_runs.status                      longest value "SUCCEEDED"              (9 chars) -> String(16) safe
oqi_connector_runs.failure_kind                longest value "CONNECTOR_AUTHENTICATION_FAILED" (31 chars, verified
                                                by direct character count) -> String(32) would be a 1-character
                                                margin; String(40) is frozen instead (CDD-059 §14) to avoid
                                                repeating this repository's own recurring off-by-a-few-characters
                                                history (OQI2's migration-revision-length defect, this same
                                                document's own §5 finding) -- deliberate extra margin, not
                                                arbitrary.
```

## 7. Table count expectations (binding)

```
Pre-CDD-059:   123  (verified, Production-Remediation-Orchestration-VM's own post-merge proof, re-verified
                     independently again at the start of this governance phase, §2 of CDD-059)
Post-CDD-059:  126  (123 + 3: oqi_connector_configurations, oqi_connector_field_mappings, oqi_connector_runs)
```

## 8. Docker fixture service — exact topology (binding)

The fixture service (item 14 above, run via item 17's new `docker-compose.yml` entry) is:
```
a separate container, built from the existing backend/Dockerfile-produced image (reusing the same Python
    runtime; no new base image), overriding its entrypoint to run
    `python -m app.tests.fixtures.deterministic_http_fixture_server` instead of the production
    `docker-entrypoint.sh`
reachable only by its own Docker-Compose service name on the internal Compose network (never published to
    the host, never reachable from outside the Compose network)
never depended upon by the `backend` or `frontend` service definitions -- the production image and the
    production service graph are byte-identically unaffected by this addition
started only when a test/CI profile explicitly requests it (`docker compose --profile ingestion-test up`
    or the VM phase's own equivalent invocation), never by a bare `docker compose up`
```
Serves HTTPS with a self-signed certificate generated deterministically at fixture-server startup; the test
suite's own HTTP client configuration trusts that specific certificate explicitly (e.g. via a test-scoped CA
bundle passed to `RestConnector`'s own, already-parameterized SSL context) — **never** by disabling verification
globally and **never** by adding a production HTTP-only code path. This is the exact mechanism CDD-059 §34
requires be resolved cleanly, resolved here: the production connector's TLS-verification code path is
identical in test and production; only the trusted CA differs, injected the same way a real enterprise
customer's own custom-CA configuration would be (a capability explicitly deferred, §54, but whose test-only
narrow use here does not require implementing that deferred feature — the test fixture supplies its CA bundle
directly to the same standard-library `ssl.create_default_context(cafile=...)` mechanism `urllib.request`
already uses, which requires no new production configuration surface).

## 9. Final accounting

```
CREATE 16 / MODIFY 12 / DELETE 0 / TOTAL 28 -- exact, no phase gating, fully authorized now for
Real-Enterprise-Ingestion-I.
```
