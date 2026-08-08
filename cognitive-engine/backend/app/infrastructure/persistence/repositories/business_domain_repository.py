# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.business_domain import BusinessDomain
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class BusinessDomainRepository(BaseRepository[BusinessDomain]):
    model_type = BusinessDomain
