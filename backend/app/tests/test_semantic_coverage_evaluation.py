"""Unit tests for `SemanticCoverageEvaluationApplicationService` (Gate I I1;
CDD-020 §7-§13; I1 Semantic Coverage Evaluation Artifact Authorization).
Uses `BlueprintLookup`-conforming and `MappingResolver`-conforming test
doubles -- no PostgreSQL dependency: `BlueprintRepositoryImpl`'s and
`SemanticMappingRepositoryImpl`'s real query logic is already proven against
real Postgres elsewhere; re-proving it here would duplicate existing
coverage without adding evidence value.
"""

import inspect
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    SemanticCoverageEvaluationApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
)
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingResolution,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
BLUEPRINT_NAME = "CTEC Semiconductor Supply Chain Blueprint"


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


def _element(
    *, obligation: Obligation, element_name: str = "Element"
) -> InformationElementRequirement:
    return InformationElementRequirement(
        information_element_requirement_id=Identifier(uuid4()),
        concept_requirement_id=Identifier(uuid4()),
        element_name=CanonicalName(element_name),
        description=Description("A test information element requirement."),
        obligation=obligation,
    )


def _blueprint(elements: tuple[InformationElementRequirement, ...]) -> Blueprint:
    concept = ConceptRequirement(
        concept_requirement_id=Identifier(uuid4()),
        blueprint_id=Identifier(uuid4()),
        entity_type_id=Identifier(uuid4()),
        obligation=Obligation.REQUIRED,
        information_element_requirements=elements,
    )
    return Blueprint(
        blueprint_id=Identifier(uuid4()),
        blueprint_name=CanonicalName(BLUEPRINT_NAME),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(concept,),
    )


class _FakeBlueprintLookup:
    def __init__(self, blueprint: Blueprint | None) -> None:
        self.blueprint = blueprint
        self.requested_names: list[str] = []

    def get_approved_by_name(self, blueprint_name: str) -> Blueprint | None:
        self.requested_names.append(blueprint_name)
        return self.blueprint


class _FakeMappingResolver:
    def __init__(
        self,
        resolutions: dict[UUID, SemanticMappingResolution],
        *,
        error: Exception | None = None,
    ) -> None:
        self.resolutions = resolutions
        self.error = error
        self.requested_arguments: list[tuple[UUID, str]] = []

    def resolve_approved_source_field(
        self, information_element_requirement_id: UUID, tenant_id: str
    ) -> SemanticMappingResolution | None:
        self.requested_arguments.append((information_element_requirement_id, tenant_id))
        if self.error is not None:
            raise self.error
        return self.resolutions.get(information_element_requirement_id)


def test_element_is_mapped_when_resolver_returns_a_resolution() -> None:
    element = _element(obligation=Obligation.REQUIRED)
    requirement_id = element.information_element_requirement_id.value
    resolution = _resolution(requirement_id)
    blueprint_lookup = _FakeBlueprintLookup(_blueprint((element,)))
    resolver = _FakeMappingResolver({requirement_id: resolution})
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )

    result = service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-a")

    assert len(result.information_element_results) == 1
    element_result = result.information_element_results[0]
    assert element_result.status is CoverageStatus.MAPPED
    assert element_result.resolution is resolution


def test_element_is_unmapped_when_resolver_returns_none() -> None:
    element = _element(obligation=Obligation.REQUIRED)
    blueprint_lookup = _FakeBlueprintLookup(_blueprint((element,)))
    resolver = _FakeMappingResolver({})
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )

    result = service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-a")

    element_result = result.information_element_results[0]
    assert element_result.status is CoverageStatus.UNMAPPED
    assert element_result.resolution is None


def test_resolver_ambiguity_propagates_unchanged() -> None:
    element = _element(obligation=Obligation.REQUIRED)
    blueprint_lookup = _FakeBlueprintLookup(_blueprint((element,)))
    resolver = _FakeMappingResolver(
        {}, error=ValidationException("Ambiguous Approved SemanticMapping resolution")
    )
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )

    with pytest.raises(ValidationException, match="Ambiguous Approved SemanticMapping"):
        service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-a")


@pytest.mark.parametrize(
    "obligation", [Obligation.REQUIRED, Obligation.CONDITIONAL, Obligation.OPTIONAL]
)
def test_obligation_is_preserved_unchanged(obligation: Obligation) -> None:
    element = _element(obligation=obligation)
    blueprint_lookup = _FakeBlueprintLookup(_blueprint((element,)))
    resolver = _FakeMappingResolver({})
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )

    result = service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-a")

    assert result.information_element_results[0].obligation is obligation


def test_all_six_obligation_and_coverage_combinations_are_representable() -> None:
    obligations = (Obligation.REQUIRED, Obligation.CONDITIONAL, Obligation.OPTIONAL)
    elements = tuple(
        _element(obligation=obligation) for obligation in obligations for _ in range(2)
    )
    mapped_ids = {
        elements[0].information_element_requirement_id.value,
        elements[2].information_element_requirement_id.value,
        elements[4].information_element_requirement_id.value,
    }
    resolutions = {
        element.information_element_requirement_id.value: _resolution(
            element.information_element_requirement_id.value
        )
        for element in elements
        if element.information_element_requirement_id.value in mapped_ids
    }
    blueprint_lookup = _FakeBlueprintLookup(_blueprint(elements))
    resolver = _FakeMappingResolver(resolutions)
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )

    result = service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-a")

    combinations = {
        (element_result.obligation, element_result.status)
        for element_result in result.information_element_results
    }
    assert combinations == {
        (Obligation.REQUIRED, CoverageStatus.MAPPED),
        (Obligation.REQUIRED, CoverageStatus.UNMAPPED),
        (Obligation.CONDITIONAL, CoverageStatus.MAPPED),
        (Obligation.CONDITIONAL, CoverageStatus.UNMAPPED),
        (Obligation.OPTIONAL, CoverageStatus.MAPPED),
        (Obligation.OPTIONAL, CoverageStatus.UNMAPPED),
    }


def test_tenant_id_is_passed_through_unchanged_to_the_resolver() -> None:
    element = _element(obligation=Obligation.REQUIRED)
    requirement_id = element.information_element_requirement_id.value
    blueprint_lookup = _FakeBlueprintLookup(_blueprint((element,)))
    resolver = _FakeMappingResolver({})
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )

    service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-b")

    assert resolver.requested_arguments == [(requirement_id, "tenant-b")]


def test_evaluate_does_not_mutate_the_input_blueprint_or_elements() -> None:
    element = _element(obligation=Obligation.CONDITIONAL)
    blueprint = _blueprint((element,))
    blueprint_lookup = _FakeBlueprintLookup(blueprint)
    resolver = _FakeMappingResolver({})
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )
    before = blueprint

    service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-a")

    assert blueprint_lookup.blueprint is before
    assert (
        blueprint_lookup.blueprint.concept_requirements[0].information_element_requirements[0]
        is element
    )
    assert element.obligation is Obligation.CONDITIONAL


def test_blueprint_not_found_raises_explicit_failure() -> None:
    blueprint_lookup = _FakeBlueprintLookup(None)
    resolver = _FakeMappingResolver({})
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )

    with pytest.raises(ValidationException, match="No Approved Blueprint found"):
        service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-a")


def test_deterministic_result_ordering() -> None:
    elements = tuple(_element(obligation=Obligation.REQUIRED) for _ in range(5))
    blueprint_lookup = _FakeBlueprintLookup(_blueprint(elements))
    resolver = _FakeMappingResolver({})
    service = SemanticCoverageEvaluationApplicationService(
        blueprint_service=blueprint_lookup, resolver=resolver
    )

    result = service.evaluate(blueprint_name=BLUEPRINT_NAME, tenant_id="tenant-a")

    ids = [
        element_result.information_element_requirement_id
        for element_result in result.information_element_results
    ]
    assert ids == sorted(ids)


def test_service_exposes_no_method_beyond_evaluate() -> None:
    public_methods = {
        name
        for name, _ in inspect.getmembers(
            SemanticCoverageEvaluationApplicationService, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    }
    assert public_methods == {"evaluate"}


def test_service_module_contains_no_persistence_repository_import() -> None:
    import app.application.semantic_coverage_evaluation as module

    source = inspect.getsource(module)
    assert "Repository" not in source
    assert "ORM" not in source
    assert "sqlalchemy" not in source.lower()


def test_service_module_references_no_http_layer_object() -> None:
    import app.application.semantic_coverage_evaluation as module

    source = inspect.getsource(module)
    assert "fastapi" not in source.lower()
    assert "router" not in source.lower()
