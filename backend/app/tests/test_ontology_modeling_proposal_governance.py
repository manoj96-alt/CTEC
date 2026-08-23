"""Unit-only acceptance evidence for Gate M proposal governance (CDD-028
§12-§20; Gate M Artifact Authorization v1.1 §4.4). Proves deterministic
validation, the Proposed/Approved/Rejected/Published lifecycle, the human
authorization boundary, and that only `publish()` ever writes a canonical
row -- entirely with hand-built fakes and a mocked `Session`, no database.
Real canonical-write/concurrency behavior is proven separately, against
real Postgres, in `test_ontology_modeling_proposal_lifecycle_postgres.py`."""

import ast
import inspect
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import ModuleType
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application import ontology_modeling_proposal_governance as gate_m_governance_module
from app.application.ontology_modeling_proposal_governance import (
    OntologyModelingProposalGovernanceApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.ontology_modeling.proposal import (
    OntologyChangeProposal,
    ProposalKind,
    ProposalStatus,
)
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier

_TENANT_ID = "acme-tenant"


class _FakeProposalRepository:
    def __init__(self) -> None:
        self.created: list[OntologyChangeProposal] = []
        self.updated: list[OntologyChangeProposal] = []

    def create(self, proposal: OntologyChangeProposal) -> None:
        self.created.append(proposal)

    def get_by_id(self, ontology_change_proposal_id: UUID) -> OntologyChangeProposal | None:
        for row in self.created + self.updated:
            if row.ontology_change_proposal_id.value == ontology_change_proposal_id:
                return row
        return None

    def update_status(self, proposal: OntologyChangeProposal) -> None:
        self.updated.append(proposal)

    def list(self, *, status: ProposalStatus | None = None) -> list[OntologyChangeProposal]:
        return list(self.created)


@dataclass
class _FakeSession:
    """Stand-in for the raw canonical-collision/endpoint-validation queries
    `publish()` issues via `session.scalar`/`session.execute` -- values are
    returned in call order. No real database, no `session.add` side
    effects beyond recording what was added (proving canonical writes only
    ever happen inside `publish()`)."""

    scalar_results: list[object] = field(default_factory=list)
    execute_results: list[object] = field(default_factory=list)
    added: list[Any] = field(default_factory=list)
    flushed: int = 0

    def scalar(self, _statement: object) -> object:
        return self.scalar_results.pop(0)

    def execute(self, _statement: object) -> object:
        return self.execute_results.pop(0)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        self.flushed += 1


class _OneResult:
    def __init__(self, value: tuple[object, ...] | None) -> None:
        self._value = value

    def one_or_none(self) -> tuple[object, ...] | None:
        return self._value


def _principal(*, scopes: tuple[str, ...] = ()) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="oidc-subject-jane",
        tenant_id=_TENANT_ID,
        scopes=scopes,
        roles=(),
        issuer="https://issuer.example",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )


def _service(
    session: _FakeSession, repository: _FakeProposalRepository
) -> OntologyModelingProposalGovernanceApplicationService:
    return OntologyModelingProposalGovernanceApplicationService(
        session=session,  # type: ignore[arg-type]
        proposal_repository=repository,
    )


def _proposed_concept(*, entity_type_name: str = "Warehouse") -> OntologyChangeProposal:
    return OntologyChangeProposal(
        ontology_change_proposal_id=Identifier(uuid4()),
        proposal_kind=ProposalKind.CREATE_CONCEPT,
        status=ProposalStatus.PROPOSED,
        proposed_entity_type_name=entity_type_name,
        proposed_definition="A storage facility.",
        proposed_relationship_type_name=None,
        proposed_source_entity_type_id=None,
        proposed_target_entity_type_id=None,
        proposed_by="oidc-subject-jane",
        proposed_on=datetime.now(UTC),
    )


def _proposed_relationship() -> OntologyChangeProposal:
    return OntologyChangeProposal(
        ontology_change_proposal_id=Identifier(uuid4()),
        proposal_kind=ProposalKind.CREATE_RELATIONSHIP,
        status=ProposalStatus.PROPOSED,
        proposed_entity_type_name=None,
        proposed_definition=None,
        proposed_relationship_type_name="storesAt",
        proposed_source_entity_type_id=Identifier(uuid4()),
        proposed_target_entity_type_id=Identifier(uuid4()),
        proposed_by="oidc-subject-jane",
        proposed_on=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# PROPOSE.
# ---------------------------------------------------------------------------


def test_propose_concept_creates_only_a_proposal_row() -> None:
    repository = _FakeProposalRepository()
    service = _service(_FakeSession(), repository)

    result = service.propose_concept(
        principal=_principal(), entity_type_name="Warehouse", definition="A storage facility."
    )

    assert result.status is ProposalStatus.PROPOSED
    assert result.proposed_by == "oidc-subject-jane"
    assert repository.created == [result]


def test_propose_relationship_creates_only_a_proposal_row() -> None:
    repository = _FakeProposalRepository()
    session = _FakeSession(
        execute_results=[_OneResult(("Active", "Approved")), _OneResult(("Active", "Approved"))]
    )
    service = _service(session, repository)
    source_id = Identifier(uuid4())
    target_id = Identifier(uuid4())

    result = service.propose_relationship(
        principal=_principal(),
        relationship_type_name="storesAt",
        source_entity_type_id=source_id,
        target_entity_type_id=target_id,
    )

    assert result.status is ProposalStatus.PROPOSED
    assert result.proposed_source_entity_type_id == source_id
    assert repository.created == [result]


def test_propose_requires_a_trusted_principal() -> None:
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.propose_concept(
            principal=None,  # type: ignore[arg-type]
            entity_type_name="Warehouse",
            definition=None,
        )


# ---------------------------------------------------------------------------
# APPROVE / REJECT -- zero canonical writes, exact state-transition contract.
# ---------------------------------------------------------------------------


def test_approve_transitions_the_same_proposal_and_performs_no_canonical_write() -> None:
    proposal = _proposed_concept()
    session = _FakeSession()
    repository = _FakeProposalRepository()
    service = _service(session, repository)

    approved = service.approve(principal=_principal(), proposal=proposal)

    assert approved.status is ProposalStatus.APPROVED
    assert approved.ontology_change_proposal_id == proposal.ontology_change_proposal_id
    assert approved.approved_by == "oidc-subject-jane"
    assert repository.updated == [approved]
    assert session.added == []  # no canonical write


def test_approve_requires_proposed_state() -> None:
    already_approved = _proposed_concept()
    object.__setattr__(already_approved, "status", ProposalStatus.APPROVED)
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.approve(principal=_principal(), proposal=already_approved)


def test_approve_requires_a_trusted_principal() -> None:
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.approve(principal=None, proposal=_proposed_concept())  # type: ignore[arg-type]


def test_reject_transitions_the_same_proposal_records_reason_and_performs_no_canonical_write() -> (
    None
):
    proposal = _proposed_concept()
    session = _FakeSession()
    repository = _FakeProposalRepository()
    service = _service(session, repository)

    rejected = service.reject(
        principal=_principal(), proposal=proposal, rejection_reason="Duplicate of Facility."
    )

    assert rejected.status is ProposalStatus.REJECTED
    assert rejected.rejected_by == "oidc-subject-jane"
    assert rejected.rejection_reason == "Duplicate of Facility."
    assert repository.updated == [rejected]
    assert session.added == []  # no canonical write


def test_reject_requires_proposed_state() -> None:
    already_rejected = _proposed_concept()
    object.__setattr__(already_rejected, "status", ProposalStatus.REJECTED)
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.reject(principal=_principal(), proposal=already_rejected, rejection_reason=None)


def test_reject_requires_a_trusted_principal() -> None:
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.reject(
            principal=None,  # type: ignore[arg-type]
            proposal=_proposed_concept(),
            rejection_reason=None,
        )


# ---------------------------------------------------------------------------
# PUBLISH -- the sole canonical write path.
# ---------------------------------------------------------------------------


def test_publish_requires_approved_state() -> None:
    proposal = _proposed_concept()  # still Proposed
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.publish(principal=_principal(), proposal=proposal)


def test_publish_requires_a_trusted_principal() -> None:
    proposal = _proposed_concept()
    object.__setattr__(proposal, "status", ProposalStatus.APPROVED)
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.publish(principal=None, proposal=proposal)  # type: ignore[arg-type]


def test_publish_concept_fails_closed_on_name_collision() -> None:
    proposal = _proposed_concept()
    object.__setattr__(proposal, "status", ProposalStatus.APPROVED)
    session = _FakeSession(scalar_results=[uuid4(), None])  # existing InstitutionalConcept found
    repository = _FakeProposalRepository()
    service = _service(session, repository)

    with pytest.raises(ValidationException):
        service.publish(principal=_principal(), proposal=proposal)

    assert session.added == []  # no partial canonical write
    assert repository.updated == []


def test_publish_relationship_fails_closed_when_source_endpoint_missing() -> None:
    proposal = _proposed_relationship()
    object.__setattr__(proposal, "status", ProposalStatus.APPROVED)
    session = _FakeSession(
        scalar_results=[None],  # no existing relationship-name collision
        execute_results=[_OneResult(None)],  # source EntityType not found
    )
    repository = _FakeProposalRepository()
    service = _service(session, repository)

    with pytest.raises(ValidationException):
        service.publish(principal=_principal(), proposal=proposal)

    assert session.added == []


def test_publish_relationship_fails_closed_when_target_endpoint_not_approved() -> None:
    proposal = _proposed_relationship()
    object.__setattr__(proposal, "status", ProposalStatus.APPROVED)
    session = _FakeSession(
        scalar_results=[None],
        execute_results=[_OneResult(("Active", "Approved")), _OneResult(("Active", "Proposed"))],
    )
    repository = _FakeProposalRepository()
    service = _service(session, repository)

    with pytest.raises(ValidationException):
        service.publish(principal=_principal(), proposal=proposal)

    assert session.added == []


def test_publish_concept_creates_canonical_rows_with_bootstrap_attribution_not_principal_id() -> (
    None
):
    proposal = _proposed_concept()
    object.__setattr__(proposal, "status", ProposalStatus.APPROVED)
    session = _FakeSession(scalar_results=[None, None])  # no collision
    repository = _FakeProposalRepository()
    service = _service(session, repository)

    published = service.publish(principal=_principal(), proposal=proposal)

    assert published.status is ProposalStatus.PUBLISHED
    assert published.published_by == "oidc-subject-jane"
    assert published.published_entity_type_id is not None
    assert len(session.added) == 2  # InstitutionalConcept + EntityType, nothing else
    for row in session.added:
        assert row.created_by == BOOTSTRAP_SYSTEM_ENTITY_ID
        assert row.governance_status == "Approved"
        assert row.version_number == 1
        assert row.previous_version_id is None
        assert str(row.created_by) != "oidc-subject-jane"
    assert repository.updated == [published]


def test_publish_relationship_creates_relationship_type_and_binding_atomically() -> None:
    proposal = _proposed_relationship()
    object.__setattr__(proposal, "status", ProposalStatus.APPROVED)
    session = _FakeSession(
        scalar_results=[None],
        execute_results=[_OneResult(("Active", "Approved")), _OneResult(("Active", "Approved"))],
    )
    repository = _FakeProposalRepository()
    service = _service(session, repository)

    published = service.publish(principal=_principal(), proposal=proposal)

    assert published.status is ProposalStatus.PUBLISHED
    assert published.published_relationship_type_id is not None
    assert len(session.added) == 2  # RelationshipType + OntologyRelationshipBinding
    relationship_row, binding_row = session.added
    assert relationship_row.created_by == BOOTSTRAP_SYSTEM_ENTITY_ID
    assert relationship_row.governance_status == "Approved"
    assert binding_row.relationship_type_id == relationship_row.relationship_type_id


def test_publish_only_writes_via_session_add_never_via_entity_type_repository() -> None:
    imported = _module_imported_names(gate_m_governance_module)
    assert not any("entity_type_repository" in name for name in imported)
    assert not any("relationship_type_repository" in name for name in imported)


# ---------------------------------------------------------------------------
# State-transition contract -- exhaustively invalid transitions fail closed.
# ---------------------------------------------------------------------------


def test_reject_then_approve_fails_closed() -> None:
    proposal = _proposed_concept()
    object.__setattr__(proposal, "status", ProposalStatus.REJECTED)
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.approve(principal=_principal(), proposal=proposal)


def test_published_cannot_republish() -> None:
    proposal = _proposed_concept()
    object.__setattr__(proposal, "status", ProposalStatus.PUBLISHED)
    service = _service(_FakeSession(), _FakeProposalRepository())
    with pytest.raises(ValidationException):
        service.publish(principal=_principal(), proposal=proposal)


# ---------------------------------------------------------------------------
# Production-module import hygiene.
# ---------------------------------------------------------------------------


def _module_imported_names(module: ModuleType) -> set[str]:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom | ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_production_module_imports_no_ai_sdk_or_model_provider() -> None:
    imported = _module_imported_names(gate_m_governance_module)
    forbidden_substrings = ("openai", "anthropic", "langchain", "azure")
    for name in imported:
        lowered = name.lower()
        assert not any(term in lowered for term in forbidden_substrings)


def test_production_module_imports_no_gate_l_semantic_mapping_module() -> None:
    imported = _module_imported_names(gate_m_governance_module)
    assert not any("semantic_mapping" in name for name in imported)


def test_production_module_imports_no_resolver() -> None:
    imported = _module_imported_names(gate_m_governance_module)
    assert not any(name.endswith("ontology.resolver") for name in imported)
