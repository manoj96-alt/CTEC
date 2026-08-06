# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class EntityTypeRepository(BaseRepository[EntityType]):
    model_type = EntityType
