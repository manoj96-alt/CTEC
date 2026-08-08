# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.evidence import Evidence
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    model_type = Evidence
