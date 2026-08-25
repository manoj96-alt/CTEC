"""Gate Q -- Governed Outbound MCP Client (CDD-030 Sec8 [Q-D2], Sec12,
Sec17; Gate Q Artifact Authorization v1.0 Sec6). Implements the smallest
deterministic MCP protocol round trip authorized by CDD-030: initialize ->
Tools discovery -> one protocol-conformance invocation, over exactly one
deterministic local transport (two file-like stdin/stdout handles). No
transport abstraction/interface, no Resources, no Prompts, no
retry/orchestration framework, no credential handling, no persistence. The
conformance invocation is explicitly not a Gate R business action: no
eligibility check, no approval step, no provenance record."""

from __future__ import annotations

import json
import select
from collections.abc import Mapping
from dataclasses import dataclass
from typing import IO, Any

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.mcp_connector_catalog import McpToolDefinition, authorized_catalog_for


class McpProtocolError(Exception):
    """Raised for any transport/protocol failure. Fails closed -- never
    silently widens capability visibility or fabricates a result
    (CDD-030 Sec16)."""


@dataclass(frozen=True, slots=True)
class McpToolDiscoveryResult:
    tools: tuple[McpToolDefinition, ...]


@dataclass(frozen=True, slots=True)
class McpToolInvocationResult:
    capability_id: str
    content: tuple[Mapping[str, object], ...]


class McpClient:
    """Constructed directly from two file-like handles representing the
    approved deterministic stdio transport -- no transport interface, no
    pluggable/generalized transport framework (CDD-030 Sec8)."""

    def __init__(
        self,
        *,
        stdin: IO[bytes],
        stdout: IO[bytes],
        timeout_seconds: float = 5.0,
    ) -> None:
        self._stdin = stdin
        self._stdout = stdout
        self._timeout_seconds = timeout_seconds
        self._next_id = 1

    def initialize(self) -> Mapping[str, object]:
        return self._request("initialize", {})

    def list_tools(self, *, principal: TrustedPrincipal) -> McpToolDiscoveryResult:
        authorized = authorized_catalog_for(principal)
        if not authorized:
            # Fail closed (CDD-030 Sec9): an unauthorized/under-scoped caller
            # receives an empty discovery result, structurally
            # indistinguishable from "no capability exists" -- the protocol
            # request is never even issued.
            return McpToolDiscoveryResult(tools=())
        response = self._request("tools/list", {})
        discovered = response.get("tools")
        if not isinstance(discovered, list):
            raise McpProtocolError("malformed response")
        discovered_names = {
            tool["name"] for tool in discovered if isinstance(tool, dict) and "name" in tool
        }
        matched = tuple(
            definition for definition in authorized if definition.tool_name in discovered_names
        )
        return McpToolDiscoveryResult(tools=matched)

    def call_tool(
        self, *, principal: TrustedPrincipal, capability_id: str
    ) -> McpToolInvocationResult:
        authorized = authorized_catalog_for(principal)
        definition = next(
            (entry for entry in authorized if entry.capability_id == capability_id), None
        )
        if definition is None:
            # Fail closed (CDD-030 Sec9): never confirms whether an
            # unauthorized or unknown capability_id exists at all.
            raise McpProtocolError("capability not available")
        response = self._request("tools/call", {"name": definition.tool_name, "arguments": {}})
        content = response.get("content")
        if not isinstance(content, list):
            raise McpProtocolError("malformed response")
        return McpToolInvocationResult(capability_id=capability_id, content=tuple(content))

    def _request(self, method: str, params: Mapping[str, object]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        try:
            self._stdin.write((payload + "\n").encode("utf-8"))
            self._stdin.flush()
        except (BrokenPipeError, ValueError) as exc:
            raise McpProtocolError("transport failure") from exc

        ready, _, _ = select.select([self._stdout], [], [], self._timeout_seconds)
        if not ready:
            raise McpProtocolError("transport timeout")

        line = self._stdout.readline()
        if not line:
            raise McpProtocolError("transport failure")
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise McpProtocolError("malformed response") from exc
        if not isinstance(message, dict) or message.get("id") != request_id:
            raise McpProtocolError("malformed response")
        if "error" in message:
            raise McpProtocolError(str(message["error"]))
        result = message.get("result")
        if not isinstance(result, dict):
            raise McpProtocolError("malformed response")
        return result
