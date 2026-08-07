# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class EnterpriseEntityRepository(BaseRepository[EnterpriseEntity]):
    model_type = EnterpriseEntity
