# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.decision import Decision
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class DecisionRepository(BaseRepository[Decision]):
    model_type = Decision
