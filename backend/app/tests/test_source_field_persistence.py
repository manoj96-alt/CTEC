"""Unit-level tests for the Gate H H1 SourceField domain model and ORM shape
(CDD-019 §7, H1 Source Field / Semantic Mapping Artifact Authorization
companion). No database connection required. Real FK enforcement and the
physical-field-identity uniqueness constraint are covered by
test_source_field_persistence_postgres.py.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.integration import SourceField
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.models.source_field import SourceFieldORM

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _source_field(**overrides: object) -> SourceField:
    defaults: dict[str, object] = {
        "source_field_id": Identifier(uuid4()),
        "source_object_id": Identifier(uuid4()),
        "field_label": CanonicalName("LFA1-NAME1"),
        "lifecycle_state": LifecycleState.ACTIVE,
        "governance_status": GovernanceStatus.APPROVED,
        "created_by": Identifier(uuid4()),
        "created_on": NOW,
    }
    defaults.update(overrides)
    return SourceField(**defaults)  # type: ignore[arg-type]


def test_source_field_requires_timezone_aware_created_on() -> None:
    with pytest.raises(ValidationException):
        _source_field(created_on=datetime(2026, 1, 1))  # noqa: DTZ001


def test_source_field_requires_a_canonical_name_field_label() -> None:
    with pytest.raises(ValidationException):
        SourceField(
            source_field_id=Identifier(uuid4()),
            source_object_id=Identifier(uuid4()),
            field_label="not a CanonicalName",  # type: ignore[arg-type]
            lifecycle_state=LifecycleState.DRAFT,
            governance_status=GovernanceStatus.PROPOSED,
            created_by=Identifier(uuid4()),
            created_on=NOW,
        )


def test_source_field_requires_identifiers() -> None:
    with pytest.raises(ValidationException):
        SourceField(
            source_field_id=uuid4(),  # type: ignore[arg-type]
            source_object_id=Identifier(uuid4()),
            field_label=CanonicalName("LFA1-NAME1"),
            lifecycle_state=LifecycleState.DRAFT,
            governance_status=GovernanceStatus.PROPOSED,
            created_by=Identifier(uuid4()),
            created_on=NOW,
        )


def test_source_field_carries_exactly_the_authorized_fields() -> None:
    field_names = set(SourceField.__dataclass_fields__)
    assert field_names == {
        "source_field_id",
        "source_object_id",
        "field_label",
        "lifecycle_state",
        "governance_status",
        "created_by",
        "created_on",
        "modified_by",
        "modified_on",
    }


def test_source_field_orm_carries_no_tenant_id_column() -> None:
    column_names = {column.name for column in SourceFieldORM.__table__.columns}
    assert "tenant_id" not in column_names


def test_source_field_orm_carries_no_source_system_id_column() -> None:
    column_names = {column.name for column in SourceFieldORM.__table__.columns}
    assert "source_system_id" not in column_names


def test_source_field_orm_carries_no_version_chain_columns() -> None:
    column_names = {column.name for column in SourceFieldORM.__table__.columns}
    assert "version_number" not in column_names
    assert "previous_version_id" not in column_names


def test_source_field_orm_references_source_object_by_foreign_key() -> None:
    foreign_key_targets = {fk.target_fullname for fk in SourceFieldORM.__table__.foreign_keys}
    assert "source_objects.source_object_id" in foreign_key_targets


def test_source_field_orm_has_object_label_unique_constraint() -> None:
    unique_constraints = [
        constraint
        for constraint in SourceFieldORM.__table__.constraints  # type: ignore[attr-defined]
        if constraint.__class__.__name__ == "UniqueConstraint"
    ]
    matching = [
        constraint
        for constraint in unique_constraints
        if {column.name for column in constraint.columns} == {"source_object_id", "field_label"}
    ]
    assert len(matching) == 1
