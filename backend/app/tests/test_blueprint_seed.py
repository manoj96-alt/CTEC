"""Tests for `BlueprintSeeder` (Gate G G3.5; CDD-017 §3, §13; G3.5 Canonical
Blueprint Seed Artifact Authorization). Determinism/stability checks require
no database. Content, idempotency, ontology-resolution, and G3-readability
checks require real PostgreSQL (`migrated_engine`) -- following
`test_ontology_seed.py::test_ontology_seed_is_repeatable_and_idempotent`'s
established idempotency-test pattern.
"""

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.domain.blueprint import Obligation
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import (
    BLUEPRINT_SEED_VERSION,
    CANONICAL_BLUEPRINT_NAME,
    REQUIRED_CONCEPT_NAMES,
    REQUIRED_RELATIONSHIP_TUPLES,
    BlueprintSeeder,
)
from app.infrastructure.persistence.models.blueprint import (
    ConceptRequirementORM,
    InformationElementRequirementORM,
    RelationshipRequirementORM,
)
from app.infrastructure.persistence.ontology_seed import OntologySeeder


def test_blueprint_seed_version_is_a_fixed_curated_constant() -> None:
    assert BLUEPRINT_SEED_VERSION == "CANONICAL-BLUEPRINT-V1"
    assert CANONICAL_BLUEPRINT_NAME == "CTEC Semiconductor Supply Chain Blueprint"


def test_requirement_identity_is_deterministic_and_stable() -> None:
    blueprint_id_first = BlueprintSeeder._stable_id("blueprint", CANONICAL_BLUEPRINT_NAME)
    blueprint_id_second = BlueprintSeeder._stable_id("blueprint", CANONICAL_BLUEPRINT_NAME)
    assert blueprint_id_first == blueprint_id_second

    for name in REQUIRED_CONCEPT_NAMES:
        first = BlueprintSeeder._stable_id("concept-requirement", name)
        second = BlueprintSeeder._stable_id("concept-requirement", name)
        assert first == second

    for relationship_name, _source, _target in REQUIRED_RELATIONSHIP_TUPLES:
        first = BlueprintSeeder._stable_id("relationship-requirement", relationship_name)
        second = BlueprintSeeder._stable_id("relationship-requirement", relationship_name)
        assert first == second


def test_seeder_carries_no_tenant_parameter() -> None:
    import inspect

    init_parameters = inspect.signature(BlueprintSeeder.__init__).parameters
    load_parameters = inspect.signature(BlueprintSeeder.load).parameters
    assert "tenant_id" not in init_parameters
    assert "tenant_id" not in load_parameters


def test_missing_governed_entity_type_fails_explicitly(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        seeder = BlueprintSeeder(session)
        with pytest.raises(ValidationException, match="Required governed entity type not found"):
            seeder._entity_type_id("Nonexistent Concept XYZ")
        # No substitute EntityType (or any other row) was staged for insertion.
        assert not session.new


def test_missing_governed_relationship_type_fails_explicitly(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        seeder = BlueprintSeeder(session)
        with pytest.raises(
            ValidationException, match="Required governed relationship type not found"
        ):
            seeder._relationship_type_id("nonexistentRelationshipXYZ")
        assert not session.new


def test_canonical_blueprint_seed_creates_expected_content_and_is_idempotent(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)

    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

    with factory() as session:
        first = BlueprintSeeder(session).load()
        session.commit()

    assert first.created is True
    assert first.blueprint_seed_version == BLUEPRINT_SEED_VERSION
    assert first.blueprint_id == BlueprintSeeder._stable_id("blueprint", CANONICAL_BLUEPRINT_NAME)

    with factory() as session:
        loaded = BlueprintRepositoryImpl(session).get_by_id(first.blueprint_id)
        assert loaded is not None
        assert loaded.blueprint_name.value == CANONICAL_BLUEPRINT_NAME
        assert loaded.version_number == 1
        assert loaded.previous_version_id is None
        assert len(loaded.concept_requirements) == 10
        assert all(
            concept.obligation is Obligation.REQUIRED for concept in loaded.concept_requirements
        )

        all_relationships = [
            relationship
            for concept in loaded.concept_requirements
            for relationship in concept.relationship_requirements
        ]
        assert len(all_relationships) == 10
        assert all(
            relationship.obligation is Obligation.REQUIRED for relationship in all_relationships
        )

        all_information_elements = [
            element
            for concept in loaded.concept_requirements
            for element in concept.information_element_requirements
        ]
        assert len(all_information_elements) == 2
        elements_by_name = {
            element.element_name.value: element for element in all_information_elements
        }
        assert set(elements_by_name) == {"Supplier Legal Name", "Risk Event Severity"}
        assert elements_by_name["Supplier Legal Name"].obligation is Obligation.REQUIRED
        assert elements_by_name["Risk Event Severity"].obligation is Obligation.CONDITIONAL

        concept_requirement_count = len(session.scalars(select(ConceptRequirementORM)).all())
        relationship_requirement_count = len(
            session.scalars(select(RelationshipRequirementORM)).all()
        )
        information_element_requirement_count = len(
            session.scalars(select(InformationElementRequirementORM)).all()
        )

    with factory() as session:
        second = BlueprintSeeder(session).load()
        session.commit()

    assert second.created is False
    assert second.blueprint_id == first.blueprint_id

    with factory() as session:
        assert (
            len(session.scalars(select(ConceptRequirementORM)).all()) == concept_requirement_count
        )
        assert (
            len(session.scalars(select(RelationshipRequirementORM)).all())
            == relationship_requirement_count
        )
        assert (
            len(session.scalars(select(InformationElementRequirementORM)).all())
            == information_element_requirement_count
        )


def test_canonical_blueprint_is_readable_through_the_g3_application_service(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        summary = BlueprintSeeder(session).load()
        session.commit()

    with factory() as session:
        service = BlueprintApplicationService(repository=BlueprintRepositoryImpl(session))
        result = service.get_by_id(summary.blueprint_id)

    assert result is not None
    assert result.blueprint_name.value == CANONICAL_BLUEPRINT_NAME
    assert len(result.concept_requirements) == 10
