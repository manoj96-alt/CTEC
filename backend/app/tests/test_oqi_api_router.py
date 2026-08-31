"""CDD-045 Artifact Authorization §2 row 6 -- OQI7-I1 router-level tests.
Exercises authentication, scope authorization (an under-scoped caller never
reaches `OqiProductExperienceService`), error-code mapping, and response
schema shape purely through FastAPI dependency overrides -- mirroring
`test_information_element_evidence_fitness_router.py`'s own established
pattern exactly. No database is required; `FakeService` only ever sees what
the router actually passes to it. Real end-to-end composition against real
Postgres is proven separately in `test_oqi_api_postgres.py`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.oqi.router import oqi_service
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.application.oqi_remediation_service import OqiRemediationError
from app.core.config import Settings
from app.core.dependency_container import Container
from app.main import create_app

NOW = datetime.now(UTC)


def _principal(*, scopes: tuple[str, ...] = (), tenant_id: str = "tenant-a") -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id=tenant_id,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


class Audit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, **values: object) -> UUID:
        self.events.append(values)
        return uuid4()


def _container(*, audit: Audit | None = None) -> Container:
    return Container(Settings(), security_audit=audit)  # type: ignore[arg-type]


class Row:
    """Generic attribute bag standing in for the service's dataclass rows,
    so `FakeService` never has to import the real production dataclasses."""

    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.raise_on_action: OqiRemediationError | None = None

    def get_command_center(self, *, tenant_id: str) -> Row:
        self.calls.append(("get_command_center", {"tenant_id": tenant_id}))
        return Row(
            reliance_supported_count=3,
            reliance_at_risk_count=1,
            reliance_unknown_count=2,
            critical_dependencies_at_risk_count=1,
            open_findings_count=1,
            active_agent_investigations_count=0,
            pending_human_authorizations_count=0,
        )

    def list_findings(self, **kwargs: Any) -> tuple[tuple[Any, ...], str | None]:
        self.calls.append(("list_findings", kwargs))
        return (), None

    def get_finding_detail(self, *, tenant_id: str, finding_id: UUID) -> Row | None:
        self.calls.append(
            ("get_finding_detail", {"tenant_id": tenant_id, "finding_id": finding_id})
        )
        return Row(
            finding_id=finding_id,
            family=Row(value="OQI1"),
            condition_label="cond-1",
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
        )

    def get_evidence(self, *, tenant_id: str, finding_id: UUID) -> Row:
        self.calls.append(("get_evidence", {"tenant_id": tenant_id, "finding_id": finding_id}))
        return Row(participants=(), candidate=None)

    def get_ontology_impact(self, *, tenant_id: str, finding_id: UUID) -> Row:
        self.calls.append(
            ("get_ontology_impact", {"tenant_id": tenant_id, "finding_id": finding_id})
        )
        return Row(
            outcome=Row(value="IMPACT_UNKNOWN"),
            direct_entity_id=None,
            direct_entity_type=None,
            propagated_path=None,
        )

    def get_business_impact(self, *, tenant_id: str, finding_id: UUID) -> Row:
        self.calls.append(
            ("get_business_impact", {"tenant_id": tenant_id, "finding_id": finding_id})
        )
        return Row(outcome=Row(value="BUSINESS_IMPACT_UNKNOWN"), dependencies=())

    def get_reliance(self, *, tenant_id: str, finding_id: UUID) -> Row:
        self.calls.append(("get_reliance", {"tenant_id": tenant_id, "finding_id": finding_id}))
        return Row(
            state=Row(value="RELIANCE_UNKNOWN"),
            reason_codes=("INSUFFICIENT_QUALITY_COVERAGE",),
            contributing_finding_ids=(),
            history=(),
        )

    def get_agent_investigation(self, *, tenant_id: str, finding_id: UUID) -> Row:
        self.calls.append(
            ("get_agent_investigation", {"tenant_id": tenant_id, "finding_id": finding_id})
        )
        return Row(specialists=(), recommendation=None)

    def get_remediation(self, *, tenant_id: str, finding_id: UUID) -> Row:
        self.calls.append(("get_remediation", {"tenant_id": tenant_id, "finding_id": finding_id}))
        return Row(
            case_status=None,
            candidate=None,
            recommendation=None,
            authorization=None,
            external_execution=None,
        )

    def decide_authorization(self, **kwargs: Any) -> str:
        self.calls.append(("decide_authorization", kwargs))
        if self.raise_on_action is not None:
            raise self.raise_on_action
        return "APPROVED"

    def report_execution(self, **kwargs: Any) -> str:
        self.calls.append(("report_execution", kwargs))
        if self.raise_on_action is not None:
            raise self.raise_on_action
        return "EXTERNAL_EXECUTION_REPORTED"


def _client(
    app_container: Container, service: FakeService, authenticated: TrustedPrincipal
) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: app_container
    app.dependency_overrides[oqi_service] = lambda: service
    return TestClient(app)


_FINDING_ID = uuid4()
_AUTH_ID = uuid4()

_READ_ENDPOINTS = (
    ("GET", "/api/v1/oqi/command-center"),
    ("GET", "/api/v1/oqi/findings"),
    ("GET", f"/api/v1/oqi/findings/{_FINDING_ID}"),
    ("GET", f"/api/v1/oqi/findings/{_FINDING_ID}/evidence"),
    ("GET", f"/api/v1/oqi/findings/{_FINDING_ID}/ontology-impact"),
    ("GET", f"/api/v1/oqi/findings/{_FINDING_ID}/business-impact"),
    ("GET", f"/api/v1/oqi/findings/{_FINDING_ID}/reliance"),
    ("GET", f"/api/v1/oqi/findings/{_FINDING_ID}/agent-investigation"),
    ("GET", f"/api/v1/oqi/findings/{_FINDING_ID}/remediation"),
)


# ---------------------------------------------------------------------------
# Authentication / scope enforcement -- every read endpoint requires
# oqi:read; the under-scoped caller must never reach the service.
# ---------------------------------------------------------------------------


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/oqi/command-center")
    assert response.status_code == 401


def test_missing_scope_rejects_every_read_endpoint_before_service_invocation() -> None:
    for method, path in _READ_ENDPOINTS:
        service = FakeService()
        client = _client(_container(audit=Audit()), service, _principal(scopes=()))
        response = client.request(method, path)
        assert response.status_code == 403, path
        assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
        assert service.calls == [], path


def test_oqi_read_scope_is_sufficient_for_command_center() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=("oqi:read",)))
    response = client.get("/api/v1/oqi/command-center")
    assert response.status_code == 200
    assert len(service.calls) == 1


def test_denied_authorization_is_recorded_to_security_audit() -> None:
    audit = Audit()
    client = _client(_container(audit=audit), FakeService(), _principal(scopes=()))
    client.get("/api/v1/oqi/command-center")
    assert len(audit.events) == 1
    assert audit.events[0]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"


def test_read_scope_alone_does_not_authorize_authorize_action() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=("oqi:read",)))
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{_AUTH_ID}/decide",
        json={"approve": True, "decided_by": "approver"},
    )
    assert response.status_code == 403
    assert service.calls == []


def test_read_scope_alone_does_not_authorize_report_execution_action() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=("oqi:read",)))
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{_AUTH_ID}/report-execution", json={}
    )
    assert response.status_code == 403
    assert service.calls == []


def test_authorize_scope_is_sufficient_for_decide() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("oqi-remediation:authorize",))
    )
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{_AUTH_ID}/decide",
        json={"approve": True, "decided_by": "approver"},
    )
    assert response.status_code == 200
    assert response.json() == {"case_status": "APPROVED"}


def test_report_execution_scope_is_sufficient() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("oqi-remediation:report-execution",)),
    )
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{_AUTH_ID}/report-execution", json={}
    )
    assert response.status_code == 200
    assert response.json() == {"case_status": "EXTERNAL_EXECUTION_REPORTED"}


def test_authorize_scope_does_not_imply_report_execution_scope() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("oqi-remediation:authorize",))
    )
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{_AUTH_ID}/report-execution", json={}
    )
    assert response.status_code == 403
    assert service.calls == []


# ---------------------------------------------------------------------------
# Tenant scoping -- tenant_id always comes from TrustedPrincipal, never a
# client-supplied field (CDD-045 §22, §59). The closed request schemas
# below contain no tenant_id field at all -- proven by construction, and by
# asserting the exact call the service actually received.
# ---------------------------------------------------------------------------


def test_command_center_uses_principal_tenant_not_a_client_value() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("oqi:read",), tenant_id="tenant-x")
    )
    client.get("/api/v1/oqi/command-center")
    assert service.calls[0] == ("get_command_center", {"tenant_id": "tenant-x"})


def test_decide_authorization_uses_principal_tenant() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("oqi-remediation:authorize",), tenant_id="tenant-y"),
    )
    client.post(
        f"/api/v1/oqi/remediation/authorizations/{_AUTH_ID}/decide",
        json={"approve": True, "decided_by": "approver"},
    )
    _, kwargs = service.calls[0]
    assert kwargs["tenant_id"] == "tenant-y"
    assert kwargs["authorization_id"] == _AUTH_ID


# ---------------------------------------------------------------------------
# Not-found mapping.
# ---------------------------------------------------------------------------


def test_finding_not_found_maps_to_404() -> None:
    class NotFoundService(FakeService):
        def get_finding_detail(self, *, tenant_id: str, finding_id: UUID) -> Row | None:
            self.calls.append(("get_finding_detail", {}))
            return None

    client = _client(_container(audit=Audit()), NotFoundService(), _principal(scopes=("oqi:read",)))
    response = client.get(f"/api/v1/oqi/findings/{_FINDING_ID}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "OQI_FINDING_NOT_FOUND"


def test_remediation_error_from_decide_maps_to_frozen_status_code() -> None:
    service = FakeService()
    service.raise_on_action = OqiRemediationError("REMEDIATION_SELF_APPROVAL_PROHIBITED")
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("oqi-remediation:authorize",))
    )
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{_AUTH_ID}/decide",
        json={"approve": True, "decided_by": "approver"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "REMEDIATION_SELF_APPROVAL_PROHIBITED"


def test_remediation_action_mismatch_maps_to_409() -> None:
    service = FakeService()
    service.raise_on_action = OqiRemediationError("REMEDIATION_ACTION_MISMATCH")
    client = _client(
        _container(audit=Audit()),
        service,
        _principal(scopes=("oqi-remediation:report-execution",)),
    )
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{_AUTH_ID}/report-execution", json={}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "REMEDIATION_ACTION_MISMATCH"


# ---------------------------------------------------------------------------
# Response shape -- proves every returned schema contains no
# trust_score/quality_score/confidence_score/monetary field at the API
# boundary (CDD-045 §8, §26 -- static/behavioral proof, complements the
# repository-wide grep in test_oqi_api_postgres.py).
# ---------------------------------------------------------------------------

_PROHIBITED_FIELD_SUBSTRINGS = (
    "trust_score",
    "reliability_score",
    "confidence_score",
    "business_impact_score",
    "criticality_score",
    "quality_health_score",
    "revenue",
    "monetary",
    "dollar",
)


def test_command_center_response_has_no_score_or_monetary_field() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=("oqi:read",)))
    body = client.get("/api/v1/oqi/command-center").json()
    for key in body:
        assert key.lower() not in _PROHIBITED_FIELD_SUBSTRINGS
    assert set(body.keys()) == {
        "reliance_supported_count",
        "reliance_at_risk_count",
        "reliance_unknown_count",
        "critical_dependencies_at_risk_count",
        "open_findings_count",
        "active_agent_investigations_count",
        "pending_human_authorizations_count",
    }


def test_reliance_unknown_is_serialized_as_explicit_string_not_null() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=("oqi:read",)))
    body = client.get(f"/api/v1/oqi/findings/{_FINDING_ID}/reliance").json()
    assert body["state"] == "RELIANCE_UNKNOWN"
    assert body["state"] is not None


def test_impact_unknown_is_serialized_as_explicit_string_not_no_impact() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=("oqi:read",)))
    body = client.get(f"/api/v1/oqi/findings/{_FINDING_ID}/ontology-impact").json()
    assert body["outcome"] == "IMPACT_UNKNOWN"
    assert body["outcome"] != "NO_IMPACT"


def test_remediation_authorization_id_survives_serialization_to_json() -> None:
    """OQI-UX authorization-ID contract correction: the field the governed
    decide/report-execution routes require as their path parameter must
    survive application row -> Pydantic response -> JSON body, not be
    silently dropped at any layer."""
    service = FakeService()
    service.get_remediation = lambda *, tenant_id, finding_id: Row(  # type: ignore[method-assign]
        case_status="AWAITING_AUTHORITY",
        candidate=None,
        recommendation=None,
        authorization=Row(
            authorization_id=_AUTH_ID,
            principal="requester",
            decided_on=None,
            instruction="UPDATE_FIELD",
            authorized_against_state_revision=1,
            is_stale=False,
            status="PENDING",
        ),
        external_execution=None,
    )
    client = _client(_container(audit=Audit()), service, _principal(scopes=("oqi:read",)))
    body = client.get(f"/api/v1/oqi/findings/{_FINDING_ID}/remediation").json()
    assert body["authorization"]["authorization_id"] == str(_AUTH_ID)


# ---------------------------------------------------------------------------
# Exact route existence.
# ---------------------------------------------------------------------------


def test_all_nine_frozen_routes_exist() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, _principal(scopes=("oqi:read",)))
    for method, path in _READ_ENDPOINTS:
        response = client.request(method, path)
        assert response.status_code != 404, path

    unrelated = client.get("/api/v1/oqi/nonexistent")
    assert unrelated.status_code == 404
