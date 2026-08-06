# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.institutional_action import (
    InstitutionalAction,
)
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class InstitutionalActionRepository(BaseRepository[InstitutionalAction]):
    model_type = InstitutionalAction
