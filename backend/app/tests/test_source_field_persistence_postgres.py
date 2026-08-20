"""Postgres-backed persistence tests for the Gate H H1 SourceField
foundation (CDD-019 §7, H1 Source Field / Semantic Mapping Artifact
Authorization companion). Proves real FK constraint enforcement and the
`UniqueConstraint(source_object_id, field_label)` physical-field-identity
invariant against a live database -- the first real-PostgreSQL evidence
this repository has for either mechanism on these two new tables.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.integration import SourceField
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _seed_source_object(session: Session, *, tenant_id: str) -> UUID:
    system_id = uuid4()
    object_id = uuid4()
    session.add(
        SourceSystem(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=f"Source System {system_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
        )
    )
    session.flush()
    session.add(
        SourceObject(
            source_object_id=object_id,
            tenant_id=tenant_id,
            source_object_name=f"Source Object {object_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            source_system_id=system_id,
        )
    )
    session.flush()
    return object_id


def _source_field(*, source_object_id: UUID, field_label: str) -> SourceField:
    return SourceField(
        source_field_id=Identifier(uuid4()),
        source_object_id=Identifier(source_object_id),
        field_label=CanonicalName(field_label),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
    )


def test_source_field_round_trips_through_create_and_get_by_id(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=f"tenant-{uuid4()}")
        session.commit()

        repository = SourceFieldRepositoryImpl(session)
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        repository.create(field)
        session.commit()

        loaded = repository.get_by_id(field.source_field_id.value)

    assert loaded is not None
    assert loaded.source_field_id == field.source_field_id
    assert loaded.source_object_id == Identifier(object_id)
    assert loaded.field_label.value == "LFA1-NAME1"


def test_get_by_id_returns_none_for_a_nonexistent_source_field(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        repository = SourceFieldRepositoryImpl(session)
        assert repository.get_by_id(uuid4()) is None


def test_invalid_source_object_reference_is_rejected_at_the_database_layer(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        repository = SourceFieldRepositoryImpl(session)
        field = _source_field(source_object_id=uuid4(), field_label="LFA1-NAME1")
        repository.create(field)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_duplicate_field_label_within_the_same_source_object_is_rejected(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=f"tenant-{uuid4()}")
        session.commit()

        repository = SourceFieldRepositoryImpl(session)
        repository.create(_source_field(source_object_id=object_id, field_label="LFA1-NAME1"))
        session.commit()

        repository.create(_source_field(source_object_id=object_id, field_label="LFA1-NAME1"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_same_field_label_across_different_source_objects_is_allowed(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_a = _seed_source_object(session, tenant_id=f"tenant-a-{uuid4()}")
        object_b = _seed_source_object(session, tenant_id=f"tenant-b-{uuid4()}")
        session.commit()

        repository = SourceFieldRepositoryImpl(session)
        repository.create(_source_field(source_object_id=object_a, field_label="LFA1-NAME1"))
        repository.create(_source_field(source_object_id=object_b, field_label="LFA1-NAME1"))
        session.commit()
