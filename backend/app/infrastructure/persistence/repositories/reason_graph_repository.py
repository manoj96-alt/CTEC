# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.reason_graph import ReasonGraph
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class ReasonGraphRepository(BaseRepository[ReasonGraph]):
    model_type = ReasonGraph
