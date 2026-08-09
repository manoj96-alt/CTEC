# CDD-013 — Security and Authorization Assessment

Version: 1.0 DRAFT

Status: RESOLVED — PAS-001 v1.0 / IDP-001 v1.0

The prior P0 findings are resolved by PAS-001 v1.0 and IDP-001 v1.0; RFC-014 v1.3, PMM-001 v1.2,
and Physical Model v1.5 authorize durable rejected-request audit evidence.

## Trust boundary

The Product Access boundary authenticates a credential using an approved trusted verifier. Only
the verifier result—not request JSON or arbitrary headers—may supply principal, organization,
roles/scopes, authorization decision/reference, trust source, delegation, issuance, and expiry.
The boundary binds those values to request/correlation identifiers and creates the immutable
AuthorityContext passed separately to the CDD-010 runtime.

CDD-013 stores no credential, token, secret, signing key, or complete authentication material.

## Proposed authorization matrix requiring PAS-001 approval

| Operation | Minimum authority |
|---|---|
| Submit assessment | Tenant-bound supplier-risk submit scope. |
| Read execution/attempt/stage | Tenant-bound execution read scope. |
| Read governed result/references | Tenant-bound result read scope plus disclosure policy. |
| Retry failed attempt | Tenant-bound retry scope and CDD-012 eligibility. |
| Replay from checkpoint | Exact RSP-001 `EXECUTION_RECOVERY_OPERATOR` + `execution:replay`. |

PAS-001 must freeze the ordinary scope identifiers and whether retry is ordinary or privileged.
The API must authorize before resource lookup and use a tenant-concealing response where required.

## Tenant isolation

Every command and query carries the authenticated organization identifier to the application
service. Repository predicates include tenant and logical execution/attempt identifiers in the
same query. IDs alone confer no authority. Cursors, idempotency keys, cache entries, ETags, logs,
metrics, and audit events are tenant-bound.

## Disclosure and redaction

Allowed by default: stable identifiers; stage names/status; safe diagnostics; recommendation,
standing and actionability; produced-record identifiers; explicitly permitted evidence,
provenance, and policy references.

Denied by default: protected handoff content; raw evidence; narrative explanations unless PAS-001
expressly permits them; confidence internals not in the external contract; full AuthorityContext;
principal roles/scopes; authorization/delegation detail; hashes/fingerprints; SQL; stack traces;
credentials, tokens, or secrets.

## Authentication failures

Missing, malformed, expired, wrong-audience, wrong-issuer, unverifiable, conflicting, or replayed
identity material fails before invocation. Caller-supplied tenant/principal/role/scope fields are
ignored as authority and rejected when contractually prohibited. Unsupported control-metadata
versions fail deterministically; no downgrade or default authority.

## Abuse controls

PAS-001 must freeze request-body maximum, collection cardinalities, per-tenant/principal command
and read limits, burst policy, retry response, and whether enforcement is application-local or
delegated to an approved trusted gateway. Limits apply before expensive parsing/execution where
possible. Idempotent replay must not become a bypass.

## Audit

Each mutating request produces an allowlisted event containing time, tenant, pseudonymous/stable
principal reference, action, resource/request/correlation identifiers, decision, authorization
reference, safe result code, and API/protocol versions. It excludes payload, raw evidence, full
authority, token, and secret. RSP-001 replay evidence remains separately persisted. PAS-001 must
state whether safe platform logging satisfies rejected/pre-admission audit or a governed durable
record is required; the latter would reopen Physical Model/PMM scope.

## Security gate

No authentication mechanism or header convention is selected by this package. Existing
`X-User` logging is not an authentication boundary and must not authorize CDD-013. Implementation
is blocked until PAS-001 identifies the trusted verifier owner and freezes the matrix, disclosure,
limits, and audit decision above.
