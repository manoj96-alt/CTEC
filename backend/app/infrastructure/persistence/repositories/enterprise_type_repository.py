# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.enterprise_type import EnterpriseType
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class EnterpriseTypeRepository(BaseRepository[EnterpriseType]):
    model_type = EnterpriseType
