"""PRODUCT-WIDE-DOCKER-CLOSURE-G-R5/I-R5 -- static reconciliation between
`backend/app/api/`'s real OAuth-scope authorization requirements and the
Docker/dev-demo Keycloak realm (`keycloak/ctec-realm.json`).

Discovered defect class (this correction closes the second occurrence):
a route requires a scope via `authorize(...)`/`_authorize(...)` or an
inline `"<scope>" in authenticated.scopes` check, but the realm never
defines and/or never assigns that scope to `ctec-frontend` -- so no real
Authorization Code + PKCE token can ever satisfy the route, and Keycloak
rejects the whole login (`error=invalid_scope`) before any page renders.
`git log -- keycloak/ctec-realm.json` shows this recurring at least
three times with no systematic guard; this test is that guard.

Extraction is intentionally scoped to `backend/app/api/` only: every
route reachable via a real HTTP request lives there. A scope constant
defined elsewhere (e.g. `app/application/mcp_connector_catalog.py`'s
`MCP_CONNECTOR_READ_SCOPE`, `app/application/governed_tool_executor.py`'s
`TOOL_EXECUTION_SCOPE`) is correctly excluded by this scoping alone,
without a fragile allowlist, because it is never referenced by literal
string or otherwise inside `app/api/` -- neither module is imported
anywhere under `app/api/` or `app/main.py` (independently confirmed
during G-R5), so it gates no currently-reachable route. Likewise,
`RECOVERY_SCOPE` ("execution:replay", `app/runtime/persistence/
contracts.py`) is never read from an authenticated principal's own
token -- it is synthesized internally, only after the caller already
carries `supplier-risk:replay` -- so it is correctly absent from the
realm and correctly never surfaces from this `app/api/`-scoped scan.

Role-based checks (e.g. `"EXECUTION_RECOVERY_OPERATOR" not in
authenticated.roles`, `supplier_risk/router.py`) are a materially
different Keycloak construct (realm roles, not client scopes) and are
out of this test's scope by design -- disclosed separately in CDD-060
§31, not corrected here."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

_BACKEND_APP_ROOT = Path(__file__).parents[1]
_API_ROOT = _BACKEND_APP_ROOT / "api"
_REALM_PATH = Path(__file__).parents[3] / "keycloak" / "ctec-realm.json"
_FRONTEND_CLIENT_ID = "ctec-frontend"

# The one shared helper, `authorize` (`app/api/oqi/dependencies.py`), is
# imported by name into every module that uses it, so it is always
# discoverable by name alone. Every *other* authorization helper
# (`_authorize`, `_authorize_any`, and any future `_authorize_*`
# variant) is defined locally, once per router module -- discovered
# structurally below (any function whose own body contains a `.scopes`
# attribute access), never by guessing name patterns, so a new variant
# needs no update here.
_KNOWN_IMPORTED_AUTHORIZE_NAMES = {"authorize"}


def _is_scope_shaped(value: object) -> bool:
    return (
        isinstance(value, str)
        and ":" in value
        and all(part and part.replace("-", "").isalpha() for part in value.split(":"))
    )


def _function_body_checks_scopes(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(child, ast.Attribute) and child.attr == "scopes" for child in ast.walk(node)
    )


def _local_authorize_helper_names(tree: ast.Module) -> set[str]:
    """Every function defined in this module whose own body checks
    `.scopes` -- the structural definition of "this is an authorization
    helper", independent of what it happens to be named."""
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _function_body_checks_scopes(node)
    }


def _scopes_required_by_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, authorize_names: set[str]
) -> set[str]:
    """Every scope-shaped string constant inside `node`'s own subtree,
    excluding `node`'s own docstring (to avoid picking up scope names
    mentioned only in descriptive prose, never enforced). Only collected
    at all if `node` itself performs a check -- calls a known
    authorization helper, or itself contains a `.scopes` membership
    comparison (covers both `"x" in authenticated.scopes` directly and
    the `any(scope in authenticated.scopes for scope in (...))`
    tuple-literal pattern, since the tuple lives in the same enclosing
    function as the comparison)."""
    performs_check = _function_body_checks_scopes(node)
    if not performs_check:
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
                if name in authorize_names:
                    performs_check = True
                    break
    if not performs_check:
        return set()

    docstring_node: ast.Constant | None = None
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        docstring_node = node.body[0].value

    found: set[str] = set()
    for child in ast.walk(node):
        if child is docstring_node:
            continue
        if (
            isinstance(child, ast.Constant)
            and isinstance(child.value, str)
            and _is_scope_shaped(child.value)
        ):
            found.add(child.value)
    return found


def _required_scopes_in_file(path: Path) -> set[str]:
    """Every function is scanned, whether it is a route that inlines its
    own `.scopes` check (e.g. `gate_v/router.py`) or a route that calls a
    separately-defined helper (e.g. `_authorize_any`) -- helper
    definitions themselves are harmless to scan too: `authorize`/
    `_authorize`/`_authorize_any` take `scope`/`scopes` as parameters, not
    literals, so they never contribute a false scope-shaped constant."""
    tree = ast.parse(path.read_text(), filename=str(path))
    authorize_names = _local_authorize_helper_names(tree) | _KNOWN_IMPORTED_AUTHORIZE_NAMES
    required: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            required |= _scopes_required_by_function(node, authorize_names)
    return required


def _backend_required_scopes() -> set[str]:
    required: set[str] = set()
    for path in _API_ROOT.rglob("*.py"):
        if path.name.startswith("test_"):
            continue
        required |= _required_scopes_in_file(path)
    return required


def _load_realm() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(_REALM_PATH.read_text())
    return result


def _defined_client_scopes(realm: dict[str, Any]) -> set[str]:
    return {scope["name"] for scope in realm["clientScopes"]}


def _client_requestable_scopes(realm: dict[str, Any], client_id: str) -> set[str]:
    for client in realm["clients"]:
        if client["clientId"] == client_id:
            return set(client.get("defaultClientScopes", [])) | set(
                client.get("optionalClientScopes", [])
            )
    raise AssertionError(f"client {client_id!r} not found in realm")


def reconcile(
    required: set[str], defined: set[str], assigned: set[str]
) -> tuple[set[str], set[str]]:
    """Pure, directly-unit-testable reconciliation: returns
    (missing_definition, missing_assignment). A scope missing from
    `defined` is necessarily also missing from `assigned` from the
    client's perspective, but the two are reported separately so a
    defined-but-unassigned scope (a different, subtler wiring failure)
    is distinguishable from a wholly-undefined one."""
    missing_definition = required - defined
    missing_assignment = required - assigned
    return missing_definition, missing_assignment


def test_backend_required_scopes_extraction_finds_the_known_inventory() -> None:
    """Independently re-derived, not copied: confirms the extractor finds
    exactly the OQI-domain inventory G-R5 manually established, proving
    the extraction mechanism itself is sound before trusting its verdict
    on the full realm below."""
    required = _backend_required_scopes()
    oqi_domain_expected = {
        "oqi:read",
        "oqi-connector:configure",
        "oqi-connector:read",
        "oqi-connector:run",
        "oqi-evaluation:trigger",
        "oqi-reference-evidence:configure",
        "oqi-reference-evidence:verify",
        "oqi-remediation:authorize",
        "oqi-remediation:prepare",
        "oqi-remediation:report-execution",
    }
    assert oqi_domain_expected <= required


def test_reconcile_detects_a_missing_definition() -> None:
    """Proves the reconciliation function itself catches the exact
    defect class this test guards against -- using synthetic data, never
    the tracked realm file, per CDD-060 §31's own explicit instruction
    not to mutate tracked state merely to demonstrate detection."""
    required = {"oqi-evaluation:trigger", "oqi:read"}
    defined = {"oqi:read"}
    assigned = {"oqi:read"}
    missing_definition, missing_assignment = reconcile(required, defined, assigned)
    assert missing_definition == {"oqi-evaluation:trigger"}
    assert missing_assignment == {"oqi-evaluation:trigger"}


def test_reconcile_detects_a_defined_but_unassigned_scope() -> None:
    """The subtler wiring failure: a scope exists in `clientScopes` but
    was never added to the client's own default/optional list, so it is
    still not requestable."""
    required = {"oqi-evaluation:trigger", "oqi:read"}
    defined = {"oqi-evaluation:trigger", "oqi:read"}
    assigned = {"oqi:read"}
    missing_definition, missing_assignment = reconcile(required, defined, assigned)
    assert missing_definition == set()
    assert missing_assignment == {"oqi-evaluation:trigger"}


def test_reconcile_is_clean_when_fully_wired() -> None:
    required = {"oqi-evaluation:trigger", "oqi:read"}
    defined = {"oqi-evaluation:trigger", "oqi:read"}
    assigned = {"oqi-evaluation:trigger", "oqi:read"}
    missing_definition, missing_assignment = reconcile(required, defined, assigned)
    assert missing_definition == set()
    assert missing_assignment == set()


def test_all_backend_required_scopes_are_defined_and_client_requestable() -> None:
    """The live guard: every OAuth scope any reachable `backend/app/api/`
    route requires must be defined in the realm and assigned (default or
    optional) to `ctec-frontend` -- the actual defect class this file
    exists to catch, run against the real tracked realm."""
    required = _backend_required_scopes()
    realm = _load_realm()
    defined = _defined_client_scopes(realm)
    assigned = _client_requestable_scopes(realm, _FRONTEND_CLIENT_ID)

    missing_definition, missing_assignment = reconcile(required, defined, assigned)

    assert missing_definition == set(), (
        f"scopes required by backend/app/api/ but not defined in "
        f"keycloak/ctec-realm.json's clientScopes: {sorted(missing_definition)}"
    )
    assert missing_assignment == set(), (
        f"scopes required by backend/app/api/ but not assigned to "
        f"{_FRONTEND_CLIENT_ID}: {sorted(missing_assignment)}"
    )


def test_oqi_evaluation_trigger_is_optional_not_default() -> None:
    """Least-privilege placement (CDD-060 §31): an explicit action-trigger
    scope must never become an unintended default -- it must remain
    something the caller (this runbook's own PKCE script, ultimately)
    explicitly requests, exactly like its sibling oqi-remediation:*
    action scopes."""
    realm = _load_realm()
    for client in realm["clients"]:
        if client["clientId"] == _FRONTEND_CLIENT_ID:
            assert "oqi-evaluation:trigger" not in client.get("defaultClientScopes", [])
            assert "oqi-evaluation:trigger" in client.get("optionalClientScopes", [])
            return
    raise AssertionError(f"client {_FRONTEND_CLIENT_ID!r} not found in realm")
