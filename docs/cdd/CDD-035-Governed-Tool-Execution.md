# CDD-035 — Governed Tool Execution

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-030 (FROZEN, Gate Q — the sole prior document naming Gate R, §21: "Gate R
(Governed Tool Execution: Capability -> Authorization -> Execution Eligibility -> Controlled Invocation ->
Result -> Provenance)... Gate R remains free to define all of it without any Gate Q rework" -- this CDD is
the first to define, not merely forward-declare, Gate R), CDD-013 (FROZEN, `SecurityAuditService`/
`ApiSecurityAuditRepository` -- reused unmodified, Sec22), CDD-010/CDD-012 (FROZEN, the closed six-stage
Cognitive Engine Runtime Shell -- structurally independent from and never extended by this CDD, Sec30)

Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via read-only architecture discovery
(Gate R0, establishing that no prior CDD defines Gate R and that MCP/Gate Q explicitly does not implement
execution eligibility, approval, or provenance) -> Product Owner architecture-decision resolution (Gate R1,
approving decisions R1-D1 through R1-D20 exactly as recorded) -> drafting (Gate R2, resolving the two items
R1 left open: exact v1 tool identity and exact audit-field mapping) -> this R2 freeze-ready text, pending
Product Owner publication authorization (Gate R3).

## 1. Objective and business outcome

Prove that CTEC can execute a registered tool through a governed, provider-neutral runtime boundary --
under an authenticated, tenant-scoped, explicitly-authorized principal -- and return a normalized result
with durable, tamper-evident provenance, without depending on MCP, any external provider, the closed
cognitive-engine runtime, or any consequential/write action.

## 2. Governing authorities

CDD-030 remains the sole prior reference to "Gate R" and is not reopened, reinterpreted, or extended by
this CDD (Sec29). CDD-013 remains the sole authority for `SecurityAuditService`/`ApiSecurityAuditRepository`
semantics, reused here unmodified (Sec22). CDD-010/CDD-012 remain the sole authority for the closed,
six-stage Cognitive Engine Runtime Shell, structurally independent from this CDD (Sec30).

## 3. Why this CDD requires its own governance

No prior CDD defines Gate R's execution-eligibility, controlled-invocation, or provenance semantics.
CDD-030 explicitly declines to (Sec21: "this CDD establishes no execution-eligibility, controlled-
invocation, or provenance mechanism"). This CDD is that first, narrow definition.

## 4. In scope (Gate R v1)

Exactly one Gate-R-owned, deterministic, local, read-only, non-consequential tool, executed through a
provider-neutral governed pipeline: tool resolution, execution authorization, execution eligibility, input
validation, execution-identity generation, controlled invocation, result normalization, and durable
provenance recording via the existing, unmodified audit mechanism.

## 5. Architecture (binding)

```
Authenticated TrustedPrincipal
        |
        v
Resolve registered tool (closed, static allowlist)
        |
        v
Execution authorization (tool-execution:execute)
        |
        v
Execution eligibility (side_effect_class == READ_ONLY)
        |
        v
Input validation (closed, typed contract)
        |
        v
Generate execution identity (execution_id)
        |
        v
Controlled invocation (the one registered deterministic tool)
        |
        v
Normalize result/failure (closed result contract)
        |
        v
Record durable provenance (existing SecurityAuditService, unmodified)
        |
        v
Return normalized result
```

No tool implementation may execute before tool resolution, authorization, eligibility, and input
validation all succeed. Every pre-invocation denial produces exactly zero tool invocations.

## 6. Out of scope (binding)

MCP integration (any adapter, transport, or catalog reuse); real MCP servers; any real external
provider (OpenAI, Azure OpenAI, Anthropic, any external SaaS/cloud API, any vendor SDK); consequential
or write-capable tools; human approval of any kind (Gate S); agent planning, LLM tool selection, or
autonomous action (Gate V); retry, replay, or idempotency of any kind; a public API of any kind; any
frontend; new persistence or migration; modification of Gate Q (`mcp_client.py`, `mcp_connector_catalog.py`,
CDD-030); modification of the Cognitive Engine Runtime Shell (`backend/app/runtime/**`,
`backend/app/integration/adapters/**`); generalized Data Quality; Simulation; Evidence Fitness;
remediation.

## 7. R-D1 -- Provider-neutral GovernedToolExecutor (binding, R1-D1-approved)

Gate R's governance model is not MCP-specific and is not a generic plugin/adapter framework. It is a
single, closed pipeline over a single, closed, code-registered tool allowlist. Future adapters (MCP or
otherwise) are explicitly not authorized by this CDD and require their own, separate, future Product
Owner architecture decision (restated Sec29).

## 8. R-D2 -- Exactly one tool, READ-ONLY / NON-CONSEQUENTIAL (binding, R1-D2/D3-approved)

Exactly one tool is registered in v1: `gate-r-text-digest` -- a deterministic SHA-256 digest computation
over a caller-supplied, length-bounded text string. `side_effect_class` is fixed to `READ_ONLY` for this
and, structurally, for every tool eligible for execution in v1 (Sec14). No consequential/write tool may
ever be registered under this CDD's authority.

## 9. Exact v1 tool contract (binding, frozen)

```
tool_id:          "gate-r-text-digest"
description:      "Deterministic SHA-256 digest computation over caller-supplied, length-bounded text.
                    Proves Gate R's governed invocation pipeline with a real, verifiable, side-effect-free
                    computation -- not a business action of any existing Gate."
side_effect_class: READ_ONLY
required_scope:    "tool-execution:execute"
```

Input contract (closed, no extra fields):
```
text: str, 1 <= len(text) <= 1024
```

Output contract (closed, no extra fields):
```
algorithm:   Literal["sha256"]
digest_hex:  str  (exactly 64 lowercase hex characters)
```

The digest is computed via the Python standard library `hashlib.sha256(text.encode("utf-8")).hexdigest()`
-- deterministic, pure, no I/O, no network, no filesystem, no database, no system mutation.

## 10. R-D4 -- MCP boundary (binding, R1-D4-approved)

MCP integration of any kind is explicitly DEFERRED. This CDD does not authorize, imply, or streamline any
future MCP adapter. `backend/app/application/mcp_client.py`, `backend/app/application/
mcp_connector_catalog.py`, and CDD-030 remain byte-unchanged and unreopened by this CDD in every respect.

## 11. TrustedPrincipal authority (binding, R1-D6-approved)

The existing `TrustedPrincipal` (principal_id, tenant_id, scopes, roles, issuer, issued_at, expires_at) is
the sole identity/tenant authority. No new identity abstraction is introduced. The execution input
contract (Sec9) is structurally incapable of carrying `principal_id`, `tenant_id`, `scopes`, or `roles` --
it is a closed dataclass containing exactly the `text` field and nothing else.

## 12. Execution-scope contract (binding, frozen, R1-D5-approved)

New scope: `tool-execution:execute`.

```
DEFINED  = YES
OPTIONAL = YES
DEFAULT  = NO
```

This scope is distinct from, and must never be conflated with or substituted by, `mcp-connector:read` (a
different Gate's discovery-only scope) or any other existing scope. Discovery authority never implies
execution authority.

Keycloak realm change (exact, for R4):
- Add one new `clientScopes` entry:
  ```json
  {
    "name": "tool-execution:execute",
    "protocol": "openid-connect",
    "description": "CDD-035 canonical scope -- Governed Tool Execution invocation authority (not granted to the primary demo persona).",
    "attributes": {
      "include.in.token.scope": "true",
      "display.on.consent.screen": "false"
    }
  }
  ```
- Add `"tool-execution:execute"` to `ctec-frontend.optionalClientScopes`.
- Do NOT add it to `ctec-frontend.defaultClientScopes`.
- No other scope, client, user, role, or group may be modified.

## 13. Tool registration contract (binding, frozen, R1-D7-approved)

Static, code-registered, closed allowlist -- a single Python tuple of exactly one entry, mirroring
`MCP_CONNECTOR_CATALOG`'s own shape. Minimum metadata, each field individually justified:

```
tool_id:            str   -- stable identity, the allowlist's primary key
description:        str   -- governance auditability
required_scope:     str   -- the entire authorization mechanism
side_effect_class:  Literal["READ_ONLY"]  -- frozen to one value in v1; kept as an explicit field
                                              (not omitted) so a future, separately-governed value is
                                              additive, not a schema break
input_contract:     the frozen input dataclass type
output_contract:    the frozen output dataclass type
execution_reference: the one Python callable implementing the tool
```

No `enabled`/`disabled` administrative field. No dynamic registration, runtime installation, plugin
marketplace, or arbitrary code loading of any kind. If a tool must be removed, it is removed from this
code-level tuple -- a governed code change, never a runtime toggle.

## 14. Exact v1 tool identity (restated, binding)

The allowlist contains exactly the entry frozen in Sec9. No second entry may be added under this CDD's
authority.

## 15. Side-effect classification (binding)

`side_effect_class` is a closed enumeration with exactly one member authorized for execution in v1:
`READ_ONLY`. Any future value (e.g. a consequential/write class) requires its own, separate, future
Product Owner architecture decision and is not implied, streamlined, or pre-authorized by this CDD.

## 16. Execution eligibility (binding, frozen, R1-D8-approved)

A registered tool is eligible for execution if and only if, evaluated fresh on every call (never
persisted, no eligibility table, no state machine):

```
registered
AND side_effect_class == READ_ONLY
AND principal holds "tool-execution:execute"
AND input satisfies the declared, closed input contract
AND principal/tenant context originates from a valid, authenticated TrustedPrincipal
```

## 17. Input contract / validation (binding, R1-D9-approved)

Validation uses the repository's existing typed, closed-dataclass-with-`__post_init__` pattern (mirroring
Gate M's own domain-object validation, since Gate R v1 has no HTTP/Pydantic schema boundary). Validation
occurs strictly before invocation. Invalid input produces zero tool invocations and the `INVALID_INPUT`
status (Sec19). No generic JSON-schema validation engine is introduced.

## 18. Invocation semantics (binding)

Exactly one call site invokes the tool's `execution_reference`, reached only after tool resolution,
authorization, eligibility, and input validation have all succeeded, in that order. `execution_id` (a
fresh UUID) is generated immediately before this call and is included in both the result (Sec19) and the
provenance record (Sec22) from this point onward.

## 19. Normalized result contract (binding, frozen, R1-D10-approved)

A single, closed, unified result object represents every outcome (success and every denial/failure alike)
-- not controlled exceptions -- mirroring the existing `InformationElementEvidenceFitnessResolutionResult`
application-layer pattern.

```
execution_id:    UUID | None   (None only for denials occurring before execution-identity generation --
                                 UNKNOWN_TOOL, AUTHORIZATION_SCOPE_REQUIRED, TOOL_INELIGIBLE, INVALID_INPUT)
tool_id:         str
status:          GovernedToolExecutionStatus  (closed enum, Sec20)
result:          Mapping[str, object] | None  (populated only when status == EXECUTED; contains exactly
                                                 the tool's frozen output contract, Sec9)
correlation_id:  UUID  (always present, generated fresh at the very start of every call)
completed_at:    datetime  (always present)
diagnostic_code: str | None  (None only when status == EXECUTED; equals the status name otherwise)
```

No raw provider payload, no credential material, no unbounded or provider-specific data may ever appear
in `result`.

## 20. Failure/error taxonomy (binding, frozen)

Exactly six closed status values, no HTTP status semantics (Gate R v1 has no HTTP API):

```
EXECUTED                     -- success
UNKNOWN_TOOL                 -- tool_id not present in the closed allowlist
AUTHORIZATION_SCOPE_REQUIRED -- principal lacks tool-execution:execute
TOOL_INELIGIBLE              -- registered tool's side_effect_class is not READ_ONLY (structurally
                                 unreachable in v1, since the only registered tool is READ_ONLY; retained
                                 for forward-compatible closure of the eligibility rule, Sec16)
INVALID_INPUT                -- input fails the closed input contract
INVOCATION_FAILED            -- the tool's execution_reference raised during invocation
```

## 21. Audit-failure fail-closed rule (binding, load-bearing)

The success provenance record (Sec22) is written before the `EXECUTED` result is returned to the caller.
If writing it raises, that exception propagates out of the executor -- the caller never receives an
`EXECUTED` result. A governed execution whose required provenance cannot be durably recorded is never
represented as successfully governed execution.

## 22. Audit/provenance contract (binding, frozen, R1-D11-approved)

Reuses the existing, unmodified `SecurityAuditService.record(...)` / `ApiSecurityAuditRepository` /
`api_security_audit_events` mechanism (CDD-013). No new Gate R persistence, no new table, no migration.

Exact field mapping, frozen for R4:

```
operation:                        "EXECUTE_GOVERNED_TOOL"  (stable constant, never tool-specific)
endpoint_classification:          "GOVERNED_TOOL_EXECUTION_APPLICATION_V1"
event_category:                   "TOOL_EXECUTION"
outcome:                          "SUCCESS" | "DENIED" | "FAILED"
diagnostic_code:                  the exact status value (Sec20)
correlation_id:                   the fresh correlation_id generated at call start
tenant_id / principal_reference:  derived automatically from principal= (existing behavior, unmodified)
execution_id:                     present from generation onward (Sec18); None for pre-validation denials
attempt_id:                       not used (None always) -- meaningful only once retry exists (deferred,
                                   Sec26)
authorization_decision_reference: literal "tool-execution:execute" (the scope evaluated), always present
evidence_resource_reference:      the tool_id (e.g. "gate-r-text-digest") -- the chosen safe, bounded
                                   field encoding tool identity
source_channel:                   "APPLICATION_LAYER"
```

Exactly one audit record is produced per executor call, for every outcome (success and every denial/
failure alike).

## 23. Payload-persistence prohibition (binding, restated from CDD-013, R1-D12-approved)

Raw tool input (`text`) and raw tool output (`digest_hex`) are never written to any audit field, any new
table, or any log beyond standard application logging already governed elsewhere. Only the bounded
`tool_id` reference (Sec22) identifies which tool executed.

## 24. Tenant/principal isolation (binding)

Tenant and principal identity in every result and every audit record originate exclusively from the
authenticated `TrustedPrincipal` resolved at the OIDC boundary -- never from caller-supplied input (Sec11,
Sec17).

## 25. Authorization ordering (binding, restated)

Authorization (Sec12) is evaluated strictly before eligibility (Sec16), which is evaluated strictly before
input validation (Sec17), which is evaluated strictly before invocation (Sec18). No reordering is
authorized.

## 26. Validation ordering (binding, restated)

Input validation occurs after authorization and eligibility, and strictly before execution-identity
generation and invocation (Sec5).

## 27. No-side-effect-on-denial rule (binding, load-bearing)

Every one of `UNKNOWN_TOOL`, `AUTHORIZATION_SCOPE_REQUIRED`, `TOOL_INELIGIBLE`, and `INVALID_INPUT`
produces exactly zero tool invocations. This is structurally guaranteed by Sec18's single call site being
reachable only after all four checks succeed, not merely a documented convention.

## 28. Deterministic behavior (binding)

The v1 tool is a pure function of its validated input -- identical input always yields identical output.
No randomness, no clock dependency, no external state dependency of any kind.

## 29. Gate Q firewall (binding, R1-D19-approved)

`backend/app/application/mcp_client.py`, `backend/app/application/mcp_connector_catalog.py`, and CDD-030
(core document and its Artifact Authorization) remain byte-unchanged. This CDD does not reopen, reinterpret,
or extend CDD-030 in any way -- Sec21's forward-declaration is fulfilled, not amended.

## 30. Cognitive-runtime firewall (binding, R1-D18-approved)

Gate R is structurally independent from the closed, six-stage Cognitive Engine Runtime Shell. No file
under `backend/app/runtime/**` or `backend/app/integration/adapters/**` is created or modified. No
seventh cognitive-engine stage is introduced (enforced by the existing, unmodified
`test_gate_f_introduces_no_seventh_cognitive_engine_stage` test). No CDD-010 or CDD-012 semantic changes.

## 31. Gate S firewall (binding, R1-D16-approved)

No human-approval concept of any kind is implemented: no approval record, approval state, approval
placeholder, approver identity, approval hook, approval API, approval UI, or approval persistence. Gate S
remains the sole future owner of approval semantics, downstream of Gate R's own eligibility check.

## 32. Gate V firewall (binding)

No agent, planner, LLM, autonomous tool-selection policy, or orchestration framework of any kind is
implemented or implied.

## 33. API firewall (binding, R1-D13-approved)

No public API of any kind: no router, no HTTP endpoint, no API-layer DTO, no `backend/app/main.py`
registration. Gate R v1 is application-layer-only.

## 34. Frontend firewall (binding, R1-D14-approved)

No frontend file of any kind is created or modified.

## 35. Persistence/migration firewall (binding, R1-D11-approved)

No new database table, ORM model, repository, or migration of any kind. The existing
`api_security_audit_events` table and its existing repository/service are reused entirely unmodified.

## 36. Provider firewall (binding, R1-D17-approved)

OpenAI, Azure OpenAI, Anthropic, any external SaaS, any cloud provider API, any production MCP server, and
any vendor SDK are all explicitly PROHIBITED in Gate R v1.

## 37. Retry/replay/idempotency boundary (binding, R1-D15-approved)

Retry, replay, and idempotency are explicitly DEFERRED -- not implemented, not scaffolded, not
placeholder-hooked. A synchronous, deterministic, read-only tool has no duplicate-side-effect risk to
suppress. CDD-012's cognitive-runtime retry/replay/idempotency mechanisms are not inherited, referenced,
or reused. A future consequential-tool decision would need to explicitly revisit this boundary.

## 38. Security invariants (binding, summary)

Discoverable (registered) != execution-authorized (holds the scope) != execution-eligible (passes the
eligibility conjunction) != executed (passed validation and was invoked). `tool-execution:execute` can
never be satisfied by `mcp-connector:read` or any other existing scope. Caller input can never supply
`principal_id`, `tenant_id`, `scopes`, or `roles`. No default-granted execution authority exists.

## 39. Acceptance criteria

1. Exactly one tool is registered, matching Sec9 exactly.
2. `tool-execution:execute` exists exactly once in `clientScopes`, exactly once in
   `optionalClientScopes`, and zero times in `defaultClientScopes`.
3. A principal holding `tool-execution:execute` and valid input successfully executes the tool and
   receives an `EXECUTED` result matching the tool's output contract exactly.
4. A principal lacking the scope receives `AUTHORIZATION_SCOPE_REQUIRED` and zero invocations occur.
5. An unknown `tool_id` receives `UNKNOWN_TOOL` and zero invocations occur.
6. Invalid input (empty or >1024 chars) receives `INVALID_INPUT` and zero invocations occur.
7. Every outcome (success and every denial) produces exactly one audit record with the exact field
   mapping in Sec22.
8. No audit record ever contains the raw `text` or raw `digest_hex` value.
9. `tenant_id`/`principal_reference` in every audit record originate only from the calling
   `TrustedPrincipal`.
10. Gate Q's two files and CDD-030 remain byte-identical. The cognitive-runtime's existing tests remain
    green, unmodified.

## 40. Required tests (minimum set)

Successful execution; missing execution scope (fail-closed, zero invocations); unknown tool (fail-closed,
zero invocations); invalid input, both too-short and too-long (fail-closed, zero invocations); exact
normalized result shape on success; exactly one audit record per call, for both success and each denial
path, with correct tenant/principal/tool-identity/outcome fields; raw input/output absence from the audit
call's arguments; deterministic repeatability (same input twice yields identical digest); no Gate Q file
imported or modified (static analysis/architecture-test level, not this file's own responsibility --
already covered by existing, unmodified `test_runtime_architecture.py` tests).

## 41. Non-goals

MCP integration; real MCP server; any real external provider; consequential/write tools; human approval;
agent orchestration; LLM tool selection; retry; replay; idempotency; public API; frontend; new
persistence; migration; multi-tool registration; dynamic/runtime tool registration; generalized plugin
framework; modification of Gate Q or the cognitive runtime; generalized Data Quality; Simulation;
Evidence Fitness; remediation; autonomous action.

## 42. Future extension boundary

Any future work building on this CDD -- a second registered tool, a consequential/write tool class, an
MCP adapter, a public API, frontend exposure, retry/replay/idempotency, or Gate S/Gate V integration --
requires its own, separate, explicit Product Owner architecture decision. This CDD does not pre-authorize,
imply, or streamline approval for any of them.

## 43. Architecture drift protections

The eligibility rule (Sec16) structurally rejects any tool whose `side_effect_class` is not `READ_ONLY` --
a future consequential tool cannot silently become executable merely by being added to the allowlist; it
requires both a code change to the eligibility rule itself (a visible, reviewable diff) and its own
governance decision. The closed result-status enum (Sec20) prevents silent addition of new outcomes
without a visible schema change.

## 44. Freeze conditions

Upon approval, this CDD freezes: the exact tool identity and contract (Sec9), the exact scope name and
classification (Sec12), the exact eligibility conjunction (Sec16), the exact result contract and status
taxonomy (Sec19-20), the exact audit field mapping (Sec22), and every firewall in Sec29-36. Any change to
these requires a new Product Owner decision.

## 45. Implementation authorization relationship

**Publication and freeze of this CDD does NOT itself authorize implementation.** A separate Artifact
Authorization (this CDD's companion document) enumerates the exact, closed implementation file surface. A
further, separate Product Owner implementation authorization (Gate R4) remains required before any
authorized file may be created or modified.

## 46. Explicit closure claim permitted by Gate R v1

Upon successful implementation and merge, CTEC may truthfully claim: "CTEC can execute exactly one
registered, deterministic, read-only, non-consequential tool through a governed, provider-neutral,
application-layer runtime boundary, under an authenticated, tenant-scoped principal holding an explicit,
non-default execution authority, and return a narrow, normalized, provider-agnostic result -- with a
durable, tamper-evident audit/provenance record via the existing security-audit mechanism -- without
touching Gate Q, the closed cognitive-engine runtime, any external provider, any consequential/write
action, or any human-approval concept." No broader claim is authorized.

## 47. Authorization

This CDD is approved for publication, reached via Gate R0 (discovery) -> R1 (architecture decision,
Product Owner approval of R1-D1 through R1-D20) -> this R2 drafting turn. Pending Product Owner review
before R3 publication. CDD-030, CDD-013, CDD-010, and CDD-012 remain FROZEN and PUBLISHED, unchanged by
this document.
