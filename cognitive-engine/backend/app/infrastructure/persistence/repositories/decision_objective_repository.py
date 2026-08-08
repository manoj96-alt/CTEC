# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.decision_objective import DecisionObjective
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class DecisionObjectiveRepository(BaseRepository[DecisionObjective]):
    model_type = DecisionObjective
