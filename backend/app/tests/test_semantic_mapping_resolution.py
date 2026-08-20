"""Unit tests for `SemanticMappingResolutionApplicationService` (Gate H H2;
CDD-019 §14; H2 Semantic Mapping Resolution Artifact Authorization). Uses a
`SemanticMappingRepository`-protocol-conforming fake -- no PostgreSQL
dependency: `SemanticMappingRepositoryImpl.get_approved_by_information_element_requirement()`
is already proven against real Postgres by
`test_semantic_mapping_persistence_postgres.py`; re-proving that here would
duplicate existing coverage without adding evidence value.
"""

import inspect
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.semantic_mapping_resolution import (
    SemanticMappingResolutionApplicationService,
)
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingResolution,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _resolution() -> SemanticMappingResolution:
    return SemanticMappingResolution(
        semantic_mapping_id=uuid4(),
        source_field_id=uuid4(),
        source_object_id=uuid4(),
        source_system_id=uuid4(),
        information_element_requirement_id=uuid4(),
        created_by=uuid4(),
        created_on=NOW,
        modified_by=None,
        modified_on=None,
    )


class _FakeSemanticMappingRepository:
    def __init__(
        self,
        resolution: SemanticMappingResolution | None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.resolution = resolution
        self.error = error
        self.requested_arguments: list[tuple[UUID, str]] = []

    def create(self, semantic_mapping: SemanticMapping) -> None:
        raise NotImplementedError

    def get_by_id(self, semantic_mapping_id: UUID) -> SemanticMapping | None:
        raise NotImplementedError

    def get_approved_by_information_element_requirement(
        self, information_element_requirement_id: UUID, tenant_id: str
    ) -> SemanticMappingResolution | None:
        self.requested_arguments.append((information_element_requirement_id, tenant_id))
        if self.error is not None:
            raise self.error
        return self.resolution


def test_resolve_approved_source_field_delegates_to_the_repository() -> None:
    resolution = _resolution()
    repository = _FakeSemanticMappingRepository(resolution)
    service = SemanticMappingResolutionApplicationService(repository=repository)
    requirement_id = uuid4()

    result = service.resolve_approved_source_field(requirement_id, "tenant-a")

    assert result is resolution
    assert repository.requested_arguments == [(requirement_id, "tenant-a")]


def test_resolve_approved_source_field_returns_none_cleanly_when_not_found() -> None:
    repository = _FakeSemanticMappingRepository(None)
    service = SemanticMappingResolutionApplicationService(repository=repository)

    result = service.resolve_approved_source_field(uuid4(), "tenant-a")

    assert result is None


def test_resolve_approved_source_field_propagates_ambiguity_unchanged() -> None:
    repository = _FakeSemanticMappingRepository(
        None, error=ValidationException("Ambiguous Approved SemanticMapping resolution")
    )
    service = SemanticMappingResolutionApplicationService(repository=repository)

    with pytest.raises(ValidationException, match="Ambiguous Approved SemanticMapping"):
        service.resolve_approved_source_field(uuid4(), "tenant-a")


def test_service_exposes_no_method_beyond_resolve_approved_source_field() -> None:
    public_methods = {
        name
        for name, _ in inspect.getmembers(
            SemanticMappingResolutionApplicationService, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    }
    assert public_methods == {"resolve_approved_source_field"}
