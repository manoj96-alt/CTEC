# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class SourceSystemRepository(BaseRepository[SourceSystem]):
    model_type = SourceSystem
