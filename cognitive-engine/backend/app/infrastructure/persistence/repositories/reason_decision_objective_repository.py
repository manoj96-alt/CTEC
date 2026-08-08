# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.reason_decision_objective import (
    ReasonDecisionObjectives,
)
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class ReasonDecisionObjectivesRepository(BaseRepository[ReasonDecisionObjectives]):
    model_type = ReasonDecisionObjectives
