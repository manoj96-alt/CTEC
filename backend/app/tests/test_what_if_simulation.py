"""Unit tests for `WhatIfSimulationApplicationService` (Gate U; CDD-032
§6-§19; Gate U Artifact Authorization §6, §9). Uses plain,
directly-constructed `InformationElementEvidenceFitnessResult`/`Blueprint`
fixtures -- no PostgreSQL dependency: this service performs no I/O, and its
sole collaborator (`SourceEvidenceFitnessImpactRemediationApplicationService`)
is already proven against real Postgres-sourced `Blueprint` objects
elsewhere (CDD-031); re-proving that here would duplicate existing
coverage without adding evidence value."""

import ast
import dataclasses
import inspect
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application import what_if_simulation as what_if_simulation_module
from app.application.source_evidence_fitness_evaluation import (
    EvidenceFitnessStatus,
    InformationElementEvidenceFitnessResult,
)
from app.application.source_evidence_fitness_impact_remediation import (
    EvidenceFitnessImpactContext,
    EvidenceFitnessRemediationAction,
    SourceEvidenceFitnessImpactRemediationApplicationService,
)
from app.application.what_if_simulation import (
    WhatIfSimulationApplicationService,
    WhatIfSimulationResult,
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
BLUEPRINT_NAME = "Gate U Test Blueprint"

SUPPLIER_ENTITY_TYPE_ID = uuid4()
REGION_ENTITY_TYPE_ID = uuid4()
LOCATED_IN_TYPE_ID = uuid4()


def _element_requirement(*, element_name: str = "Element") -> InformationElementRequirement:
    return InformationElementRequirement(
        information_element_requirement_id=Identifier(uuid4()),
        concept_requirement_id=Identifier(uuid4()),
        element_name=CanonicalName(element_name),
        description=Description("A test information element requirement."),
        obligation=Obligation.REQUIRED,
    )


def _blueprint() -> tuple[Blueprint, InformationElementRequirement]:
    blueprint_id = uuid4()
    supplier_legal_name = _element_requirement(element_name="Supplier Legal Name")

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
    )

    blueprint = Blueprint(
        blueprint_id=Identifier(blueprint_id),
        blueprint_name=CanonicalName(BLUEPRINT_NAME),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(supplier, region),
    )
    return blueprint, supplier_legal_name


def _hypothetical(
    *, requirement: InformationElementRequirement, fitness_status: EvidenceFitnessStatus | None
) -> InformationElementEvidenceFitnessResult:
    return InformationElementEvidenceFitnessResult(
        information_element_requirement_id=requirement.information_element_requirement_id.value,
        source_field_id=uuid4(),
        fitness_status=fitness_status,
    )


# ---------------------------------------------------------------------------
# 1-4: remediation semantics reused from Gate T
# ---------------------------------------------------------------------------


def test_hypothetical_fit_yields_no_remediation() -> None:
    blueprint, supplier_legal_name = _blueprint()
    hypothetical = _hypothetical(
        requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.FIT
    )
    service = WhatIfSimulationApplicationService()

    result = service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)

    assert result.simulated_impact_context.remediation_action is None


def test_hypothetical_stale_yields_refresh_source_evidence() -> None:
    blueprint, supplier_legal_name = _blueprint()
    hypothetical = _hypothetical(
        requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.STALE
    )
    service = WhatIfSimulationApplicationService()

    result = service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)

    assert (
        result.simulated_impact_context.remediation_action
        is EvidenceFitnessRemediationAction.REFRESH_SOURCE_EVIDENCE
    )


def test_hypothetical_conflicting_yields_review_conflicting_evidence() -> None:
    blueprint, supplier_legal_name = _blueprint()
    hypothetical = _hypothetical(
        requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.CONFLICTING
    )
    service = WhatIfSimulationApplicationService()

    result = service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)

    assert (
        result.simulated_impact_context.remediation_action
        is EvidenceFitnessRemediationAction.REVIEW_CONFLICTING_EVIDENCE
    )


def test_hypothetical_none_fitness_status_yields_no_remediation() -> None:
    blueprint, supplier_legal_name = _blueprint()
    hypothetical = _hypothetical(requirement=supplier_legal_name, fitness_status=None)
    service = WhatIfSimulationApplicationService()

    result = service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)

    assert result.simulated_impact_context.remediation_action is None


# ---------------------------------------------------------------------------
# 5-6: determinism / exact reuse of Gate T semantics
# ---------------------------------------------------------------------------


def test_repeated_simulation_with_identical_input_is_value_equal() -> None:
    blueprint, supplier_legal_name = _blueprint()
    hypothetical = _hypothetical(
        requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.STALE
    )
    service = WhatIfSimulationApplicationService()

    first = service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)
    second = service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)

    assert first == second


def test_simulated_structural_context_matches_direct_gate_t_call() -> None:
    blueprint, supplier_legal_name = _blueprint()
    hypothetical = _hypothetical(
        requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.CONFLICTING
    )
    service = WhatIfSimulationApplicationService()

    simulated = service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)

    direct = SourceEvidenceFitnessImpactRemediationApplicationService().derive(
        fitness_results=(hypothetical,), blueprint=blueprint
    )
    assert simulated.simulated_impact_context == direct[0]


# ---------------------------------------------------------------------------
# 9: fail-closed behavior (existing Gate T ValidationException, unchanged)
# ---------------------------------------------------------------------------


def test_requirement_absent_from_blueprint_raises_existing_validation_exception() -> None:
    blueprint, _ = _blueprint()
    orphan = _element_requirement(element_name="Orphan Element")
    hypothetical = _hypothetical(requirement=orphan, fitness_status=EvidenceFitnessStatus.FIT)
    service = WhatIfSimulationApplicationService()

    with pytest.raises(ValidationException, match="No owning ConceptRequirement"):
        service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)


# ---------------------------------------------------------------------------
# 17: single-field WhatIfSimulationResult
# ---------------------------------------------------------------------------


def test_result_contract_contains_exactly_one_field() -> None:
    field_names = {field.name for field in dataclasses.fields(WhatIfSimulationResult)}
    assert field_names == {"simulated_impact_context"}


def test_result_is_never_structurally_interchangeable_with_bare_impact_context() -> None:
    blueprint, supplier_legal_name = _blueprint()
    hypothetical = _hypothetical(
        requirement=supplier_legal_name, fitness_status=EvidenceFitnessStatus.FIT
    )
    service = WhatIfSimulationApplicationService()

    result = service.simulate(hypothetical_fitness_result=hypothetical, blueprint=blueprint)

    assert not isinstance(result, EvidenceFitnessImpactContext)
    assert isinstance(result.simulated_impact_context, EvidenceFitnessImpactContext)


# ---------------------------------------------------------------------------
# structural / firewall
# ---------------------------------------------------------------------------


def test_service_exposes_no_method_beyond_simulate() -> None:
    public_methods = [
        name for name in dir(WhatIfSimulationApplicationService) if not name.startswith("_")
    ]
    assert public_methods == ["simulate"]


def _module_imported_names() -> set[str]:
    tree = ast.parse(inspect.getsource(what_if_simulation_module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(alias.name for alias in node.names)
    return names


def test_module_imports_no_concrete_repository_orm_or_sqlalchemy() -> None:
    imported = _module_imported_names()
    assert not any("sqlalchemy" in name.lower() for name in imported)
    assert not any(name.endswith("ORM") for name in imported)
    assert not any("Repository" in name for name in imported)
    assert not any(name == "Session" or name.endswith(".Session") for name in imported)


def test_module_imports_no_mcp_capability() -> None:
    imported = _module_imported_names()
    assert not any("mcp" in name.lower() for name in imported)


def test_module_imports_no_forbidden_capability() -> None:
    imported = _module_imported_names()
    forbidden = {
        "GapImpactContext",
        "GapImpactRemediationApplicationService",
        "RemediationAction",
        "RelationshipContextEntry",
    }
    assert imported.isdisjoint(forbidden)
    assert not any("gap_impact_remediation" in name for name in imported)
    assert not any("app.integration" in name or "app.api" in name for name in imported)
    assert not any("fastapi" in name.lower() for name in imported)


def test_module_never_calls_datetime_now() -> None:
    source = inspect.getsource(what_if_simulation_module)
    assert "datetime.now(" not in source


def test_module_does_not_duplicate_gate_t_traversal_logic() -> None:
    source = inspect.getsource(what_if_simulation_module)
    # Gate T's own owning-concept/relationship-context traversal helper
    # names must never appear here -- Gate U consumes Gate T's public
    # `.derive(...)` method only, never reimplements its private logic.
    for forbidden_symbol in (
        "_find_owning_concept",
        "_relationship_context",
        "concept_requirements",
    ):
        assert forbidden_symbol not in source
