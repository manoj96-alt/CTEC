"""Unit tests for `BlueprintApplicationService` (Gate G G3; CDD-017 §3, §14;
G3 Internal Blueprint Application Service Artifact Authorization). Uses a
`BlueprintRepository`-protocol-conforming fake -- no PostgreSQL dependency:
`BlueprintRepositoryImpl.get_by_id()` is already proven against real
Postgres by `test_blueprint_persistence_postgres.py`; re-proving that here
would duplicate existing coverage without adding evidence value.
"""

import inspect
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.application.blueprint_service import BlueprintApplicationService
from app.domain.blueprint import Blueprint
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Identifier

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _blueprint() -> Blueprint:
    return Blueprint(
        blueprint_id=Identifier(uuid4()),
        blueprint_name=CanonicalName("CTEC Semiconductor Supply Chain Blueprint"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(uuid4()),
        created_on=NOW,
    )


class _FakeBlueprintRepository:
    def __init__(self, blueprint: Blueprint | None) -> None:
        self.blueprint = blueprint
        self.requested_ids: list[UUID] = []

    def create(self, blueprint: Blueprint) -> None:
        raise NotImplementedError

    def get_by_id(self, blueprint_id: UUID) -> Blueprint | None:
        self.requested_ids.append(blueprint_id)
        return self.blueprint


def test_get_by_id_delegates_to_the_repository() -> None:
    blueprint = _blueprint()
    repository = _FakeBlueprintRepository(blueprint)
    service = BlueprintApplicationService(repository=repository)
    blueprint_id = blueprint.blueprint_id.value

    result = service.get_by_id(blueprint_id)

    assert result is blueprint
    assert repository.requested_ids == [blueprint_id]


def test_get_by_id_returns_none_cleanly_when_not_found() -> None:
    repository = _FakeBlueprintRepository(None)
    service = BlueprintApplicationService(repository=repository)

    result = service.get_by_id(uuid4())

    assert result is None


def test_service_carries_no_tenant_parameter() -> None:
    init_parameters = inspect.signature(BlueprintApplicationService.__init__).parameters
    get_by_id_parameters = inspect.signature(BlueprintApplicationService.get_by_id).parameters
    assert "tenant_id" not in init_parameters
    assert "tenant_id" not in get_by_id_parameters


def test_service_references_no_http_layer_object() -> None:
    source = (Path(__file__).parents[1] / "application" / "blueprint_service.py").read_text()
    forbidden = ("fastapi", "APIRouter", "BaseModel", "pydantic", "Depends")
    assert not any(value in source for value in forbidden)


def test_service_exposes_no_conformance_or_scoring_method() -> None:
    public_methods = {
        name
        for name, value in vars(BlueprintApplicationService).items()
        if not name.startswith("_")
    }
    assert public_methods == {"get_by_id"}
