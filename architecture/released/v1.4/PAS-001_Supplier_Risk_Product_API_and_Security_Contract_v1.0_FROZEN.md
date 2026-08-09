# PAS-001 — Supplier Risk Product API and Security Contract

Version: 1.0  
Status: FROZEN  
Owner: ECOM Platform Enterprise (`00000000-0000-0000-0000-000000000004`)  
Approval: CDD-013 bounded governance decision

## Boundary

PAS-001 governs only `/api/v1/supplier-risk`. It transports existing CDD-010/011/012 outcomes and
does not create business semantics, canonical entities, a second orchestration path, or executable
sourcing actions.

## Protocol

Commands submit an assessment, retry an eligible failed execution, or request authorized replay.
Reads return tenant-scoped logical execution, attempts, stages, safe failures, governed final
recommendation, and permitted evidence/provenance/policy references. The stable identifiers are
request, correlation, logical execution, execution attempt, and produced-record references.

Submission requires `Idempotency-Key`; duplicate behavior is inherited from CDD-010/012. API
version `1` is explicit. Unsupported or conflicting versions reject deterministically; there is no
silent downgrade or semantic coercion. List resources use bounded cursor pagination.

## Authentication and AuthorityContext

The trusted application boundary validates an OAuth 2.0 bearer access token under IDP-001 before
authorization, runtime admission, or execution creation. `X-User`, request payload identity,
tenant, scope, role, or AuthorityContext claims are untrusted and cannot override validated
identity evidence. The boundary constructs the minimum immutable AuthorityContext from validated
principal, tenant, roles/scopes, authorization reference, trusted issuer, request/correlation
identifiers, and server timestamps. Raw tokens and complete claim sets never propagate.

## Authorization

| Operation | Required scope | Additional rule |
|---|---|---|
| submit | `supplier-risk:submit` | tenant from token must match resource tenant |
| status/result/reference read | `supplier-risk:read` | tenant-scoped non-disclosure |
| retry | `supplier-risk:retry` | CDD-012 retry eligibility |
| replay | `execution:replay` | `EXECUTION_RECOVERY_OPERATOR`, reason, authorization reference |

Ordinary users cannot replay. Authorization applies equally to commands and reads. Cross-tenant
lookups disclose no resource existence.

## Errors and status

Responses use stable `{code, message, correlation_id, retryable}` errors. Safe categories are
validation, authentication, authorization, not-found/non-disclosure, conflict, throttled,
unsupported-version, business-gated, and technical-failure. Stack traces, tokens, claims,
credentials, database details, protected handoffs, and sensitive evidence are prohibited.

HTTP mapping: malformed request `400/422`; missing/invalid bearer token `401`; authenticated but
unauthorized `403`; tenant-safe absent resource `404`; idempotency/concurrency conflict `409`;
payload too large `413`; throttled `429`; unsupported API version `400`; unexpected technical
failure `500/503`. Completed business-gated termination remains a successful execution result.

## Abuse protection and audit

Requests have server-configured payload and rate limits. Every security-relevant admission,
denial, protected disclosure, retry/replay, version conflict, idempotency conflict, throttling,
payload-limit event, and verifier/configuration failure writes an `API_SECURITY_AUDIT_EVENT` under
PMM-001 v1.2. Security mutations fail closed when audit insertion fails. Audit data is append-only,
tenant-scoped when identity is known, retained seven years, and protected by legal hold.

## Compatibility

The contract is provider-neutral and compatible with conforming OIDC providers or trusted
gateways. Authentication settings are deployment-controlled. Existing CDD-010 invocations remain
unchanged; this external API always uses trusted metadata and does not reinterpret legacy calls.

