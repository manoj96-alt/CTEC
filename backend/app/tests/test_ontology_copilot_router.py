"""Router-level tests for the Ask CTEC API (Gate D). These exercise
authentication, scope authorization, rate limiting, malformed-request
validation, and audit recording purely through FastAPI dependency
overrides -- no database is required, since the application service is
replaced with an in-memory fake that only ever sees what the router
actually passes to it (proving tenant identity comes from
TrustedPrincipal, not the request body)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.ontology_copilot.dependencies import ontology_copilot_api_service
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.api.supplier_risk.rate_limit import RateLimiter
from app.application.information_element_evidence_availability import EvidenceAvailabilityStatus
from app.application.ontology_copilot_api import (
    AskResult,
    AskStatus,
    GatePAskStatus,
    InformationElementContextExplanationResult,
)
from app.application.semantic_coverage_evaluation import CoverageStatus
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.blueprint import Obligation
from app.main import create_app

NOW = datetime.now(UTC)


class Audit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, **values: object) -> UUID:
        self.events.append(values)
        return uuid4()


def _principal(*, tenant_id: str = "tenant-a", scopes: tuple[str, ...] = ()) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id=tenant_id,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


@dataclass
class FakeOntologyCopilotService:
    calls: list[tuple[Any, ...]] = field(default_factory=list)
    result: AskResult | None = None

    def ask(self, principal: TrustedPrincipal, question: str) -> AskResult:
        self.calls.append((principal, question))
        assert self.result is not None
        return self.result


def _client(
    app_container: Container, service: FakeOntologyCopilotService, authenticated: TrustedPrincipal
) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: app_container
    app.dependency_overrides[ontology_copilot_api_service] = lambda: service
    return TestClient(app)


def _container(*, audit: Audit | None = None, rate_limiter: RateLimiter | None = None) -> Container:
    return Container(
        Settings(),
        security_audit=audit,  # type: ignore[arg-type]
        rate_limiter=rate_limiter,
    )


_ANSWERED_RESULT = AskResult(
    status=AskStatus.ANSWERED,
    intent=None,
    answer="2 products depend on TSMC:\n- Product A\n- Product B",
    resolved_entity=None,
    result_names=("Product A", "Product B"),
    evidence=(),
)


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/ontology-copilot/ask", json={"question": "x"})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_MISSING"


def test_ask_requires_the_ask_scope() -> None:
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(_container(audit=Audit()), service, _principal(scopes=()))
    response = client.post("/api/v1/ontology-copilot/ask", json={"question": "x"})
    assert response.status_code == 403
    assert response.json()["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_ask_scope_is_sufficient() -> None:
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post(
        "/api/v1/ontology-copilot/ask", json={"question": "Which products depend on TSMC?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["result_names"] == ["Product A", "Product B"]
    assert service.calls[0][1] == "Which products depend on TSMC?"


def test_rate_limiting_rejects_before_service_disclosure() -> None:
    class AlwaysDenyRateLimiter:
        def admit(self, tenant_id: str) -> bool:
            del tenant_id
            return False

    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(
        _container(audit=Audit(), rate_limiter=AlwaysDenyRateLimiter()),  # type: ignore[arg-type]
        service,
        _principal(scopes=("ontology-copilot:ask",)),
    )
    response = client.post("/api/v1/ontology-copilot/ask", json={"question": "x"})
    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"
    assert service.calls == []


def test_empty_question_is_rejected_as_malformed() -> None:
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post("/api/v1/ontology-copilot/ask", json={"question": ""})
    assert response.status_code == 422
    assert service.calls == []


def test_missing_question_field_is_rejected_as_malformed() -> None:
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post("/api/v1/ontology-copilot/ask", json={})
    assert response.status_code == 422
    assert service.calls == []


def test_unexpected_extra_field_is_rejected_as_malformed() -> None:
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": "x", "tenant_id": "attacker-supplied-tenant"},
    )
    assert response.status_code == 422
    assert service.calls == []


def test_overlong_question_is_rejected_as_malformed() -> None:
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post("/api/v1/ontology-copilot/ask", json={"question": "x" * 501})
    assert response.status_code == 422
    assert service.calls == []


def test_tenant_identity_comes_only_from_the_trusted_principal_never_the_body() -> None:
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    authenticated = _principal(tenant_id="tenant-real", scopes=("ontology-copilot:ask",))
    client = _client(_container(audit=Audit()), service, authenticated)
    client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": "Which products depend on TSMC?"},
    )
    called_principal, _question = service.calls[0]
    assert called_principal.tenant_id == "tenant-real"


def test_successful_ask_records_an_audit_event() -> None:
    audit = Audit()
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(_container(audit=audit), service, _principal(scopes=("ontology-copilot:ask",)))
    response = client.post(
        "/api/v1/ontology-copilot/ask", json={"question": "Which products depend on TSMC?"}
    )
    assert response.status_code == 200
    assert len(audit.events) == 1
    assert audit.events[0]["operation"] == "ASK_ONTOLOGY_QUESTION"
    assert audit.events[0]["outcome"] == "ANSWERED"


def test_no_match_result_still_returns_200_not_an_error() -> None:
    service = FakeOntologyCopilotService(
        result=AskResult(
            status=AskStatus.NO_MATCH,
            intent=None,
            answer="CTEC does not currently have sufficient governed ontology evidence.",
            resolved_entity=None,
            result_names=(),
            evidence=(),
            reason="NO_MATCHING_ENTITY",
        )
    )
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post(
        "/api/v1/ontology-copilot/ask", json={"question": "Which products depend on Nobody?"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "no_match"
    assert response.json()["reason"] == "NO_MATCHING_ENTITY"


def test_get_is_not_allowed_endpoint_is_logically_read_only_but_wired_as_post() -> None:
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.get("/api/v1/ontology-copilot/ask")
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# Gate P (CDD-025): response-schema mapping
# ---------------------------------------------------------------------------


def test_existing_supplier_intent_response_has_no_context_explanation_field_populated() -> None:
    # Backward compatibility: the existing intent's response must be
    # unaffected by the new optional Gate P field.
    service = FakeOntologyCopilotService(result=_ANSWERED_RESULT)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post(
        "/api/v1/ontology-copilot/ask", json={"question": "Which products depend on TSMC?"}
    )
    assert response.status_code == 200
    assert response.json()["context_explanation"] is None


def test_gate_p_answered_response_maps_context_explanation_fields() -> None:
    requirement_id = uuid4()
    blueprint_id = uuid4()
    gate_p_result = AskResult(
        status=AskStatus.ANSWERED,
        intent=None,
        answer="'Supplier Legal Name' in the Blueprint A Blueprint: ...",
        resolved_entity=None,
        result_names=(),
        evidence=(),
        reason=None,
        context_explanation=InformationElementContextExplanationResult(
            status=GatePAskStatus.ANSWERED,
            blueprint_id=blueprint_id,
            blueprint_version_number=1,
            information_element_requirement_id=requirement_id,
            information_element_name="Supplier Legal Name",
            obligation=Obligation.REQUIRED,
            coverage_status=CoverageStatus.MAPPED,
            evidence_availability_status=EvidenceAvailabilityStatus.EVIDENCE_PRESENT,
            answer="'Supplier Legal Name' in the Blueprint A Blueprint: ...",
            reason=None,
        ),
    )
    service = FakeOntologyCopilotService(result=gate_p_result)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": "What is the evidence status of Supplier Legal Name in Blueprint A?"},
    )
    assert response.status_code == 200
    body = response.json()["context_explanation"]
    assert body is not None
    assert body["status"] == "answered"
    assert body["blueprint_id"] == str(blueprint_id)
    assert body["blueprint_version_number"] == 1
    assert body["information_element_requirement_id"] == str(requirement_id)
    assert body["information_element_name"] == "Supplier Legal Name"
    assert body["obligation"] == "REQUIRED"
    assert body["coverage_status"] == "MAPPED"
    assert body["evidence_availability_status"] == "EVIDENCE_PRESENT"
    assert body["reason"] is None


def test_gate_p_blueprint_not_found_response_has_null_coverage_and_evidence_fields() -> None:
    gate_p_result = AskResult(
        status=AskStatus.NO_MATCH,
        intent=None,
        answer="CTEC does not currently have an Approved Blueprint named 'Nonexistent'.",
        resolved_entity=None,
        result_names=(),
        evidence=(),
        reason="BLUEPRINT_NOT_FOUND",
        context_explanation=InformationElementContextExplanationResult(
            status=GatePAskStatus.BLUEPRINT_NOT_FOUND,
            blueprint_id=None,
            blueprint_version_number=None,
            information_element_requirement_id=None,
            information_element_name=None,
            obligation=None,
            coverage_status=None,
            evidence_availability_status=None,
            answer="CTEC does not currently have an Approved Blueprint named 'Nonexistent'.",
            reason="BLUEPRINT_NOT_FOUND",
        ),
    )
    service = FakeOntologyCopilotService(result=gate_p_result)
    client = _client(
        _container(audit=Audit()), service, _principal(scopes=("ontology-copilot:ask",))
    )
    response = client.post(
        "/api/v1/ontology-copilot/ask",
        json={"question": "What is the evidence status of X in Nonexistent?"},
    )
    assert response.status_code == 200
    body = response.json()["context_explanation"]
    assert body["status"] == "blueprint_not_found"
    assert body["coverage_status"] is None
    assert body["evidence_availability_status"] is None
    assert body["information_element_requirement_id"] is None
