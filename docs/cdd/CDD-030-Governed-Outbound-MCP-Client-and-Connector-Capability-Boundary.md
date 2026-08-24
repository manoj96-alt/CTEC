# CDD-030 — Governed Outbound MCP Client and Connector Capability Boundary

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: RFC-010 (FROZEN, Canonical Enterprise Ontology Boundary — this CDD introduces no
cognitive capability and no canonical entity, §13 below), RFC-013 (FROZEN, Governance Authority and Evaluation
Separation — this CDD's discovery boundary is pure Governance Evaluation exposure, never Governance Authority,
§9 below), RFC-015 (FROZEN, Tenant Ownership Physical Model Authorization — tenant/identity origin exclusively
from the existing authenticated principal, §14 below), CDD-025/026/027/028/029 (FROZEN, Gates P/K/L/M/O — each
carries an identical, repeated MCP-firewall clause; this CDD is the first to resolve, not merely restate, that
deferral), CDD-013 (FROZEN, `SecurityAuditService`/`ApiSecurityAuditRepository` — reused unmodified, §9)

Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via discovery (Gate Q0, which established
that no prior CDD defines "Gate Q" — every one of CDD-025 §17, CDD-026, CDD-027 §22, CDD-028, and CDD-029 §21
contains only a negative firewall clause naming "MCP"/"Gate Q," never a definition) → Product Owner
architecture-decision resolution (Gate Q1, approving Q-D1 through Q-D5 exactly as recommended, P0=0/P1=0/P2=0)
→ drafting (Gate Q2) → Product Owner CDD final review and contract normalization (Gate Q3, two P2 textual
tightenings, no architectural change, P0=0/P1=0/P2=2 resolved) → this Gate Q4 publication turn. No
implementation exists, and none is authorized by this frozen document — a separate, subsequent Artifact
Authorization companion remains required before any file is created or modified.

## 1. Objective and business outcome

Establish the smallest durable, governed boundary through which CTEC may act as an **outbound Model Context
Protocol (MCP) client**: authorized, fail-closed discovery of a small, statically-defined set of governed
external tool capabilities, and a deterministic protocol round-trip proving CTEC can correctly speak MCP —
without granting any execution authority, without persisting any credential, and without ever allowing external
MCP-sourced data to become ontology, evidence, or semantic truth.

## 2. Governing authorities

(restated per header; RFC-010/013/015 govern this CDD's constitutional boundaries; CDD-025/026/027/028/029 each
independently establish that MCP has been deferred, never designed, prior to this CDD; CDD-013 governs the
reused, unmodified security-audit infrastructure)

## 3. Why this CDD requires its own governance

Gate Q0 confirmed, by exhaustive search, that "Gate Q," "MCP client," "MCP server," and "connector framework"
have never been defined by any prior authority — every mention across CDD-025 through CDD-029 is a negative
firewall clause ("no MCP client, no MCP server... anywhere in this CDD's scope"). The only concrete, non-CDD
repository evidence is `backend/app/domain/ontology/connector_catalog.py`'s own `mcp` entry
(`maturity="Roadmap"`, `source_system_type="Model Context Protocol"`), which is Ontology-Studio display
metadata, not governance, and does not itself authorize anything. A new, standalone CDD is the only textually
honest instrument, identical reasoning to every prior standalone CDD in this lineage.

## 4. In scope (Gate Q v1)

A new, standalone application-layer MCP client capable of: (a) protocol initialization against exactly one
deterministic local transport; (b) fail-closed, per-caller-authorized Tools discovery against a new, small,
statically-defined, Gate-Q-owned tool/connector catalog; (c) one protocol-conformance tool invocation against
the same deterministic local server, explicitly classified as a test/protocol-proof action, never a governed
business action. Nothing else.

## 5. Architecture (binding — encodes the Gate Q1-approved diagram)

```
Authenticated Principal (existing Gate E TrustedPrincipal)
    |
    v
Fail-Closed Discovery Authorization  (new, Gate-Q-owned scope check, before any catalog exposure)
    |
    v
Gate-Q-Owned Static Tool/Connector Catalog  (new, code-defined, separate from connector_catalog.py)
    |
    v
MCP Client  (new; Tools primitive only)
    |
    v
Deterministic Local Transport  (one, test-only)
    |
    v
Local Test MCP Server  (test-only; never a real external server)
    |
    v
Tool Metadata / Protocol Result
    |
    v
Untrusted + Ephemeral Boundary  (never promoted to ontology/evidence/semantic truth)
```

No connection of any kind to Gate O, Gate I, H4, Gate N, Ask CTEC, or `connector_catalog.py`'s runtime path.

## 6. Out of scope (binding)

Any MCP server (CTEC exposing itself to external agents/consumers). Any MCP Resources or Prompts primitive. Any
second transport. Any real external MCP server or network egress. Any durable credential, secret, OAuth token,
or refresh-token persistence. Any modification to `connector_catalog.py`. Any governed business-action
execution, execution-eligibility check, or provenance record (Gate R). Any human-approval workflow (Gate S).
Any agent planner, agent memory, agent-to-agent protocol, orchestration engine, or dynamic agent generation
(Gate V). Any simulation capability (Gate U). Any frontend or UI/UX change (Gate X). Any new persistence,
migration, API endpoint, or authentication mechanism.

## 7. Q-D1 — MCP client only (binding, Gate Q1-approved)

CTEC is an outbound MCP **client** exclusively. No MCP server capability — inbound tool/resource/prompt serving
of any CTEC capability to an external MCP consumer — is authorized by this CDD. This is a structural, not
merely a v1-scope-limiting, decision: no server-side code path may exist.

## 8. Q-D2 — Tools primitive only, one deterministic transport (binding, Gate Q1-approved)

Only the MCP **Tools** primitive is authorized (discovery + the one protocol-conformance invocation of §17).
Resources and Prompts are not authorized. Exactly one deterministic local transport is authorized for the
entire v1 proof; no second transport, no configurable/pluggable transport framework.

## 9. Q-D3 — Fail-closed discovery authorization (binding, Gate Q1-approved)

An authenticated principal lacking the required Gate-Q scope MUST NOT receive any indication — in a tool
listing, error detail, or otherwise — that a given Gate-Q-governed capability exists. This is stronger than
"discover then reject invocation": the catalog returned by discovery must already be filtered to only the
capabilities the calling principal's scopes actually authorize (RFC-013's Governance Evaluation/Governance
Authority separation is preserved — this CDD only evaluates and filters already-governed catalog entries, it
never grants anything).

## 10. Q-D4 — Zero durable credential/secret persistence (binding, Gate Q1-approved)

No table, migration, cache, or any other durable store for a credential, secret, OAuth token, or refresh token
is authorized. The deterministic local test server (§8, §17) requires no real credential of any kind, proving
the entire v1 capability is achievable credential-free.

## 11. Q-D5 — Separate, non-overlapping catalog structure (binding, Gate Q1-approved)

The Gate Q tool/connector catalog is a new, small, statically-defined, Gate-Q-owned structure, entirely separate
from `backend/app/domain/ontology/connector_catalog.py`. That file — Ontology Studio display metadata,
ungoverned by any CDD — is not modified, extended, imported, depended upon, reinterpreted, synchronized with,
or merged with the Gate Q catalog. Its existing `mcp` entry (`maturity="Roadmap"`) remains an accurate
description of the fact that Gate Q v1 proves a protocol/capability boundary, not a production MCP integration.

## 12. Discovery/execution separation (binding, load-bearing)

This CDD encodes and preserves, without exception:

```
Capability Exists ≠ Capability Discoverable ≠ Capability Execution Authorized ≠ Capability Approved ≠ Capability Executed
```

This CDD resolves only the first two relations (existence, discoverability — §9). It explicitly does **not**
resolve, define, or partially implement "Capability Execution Authorized," "Approved," or "Executed" — those
belong entirely to a future Gate R (Governed Tool Execution: Capability → Authorization → Execution Eligibility
→ Controlled Invocation → Result → Provenance) and, downstream of it, Gate S (Human Approval). The one
protocol-conformance invocation authorized by §8/§17 is explicitly **not** an instance of "Capability Executed"
in Gate R's sense: it carries no execution-eligibility check, no approval step, and produces no durable
provenance record — its only purpose is proving the MCP client completes a full protocol round trip, and its
result is discarded/asserted-only.

## 13. Trust boundary (binding, load-bearing)

External MCP server metadata, tool schemas, capability descriptions, and tool results are **untrusted,
ephemeral, external input** for all purposes under this CDD. None of it may be:
- treated as ontology or canonical semantic authority (RFC-010's protected boundary);
- promoted to `SourceObservation`, `FieldValueEvidence`, or any governed evidence record (CDD-022);
- used to influence, override, or supplement `CoverageStatus` (Gate I), `EvidenceAvailabilityStatus` (H4), or
  any `InformationElementContextAvailabilityResult` (Gate N);
- persisted in any durable store.

Any future promotion path is a separate, explicitly-governed capability, not something this CDD authorizes even
implicitly.

## 14. Tenant / identity boundary (binding)

Discovery authorization uses the existing authenticated principal's identity/scopes only, exactly as every
prior gate's router-level `_authorize` pattern does — no new identity, tenant, service-identity, or
delegated-identity concept is introduced. `principal_id` is never persisted merely because an MCP interaction
occurred (RFC-015's tenant-origin discipline and this session's own "preserve existing identity semantics"
principle are both preserved).

## 15. Authorization semantics (binding)

A dedicated, new scope literal (exact string reserved for Artifact Authorization, following the established
`<capability-area>:<verb>` convention, e.g. `mcp-connector:read`) gates discovery; the same or a second
dedicated scope gates the one protocol-conformance invocation (§8, §12, §17). Holding this invocation-gating
scope authorizes only the deterministic, test-only protocol round trip described in §12 — it is an ordinary API
access scope, structurally identical to every other router's own scope check in this repository, and is never,
under any interpretation, a Gate R "Execution Authorization" grant; it carries no eligibility check, no
approval step, and no provenance record (§12). Authorization is checked before the catalog is filtered and
returned (§9) — no unauthorized principal ever receives a populated or partially-populated tool listing.

## 16. Failure taxonomy (binding structure, exact codes reserved for Artifact Authorization)

Missing/invalid authentication → existing Gate E behavior, reused. Missing required scope → existing
`AUTHORIZATION_SCOPE_REQUIRED`-style pattern, reused; capability remains invisible (§9), never merely rejected.
Malformed catalog entry (a Gate-Q-owned static-catalog integrity issue) → fails closed, treated as if the entry
did not exist. MCP initialization failure, protocol incompatibility, capability-discovery failure, malformed
tool metadata/schema, transport failure, timeout, and malformed external response are all **Gate-Q-owned
service/connector failures** — none of them may ever be represented as if they widened capability visibility (a
failed or unavailable connector must never fail *open*). No governed CTEC semantic failure category applies,
since this CDD's scope never touches Gate I/H4/Gate N/Gate O.

## 17. Deterministic closure proof (binding)

Two proofs, both required:

```
Authorized Principal -> Governed Discovery -> Visible Authorized Tool -> MCP Client
    -> Deterministic Local MCP Server -> Tool Discovery / Metadata
```
```
Unauthorized Principal -> Governed Discovery -> Capability Invisible
```

plus one protocol-conformance tool invocation against the same deterministic local server (§8, §12), explicitly
and structurally distinguished from any Gate R business-action execution: no eligibility check, no approval
step, no durable provenance, result discarded/asserted-only.

## 18. Determinism boundary (binding)

The tool/connector catalog, discovery-authorization outcome, and identity/tenant derivation must be fully
deterministic. The deterministic local MCP server's own responses must be fixed and reproducible for test
purposes. No real external MCP server's non-deterministic behavior is in scope for v1's proof.

## 19. Persistence / migration boundary (binding)

**Zero new persistence. Zero migration.** Existing `SecurityAuditService`/`ApiSecurityAuditRepository`
(CDD-013) may be reused, unmodified, for authorization-denial and discovery-filtering audit events — this is
reuse of existing governed infrastructure, not a new Gate Q persistence authority.

## 20. API / frontend boundary (binding)

**No new REST API endpoint is authorized by this CDD's minimum proof** — the closure proof (§17) is achievable
entirely at the application-service/test layer, mirroring Gate L's own backend-only MVP precedent. **No
frontend artifact is authorized.**

## 21. Firewalls — future gates (binding, restated per Gate Q1)

**Gate R** (Governed Tool Execution): this CDD establishes no execution-eligibility, controlled-invocation, or
provenance mechanism; Gate R remains free to define all of it without any Gate Q rework. **Gate S** (Human
Approval): no consequential-action concept exists in this CDD to retrofit. **Gate V** (Governed Multi-Agent
Orchestration): the fail-closed, per-caller-filtered catalog (§9) is a clean primitive Gate V may later consume
for named, bounded-responsibility agents; this CDD makes no claim about and does not implement any Agent
Resolution Trace. **Gate U** (What-if Simulation): this CDD's untrusted-external-data boundary (§13) is exactly
what keeps Gate U's own non-authoritative requirement satisfiable. **Gate X** (UI/UX): no frontend surface
exists to unify or conflict with.

## 22. `connector_catalog.py` firewall (binding, restated per Q-D5)

`backend/app/domain/ontology/connector_catalog.py` is not modified, extended, imported by, depended upon by,
reinterpreted by, synchronized with, or merged with any Gate Q artifact.

## 23. Security invariants (binding, summary)

No cross-caller capability-existence leak (§9). No execution authority granted by discovery (§12). No untrusted
external data promoted to semantic truth (§13). No new identity/tenant mechanism (§14). No durable credential of
any kind (§10). No canonical ontology mutation of any kind — this CDD is entirely read/discovery-oriented,
touching no canonical table.

## 24. Test obligations

Positive: authorized principal sees exactly its own authorized tool(s) in discovery; protocol initialization
succeeds against the deterministic local server; the one protocol-conformance invocation completes and its
result is provably never persisted. Negative: unauthorized principal's discovery response contains zero trace
of the capability (not an empty-with-metadata response — a response indistinguishable from "no such capability
exists"); missing/invalid authentication rejected before any catalog access; malformed static-catalog entry
fails closed; simulated transport failure/timeout/malformed-response each fail closed without widening
visibility. Determinism: two discovery calls under identical principal/catalog state yield byte-identical
results.

## 25. Acceptance criteria

1. An authorized principal's discovery response contains only tools its own scopes authorize.
2. An unauthorized principal's discovery response is indistinguishable from a world where the capability does
   not exist.
3. The MCP client completes a full protocol round trip (initialize → discover → one conformance invocation)
   against the deterministic local server with a byte-identical result across repeated runs.
4. No code path in the Gate Q implementation writes to any persistence store.
5. `connector_catalog.py` passes unmodified, with zero behavior change, before and after Gate Q implementation.
6. No Gate I/H4/Gate N/Gate O/Ask CTEC production file requires any modification.

## 26. Non-claims

This CDD does not claim: any production-ready external MCP integration; any real credential/secret handling;
any execution authority (Gate R's own future claim); any human-approval capability (Gate S's); any agent
orchestration capability (Gate V's); any UI/UX surface (Gate X's); that external MCP data becomes ontology,
evidence, or semantic truth under any circumstance in this CDD's scope.

## 27. Artifact Authorization boundary

Deferred to Artifact Authorization: exact module/file names; exact scope literal(s); exact catalog entry
schema; exact test filenames; exact `AUTHORIZED_CHANGED_PATHS` entries (if any existing file requires a
minimal, mechanical change — none is currently expected, but this determination itself is reserved for AA
discovery, mirroring Gate O's own AA-discovery methodology).

## 28. Rollback

Reverting this CDD's eventual implementation removes a small number of new, self-contained files (application
service, catalog, MCP client wrapper, tests) with no existing-file rollback required, matching Gate O's own
`connector_catalog.py`-untouched, zero-write precedent.

## 29. Numbered architecture baseline determination

No new numbered architecture baseline is required, following the identical method every CDD since CDD-016 has
used: this CDD cites RFC-010/013/015 and CDD-013/025/026/027/028/029 unchanged, and is registered via
`architecture/INDEX.md`'s existing "Governed implementation work orders" table alone.

## 30. Authorization

This document reached FROZEN status via: Gate Q0 discovery (P0=0/P1=0/P2=0) → Gate Q1 Product Owner
architecture-decision resolution (Q-D1 through Q-D5, P0=0/P1=0/P2=0) → Gate Q2 CDD drafting → Gate Q3 Product
Owner final review and contract normalization (two P2 textual tightenings incorporated, P0=0/P1=0/P2=0 after
resolution) → Gate Q4 publication authorization, under which this document is published and frozen.

**Implementation remains unauthorized.** A separate, subsequent Artifact Authorization (Gate Q5) is required
before any file governed by this CDD may be created or modified, matching every prior CDD's identical
multi-step discipline in this lineage.
