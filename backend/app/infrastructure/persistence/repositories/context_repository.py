# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.context import Context
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class ContextRepository(BaseRepository[Context]):
    model_type = Context
