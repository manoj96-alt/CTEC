from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import api_service, container, principal
from app.core.config import Settings
from app.core.dependency_container import Container
from app.main import create_app


class Audit:
    def record(self, **values: object) -> UUID:
        del values
        return uuid4()


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/supplier-risk/executions/00000000-0000-0000-0000-000000000001"
        )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_MISSING"


def test_replay_requires_recovery_role_even_with_scope() -> None:
    now = datetime.now(UTC)
    trusted = TrustedPrincipal(
        "principal",
        "tenant",
        ("supplier-risk:replay",),
        ("analyst",),
        "issuer",
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )
    app = create_app()
    app.dependency_overrides[principal] = lambda: trusted
    app.dependency_overrides[api_service] = lambda: object()
    app.dependency_overrides[container] = lambda: Container(
        Settings(), security_audit=Audit()  # type: ignore[arg-type]
    )
    request_id = uuid4()
    response = TestClient(app).post(
        f"/api/v1/supplier-risk/executions/{uuid4()}/replay",
        json={
            "request_identifier": str(request_id),
            "correlation_identifier": str(uuid4()),
            "reason": "recovery needed",
        },
        headers={"Idempotency-Key": str(request_id)},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "RECOVERY_ROLE_REQUIRED"


def test_x_user_does_not_authenticate() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/supplier-risk/executions/00000000-0000-0000-0000-000000000001",
            headers={"X-User": "admin"},
        )
    assert response.status_code == 401
