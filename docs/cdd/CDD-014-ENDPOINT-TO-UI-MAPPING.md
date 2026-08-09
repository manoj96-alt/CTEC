# CDD-014 — CDD-013 Endpoint-to-UI Mapping

Version: 1.0

| UI operation | Frozen endpoint | Request construction | View mapping / gap |
|---|---|---|---|
| Submit | `POST /api/v1/supplier-risk/assessments` | UUID request/correlation/session; Idempotency-Key equals request ID; closed supplier-risk body required | Response IDs → overview; body is currently untyped (P0) |
| Execution | `GET /executions/{logical_execution_id}` | Bearer token; URL ID only | State/timestamps/result fields; terminal classification absent (P0) |
| Attempts | `GET /executions/{id}/attempts?cursor&limit` | Opaque cursor; bounded limit | Immutable attempt history and next cursor |
| Stages | `GET /executions/{logical}/attempts/{attempt}/stages` | IDs from server | Ordered timeline, safe failure, references |
| Result | `GET /executions/{logical}/result` | Logical ID | `202` pending; result fields lack conditions/evidence/policy (P0) |
| Retry | `POST /executions/{logical}/retry` | New request/correlation IDs, matching key, reason | Existing logical ID plus returned new attempt; eligibility absent (P0) |
| Replay | `POST /executions/{logical}/replay` | New IDs/key and reason; never checkpoint payload | Server checkpoint options and authorization reference not exposed (P0) |
| Work queue | None | — | P0: required paginated tenant-safe endpoint absent |

## Client behavior

- One client boundary owns base URL, explicit API version, bearer attachment, safe error decoding,
  AbortController cancellation, and schema validation.
- No identity, tenant, role, scope, or AuthorityContext enters request bodies.
- Mutations retain their request ID and canonical body fingerprint until a definitive response.
- Reads refetch after mutations and on browser visibility return. Active execution polling starts at
  five seconds, backs off to thirty seconds, pauses while hidden/offline, and stops at terminal state
  or authentication failure. Final values are governed configuration subject to PAS limits.
- Stale responses are ignored using request sequence/abort state; server timestamps/revisions win.
- Unsupported version, conflict, rate, and availability codes map to safe UI states, never business
  outcomes.
- The repository has no governed OpenAPI client-generation facility. After contract remediation,
  either commit a verified OpenAPI snapshot and generated client or implement a narrow client with
  contract tests against backend OpenAPI; governance must authorize the selected paths/dependency.
