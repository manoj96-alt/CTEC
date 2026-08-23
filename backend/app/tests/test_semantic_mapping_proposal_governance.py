"""Unit-only acceptance evidence for Gate L proposal governance (CDD-027
§11-§13, §17-§18; AI-Assisted Semantic Mapping Candidate Discovery
Artifact Authorization §4.2, as corrected by the Human-Approver Attribution
Clarification and Remediation Report). Proves deterministic validation,
Proposed/Approved materialization semantics, the human-approval boundary,
and rejection semantics -- entirely with hand-built fakes, no database.
Real repository-enforced Approved-uniqueness/concurrency behavior is
proven separately, against real Postgres, in
`test_semantic_mapping_proposal_lifecycle_postgres.py`."""

import ast
import inspect
from dataclasses import dataclass
from datetime import UTC, datetime
from types import ModuleType
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application import semantic_mapping_proposal_governance as gate_l_governance_module
from app.application.semantic_mapping_candidate_discovery import (
    CandidateDiscoveryContext,
    CandidateSelection,
    CandidateSourceField,
)
from app.application.semantic_mapping_proposal_governance import (
    SemanticMappingProposalGovernanceApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.blueprint import Obligation
from app.domain.integration import SourceField
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepository,
    SemanticMappingResolution,
)
from app.infrastructure.persistence.source_field_repository import SourceFieldRepository

_TENANT_ID = "acme-tenant"


class _FakeSemanticMappingRepository:
    def __init__(self) -> None:
        self.created: list[SemanticMapping] = []

    def create(self, semantic_mapping: SemanticMapping) -> None:
        self.created.append(semantic_mapping)

    def get_by_id(self, semantic_mapping_id: UUID) -> SemanticMapping | None:
        for row in self.created:
            if row.semantic_mapping_id.value == semantic_mapping_id:
                return row
        return None

    def get_approved_by_information_element_requirement(
        self, information_element_requirement_id: UUID, tenant_id: str
    ) -> SemanticMappingResolution | None:
        return None


class _FakeSourceFieldRepository:
    def __init__(self, *, fields_by_id: dict[UUID, SourceField]) -> None:
        self._fields_by_id = fields_by_id

    def create(self, source_field: SourceField) -> None:
        raise NotImplementedError

    def get_by_id(self, source_field_id: UUID) -> SourceField | None:
        return self._fields_by_id.get(source_field_id)


@dataclass
class _FakeSession:
    """Minimal stand-in for the one raw tenant-resolution query this
    service issues outside the two narrow repositories. Returns
    pre-configured tenant_id values in call order."""

    tenant_ids: list[str | None]

    def scalar(self, _statement: object) -> str | None:
        return self.tenant_ids.pop(0)


def _service(
    *,
    session: _FakeSession,
    semantic_mapping_repository: _FakeSemanticMappingRepository,
    source_field_repository: _FakeSourceFieldRepository,
) -> SemanticMappingProposalGovernanceApplicationService:
    """Constructs the service under test against its real, narrow
    Session/Protocol dependencies -- the hand-built fakes above satisfy
    those contracts structurally/behaviorally but are intentionally not
    nominal subtypes, so the boundary is bridged here, once, via cast."""
    return SemanticMappingProposalGovernanceApplicationService(
        session=cast(Session, session),
        semantic_mapping_repository=cast(SemanticMappingRepository, semantic_mapping_repository),
        source_field_repository=cast(SourceFieldRepository, source_field_repository),
    )


def _source_field(*, source_object_id: UUID | None = None) -> tuple[UUID, SourceField]:
    source_field_id = uuid4()
    return source_field_id, SourceField(
        source_field_id=Identifier(source_field_id),
        source_object_id=Identifier(source_object_id or uuid4()),
        field_label=CanonicalName("NAME1"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=datetime.now(UTC),
    )


def _context(
    *, information_element_requirement_id: UUID, candidates: tuple[UUID, ...]
) -> CandidateDiscoveryContext:
    return CandidateDiscoveryContext(
        information_element_requirement_id=information_element_requirement_id,
        element_name="Supplier Legal Name",
        description="Legal name of the supplier entity",
        obligation=Obligation.REQUIRED,
        candidate_source_fields=tuple(
            CandidateSourceField(
                source_field_id=sid,
                field_label="NAME1",
                source_object_id=uuid4(),
                source_object_name="LFA1",
                source_system_id=uuid4(),
                source_system_name="H3 Demo ERP",
            )
            for sid in candidates
        ),
    )


def _principal(*, tenant_id: str = _TENANT_ID) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="oidc-subject-abc123",
        tenant_id=tenant_id,
        scopes=(),
        roles=(),
        issuer="https://issuer.example",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Deterministic validation + Proposed materialization.
# ---------------------------------------------------------------------------


def test_materialize_proposal_succeeds_for_valid_in_universe_candidate() -> None:
    source_field_id, source_field = _source_field()
    mapping_repo = _FakeSemanticMappingRepository()
    service = _service(
        session=_FakeSession(tenant_ids=[_TENANT_ID, None]),
        semantic_mapping_repository=mapping_repo,
        source_field_repository=_FakeSourceFieldRepository(
            fields_by_id={source_field_id: source_field}
        ),
    )
    context = _context(information_element_requirement_id=uuid4(), candidates=(source_field_id,))

    result = service.materialize_proposal(
        tenant_id=_TENANT_ID,
        candidate=CandidateSelection(source_field_id=source_field_id),
        context=context,
    )

    assert result.governance_status is GovernanceStatus.PROPOSED
    assert result.source_field_id.value == source_field_id
    assert (
        result.information_element_requirement_id.value
        == context.information_element_requirement_id
    )
    assert mapping_repo.created == [result]


def test_materialize_proposal_uses_fixed_system_identity_not_a_human() -> None:
    source_field_id, source_field = _source_field()
    service = _service(
        session=_FakeSession(tenant_ids=[_TENANT_ID, None]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(
            fields_by_id={source_field_id: source_field}
        ),
    )
    context = _context(information_element_requirement_id=uuid4(), candidates=(source_field_id,))

    result = service.materialize_proposal(
        tenant_id=_TENANT_ID,
        candidate=CandidateSelection(source_field_id=source_field_id),
        context=context,
    )

    assert result.created_by.value == BOOTSTRAP_SYSTEM_ENTITY_ID


def test_materialize_proposal_rejects_out_of_universe_candidate() -> None:
    source_field_id, source_field = _source_field()
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(
            fields_by_id={source_field_id: source_field}
        ),
    )
    context = _context(information_element_requirement_id=uuid4(), candidates=())

    with pytest.raises(ValidationException):
        service.materialize_proposal(
            tenant_id=_TENANT_ID,
            candidate=CandidateSelection(source_field_id=source_field_id),
            context=context,
        )


def test_materialize_proposal_rejects_hallucinated_source_field_not_found() -> None:
    hallucinated_id = uuid4()
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )
    context = _context(information_element_requirement_id=uuid4(), candidates=(hallucinated_id,))

    with pytest.raises(ValidationException):
        service.materialize_proposal(
            tenant_id=_TENANT_ID,
            candidate=CandidateSelection(source_field_id=hallucinated_id),
            context=context,
        )


def test_materialize_proposal_rejects_cross_tenant_source_field() -> None:
    source_field_id, source_field = _source_field()
    service = _service(
        session=_FakeSession(tenant_ids=["a-different-tenant"]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(
            fields_by_id={source_field_id: source_field}
        ),
    )
    context = _context(information_element_requirement_id=uuid4(), candidates=(source_field_id,))

    with pytest.raises(ValidationException):
        service.materialize_proposal(
            tenant_id=_TENANT_ID,
            candidate=CandidateSelection(source_field_id=source_field_id),
            context=context,
        )


def test_materialize_proposal_rejects_non_active_source_field() -> None:
    source_field_id, source_field = _source_field()
    retired_field = SourceField(
        source_field_id=source_field.source_field_id,
        source_object_id=source_field.source_object_id,
        field_label=source_field.field_label,
        lifecycle_state=LifecycleState.ARCHIVED,
        governance_status=GovernanceStatus.APPROVED,
        created_by=source_field.created_by,
        created_on=source_field.created_on,
    )
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(
            fields_by_id={source_field_id: retired_field}
        ),
    )
    context = _context(information_element_requirement_id=uuid4(), candidates=(source_field_id,))

    with pytest.raises(ValidationException):
        service.materialize_proposal(
            tenant_id=_TENANT_ID,
            candidate=CandidateSelection(source_field_id=source_field_id),
            context=context,
        )


def test_materialize_proposal_rejects_source_field_not_approved_governance_status() -> None:
    source_field_id, source_field = _source_field()
    ungoverned_field = SourceField(
        source_field_id=source_field.source_field_id,
        source_object_id=source_field.source_object_id,
        field_label=source_field.field_label,
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.PROPOSED,
        created_by=source_field.created_by,
        created_on=source_field.created_on,
    )
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(
            fields_by_id={source_field_id: ungoverned_field}
        ),
    )
    context = _context(information_element_requirement_id=uuid4(), candidates=(source_field_id,))

    with pytest.raises(ValidationException):
        service.materialize_proposal(
            tenant_id=_TENANT_ID,
            candidate=CandidateSelection(source_field_id=source_field_id),
            context=context,
        )


def test_materialize_proposal_rejects_malformed_candidate_type() -> None:
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )
    context = _context(information_element_requirement_id=uuid4(), candidates=())

    with pytest.raises(ValidationException):
        service.materialize_proposal(
            tenant_id=_TENANT_ID,
            candidate="not-a-candidate-selection",  # type: ignore[arg-type]
            context=context,
        )


# ---------------------------------------------------------------------------
# Human approval boundary.
# ---------------------------------------------------------------------------


def _proposed_mapping(
    *, source_field_id: UUID, information_element_requirement_id: UUID
) -> SemanticMapping:
    return SemanticMapping(
        semantic_mapping_id=Identifier(uuid4()),
        source_field_id=Identifier(source_field_id),
        information_element_requirement_id=Identifier(information_element_requirement_id),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.PROPOSED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=datetime.now(UTC),
    )


def test_approve_requires_a_trusted_principal() -> None:
    proposed = _proposed_mapping(
        source_field_id=uuid4(), information_element_requirement_id=uuid4()
    )
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )

    with pytest.raises(ValidationException):
        service.approve(proposed=proposed, principal=None)  # type: ignore[arg-type]


def test_approve_fails_for_wrong_tenant_principal() -> None:
    proposed = _proposed_mapping(
        source_field_id=uuid4(), information_element_requirement_id=uuid4()
    )
    service = _service(
        session=_FakeSession(tenant_ids=[_TENANT_ID]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )

    with pytest.raises(ValidationException):
        service.approve(proposed=proposed, principal=_principal(tenant_id="a-different-tenant"))


def test_approve_creates_new_approved_row_and_leaves_proposed_unchanged() -> None:
    proposed = _proposed_mapping(
        source_field_id=uuid4(), information_element_requirement_id=uuid4()
    )
    before = SemanticMapping(**{f: getattr(proposed, f) for f in proposed.__dataclass_fields__})
    mapping_repo = _FakeSemanticMappingRepository()
    service = _service(
        session=_FakeSession(tenant_ids=[_TENANT_ID]),
        semantic_mapping_repository=mapping_repo,
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )

    approved = service.approve(proposed=proposed, principal=_principal())

    assert approved.governance_status is GovernanceStatus.APPROVED
    assert approved.semantic_mapping_id != proposed.semantic_mapping_id
    assert approved.source_field_id == proposed.source_field_id
    assert (
        approved.information_element_requirement_id == proposed.information_element_requirement_id
    )
    assert proposed == before
    assert mapping_repo.created == [approved]


def test_approve_uses_fixed_system_identity_not_principal_id() -> None:
    proposed = _proposed_mapping(
        source_field_id=uuid4(), information_element_requirement_id=uuid4()
    )
    service = _service(
        session=_FakeSession(tenant_ids=[_TENANT_ID]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )

    approved = service.approve(proposed=proposed, principal=_principal())

    assert approved.created_by.value == BOOTSTRAP_SYSTEM_ENTITY_ID
    assert approved.modified_by is None
    assert str(approved.created_by.value) != "oidc-subject-abc123"


def test_approve_rejects_already_approved_proposed_row() -> None:
    already_approved = _proposed_mapping(
        source_field_id=uuid4(), information_element_requirement_id=uuid4()
    )
    object.__setattr__(already_approved, "governance_status", GovernanceStatus.APPROVED)
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )

    with pytest.raises(ValidationException):
        service.approve(proposed=already_approved, principal=_principal())


# ---------------------------------------------------------------------------
# Rejection semantics.
# ---------------------------------------------------------------------------


def test_reject_performs_no_repository_write() -> None:
    proposed = _proposed_mapping(
        source_field_id=uuid4(), information_element_requirement_id=uuid4()
    )
    mapping_repo = _FakeSemanticMappingRepository()
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=mapping_repo,
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )

    service.reject(proposed=proposed, principal=_principal())

    assert mapping_repo.created == []


def test_reject_requires_a_trusted_principal() -> None:
    proposed = _proposed_mapping(
        source_field_id=uuid4(), information_element_requirement_id=uuid4()
    )
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )

    with pytest.raises(ValidationException):
        service.reject(proposed=proposed, principal=None)  # type: ignore[arg-type]


def test_reject_rejects_a_non_proposed_row() -> None:
    already_approved = _proposed_mapping(
        source_field_id=uuid4(), information_element_requirement_id=uuid4()
    )
    object.__setattr__(already_approved, "governance_status", GovernanceStatus.APPROVED)
    service = _service(
        session=_FakeSession(tenant_ids=[]),
        semantic_mapping_repository=_FakeSemanticMappingRepository(),
        source_field_repository=_FakeSourceFieldRepository(fields_by_id={}),
    )

    with pytest.raises(ValidationException):
        service.reject(proposed=already_approved, principal=_principal())


def test_reject_does_not_introduce_a_new_governance_status() -> None:
    valid_statuses = {member.value for member in GovernanceStatus}
    assert valid_statuses == {"Proposed", "Approved", "Retired", "Archived"}


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


def test_production_module_imports_no_candidate_provider() -> None:
    imported = _module_imported_names(gate_l_governance_module)
    assert "SemanticMappingCandidateProvider" not in imported


def test_production_module_imports_no_gate_i_or_h2_service_class() -> None:
    imported = _module_imported_names(gate_l_governance_module)
    assert "SemanticCoverageEvaluationApplicationService" not in imported
    assert "SemanticMappingResolutionApplicationService" not in imported


def test_production_module_imports_no_gate_j_or_gate_p_dependency() -> None:
    imported = _module_imported_names(gate_l_governance_module)
    assert not any("gap_impact_remediation" in name for name in imported)
    assert not any("ontology_copilot" in name for name in imported)


def test_production_module_imports_no_ai_sdk_or_model_provider() -> None:
    imported = _module_imported_names(gate_l_governance_module)
    forbidden_substrings = ("openai", "anthropic", "langchain", "azure")
    for name in imported:
        lowered = name.lower()
        assert not any(term in lowered for term in forbidden_substrings)


def test_no_new_persistence_or_migration_import_exists() -> None:
    imported = _module_imported_names(gate_l_governance_module)
    assert not any("alembic" in name.lower() for name in imported)
    assert not any("api_security_audit" in name for name in imported)
