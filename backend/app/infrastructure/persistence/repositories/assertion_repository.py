# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class AssertionRepository(BaseRepository[Assertion]):
    model_type = Assertion
