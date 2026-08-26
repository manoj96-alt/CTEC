"""Router-level tests for the Governed Evidence Fitness Exposure API
(CDD-034; CDD-034 Artifact Authorization v1.0 §9). These exercise
authentication, scope authorization (including that an under-scoped caller
never reaches the application service at all), request-schema closure, and
the frozen HTTP failure mapping purely through FastAPI dependency
overrides -- no database is required, since the application service is
replaced with an in-memory fake that only ever sees what the router
actually passes to it. Real end-to-end composition behavior -- including
the UNMAPPED short-circuit's genuine non-construction of H4/Gate T -- is
proven separately, against real Postgres, in
`test_information_element_evidence_fitness_resolution.py` and
`test_information_element_evidence_fitness_resolution_postgres.py`."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.information_element_evidence_fitness.dependencies import (
    information_element_evidence_fitness_service,
)
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.application.information_element_evidence_fitness_resolution import (
    InformationElementEvidenceFitnessResolutionResult,
    InformationElementEvidenceFitnessResolutionStatus,
)
from app.application.source_evidence_fitness_evaluation import EvidenceFitnessStatus
from app.core.config import Settings
from app.core.dependency_container import Container
from app.main import create_app

NOW = datetime.now(UTC)

RESOLVED_RESULT = InformationElementEvidenceFitnessResolutionResult(
    status=InformationElementEvidenceFitnessResolutionStatus.RESOLVED,
    information_element_requirement_id=uuid4(),
    source_field_id=uuid4(),
    fitness_status=EvidenceFitnessStatus.FIT,
    evaluated_at=NOW,
)

UNMAPPED_RESULT = InformationElementEvidenceFitnessResolutionResult(
    status=InformationElementEvidenceFitnessResolutionStatus.RESOLVED,
    information_element_requirement_id=uuid4(),
    source_field_id=None,
    fitness_status=None,
    evaluated_at=NOW,
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
    an under-scoped caller or a closed-schema rejection."""

    def __init__(
        self, *, result: InformationElementEvidenceFitnessResolutionResult | None = None
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result = result if result is not None else RESOLVED_RESULT

    def resolve(self, **kwargs: Any) -> InformationElementEvidenceFitnessResolutionResult:
        self.calls.append(kwargs)
        return self.result


def _client(
    app_container: Container, service: FakeService, authenticated: TrustedPrincipal
) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: app_container
    app.dependency_overrides[information_element_evidence_fitness_service] = lambda: service
    return TestClient(app)


def _container(*, audit: Audit | None = None) -> Container:
    return Container(Settings(), security_audit=audit)  # type: ignore[arg-type]


_VALID_BODY = {
    "blueprint_name": "CTEC Semiconductor Supply Chain Blueprint",
    "information_element_name": "Supplier Legal Name",
}

_ENDPOINT = "/api/v1/information-element-evidence-fitness/resolve"
_SCOPE = "information-element-evidence-fitness:read"


# ---------------------------------------------------------------------------
# Authentication / scope enforcement.
# ---------------------------------------------------------------------------


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.post(_ENDPOINT, json=_VALID_BODY)
    assert response.status_code == 401


def test_missing_scope_is_rejected_before_resolution_is_invoked() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=()))
    response = client.post(_ENDPOINT, json=_VALID_BODY)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    # An under-scoped caller must never cause Blueprint resolution, Gate I,
    # H4, or Gate T to execute (CDD-034 §13, §16).
    assert service.calls == []


def test_correct_scope_is_sufficient() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json=_VALID_BODY)

    assert response.status_code == 200
    assert len(service.calls) == 1


def test_denied_authorization_is_recorded_to_security_audit() -> None:
    audit = Audit()
    client = _client(_container(audit=audit), FakeService(), _principal(scopes=()))
    client.post(_ENDPOINT, json=_VALID_BODY)

    assert len(audit.events) == 1
    assert audit.events[0]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"


# ---------------------------------------------------------------------------
# Successful resolution payload.
# ---------------------------------------------------------------------------


def test_successful_resolution_returns_exactly_the_four_governed_fields() -> None:
    service = FakeService(result=RESOLVED_RESULT)
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json=_VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "information_element_requirement_id",
        "source_field_id",
        "fitness_status",
        "evaluated_at",
    }
    assert body["fitness_status"] == "FIT"
    assert body["source_field_id"] is not None
    # No tenant data leaked into the response.
    assert "tenant_id" not in body


def test_unmapped_result_returns_200_with_null_source_field_and_fitness() -> None:
    service = FakeService(result=UNMAPPED_RESULT)
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json=_VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["source_field_id"] is None
    assert body["fitness_status"] is None
    assert body["evaluated_at"] is not None


# ---------------------------------------------------------------------------
# Frozen failure mapping (CDD-034 §18 -- not reopened here).
# ---------------------------------------------------------------------------


def _failure_result(
    status: InformationElementEvidenceFitnessResolutionStatus,
) -> InformationElementEvidenceFitnessResolutionResult:
    return InformationElementEvidenceFitnessResolutionResult(
        status=status,
        information_element_requirement_id=None,
        source_field_id=None,
        fitness_status=None,
        evaluated_at=None,
    )


def test_blueprint_not_found_maps_to_404() -> None:
    service = FakeService(
        result=_failure_result(
            InformationElementEvidenceFitnessResolutionStatus.BLUEPRINT_NOT_FOUND
        )
    )
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json=_VALID_BODY)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BLUEPRINT_NOT_FOUND"


def test_information_element_not_found_maps_to_404() -> None:
    service = FakeService(
        result=_failure_result(
            InformationElementEvidenceFitnessResolutionStatus.INFORMATION_ELEMENT_NOT_FOUND
        )
    )
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json=_VALID_BODY)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "INFORMATION_ELEMENT_NOT_FOUND"


def test_ambiguous_information_element_name_maps_to_422_not_500() -> None:
    service = FakeService(
        result=_failure_result(
            InformationElementEvidenceFitnessResolutionStatus.INFORMATION_ELEMENT_NAME_AMBIGUOUS
        )
    )
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json=_VALID_BODY)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INFORMATION_ELEMENT_NAME_AMBIGUOUS"


def test_upstream_integrity_failure_maps_to_500_not_422() -> None:
    service = FakeService(
        result=_failure_result(
            InformationElementEvidenceFitnessResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
        )
    )
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json=_VALID_BODY)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "UPSTREAM_INTEGRITY_FAILURE"


# ---------------------------------------------------------------------------
# Closed request schema.
# ---------------------------------------------------------------------------


def test_missing_required_field_is_rejected_with_422() -> None:
    client = _client(_container(audit=Audit()), FakeService(), _principal(scopes=(_SCOPE,)))
    response = client.post(
        _ENDPOINT,
        json={"blueprint_name": "CTEC Semiconductor Supply Chain Blueprint"},
    )
    assert response.status_code == 422


def test_caller_supplied_tenant_id_is_rejected_by_the_closed_schema() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json={**_VALID_BODY, "tenant_id": "some-other-tenant"})

    assert response.status_code == 422
    assert service.calls == []


def test_caller_supplied_as_of_is_rejected_by_the_closed_schema() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json={**_VALID_BODY, "as_of": NOW.isoformat()})

    assert response.status_code == 422
    assert service.calls == []


def test_caller_supplied_evaluated_at_is_rejected_by_the_closed_schema() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json={**_VALID_BODY, "evaluated_at": NOW.isoformat()})

    assert response.status_code == 422
    assert service.calls == []


def test_unexpected_extra_field_is_rejected_by_the_closed_schema() -> None:
    client = _client(_container(audit=Audit()), FakeService(), _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json={**_VALID_BODY, "unexpected_field": "value"})
    assert response.status_code == 422


def test_empty_blueprint_name_is_rejected_with_422() -> None:
    client = _client(_container(audit=Audit()), FakeService(), _principal(scopes=(_SCOPE,)))
    response = client.post(_ENDPOINT, json={**_VALID_BODY, "blueprint_name": ""})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Exact route path.
# ---------------------------------------------------------------------------


def test_router_exposes_exactly_the_frozen_endpoint_path() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}  # type: ignore[attr-defined]
    assert "/api/v1/information-element-evidence-fitness/resolve" in paths
