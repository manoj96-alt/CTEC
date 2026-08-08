# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.institutional_act import InstitutionalAct
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class InstitutionalActRepository(BaseRepository[InstitutionalAct]):
    model_type = InstitutionalAct
