# CDD-059 — Production Governed Enterprise REST Ingestion

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Governing authorities: CDD-022 (FROZEN, Governed Source Field-Value Evidence — its domain/persistence files are
read-only consumed, never modified; this document explicitly reconfirms `FieldValueEvidence`'s identity,
append-only, and current-selection semantics unchanged), CDD-019 (FROZEN, Source-to-Blueprint Semantic Mapping —
`SourceSystem`/`SourceObject`/`SourceField` consumed read/write through their existing, unmodified repositories
only), CDD-039/040/041 (FROZEN, OQI1/OQI2/OQI3 — evidence consumers, unmodified), CDD-056 (FROZEN, Production OQI
Explicit Evaluation Orchestration — `POST /api/v1/oqi/evaluate` remains the sole, separate, explicit invocation
path; not modified, not auto-invoked), CDD-058 (FROZEN, Production Governed Remediation Orchestration, unrelated,
unchanged)
Precedent: Real-Enterprise-Ingestion-DR (discovery; this document freezes its recommended architecture with zero
material refinement — DR's own conclusion is independently reconfirmed true during this governance phase, see §2)
Classification: NEW PRODUCTION CAPABILITY — NEW DOMAIN CONTRACT, NEW INFRASTRUCTURE ADAPTER, NEW PERSISTENCE (3
tables), NEW API SURFACE, ZERO changes to the existing evidence foundation or Production Evaluation chain

## 1. Purpose

Freezes the exact architecture, security invariants, persistence schema, API contract, and verification
obligations for Noetva's first genuine bridge between a real external enterprise REST data source and its
governed evidence system. This document authorizes the smallest correct closure of the proven capability gap
(zero genuine production enterprise connectors): **a tenant-scoped, explicitly-triggered, bounded, synchronous
Generic Governed REST Connector that fetches real external HTTP data, admits it as `FieldValueEvidence` against
pre-existing, pre-governed `SourceSystem`/`SourceObject`/`SourceField` configuration, and stops** — Production
Evaluation remains a separate, unmodified, explicitly-invoked action.

## 2. Independent re-verification — authoritative baseline (binding)

`origin/main`, local `main`, and GitHub `main` all independently re-confirmed equal to
`5d59eec14f7248e543b806c840d2199c3f66e131` (Production-Remediation-Orchestration-VM's own merge commit).
Migration head independently reconfirmed `0044_oqi4_r1_current_tenancy`, single head. Table count independently
reconfirmed `123`. Working tree independently reconfirmed clean except the inherited, pre-existing, unrelated
untracked `docs/product/` (untouched, not part of this or any prior phase).

DR's central findings independently re-derived, not merely trusted, during this governance phase:
```
SourceSystem/SourceObject carry a genuine tenant-qualified composite FK
    (fk_source_objects_tenant_source_system on (tenant_id, source_system_id)) -- confirmed directly in
    app/infrastructure/persistence/models/source_object.py.
SourceField/FieldValueEvidence carry NO tenant_id column at all, by CDD-019/CDD-022's own deliberate design --
    confirmed directly; tenant is resolved transitively, exactly as FieldValueEvidenceRepositoryImpl.
    get_by_source_field already demonstrates the correct two-hop join.
FieldValueEvidence identity is exactly the 4-tuple (source_field_id, source_record_reference,
    observed_representation, observed_at), domain-derived via uuid5 -- confirmed directly in
    app/domain/integration/field_value_evidence.py. received_at/evidence_reference do not participate.
Current-evidence selection is `ORDER BY observed_at DESC, received_at DESC` filtered
    `observed_representation != ""` and `received_at <= evaluation_horizon` -- confirmed byte-identical across
    all three call sites in oqi_quality_evaluation_repository.py.
Zero production callers exist for SourceSystem/SourceObject/SourceField creation, for
    OqiCrossSourceCorrespondenceRepositoryImpl.create(), or for SemanticMappingRepositoryImpl.create() -- all
    demo/test-only, confirmed by exhaustive grep.
Zero production httpx/requests/aiohttp import exists; AnthropicMessagesProvider's stdlib-only
    (urllib.request) precedent, adapter-owned os.environ credential read, and closed ProviderFailureKind
    taxonomy are confirmed directly in app/infrastructure/model_provider/provider.py and are the frozen
    architectural template for this connector's own HTTP/failure-taxonomy design (§9/§27).
No Celery/Kafka/Redis/worker/scheduler infrastructure exists anywhere in docker-compose.yml or pyproject.toml;
    CDD-022/CDD-051/CDD-056/CDD-058 each independently and explicitly prohibit exactly this class of
    infrastructure -- confirmed directly.
```
DR's architecture selection (generic pull REST connector, synchronous V1, Level 1+2 proof, backend-only,
Production Evaluation untouched) is independently reconfirmed correct and is frozen below without material
change.

## 3. Definitions

```
Connector           A configured, tenant-owned binding of one external HTTPS REST endpoint to one existing
                     SourceSystem, with a closed authentication mechanism and a set of field mappings.
Connector Run        One bounded, synchronous, explicitly-triggered execution of a Connector against its
                     live external endpoint, producing a terminal run record.
Field Mapping        A governed, administrator-configured binding of one external JSON field path to one
                     existing SourceField, scoped to one Connector.
ConnectorRecord       The transport-neutral, in-memory-only envelope one externally-fetched logical record
                     is normalized into before mapping/admission (§8). Never persisted verbatim.
Evidence Admission   The act of constructing and calling `FieldValueEvidence.new(...)` +
                     `FieldValueEvidenceRepositoryImpl.create_or_get_existing(...)` -- unchanged, existing
                     mechanism (§18/§19).
```

## 4. In scope

```
Domain contract for a generic enterprise connector (EnterpriseConnector Protocol, ConnectorRecord envelope).
One infrastructure adapter: RestConnector (stdlib urllib.request, HTTPS-only, SSRF-hardened, paginated,
    retried, bounded).
Application service: ConnectorIngestionService (trusted orchestration, tenant proof, mapping application,
    per-page transaction boundary, run accounting).
New tenant-owned persistence: connector configuration, field mapping, run ledger (§12-§14).
New, narrow API surface for configuring, reading, and running a connector, and reading run history (§AU of
    the governing G report; exact routes frozen in the Artifact Authorization).
Reuse of the existing SecurityAuditService for connector lifecycle/run events.
One new Docker-Compose test/CI-only deterministic HTTP fixture service, never part of the production
    `backend`/`frontend` topology.
```

## 5. Out of scope (binding)

```
Any modification to SourceSystem/SourceObject/SourceField/FieldValueEvidence existing semantics, identity,
    append-only behavior, or current-evidence selection.
Any modification to Production Evaluation (oqi_evaluation_orchestration_service.py, its router/schemas, any
    of the 9 dimension evaluators, OQI4, OQI6, Reliance, OQI5/remediation).
Automatic invocation of `/api/v1/oqi/evaluate` from a connector run.
Automatic creation of SourceSystem, SourceObject, SourceField, SemanticMapping, or
    ComparisonSubjectCorrespondence.
EntityResolution invocation of any kind.
Any scheduler, worker, queue, Celery, Redis, Kafka, CDC, or webhook/push ingestion mechanism.
OAuth2, Basic auth, mTLS, custom-CA support (all explicitly deferred, §30).
Any frontend path.
Any vendor-specific (SAP/Snowflake/Databricks/Fabric) adapter or certification claim (Level 3, explicitly
    deferred).
Live LLM/agent-provider wiring of any kind.
```

## 6. Architecture (binding) — full production flow

```
External Enterprise REST Source (administrator-configured HTTPS endpoint)
        |  HTTPS, SSRF-validated, credential from server-side environment
        v
RestConnector (infrastructure) -- stdlib urllib.request, paginated, retried, bounded
        |
        v
ConnectorRecord (transport-neutral envelope; never persisted verbatim)
        |
        v
ConnectorIngestionService (application) -- tenant proof (2-hop), mapping application, datatype
        |                                    normalization, record-level accept/reject
        v
FieldValueEvidence.new(...) -> FieldValueEvidenceRepositoryImpl.create_or_get_existing(...)
        |  (existing, unmodified mechanism; per-page short transaction; §21)
        v
[ CONNECTOR RUN STOPS HERE -- terminal run record persisted, honest counts reported ]

--------------------------- separate, explicit, pre-existing action ---------------------------

        POST /api/v1/oqi/evaluate  (CDD-056, unmodified, human/API-triggered)
        |
        v
        9 DQ dimensions -> OQI4 -> OQI6 -> Reliance   (all existing, unmodified)
```

## 7. Central governance invariants (binding)

```
REMOTE DATA != TENANT AUTHORITY               -- TrustedPrincipal.tenant_id is the sole tenant source (§13).
TRANSPORT SUCCESS != DATA QUALITY              -- ingestion success is never a DQ Finding (§26).
INGESTION SUCCESS != EVALUATION SUCCESS        -- evaluation is a separate, explicit, unmodified action (§9/§25).
SERVICE TENANT VALIDATION != DATABASE TENANT ENFORCEMENT
                                                -- every new table structurally tenant-isolated from its first
                                                   migration (§15).
```

## 8. Normalized ConnectorRecord contract (binding, exact)

```python
@dataclass(frozen=True, slots=True)
class ConnectorRecord:
    external_record_id: str          # the administrator-designated stable natural key; never fabricated
    observed_at: datetime             # tz-aware; source event time, or the frozen fallback (§10)
    fields: Mapping[str, str | None]  # field_label -> raw string value, or None for JSON null/explicit empty
                                       # (a key ABSENT from this mapping means the source payload omitted it
                                       # entirely -- distinct from a present key mapped to None; §11)
```
`fields` never carries a `tenant_id` key or any other authority-bearing value; the envelope is purely
transport-neutral data. Run/connector/tenant context is supplied exclusively by the trusted orchestration layer
(`ConnectorIngestionService`), never derived from `ConnectorRecord` content.

## 9. Evidence identity — unchanged (binding, restated verbatim from CDD-022)

```
field_value_evidence_id = uuid5(BOOTSTRAP_SEED_NAMESPACE, canonical(source_field_id, source_record_reference,
                                                                     observed_representation, observed_at))
```
`received_at` and `evidence_reference` never participate. No connector-specific evidence-identity mechanism is
authorized. Replay of an identical observation converges to the existing row via
`FieldValueEvidenceRepositoryImpl.create_or_get_existing` unmodified.

## 10. observed_at / received_at (binding, exact)

`observed_at` MUST be the source's own genuine event/extraction timestamp when the source supplies one.

**Frozen fallback when the source supplies no trustworthy per-record event timestamp**: the
`ConnectorIngestionService` establishes exactly one trusted extraction timestamp — `run_started_at` — at the
start of the run, before any page is fetched, and uses this same single value as `observed_at` for every record
lacking a source-supplied timestamp within that run. This is deterministic within a run (identical for every
qualifying record in that run) and therefore preserves replay safety for that run (re-running produces a
*different* `run_started_at` and therefore genuinely new, additional historical evidence on replay of unchanged
data — an accepted, disclosed consequence of a source with no real event-time concept, not a defect). Connectors
whose source *does* supply a genuine timestamp per record MUST use it; the fallback is a documented last resort,
never a silent default when a real timestamp is available.

`received_at` is always the wall-clock moment `ConnectorIngestionService` admits the record, established
independently per page/batch, never substituted for `observed_at`, preserving H5 `TimelinessPolicy`
(`freshness_window_seconds` on `observed_at`; `ingestion_sla_seconds` on the `observed_at`→`received_at` gap)
exactly as already governed.

## 11. Null vs absent (binding, restated exact)

```
JSON null, or an explicitly empty value the source returns for a mapped field
    -> ConnectorRecord.fields[field_label] = None -> admitted as observed_representation=""
A mapped field's key entirely absent from the source payload
    -> ConnectorRecord.fields has no entry for field_label at all -> NO evidence row admitted this run
```
Never silently transformed one into the other. Both are structurally distinguishable at the persistence layer
(row exists with `""` vs. no new row); today's evaluators already treat both as equally non-qualifying for
value-selection purposes, per CDD-039's own frozen `observed_representation != ""` convention — unchanged.

## 12. Connector configuration — conceptual schema (binding)

```
oqi_connector_configurations
    connector_id            UUID, PK
    tenant_id                String(200), NOT NULL
    source_system_id         UUID, NOT NULL
    display_name             String(200), NOT NULL
    connector_type            String(32), NOT NULL   -- closed: "GENERIC_REST" (V1's only value)
    endpoint_url              String(2000), NOT NULL  -- HTTPS only, validated at write time (§32)
    auth_mechanism            String(32), NOT NULL   -- closed: "API_KEY" | "BEARER_TOKEN"
    auth_header_name          String(200), NULLABLE   -- required iff auth_mechanism = API_KEY
    credential_env_var_name  String(200), NOT NULL   -- a REFERENCE only; never the secret value
    pagination_style          String(16), NOT NULL   -- closed: "NONE" | "CURSOR"
    status                    String(16), NOT NULL   -- closed: "ACTIVE" | "DISABLED"
    created_by                String(200), NOT NULL   -- principal_id, not an enterprise_entities FK (this is
                                                        operational configuration, not ontology governance
                                                        vocabulary -- deliberately NOT shaped like
                                                        SourceSystem/SourceObject's own lifecycle_state/
                                                        governance_status/version_number fields, which govern
                                                        a materially different kind of artifact)
    created_on                TIMESTAMPTZ, NOT NULL
    modified_by                String(200), NULLABLE
    modified_on                TIMESTAMPTZ, NULLABLE
```
No `lifecycle_state`/`governance_status`/`version_number` — this is operational connector configuration, not
ontology-governance vocabulary; versioning is explicitly deferred (§34, P3). Disabling (`status="DISABLED"`) is
the only supported deactivation; **delete is not authorized in V1** — a connector row, once created, may only
transition to `DISABLED`, never be removed, so no historical evidence's provenance trail can ever dangle. This
is stricter than DR's own "prefer disable over delete" recommendation, adopted here because V1 introduces no
delete path to reason about at all, eliminating an entire class of future defect.

## 13. Field mapping — conceptual schema (binding)

```
oqi_connector_field_mappings
    mapping_id                UUID, PK
    tenant_id                 String(200), NOT NULL
    connector_id               UUID, NOT NULL
    external_field_path        String(500), NOT NULL   -- dotted-path traversal contract (§29)
    source_field_id             UUID, NOT NULL
    is_external_record_id       BOOLEAN, NOT NULL DEFAULT false  -- exactly one mapping per connector must be true
    created_by                 String(200), NOT NULL
    created_on                 TIMESTAMPTZ, NOT NULL
```
Exactly one field mapping per connector MUST carry `is_external_record_id=true`, designating which external
path supplies `ConnectorRecord.external_record_id` (§16/D10). A connector with zero or more-than-one such mapping
fails closed at configuration-save time (`MAPPING_INVALID`) — never silently picks one. Mapping establishes
`external_field_path → source_field_id` only; it never creates a `SourceField`, `SourceObject`, `SourceSystem`,
`SemanticMapping`, or `ComparisonSubjectCorrespondence` (§27/§ Business-rule integration, restated from DR §44,
§45, §X of the DR report).

## 14. Connector run ledger — conceptual schema (binding)

```
oqi_connector_runs
    run_id                     UUID, PK
    tenant_id                  String(200), NOT NULL
    connector_id                UUID, NOT NULL
    correlation_id               UUID, NOT NULL         -- equals run_id unless a caller-supplied
                                                          correlation_id is threaded through (mirrors
                                                          CDD-056/058's own optional correlation_id pattern)
    status                      String(16), NOT NULL     -- closed: "RUNNING" | "SUCCEEDED" | "PARTIAL" | "FAILED"
    started_on                  TIMESTAMPTZ, NOT NULL
    completed_on                 TIMESTAMPTZ, NULLABLE
    checkpoint_page_token         String(2000), NULLABLE  -- opaque cursor/next-link for within-run resume only
    fetched_records               INTEGER, NOT NULL DEFAULT 0
    accepted_records               INTEGER, NOT NULL DEFAULT 0
    rejected_records                INTEGER, NOT NULL DEFAULT 0
    duplicate_records                INTEGER, NOT NULL DEFAULT 0
    evidence_written                INTEGER, NOT NULL DEFAULT 0   -- accepted_records minus duplicate_records
                                                                    among accepted (§40)
    failure_kind                    String(40), NULLABLE    -- closed taxonomy, §27
    failure_summary                  String(500), NULLABLE   -- credential-free, human-readable; never a raw
                                                               exception string, never a response body
    triggered_by                    String(200), NOT NULL    -- principal_id
```
No `PENDING` state is authorized — a run row is created only at the moment of genuine, synchronous execution
start (`RUNNING`), never queued (§15/§AF). `duplicate` (§40) counts records whose computed evidence identity
already existed (idempotent no-op), never counted toward `evidence_written`.

## 15. Checkpoint (binding)

Within-run page checkpoint only (`checkpoint_page_token`, used solely to resume a `FAILED` run's own next
attempt within its own bounded retry policy, §35). **No cross-run incremental/delta watermark is authorized in
V1** — every explicit trigger performs a full bounded pull. This is safe (not merely tolerable) because evidence
admission is already idempotent (§9); it is not a CDC or scheduled-synchronization mechanism, and V1 must never
be described as one.

## 16. External record identity (binding)

```
Conceptual identity: (SourceObject, source_record_reference)
```
`source_record_reference` is always exactly the value the administrator-designated `is_external_record_id`
mapping (§13) extracts for that record. If that path is absent, empty, or unparseable for a given record, that
record is `RECORD_REJECTED` (§26) — never a random UUID, never the run ID, never a row/page position, never an
unstable hash of the record's own content.

## 17. Datatype normalization (binding, exact)

```
string      -> as-is (already the evidence model's own native representation)
boolean     -> "true" | "false" (lowercase, exact)
date        -> ISO-8601 date (YYYY-MM-DD)
datetime    -> ISO-8601, timezone-aware (source-naive timestamps rejected as MAPPING_INVALID for that record --
               never silently assumed UTC)
integer     -> canonical base-10 string, no leading zeros, no thousands separators
decimal     -> canonical base-10 string, fixed-point (never scientific notation), no trailing-zero
               normalization performed (the source's own precision is preserved verbatim as text)
enum/code   -> as-is (string)
null        -> "" (§11)
array       -> OUT OF V1 -- record rejected (MAPPING_INVALID) if a mapped field resolves to an array
object      -> OUT OF V1 -- record rejected (MAPPING_INVALID) if a mapped field resolves to a nested object
```
A normalized value exceeding `FieldValueEvidenceORM.observed_representation`'s existing `String(1000)` bound is
**rejected** (`RECORD_REJECTED`, honestly counted) — never silently truncated.

## 18. Append-only evidence (binding, restated verbatim from CDD-022)

`FieldValueEvidence` remains append-only. No connector code path may update, delete, or maintain a "current"
pointer. A changed source observation is always a new, independent, immutable row.

## 19. Current-evidence selection (binding, restated verbatim)

Unchanged: `ORDER BY observed_at DESC, received_at DESC` within the existing evaluation-horizon semantics. No
connector-owned competing selection algorithm is authorized.

## 20. Out-of-order observations (binding, restated)

An older `observed_at` admitted after a newer one never becomes current; both persist immutably; the evaluator's
existing `ORDER BY` is naturally immune to arrival order. No special connector handling is required or
authorized beyond correctly computing each record's own genuine `observed_at`.

## 21. Transaction boundaries (binding, exact)

```
[ NO DB TRANSACTION OPEN ]
        v
Remote HTTPS fetch of exactly one page (urllib.request, bounded timeout/size)
        v
Normalize + validate + tenant-prove every record in that page (in-memory, no DB access)
        v
[ ONE SHORT DB TRANSACTION ]
    for each valid record: FieldValueEvidence.new(...) -> create_or_get_existing(...)
    update the run row's checkpoint/counters
[ COMMIT ]
        v
Next page's remote fetch (only after the previous page's transaction has already committed)
```
No PostgreSQL transaction or lock is ever held across a network wait. Run-row creation (`RUNNING`) and its
terminal update are each their own short transaction.

## 22. Partial-durability contract (binding, restated from CDD-056/058's own precedent)

A later page's network or admission failure never rolls back an earlier page's already-committed evidence. The
run's terminal status is `PARTIAL` with exact, honest counts. Retry is safe because re-fetching an
already-processed page is a pure idempotent no-op at the evidence layer.

## 23. Record-level rejection (binding, exact)

```
one malformed/unmappable/oversized/duplicate-external-id-conflicting record among N valid ones in the same page
    -> that record: RECORD_REJECTED, honestly counted
    -> the other N-1 records in the same page: admitted normally
```
A malformed *page* (the HTTP response itself is not valid JSON, or its top-level shape cannot be paginated at
all) is a **page failure**, never silently degraded into a record-by-record salvage attempt.

## 24. Retry policy (binding, exact)

```
Retryable:      TIMEOUT, NETWORK_ERROR, HTTP 429 (honor Retry-After up to the total run-duration bound, §33),
                HTTP 5xx.
Non-retryable:  HTTP 401/403 (CONNECTOR_AUTHENTICATION_FAILED), other 4xx, MAPPING_INVALID,
                CONNECTOR_RESPONSE_INVALID (malformed JSON), any SSRF policy rejection.
Max attempts:   3 per page, bounded exponential backoff (base 1s, factor 2, jitm not required for V1).
```
No retry ever occurs for an SSRF rejection, an authentication failure, or a governance/validation violation —
these fail the run closed immediately.

## 25. Error taxonomy (binding, exact, closed)

```
CONNECTOR_UNAVAILABLE            DNS failure, connection refused, TLS handshake failure
CONNECTOR_AUTHENTICATION_FAILED  HTTP 401/403
CONNECTOR_TIMEOUT                 request or total-run timeout exceeded
CONNECTOR_RESPONSE_INVALID        malformed JSON, oversized response, non-2xx not otherwise classified
MAPPING_INVALID                   configuration-time or record-time mapping/datatype/record-id failure
RECORD_REJECTED                   a single record fails admission for a reason not covered above
EVIDENCE_ADMISSION_FAILED         a genuine PostgreSQL-level failure during the short admission transaction
```
Mirrors `ProviderFailureKind`'s own precedent almost exactly (§2). No evaluation-related error code belongs
here — evaluation is out of scope (§5/§9 architecture).

## 26. Business-rule/DQ boundary (binding, restated)

The connector contains zero Completeness/Validity/Accuracy/Conformity/Reasonableness/Consistency/Timeliness
logic. Ingestion validation (§17/§23) is never confused with a DQ Finding: a value that fails to parse is a
`RECORD_REJECTED` ingestion outcome; a value that parses successfully to `""` is legitimate admitted evidence,
later eligible for a genuine Completeness Finding through the existing, unmodified evaluator chain.

## 27. Identity resolution / correspondence / semantic mapping boundary (binding, restated)

Ingestion never invokes `EntityResolutionStore`. Ingestion never creates `SourceSystem`, `SourceObject`,
`SourceField`, `SemanticMapping`, or `ComparisonSubjectCorrespondence` — all five must already exist,
independent of this capability (an orthogonal, pre-existing gap: DR discovered zero production creation path
exists for `SemanticMapping`/correspondence either; this document does not close that gap and does not attempt
to, per §5).

## 28. Production Evaluation boundary (binding, restated — DR Option A)

A connector run persists evidence and stops. `POST /api/v1/oqi/evaluate` (CDD-056, byte-unchanged) remains the
sole, separate, explicitly human/API-triggered path to evaluation. No connector code fabricates
`business_process_id`/`business_process_version` to force auto-evaluation. No auto-evaluate option exists in V1.

## 29. Remediation boundary (binding, restated)

`INGESTION SUCCESS != EVALUATION SUCCESS != REMEDIATION AUTHORIZATION`. No connector action invokes OQI5/CDD-058
in any way. `AGENT != AUTHORITY`; `EXECUTION != RESOLUTION` remain unmodified and unaffected.

## 30. Authentication (binding, exact, closed for V1)

```
API_KEY        -- a single configured custom header name + a secret value read from the environment
                  variable named by credential_env_var_name at request time.
BEARER_TOKEN   -- `Authorization: Bearer <secret>`, secret read the same way.
```
OAuth2 (any grant type), Basic auth, and mTLS are explicitly deferred (P3) — not authorized for V1, and their
absence is not a defect.

## 31. Secret model (binding, exact)

`oqi_connector_configurations.credential_env_var_name` stores only the **name** of a server-side environment
variable (e.g. `NOETVA_CONNECTOR_<TENANT-SCOPED-IDENTIFIER>_TOKEN`); `RestConnector` reads the actual secret via
`os.environ` at request time, mirroring `AnthropicMessagesProvider`'s own established pattern exactly. The
secret value MUST NEVER appear in: any database row, any audit event, any API response (including read
responses for the connector's own configuration — §63 of the governing report), any log line, any exception
message, or `oqi_connector_runs.failure_summary`. Secret rotation (changing the environment variable's own
value) never touches any database row and never changes any evidence's identity.

## 32. SSRF policy (binding, exact, no implementation freedom)

Every outbound request the connector issues — the configured `endpoint_url` **and every subsequent
cursor/next-link value** — MUST pass this identical policy, evaluated fresh immediately before each individual
request (not cached from a prior check), because DNS resolution can change between checks:

```
1. Scheme MUST be exactly "https". Any other scheme (http, file, ftp, gopher, ...) -> rejected immediately.
2. The hostname is resolved to its full set of A/AAAA addresses. If ANY resolved address matches a prohibited
   range below, the ENTIRE request is rejected -- not merely the first matching address.
3. Prohibited IPv4 ranges: 127.0.0.0/8 (loopback), 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 (RFC1918
   private), 169.254.0.0/16 (link-local, includes 169.254.169.254 cloud metadata), 0.0.0.0/8, 224.0.0.0/4
   (multicast), 240.0.0.0/4 (reserved).
4. Prohibited IPv6 ranges: ::1/128 (loopback), fc00::/7 (unique local / private equivalent), fe80::/10
   (link-local), ::ffff:0:0/96 IPv4-mapped addresses are resolved to their embedded IPv4 form and checked
   against rule 3, multicast (ff00::/8).
5. This same full validation (scheme + DNS resolution + full-address-set range check) is repeated for the
   INITIAL configured endpoint at configuration-save time (fail closed immediately, before any run ever
   executes) AND again immediately before every individual HTTP request at run time (fail closed, run
   terminates FAILED/CONNECTOR_UNAVAILABLE for that request).
6. HTTP redirect-following is DISABLED. A 3xx response is treated as CONNECTOR_RESPONSE_INVALID, never
   silently followed. (If a future phase requires redirect support, every hop must independently pass this
   identical six-point policy before being followed -- not authorized in V1.)
7. Bounded connect+read timeout (§33) and bounded response size (§33) apply to every request without
   exception.
```
Any implementation gap in this policy discovered during I/VM is `FAIL CLOSED — NO MERGE` (P0/P1, per the
governing report's own STOP conditions).

## 33. Resource bounds (binding, exact V1 defaults)

```
request connect+read timeout     :  30 seconds (mirrors AnthropicMessagesProvider's own _DEFAULT_TIMEOUT_SECONDS)
max response bytes per page      :  2,097,152  (2 MiB; checked via Content-Length where present, and via a hard
                                     streaming-read cap regardless, mirroring supplier_risk_payload_limit_bytes'
                                     own established governed-limit pattern)
max records per page             :  500
max pages per run                :  200
max fields per record             :  200
max field-value length observed   :  1000 characters (already the hard DB bound, §17)
max total run duration            :  600 seconds (10 minutes)
```
All six are connector-configuration-independent, global V1 constants (not per-tenant configurable) unless a
future phase justifies configurability. A run exceeding any bound terminates `FAILED` /
`CONNECTOR_TIMEOUT`/`CONNECTOR_RESPONSE_INVALID` as appropriate, with prior committed pages' evidence intact
(§22).

## 34. TLS policy (binding, restated exact)

HTTPS required in every environment, including local/Docker/CI. Certificate verification is always on
(`urllib.request`'s own default system-CA verification; no code path may disable it). Custom enterprise CA
trust and mTLS are explicitly deferred (P3) — never implemented by weakening default verification to
accommodate a test fixture; the Docker fixture service instead presents a certificate the connector's own
trust store is configured to accept in the test/CI environment specifically (exact mechanism frozen in the
Artifact Authorization's Docker section), never via `verify=False` or an HTTP-only production exception.

## 35. Pagination (binding, exact)

`pagination_style = "CURSOR"` reads the next-page descriptor from a source-supplied field the connector
configuration designates (an opaque continuation token or an absolute next-URL) and treats it as a fresh
externally-supplied URL/token subject to the identical SSRF policy (§32) before every use — trusted status is
never inherited merely because the initial endpoint was already validated. `pagination_style = "NONE"` performs
exactly one request per run. Loop detection: a run tracks the set of previously-used page tokens/URLs within
that run and terminates `CONNECTOR_RESPONSE_INVALID` if an identical token repeats (defends against a
misbehaving or malicious source causing an infinite pagination loop, independent of the `max pages per run`
bound in §33).

## 36. JSON field extraction (binding, exact)

A dotted-path traversal contract (e.g. `product.supplier_id`), no external JSONPath dependency:
```
supported traversal    : object-key and 0-based array-index segments (e.g. "items.0.id")
missing-path semantics : the field is treated as ABSENT (§11) for that record -- never an error, never null
null semantics         : the field is treated as PRESENT-NULL (§11) -- observed_representation=""
invalid-path semantics : a path segment that cannot be traversed (e.g. indexing into a string) is
                         MAPPING_INVALID for that specific field on that specific record -> RECORD_REJECTED,
                         never a page-wide failure
array/object result    : OUT OF V1, MAPPING_INVALID for that field (§17)
```

## 37. Duplicate accounting (binding, exact)

`duplicate_records` counts every record whose computed 4-tuple identity already exists in
`field_value_evidence` (an idempotent no-op via `create_or_get_existing`). `evidence_written` counts only
genuinely new rows. `accepted_records` counts every record that passed validation/tenant-proof and reached
admission, whether it turned out to be a fresh write or a duplicate no-op — `accepted_records = evidence_written
+ duplicate_records` always holds, an invariant the test suite must assert directly.

## 38. Tenant authority (binding, restated exact)

`TrustedPrincipal.tenant_id` is the sole authoritative tenant source for every connector action (configure,
read, run, disable, read-run-history). No request schema accepts an authoritative `tenant_id` field
(`ConfigDict(extra="forbid")`, per every prior OQI precedent). No value inside a fetched `ConnectorRecord` is
ever read as tenant-authoritative. Every configuration/mapping/run lookup is tenant-scoped at the query itself
(`WHERE tenant_id = :tenant_id AND ...`), never merely tenant-checked after an untenanted lookup.

## 39. SourceField tenant-authority proof — P1, mandatory (binding, exact)

Because `source_fields`/`field_value_evidence` deliberately carry no `tenant_id` column (§2/CDD-019/CDD-022),
**every** field mapping's `source_field_id` MUST be proven tenant-owned via the exact two-hop join
`FieldValueEvidenceRepositoryImpl.get_by_source_field` already establishes as correct precedent —
`source_field_id → source_fields.source_object_id → source_objects.tenant_id`, compared equal to
`TrustedPrincipal.tenant_id` — **at mapping-configuration-save time AND again immediately before every run's own
evidence admission for that mapping** (never trusting a prior check to still hold, mirroring the SSRF
double-check discipline in §32). A mapping whose `source_field_id` fails this proof is rejected
(`MAPPING_INVALID`) at configuration time and never reaches a run at all; if a run somehow observes a stale
mapping whose target has since become cross-tenant (e.g. through direct data corruption), that record is
`RECORD_REJECTED`, never admitted. This is the single highest-priority control this capability introduces and is
non-negotiable (P1; any gap is FAIL CLOSED — NO MERGE).

## 40. Structural tenant isolation — P1, mandatory (binding, exact)

Every new table is tenant-owned from its first migration, using the exact composite tenant-qualified FK
technique `fk_source_objects_tenant_source_system` already proves correct (never the single-column-FK mistake
OQI4/OQI6 later had to retroactively correct):
```
oqi_connector_configurations(tenant_id, connector_id)             UNIQUE  (composite-FK target)
    -> fk_..._tenant_source_system:  (tenant_id, source_system_id) -> source_systems(tenant_id, source_system_id)

oqi_connector_field_mappings(tenant_id, mapping_id)                UNIQUE  (not itself an FK target)
    -> fk_..._tenant_connector:      (tenant_id, connector_id) -> oqi_connector_configurations(tenant_id, connector_id)
    -- source_field_id has NO structural FK-level tenant proof (source_fields itself carries no tenant_id,
       §39) -- the composite FK here proves the MAPPING row's own tenant matches its owning CONNECTOR's
       tenant; source_field_id's own tenant ownership is proven exclusively at the application layer (§39),
       and this is explicitly documented here as the one honest limit of DB-structural enforcement this
       schema can support without modifying source_fields (out of scope, §5).

oqi_connector_runs(tenant_id, run_id)                              UNIQUE  (not itself an FK target)
    -> fk_..._tenant_connector:      (tenant_id, connector_id) -> oqi_connector_configurations(tenant_id, connector_id)
```
A direct, malicious PostgreSQL `INSERT` attempting to create a mapping or run row whose `tenant_id` differs from
its referenced connector's own `tenant_id` fails with a genuine `IntegrityError` — this must be proven directly
against real PostgreSQL (`pg_constraint` introspection), never merely asserted at the service layer, per the
proof standard CDD-055 §26 already established ("mocks do not count... a service-layer exception alone does not
count as structural proof").

## 41. Authorization scopes (binding, exact)

```
oqi-connector:read         GET  configuration list/detail, run history/detail
oqi-connector:configure    POST/PATCH configuration, field mappings; disable
oqi-connector:run          POST run-trigger
```
Mirrors the existing `resource:action` convention exactly (`oqi-remediation:prepare`,
`oqi-reference-evidence:configure`, etc.). No single super-admin scope. `oqi-connector:run` never implies
`oqi-connector:configure` or vice versa, exactly as no two existing OQI scopes ever imply one another.

## 42. Audit (binding, restated — reuse only)

Reuses `SecurityAuditService` exactly as CDD-058 established (`_record_success`/`_record_denied` pattern).
Operations: `CONFIGURE_CONNECTOR`, `TRIGGER_CONNECTOR_RUN`, `CONNECTOR_RUN_SUCCEEDED`,
`CONNECTOR_RUN_PARTIALLY_SUCCEEDED`, `CONNECTOR_RUN_FAILED`, `DISABLE_CONNECTOR`. Category `ADMISSION` for
run-outcome events (they represent evidence admission activity); category `AUTHORIZATION` for
configure/disable/scope-denial events (mirroring the existing category taxonomy exactly, §41 of the DR
report). No new observability subsystem. No credential ever appears in an audit row (§31).

## 43. Frontend (binding)

Zero frontend paths authorized. Backend-only V1.

## 44. Database impact (binding, exact)

Exactly 3 new tables (`oqi_connector_configurations`, `oqi_connector_field_mappings`, `oqi_connector_runs`),
one new migration (`0045_oqi_connector_ingestion`, revision string 28 characters, safe under the 32-character
`alembic_version.version_num` bound — verified directly, per the Artifact Authorization's own enum/revision
verification section). Zero modification to any of the 123 existing tables. Post-migration table count:
**126**.

## 45. Docker/runtime impact (binding)

One new Docker-Compose service — a deterministic, stdlib-only HTTP fixture server — added under a test/CI
profile only, never part of the production `backend`/`frontend` service graph, never started by
`docker-entrypoint.sh`, never reachable from the production network path. Exact topology frozen in the
Artifact Authorization.

## 46. Reliance replay-sensitivity (binding — reaffirmed unchanged from DR)

Classification **B** (blocker before automated/connector-driven *remediation*) is **not triggered** by this
phase: V1 never auto-evaluates and never auto-remediates; evaluation and remediation both remain separate,
unmodified, explicitly human/API-triggered actions. The register item is carried forward unchanged, not removed.

## 47. OQI2/OQI3/OQI4→OQI6 pointer classifications (binding — reaffirmed unchanged from DR)

Re-confirmed directly: none of the four registered P2 items sit on any table or code path this capability reads
or writes. Not exposed, not newly exploitable. Carried forward unchanged, unfixed.

## 48. Concurrency matrix (binding, mandatory for I/VM)

```
C1  Two concurrent runs of the SAME connector: both complete; evidence converges idempotently; run ledger
    shows two independent, honestly-accounted run rows (no cross-run corruption of counts).
C2  Two concurrent runs of DIFFERENT connectors, same tenant: independent, no unnecessary serialization.
C3  Two concurrent runs, different tenants: independent, zero cross-tenant convergence, verified via direct
    PostgreSQL query.
C4  Concurrent configuration-mapping writes for the same connector: no partial/torn mapping set observable by
    a concurrently-running connector run.
C5  A run in progress against a connector that is concurrently disabled: the in-flight run completes honestly
    (its own already-open transactions/pages finish per §22); no new run may start once disabled.
```

## 49. Real connector boundary (restated, binding)

The connector is transport/admission-only. It is not, and must never become, a second evaluation engine, a
second identity-resolution engine, a second correspondence-authoring mechanism, or a remediation-authority path.

## 50. Response contracts (binding, exact)

```json
// POST /run response
{
  "run_id": "UUID",
  "correlation_id": "UUID",
  "status": "SUCCEEDED | PARTIAL | FAILED",
  "fetched_records": "int",
  "accepted_records": "int",
  "rejected_records": "int",
  "duplicate_records": "int",
  "evidence_written": "int",
  "started_on": "datetime",
  "completed_on": "datetime",
  "failure_kind": "string | null"
}
```
Never includes `evaluation_status` — evaluation is not invoked (§28). Never includes any secret material.

```json
// connector configuration read response
{
  "connector_id": "UUID",
  "tenant_id": "implicit via TrustedPrincipal, never echoed as request-controllable",
  "source_system_id": "UUID",
  "display_name": "string",
  "connector_type": "GENERIC_REST",
  "endpoint_url": "string",
  "auth_mechanism": "API_KEY | BEARER_TOKEN",
  "status": "ACTIVE | DISABLED"
}
```
`credential_env_var_name` is **redacted from every ordinary read response** (returned only as a fixed
placeholder, e.g. `"***"`) — even the environment-variable *name* is treated as sensitive enough to avoid
casual disclosure, a stricter policy than DR's own open question in §63 of the DR report, adopted here to
close that question definitively rather than leave it to I's own discretion.

## 51. Test obligations (minimum set, binding — full crown designs restated in the governing G report)

```
Domain contract (EnterpriseConnector Protocol, ConnectorRecord construction/validation).
SSRF policy (every prohibited range, IPv4 and IPv6, redirect-disabled, next-link re-validation, DNS-rebinding
    resistance via fresh-resolution-per-request).
Authentication (both mechanisms, credential-absence-from-everywhere proof).
Pagination (cursor style, loop detection, bounds).
Retry (every retryable/non-retryable classification, backoff, Retry-After honoring within the run bound).
Mapping validation (tenant-proof at save time and at run time, external-record-id uniqueness, datatype
    normalization matrix, malformed-path/record rejection).
Idempotence/replay (real PostgreSQL).
Real-PostgreSQL structural tenant-isolation attacks (direct SQL, per §40).
API authority (scope matrix, tenant-scoped lookups, cross-tenant attack matrix per §45 of the governing
    report).
Real-network integration against the Docker fixture service (positive/multi-source/update/replay/
    out-of-order/malformed-record/network-failure/scale crowns).
Fresh, no-cache Docker crown proving the exact production connector code path over a real, separate network
    boundary.
```

## 52. Frozen verification matrix (binding — the existing crown regressions this phase must never break)

```
backend/app/tests/test_source_field_persistence.py
backend/app/tests/test_source_field_persistence_postgres.py
backend/app/tests/test_oqi_quality_postgres.py                 (FieldValueEvidence identity/idempotence crown)
backend/app/tests/test_oqi_cross_source_postgres.py
backend/app/tests/test_runtime_architecture.py
```
All must remain fully green, unmodified in their own existing assertions (mechanical table-count-literal
bumps in the 8 named files per the Artifact Authorization's §6 are the sole authorized exception, exact and
narrow).

## 53. Full backend regression, static quality, frontend regression, fresh Docker (binding, restated)

Identical discipline to every prior phase: full `pytest app/tests` with `0` unexplained failures (the same
pre-existing environmental failure class, already independently baseline-adjudicated across every prior phase,
remains separately classified, never silently re-attributed to this candidate); `black`/`isort`/`ruff`/
whole-package `mypy`; frontend `npm test`/`lint`/`typecheck`/`build` (frontend untouched, so zero new frontend
failures are possible by construction); fresh `--no-cache` Docker proof of the complete verification matrix
inside a genuinely fresh runtime, distinct project namespace, structural byte-binding to the exact candidate,
plus the new deterministic HTTP fixture service genuinely reachable only over the Docker network boundary.

```
FORMATTER-ONLY != AUTOMATICALLY AUTHORIZED
```

## 54. Deferred register (binding, restated and extended)

```
P2 — OQI2 latest_evaluation_id structural tenant pointer (reconfirmed: not on this capability's path)
P2 — OQI2 load_participant_observations lacks independent tenant filter (reconfirmed: not on this
     capability's path)
P2 — OQI3 latest_evaluation_id structural tenant pointer (reconfirmed: not on this capability's path)
P2 — OQI4->OQI6 considered_current_impact_id structural weakness (reconfirmed: not on this capability's path)
B  — Reliance replay sensitivity before automated/connector-driven remediation (reconfirmed: not triggered by
     this phase, §46)
P3 — frontend Docker internal-loopback healthcheck discrepancy (untouched)
P3 — local demo Keycloak realm missing oqi-remediation:prepare scope registration (-> OQI-H7; distinct from
     any NEW connector scope registration this phase's own I may separately require for
     oqi-connector:read/configure/run in the SAME local demo realm -- these are two independent registration
     needs, never conflated)
P3 — record-level tombstone/deletion semantics unsupported, explicitly deferred (source disappearance is never
     interpreted as deletion in V1)
P3 — connector configuration versioning deferred (no lifecycle_state/governance_status/version_number on
     oqi_connector_configurations)
P3 — cross-run incremental/delta watermark deferred (§15)
P3 — OAuth2/Basic-auth/mTLS/custom-CA deferred (§30/§34)
NEW DISCOVERY (carried from DR, unfixed) — ComparisonSubjectCorrespondence creation has zero production
     callers; orthogonal to this capability, not fixed here
NEW DISCOVERY (carried from DR, unfixed) — SemanticMapping creation has zero production callers; orthogonal to
     this capability, not fixed here
CAPABILITY GAP — real production LLM agent reasoning / user-selectable governed model (unchanged)
CAPABILITY GAP — Level 3 real-vendor (SAP/Snowflake/Databricks/Fabric) connector certification (explicitly out
     of scope for this phase)
CAPABILITY GAP — zero genuine production enterprise connectors (NOT removed by this document; removable only
     upon a future connector VM's own independent, successful closure)
```

## 55. Governance byte-integrity

This document and its own paired Artifact Authorization are the two new governance artifacts this phase
publishes. CDD-019, CDD-022, CDD-039, CDD-040, CDD-041, CDD-056, CDD-058, and their respective Artifact
Authorizations are independently re-hashed immediately before this document's own publication and confirmed
byte-identical to their prior published values; none is modified by this document. `architecture/INDEX.md`
independently confirmed to list no CDD numbered 035 or higher at all (the entire OQI series through CDD-058 is,
and always has been, outside that registry's scope) — this document follows that same established precedent
and requires no index update.

## 56. Authorization

This document is approved and published as a standalone governance artifact, building on CDD-019/022/039-041/
056/058 without modifying any of them. Implementation against the paired Artifact Authorization's exact path
set may proceed under `Real-Enterprise-Ingestion-I`.
