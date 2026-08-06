from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers["X-Request-ID"]


def test_root_health_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_config_exposes_only_public_values() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json() == {"environment": "development", "api_version": "v1"}
    assert "database_url" not in response.text


def test_version_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"name": "CTEC", "version": "0.1.0"}
