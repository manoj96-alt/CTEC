"""Unit tests for `GapImpactRemediationApplicationService` (Gate J J1/J2;
CDD-021 §6-§24; J1/J2 Gap Impact Context and Remediation Artifact
Authorization). Uses plain, directly-constructed `SemanticCoverageEvaluationResult`/
`Blueprint` fixtures -- no PostgreSQL dependency: this service performs no
I/O, so its unit-test evidence needs no test double or fake, only
already-in-memory objects.
"""

import inspect
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.gap_impact_remediation import (
    Direction,
    GapImpactContext,
    GapImpactRemediationApplicationService,
    RelationshipContextEntry,
    RemediationAction,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    InformationElementCoverageResult,
    SemanticCoverageEvaluationResult,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
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
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingResolution,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
BLUEPRINT_NAME = "Gate J Test Blueprint"

SUPPLIER_ENTITY_TYPE_ID = uuid4()
REGION_ENTITY_TYPE_ID = uuid4()
RISK_EVENT_ENTITY_TYPE_ID = uuid4()
FACILITY_ENTITY_TYPE_ID = uuid4()
LOCATED_IN_TYPE_ID = uuid4()
EXPOSED_TO_TYPE_ID = uuid4()
RELATES_TO_TYPE_ID = uuid4()


def _resolution(information_element_requirement_id: UUID) -> SemanticMappingResolution:
    return SemanticMappingResolution(
        semantic_mapping_id=uuid4(),
        source_field_id=uuid4(),
        source_object_id=uuid4(),
        source_system_id=uuid4(),
        information_element_requirement_id=information_element_requirement_id,
        created_by=uuid4(),
        created_on=NOW,
        modified_by=None,
        modified_on=None,
    )


def _element_requirement(
    *, obligation: Obligation, element_name: str = "Element"
) -> InformationElementRequirement:
    return InformationElementRequirement(
        information_element_requirement_id=Identifier(uuid4()),
        concept_requirement_id=Identifier(uuid4()),
        element_name=CanonicalName(element_name),
        description=Description("A test information element requirement."),
        obligation=obligation,
    )


def _coverage_result(
    *,
    element: InformationElementRequirement,
    status: CoverageStatus,
    resolution: SemanticMappingResolution | None,
) -> InformationElementCoverageResult:
    return InformationElementCoverageResult(
        information_element_requirement_id=element.information_element_requirement_id.value,
        obligation=element.obligation,
        status=status,
        resolution=resolution,
    )


def _evaluation_result(
    *results: InformationElementCoverageResult,
) -> SemanticCoverageEvaluationResult:
    return SemanticCoverageEvaluationResult(
        blueprint_id=uuid4(),
        blueprint_version_number=1,
        tenant_id="gate-j-test-tenant",
        evaluated_at=NOW,
        information_element_results=results,
    )


def _worked_example_blueprint() -> (
    tuple[Blueprint, InformationElementRequirement, InformationElementRequirement]
):
    """Mirrors CDD-021's own worked example structurally: Supplier (source of
    `locatedIn` -> Region), Region (source of `exposedTo` -> Risk Event),
    Risk Event (source of `relatesTo` -> Facility), giving Risk Event both an
    OUTGOING and an INCOMING relationship-context entry so the uniform-shape
    rule is proven across both directions on the same owning Concept."""
    blueprint_id = uuid4()
    supplier_legal_name = _element_requirement(
        obligation=Obligation.REQUIRED, element_name="Supplier Legal Name"
    )
    risk_event_severity = _element_requirement(
        obligation=Obligation.CONDITIONAL, element_name="Risk Event Severity"
    )

    supplier = ConceptRequirement(
        concept_requirement_id=Identifier(uuid4()),
        blueprint_id=Identifier(blueprint_id),
        entity_type_id=Identifier(SUPPLIER_ENTITY_TYPE_ID),
        obligation=Obligation.REQUIRED,
        relationship_requirements=(
            RelationshipRequirement(
                relationship_requirement_id=Identifier(uuid4()),
                concept_requirement_id=Identifier(uuid4()),
                relationship_type_id=Identifier(LOCATED_IN_TYPE_ID),
                target_entity_type_id=Identifier(REGION_ENTITY_TYPE_ID),
                obligation=Obligation.REQUIRED,
            ),
        ),
        information_element_requirements=(supplier_legal_name,),
    )
    region = ConceptRequirement(
        concept_requirement_id=Identifier(uuid4()),
        blueprint_id=Identifier(blueprint_id),
        entity_type_id=Identifier(REGION_ENTITY_TYPE_ID),
        obligation=Obligation.REQUIRED,
        relationship_requirements=(
            RelationshipRequirement(
                relationship_requirement_id=Identifier(uuid4()),
                concept_requirement_id=Identifier(uuid4()),
                relationship_type_id=Identifier(EXPOSED_TO_TYPE_ID),
                target_entity_type_id=Identifier(RISK_EVENT_ENTITY_TYPE_ID),
                obligation=Obligation.REQUIRED,
            ),
        ),
    )
    risk_event = ConceptRequirement(
        concept_requirement_id=Identifier(uuid4()),
        blueprint_id=Identifier(blueprint_id),
        entity_type_id=Identifier(RISK_EVENT_ENTITY_TYPE_ID),
        obligation=Obligation.REQUIRED,
        relationship_requirements=(
            RelationshipRequirement(
                relationship_requirement_id=Identifier(uuid4()),
                concept_requirement_id=Identifier(uuid4()),
                relationship_type_id=Identifier(RELATES_TO_TYPE_ID),
                target_entity_type_id=Identifier(FACILITY_ENTITY_TYPE_ID),
                obligation=Obligation.REQUIRED,
            ),
        ),
        information_element_requirements=(risk_event_severity,),
    )
    facility = ConceptRequirement(
        concept_requirement_id=Identifier(uuid4()),
        blueprint_id=Identifier(blueprint_id),
        entity_type_id=Identifier(FACILITY_ENTITY_TYPE_ID),
        obligation=Obligation.REQUIRED,
    )

    blueprint = Blueprint(
        blueprint_id=Identifier(blueprint_id),
        blueprint_name=CanonicalName(BLUEPRINT_NAME),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(supplier, region, risk_event, facility),
    )
    return blueprint, supplier_legal_name, risk_event_severity


def _worked_example() -> tuple[
    GapImpactRemediationApplicationService,
    SemanticCoverageEvaluationResult,
    Blueprint,
    dict[UUID, GapImpactContext],
]:
    blueprint, supplier_legal_name, risk_event_severity = _worked_example_blueprint()
    coverage_result = _evaluation_result(
        _coverage_result(
            element=supplier_legal_name,
            status=CoverageStatus.MAPPED,
            resolution=_resolution(supplier_legal_name.information_element_requirement_id.value),
        ),
        _coverage_result(
            element=risk_event_severity, status=CoverageStatus.UNMAPPED, resolution=None
        ),
    )
    service = GapImpactRemediationApplicationService()
    results = service.derive(coverage_result=coverage_result, blueprint=blueprint)
    by_id = {
        result.coverage_result.information_element_requirement_id: result for result in results
    }
    return service, coverage_result, blueprint, by_id


# ---------------------------------------------------------------------------
# J1 -- Descriptive Gap Impact Context
# ---------------------------------------------------------------------------


def test_context_is_produced_for_every_element_mapped_and_unmapped() -> None:
    _, coverage_result, _, by_id = _worked_example()

    assert len(by_id) == len(coverage_result.information_element_results)
    assert all(
        element.information_element_requirement_id in by_id
        for element in coverage_result.information_element_results
    )


def test_owning_concept_identity_matches_exactly() -> None:
    _, _, blueprint, by_id = _worked_example()
    supplier, _, risk_event, _ = blueprint.concept_requirements

    supplier_result = next(
        result for result in by_id.values() if result.entity_type_id == SUPPLIER_ENTITY_TYPE_ID
    )
    assert supplier_result.concept_requirement_id == supplier.concept_requirement_id.value
    assert supplier_result.entity_type_id == supplier.entity_type_id.value

    risk_event_result = next(
        result for result in by_id.values() if result.entity_type_id == RISK_EVENT_ENTITY_TYPE_ID
    )
    assert risk_event_result.concept_requirement_id == risk_event.concept_requirement_id.value
    assert risk_event_result.entity_type_id == risk_event.entity_type_id.value


def test_relationship_context_includes_both_source_and_target_relationships() -> None:
    _, _, _, by_id = _worked_example()
    risk_event_result = next(
        result for result in by_id.values() if result.entity_type_id == RISK_EVENT_ENTITY_TYPE_ID
    )

    directions = {entry.direction for entry in risk_event_result.relationship_context}
    assert directions == {Direction.OUTGOING, Direction.INCOMING}

    outgoing = next(
        entry
        for entry in risk_event_result.relationship_context
        if entry.direction is Direction.OUTGOING
    )
    assert outgoing.relationship_type_id == RELATES_TO_TYPE_ID
    assert outgoing.other_entity_type_id == FACILITY_ENTITY_TYPE_ID

    incoming = next(
        entry
        for entry in risk_event_result.relationship_context
        if entry.direction is Direction.INCOMING
    )
    assert incoming.relationship_type_id == EXPOSED_TO_TYPE_ID
    assert incoming.other_entity_type_id == REGION_ENTITY_TYPE_ID


def test_relationship_context_is_bounded_to_structurally_connected_relationships() -> None:
    _, _, _, by_id = _worked_example()
    risk_event_result = next(
        result for result in by_id.values() if result.entity_type_id == RISK_EVENT_ENTITY_TYPE_ID
    )

    assert len(risk_event_result.relationship_context) == 2
    referenced_type_ids = {
        entry.relationship_type_id for entry in risk_event_result.relationship_context
    }
    assert referenced_type_ids == {RELATES_TO_TYPE_ID, EXPOSED_TO_TYPE_ID}
    assert LOCATED_IN_TYPE_ID not in referenced_type_ids


def test_relationship_context_entry_carries_only_governed_ids() -> None:
    assert set(RelationshipContextEntry.__dataclass_fields__) == {
        "relationship_type_id",
        "direction",
        "other_entity_type_id",
    }


def test_gap_impact_context_stores_no_tenant_id_field() -> None:
    assert "tenant_id" not in GapImpactContext.__dataclass_fields__
    signature = inspect.signature(GapImpactRemediationApplicationService.derive)
    assert set(signature.parameters) == {"self", "coverage_result", "blueprint"}


def test_gap_impact_context_does_not_duplicate_blueprint_identity_or_version() -> None:
    fields = set(GapImpactContext.__dataclass_fields__)
    assert "blueprint_id" not in fields
    assert "blueprint_version_number" not in fields


def test_service_module_contains_no_persistence_or_orm_import() -> None:
    import app.application.gap_impact_remediation as module

    source = inspect.getsource(module)
    assert "Repository" not in source
    assert "ORM" not in source
    assert "sqlalchemy" not in source.lower()


def test_service_module_references_no_http_layer_object() -> None:
    import app.application.gap_impact_remediation as module

    source = inspect.getsource(module)
    assert "fastapi" not in source.lower()
    assert "router" not in source.lower()


# ---------------------------------------------------------------------------
# J2 -- Governed Remediation Recommendation
# ---------------------------------------------------------------------------


def test_remediation_action_has_exactly_one_member() -> None:
    assert list(RemediationAction) == [RemediationAction.REVIEW_SEMANTIC_MAPPING]


def test_remediation_populated_if_and_only_if_unmapped() -> None:
    _, _, _, by_id = _worked_example()
    risk_event_result = next(
        result for result in by_id.values() if result.entity_type_id == RISK_EVENT_ENTITY_TYPE_ID
    )
    assert risk_event_result.remediation_action is RemediationAction.REVIEW_SEMANTIC_MAPPING


def test_remediation_is_none_for_mapped_results() -> None:
    _, _, _, by_id = _worked_example()
    supplier_result = next(
        result for result in by_id.values() if result.entity_type_id == SUPPLIER_ENTITY_TYPE_ID
    )
    assert supplier_result.remediation_action is None


def test_service_module_imports_no_h2_semantic_mapping_or_source_field_type() -> None:
    import app.application.gap_impact_remediation as module

    module_names = set(dir(module))
    assert "SemanticMappingResolutionApplicationService" not in module_names
    assert "BlueprintApplicationService" not in module_names
    assert "SemanticMapping" not in module_names
    assert "SourceField" not in module_names


def test_gap_impact_context_has_no_ranking_or_scoring_field() -> None:
    assert set(GapImpactContext.__dataclass_fields__) == {
        "coverage_result",
        "concept_requirement_id",
        "entity_type_id",
        "relationship_context",
        "remediation_action",
    }


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


def test_missing_owning_concept_raises_explicit_failure() -> None:
    blueprint, _, _ = _worked_example_blueprint()
    orphan_element = _element_requirement(obligation=Obligation.REQUIRED, element_name="Orphan")
    coverage_result = _evaluation_result(
        _coverage_result(element=orphan_element, status=CoverageStatus.UNMAPPED, resolution=None)
    )
    service = GapImpactRemediationApplicationService()

    with pytest.raises(ValidationException, match="No owning ConceptRequirement found"):
        service.derive(coverage_result=coverage_result, blueprint=blueprint)


def test_deterministic_result_ordering() -> None:
    blueprint_id = uuid4()
    elements = tuple(
        _element_requirement(obligation=Obligation.REQUIRED, element_name=f"Element {i}")
        for i in range(5)
    )
    concept = ConceptRequirement(
        concept_requirement_id=Identifier(uuid4()),
        blueprint_id=Identifier(blueprint_id),
        entity_type_id=Identifier(SUPPLIER_ENTITY_TYPE_ID),
        obligation=Obligation.REQUIRED,
        information_element_requirements=elements,
    )
    blueprint = Blueprint(
        blueprint_id=Identifier(blueprint_id),
        blueprint_name=CanonicalName(BLUEPRINT_NAME),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(concept,),
    )
    coverage_result = _evaluation_result(
        *(
            _coverage_result(element=element, status=CoverageStatus.UNMAPPED, resolution=None)
            for element in elements
        )
    )
    service = GapImpactRemediationApplicationService()

    results = service.derive(coverage_result=coverage_result, blueprint=blueprint)

    ids = [result.coverage_result.information_element_requirement_id for result in results]
    assert ids == sorted(ids)


def test_service_exposes_no_method_beyond_derive() -> None:
    public_methods = {
        name
        for name, _ in inspect.getmembers(
            GapImpactRemediationApplicationService, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    }
    assert public_methods == {"derive"}


def test_risk_event_severity_supplier_legal_name_worked_example() -> None:
    """Reproduces CDD-021's own worked example structurally, asserting only
    the FACT-level fields CDD-021 §12 authorizes: obligation, coverage
    status, owning-Concept identity, and declared relationship-requirement
    existence -- nothing beyond them."""
    _, _, _, by_id = _worked_example()

    supplier_result = next(
        result for result in by_id.values() if result.entity_type_id == SUPPLIER_ENTITY_TYPE_ID
    )
    assert supplier_result.coverage_result.obligation is Obligation.REQUIRED
    assert supplier_result.coverage_result.status is CoverageStatus.MAPPED
    assert supplier_result.remediation_action is None

    risk_event_result = next(
        result for result in by_id.values() if result.entity_type_id == RISK_EVENT_ENTITY_TYPE_ID
    )
    assert risk_event_result.coverage_result.obligation is Obligation.CONDITIONAL
    assert risk_event_result.coverage_result.status is CoverageStatus.UNMAPPED
    assert risk_event_result.remediation_action is RemediationAction.REVIEW_SEMANTIC_MAPPING
    assert any(
        entry.direction is Direction.INCOMING
        and entry.other_entity_type_id == REGION_ENTITY_TYPE_ID
        for entry in risk_event_result.relationship_context
    )
