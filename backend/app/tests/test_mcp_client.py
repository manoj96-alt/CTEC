"""Tests for Gate Q's MCP client (CDD-030 Sec8 [Q-D2], Sec12, Sec17; Gate Q
Artifact Authorization v1.0 Sec6, Sec9). The deterministic local MCP
server defined below is TEST INFRASTRUCTURE ONLY: local, deterministic,
credential-free, network-egress-free, side-effect-free, lifecycle-bounded
to the tests that spawn it. It is never imported by, referenced from, or
reachable via any production file, and its existence does not establish
CTEC as an MCP server (Q-D1)."""

from __future__ import annotations

import ast
import inspect
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

import app.application.mcp_client as mcp_client_module
import app.application.mcp_connector_catalog as mcp_catalog_module
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.mcp_client import McpClient, McpProtocolError
from app.application.mcp_connector_catalog import MCP_CONNECTOR_CATALOG, MCP_CONNECTOR_READ_SCOPE

NOW = datetime.now(UTC)

_TOOL = MCP_CONNECTOR_CATALOG[0]

# A tiny, fully deterministic, test-only MCP server: reads one
# newline-delimited JSON-RPC request per line from stdin, writes one fixed
# response per line to stdout. Never a real external service, never
# production code, never imported by anything under backend/app/application
# or backend/app/api.
_GOOD_SERVER_SCRIPT = f"""
import json
import sys

TOOL_NAME = {_TOOL.tool_name!r}
TOOL_DESCRIPTION = {_TOOL.description!r}
TOOL_SCHEMA = {dict(_TOOL.input_schema)!r}

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    request = json.loads(line)
    method = request["method"]
    request_id = request["id"]
    if method == "initialize":
        result = {{"protocolVersion": "2024-11-05", "serverInfo": {{"name": "gate-q-deterministic-test-server"}}}}
    elif method == "tools/list":
        result = {{"tools": [{{"name": TOOL_NAME, "description": TOOL_DESCRIPTION, "inputSchema": TOOL_SCHEMA}}]}}
    elif method == "tools/call":
        result = {{"content": [{{"type": "text", "text": "deterministic-conformance-result"}}]}}
    else:
        result = {{}}
    response = {{"jsonrpc": "2.0", "id": request_id, "result": result}}
    sys.stdout.write(json.dumps(response) + chr(10))
    sys.stdout.flush()
"""

_MALFORMED_RESPONSE_SERVER_SCRIPT = """
import sys
for line in sys.stdin:
    if not line.strip():
        continue
    sys.stdout.write("not-json" + chr(10))
    sys.stdout.flush()
    break
"""

_SILENT_SERVER_SCRIPT = """
import sys
import time
sys.stdin.readline()
time.sleep(60)
"""

_EXITS_IMMEDIATELY_SERVER_SCRIPT = """
import sys
sys.exit(0)
"""


@contextmanager
def _spawn_server(script: str) -> Iterator[subprocess.Popen[bytes]]:
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield process
    finally:
        process.kill()
        process.wait(timeout=5)


def _principal(*, scopes: tuple[str, ...] = ()) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id="tenant-a",
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def test_initialize_succeeds_against_the_deterministic_local_server() -> None:
    with _spawn_server(_GOOD_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout)
        result = client.initialize()
        assert result["serverInfo"] == {"name": "gate-q-deterministic-test-server"}


def test_authorized_principal_discovers_the_expected_tool() -> None:
    with _spawn_server(_GOOD_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout)
        client.initialize()
        principal = _principal(scopes=(MCP_CONNECTOR_READ_SCOPE,))
        discovery = client.list_tools(principal=principal)
        assert discovery.tools == (_TOOL,)


def test_unauthorized_principal_discovers_no_capability() -> None:
    with _spawn_server(_GOOD_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout)
        client.initialize()
        principal = _principal(scopes=())
        discovery = client.list_tools(principal=principal)
        assert discovery.tools == ()


def test_repeated_discovery_is_deterministic() -> None:
    with _spawn_server(_GOOD_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout)
        client.initialize()
        principal = _principal(scopes=(MCP_CONNECTOR_READ_SCOPE,))
        first = client.list_tools(principal=principal)
        second = client.list_tools(principal=principal)
        assert first == second


def test_protocol_conformance_invocation_returns_fixed_deterministic_result() -> None:
    with _spawn_server(_GOOD_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout)
        client.initialize()
        principal = _principal(scopes=(MCP_CONNECTOR_READ_SCOPE,))
        result = client.call_tool(principal=principal, capability_id=_TOOL.capability_id)
        assert result.capability_id == _TOOL.capability_id
        assert result.content == ({"type": "text", "text": "deterministic-conformance-result"},)


def test_unauthorized_invocation_fails_closed_without_confirming_existence() -> None:
    with _spawn_server(_GOOD_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout)
        client.initialize()
        principal = _principal(scopes=())
        with pytest.raises(McpProtocolError):
            client.call_tool(principal=principal, capability_id=_TOOL.capability_id)


def test_transport_failure_when_server_exits_immediately_fails_closed() -> None:
    with _spawn_server(_EXITS_IMMEDIATELY_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout, timeout_seconds=2.0)
        with pytest.raises(McpProtocolError):
            client.initialize()


def test_timeout_when_server_never_responds_fails_closed() -> None:
    with _spawn_server(_SILENT_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout, timeout_seconds=0.5)
        with pytest.raises(McpProtocolError):
            client.initialize()


def test_malformed_response_fails_closed() -> None:
    with _spawn_server(_MALFORMED_RESPONSE_SERVER_SCRIPT) as process:
        assert process.stdin is not None
        assert process.stdout is not None
        client = McpClient(stdin=process.stdin, stdout=process.stdout, timeout_seconds=2.0)
        with pytest.raises(McpProtocolError):
            client.initialize()


def test_production_modules_have_no_persistence_or_connector_catalog_dependency() -> None:
    # Exact forbidden import targets -- not bare substrings, since Gate Q's
    # own module name (mcp_connector_catalog) legitimately contains the
    # substring "connector_catalog" without being the forbidden
    # app.domain.ontology.connector_catalog module.
    forbidden_exact = (
        "app.domain.ontology.connector_catalog",
        "app.core.dependency_container",
        "sqlalchemy",
    )
    forbidden_substrings = ("Session", "Repository")
    for module in (mcp_client_module, mcp_catalog_module):
        tree = ast.parse(inspect.getsource(module))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
                names.update(alias.name for alias in node.names)
        for forbidden in forbidden_exact:
            assert not any(
                name == forbidden or name.startswith(forbidden + ".") for name in names
            ), f"{module.__name__} imports forbidden {forbidden}"
        for forbidden in forbidden_substrings:
            assert not any(
                forbidden in name for name in names
            ), f"{module.__name__} imports forbidden {forbidden}"
