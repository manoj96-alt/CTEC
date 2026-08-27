"""Router-level tests for the Gate M Ontology Modeling API (CDD-028; Gate M
Artifact Authorization v1.1 §10, §18). These exercise authentication, scope
authorization (including that PUBLISH is never implied by APPROVE), and
malformed-request validation purely through FastAPI dependency overrides --
no database is required, since the application service/repository are
replaced with in-memory fakes that only ever see what the router actually
passes to them. Real canonical-write behavior is proven separately, against
real Postgres, in `test_ontology_modeling_proposal_lifecycle_postgres.py`."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.ontology_modeling.dependencies import (
    ontology_modeling_proposal_repository,
    ontology_modeling_service,
)
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.ontology_modeling.proposal import (
    OntologyChangeProposal,
    ProposalKind,
    ProposalStatus,
)
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
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
        principal_id="user-jane",
        tenant_id="tenant-a",
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _proposal(*, status: ProposalStatus = ProposalStatus.PROPOSED) -> OntologyChangeProposal:
    return OntologyChangeProposal(
        ontology_change_proposal_id=Identifier(uuid4()),
        proposal_kind=ProposalKind.CREATE_CONCEPT,
        status=status,
        proposed_entity_type_name="Warehouse",
        proposed_definition=None,
        proposed_relationship_type_name=None,
        proposed_source_entity_type_id=None,
        proposed_target_entity_type_id=None,
        proposed_by="user-jane",
        proposed_on=NOW,
    )


class FakeService:
    """Records every call, proves the router never writes canonical state
    itself (nothing here touches `entity_types`/`relationship_types`)."""

    def __init__(self, *, result: OntologyChangeProposal | None = None) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.result = result if result is not None else _proposal()
        self.raise_on_call: Exception | None = None

    def propose_concept(self, **kwargs: Any) -> OntologyChangeProposal:
        self.calls.append(("propose_concept", (kwargs,)))
        if self.raise_on_call:
            raise self.raise_on_call
        return self.result

    def propose_relationship(self, **kwargs: Any) -> OntologyChangeProposal:
        self.calls.append(("propose_relationship", (kwargs,)))
        if self.raise_on_call:
            raise self.raise_on_call
        return self.result

    def approve(self, **kwargs: Any) -> OntologyChangeProposal:
        self.calls.append(("approve", (kwargs,)))
        if self.raise_on_call:
            raise self.raise_on_call
        return self.result

    def reject(self, **kwargs: Any) -> OntologyChangeProposal:
        self.calls.append(("reject", (kwargs,)))
        if self.raise_on_call:
            raise self.raise_on_call
        return self.result

    def publish(self, **kwargs: Any) -> OntologyChangeProposal:
        self.calls.append(("publish", (kwargs,)))
        if self.raise_on_call:
            raise self.raise_on_call
        return self.result


class FakeRepository:
    def __init__(self, *, proposal: OntologyChangeProposal | None = None) -> None:
        self.proposal = proposal
        self.calls: list[str] = []

    def get_by_id(self, ontology_change_proposal_id: UUID) -> OntologyChangeProposal | None:
        self.calls.append("get_by_id")
        return self.proposal

    def list(self, *, status: ProposalStatus | None = None) -> list[OntologyChangeProposal]:
        self.calls.append("list")
        return [self.proposal] if self.proposal is not None else []


def _client(
    app_container: Container,
    service: FakeService,
    repository: FakeRepository,
    authenticated: TrustedPrincipal,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: app_container
    app.dependency_overrides[ontology_modeling_service] = lambda: service
    app.dependency_overrides[ontology_modeling_proposal_repository] = lambda: repository
    return TestClient(app)


def _container(*, audit: Audit | None = None) -> Container:
    return Container(Settings(), security_audit=audit)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Authentication / scope enforcement.
# ---------------------------------------------------------------------------


def test_missing_bearer_token_rejects_before_service_disclosure() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/ontology-modeling/proposals",
            json={"proposal_kind": "CreateConcept", "entity_type_name": "Warehouse"},
        )
    assert response.status_code == 401


def test_propose_requires_the_propose_scope() -> None:
    service = FakeService()
    client = _client(_container(audit=Audit()), service, FakeRepository(), _principal(scopes=()))
    response = client.post(
        "/api/v1/ontology-modeling/proposals",
        json={"proposal_kind": "CreateConcept", "entity_type_name": "Warehouse"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_propose_scope_is_sufficient_for_propose() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("ontology-modeling:propose",)),
    )
    response = client.post(
        "/api/v1/ontology-modeling/proposals",
        json={"proposal_kind": "CreateConcept", "entity_type_name": "Warehouse"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Proposed"
    assert service.calls[0][0] == "propose_concept"


def test_approve_requires_the_approve_scope_not_propose() -> None:
    proposal = _proposal()
    service = FakeService(result=proposal)
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(proposal=proposal),
        _principal(scopes=("ontology-modeling:propose",)),
    )
    response = client.post(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}/approve"
    )
    assert response.status_code == 403
    assert service.calls == []


def test_publish_is_denied_when_only_approve_scope_is_held() -> None:
    """The core AA v1.1 §7/§14 invariant: approve authority never implies
    publish authority."""
    proposal = _proposal(status=ProposalStatus.APPROVED)
    service = FakeService(result=proposal)
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(proposal=proposal),
        _principal(scopes=("ontology-modeling:approve",)),
    )
    response = client.post(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}/publish"
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_publish_scope_is_sufficient_for_publish() -> None:
    proposal = _proposal(status=ProposalStatus.APPROVED)
    published = _proposal(status=ProposalStatus.PUBLISHED)
    service = FakeService(result=published)
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(proposal=proposal),
        _principal(scopes=("ontology-modeling:publish",)),
    )
    response = client.post(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}/publish"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Published"
    assert service.calls[0][0] == "publish"


def test_get_and_list_accept_either_propose_or_approve_scope() -> None:
    proposal = _proposal()
    repository = FakeRepository(proposal=proposal)
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        repository,
        _principal(scopes=("ontology-modeling:approve",)),
    )
    response = client.get(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}"
    )
    assert response.status_code == 200
    list_response = client.get("/api/v1/ontology-modeling/proposals")
    assert list_response.status_code == 200
    assert len(list_response.json()["proposals"]) == 1


def test_get_unknown_proposal_returns_404() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        FakeRepository(proposal=None),
        _principal(scopes=("ontology-modeling:propose",)),
    )
    response = client.get(f"/api/v1/ontology-modeling/proposals/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PROPOSAL_NOT_FOUND"


# ---------------------------------------------------------------------------
# GAP-11-FOLLOWUP-1 (Ontology-Modeling Read Authority Artifact Authorization
# Amendment): ontology-modeling:read is non-consequential read/list/get
# authority only. It is sufficient for GET/list, backward compatibility
# with :propose/:approve holders is preserved, and :read alone can never
# propose, approve, reject, or publish.
# ---------------------------------------------------------------------------


def test_read_scope_is_sufficient_for_get_and_list() -> None:
    proposal = _proposal()
    repository = FakeRepository(proposal=proposal)
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        repository,
        _principal(scopes=("ontology-modeling:read",)),
    )
    response = client.get(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}"
    )
    assert response.status_code == 200
    list_response = client.get("/api/v1/ontology-modeling/proposals")
    assert list_response.status_code == 200
    assert len(list_response.json()["proposals"]) == 1


def test_propose_scope_alone_still_grants_get_and_list() -> None:
    """Backward compatibility: existing :propose holders retain GET/list
    access exactly as before, unaffected by the new :read scope."""
    proposal = _proposal()
    repository = FakeRepository(proposal=proposal)
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        repository,
        _principal(scopes=("ontology-modeling:propose",)),
    )
    response = client.get(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}"
    )
    assert response.status_code == 200
    list_response = client.get("/api/v1/ontology-modeling/proposals")
    assert list_response.status_code == 200


def test_read_scope_alone_cannot_propose() -> None:
    service = FakeService()
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(),
        _principal(scopes=("ontology-modeling:read",)),
    )
    response = client.post(
        "/api/v1/ontology-modeling/proposals",
        json={"proposal_kind": "CreateConcept", "entity_type_name": "Warehouse"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_read_scope_alone_cannot_approve() -> None:
    proposal = _proposal()
    service = FakeService(result=proposal)
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(proposal=proposal),
        _principal(scopes=("ontology-modeling:read",)),
    )
    response = client.post(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}/approve"
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_read_scope_alone_cannot_reject() -> None:
    proposal = _proposal()
    service = FakeService(result=proposal)
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(proposal=proposal),
        _principal(scopes=("ontology-modeling:read",)),
    )
    response = client.post(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}/reject",
        json={"rejection_reason": None},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


def test_read_scope_alone_cannot_publish() -> None:
    proposal = _proposal(status=ProposalStatus.APPROVED)
    service = FakeService(result=proposal)
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(proposal=proposal),
        _principal(scopes=("ontology-modeling:read",)),
    )
    response = client.post(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}/publish"
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_SCOPE_REQUIRED"
    assert service.calls == []


# ---------------------------------------------------------------------------
# Validation / invalid-transition surfacing.
# ---------------------------------------------------------------------------


def test_propose_missing_entity_type_name_for_concept_returns_422() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        FakeRepository(),
        _principal(scopes=("ontology-modeling:propose",)),
    )
    response = client.post(
        "/api/v1/ontology-modeling/proposals", json={"proposal_kind": "CreateConcept"}
    )
    assert response.status_code == 422


def test_invalid_proposal_kind_returns_400() -> None:
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        FakeRepository(),
        _principal(scopes=("ontology-modeling:propose",)),
    )
    response = client.post(
        "/api/v1/ontology-modeling/proposals",
        json={"proposal_kind": "DeleteConcept", "entity_type_name": "x"},
    )
    assert response.status_code == 400


def test_approve_surfaces_invalid_transition_as_409() -> None:
    proposal = _proposal(status=ProposalStatus.PUBLISHED)
    service = FakeService(result=proposal)
    service.raise_on_call = ValidationException(
        "Only a Proposed OntologyChangeProposal may be approved"
    )
    client = _client(
        _container(audit=Audit()),
        service,
        FakeRepository(proposal=proposal),
        _principal(scopes=("ontology-modeling:approve",)),
    )
    response = client.post(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}/approve"
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INVALID_PROPOSAL_TRANSITION"


# ---------------------------------------------------------------------------
# No endpoint beyond the six authorized (no PUT/PATCH/DELETE).
# ---------------------------------------------------------------------------


def test_no_delete_or_patch_endpoint_exists() -> None:
    proposal = _proposal()
    client = _client(
        _container(audit=Audit()),
        FakeService(),
        FakeRepository(proposal=proposal),
        _principal(scopes=("ontology-modeling:propose", "ontology-modeling:approve")),
    )
    delete_response = client.delete(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}"
    )
    patch_response = client.patch(
        f"/api/v1/ontology-modeling/proposals/{proposal.ontology_change_proposal_id.value}"
    )
    assert delete_response.status_code == 405
    assert patch_response.status_code == 405


# ---------------------------------------------------------------------------
# Keycloak configuration (GAP-11; CDD-028 Keycloak Scope Defect
# Authorization). Mirrors test_information_element_context_router.py's own
# structural realm-parsing pattern, scoped to this router's own three frozen
# scope literals -- all three are optional, none is default (not granted to
# the primary demo persona).
# ---------------------------------------------------------------------------


def test_keycloak_gate_m_scopes_are_optional_not_default() -> None:
    import json
    from pathlib import Path

    realm = json.loads((Path(__file__).parents[3] / "keycloak" / "ctec-realm.json").read_text())
    scope_names = {block["name"] for block in realm["clientScopes"]}
    client = realm["clients"][0]
    default_scopes = set(client["defaultClientScopes"])
    optional_scopes = set(client["optionalClientScopes"])

    gate_m_scopes = {
        "ontology-modeling:propose",
        "ontology-modeling:approve",
        "ontology-modeling:publish",
    }
    assert gate_m_scopes <= scope_names
    assert gate_m_scopes <= optional_scopes
    assert gate_m_scopes.isdisjoint(default_scopes)


# ---------------------------------------------------------------------------
# GAP-11-FOLLOWUP-1 (Ontology-Modeling Read Authority Artifact Authorization
# Amendment): ontology-modeling:read is non-consequential and default-granted
# -- the opposite classification from the three scopes above, which remain
# unaffected by this addition.
# ---------------------------------------------------------------------------


def test_keycloak_gate_m_read_scope_is_default_not_optional() -> None:
    import json
    from pathlib import Path

    realm = json.loads((Path(__file__).parents[3] / "keycloak" / "ctec-realm.json").read_text())
    scope_names = [block["name"] for block in realm["clientScopes"]]
    client = realm["clients"][0]
    default_scopes = client["defaultClientScopes"]
    optional_scopes = client["optionalClientScopes"]

    assert scope_names.count("ontology-modeling:read") == 1
    assert default_scopes.count("ontology-modeling:read") == 1
    assert optional_scopes.count("ontology-modeling:read") == 0

    gate_m_write_scopes = {
        "ontology-modeling:propose",
        "ontology-modeling:approve",
        "ontology-modeling:publish",
    }
    assert gate_m_write_scopes <= set(optional_scopes)
    assert gate_m_write_scopes.isdisjoint(set(default_scopes))
