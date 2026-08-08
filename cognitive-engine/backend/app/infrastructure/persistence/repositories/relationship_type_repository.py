# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class RelationshipTypeRepository(BaseRepository[RelationshipType]):
    model_type = RelationshipType
