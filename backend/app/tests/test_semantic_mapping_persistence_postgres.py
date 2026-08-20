"""Postgres-backed persistence tests for the Gate H H1 SemanticMapping
foundation (CDD-019 §8, §11, §18, H1 Source Field / Semantic Mapping
Artifact Authorization companion). Proves real FK constraint enforcement
and both halves of CDD-019 §11's bidirectional Approved-mapping uniqueness
rule -- including, critically, the PostgreSQL partial unique index's actual
rejection behavior at the database layer, independent of the repository's
own application-layer check (the first real-PostgreSQL evidence this
repository has for this schema pattern).
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

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
)
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.semantic_mapping import SemanticMappingORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.tests.test_source_field_persistence_postgres import _seed_source_object, _source_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _entity_type_id(session: Session, name: str) -> UUID:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return value


def _seed_information_element_requirement(
    session: Session, *, element_name: str, entity_type_name: str = "Supplier"
) -> UUID:
    OntologySeeder(session).load()
    session.flush()

    entity_type_id = _entity_type_id(session, entity_type_name)
    blueprint_id = Identifier(uuid4())
    concept_requirement_id = Identifier(uuid4())
    information_element_requirement_id = Identifier(uuid4())
    blueprint = Blueprint(
        blueprint_id=blueprint_id,
        blueprint_name=CanonicalName(f"H1 Test Blueprint {uuid4()}"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(
            ConceptRequirement(
                concept_requirement_id=concept_requirement_id,
                blueprint_id=blueprint_id,
                entity_type_id=Identifier(entity_type_id),
                obligation=Obligation.REQUIRED,
                information_element_requirements=(
                    InformationElementRequirement(
                        information_element_requirement_id=information_element_requirement_id,
                        concept_requirement_id=concept_requirement_id,
                        element_name=CanonicalName(element_name),
                        description=Description(f"H1 test information element {element_name}."),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
            ),
        ),
    )
    BlueprintRepositoryImpl(session).create(blueprint)
    session.flush()
    return information_element_requirement_id.value


def _semantic_mapping(
    *,
    source_field_id: UUID,
    information_element_requirement_id: UUID,
    governance_status: GovernanceStatus = GovernanceStatus.APPROVED,
) -> SemanticMapping:
    return SemanticMapping(
        semantic_mapping_id=Identifier(uuid4()),
        source_field_id=Identifier(source_field_id),
        information_element_requirement_id=Identifier(information_element_requirement_id),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=governance_status,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
    )


def test_semantic_mapping_round_trips_through_create_and_get_by_id(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=f"tenant-{uuid4()}")
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_id = _seed_information_element_requirement(session, element_name="Legal Name A")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        mapping = _semantic_mapping(
            source_field_id=field.source_field_id.value,
            information_element_requirement_id=element_id,
        )
        repository.create(mapping)
        session.commit()

        loaded = repository.get_by_id(mapping.semantic_mapping_id.value)

    assert loaded is not None
    assert loaded.source_field_id == field.source_field_id
    assert loaded.information_element_requirement_id == Identifier(element_id)


def test_get_by_id_returns_none_for_a_nonexistent_semantic_mapping(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        repository = SemanticMappingRepositoryImpl(session)
        assert repository.get_by_id(uuid4()) is None


def test_invalid_source_field_reference_is_rejected_at_the_database_layer(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        element_id = _seed_information_element_requirement(session, element_name="Legal Name B")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        mapping = _semantic_mapping(
            source_field_id=uuid4(), information_element_requirement_id=element_id
        )
        repository.create(mapping)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_invalid_information_element_requirement_reference_is_rejected_at_the_database_layer(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=f"tenant-{uuid4()}")
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        mapping = _semantic_mapping(
            source_field_id=field.source_field_id.value,
            information_element_requirement_id=uuid4(),
        )
        repository.create(mapping)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_one_source_field_cannot_have_two_simultaneously_approved_mappings(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=f"tenant-{uuid4()}")
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_x = _seed_information_element_requirement(session, element_name="Legal Name X1")
        element_y = _seed_information_element_requirement(session, element_name="Legal Name Y1")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        repository.create(
            _semantic_mapping(
                source_field_id=field.source_field_id.value,
                information_element_requirement_id=element_x,
            )
        )
        session.commit()

        with pytest.raises(ValidationException, match="Approved SemanticMapping already exists"):
            repository.create(
                _semantic_mapping(
                    source_field_id=field.source_field_id.value,
                    information_element_requirement_id=element_y,
                )
            )


def test_two_source_fields_cannot_both_approve_the_same_element_in_one_tenant(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        object_id = _seed_source_object(session, tenant_id=tenant_id)
        field_a = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        field_b = _source_field(source_object_id=object_id, field_label="LFA1-NAME2")
        SourceFieldRepositoryImpl(session).create(field_a)
        SourceFieldRepositoryImpl(session).create(field_b)
        element_id = _seed_information_element_requirement(session, element_name="Legal Name X2")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        repository.create(
            _semantic_mapping(
                source_field_id=field_a.source_field_id.value,
                information_element_requirement_id=element_id,
            )
        )
        session.commit()

        with pytest.raises(ValidationException, match="Approved SemanticMapping already exists"):
            repository.create(
                _semantic_mapping(
                    source_field_id=field_b.source_field_id.value,
                    information_element_requirement_id=element_id,
                )
            )


def test_equivalent_mappings_in_different_tenants_are_independent(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_a = _seed_source_object(session, tenant_id=f"tenant-a-{uuid4()}")
        object_b = _seed_source_object(session, tenant_id=f"tenant-b-{uuid4()}")
        field_a = _source_field(source_object_id=object_a, field_label="LFA1-NAME1")
        field_b = _source_field(source_object_id=object_b, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field_a)
        SourceFieldRepositoryImpl(session).create(field_b)
        element_id = _seed_information_element_requirement(session, element_name="Legal Name X3")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        repository.create(
            _semantic_mapping(
                source_field_id=field_a.source_field_id.value,
                information_element_requirement_id=element_id,
            )
        )
        repository.create(
            _semantic_mapping(
                source_field_id=field_b.source_field_id.value,
                information_element_requirement_id=element_id,
            )
        )
        session.commit()


def test_approved_mapping_coexists_with_retired_history_for_the_same_source_field(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=f"tenant-{uuid4()}")
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_id = _seed_information_element_requirement(session, element_name="Legal Name X4")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        retired = _semantic_mapping(
            source_field_id=field.source_field_id.value,
            information_element_requirement_id=element_id,
            governance_status=GovernanceStatus.RETIRED,
        )
        repository.create(retired)
        session.commit()

        approved = _semantic_mapping(
            source_field_id=field.source_field_id.value,
            information_element_requirement_id=element_id,
            governance_status=GovernanceStatus.APPROVED,
        )
        repository.create(approved)
        session.commit()

        assert repository.get_by_id(retired.semantic_mapping_id.value) is not None
        assert repository.get_by_id(approved.semantic_mapping_id.value) is not None


def test_draft_mapping_does_not_block_an_approved_mapping_for_a_different_element(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=f"tenant-{uuid4()}")
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_draft = _seed_information_element_requirement(
            session, element_name="Legal Name Draft"
        )
        element_approved = _seed_information_element_requirement(
            session, element_name="Legal Name Draft Approved Sibling"
        )
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        draft = _semantic_mapping(
            source_field_id=field.source_field_id.value,
            information_element_requirement_id=element_draft,
            governance_status=GovernanceStatus.PROPOSED,
        )
        repository.create(draft)
        session.commit()

        assert repository.get_by_id(draft.semantic_mapping_id.value) is not None

        # The claim in this test's name is only proven by actually attempting
        # the Approved mapping the Draft must not block -- not by merely
        # confirming the Draft row itself persisted.
        approved = _semantic_mapping(
            source_field_id=field.source_field_id.value,
            information_element_requirement_id=element_approved,
            governance_status=GovernanceStatus.APPROVED,
        )
        repository.create(approved)
        session.commit()

        assert repository.get_by_id(approved.semantic_mapping_id.value) is not None


def test_source_side_partial_index_rejects_a_second_approved_row_at_the_database_layer(
    migrated_engine: Engine,
) -> None:
    """Bypasses SemanticMappingRepositoryImpl.create()'s own application-
    layer pre-check entirely, inserting two raw ORM rows directly, to prove
    the PostgreSQL partial unique index itself -- not merely the repository
    logic -- rejects a second Approved row for the same source_field_id."""
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=f"tenant-{uuid4()}")
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_x = _seed_information_element_requirement(session, element_name="Legal Name Raw1")
        element_y = _seed_information_element_requirement(session, element_name="Legal Name Raw2")
        session.commit()

        session.add(
            SemanticMappingORM(
                semantic_mapping_id=uuid4(),
                source_field_id=field.source_field_id.value,
                information_element_requirement_id=element_x,
                lifecycle_state="Active",
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
            )
        )
        session.commit()

        session.add(
            SemanticMappingORM(
                semantic_mapping_id=uuid4(),
                source_field_id=field.source_field_id.value,
                information_element_requirement_id=element_y,
                lifecycle_state="Active",
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_approved_mapping_resolves_with_correct_provenance(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        object_id = _seed_source_object(session, tenant_id=tenant_id)
        source_system_id = session.scalar(
            select(SourceObjectORM.source_system_id).where(
                SourceObjectORM.source_object_id == object_id
            )
        )
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_id = _seed_information_element_requirement(session, element_name="Resolution A")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        mapping = _semantic_mapping(
            source_field_id=field.source_field_id.value,
            information_element_requirement_id=element_id,
        )
        repository.create(mapping)
        session.commit()

        result = repository.get_approved_by_information_element_requirement(element_id, tenant_id)

    assert result is not None
    assert result.semantic_mapping_id == mapping.semantic_mapping_id.value
    assert result.source_field_id == field.source_field_id.value
    assert result.source_object_id == object_id
    assert result.source_system_id == source_system_id
    assert result.information_element_requirement_id == element_id
    assert result.created_by == BOOTSTRAP_SYSTEM_ENTITY_ID


def test_resolution_returns_none_when_only_a_draft_mapping_exists(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        object_id = _seed_source_object(session, tenant_id=tenant_id)
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_id = _seed_information_element_requirement(session, element_name="Resolution B")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        repository.create(
            _semantic_mapping(
                source_field_id=field.source_field_id.value,
                information_element_requirement_id=element_id,
                governance_status=GovernanceStatus.PROPOSED,
            )
        )
        session.commit()

        result = repository.get_approved_by_information_element_requirement(element_id, tenant_id)

    assert result is None


def test_resolution_returns_none_when_only_a_retired_mapping_exists(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        object_id = _seed_source_object(session, tenant_id=tenant_id)
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_id = _seed_information_element_requirement(session, element_name="Resolution C")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        repository.create(
            _semantic_mapping(
                source_field_id=field.source_field_id.value,
                information_element_requirement_id=element_id,
                governance_status=GovernanceStatus.RETIRED,
            )
        )
        session.commit()

        result = repository.get_approved_by_information_element_requirement(element_id, tenant_id)

    assert result is None


def test_resolution_returns_none_when_no_mapping_exists_for_the_requirement(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        element_id = _seed_information_element_requirement(session, element_name="Resolution D")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        result = repository.get_approved_by_information_element_requirement(element_id, tenant_id)

    assert result is None


def test_resolution_does_not_cross_tenant_boundaries(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_a = f"tenant-a-{uuid4()}"
        tenant_b = f"tenant-b-{uuid4()}"
        object_id = _seed_source_object(session, tenant_id=tenant_a)
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_id = _seed_information_element_requirement(session, element_name="Resolution E")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        repository.create(
            _semantic_mapping(
                source_field_id=field.source_field_id.value,
                information_element_requirement_id=element_id,
            )
        )
        session.commit()

        result = repository.get_approved_by_information_element_requirement(element_id, tenant_b)

    assert result is None


def test_resolution_raises_on_ambiguous_approved_rows(migrated_engine: Engine) -> None:
    """Bypasses SemanticMappingRepositoryImpl.create()'s own application-
    layer target-side check entirely, inserting two raw ORM rows for two
    different SourceFields both Approved for the same
    information_element_requirement_id within the same tenant -- the one
    invariant H1 has no database backstop for (CDD-019 §11: tenant is
    join-derived, not a stored column) -- to prove the resolution query
    itself raises defensively rather than silently selecting either row."""
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        object_id = _seed_source_object(session, tenant_id=tenant_id)
        field_a = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        field_b = _source_field(source_object_id=object_id, field_label="LFA1-NAME2")
        SourceFieldRepositoryImpl(session).create(field_a)
        SourceFieldRepositoryImpl(session).create(field_b)
        element_id = _seed_information_element_requirement(session, element_name="Resolution F")
        session.commit()

        session.add(
            SemanticMappingORM(
                semantic_mapping_id=uuid4(),
                source_field_id=field_a.source_field_id.value,
                information_element_requirement_id=element_id,
                lifecycle_state="Active",
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
            )
        )
        session.add(
            SemanticMappingORM(
                semantic_mapping_id=uuid4(),
                source_field_id=field_b.source_field_id.value,
                information_element_requirement_id=element_id,
                lifecycle_state="Active",
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
            )
        )
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        with pytest.raises(ValidationException, match="Ambiguous Approved SemanticMapping"):
            repository.get_approved_by_information_element_requirement(element_id, tenant_id)


def test_resolution_is_deterministic_across_repeated_calls(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        object_id = _seed_source_object(session, tenant_id=tenant_id)
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(field)
        element_id = _seed_information_element_requirement(session, element_name="Resolution G")
        session.commit()

        repository = SemanticMappingRepositoryImpl(session)
        repository.create(
            _semantic_mapping(
                source_field_id=field.source_field_id.value,
                information_element_requirement_id=element_id,
            )
        )
        session.commit()

        first = repository.get_approved_by_information_element_requirement(element_id, tenant_id)
        second = repository.get_approved_by_information_element_requirement(element_id, tenant_id)

    assert first == second
