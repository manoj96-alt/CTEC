from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import api_service, container, principal
from app.api.supplier_risk.rate_limit import RateLimiter
from app.api.supplier_risk.schemas import SubmissionResponse
from app.application.supplier_risk_api import SupplierRiskApiService
from app.core.config import Settings
from app.core.dependency_container import Container
from app.main import create_app
from app.tests.test_supplier_risk_pipeline import build_request, runtime_and_persistence


class Audit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record(self, **values: object) -> UUID:
        self.events.append(values)
        return uuid4()


class RecoveryService:
    def retry(
        self, logical_id: UUID, body: object, principal: TrustedPrincipal
    ) -> SubmissionResponse:
        del body, principal
        return SubmissionResponse(
            execution_identifier=uuid4(),
            logical_execution_identifier=logical_id,
            correlation_identifier=uuid4(),
            state="Accepted",
        )

    replay = retry


def test_valid_submission_uses_existing_runtime_and_is_idempotent() -> None:
    runtime, persistence = runtime_and_persistence()
    service = SupplierRiskApiService(runtime)
    now = datetime.now(UTC)
    trusted = TrustedPrincipal(
        "principal",
        "tenant-a",
        ("supplier-risk:submit", "supplier-risk:read"),
        ("analyst",),
        "https://issuer.example/",
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )
    audit = Audit()
    value = Container(
        Settings(),
        supplier_risk_api=service,
        security_audit=audit,  # type: ignore[arg-type]
        rate_limiter=RateLimiter(10),
    )
    app = create_app()
    app.dependency_overrides[principal] = lambda: trusted
    app.dependency_overrides[api_service] = lambda: service
    app.dependency_overrides[container] = lambda: value
    request_id, correlation, session = uuid4(), uuid4(), uuid4()
    body = {
        "request_identifier": str(request_id),
        "correlation_identifier": str(correlation),
        "session_identifier": str(session),
        "supplier_risk": jsonable_encoder(asdict(build_request())),
    }
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/supplier-risk/assessments",
            json=body,
            headers={"Idempotency-Key": str(request_id)},
        )
        second = client.post(
            "/api/v1/supplier-risk/assessments",
            json=body,
            headers={"Idempotency-Key": str(request_id)},
        )
    assert first.status_code == 202 and second.status_code == 202
    assert first.json()["execution_identifier"] == second.json()["execution_identifier"]
    assert len(persistence.records) <= 6
    assert audit.events


def test_retry_and_privileged_replay_routes_are_bounded_and_audited() -> None:
    now = datetime.now(UTC)
    trusted = TrustedPrincipal(
        "operator",
        "tenant-a",
        ("supplier-risk:retry", "execution:replay"),
        ("EXECUTION_RECOVERY_OPERATOR",),
        "https://issuer.example/",
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )
    audit = Audit()
    value = Container(Settings(), security_audit=audit)  # type: ignore[arg-type]
    service = RecoveryService()
    app = create_app()
    app.dependency_overrides[principal] = lambda: trusted
    app.dependency_overrides[api_service] = lambda: service
    app.dependency_overrides[container] = lambda: value
    logical_id = uuid4()
    for operation in ("retry", "replay"):
        request_id = uuid4()
        response = TestClient(app).post(
            f"/api/v1/supplier-risk/executions/{logical_id}/{operation}",
            json={
                "request_identifier": str(request_id),
                "correlation_identifier": str(uuid4()),
                "reason": "authorized recovery",
            },
            headers={"Idempotency-Key": str(request_id)},
        )
        assert response.status_code == 202
        assert response.json()["logical_execution_identifier"] == str(logical_id)
    assert {event["operation"] for event in audit.events} >= {
        "RETRY_EXECUTION",
        "REPLAY_EXECUTION",
    }
