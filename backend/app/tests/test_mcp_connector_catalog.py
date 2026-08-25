"""Tests for Gate Q's static tool/connector catalog and fail-closed
discovery-authorization filter (CDD-030 Sec9 [Q-D3], Sec11 [Q-D5]; Gate Q
Artifact Authorization v1.0 Sec6, Sec9)."""

from datetime import UTC, datetime, timedelta

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.mcp_connector_catalog import (
    MCP_CONNECTOR_CATALOG,
    MCP_CONNECTOR_READ_SCOPE,
    McpToolDefinition,
    authorized_catalog_for,
)

NOW = datetime.now(UTC)


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


def test_catalog_contains_exactly_one_entry_with_expected_fields() -> None:
    assert len(MCP_CONNECTOR_CATALOG) == 1
    entry = MCP_CONNECTOR_CATALOG[0]
    assert entry.required_scope == MCP_CONNECTOR_READ_SCOPE
    assert entry.capability_id
    assert entry.tool_name
    assert entry.description
    assert isinstance(entry.input_schema, dict)


def test_authorized_principal_sees_the_one_catalog_entry() -> None:
    principal = _principal(scopes=(MCP_CONNECTOR_READ_SCOPE,))
    assert authorized_catalog_for(principal) == MCP_CONNECTOR_CATALOG


def test_unauthorized_principal_sees_no_capability_metadata() -> None:
    principal = _principal(scopes=())
    assert authorized_catalog_for(principal) == ()


def test_unrelated_scope_does_not_leak_capability() -> None:
    principal = _principal(scopes=("entity-resolution:read",))
    assert authorized_catalog_for(principal) == ()


def test_repeated_discovery_for_identical_principal_is_deterministic() -> None:
    principal = _principal(scopes=(MCP_CONNECTOR_READ_SCOPE,))
    first = authorized_catalog_for(principal)
    second = authorized_catalog_for(principal)
    assert first == second


def test_malformed_catalog_entry_is_excluded_rather_than_crashing_or_leaking() -> None:
    malformed_catalog = (
        McpToolDefinition(
            capability_id="malformed",
            tool_name="malformed_tool",
            required_scope="not-a-real-convention-following-scope",
            description="",
            input_schema={},
        ),
    )
    # This principal legitimately holds the real Gate Q scope -- proving the
    # malformed entry's own distinct, bogus required_scope is what excludes
    # it, not merely an absence of any authorization on the caller's side.
    principal = _principal(scopes=(MCP_CONNECTOR_READ_SCOPE,))
    assert authorized_catalog_for(principal, catalog=malformed_catalog) == ()
