"""Router-level tests for the Gate O Information-Element Context API
(CDD-029; Gate O Artifact Authorization v1.0 §5). These exercise
authentication, scope authorization (including that an under-scoped caller
never reaches the application service at all), request-schema closure, and
the frozen HTTP failure mapping purely through FastAPI dependency
overrides -- no database is required, since the application service is
replaced with an in-memory fake that only ever sees what the router
actually passes to it. Real end-to-end resolution behavior is proven
separately, against real Postgres, in
`test_information_element_context_resolution_postgres.py` and
`test_information_element_context_resolution.py`."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.information_element_context.dependencies import information_element_context_service
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.application.information_element_context_resolution import (
    InformationElementContextResolutionResult,
    InformationElementContextResolutionStatus,
)
from app.application.information_element_evidence_availability import EvidenceAvailabilityStatus
from app.application.semantic_coverage_evaluation import CoverageStatus
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.blueprint import Obligation
from app.main import create_app

NOW = datetime.now(UTC)

RESOLVED_RESULT = InformationElementContextResolutionResult(
    status=InformationElementContextResolutionStatus.RESOLVED,
    blueprint_id=uuid4(),
    blueprint_version_number=1,
    information_element_requirement_id=uuid4(),
    information_element_name="Supplier Legal Name",
    obligation=Obligation.REQUIRED,
    coverage_status=CoverageStatus.MAPPED,
    evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
)


class Audit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, **values: object) -> UUID:
        self.events.append(values)
        return uuid4()


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


class FakeService:
    """Records every call, proving the router never invokes resolution for
    an under-scoped caller."""

    def __init__(self, *, result: InformationElementContextResolutionResult | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result = result if result is not None else RESOLVED_RESULT

    def resolve(self, **kwargs: Any) -> InformationElementContextResolutionResult:
        self.calls.append(kwargs)
        return self.result


def _client(
    app_container: Container, service: FakeService, authenticated: TrustedPrincipal
) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: app_container
    app.dependency_overrides[information_element_context_service] = lambda: service
    return TestClient(app)


def _container(*, audit: Audit | None = None) -> Container:
    return Container(Settings(), security_audit=audit)  # type: ignore[arg-type]


_VALID_BODY = {
    "blueprint_name": "CTEC Semiconductor Supply Chain Blueprint",
    "information_element_name": "Supplier Legal Name",
}


# ---------------------------------------------------------------------------
# Authentication / scope enforcement.
# ---------------------------------------------------------------------------


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)
    assert response.status_code == 401


def test_missing_scope_is_rejected_before_resolution_is_invoked() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=()))
    response = client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    # An under-scoped caller must never cause Blueprint resolution, Gate I,
    # H4, or Gate N to execute (CDD-029 §10, §14).
    assert service.calls == []


def test_correct_scope_is_sufficient() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)

    assert response.status_code == 200
    assert len(service.calls) == 1


def test_denied_authorization_is_recorded_to_security_audit() -> None:
    audit = Audit()
    client = _client(_container(audit=audit), FakeService(), _principal(scopes=()))
    client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)

    assert len(audit.events) == 1
    assert audit.events[0]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"


# ---------------------------------------------------------------------------
# Successful resolution payload.
# ---------------------------------------------------------------------------


def test_successful_resolution_returns_exactly_the_seven_governed_fields() -> None:
    service = FakeService(result=RESOLVED_RESULT)
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "blueprint_id",
        "blueprint_version_number",
        "information_element_requirement_id",
        "information_element_name",
        "obligation",
        "coverage_status",
        "evidence_availability_status",
    }
    assert body["coverage_status"] == "MAPPED"
    assert body["evidence_availability_status"] == "EVIDENCE_PRESENT"
    # No redundant success status field, no raw evidence, no tenant data.
    assert "status" not in body
    assert "tenant_id" not in body


# ---------------------------------------------------------------------------
# Frozen failure mapping (CDD-029 §15, O3-D8 -- not reopened here).
# ---------------------------------------------------------------------------


def _failure_result(
    status: InformationElementContextResolutionStatus,
) -> InformationElementContextResolutionResult:
    return InformationElementContextResolutionResult(
        status=status,
        blueprint_id=None,
        blueprint_version_number=None,
        information_element_requirement_id=None,
        information_element_name=None,
        obligation=None,
        coverage_status=None,
        evidence_availability_status=None,
    )


def test_blueprint_not_found_maps_to_404() -> None:
    service = FakeService(
        result=_failure_result(InformationElementContextResolutionStatus.BLUEPRINT_NOT_FOUND)
    )
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BLUEPRINT_NOT_FOUND"


def test_information_element_not_found_maps_to_404() -> None:
    service = FakeService(
        result=_failure_result(
            InformationElementContextResolutionStatus.INFORMATION_ELEMENT_NOT_FOUND
        )
    )
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "INFORMATION_ELEMENT_NOT_FOUND"


def test_ambiguous_information_element_name_maps_to_422_not_500() -> None:
    service = FakeService(
        result=_failure_result(
            InformationElementContextResolutionStatus.INFORMATION_ELEMENT_NAME_AMBIGUOUS
        )
    )
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INFORMATION_ELEMENT_NAME_AMBIGUOUS"


def test_upstream_integrity_failure_maps_to_500_not_422() -> None:
    service = FakeService(
        result=_failure_result(InformationElementContextResolutionStatus.UPSTREAM_INTEGRITY_FAILURE)
    )
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post("/api/v1/information-element-context/resolve", json=_VALID_BODY)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "UPSTREAM_INTEGRITY_FAILURE"


# ---------------------------------------------------------------------------
# Closed request schema.
# ---------------------------------------------------------------------------


def test_missing_required_field_is_rejected_with_422() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post(
        "/api/v1/information-element-context/resolve",
        json={"blueprint_name": "CTEC Semiconductor Supply Chain Blueprint"},
    )
    assert response.status_code == 422


def test_caller_supplied_tenant_id_is_rejected_by_the_closed_schema() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post(
        "/api/v1/information-element-context/resolve",
        json={**_VALID_BODY, "tenant_id": "some-other-tenant"},
    )

    assert response.status_code == 422
    assert service.calls == []


def test_unexpected_extra_field_is_rejected_by_the_closed_schema() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        _principal(scopes=("information-element-context:read",)),
    )
    response = client.post(
        "/api/v1/information-element-context/resolve",
        json={**_VALID_BODY, "unexpected_field": "value"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Keycloak configuration (POST-U/X-DEBT-6; CDD-029 Keycloak Scope Defect
# Authorization). Mirrors test_gate_f_api_security.py's own structural
# realm-parsing pattern, scoped to this router's own frozen scope literal.
# ---------------------------------------------------------------------------


def test_keycloak_demo_persona_has_information_element_context_scope() -> None:
    import json
    from pathlib import Path

    realm = json.loads((Path(__file__).parents[3] / "keycloak" / "ctec-realm.json").read_text())
    default_scopes = realm["clients"][0]["defaultClientScopes"]
    assert "information-element-context:read" in default_scopes
    scope_names = {block["name"] for block in realm["clientScopes"]}
    assert "information-element-context:read" in scope_names
