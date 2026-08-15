"""Router-level tests for the Entity Resolution Steward API. These exercise
authentication, scope authorization, rate limiting, error-code mapping, and
audit recording purely through FastAPI dependency overrides -- no database
is required, since the application service is replaced with an in-memory
fake that only ever sees what the router actually passes to it (proving
tenant identity comes from TrustedPrincipal, not the request)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.entity_resolution.dependencies import steward_api_service
from app.api.entity_resolution.schemas import (
    CaseDetailResponse,
    CaseListResponse,
    DecisionRequest,
    DecisionResponse,
    PolicyListResponse,
    PreviewResponse,
)
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.api.supplier_risk.rate_limit import RateLimiter
from app.application.entity_resolution_steward_api import (
    CaseNotFoundError,
    NoEvidenceProfileError,
    PolicyNotFoundError,
)
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.identity_resolution.service import OverrideNotPermittedError
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.entity_resolution_store import StaleResolutionCaseError
from app.main import create_app

NOW = datetime.now(UTC)


class Audit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, **values: object) -> UUID:
        self.events.append(values)
        return uuid4()


def _principal(*, scopes: tuple[str, ...] = ()) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="steward-jane",
        tenant_id="tenant-a",
        scopes=scopes,
        roles=("steward",),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


@dataclass
class FakeStewardService:
    """Records every call it receives; canned results/exceptions are set
    per-test. Never touches a database."""

    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = field(default_factory=list)
    list_cases_result: CaseListResponse | None = None
    get_case_result: CaseDetailResponse | None = None
    list_policies_result: PolicyListResponse | None = None
    preview_result: PreviewResponse | None = None
    preview_exception: Exception | None = None
    decide_result: DecisionResponse | None = None
    decide_exception: Exception | None = None

    def list_cases(
        self, principal: TrustedPrincipal, *, outcomes: tuple[str, ...] | None = None
    ) -> CaseListResponse:
        self.calls.append(("list_cases", (principal, outcomes), {}))
        return self.list_cases_result or CaseListResponse(items=[])

    def get_case(
        self, principal: TrustedPrincipal, understanding_key: str
    ) -> CaseDetailResponse | None:
        self.calls.append(("get_case", (principal, understanding_key), {}))
        return self.get_case_result

    def list_policies(self, principal: TrustedPrincipal) -> PolicyListResponse:
        self.calls.append(("list_policies", (principal,), {}))
        return self.list_policies_result or PolicyListResponse(items=[])

    def preview(
        self, principal: TrustedPrincipal, understanding_key: str, policy_id: UUID
    ) -> PreviewResponse:
        self.calls.append(("preview", (principal, understanding_key, policy_id), {}))
        if self.preview_exception is not None:
            raise self.preview_exception
        assert self.preview_result is not None
        return self.preview_result

    def decide_case(
        self,
        principal: TrustedPrincipal,
        understanding_key: str,
        request: DecisionRequest,
        **kwargs: Any,
    ) -> DecisionResponse:
        self.calls.append(("decide_case", (principal, understanding_key, request), kwargs))
        if self.decide_exception is not None:
            raise self.decide_exception
        assert self.decide_result is not None
        return self.decide_result


def _client(
    app_container: Container, service: FakeStewardService, authenticated: TrustedPrincipal
) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: app_container
    app.dependency_overrides[steward_api_service] = lambda: service
    return TestClient(app)


def _container(*, audit: Audit | None = None, rate_limiter: RateLimiter | None = None) -> Container:
    return Container(
        Settings(),
        security_audit=audit,  # type: ignore[arg-type]
        rate_limiter=rate_limiter,
    )


# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/entity-resolution/cases")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_MISSING"


def test_list_cases_requires_the_read_scope() -> None:
    service = FakeStewardService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=()))
    response = client.get("/api/v1/entity-resolution/cases")
    assert response.status_code == 403
    assert response.json()["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_decide_requires_the_decide_scope_even_with_read_scope() -> None:
    service = FakeStewardService()
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:read",))
    )
    response = client.post(
        "/api/v1/entity-resolution/cases/some-key/decisions",
        json={
            "action": "mark_unresolved",
            "rationale": "deferred",
            "based_on_record_id": str(uuid4()),
            "policy_id": str(uuid4()),
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_read_scope_is_sufficient_for_list_cases() -> None:
    service = FakeStewardService(list_cases_result=CaseListResponse(items=[]))
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:read",))
    )
    response = client.get("/api/v1/entity-resolution/cases")
    assert response.status_code == 200
    assert response.json() == {"items": []}
    assert service.calls[0][0] == "list_cases"


def test_rate_limiting_rejects_before_service_disclosure() -> None:
    class AlwaysDenyRateLimiter:
        def admit(self, tenant_id: str) -> bool:
            del tenant_id
            return False

    service = FakeStewardService(list_cases_result=CaseListResponse(items=[]))
    client = _client(
        _container(audit=Audit(), rate_limiter=AlwaysDenyRateLimiter()),  # type: ignore[arg-type]
        service,
        _principal(scopes=("entity-resolution:read",)),
    )
    response = client.get("/api/v1/entity-resolution/cases")
    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"
    assert service.calls == []


# ---------------------------------------------------------------------------
# Tenant identity source
# ---------------------------------------------------------------------------


def test_tenant_identity_comes_only_from_the_trusted_principal() -> None:
    """The router accepts no tenant_id from the request at all -- the fake
    service only ever receives the TrustedPrincipal, and its tenant_id is
    exactly what the (verified) principal carried."""
    service = FakeStewardService(list_cases_result=CaseListResponse(items=[]))
    authenticated = _principal(scopes=("entity-resolution:read",))
    client = _client(_container(audit=Audit()), service, authenticated)
    client.get("/api/v1/entity-resolution/cases")
    passed_principal = service.calls[0][1][0]
    assert passed_principal.tenant_id == "tenant-a"


# ---------------------------------------------------------------------------
# Not-found / validation error mapping
# ---------------------------------------------------------------------------


def test_get_case_not_found_returns_404() -> None:
    service = FakeStewardService(get_case_result=None)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:read",))
    )
    response = client.get("/api/v1/entity-resolution/cases/unknown-key")
    assert response.status_code == 404
    assert response.json()["code"] == "RESOLUTION_CASE_NOT_FOUND"


def test_preview_case_not_found_returns_404() -> None:
    service = FakeStewardService(preview_exception=CaseNotFoundError("k"))
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:read",))
    )
    response = client.post(f"/api/v1/entity-resolution/cases/some-key/preview?policy_id={uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "RESOLUTION_CASE_NOT_FOUND"


def test_preview_unknown_policy_returns_404() -> None:
    service = FakeStewardService(preview_exception=PolicyNotFoundError("p"))
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:read",))
    )
    response = client.post(f"/api/v1/entity-resolution/cases/some-key/preview?policy_id={uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "RESOLUTION_POLICY_NOT_FOUND"


def test_preview_without_an_evidence_profile_returns_422() -> None:
    service = FakeStewardService(preview_exception=NoEvidenceProfileError("k"))
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:read",))
    )
    response = client.post(f"/api/v1/entity-resolution/cases/some-key/preview?policy_id={uuid4()}")
    assert response.status_code == 422
    assert response.json()["code"] == "NO_EVIDENCE_PROFILE_TO_PREVIEW"


def test_invalid_outcome_filter_returns_400() -> None:
    service = FakeStewardService()
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:read",))
    )
    response = client.get("/api/v1/entity-resolution/cases?outcome=NotARealOutcome")
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_OUTCOME_FILTER"
    assert service.calls == []


# ---------------------------------------------------------------------------
# Decision endpoint: stable error contract + audit trail
# ---------------------------------------------------------------------------


def _decision_body(**overrides: Any) -> dict[str, Any]:
    body = {
        "action": "mark_unresolved",
        "rationale": "deferred pending more information",
        "based_on_record_id": str(uuid4()),
        "policy_id": str(uuid4()),
    }
    body.update(overrides)
    return body


def test_decide_stale_case_returns_a_stable_409_and_audits_the_rejection() -> None:
    audit = Audit()
    service = FakeStewardService(decide_exception=StaleResolutionCaseError("stale"))
    client = _client(
        _container(audit=audit), service, _principal(scopes=("entity-resolution:decide",))
    )
    response = client.post(
        "/api/v1/entity-resolution/cases/some-key/decisions", json=_decision_body()
    )
    assert response.status_code == 409
    assert response.json()["code"] == "STALE_RESOLUTION_CASE"
    codes = [event["code"] for event in audit.events]
    assert "STALE_RESOLUTION_CASE" in codes


def test_decide_override_not_permitted_returns_422() -> None:
    audit = Audit()
    service = FakeStewardService(decide_exception=OverrideNotPermittedError("veto"))
    client = _client(
        _container(audit=audit), service, _principal(scopes=("entity-resolution:decide",))
    )
    response = client.post(
        "/api/v1/entity-resolution/cases/some-key/decisions",
        json=_decision_body(action="confirm_match"),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "OVERRIDE_NOT_PERMITTED"


def test_decide_generic_validation_error_returns_422() -> None:
    service = FakeStewardService(decide_exception=ValidationException("bad"))
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:decide",))
    )
    response = client.post(
        "/api/v1/entity-resolution/cases/some-key/decisions",
        json=_decision_body(action="block_conflict"),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "DECISION_NOT_PERMITTED"


def test_decide_case_not_found_returns_404() -> None:
    service = FakeStewardService(decide_exception=CaseNotFoundError("k"))
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("entity-resolution:decide",))
    )
    response = client.post(
        "/api/v1/entity-resolution/cases/some-key/decisions", json=_decision_body()
    )
    assert response.status_code == 404
    assert response.json()["code"] == "RESOLUTION_CASE_NOT_FOUND"


def test_decide_success_returns_201_and_records_an_authorized_and_accepted_audit_trail() -> None:
    audit = Audit()
    record_id = uuid4()
    result = DecisionResponse(
        record_id=record_id,
        understanding_key="some-key",
        outcome="Unresolved",
        business_confidence="Low",
        produced_at=NOW.isoformat(),
        policy_id=uuid4(),
        policy_version="Supplier Resolution — Conservative v1.0",
        narrative_explanation="Unresolved using policy ...",
        structured_reasons=["Steward marked this case unresolved."],
    )
    service = FakeStewardService(decide_result=result)
    client = _client(
        _container(audit=audit), service, _principal(scopes=("entity-resolution:decide",))
    )
    response = client.post(
        "/api/v1/entity-resolution/cases/some-key/decisions", json=_decision_body()
    )
    assert response.status_code == 201
    assert response.json()["record_id"] == str(record_id)
    outcomes = [event["outcome"] for event in audit.events]
    assert "AUTHORIZED" in outcomes
    assert "ACCEPTED" in outcomes
    assert all(
        event.get("endpoint_classification") == "ENTITY_RESOLUTION_STEWARD_API_V1"
        for event in audit.events
    )
