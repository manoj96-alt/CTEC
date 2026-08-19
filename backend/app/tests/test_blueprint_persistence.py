"""Unit-level tests for the CDD-017 Blueprint domain model and ORM shape
(Gate G G2; CDD-017 §6-9, G2 Persistence and Domain Artifact Authorization
companion). No database connection required -- these tests exercise domain
dataclass validation and static SQLAlchemy table metadata only. Real
ontology-FK enforcement and version-chain behavior against a live database
are covered by test_blueprint_persistence_postgres.py.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

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
from app.infrastructure.persistence.models.blueprint import (
    BlueprintORM,
    ConceptRequirementORM,
    InformationElementRequirementORM,
    RelationshipRequirementORM,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _blueprint(**overrides: object) -> Blueprint:
    defaults: dict[str, object] = {
        "blueprint_id": Identifier(uuid4()),
        "blueprint_name": CanonicalName("CTEC Semiconductor Supply Chain Blueprint"),
        "lifecycle_state": LifecycleState.ACTIVE,
        "governance_status": GovernanceStatus.APPROVED,
        "created_by": Identifier(uuid4()),
        "created_on": NOW,
    }
    defaults.update(overrides)
    return Blueprint(**defaults)  # type: ignore[arg-type]


def test_obligation_is_a_closed_three_value_vocabulary() -> None:
    assert {member.value for member in Obligation} == {"REQUIRED", "CONDITIONAL", "OPTIONAL"}


def test_blueprint_requires_timezone_aware_created_on() -> None:
    with pytest.raises(ValidationException):
        _blueprint(
            created_on=datetime(2026, 1, 1)
        )  # noqa: DTZ001 - deliberately naive negative fixture


def test_blueprint_requires_a_canonical_name() -> None:
    with pytest.raises(ValidationException):
        Blueprint(
            blueprint_id=Identifier(uuid4()),
            blueprint_name="not a CanonicalName",  # type: ignore[arg-type]
            lifecycle_state=LifecycleState.DRAFT,
            governance_status=GovernanceStatus.PROPOSED,
            created_by=Identifier(uuid4()),
            created_on=NOW,
        )


def test_concept_requirement_requires_identifiers_and_obligation() -> None:
    with pytest.raises(ValidationException):
        ConceptRequirement(
            concept_requirement_id=Identifier(uuid4()),
            blueprint_id=Identifier(uuid4()),
            entity_type_id=Identifier(uuid4()),
            obligation="REQUIRED",  # type: ignore[arg-type]
        )


def test_relationship_requirement_requires_all_four_identifiers() -> None:
    with pytest.raises(ValidationException):
        RelationshipRequirement(
            relationship_requirement_id=Identifier(uuid4()),
            concept_requirement_id=Identifier(uuid4()),
            relationship_type_id=Identifier(uuid4()),
            target_entity_type_id=uuid4(),  # type: ignore[arg-type]
            obligation=Obligation.REQUIRED,
        )


def test_information_element_requirement_carries_only_name_description_obligation() -> None:
    element = InformationElementRequirement(
        information_element_requirement_id=Identifier(uuid4()),
        concept_requirement_id=Identifier(uuid4()),
        element_name=CanonicalName("Supplier Legal Name"),
        description=Description("The supplier's registered legal entity name."),
        obligation=Obligation.REQUIRED,
    )
    field_names = {field for field in InformationElementRequirement.__dataclass_fields__}
    assert field_names == {
        "information_element_requirement_id",
        "concept_requirement_id",
        "element_name",
        "description",
        "obligation",
    }
    assert element.element_name.value == "Supplier Legal Name"


@pytest.mark.parametrize(
    "orm_class",
    [
        BlueprintORM,
        ConceptRequirementORM,
        RelationshipRequirementORM,
        InformationElementRequirementORM,
    ],
)
def test_no_blueprint_table_carries_a_tenant_id_column(orm_class: type) -> None:
    column_names = {column.name for column in orm_class.__table__.columns}  # type: ignore[attr-defined]
    assert "tenant_id" not in column_names


def test_blueprint_name_column_carries_no_unique_constraint() -> None:
    column = BlueprintORM.__table__.columns["blueprint_name"]
    assert column.unique is not True


def test_blueprint_carries_its_own_version_chain_not_a_separate_version_table() -> None:
    column_names = {column.name for column in BlueprintORM.__table__.columns}
    assert "version_number" in column_names
    assert "previous_version_id" in column_names


def test_concept_requirement_references_entity_types_by_foreign_key() -> None:
    foreign_key_targets = {
        fk.target_fullname for fk in ConceptRequirementORM.__table__.foreign_keys
    }
    assert "entity_types.entity_type_id" in foreign_key_targets
    assert "blueprints.blueprint_id" in foreign_key_targets


def test_relationship_requirement_references_relationship_types_and_entity_types() -> None:
    foreign_key_targets = {
        fk.target_fullname for fk in RelationshipRequirementORM.__table__.foreign_keys
    }
    assert "relationship_types.relationship_type_id" in foreign_key_targets
    assert "entity_types.entity_type_id" in foreign_key_targets
    assert "concept_requirements.concept_requirement_id" in foreign_key_targets


def test_information_element_requirement_has_no_type_system_column() -> None:
    column_names = {column.name for column in InformationElementRequirementORM.__table__.columns}
    assert column_names == {
        "information_element_requirement_id",
        "concept_requirement_id",
        "element_name",
        "description",
        "obligation",
    }
