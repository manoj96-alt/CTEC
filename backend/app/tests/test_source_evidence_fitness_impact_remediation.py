"""Unit tests for `SourceEvidenceFitnessImpactRemediationApplicationService`
(Gate T; CDD-031 §15-§16; Gate T Artifact Authorization §6). Uses plain,
directly-constructed `InformationElementEvidenceFitnessResult`/`Blueprint`
fixtures -- no PostgreSQL dependency: this service performs no I/O, so its
unit-test evidence needs no test double or fake, only already-in-memory
objects."""

import ast
import dataclasses
import inspect
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application import source_evidence_fitness_impact_remediation as impact_module
from app.application.source_evidence_fitness_evaluation import (
    EvidenceFitnessStatus,
    InformationElementEvidenceFitnessResult,
)
from app.application.source_evidence_fitness_impact_remediation import (
    Direction,
    EvidenceFitnessRemediationAction,
    SourceEvidenceFitnessImpactRemediationApplicationService,
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

NOW = datetime(2026, 1, 1, tzinfo=UTC)
BLUEPRINT_NAME = "Gate T Test Blueprint"

SUPPLIER_ENTITY_TYPE_ID = uuid4()
REGION_ENTITY_TYPE_ID = uuid4()
RISK_EVENT_ENTITY_TYPE_ID = uuid4()
LOCATED_IN_TYPE_ID = uuid4()
EXPOSED_TO_TYPE_ID = uuid4()


def _element_requirement(*, element_name: str = "Element") -> InformationElementRequirement:
    return InformationElementRequirement(
        information_element_requirement_id=Identifier(uuid4()),
        concept_requirement_id=Identifier(uuid4()),
        element_name=CanonicalName(element_name),
        description=Description("A test information element requirement."),
        obligation=Obligation.REQUIRED,
    )


def _blueprint() -> tuple[Blueprint, InformationElementRequirement, InformationElementRequirement]:
    """Supplier (source of `locatedIn` -> Region), Region (source of
    `exposedTo` -> Risk Event) -- giving Region both an INCOMING (from
    Supplier) and OUTGOING (to Risk Event) relationship-context entry, so
    the uniform-shape rule is proven across both directions."""
    blueprint_id = uuid4()
    supplier_legal_name = _element_requirement(element_name="Supplier Legal Name")
    region_code = _element_requirement(element_name="Region Code")

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
        information_element_requirements=(region_code,),
    )
    risk_event = ConceptRequirement(
        concept_requirement_id=Identifier(uuid4()),
        blueprint_id=Identifier(blueprint_id),
        entity_type_id=Identifier(RISK_EVENT_ENTITY_TYPE_ID),
        obligation=Obligation.REQUIRED,
    )

    blueprint = Blueprint(
        blueprint_id=Identifier(blueprint_id),
        blueprint_name=CanonicalName(BLUEPRINT_NAME),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(supplier, region, risk_event),
    )
    return blueprint, supplier_legal_name, region_code


def _fitness_result(
    *, requirement: InformationElementRequirement, fitness_status: EvidenceFitnessStatus | None
) -> InformationElementEvidenceFitnessResult:
    return InformationElementEvidenceFitnessResult(
        information_element_requirement_id=requirement.information_element_requirement_id.value,
        source_field_id=uuid4(),
        fitness_status=fitness_status,
    )


# ---------------------------------------------------------------------------
# structural traversal
# ---------------------------------------------------------------------------


def test_context_is_produced_for_every_fitness_result() -> None:
    blueprint, supplier_legal_name, region_code = _blueprint()
    results = (
        _fitness_result(requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.FIT),
        _fitness_result(requirement=region_code, fitness_status=EvidenceFitnessStatus.STALE),
    )
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    assert len(contexts) == 2


def test_owning_concept_identity_matches_exactly() -> None:
    blueprint, supplier_legal_name, _ = _blueprint()
    results = (
        _fitness_result(requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.FIT),
    )
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    supplier = next(
        concept
        for concept in blueprint.concept_requirements
        if concept.entity_type_id.value == SUPPLIER_ENTITY_TYPE_ID
    )
    assert contexts[0].concept_requirement_id == supplier.concept_requirement_id.value
    assert contexts[0].entity_type_id == SUPPLIER_ENTITY_TYPE_ID


def test_relationship_context_includes_both_outgoing_and_incoming() -> None:
    blueprint, _, region_code = _blueprint()
    results = (_fitness_result(requirement=region_code, fitness_status=EvidenceFitnessStatus.FIT),)
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    directions = {entry.direction for entry in contexts[0].relationship_context}
    assert directions == {Direction.OUTGOING, Direction.INCOMING}


def test_relationship_context_entry_carries_only_governed_ids() -> None:
    blueprint, _, region_code = _blueprint()
    results = (_fitness_result(requirement=region_code, fitness_status=EvidenceFitnessStatus.FIT),)
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    for entry in contexts[0].relationship_context:
        field_names = {field.name for field in dataclasses.fields(entry)}
        assert field_names == {"relationship_type_id", "direction", "other_entity_type_id"}


def test_missing_owning_concept_raises_existing_shared_validation_exception() -> None:
    blueprint, _, _ = _blueprint()
    orphan = _element_requirement(element_name="Orphan Element")
    results = (_fitness_result(requirement=orphan, fitness_status=EvidenceFitnessStatus.FIT),)
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    with pytest.raises(ValidationException, match="No owning ConceptRequirement"):
        service.derive(fitness_results=results, blueprint=blueprint)


def test_deterministic_result_ordering() -> None:
    blueprint, supplier_legal_name, region_code = _blueprint()
    results = (
        _fitness_result(requirement=region_code, fitness_status=EvidenceFitnessStatus.STALE),
        _fitness_result(requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.FIT),
    )
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    ids = [context.fitness_result.information_element_requirement_id for context in contexts]
    assert ids == sorted(ids)


def test_derivation_is_deterministic_across_repeated_calls() -> None:
    blueprint, supplier_legal_name, region_code = _blueprint()
    results = (
        _fitness_result(
            requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.STALE
        ),
        _fitness_result(requirement=region_code, fitness_status=EvidenceFitnessStatus.CONFLICTING),
    )
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    first = service.derive(fitness_results=results, blueprint=blueprint)
    second = service.derive(fitness_results=results, blueprint=blueprint)

    assert first == second


# ---------------------------------------------------------------------------
# remediation semantics
# ---------------------------------------------------------------------------


def test_fit_yields_no_remediation() -> None:
    blueprint, supplier_legal_name, _ = _blueprint()
    results = (
        _fitness_result(requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.FIT),
    )
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    assert contexts[0].remediation_action is None


def test_none_fitness_status_yields_no_remediation() -> None:
    blueprint, supplier_legal_name, _ = _blueprint()
    results = (_fitness_result(requirement=supplier_legal_name, fitness_status=None),)
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    assert contexts[0].remediation_action is None


def test_stale_yields_refresh_source_evidence() -> None:
    blueprint, supplier_legal_name, _ = _blueprint()
    results = (
        _fitness_result(
            requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.STALE
        ),
    )
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    assert (
        contexts[0].remediation_action is EvidenceFitnessRemediationAction.REFRESH_SOURCE_EVIDENCE
    )


def test_conflicting_yields_review_conflicting_evidence() -> None:
    blueprint, supplier_legal_name, _ = _blueprint()
    results = (
        _fitness_result(
            requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.CONFLICTING
        ),
    )
    service = SourceEvidenceFitnessImpactRemediationApplicationService()

    contexts = service.derive(fitness_results=results, blueprint=blueprint)

    assert (
        contexts[0].remediation_action
        is EvidenceFitnessRemediationAction.REVIEW_CONFLICTING_EVIDENCE
    )


def test_remediation_action_has_exactly_two_members() -> None:
    assert {member.value for member in EvidenceFitnessRemediationAction} == {
        "REFRESH_SOURCE_EVIDENCE",
        "REVIEW_CONFLICTING_EVIDENCE",
    }


def test_no_positive_no_action_required_literal_exists() -> None:
    assert "NO_ACTION_REQUIRED" not in {member.name for member in EvidenceFitnessRemediationAction}


# ---------------------------------------------------------------------------
# structural / import firewall
# ---------------------------------------------------------------------------


def test_service_exposes_no_method_beyond_derive() -> None:
    public_methods = [
        name
        for name in dir(SourceEvidenceFitnessImpactRemediationApplicationService)
        if not name.startswith("_")
    ]
    assert public_methods == ["derive"]


def _module_imported_names() -> set[str]:
    tree = ast.parse(inspect.getsource(impact_module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(alias.name for alias in node.names)
    return names


def test_module_does_not_import_from_gap_impact_remediation() -> None:
    imported = _module_imported_names()
    forbidden = {
        "GapImpactContext",
        "GapImpactRemediationApplicationService",
        "RemediationAction",
        "RelationshipContextEntry",
    }
    assert imported.isdisjoint(forbidden)
    assert not any("gap_impact_remediation" in name for name in imported)


def test_module_imports_no_concrete_repository_orm_or_sqlalchemy() -> None:
    imported = _module_imported_names()
    assert not any("sqlalchemy" in name.lower() for name in imported)
    assert not any(name.endswith("ORM") for name in imported)
    assert not any("Repository" in name for name in imported)
