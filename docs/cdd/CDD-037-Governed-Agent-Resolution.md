# CDD-037 — Governed Agent Resolution

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-030 (FROZEN, Gate Q — §21: "Gate V (Governed Multi-Agent Orchestration)...
this CDD makes no claim about and does not implement any Agent Resolution Trace" — this CDD is the
first to define, not merely forward-declare, Gate V), CDD-036 (FROZEN, Gate S — §30: "A future Gate V
may call request()/execute() ... but can never call decide()" — this CDD composes with, and does not
reopen, CDD-036), CDD-013 (FROZEN, `SecurityAuditService`/`ApiSecurityAuditRepository` — reused
unmodified, Sec18)

Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via a single combined
discovery-decide-govern phase (Gate V0), per the compressed small-gate process established for Gate
R/S: exhaustive repository discovery of every Gate V forward-reference (CDD-030, CDD-033, CDD-036,
the canonical gap register), a proactive migration-impact search learning directly from Gate S's own
migration-head omission, and this freeze-ready text — pending Product Owner publication authorization
(Gate V1).

## 1. Title

Governed Agent Resolution — the first implementation of Gate V (Governed Multi-Agent Orchestration).

## 2. Capability statement (exact, binding)

A named, bounded-responsibility, deterministic agent can propose a consequential action on behalf of
an authenticated principal — with a durable, auditable resolution trace explaining its decision —
without ever acquiring, forging, or bypassing the human approval authority Gate S already enforces.

## 3. Problem

CDD-030 §21 forward-declared "Gate V (Governed Multi-Agent Orchestration)" and its "Agent Resolution
Trace" concept but implemented neither. No prior CDD defines how an automated, non-human component may
participate in CTEC's governed action pipeline without itself becoming, forging, or bypassing human
approval authority.

## 4. Why now

Gate S (CLOSED) proved durable human approval for a bounded consequential action. Gate R (CLOSED)
proved deterministic governed execution. Both boundaries are stable enough to compose with rather than
wait on. Building the smallest possible agent-proposal capability now — reusing Gate S's approval
pipeline entirely unchanged — closes CDD-030's own forward-declared gap without inventing new
architecture beyond what composition requires.

## 5. Dependencies (binding)

Consumes, by call only, entirely unmodified: `GateSApprovalService.request()` (CDD-036), the existing
`TrustedPrincipal` (CDD-013/Gate E), `SecurityAuditService`/`ApiSecurityAuditRepository` (CDD-013), and
`Container.ontology_sessions` (the existing, already-shared session factory). Does not depend on Gate
Q's MCP catalog (explicitly deferred, Sec6), Gate R (not consumed at all), or Gate T (no functional
relationship).

## 6. Non-goals (binding)

No real LLM/AI reasoning of any kind — the v1 agent is a deterministic, bounded, rule-based decision
procedure, matching the honesty convention of every prior gate ("Name it honestly. Do not imply [real
capability] beyond what is proven"). No multi-agent coordination — exactly one named agent in v1. No
agent-to-agent interaction. No new consequential action type — reuses Gate S's `gate-s-governed-note-
write` unchanged. No execution capability — Gate V only proposes; execution remains Gate S's own,
unmodified `execute()`. No frontend. No Gate Q catalog consumption in v1. No DQ. No Gate W. No
idempotency/deduplication of repeated proposals (documented, not claimed).

## 7. Domain model (binding, frozen)

```
AgentResolutionOutcome (closed StrEnum): PROPOSED, SUPPRESSED

GateVAgentResolution (frozen dataclass):
  resolution_id:      UUID
  tenant_id:           str
  agent_id:             str    -- fixed literal "gate-v-deterministic-notifier-agent" in v1
  requested_by:          str    -- the calling principal's principal_id (plain string, no FK,
                                    matching Gate S's own requested_by convention)
  observation_text:       str    -- caller-supplied, 1 <= len <= 500
  priority_score:          int    -- caller-supplied, 0 <= value <= 100
  outcome:                  AgentResolutionOutcome
  approval_id:                UUID | None  -- present only when outcome == PROPOSED; references
                                              gate_s_approval_requests.approval_id (read-only, Gate S
                                              schema unchanged)
  resolved_on:                 datetime
```

Immutable: no field is ever updated after the row is written. No lifecycle beyond one-shot creation
(Sec13).

## 8. Identity model (binding, load-bearing)

The existing `TrustedPrincipal` (principal_id, tenant_id, scopes, roles, issuer, issued_at, expires_at)
is the sole identity/tenant authority, reused unchanged. **No new identity type is introduced.** The
named agent (`gate-v-deterministic-notifier-agent`) is a capability/component identifier stored as a
plain string domain field — it is never a security principal, holds no scopes, no token, and cannot be
authenticated as. Every Gate V operation is invoked by, and every resulting Gate S approval request is
attributed to, the real, already-authenticated calling `TrustedPrincipal`.

## 9. Authority model (binding, frozen)

Two authorities gate the one write-adjacent operation, both required together (Sec10):

```
governed-agent:propose      DEFINED=YES  OPTIONAL=YES  DEFAULT=NO
governed-approval:request   (existing, CDD-036 — unmodified)
```

```
POST /resolutions:  governed-agent:propose AND governed-approval:request
GET  /resolutions/{id}: governed-agent:propose OR governed-approval:decide
```

No `gate-v:admin` or broad capability is created. Authority is revalidated independently at Gate V's
own router and again, unmodified, inside Gate S's `request()`.

## 10. Confused-deputy prevention (binding, load-bearing)

Requiring **both** `governed-agent:propose` and `governed-approval:request` — not `governed-agent:
propose` alone — before invoking `GateSApprovalService.request()` on the caller's behalf ensures Gate
V can never grant a principal the ability to create a Gate S approval request they could not already
create by calling Gate S directly. Gate V introduces zero privilege escalation.

## 11. Tenant model (binding)

Tenant is derived exclusively from `TrustedPrincipal.tenant_id` — never from caller-supplied payload.
`gate_v_agent_resolutions.tenant_id` is set once, immutable. `GET` from a different tenant fails with
`RESOLUTION_TENANT_MISMATCH` (fetch-then-compare, mirroring CDD-036's own tenant-check pattern).

## 12. Human-authority firewall (binding, load-bearing)

The agent cannot approve: no Gate V code imports or calls `GateSApprovalService.approve()`/`reject()`/
`decide()`. The agent cannot forge approver identity: `decided_by` is always Gate S's own
`principal.principal_id`, entirely outside Gate V's reach. The agent cannot grant itself approval
authority: it has no identity to grant anything to (Sec8). **Self-approval is inherited from Gate S at
zero additional cost**: because Gate V sets `requested_by` to the calling principal's own
`principal_id` — identical to what Gate S would record if that principal called it directly — Gate
S's existing `principal.principal_id == request.requested_by` check automatically prevents the same
principal from approving their own agent-derived request.

## 13. Lifecycle (binding)

None beyond one-shot creation. A `GateVAgentResolution` is written exactly once and never transitions.
There is no "approve this resolution" step — only the Gate S request it may produce (when
`PROPOSED`) follows Gate S's own unchanged lifecycle.

## 14. Deterministic decision rule (binding, frozen)

```
IF priority_score >= 50:
    outcome = PROPOSED
    note_text = f"Agent observation: {observation_text}"
    call GateSApprovalService.request(principal=caller, note_text=note_text)
    approval_id = <result.approval_id>
ELSE:
    outcome = SUPPRESSED
    approval_id = None
```

The threshold (`50`) is a fixed domain constant, not caller-configurable, not a runtime policy engine
(Sec6's non-goal boundary). `note_text` derivation is a fixed, deterministic string transform — not
free-form generation.

## 15. Persistence model (binding, frozen)

One new table, migration `0019_gate_v_agent_resolution.py`:

```
gate_v_agent_resolutions
  resolution_id      UUID PRIMARY KEY
  tenant_id            String(200) NOT NULL, indexed
  agent_id              String(200) NOT NULL
  requested_by            String(200) NOT NULL
  observation_text         String(500) NOT NULL
  priority_score             Integer NOT NULL
  outcome                     String(16) NOT NULL   -- PROPOSED | SUPPRESSED
  approval_id                  UUID NULL, references gate_s_approval_requests.approval_id
                                          (read-only reference; Gate S's own table is not modified by
                                          this foreign key's declaration)
  resolved_on                   DateTime(timezone=True) NOT NULL
```

No existing table is altered.

## 16. Migration (binding, frozen)

```
revision = "0019_gate_v_agent_resolution"
down_revision = "0018_gate_s_approval"
```

## 17. Migration-impact remediation (binding, load-bearing — learned from Gate S)

The following four pre-existing, Gate-V-unrelated tests hardcode the overall repository migration head
and will become stale the instant `0019_gate_v_agent_resolution` is applied. Their corrections are
authorized directly in this CDD's companion Artifact Authorization — not deferred to a second,
post-hoc Defect Authorization:

```
backend/app/tests/test_decision_engine.py        revision: "0018_gate_s_approval" -> "0019_gate_v_agent_resolution"
backend/app/tests/test_governance_engine.py       revision: "0018_gate_s_approval" -> "0019_gate_v_agent_resolution"
backend/app/tests/test_knowledge_engine.py         revision: "0018_gate_s_approval" -> "0019_gate_v_agent_resolution"
backend/app/tests/test_persistence_integration.py   revision: "0018_gate_s_approval" -> "0019_gate_v_agent_resolution"
                                                       table_count: 63 -> 64
```

## 18. API decision (binding, frozen)

```
POST /api/v1/governed-agent/resolutions
GET  /api/v1/governed-agent/resolutions/{resolution_id}
```

No `list`, no PUT/PATCH/DELETE, no execute endpoint.

## 19. Request/response contracts (binding, frozen)

```
POST request:   { observation_text: str (1..500), priority_score: int (0..100) }
POST response:  { resolution_id: UUID, agent_id: str, outcome: str, approval_id: UUID | None,
                   resolved_on: datetime }
GET response:   POST response fields + { tenant_id: str, requested_by: str, observation_text: str,
                   priority_score: int }
```

## 20. Gate S composition (binding, restated)

`GateVApplicationService` calls `GateSApprovalService.request(principal=caller, note_text=...)`
directly, in-process, unmodified. Gate V never calls `approve()`, `reject()`, `decide()`, or
`execute()`. Gate S's own digest binding, one-time consumption, and concurrency guarantees apply
entirely unchanged to any resulting approval request.

## 21. Audit/provenance contract (binding, frozen)

Reuses the existing, unmodified `SecurityAuditService`/`ApiSecurityAuditRepository`/
`api_security_audit_events` mechanism. Exactly one audit record per Gate V operation:

```
operation:                        "GATE_V_AGENT_RESOLUTION"
endpoint_classification:          "GOVERNED_AGENT_ORCHESTRATION_API_V1"
event_category:                   "AGENT_RESOLUTION"
outcome:                          "SUCCESS" | "DENIED"
diagnostic_code:                  "PROPOSED" | "SUPPRESSED" | one of Sec23's four codes
correlation_id:                   fresh UUID per call
tenant_id / principal_reference:  derived from calling principal
execution_id:                     None always (Gate V never executes)
authorization_decision_reference: "governed-agent:propose"
evidence_resource_reference:      resolution_id once generated, else agent_id
source_channel:                   "HTTP_API"
```

`observation_text` never enters any audit field.

## 22. Concurrency (binding)

`gate_v_agent_resolutions` rows are insert-only; no shared mutable row is ever updated. No race exists
beyond a single atomic `INSERT`. The one cross-boundary interaction (`GateSApprovalService.request()`)
relies entirely on Gate S's own already-proven guarantees.

## 23. Failure semantics (binding, frozen)

```
AGENT_PROPOSE_AUTHORITY_REQUIRED    -- caller lacks governed-agent:propose
REQUEST_AUTHORITY_REQUIRED           -- caller lacks governed-approval:request
RESOLUTION_NOT_FOUND                  -- unknown resolution_id
RESOLUTION_TENANT_MISMATCH             -- caller's tenant does not match the resolution's tenant
```

Field-level validation (`observation_text` length, `priority_score` range) is enforced by the request
schema; malformed input never reaches the domain layer. No raw internal exception ever escapes.

## 24. Bypass prevention (binding, load-bearing)

`GateVAgentResolutionORM` may be constructed in exactly one location in the entire codebase (the
repository implementation). An architecture test enforces this exactly, mirroring CDD-036's own
single-write-site enforcement.

## 25. Gate Q firewall (binding)

`mcp_client.py`/`mcp_connector_catalog.py` remain byte-unchanged and unimported. Gate Q's catalog
consumption is explicitly deferred (Sec6).

## 26. Gate R firewall (binding)

`governed_tool_executor.py`/`GOVERNED_TOOL_REGISTRY` remain byte-unchanged and unimported. Gate V does
not execute anything.

## 27. Gate S firewall (binding, restated)

`gate_s_approval_service.py`, `gate_s_approval_repository.py`, Gate S's domain/models, its tests,
CDD-036, its Artifact Authorization, and its Defect Authorization all remain byte-unchanged. Gate V
consumes `GateSApprovalService.request()` by call only.

## 28. Gate T firewall (binding)

Not consumed, not touched.

## 29. Gate W firewall (binding)

No production API-management/versioning framework is built. Gate V's 2 endpoints are its own narrow
surface.

## 30. DQ firewall (binding)

No DQ rule authoring, scoring, dashboard, issue management, remediation workflow, observability, or
certification of any kind.

## 31. Frontend boundary (binding, deferred)

No frontend file of any kind is created or modified. Deferred to Gate W.

## 32. Security invariants (binding, summary)

Proposing != approving != executing. `governed-agent:propose` can never satisfy `governed-approval:
decide`. The agent has no identity to forge, escalate, or delegate. A resolution can never authorize
itself to be re-decided. Cross-tenant access to a resolution fails closed.

## 33. Acceptance criteria

1. A caller holding both `governed-agent:propose` and `governed-approval:request`, with
   `priority_score >= 50`, receives `PROPOSED` and a valid `approval_id` referencing a real, pending
   Gate S approval request.
2. The same caller with `priority_score < 50` receives `SUPPRESSED` and `approval_id = None`; no Gate
   S request is created.
3. A caller missing either required scope is denied with the correct diagnostic code and zero writes.
4. A cross-tenant `GET` fails with `RESOLUTION_TENANT_MISMATCH`.
5. The calling principal cannot later approve their own agent-derived Gate S request (inherited,
   Sec12).
6. Exactly one construction site for `GateVAgentResolutionORM` exists in the codebase.
7. `observation_text` never appears in any audit record.
8. Gate Q, Gate R, Gate S, and Gate T's own files remain byte-identical.
9. The four Sec17 regression files pass with the corrected literal values.

## 34. Required tests (minimum set)

Happy-path proposal; threshold suppression; missing-`governed-agent:propose` denial; missing-
`governed-approval:request` denial; cross-tenant `GET` denial; self-approval inheritance proof;
migration schema verification; restart-durability of the resolution row; `observation_text` absence
from audit; single-write-site architecture enforcement; Gate Q/R/S file-import absence.

## 35. Non-goals (restated)

See Sec6.

## 36. Future extension boundary

A second named agent, real multi-agent coordination, Gate Q catalog-driven capability discovery,
configurable/policy-driven thresholds, idempotency/deduplication of repeated proposals, or any
execution capability each require their own, separate, explicit Product Owner architecture decision.

## 37. Implementation authorization relationship

Publication and freeze of this CDD does NOT itself authorize implementation. A separate Artifact
Authorization enumerates the exact, closed implementation file surface. A further, separate Product
Owner implementation authorization (Gate V2, or whatever this lineage names its next phase) remains
required before any authorized file may be created or modified.

## 38. Explicit closure claim permitted by Gate V v1

Upon successful implementation and merge, CTEC may truthfully claim: "CTEC can govern the proposal of a
consequential action by a named, bounded-responsibility, deterministic agent acting on behalf of an
authenticated principal — with a durable, auditable resolution trace — while inheriting Gate S's full
human-approval guarantees (self-approval prohibition, digest binding, one-time consumption) entirely
unchanged, and without the agent ever acquiring, forging, or bypassing human approval authority." No
broader claim (real AI reasoning, multi-agent coordination, autonomous execution) is authorized.

## 39. Authorization

This CDD is approved for publication, reached via Gate V0 (combined discovery, architecture decision,
and drafting). Pending Product Owner review before V1 publication. CDD-030, CDD-036, and CDD-013
remain FROZEN and PUBLISHED, unchanged by this document.
