# CDD-014 — CDD-013 Endpoint-to-UI Mapping

Version: 1.0

| UI operation | Frozen endpoint | Request construction | View mapping / gap |
|---|---|---|---|
| Submit | `POST /api/v1/supplier-risk/assessments` | UUID request/correlation/session; Idempotency-Key equals request ID; PAS-001 v1.1 closed body | Response IDs → overview |
| Execution | `GET /executions/{logical_execution_id}` | Bearer token; URL ID only | Explicit execution and terminal classification |
| Attempts | `GET /executions/{id}/attempts?cursor&limit` | Opaque cursor; bounded limit | Immutable attempt history and next cursor |
| Stages | `GET /executions/{logical}/attempts/{attempt}/stages` | IDs from server | Ordered timeline, safe failure, references |
| Result | `GET /executions/{logical}/result` | Logical ID | `202` pending; explicit conditions, references and policy trace when terminal |
| Retry eligibility | `GET /executions/{logical}/retry-eligibility` | Logical ID | CDD-012-owned eligibility and revision |
| Retry | `POST /executions/{logical}/retry` | New IDs/key, reason and expected revision | Existing logical ID plus returned attempt |
| Replay options | `GET /executions/{logical}/replay-options` | Logical ID | Server-authenticated option references only |
| Replay | `POST /executions/{logical}/replay` | New IDs/key, option, revision and reason | Never checkpoint payload |
| Work queue | `GET /executions?cursor&limit` | Tenant from trusted token only | Bounded stable pagination and safe summaries |

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
