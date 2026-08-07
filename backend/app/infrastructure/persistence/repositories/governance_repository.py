# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.governance import Governance
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class GovernanceRepository(BaseRepository[Governance]):
    model_type = Governance
