"""Postgres-backed persistence tests for the CDD-017 Blueprint requirement
contract (Gate G G2; CDD-017 §6-9, G2 Persistence and Domain Artifact
Authorization companion; Gate G G4, CDD-018 §13, G4 Blueprint Conformance
Artifact Authorization). Proves real FK constraint enforcement against
the existing governed ontology vocabulary -- single-version scope only
(the version re-parenting question CDD-017 §8 leaves open is out of scope
for G2, see the companion's "Remaining risks").
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.ontology_seed import OntologySeeder

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _entity_type_id(session: Session, name: str) -> Identifier:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return Identifier(value)


def _relationship_type_id(session: Session, name: str) -> Identifier:
    value = session.scalar(
        select(RelationshipType.relationship_type_id).where(
            RelationshipType.relationship_type_name == name
        )
    )
    assert value is not None
    return Identifier(value)


def test_blueprint_with_concept_relationship_and_information_element_requirements_round_trips(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

        supplier_type_id = _entity_type_id(session, "Supplier")
        material_type_id = _entity_type_id(session, "Material")
        supplies_type_id = _relationship_type_id(session, "supplies")

        blueprint_id = Identifier(uuid4())
        concept_requirement_id = Identifier(uuid4())
        blueprint_name = f"G2 Blueprint Round-Trip Test Blueprint {uuid4()}"
        blueprint = Blueprint(
            blueprint_id=blueprint_id,
            blueprint_name=CanonicalName(blueprint_name),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
            concept_requirements=(
                ConceptRequirement(
                    concept_requirement_id=concept_requirement_id,
                    blueprint_id=blueprint_id,
                    entity_type_id=supplier_type_id,
                    obligation=Obligation.REQUIRED,
                    domain_label="Sourcing",
                    relationship_requirements=(
                        RelationshipRequirement(
                            relationship_requirement_id=Identifier(uuid4()),
                            concept_requirement_id=concept_requirement_id,
                            relationship_type_id=supplies_type_id,
                            target_entity_type_id=material_type_id,
                            obligation=Obligation.REQUIRED,
                        ),
                    ),
                    information_element_requirements=(
                        InformationElementRequirement(
                            information_element_requirement_id=Identifier(uuid4()),
                            concept_requirement_id=concept_requirement_id,
                            element_name=CanonicalName("Supplier Legal Name"),
                            description=Description("The supplier's registered legal entity name."),
                            obligation=Obligation.REQUIRED,
                        ),
                    ),
                ),
            ),
        )

        repository = BlueprintRepositoryImpl(session)
        repository.create(blueprint)
        session.commit()

        loaded = repository.get_by_id(blueprint.blueprint_id.value)

    assert loaded is not None
    assert loaded.blueprint_name.value == blueprint_name
    assert len(loaded.concept_requirements) == 1
    concept = loaded.concept_requirements[0]
    assert concept.entity_type_id == supplier_type_id
    assert concept.domain_label == "Sourcing"
    assert len(concept.relationship_requirements) == 1
    assert concept.relationship_requirements[0].relationship_type_id == supplies_type_id
    assert concept.relationship_requirements[0].target_entity_type_id == material_type_id
    assert len(concept.information_element_requirements) == 1
    assert concept.information_element_requirements[0].element_name.value == "Supplier Legal Name"


def test_invalid_entity_type_reference_is_rejected_at_the_database_layer(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

        blueprint_id = Identifier(uuid4())
        blueprint = Blueprint(
            blueprint_id=blueprint_id,
            blueprint_name=CanonicalName("CTEC Invalid Reference Blueprint"),
            lifecycle_state=LifecycleState.DRAFT,
            governance_status=GovernanceStatus.PROPOSED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
            concept_requirements=(
                ConceptRequirement(
                    concept_requirement_id=Identifier(uuid4()),
                    blueprint_id=blueprint_id,
                    entity_type_id=Identifier(uuid4()),  # does not exist in entity_types
                    obligation=Obligation.REQUIRED,
                ),
            ),
        )
        repository = BlueprintRepositoryImpl(session)
        repository.create(blueprint)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_invalid_relationship_type_reference_is_rejected_at_the_database_layer(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

        supplier_type_id = _entity_type_id(session, "Supplier")
        material_type_id = _entity_type_id(session, "Material")
        blueprint_id = Identifier(uuid4())
        concept_requirement_id = Identifier(uuid4())
        blueprint = Blueprint(
            blueprint_id=blueprint_id,
            blueprint_name=CanonicalName("CTEC Invalid Relationship Reference Blueprint"),
            lifecycle_state=LifecycleState.DRAFT,
            governance_status=GovernanceStatus.PROPOSED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
            concept_requirements=(
                ConceptRequirement(
                    concept_requirement_id=concept_requirement_id,
                    blueprint_id=blueprint_id,
                    entity_type_id=supplier_type_id,
                    obligation=Obligation.REQUIRED,
                    relationship_requirements=(
                        RelationshipRequirement(
                            relationship_requirement_id=Identifier(uuid4()),
                            concept_requirement_id=concept_requirement_id,
                            relationship_type_id=Identifier(uuid4()),  # does not exist
                            target_entity_type_id=material_type_id,
                            obligation=Obligation.REQUIRED,
                        ),
                    ),
                ),
            ),
        )
        repository = BlueprintRepositoryImpl(session)
        repository.create(blueprint)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_get_by_id_returns_none_for_a_nonexistent_blueprint(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        repository = BlueprintRepositoryImpl(session)
        assert repository.get_by_id(uuid4()) is None


def test_get_approved_by_name_returns_the_matching_approved_blueprint(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"G4 Resolution Test Blueprint {uuid4()}"
    with factory() as session:
        blueprint = Blueprint(
            blueprint_id=Identifier(uuid4()),
            blueprint_name=CanonicalName(blueprint_name),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
        )
        repository = BlueprintRepositoryImpl(session)
        repository.create(blueprint)
        session.commit()

        result = repository.get_approved_by_name(blueprint_name)

    assert result is not None
    assert result.blueprint_id == blueprint.blueprint_id
    assert result.blueprint_name.value == blueprint_name
    assert result.governance_status is GovernanceStatus.APPROVED


def test_get_approved_by_name_returns_none_when_no_approved_match_exists(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"G4 Nonexistent Blueprint {uuid4()}"
    with factory() as session:
        repository = BlueprintRepositoryImpl(session)
        assert repository.get_approved_by_name(blueprint_name) is None


def test_get_approved_by_name_ignores_non_approved_rows(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"G4 Draft Blueprint {uuid4()}"
    with factory() as session:
        blueprint = Blueprint(
            blueprint_id=Identifier(uuid4()),
            blueprint_name=CanonicalName(blueprint_name),
            lifecycle_state=LifecycleState.DRAFT,
            governance_status=GovernanceStatus.PROPOSED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
        )
        repository = BlueprintRepositoryImpl(session)
        repository.create(blueprint)
        session.commit()

        assert repository.get_approved_by_name(blueprint_name) is None


def test_get_approved_by_name_raises_when_multiple_approved_matches_exist(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"G4 Ambiguous Blueprint {uuid4()}"
    with factory() as session:
        repository = BlueprintRepositoryImpl(session)
        for _ in range(2):
            repository.create(
                Blueprint(
                    blueprint_id=Identifier(uuid4()),
                    blueprint_name=CanonicalName(blueprint_name),
                    lifecycle_state=LifecycleState.ACTIVE,
                    governance_status=GovernanceStatus.APPROVED,
                    created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                    created_on=NOW,
                )
            )
        session.commit()

        with pytest.raises(ValidationException, match="Multiple Approved Blueprint rows found"):
            repository.get_approved_by_name(blueprint_name)
