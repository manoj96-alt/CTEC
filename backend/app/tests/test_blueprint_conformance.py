"""Tests for `BlueprintConformanceApplicationService` (Gate G G4; CDD-018
§6-22; G4 Blueprint Conformance Artifact Authorization). Orchestration and
comparison-logic evidence uses `BlueprintApplicationService`-conforming and
`BlueprintConformanceContextStore`-conforming test doubles -- no PostgreSQL
dependency. Tenant-isolation and real context-store correctness require real
PostgreSQL (`migrated_engine`).
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_conformance import (
    BlueprintConformanceApplicationService,
    RequirementStatus,
)
from app.core.bootstrap import BOOTSTRAP_BUSINESS_DOMAIN_ID, BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
    RelationshipRequirement,
)
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.blueprint_conformance_context_store import (
    BlueprintConformanceContextStore,
)
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.ontology_seed import OntologySeeder

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TENANT_ID = "g4-test-tenant"

SUPPLIER_TYPE_ID = uuid4()
MATERIAL_TYPE_ID = uuid4()
FACILITY_TYPE_ID = uuid4()
SUPPLIES_TYPE_ID = uuid4()
ASSEMBLED_AT_TYPE_ID = uuid4()


class _FakeBlueprintService:
    def __init__(self, blueprint: Blueprint | None) -> None:
        self.blueprint = blueprint
        self.requested_names: list[str] = []

    def get_approved_by_name(self, blueprint_name: str) -> Blueprint | None:
        self.requested_names.append(blueprint_name)
        return self.blueprint


class _FakeContextStore:
    def __init__(
        self,
        entity_type_ids: frozenset[UUID] = frozenset(),
        relationship_triples: frozenset[tuple[UUID, UUID, UUID]] = frozenset(),
    ) -> None:
        self.entity_type_ids = entity_type_ids
        self.relationship_triples = relationship_triples
        self.requested_tenant_ids: list[str] = []

    def entity_type_ids_present(self, tenant_id: str) -> frozenset[UUID]:
        self.requested_tenant_ids.append(tenant_id)
        return self.entity_type_ids

    def relationship_triples_present(self, tenant_id: str) -> frozenset[tuple[UUID, UUID, UUID]]:
        self.requested_tenant_ids.append(tenant_id)
        return self.relationship_triples


def _blueprint(*, concept_requirements: tuple[ConceptRequirement, ...]) -> Blueprint:
    return Blueprint(
        blueprint_id=Identifier(uuid4()),
        blueprint_name=CanonicalName("CTEC Semiconductor Supply Chain Blueprint"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(uuid4()),
        created_on=NOW,
        concept_requirements=concept_requirements,
    )


def _mixed_blueprint() -> Blueprint:
    """One fully-satisfiable concept (Supplier, supplies -> Material, one
    REQUIRED information element) and one entirely unsatisfiable concept
    (Facility, assembledAt, one CONDITIONAL information element)."""
    supplier_id = Identifier(uuid4())
    facility_id = Identifier(uuid4())
    return _blueprint(
        concept_requirements=(
            ConceptRequirement(
                concept_requirement_id=supplier_id,
                blueprint_id=Identifier(uuid4()),
                entity_type_id=Identifier(SUPPLIER_TYPE_ID),
                obligation=Obligation.REQUIRED,
                relationship_requirements=(
                    RelationshipRequirement(
                        relationship_requirement_id=Identifier(uuid4()),
                        concept_requirement_id=supplier_id,
                        relationship_type_id=Identifier(SUPPLIES_TYPE_ID),
                        target_entity_type_id=Identifier(MATERIAL_TYPE_ID),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
                information_element_requirements=(
                    InformationElementRequirement(
                        information_element_requirement_id=Identifier(uuid4()),
                        concept_requirement_id=supplier_id,
                        element_name=CanonicalName("Supplier Legal Name"),
                        description=Description("The supplier's registered legal entity name."),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
            ),
            ConceptRequirement(
                concept_requirement_id=facility_id,
                blueprint_id=Identifier(uuid4()),
                entity_type_id=Identifier(FACILITY_TYPE_ID),
                obligation=Obligation.REQUIRED,
                relationship_requirements=(
                    RelationshipRequirement(
                        relationship_requirement_id=Identifier(uuid4()),
                        concept_requirement_id=facility_id,
                        relationship_type_id=Identifier(ASSEMBLED_AT_TYPE_ID),
                        target_entity_type_id=Identifier(SUPPLIER_TYPE_ID),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
                information_element_requirements=(
                    InformationElementRequirement(
                        information_element_requirement_id=Identifier(uuid4()),
                        concept_requirement_id=facility_id,
                        element_name=CanonicalName("Risk Event Severity"),
                        description=Description("Severity classification, where captured."),
                        obligation=Obligation.CONDITIONAL,
                    ),
                ),
            ),
        )
    )


def _partial_context() -> _FakeContextStore:
    """Contains Supplier and Material (and the supplies relationship), but
    not Facility or the assembledAt relationship."""
    return _FakeContextStore(
        entity_type_ids=frozenset({SUPPLIER_TYPE_ID, MATERIAL_TYPE_ID}),
        relationship_triples=frozenset({(SUPPLIES_TYPE_ID, SUPPLIER_TYPE_ID, MATERIAL_TYPE_ID)}),
    )


def test_concept_requirement_satisfied_when_matching_entity_present() -> None:
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    supplier_result = next(
        r
        for r in result.concept_results
        if r.evidence.startswith(f"Matching enterprise entity of type {SUPPLIER_TYPE_ID}")
    )
    assert supplier_result.status is RequirementStatus.SATISFIED


def test_concept_requirement_missing_when_no_matching_entity_present() -> None:
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    facility_result = next(r for r in result.concept_results if str(FACILITY_TYPE_ID) in r.evidence)
    assert facility_result.status is RequirementStatus.MISSING


def test_relationship_requirement_satisfied_when_matching_relationship_present() -> None:
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    supplies_result = next(
        r for r in result.relationship_results if str(SUPPLIES_TYPE_ID) in r.evidence
    )
    assert supplies_result.status is RequirementStatus.SATISFIED


def test_relationship_requirement_missing_when_no_matching_relationship_present() -> None:
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    assembled_at_result = next(
        r for r in result.relationship_results if str(ASSEMBLED_AT_TYPE_ID) in r.evidence
    )
    assert assembled_at_result.status is RequirementStatus.MISSING


def test_relationship_vocabulary_reference_alone_does_not_satisfy_a_requirement() -> None:
    """The Blueprint itself references `ASSEMBLED_AT_TYPE_ID`/`FACILITY_TYPE_ID`
    (i.e. the governed vocabulary is referenced), but no matching instance
    exists in the evaluated tenant's context -- this must still be MISSING,
    proving vocabulary reference alone is not sufficient."""
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    assert any(r.status is RequirementStatus.MISSING for r in result.concept_results)
    assert any(r.status is RequirementStatus.MISSING for r in result.relationship_results)


def test_information_element_requirements_are_always_not_evaluated() -> None:
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    assert len(result.information_element_results) == 2
    obligations = {r.obligation for r in result.information_element_results}
    assert obligations == {Obligation.REQUIRED, Obligation.CONDITIONAL}
    assert all(
        r.status is RequirementStatus.NOT_EVALUATED for r in result.information_element_results
    )


def test_required_information_element_not_evaluated_does_not_fail_structural_result() -> None:
    """A fully-satisfiable single-concept Blueprint whose only information
    element is REQUIRED and therefore NOT_EVALUATED must still be
    structurally conformant."""
    concept_id = Identifier(uuid4())
    blueprint = _blueprint(
        concept_requirements=(
            ConceptRequirement(
                concept_requirement_id=concept_id,
                blueprint_id=Identifier(uuid4()),
                entity_type_id=Identifier(SUPPLIER_TYPE_ID),
                obligation=Obligation.REQUIRED,
                information_element_requirements=(
                    InformationElementRequirement(
                        information_element_requirement_id=Identifier(uuid4()),
                        concept_requirement_id=concept_id,
                        element_name=CanonicalName("Supplier Legal Name"),
                        description=Description("x"),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
            ),
        )
    )
    context = _FakeContextStore(entity_type_ids=frozenset({SUPPLIER_TYPE_ID}))
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(blueprint), context_store=context
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    assert result.information_element_results[0].status is RequirementStatus.NOT_EVALUATED
    assert result.overall_conformant is True


def test_conditional_information_element_requires_no_activation_engine() -> None:
    """A CONDITIONAL information element must resolve to NOT_EVALUATED
    without raising, without any condition-expression evaluation, and
    without any special-case behavior distinguishing it from REQUIRED."""
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    conditional_result = next(
        r for r in result.information_element_results if r.obligation is Obligation.CONDITIONAL
    )
    assert conditional_result.status is RequirementStatus.NOT_EVALUATED


def test_structurally_conformant_overall_result() -> None:
    concept_id = Identifier(uuid4())
    blueprint = _blueprint(
        concept_requirements=(
            ConceptRequirement(
                concept_requirement_id=concept_id,
                blueprint_id=Identifier(uuid4()),
                entity_type_id=Identifier(SUPPLIER_TYPE_ID),
                obligation=Obligation.REQUIRED,
            ),
        )
    )
    context = _FakeContextStore(entity_type_ids=frozenset({SUPPLIER_TYPE_ID}))
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(blueprint), context_store=context
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    assert result.overall_conformant is True


def test_structurally_non_conformant_overall_result() -> None:
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    assert result.overall_conformant is False


def test_deterministic_result_ordering() -> None:
    blueprint = _mixed_blueprint()
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(blueprint), context_store=_partial_context()
    )
    first = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    second = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    assert [r.requirement_id for r in first.concept_results] == [
        r.requirement_id for r in second.concept_results
    ]
    assert [r.requirement_id for r in first.relationship_results] == [
        r.requirement_id for r in second.relationship_results
    ]
    assert [r.requirement_id for r in first.information_element_results] == [
        r.requirement_id for r in second.information_element_results
    ]
    assert sorted(r.requirement_id for r in first.concept_results) == [
        r.requirement_id for r in first.concept_results
    ]


def test_blueprint_resolution_is_deterministic() -> None:
    blueprint = _mixed_blueprint()
    fake_service = _FakeBlueprintService(blueprint)
    service = BlueprintConformanceApplicationService(
        blueprint_service=fake_service, context_store=_partial_context()
    )
    first = service.evaluate(blueprint_name="Canonical Blueprint", tenant_id=TENANT_ID)
    second = service.evaluate(blueprint_name="Canonical Blueprint", tenant_id=TENANT_ID)
    assert first.blueprint_id == second.blueprint_id == blueprint.blueprint_id.value
    assert fake_service.requested_names == ["Canonical Blueprint", "Canonical Blueprint"]


def test_blueprint_not_found_raises_explicit_failure() -> None:
    """Evaluation failure (Blueprint unresolvable) must raise, never return
    a fabricated or empty result."""
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(None), context_store=_FakeContextStore()
    )
    with pytest.raises(ValidationException, match="No Approved Blueprint found"):
        service.evaluate(blueprint_name="Nonexistent", tenant_id=TENANT_ID)


def test_non_conformance_is_a_returned_result_not_an_exception() -> None:
    """A MISSING requirement must not raise -- evaluate() returns normally
    with a MISSING status embedded in the result."""
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    assert result.overall_conformant is False
    assert isinstance(result.concept_results, tuple)


def test_explainability_evidence_present_for_every_result() -> None:
    service = BlueprintConformanceApplicationService(
        blueprint_service=_FakeBlueprintService(_mixed_blueprint()),
        context_store=_partial_context(),
    )
    result = service.evaluate(blueprint_name="x", tenant_id=TENANT_ID)
    all_results = (
        *result.concept_results,
        *result.relationship_results,
        *result.information_element_results,
    )
    assert all(r.evidence.strip() for r in all_results)


def test_service_module_contains_no_persistence_calls() -> None:
    source = (Path(__file__).parents[1] / "application" / "blueprint_conformance.py").read_text()
    forbidden = ("session.add", "session.commit", "session.flush", ".add(", ".commit(", ".flush(")
    assert not any(value in source for value in forbidden)


def test_service_module_does_not_import_blueprint_seeder() -> None:
    """Precise import/instantiation-shaped check -- not a bare substring
    scan, since the module's own docstring legitimately names
    `blueprint_seed.py`/`BlueprintSeeder` while explaining this exact
    exclusion."""
    source = (Path(__file__).parents[1] / "application" / "blueprint_conformance.py").read_text()
    forbidden = (
        "import blueprint_seed",
        "from app.infrastructure.persistence.blueprint_seed",
        "BlueprintSeeder(",
    )
    assert not any(value in source for value in forbidden)


def test_service_module_references_no_http_layer_object() -> None:
    source = (Path(__file__).parents[1] / "application" / "blueprint_conformance.py").read_text()
    forbidden = ("fastapi", "APIRouter", "Depends")
    assert not any(value in source for value in forbidden)


def _entity_type_id(session: Session, name: str) -> UUID:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return value


def _relationship_type_id(session: Session, name: str) -> UUID:
    value = session.scalar(
        select(RelationshipType.relationship_type_id).where(
            RelationshipType.relationship_type_name == name
        )
    )
    assert value is not None
    return value


def _entity(session: Session, *, tenant_id: str, name: str, type_name: str) -> UUID:
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            effective_to=None,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            modified_by=None,
            modified_on=None,
            version_number=1,
            previous_version_id=None,
            entity_type_id=_entity_type_id(session, type_name),
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _relate(
    session: Session, *, tenant_id: str, type_name: str, from_id: UUID, to_id: UUID
) -> UUID:
    relationship_id = uuid4()
    session.add(
        InstitutionalRelationship(
            institutional_relationship_id=relationship_id,
            tenant_id=tenant_id,
            institutional_relationship_name=f"{type_name}:{relationship_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            effective_to=None,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            modified_by=None,
            modified_on=None,
            version_number=1,
            previous_version_id=None,
            relationship_type_id=_relationship_type_id(session, type_name),
            from_entity_id=from_id,
            to_entity_id=to_id,
            superseded_by_id=None,
        )
    )
    session.flush()
    return relationship_id


def test_context_store_tenant_isolation(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_a = f"g4-tenant-a-{uuid4()}"
    tenant_b = f"g4-tenant-b-{uuid4()}"
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

        supplier_a = _entity(session, tenant_id=tenant_a, name="Supplier A", type_name="Supplier")
        material_a = _entity(session, tenant_id=tenant_a, name="Material A", type_name="Material")
        _relate(
            session,
            tenant_id=tenant_a,
            type_name="supplies",
            from_id=supplier_a,
            to_id=material_a,
        )
        _entity(session, tenant_id=tenant_b, name="Facility B", type_name="Facility")
        session.commit()

    with factory() as session:
        store = BlueprintConformanceContextStore(session)
        tenant_a_entity_types = store.entity_type_ids_present(tenant_a)
        tenant_b_entity_types = store.entity_type_ids_present(tenant_b)
        tenant_a_relationships = store.relationship_triples_present(tenant_a)
        tenant_b_relationships = store.relationship_triples_present(tenant_b)

        supplier_type_id = _entity_type_id(session, "Supplier")
        material_type_id = _entity_type_id(session, "Material")
        facility_type_id = _entity_type_id(session, "Facility")
        supplies_type_id = _relationship_type_id(session, "supplies")

    assert supplier_type_id in tenant_a_entity_types
    assert material_type_id in tenant_a_entity_types
    assert facility_type_id not in tenant_a_entity_types

    assert facility_type_id in tenant_b_entity_types
    assert supplier_type_id not in tenant_b_entity_types
    assert material_type_id not in tenant_b_entity_types

    assert (supplies_type_id, supplier_type_id, material_type_id) in tenant_a_relationships
    assert tenant_b_relationships == frozenset()
