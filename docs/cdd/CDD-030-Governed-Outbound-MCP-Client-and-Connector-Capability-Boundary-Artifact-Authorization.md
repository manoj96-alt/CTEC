# CDD-030 — Governed Outbound MCP Client and Connector Capability Boundary — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `03a1d1bf2c09f6813c78bf3b1fdd18a4bde8d020`

## 1. Purpose

Enumerates exactly which repository artifacts Gate Q implementation may create or modify to satisfy frozen
CDD-030 — and nothing more. This document alone does not authorize implementation; a separate, subsequent
Product Owner implementation authorization remains required.

This record was produced through: discovery against the actual repository (Gate Q5, which traced every
proposed artifact to CDD-030's own text and confirmed no MCP SDK dependency exists anywhere in
`backend/pyproject.toml`), Product Owner review resolving the one open interpretive question (Gate Q6, Decision
Q5-D1 — a small, direct, deterministic stdlib-only protocol implementation is authorized; no MCP SDK, no new
third-party dependency), and explicit Product Owner approval of the reviewed contract, P0=0/P1=0/P2=0.

## 2. Implementation objective

Prove, entirely through a new, standalone, router-less application-layer MCP client, that CTEC can: (a) perform
fail-closed capability discovery, where an unauthorized principal's result is indistinguishable from the
capability not existing; (b) complete a real MCP protocol round trip (initialize → Tools discovery → one
protocol-conformance invocation) against a deterministic local test server; (c) do both without any durable
credential, any new persistence, any new dependency, any modification to `connector_catalog.py`, and without
establishing any Gate R execution-authorization, Gate S approval, or CTEC-as-MCP-server capability.

## 3. Exact artifact allowlist

CREATE:
- `backend/app/application/mcp_connector_catalog.py`
- `backend/app/application/mcp_client.py`
- `backend/app/tests/test_mcp_connector_catalog.py`
- `backend/app/tests/test_mcp_client.py`

MODIFY (exact change only, nothing else in the file):
- `backend/app/tests/test_runtime_architecture.py` — exactly one new, additive, comment-labeled Gate Q block in
  `AUTHORIZED_CHANGED_PATHS` listing exactly the 4 CREATE paths above. No unrelated architecture-test refactor.

```
AUTHORIZED_NEW    = 4
AUTHORIZED_CHANGE = 1
TOTAL IMPLEMENTATION SURFACE = 5
```

No 6th implementation path is authorized under any circumstance without a new, separate Product Owner decision.
There is no exception for a small, mechanical, convenient, formatting-only, test-only, configuration-only, or
otherwise "harmless" additional file.

## 4. Dependency contract (binding)

**No new dependency is authorized.** `backend/pyproject.toml` and any lockfile remain unchanged. The MCP client
uses only Python standard-library `subprocess` and `json` to implement a small, direct, deterministic
newline-delimited JSON-RPC round trip over a subprocess's stdin/stdout — exactly what MCP's own stdio transport
literally is. No MCP SDK, no third-party protocol library, no HTTP-based transport dependency of any kind.

## 5. Explicitly not required / not authorized

`backend/app/core/dependency_container.py` must remain unchanged — Gate Q v1 has no router and therefore no
`Container`-mediated dependency at all. `backend/app/main.py` must remain unchanged — no new REST endpoint is
authorized, so there is nothing to register. `keycloak/ctec-realm.json` must remain unchanged — no new
authentication mechanism exists to configure. `backend/app/tests/conftest.py` must remain unchanged — no shared
fixture beyond the deterministic local server defined inline in `test_mcp_client.py` is needed.
`SecurityAuditService`/`ApiSecurityAuditRepository` reuse is explicitly **not authorized for v1** (YAGNI —
CDD-030 permits but does not require it, and requiring it would force a forbidden `dependency_container.py`
touch for a proof that needs no durable audit record to satisfy its own acceptance criteria).

## 6. Module contracts

**`mcp_connector_catalog.py`**: `McpToolDefinition` — a frozen dataclass with exactly five fields:
`capability_id: str`, `tool_name: str`, `required_scope: str`, `description: str`,
`input_schema: Mapping[str, object]`. `MCP_CONNECTOR_CATALOG: tuple[McpToolDefinition, ...]` — exactly one
static entry for Gate Q v1. `authorized_catalog_for(principal: TrustedPrincipal) -> tuple[McpToolDefinition,
...]` — a fail-closed filter returning only entries whose `required_scope` is present in `principal.scopes`; no
persistence, no dynamic registration, no marketplace, no plugin framework, no UI catalog, no agent registry, no
synchronization with `connector_catalog.py` of any kind.

**`mcp_client.py`**: `McpClient` — constructed directly from two file-like stdin/stdout handles; no transport
abstraction/interface of any kind. Exactly three public methods: `initialize()` (protocol handshake);
`list_tools(principal: TrustedPrincipal)` (calls `authorized_catalog_for` first — capability disclosure is
always authorization-filtered before any protocol response is built); `call_tool(principal: TrustedPrincipal,
capability_id: str)` (the one protocol-conformance invocation, gated by the identical authorization boundary as
discovery — no separate or additional authorization concept). Neither method may introduce Gate R eligibility,
Gate R execution authorization, human approval, action provenance, or durable execution state of any kind.

**Scope literal**: `mcp-connector:read` — the sole Gate Q scope, gating both discovery and the one
protocol-conformance invocation. This scope authorizes discovery permission only; it must never be interpreted
as, and this Artifact Authorization does not create, any Gate R business-execution authorization, human
approval, or governed business action.

**Deterministic local server**: exists only inside `backend/app/tests/test_mcp_client.py` — test-only, local,
using the approved deterministic stdio transport, requiring no credential, requiring no network egress,
exposing fixed deterministic tool metadata/schema, returning a fixed deterministic conformance result, with no
business side effect, lifecycle-bounded to the tests that use it. It is never imported by, referenced from, or
reachable via any production file, and its existence does not establish CTEC as an MCP server under Q-D1.

## 7. Persistence / migration / API / frontend / provider / MCP-scope (binding)

Migration: **NONE**. New persistence: **NONE**. New REST API endpoint: **NONE**. Frontend: **NONE**. Real model
provider: **NOT AUTHORIZED**. Real external MCP server: **NOT AUTHORIZED**. MCP Resources: **NOT AUTHORIZED**.
MCP Prompts: **NOT AUTHORIZED**. A second transport: **NOT AUTHORIZED**. New third-party dependency: **NOT
AUTHORIZED** (§4). Gate U, Gate R, Gate S, Gate V, or Gate X implementation of any kind: **NOT AUTHORIZED**.

## 8. Forbidden implementation areas

`backend/app/domain/ontology/connector_catalog.py`; every Gate O production file
(`information_element_context_resolution.py`, `backend/app/api/information_element_context/*`); every Gate
N/I/H4 production file (`information_element_context_availability.py`, `semantic_coverage_evaluation.py`,
`information_element_evidence_availability.py`); every Ask CTEC production/frontend file
(`ontology_copilot_api.py`, `backend/app/api/ontology_copilot/*`); any `frontend/*` file; any migration file;
`keycloak/ctec-realm.json`; `backend/app/core/dependency_container.py`; `backend/app/main.py`; CDD-030; every
other frozen CDD/AA; released architecture.

## 9. Test obligations

Exactly the 12 items established at Gate Q6, realized across the two authorized test files: (1) authorized
capability discovery; (2) unauthorized capability invisibility; (3) deterministic repeated discovery; (4) MCP
initialization; (5) deterministic Tools discovery; (6) the one protocol-conformance invocation; (7) malformed
catalog entry fails closed; (8) deterministic transport failure fails closed; (9) timeout fails closed; (10)
malformed response fails closed; (11) no persistence side effect (structural — no session/repository exists to
write with); (12) `connector_catalog.py` unchanged (verified by diff, not a runtime assertion). No
production-grade MCP integration test infrastructure — exactly these 12, nothing broader.

## 10. Implementation stop conditions

Implementation must STOP and return to Product Owner review if: `origin/main` moves from the approved
implementation baseline before implementation branch creation; CDD-030 changes; this Artifact Authorization
changes; any §3 path proves insufficient; a 6th implementation file is required; any §8 forbidden file appears
necessary; persistence, migration, API, frontend, authentication, Keycloak, real MCP server, real external
connector, a second transport, credentials, or a new dependency becomes necessary; the scope literal, catalog
schema, or MCP client boundary would need to change; CI cannot pass without scope expansion. No exception for a
"small harmless extra file." Total implementation surface is exactly 5 files; no 6th is authorized under any
circumstance without a new Product Owner decision.

## 11. Authorization

This Artifact Authorization is **approved for publication**, reached via Gate Q5 (discovery/drafting) → Gate Q6
(Product Owner review, Decision Q5-D1 resolved, P0=0/P1=0/P2=0) → Gate Q7 (this publication turn).
**Publication/freeze of this Artifact Authorization does NOT itself authorize Gate Q implementation.** A
separate, subsequent Product Owner implementation authorization (Gate Q8) is required before any file in §3 may
be created or modified — matching every prior CDD's identical multi-step discipline in this lineage (CDD-025,
CDD-026, CDD-027, CDD-028, CDD-029).
