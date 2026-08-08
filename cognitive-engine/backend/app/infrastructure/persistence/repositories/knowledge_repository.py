# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.knowledge import Knowledge
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class KnowledgeRepository(BaseRepository[Knowledge]):
    model_type = Knowledge
