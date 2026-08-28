"""Focused Gate W (CDD-038) test suite for the Governed API Version
Declaration endpoint. `test_declared_versions_match_real_route_surface`
is the CDD-038 SS17 mechanical route/registry-consistency invariant: it
derives evidence from the real, running `create_app()` route table --
never a hardcoded expected-path list -- so a future route addition under
an unregistered version prefix fails this test automatically, and a
registry entry with zero backing routes fails it too."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.api.api_versions.router import SUPPORTED_API_VERSIONS, ApiVersionState
from app.main import create_app

_VERSION_PREFIX = re.compile(r"^/api/(v\d+)/")


def test_get_api_versions_returns_200() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/versions")
    assert response.status_code == 200


def test_response_shape_is_exact() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/versions")
    assert response.json() == {"versions": [{"version": "v1", "state": "SUPPORTED"}]}


def test_declared_version_is_v1() -> None:
    with TestClient(create_app()) as client:
        body = client.get("/api/versions").json()
    assert [entry["version"] for entry in body["versions"]] == ["v1"]


def test_declared_state_is_supported() -> None:
    with TestClient(create_app()) as client:
        body = client.get("/api/versions").json()
    assert [entry["state"] for entry in body["versions"]] == ["SUPPORTED"]


def test_no_authentication_required() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/versions")
    assert response.status_code != 401
    assert response.status_code != 403


def test_declaration_is_deterministic_across_calls() -> None:
    with TestClient(create_app()) as client:
        first = client.get("/api/versions").json()
        second = client.get("/api/versions").json()
    assert first == second


def test_no_unexpected_version_is_declared() -> None:
    assert len(SUPPORTED_API_VERSIONS) == 1
    assert SUPPORTED_API_VERSIONS[0].version == "v1"
    assert SUPPORTED_API_VERSIONS[0].state == ApiVersionState.SUPPORTED


def test_declared_versions_match_real_route_surface() -> None:
    """CDD-038 SS17: (a) every declared version has at least one real route
    under /api/{version}/; (b) no route exists under an undeclared
    /api/v{N}/ prefix. Evidence is derived from the real, running
    application's own OpenAPI schema (`app.openapi()["paths"]`) -- FastAPI's
    stable, public, version-independent flattened route enumeration -- never
    a hardcoded expected-path list. `app.routes` is deliberately not walked
    directly: FastAPI internally represents an included router as an opaque
    wrapper object across versions, so manual traversal is not a reliable
    cross-version route source."""
    app = create_app()
    route_paths = list(app.openapi()["paths"].keys())

    versioned_prefixes_in_routes = {
        match.group(1) for path in route_paths if (match := _VERSION_PREFIX.match(path)) is not None
    }
    declared_versions = {entry.version for entry in SUPPORTED_API_VERSIONS}

    assert versioned_prefixes_in_routes, "no /api/v{N}/ routes found -- test setup is broken"
    for declared in declared_versions:
        assert any(
            path.startswith(f"/api/{declared}/") for path in route_paths
        ), f"declared version {declared!r} has no backing route"
    for prefix in versioned_prefixes_in_routes:
        assert (
            prefix in declared_versions
        ), f"route exists under undeclared version prefix {prefix!r}"


def test_no_post_method_exposed() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/versions")
    assert response.status_code == 405


def test_no_put_method_exposed() -> None:
    with TestClient(create_app()) as client:
        response = client.put("/api/versions")
    assert response.status_code == 405


def test_no_patch_method_exposed() -> None:
    with TestClient(create_app()) as client:
        response = client.patch("/api/versions")
    assert response.status_code == 405


def test_no_delete_method_exposed() -> None:
    with TestClient(create_app()) as client:
        response = client.delete("/api/versions")
    assert response.status_code == 405
