# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.decision_state import DecisionState
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class DecisionStateRepository(BaseRepository[DecisionState]):
    model_type = DecisionState
