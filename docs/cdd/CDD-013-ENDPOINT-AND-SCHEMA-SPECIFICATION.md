# CDD-013 — Endpoint and Schema Specification

Version: 1.0 DRAFT

Status: APPROVED — GOVERNED BY PAS-001 v1.0

Base path: `/api/v1/supplier-risk`

## Endpoints

| Method and path | Purpose | Success | Idempotency/concurrency |
|---|---|---|---|
| `POST /assessments` | Submit assessment through CDD-010/011/012. | `202` with logical/attempt/execution/correlation identifiers and status URI. | Required `Idempotency-Key`; same tenant/key/body returns existing `202/200`; different body `409`. |
| `GET /executions/{logical_execution_id}` | Current logical execution plus attempt summary. | `200` | Read-only; ETag from projection revision. |
| `GET /executions/{logical_execution_id}/attempts` | Paginated immutable attempts. | `200` | Cursor pagination, stable oldest-to-newest ordering. |
| `GET /executions/{logical_execution_id}/attempts/{execution_id}/stages` | Ordered stage progress and safe failure. | `200` | Read-only; never returns handoff payload. |
| `GET /executions/{logical_execution_id}/result` | Governed recommendation and permitted references. | `200` when terminal result exists; provisional `202` while active. | ETag; no recommendation derivation. |
| `POST /executions/{logical_execution_id}/retry` | New request/attempt after eligible failure. | `202` | New required `Idempotency-Key`; duplicate returns same attempt. |
| `POST /executions/{logical_execution_id}/replay` | Privileged replay from verified checkpoint. | `202` | Recovery role/scope, reason and authorization reference required; atomic duplicate suppression. |

## Submission schema

`SupplierRiskAssessmentRequest` contains the caller-supplied fields already defined by CIM-001
`SupplierRiskRequest`: supplier names; source-object and candidate identifiers; semantic terms and
candidates; context, material, facility/region and effective-time identifiers; SourceObservations;
supplier eligibility; governed confidence inputs; policy identifiers/versions/rule; optional
Acceptance Evidence reference; governance conditions; verified conditions; and exceptional-policy
indicator. JSON uses UUID strings, RFC 3339 UTC timestamps, closed enums, finite `[0,1]` scores,
non-empty trimmed names/references, unique arrays, and PAS-001 size/cardinality limits.

The body contains no principal, tenant, roles, scopes, trust source, authorization decision,
credentials, token, or AuthorityContext. `request_identifier`, `correlation_identifier`, and
`session_identifier` are protocol metadata, not business payload fields; PAS-001 decides whether
the caller supplies or the boundary generates each value.

## Response schemas

`SubmissionResponse`: `api_version`, `protocol_version`, `request_identifier`,
`correlation_identifier`, `logical_execution_identifier`, `execution_identifier`, `attempt_number`,
`invocation_status`, `execution_state`, `status_url`, `replayed`.

`ExecutionResponse`: identifiers, current attempt, attempt count, ESM state, admitted/completed UTC
timestamps, safe terminal classification (`SUCCESS`, `BUSINESS_GATED`, `BUSINESS_REJECTED`,
`TECHNICAL_FAILURE`), safe diagnostic code, and links. Classification transports persisted gate,
result, and ESM data; it is never inferred from recommendation text.

`StageResponse`: stage name from the closed ERM/SRM/ASM/KRM/DRM/GRM order, ordinal, checkpoint
status, timestamps, safe failure code, and produced-record reference identifiers. No input/output
handoff content.

`GovernedResultResponse`: recommendation, governance standing, actionability, conditions-verified,
safe diagnostic, produced record references by role, permitted evidence/provenance references,
policy identifier/version/evaluated rule, supporting evidence references, completion timestamp.

`RetryRequest`: `reason`, optional expected current attempt/revision. It never includes a checkpoint.

`ReplayRequest`: `reason`, `authorization_reference`, optional requested checkpoint stage, expected
attempt/revision. The server verifies the requested checkpoint; caller choice cannot bypass stages.

`ProblemResponse`: `type`, `title`, `status`, stable `code`, safe `detail`, `request_identifier`,
`correlation_identifier`, optional field errors and `retryable`. It excludes stack traces, SQL,
payload, raw evidence, tokens, and authority details.

## Closed transport enums

- Invocation: `ACCEPTED`, `REJECTED`.
- Execution: exact ESM `Accepted`, `Executing`, `Completed`, `Failed` values.
- Governance standing: exact GRM `APPROVED`, `CONDITIONALLY_APPROVED`, `PENDING_REVIEW`, `REJECTED`,
  `INDETERMINATE`.
- Recommendation: exact CIM closed vocabulary.
- Safe diagnostic codes: existing `DiagnosticCode` values plus protocol/auth/resource/rate codes
  defined by PAS-001; API codes cannot become business outcomes.

## HTTP mapping proposed for PAS-001 approval

| Condition | HTTP |
|---|---:|
| New or identical accepted submission/retry/replay | 202 |
| Successful read | 200 |
| Schema/protocol validation | 400 or 422, one choice frozen by PAS-001 |
| Missing/invalid authentication | 401 |
| Authenticated but unauthorized | 403 |
| Tenant-safe unknown/concealed resource | 404 |
| Idempotency fingerprint or optimistic revision conflict | 409 |
| Unsupported API/media version | 406/415, exact mapping frozen by PAS-001 |
| Payload too large | 413 |
| Rate limit | 429 with bounded retry metadata |
| Safe unexpected technical error | 500/503 according to retryability |

## Pagination and compatibility

Attempt lists use opaque cursor plus `limit`; default/max limits require PAS-001. Cursors bind to
tenant, resource, sort order, and API version and carry no business meaning. API v1 accepts only its
published schema. No silent field coercion, downgrade, default-to-latest, or substitution of caller
claims for trusted metadata is permitted. Additive optional response fields are compatible; enum,
required-field, meaning, idempotency, or authorization changes require a new API version.
