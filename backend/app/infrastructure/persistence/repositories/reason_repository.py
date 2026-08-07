# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.reason import Reason
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class ReasonRepository(BaseRepository[Reason]):
    model_type = Reason
