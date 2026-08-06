# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.enterprise import Enterprise
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class EnterpriseRepository(BaseRepository[Enterprise]):
    model_type = Enterprise
