"""Postgres-backed proof of the Gate H H3 demo seeder (CDD-019 §15, §22,
§27 items 2, 7, 10, 11; H3 Deterministic Mapping Demonstration Artifact
Authorization): idempotency, and -- most importantly -- that the seeded
demonstration mapping reproduces its governed outcome through the real,
unmodified H2 `SemanticMappingResolutionApplicationService.
resolve_approved_source_field(...)`, not a special test-only code path.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.application.semantic_mapping_resolution import (
    SemanticMappingResolutionApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import (
    CANONICAL_BLUEPRINT_NAME,
    BlueprintSeeder,
)
from app.infrastructure.persistence.demo_semantic_mapping_seeder import (
    DemoSemanticMappingSeeder,
    DemoSemanticMappingSeedSummary,
)
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.tests.test_source_field_persistence_postgres import _seed_source_object, _source_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _seed(factory: "sessionmaker[Session]") -> DemoSemanticMappingSeedSummary:
    with factory() as session:
        summary = DemoSemanticMappingSeeder(session).seed()
        session.commit()
    return summary


def _element_id(session: Session, element_name: str) -> UUID:
    blueprint = BlueprintApplicationService(
        repository=BlueprintRepositoryImpl(session)
    ).get_approved_by_name(CANONICAL_BLUEPRINT_NAME)
    assert blueprint is not None
    for concept_requirement in blueprint.concept_requirements:
        for element in concept_requirement.information_element_requirements:
            if element.element_name.value == element_name:
                return element.information_element_requirement_id.value
    raise AssertionError(f"Required InformationElementRequirement not found: {element_name}")


def test_seeder_is_idempotent(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    first = _seed(factory)
    second = _seed(factory)
    assert first == second


def test_seeded_mapping_resolves_through_h2(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        service = SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        )
        result = service.resolve_approved_source_field(
            summary.information_element_requirement_id, summary.tenant_id
        )

    assert result is not None
    assert result.semantic_mapping_id == summary.semantic_mapping_id
    assert result.source_field_id == summary.source_field_id
    assert result.source_object_id == summary.source_object_id
    assert result.source_system_id == summary.source_system_id
    assert result.information_element_requirement_id == summary.information_element_requirement_id


def test_unmapped_element_returns_none_through_h2(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        risk_event_severity_id = _element_id(session, "Risk Event Severity")
        service = SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        )
        result = service.resolve_approved_source_field(risk_event_severity_id, summary.tenant_id)

    assert result is None


def test_resolution_does_not_cross_tenant_boundaries(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        BlueprintSeeder(session).load()
        session.commit()
        element_id = _element_id(session, "Supplier Legal Name")

    tenant_a = f"h3-tenant-a-{uuid4()}"
    tenant_b = f"h3-tenant-b-{uuid4()}"
    with factory() as session:
        object_id = _seed_source_object(session, tenant_id=tenant_a)
        field = _source_field(source_object_id=object_id, field_label="LFA1-NAME1-ISOLATION")
        SourceFieldRepositoryImpl(session).create(field)
        session.commit()

        SemanticMappingRepositoryImpl(session).create(
            SemanticMapping(
                semantic_mapping_id=Identifier(uuid4()),
                source_field_id=field.source_field_id,
                information_element_requirement_id=Identifier(element_id),
                lifecycle_state=LifecycleState.ACTIVE,
                governance_status=GovernanceStatus.APPROVED,
                created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                created_on=NOW,
            )
        )
        session.commit()

    with factory() as session:
        service = SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        )
        result = service.resolve_approved_source_field(element_id, tenant_b)

    assert result is None


def test_ambiguity_prevention_for_the_seeded_mapping(migrated_engine: Engine) -> None:
    """Attempts a second Approved SemanticMapping for the seeded H3
    SourceField (to a different, also-real InformationElementRequirement),
    proving H1's source-side uniqueness rule -- unmodified by this
    authorization -- still holds for the real demonstration data, not just
    synthetic H1 test fixtures."""
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        risk_event_severity_id = _element_id(session, "Risk Event Severity")
        repository = SemanticMappingRepositoryImpl(session)
        with pytest.raises(ValidationException, match="Approved SemanticMapping already exists"):
            repository.create(
                SemanticMapping(
                    semantic_mapping_id=Identifier(uuid4()),
                    source_field_id=Identifier(summary.source_field_id),
                    information_element_requirement_id=Identifier(risk_event_severity_id),
                    lifecycle_state=LifecycleState.ACTIVE,
                    governance_status=GovernanceStatus.APPROVED,
                    created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
                    created_on=NOW,
                )
            )


def test_resolution_is_deterministic_across_repeated_calls(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        service = SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        )
        first = service.resolve_approved_source_field(
            summary.information_element_requirement_id, summary.tenant_id
        )
        second = service.resolve_approved_source_field(
            summary.information_element_requirement_id, summary.tenant_id
        )

    assert first == second
