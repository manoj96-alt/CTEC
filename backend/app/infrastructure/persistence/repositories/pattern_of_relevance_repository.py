# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.pattern_of_relevance import (
    PatternOfRelevance,
)
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class PatternOfRelevanceRepository(BaseRepository[PatternOfRelevance]):
    model_type = PatternOfRelevance
