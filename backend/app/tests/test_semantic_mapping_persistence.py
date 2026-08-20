"""Unit-level tests for the Gate H H1 SemanticMapping domain model and ORM
shape (CDD-019 §8, §11, §12, H1 Source Field / Semantic Mapping Artifact
Authorization companion). No database connection required. Real FK
enforcement and the bidirectional Approved-mapping uniqueness rules are
covered by test_semantic_mapping_persistence_postgres.py.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.models.semantic_mapping import SemanticMappingORM

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _semantic_mapping(**overrides: object) -> SemanticMapping:
    defaults: dict[str, object] = {
        "semantic_mapping_id": Identifier(uuid4()),
        "source_field_id": Identifier(uuid4()),
        "information_element_requirement_id": Identifier(uuid4()),
        "lifecycle_state": LifecycleState.ACTIVE,
        "governance_status": GovernanceStatus.APPROVED,
        "created_by": Identifier(uuid4()),
        "created_on": NOW,
    }
    defaults.update(overrides)
    return SemanticMapping(**defaults)  # type: ignore[arg-type]


def test_semantic_mapping_requires_timezone_aware_created_on() -> None:
    with pytest.raises(ValidationException):
        _semantic_mapping(created_on=datetime(2026, 1, 1))  # noqa: DTZ001


def test_semantic_mapping_requires_identifiers() -> None:
    with pytest.raises(ValidationException):
        SemanticMapping(
            semantic_mapping_id=Identifier(uuid4()),
            source_field_id=uuid4(),  # type: ignore[arg-type]
            information_element_requirement_id=Identifier(uuid4()),
            lifecycle_state=LifecycleState.DRAFT,
            governance_status=GovernanceStatus.PROPOSED,
            created_by=Identifier(uuid4()),
            created_on=NOW,
        )


def test_semantic_mapping_carries_exactly_the_authorized_fields() -> None:
    field_names = set(SemanticMapping.__dataclass_fields__)
    assert field_names == {
        "semantic_mapping_id",
        "source_field_id",
        "information_element_requirement_id",
        "lifecycle_state",
        "governance_status",
        "created_by",
        "created_on",
        "modified_by",
        "modified_on",
    }


def test_semantic_mapping_carries_no_transformation_expression_or_condition_field() -> None:
    """Structural check: no field name suggesting computation, ranking,
    confidence, transformation, derivation, or conditional logic exists on
    the dataclass (CDD-019 §4, §12)."""
    forbidden_substrings = (
        "transform",
        "expression",
        "condition",
        "derive",
        "calculat",
        "confidence",
        "rank",
        "priority",
        "convert",
    )
    field_names = set(SemanticMapping.__dataclass_fields__)
    for field_name in field_names:
        for forbidden in forbidden_substrings:
            assert forbidden not in field_name.lower()


def test_semantic_mapping_orm_carries_no_tenant_id_column() -> None:
    column_names = {column.name for column in SemanticMappingORM.__table__.columns}
    assert "tenant_id" not in column_names


def test_semantic_mapping_orm_carries_no_information_element_definition_column() -> None:
    column_names = {column.name for column in SemanticMappingORM.__table__.columns}
    assert "information_element_definition_id" not in column_names


def test_semantic_mapping_orm_carries_no_version_chain_columns() -> None:
    column_names = {column.name for column in SemanticMappingORM.__table__.columns}
    assert "version_number" not in column_names
    assert "previous_version_id" not in column_names


def test_semantic_mapping_orm_references_source_field_and_information_element_requirement() -> None:
    foreign_key_targets = {fk.target_fullname for fk in SemanticMappingORM.__table__.foreign_keys}
    assert "source_fields.source_field_id" in foreign_key_targets
    assert (
        "information_element_requirements.information_element_requirement_id" in foreign_key_targets
    )


def test_semantic_mapping_orm_has_approved_only_partial_unique_index_on_source_field() -> None:
    matching = [
        index
        for index in SemanticMappingORM.__table__.indexes  # type: ignore[attr-defined]
        if index.name == "uq_semantic_mappings_approved_source_field"
    ]
    assert len(matching) == 1
    index = matching[0]
    assert index.unique is True
    assert {column.name for column in index.columns} == {"source_field_id"}
    assert index.dialect_options["postgresql"]["where"] is not None
