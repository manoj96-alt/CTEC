# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.occasion import Occasion
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class OccasionRepository(BaseRepository[Occasion]):
    model_type = Occasion
