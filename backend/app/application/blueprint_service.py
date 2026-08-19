"""Internal Blueprint application service (Gate G G3; CDD-017 §3, §14; G3
Internal Blueprint Application Service Artifact Authorization). Provides the
governed internal application/use-case read boundary over the existing G2
Blueprint persistence capability -- the "future, separately-implemented
backend read *service* (not a public API)" CDD-017 §3 describes. Performs no
persistence of its own: delegates entirely to the unmodified G2
`BlueprintRepository`, matching `DecisionApplicationService`'s constructor-
injection pattern (`backend/app/application/decision_engine.py`)."""

from uuid import UUID

from app.domain.blueprint import Blueprint
from app.infrastructure.persistence.blueprint_repository import BlueprintRepository


class BlueprintApplicationService:
    def __init__(self, *, repository: BlueprintRepository) -> None:
        self.repository = repository

    def get_by_id(self, blueprint_id: UUID) -> Blueprint | None:
        return self.repository.get_by_id(blueprint_id)
