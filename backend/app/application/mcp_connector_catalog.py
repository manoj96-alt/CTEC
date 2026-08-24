"""Gate Q -- Governed static tool/connector catalog (CDD-030 Sec9 [Q-D3],
Sec11 [Q-D5]; Gate Q Artifact Authorization v1.0 Sec6). A small,
statically-defined, Gate-Q-owned structure -- entirely separate from
`app.domain.ontology.connector_catalog`, which is Ontology Studio display
metadata, ungoverned by any CDD, and never imported, depended upon,
reinterpreted, synchronized with, or merged with this module. No
persistence, no dynamic registration, no marketplace, no plugin framework,
no UI catalog, no agent registry."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.api.supplier_risk.authentication import TrustedPrincipal

MCP_CONNECTOR_READ_SCOPE = "mcp-connector:read"


@dataclass(frozen=True, slots=True)
class McpToolDefinition:
    capability_id: str
    tool_name: str
    required_scope: str
    description: str
    input_schema: Mapping[str, object]


MCP_CONNECTOR_CATALOG: tuple[McpToolDefinition, ...] = (
    McpToolDefinition(
        capability_id="gate-q-protocol-conformance-echo",
        tool_name="protocol_conformance_echo",
        required_scope=MCP_CONNECTOR_READ_SCOPE,
        description=(
            "Deterministic, test-only capability proving Gate Q's MCP client "
            "completes a full protocol round trip (CDD-030 Sec17). Never a "
            "governed business action."
        ),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
)


def authorized_catalog_for(
    principal: TrustedPrincipal,
    *,
    catalog: tuple[McpToolDefinition, ...] = MCP_CONNECTOR_CATALOG,
) -> tuple[McpToolDefinition, ...]:
    """Fail-closed filter (CDD-030 Sec9 [Q-D3]): returns only the catalog
    entries whose `required_scope` the principal actually holds. An
    unauthorized principal receives an empty tuple -- structurally
    indistinguishable from "no capability exists", never a partially
    redacted or error-annotated result."""
    return tuple(entry for entry in catalog if entry.required_scope in principal.scopes)
