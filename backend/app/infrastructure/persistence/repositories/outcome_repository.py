# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.outcome import Outcome
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class OutcomeRepository(BaseRepository[Outcome]):
    model_type = Outcome
