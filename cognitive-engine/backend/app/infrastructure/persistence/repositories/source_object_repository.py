# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class SourceObjectRepository(BaseRepository[SourceObject]):
    model_type = SourceObject
