"""Router-level tests for the Gate V Governed Agent Resolution API (CDD-037
§18-§19; Gate V Artifact Authorization §7). These exercise authentication,
scope authorization (including that the two POST authorities never imply
each other, and that neither implies GET's authorities), and tenant
enforcement purely through FastAPI dependency overrides -- no database is
required. Real persistence/composition behavior is proven separately,
against real Postgres, in `test_gate_v_agent_postgres.py`."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.gate_v.dependencies import (
    gate_v_agent_resolution_repository,
    gate_v_agent_service,
)
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.gate_v.agent_resolution import AGENT_ID, AgentResolutionOutcome
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


class _Resolution:
    def __init__(
        self,
        *,
        outcome: str = "PROPOSED",
        tenant_id: str = "tenant-a",
        approval_id: UUID | None = None,
    ) -> None:
        self.resolution_id = uuid4()
        self.tenant_id = tenant_id
        self.agent_id = AGENT_ID
        self.requested_by = "user-jane"
        self.observation_text = "hello"
        self.priority_score = 75
        self.outcome_value = outcome
        self.approval_id = approval_id if approval_id is not None else uuid4()
        self.resolved_on = NOW

    @property
    def outcome(self) -> AgentResolutionOutcome:
        return AgentResolutionOutcome(self.outcome_value)


class FakeService:
    def __init__(self, *, result: object | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.result = result if result is not None else _Resolution()

    def resolve(self, **kwargs: Any) -> object:
        self.calls.append(("resolve", kwargs))
        return self.result


class FakeRepository:
    def __init__(self, *, result: object | None = None) -> None:
        self.result = result
        self.calls: list[str] = []

    def get_by_id(self, resolution_id: UUID) -> object | None:
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
    app.dependency_overrides[gate_v_agent_service] = lambda: service
    app.dependency_overrides[gate_v_agent_resolution_repository] = lambda: repository
    return TestClient(app)


def _container(*, audit: Audit | None = None) -> Container:
    return Container(Settings(), security_audit=audit)  # type: ignore[arg-type]


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/governed-agent/resolutions",
            json={"observation_text": "hello", "priority_score": 75},
        )
    assert response.status_code == 401


def test_missing_agent_propose_scope_denies_before_service_call() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("governed-approval:request",)),
    )
    response = client.post(
        "/api/v1/governed-agent/resolutions",
        json={"observation_text": "hello", "priority_score": 75},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AGENT_PROPOSE_AUTHORITY_REQUIRED"
    assert service.calls == []


def test_missing_request_scope_denies_before_service_call() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("governed-agent:propose",)),
    )
    response = client.post(
        "/api/v1/governed-agent/resolutions",
        json={"observation_text": "hello", "priority_score": 75},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "REQUEST_AUTHORITY_REQUIRED"
    assert service.calls == []


def test_both_scopes_present_succeeds() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("governed-agent:propose", "governed-approval:request")),
    )
    response = client.post(
        "/api/v1/governed-agent/resolutions",
        json={"observation_text": "hello", "priority_score": 75},
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "PROPOSED"
    assert service.calls[0][0] == "resolve"


def test_get_succeeds_with_agent_propose_scope_alone() -> None:
    repository = FakeRepository(result=_Resolution())
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        repository,
        _principal(scopes=("governed-agent:propose",)),
    )
    response = client.get(f"/api/v1/governed-agent/resolutions/{uuid4()}")
    assert response.status_code == 200


def test_get_succeeds_with_approval_decide_scope_alone() -> None:
    repository = FakeRepository(result=_Resolution())
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        repository,
        _principal(scopes=("governed-approval:decide",)),
    )
    response = client.get(f"/api/v1/governed-agent/resolutions/{uuid4()}")
    assert response.status_code == 200


def test_get_denied_without_either_authorized_scope() -> None:
    repository = FakeRepository(result=_Resolution())
    client = _client(_container(audit=Audit()), FakeService(), repository, _principal(scopes=()))
    response = client.get(f"/api/v1/governed-agent/resolutions/{uuid4()}")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"


def test_get_unknown_resolution_returns_not_found() -> None:
    repository = FakeRepository(result=None)
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        repository,
        _principal(scopes=("governed-agent:propose",)),
    )
    response = client.get(f"/api/v1/governed-agent/resolutions/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RESOLUTION_NOT_FOUND"


def test_get_cross_tenant_resolution_fails_tenant_mismatch() -> None:
    other_tenant_resolution = _Resolution(tenant_id="tenant-b")
    repository = FakeRepository(result=other_tenant_resolution)
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        repository,
        _principal(scopes=("governed-agent:propose",)),
    )
    response = client.get(f"/api/v1/governed-agent/resolutions/{uuid4()}")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "RESOLUTION_TENANT_MISMATCH"


def test_empty_observation_text_returns_422() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        FakeRepository(),
        _principal(scopes=("governed-agent:propose", "governed-approval:request")),
    )
    response = client.post(
        "/api/v1/governed-agent/resolutions",
        json={"observation_text": "", "priority_score": 75},
    )
    assert response.status_code == 422


def test_oversized_observation_text_returns_422() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        FakeRepository(),
        _principal(scopes=("governed-agent:propose", "governed-approval:request")),
    )
    response = client.post(
        "/api/v1/governed-agent/resolutions",
        json={"observation_text": "x" * 501, "priority_score": 75},
    )
    assert response.status_code == 422


def test_priority_score_below_zero_returns_422() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        FakeRepository(),
        _principal(scopes=("governed-agent:propose", "governed-approval:request")),
    )
    response = client.post(
        "/api/v1/governed-agent/resolutions",
        json={"observation_text": "hello", "priority_score": -1},
    )
    assert response.status_code == 422


def test_priority_score_above_100_returns_422() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        FakeRepository(),
        _principal(scopes=("governed-agent:propose", "governed-approval:request")),
    )
    response = client.post(
        "/api/v1/governed-agent/resolutions",
        json={"observation_text": "hello", "priority_score": 101},
    )
    assert response.status_code == 422


def test_request_payload_cannot_supply_tenant_or_requested_by() -> None:
    """CDD-037 §11: only `observation_text`/`priority_score` are accepted;
    any extra caller-supplied field is silently ignored, never consulted."""
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(
            principal_id="real-caller",
            scopes=("governed-agent:propose", "governed-approval:request"),
        ),
    )
    response = client.post(
        "/api/v1/governed-agent/resolutions",
        json={
            "observation_text": "hello",
            "priority_score": 75,
            "tenant_id": "forged-tenant",
            "requested_by": "forged-principal",
        },
    )
    assert response.status_code == 200
    _, kwargs = service.calls[0]
    assert kwargs["principal"].principal_id == "real-caller"
    assert "tenant_id" not in kwargs
    assert "requested_by" not in kwargs
