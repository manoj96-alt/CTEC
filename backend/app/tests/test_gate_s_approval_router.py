"""Router-level tests for the Gate S Governed Human Approval API (CDD-036
§27; Gate S Artifact Authorization §7). These exercise authentication,
scope authorization (including that request/decide scopes never imply
each other), and tenant enforcement purely through FastAPI dependency
overrides -- no database is required. Real concurrency/persistence
behavior is proven separately, against real Postgres, in
`test_gate_s_approval_postgres.py`."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.gate_s.dependencies import gate_s_approval_repository, gate_s_approval_service
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.application.gate_s_approval_service import GateSApprovalError
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.gate_s.approval import ACTION_ID, ApprovalStatus
from app.main import create_app

NOW = datetime.now(UTC)


class Audit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, **values: object) -> UUID:
        self.events.append(values)
        return uuid4()


def _principal(
    *, principal_id: str = "user-jane", scopes: tuple[str, ...] = ()
) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id=principal_id,
        tenant_id="tenant-a",
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


class _Request:
    def __init__(self, *, status: str = "Pending", requested_by: str = "user-jane") -> None:
        self.approval_id = uuid4()
        self.tenant_id = "tenant-a"
        self.action_id = ACTION_ID
        self.note_text = "hello"
        self.status_value = status
        self.requested_by = requested_by
        self.requested_on = NOW
        self.decided_by = None
        self.decided_on = None
        self.rejection_reason = None
        self.consumed_on = None
        self.consumed_execution_id = None

    @property
    def status(self) -> ApprovalStatus:
        return ApprovalStatus(self.status_value)


class FakeService:
    def __init__(
        self, *, result: object | None = None, error: GateSApprovalError | None = None
    ) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.result = result if result is not None else _Request()
        self.error = error

    def request(self, **kwargs: Any) -> object:
        self.calls.append(("request", kwargs))
        return self.result

    def approve(self, **kwargs: Any) -> object:
        self.calls.append(("approve", kwargs))
        if self.error:
            raise self.error
        return self.result

    def reject(self, **kwargs: Any) -> object:
        self.calls.append(("reject", kwargs))
        if self.error:
            raise self.error
        return self.result

    def execute(self, **kwargs: Any) -> UUID:
        self.calls.append(("execute", kwargs))
        if self.error:
            raise self.error
        return uuid4()


class FakeRepository:
    def __init__(self, *, result: object | None = None) -> None:
        self.result = result
        self.calls: list[str] = []

    def get_by_id(self, approval_id: UUID) -> object | None:
        self.calls.append("get_by_id")
        return self.result


def _client(
    app_container: Container,
    service: FakeService,
    repository: FakeRepository,
    authenticated: TrustedPrincipal,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: app_container
    app.dependency_overrides[gate_s_approval_service] = lambda: service
    app.dependency_overrides[gate_s_approval_repository] = lambda: repository
    return TestClient(app)


def _container(*, audit: Audit | None = None) -> Container:
    return Container(Settings(), security_audit=audit)  # type: ignore[arg-type]


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/governed-approval/requests", json={"note_text": "hello"})
    assert response.status_code == 401


def test_create_request_requires_request_scope() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, FakeRepository(), _principal(scopes=()))
    response = client.post("/api/v1/governed-approval/requests", json={"note_text": "hello"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_create_request_with_request_scope_succeeds() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("governed-approval:request",)),
    )
    response = client.post("/api/v1/governed-approval/requests", json={"note_text": "hello"})
    assert response.status_code == 200
    assert response.json()["status"] == "Pending"
    assert service.calls[0][0] == "request"


def test_approve_requires_decide_scope_not_request() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("governed-approval:request",)),
    )
    response = client.post(f"/api/v1/governed-approval/requests/{uuid4()}/approve")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_execute_requires_request_scope_not_decide() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("governed-approval:decide",)),
    )
    response = client.post(
        f"/api/v1/governed-approval/requests/{uuid4()}/execute", json={"note_text": "hello"}
    )
    assert response.status_code == 403
    assert service.calls == []


def test_get_request_from_different_tenant_fails_tenant_mismatch() -> None:
    other_tenant_request = _Request()
    other_tenant_request.tenant_id = "tenant-b"
    repository = FakeRepository(result=other_tenant_request)
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        repository,
        _principal(scopes=("governed-approval:request",)),
    )
    response = client.get(f"/api/v1/governed-approval/requests/{uuid4()}")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "APPROVAL_TENANT_MISMATCH"


def test_self_approval_error_from_service_maps_to_403() -> None:
    service = FakeService(error=GateSApprovalError("APPROVAL_SELF_APPROVAL_PROHIBITED"))
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("governed-approval:decide",)),
    )
    response = client.post(f"/api/v1/governed-approval/requests/{uuid4()}/approve")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "APPROVAL_SELF_APPROVAL_PROHIBITED"


def test_action_mismatch_error_from_service_maps_to_409() -> None:
    service = FakeService(error=GateSApprovalError("APPROVAL_ACTION_MISMATCH"))
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("governed-approval:request",)),
    )
    response = client.post(
        f"/api/v1/governed-approval/requests/{uuid4()}/execute", json={"note_text": "mutated"}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "APPROVAL_ACTION_MISMATCH"
