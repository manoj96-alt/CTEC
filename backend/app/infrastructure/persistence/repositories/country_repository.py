# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.country import Country
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class CountryRepository(BaseRepository[Country]):
    model_type = Country
