# CDD-036 — Governed Human Approval

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-035 (FROZEN, Gate R — Sec31: "Gate S remains the sole future owner of
approval semantics, downstream of Gate R's own eligibility check" — this CDD is the first to define,
not merely forward-declare, Gate S; Gate R remains byte-unchanged and unreopened, Sec20 of this
document), CDD-013 (FROZEN, `SecurityAuditService`/`ApiSecurityAuditRepository` — reused unmodified,
Sec18), CDD-028 (FROZEN, Gate M — the sole prior in-repository precedent for a persisted
propose/decide lifecycle; its shape/conventions are reused, its concrete proposal model is not,
Sec3)

Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via a single combined
discovery-decide-govern phase (Gate S0), per the compressed small-gate process: exhaustive
repository discovery of existing approval/tenant/concurrency/audit precedent, 20 explicit
Product Owner architecture decisions (S0-D1 through S0-D20), and this freeze-ready text —
pending Product Owner publication authorization (Gate S1).

## 1. Purpose

Prove that CTEC can require and durably enforce independent human authorization before a specific,
tenant-scoped, bounded consequential action is permitted to execute — and that the exact action
approved is the exact action executed, exactly once, under fail-closed semantics for every
tenant, authority, staleness, and replay condition.

## 2. Capability claim (exact, binding)

CTEC can prove that a specific, tenant-scoped, digest-bound consequential action cannot durably
execute until a distinct, independently-authorized human principal — never the requester —
explicitly approves that exact action under the correct tenant context, with fail-closed behavior
on any mismatch, tenant violation, self-approval attempt, missing authority, or replay attempt,
and durable, tamper-evident provenance for every request, decision, and execution.

No broader claim (consequential Gate R execution, external provider approval, MCP-governed
approval, multi-stage/quorum approval, agent-initiated approval decisions, or any frontend) is
authorized by this CDD.

## 3. Why this CDD requires its own governance

No prior CDD defines a tenant-isolated, replay-safe, digest-bound human-approval primitive.
CDD-035 explicitly declines to (Sec31) and explicitly reserves this ground for Gate S. CDD-028's
proposal-governance lifecycle (Gate M) is domain-specific (ontology only), carries no tenant
dimension at all, and enforces no approver-authority distinction or self-approval prohibition —
it is informative precedent for shape and convention, not a reusable general primitive.

## 4. Definitions

- **Approval request**: one durable record binding a tenant, a requester, a proposed action, and
  its immutable digest, awaiting a human decision.
- **Decision**: the terminal APPROVED or REJECTED transition of an approval request, made by a
  human principal distinct from the requester.
- **Consequential action (v1)**: `gate-s-governed-note-write` — a single, bounded, durable text
  write, and the only action type this CDD authorizes.
- **Execution**: the one-time, approval-gated, durable performance of the approved consequential
  action.
- **Consumption**: the durable marking of an approval request as having authorized exactly one
  execution; a consumed approval can never authorize a second execution.

## 5. In scope (Gate S v1)

`GateSApprovalService` (request, approve, reject, execute); `gate_s_approval_requests` and
`gate_s_governed_notes` persistence; two new Keycloak scopes (`governed-approval:request`,
`governed-approval:decide`); a narrow 5-endpoint FastAPI router; digest-based immutable action
binding; one-time consumption; row-lock concurrency; provenance via the existing, unmodified
security-audit mechanism.

## 6. Out of scope (binding)

Any modification to Gate R (`governed_tool_executor.py`, its test file, CDD-035, or its Artifact
Authorization); any modification to Gate Q (`mcp_client.py`, `mcp_connector_catalog.py`); any
modification to the six-stage cognitive runtime (`backend/app/runtime/**`,
`backend/app/integration/adapters/**`); any modification to `dependency_container.py`; a second
consequential action type; multi-stage, quorum, or delegated approval; approval expiry or
cancellation; a `list` endpoint; any frontend file; agent, planner, LLM, or autonomous-approval
code of any kind; MCP-triggered approval; real external provider integration.

## 7. Architecture (binding)

```
Requester (TrustedPrincipal, governed-approval:request)
        |
        v
Create approval request (tenant, action_id, note_text, digest, PENDING)
        |
        v
Approver (TrustedPrincipal, governed-approval:decide, != requester, same tenant)
        |
        +---- reject ----> REJECTED (terminal)
        |
        +---- approve
                |
                v
             APPROVED (terminal)
                |
                v
Requester re-submits note_text for execution (governed-approval:request)
        |
        v
Recompute digest; compare to stored digest
        |
        +---- mismatch ----> APPROVAL_ACTION_MISMATCH, zero write
        |
        +---- match
                |
                v
        Row-locked check: APPROVED, same tenant, not yet consumed
                |
                v
        Durable write: gate_s_governed_notes (one row)
                |
                v
        Mark consumed (same transaction)
                |
                v
        Record provenance (existing SecurityAuditService/ApiSecurityAuditRepository)
                |
                v
        Return governed result
```

No write to `gate_s_governed_notes` may occur outside this exact path. No tool/action
implementation may execute before tenant match, authority check, status check, digest match, and
consumption check all succeed.

## 8. Identity and tenant authority (binding)

The existing `TrustedPrincipal` (principal_id, tenant_id, scopes, roles, issuer, issued_at,
expires_at) is the sole identity/tenant authority, reused unchanged. No new identity abstraction
is introduced.

## 9. Approval authority (binding, frozen)

Two new scopes, both OPTIONAL, NOT DEFAULT:

```
governed-approval:request   DEFINED=YES  OPTIONAL=YES  DEFAULT=NO
governed-approval:decide    DEFINED=YES  OPTIONAL=YES  DEFAULT=NO
```

`governed-approval:request` authorizes creating an approval request and executing an approved,
matching one. `governed-approval:decide` authorizes approving or rejecting. Neither scope may ever
be satisfied by `tool-execution:execute`, `tool-execution:approve` (does not exist), or any other
existing scope. Discovery authority never implies approval authority; request authority never
implies decision authority.

Keycloak realm change (exact, for S1):
- Add two new `clientScopes` entries:
  ```json
  {
    "name": "governed-approval:request",
    "protocol": "openid-connect",
    "description": "CDD-036 canonical scope -- Governed Human Approval request/execute authority (not granted to the primary demo persona).",
    "attributes": {
      "include.in.token.scope": "true",
      "display.on.consent.screen": "false"
    }
  }
  ```
  ```json
  {
    "name": "governed-approval:decide",
    "protocol": "openid-connect",
    "description": "CDD-036 canonical scope -- Governed Human Approval decide (approve/reject) authority (not granted to the primary demo persona).",
    "attributes": {
      "include.in.token.scope": "true",
      "display.on.consent.screen": "false"
    }
  }
  ```
- Add both scope names to `ctec-frontend.optionalClientScopes`.
- Do NOT add either to `ctec-frontend.defaultClientScopes`.
- No other scope, client, user, role, or group may be modified.

## 10. Requester authority (binding)

Creating a request and executing an approved, matching request both require
`governed-approval:request`. The requester need not hold `governed-approval:decide`.

## 11. Approver authority (binding)

Approving or rejecting requires `governed-approval:decide`. The approver need not hold
`governed-approval:request`.

## 12. Self-approval policy (binding, frozen)

Self-approval is PROHIBITED. `decide()` fails with `APPROVAL_SELF_APPROVAL_PROHIBITED` whenever
`principal.principal_id == request.requested_by`, regardless of scope held. This check occurs
before the status/tenant checks are otherwise sufficient to permit a decision.

## 13. Tenant isolation (binding)

Every operation requires `principal.tenant_id == request.tenant_id`; mismatch fails with
`APPROVAL_TENANT_MISMATCH` and produces zero state change, for `decide()` and `execute()` alike.

## 14. Consequential action definition (binding, frozen)

```
action_id:     "gate-s-governed-note-write"
description:   "Deterministic, approval-gated, one-time durable write of a caller-supplied,
                length-bounded note. Proves Gate S's governed human-authorization pipeline with a
                real, durable, auditable state mutation -- not a real external business action."
input:         note_text: str, 1 <= len(note_text) <= 500
```

No second action type may be registered under this CDD's authority.

## 15. Approval lifecycle (binding, frozen)

Exactly three closed states: `PENDING`, `APPROVED`, `REJECTED`. `APPROVED` and `REJECTED` are both
terminal — no state ever transitions out of either. No DRAFT, SUBMITTED, ESCALATED, DELEGATED,
CANCELLED, EXPIRED, REOPENED, multi-stage, or quorum state is authorized.

## 16. Immutable action binding (binding, frozen)

At request creation, `action_input_digest = SHA-256(canonical_json({"action_id": action_id,
"note_text": note_text}))`, using `json.dumps(..., sort_keys=True, separators=(",", ":"))` for
canonicalization, stored immutably on the approval request row. This digest is never recomputed
or altered after creation.

## 17. Stale-action / TOCTOU protection (binding, frozen)

At `execute()`, the caller re-supplies `note_text`; the service recomputes the digest exactly as
in Sec16 and compares it to the stored digest. Any mismatch fails with `APPROVAL_ACTION_MISMATCH`
and produces zero write, zero consumption. This is the sole mechanism preventing "approve A, mutate
to B, execute B" — no separate action-versioning table is introduced.

## 18. One-time consumption / replay prevention (binding, frozen)

One approval authorizes exactly one execution. `consumed_on`/`consumed_execution_id` are set
exactly once, inside the same row-locked transaction that performs the durable write. A second
`execute()` call against the same approval — from the same or a different principal — fails with
`APPROVAL_ALREADY_CONSUMED` and produces zero write.

## 19. Persistence model (binding, frozen)

Two new tables, migration `0018_gate_s_approval.py`:

```
gate_s_approval_requests
  approval_id            UUID PRIMARY KEY
  tenant_id               String(200) NOT NULL, indexed
  action_id                String(200) NOT NULL
  note_text                String(500) NOT NULL
  action_input_digest      String(64) NOT NULL
  requested_by              String(200) NOT NULL
  requested_on              DateTime(timezone=True) NOT NULL
  status                     String(16) NOT NULL   -- PENDING | APPROVED | REJECTED
  decided_by                 String(200) NULL
  decided_on                 DateTime(timezone=True) NULL
  rejection_reason           String(1000) NULL
  consumed_on                DateTime(timezone=True) NULL
  consumed_execution_id       UUID NULL

gate_s_governed_notes
  governed_note_id          UUID PRIMARY KEY
  tenant_id                  String(200) NOT NULL, indexed
  approval_id                 UUID NOT NULL, references gate_s_approval_requests.approval_id
  note_text                   String(500) NOT NULL
  created_by                   String(200) NOT NULL
  created_at                    DateTime(timezone=True) NOT NULL
```

No other table is authorized. No existing table is modified.

## 20. Transaction / concurrency semantics (binding, frozen)

`decide()` and `execute()` each load the approval row via `SELECT ... FOR UPDATE` inside a single
database transaction that also performs the resulting write (status change, or note insert +
consumption marking). Guarantee: two concurrent decisions on the same approval serialize — the
second observes a terminal status and fails with `APPROVAL_NOT_PENDING`. Two concurrent executions
on the same approval serialize — the second observes `consumed_on` already set and fails with
`APPROVAL_ALREADY_CONSUMED`. This guarantee is scoped to a single approval row only; no cross-row,
cross-tenant, or distributed-lock guarantee is claimed.

## 21. Execution attachment (binding, restated)

`GateSApprovalService.execute()` is the sole code path with write access to
`gate_s_governed_notes`: it is the only method that calls
`GateSApprovalRepository.insert_governed_note_and_consume`, which is itself the only function body
in the entire codebase that constructs a `GateSGovernedNoteORM` row. It is entirely independent of
`GovernedToolExecutor`/`GOVERNED_TOOL_REGISTRY` — no import, no call, no shared code.

## 22. Bypass prevention (binding, load-bearing)

No other router, service, or test fixture outside the authorized surface (Sec-AA of the
companion Artifact Authorization) may construct a `GateSGovernedNoteORM` row. This is structurally
enforced, not merely a convention: the write exists in exactly one function body in the entire
codebase (`GateSApprovalRepository.insert_governed_note_and_consume`), reachable only from
`GateSApprovalService.execute()`. An architecture test asserts this exactly (Sec33).

## 23. Result/failure contract (binding, frozen)

Nine closed diagnostic codes, no HTTP-status semantics baked into the domain layer:

```
APPROVAL_REQUEST_NOT_FOUND        -- approval_id does not exist for the caller's tenant
REQUEST_AUTHORITY_REQUIRED        -- caller lacks governed-approval:request
DECISION_AUTHORITY_REQUIRED       -- caller lacks governed-approval:decide
APPROVAL_TENANT_MISMATCH          -- caller's tenant does not match the request's tenant
APPROVAL_SELF_APPROVAL_PROHIBITED -- caller is the original requester
APPROVAL_NOT_PENDING              -- decide() attempted on a non-PENDING request
APPROVAL_REJECTED                 -- execute() attempted on a REJECTED request
APPROVAL_ACTION_MISMATCH          -- recomputed digest does not match the stored digest
APPROVAL_ALREADY_CONSUMED         -- execute() attempted on an already-consumed approval
```

No raw internal exception, stack trace, or database error message ever escapes to the API
boundary.

## 24. Audit / provenance contract (binding, frozen)

Reuses the existing, unmodified `SecurityAuditService`/`ApiSecurityAuditRepository`/
`api_security_audit_events` mechanism (CDD-013). No new audit table. Exactly one audit record per
operation (request/approve/reject/execute), each carrying: `operation` (one of
`"GATE_S_REQUEST_APPROVAL"`, `"GATE_S_DECIDE_APPROVAL"`, `"GATE_S_EXECUTE_APPROVED_ACTION"`),
`endpoint_classification="GOVERNED_HUMAN_APPROVAL_API_V1"`, `event_category="HUMAN_APPROVAL"`,
`outcome` (`"SUCCESS"`/`"DENIED"`/`"FAILED"`), `diagnostic_code` (Sec23 value or `"REQUESTED"`/
`"APPROVED"`/`"REJECTED"`/`"EXECUTED"` on success), `correlation_id`, `tenant_id`/
`principal_reference` (derived from the acting principal), `execution_id` (the consuming
execution's id, present only on the execute operation), `authorization_decision_reference` (the
scope checked), `evidence_resource_reference` (the `approval_id`), `source_channel="HTTP_API"`.

## 25. Domain-state vs. audit split (binding, restated)

`gate_s_approval_requests.note_text` is domain state — it must be persisted and readable so the
approver can genuinely review what they are authorizing. It is never written to any audit field.
The audit event's `evidence_resource_reference` carries only the bounded `approval_id`.

## 26. Payload restrictions (binding)

`note_text` never enters any audit field. No credential material, no stack trace, no arbitrary
unbounded payload may ever appear in any audit field or in any API error response.

## 27. API decision (binding, frozen)

A narrow, authenticated FastAPI router, exactly five endpoints:

```
POST   /api/v1/governed-approval/requests                 (governed-approval:request)
GET    /api/v1/governed-approval/requests/{approval_id}    (governed-approval:request OR governed-approval:decide)
POST   /api/v1/governed-approval/requests/{approval_id}/approve  (governed-approval:decide)
POST   /api/v1/governed-approval/requests/{approval_id}/reject   (governed-approval:decide)
POST   /api/v1/governed-approval/requests/{approval_id}/execute  (governed-approval:request)
```

No `list`, no PUT/PATCH/DELETE.

## 28. Frontend boundary (binding, deferred)

No frontend file of any kind is created or modified in Gate S. Gate W owns the product/UI
integration and will consume the Sec27 API contract without any backend redesign.

## 29. Gate R relationship (binding, restated)

`backend/app/application/governed_tool_executor.py`, `backend/app/tests/
test_governed_tool_executor.py`, CDD-035, and CDD-035's Artifact Authorization remain
byte-unchanged. This CDD does not reopen, reinterpret, or extend CDD-035 in any way.

## 30. Gate V firewall (binding, load-bearing)

No agent, planner, LLM, model call, prompt, agent state, or agent loop exists anywhere in Gate S.
`governed-approval:decide` is never default-granted to any principal by this CDD. A future Gate V
may call `request()`/`execute()` (holding `governed-approval:request`) but can never call
`decide()`, because it would require a human-held `governed-approval:decide` grant this CDD
never issues.

## 31. Gate W boundary (binding, restated)

Gate W will later expose approval UI against the Sec27 contract. No UI work occurs in S0 or S1.

## 32. Gate Q firewall (binding)

`backend/app/application/mcp_client.py` and `backend/app/application/mcp_connector_catalog.py`
remain byte-unchanged and unimported by any Gate S file.

## 33. Cognitive-runtime firewall (binding)

No file under `backend/app/runtime/` or `backend/app/integration/adapters/` is created or
modified. No seventh cognitive-engine stage is introduced (enforced by the existing, unmodified
`test_gate_f_introduces_no_seventh_cognitive_engine_stage` test). A new architecture test asserts
Gate S imports no runtime/adapter/Gate-Q module and that `GateSGovernedNoteORM` construction
occurs in exactly one file.

## 34. Security invariants (binding, summary)

Requested != Approved != Executed. `governed-approval:request` can never satisfy
`governed-approval:decide` or vice versa. A request can never be decided by its own requester. A
request can never be decided or executed by a principal of a different tenant. An approved request
whose action has been mutated can never execute. A consumed request can never execute a second
time.

## 35. Acceptance criteria

1. Creating a request with `governed-approval:request` persists a `PENDING` row with the exact
   Sec19 fields and a correctly computed digest.
2. A principal lacking `governed-approval:request` cannot create a request.
3. A principal lacking `governed-approval:decide` cannot approve or reject.
4. A principal equal to the requester cannot approve or reject their own request.
5. A principal of a different tenant cannot approve, reject, or execute.
6. Approve transitions `PENDING -> APPROVED` exactly once; a second decide attempt fails with
   `APPROVAL_NOT_PENDING`.
7. Reject transitions `PENDING -> REJECTED` exactly once, with a stored `rejection_reason`.
8. `execute()` on a `PENDING` or `REJECTED` request fails closed with zero write.
9. `execute()` on an `APPROVED` request with matching `note_text` writes exactly one
   `gate_s_governed_notes` row and marks the approval consumed.
10. `execute()` with a mutated `note_text` fails with `APPROVAL_ACTION_MISMATCH` and zero write.
11. A second `execute()` on an already-consumed approval fails with `APPROVAL_ALREADY_CONSUMED`
    and zero write.
12. Two concurrent decide attempts on the same approval serialize; exactly one succeeds.
13. Two concurrent execute attempts on the same approval serialize; exactly one writes a note.
14. Every operation produces exactly one audit record with the exact Sec24 mapping.
15. No audit record ever contains `note_text`.
16. `governed_tool_executor.py`, `test_governed_tool_executor.py`, CDD-035, and its Artifact
    Authorization remain byte-identical.
17. Gate Q's two files and the cognitive runtime's existing tests remain green, unmodified.

## 36. Required tests (minimum set)

Request creation with correct tenant/digest; missing request-authority denial; missing
decide-authority denial; self-approval denial; cross-tenant decide/execute denial; approve
transition; reject transition (with reason); execute-on-pending denial; execute-on-rejected
denial; successful execute writes exactly one note and marks consumed; digest-mismatch denial;
double-consumption denial; concurrent-decide race (real DB, exactly one winner); concurrent-execute
race (real DB, exactly one winner); audit content for requester/approver/decision/execution-link/
correlation; `note_text` absence from audit; Gate R bypass impossibility (no other write path to
`gate_s_governed_notes`); Gate V absence; Gate W frontend absence; Gate Q unchanged; cognitive
runtime unchanged.

## 37. Non-goals

A second consequential action type; multi-stage/quorum/delegated approval; expiry/cancellation/
reopening; a `list` endpoint; real external provider execution; MCP-triggered approval; agent
-initiated decisions; frontend/UI; modification of Gate R, Gate Q, or the cognitive runtime;
modification of `dependency_container.py`.

## 38. Future extension boundary

Any future work — a second action type, multi-stage approval, delegation, expiry, MCP-triggered
requests, Gate V decision automation, or frontend exposure — requires its own, separate, explicit
Product Owner architecture decision. This CDD does not pre-authorize or streamline approval for
any of them.

## 39. Freeze conditions

Upon approval, this CDD freezes: the exact action definition (Sec14), the exact scope names and
classification (Sec9), the exact lifecycle (Sec15), the exact digest/binding mechanism (Sec16-17),
the exact consumption mechanism (Sec18), the exact persistence model (Sec19), the exact
concurrency guarantee (Sec20), the exact failure taxonomy (Sec23), and the exact audit mapping
(Sec24). Any change requires a new Product Owner decision.

## 40. Implementation authorization relationship

Publication and freeze of this CDD does NOT itself authorize implementation. A separate Artifact
Authorization enumerates the exact, closed implementation file surface. A further, separate
Product Owner implementation authorization (Gate S1) remains required before any authorized file
may be created or modified.

## 41. Explicit closure claim permitted by Gate S v1

Upon successful implementation and merge, CTEC may truthfully claim: "CTEC can require and durably
enforce independent human authorization — from a principal distinct from the requester, under the
correct tenant context — before one specific, bounded, deterministic, local consequential action
executes; the exact approved action is cryptographically bound to what executes; one approval
authorizes exactly one execution, durably enforced under real database concurrency; every request,
decision, and execution is durably, tamper-evidently recorded via the existing security-audit
mechanism — without touching Gate Q, the closed cognitive-engine runtime, Gate R's frozen
governed-tool-execution boundary, any external provider, any agent/LLM code, or any frontend." No
broader claim is authorized.

## 42. Authorization

This CDD is approved for publication, reached via Gate S0 (combined discovery, architecture
decision, and drafting). Pending Product Owner review before S1 publication. CDD-035, CDD-013, and
CDD-028 remain FROZEN and PUBLISHED, unchanged by this document.
