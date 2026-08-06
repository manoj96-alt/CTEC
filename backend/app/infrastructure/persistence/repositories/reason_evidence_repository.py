# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.reason_evidence import ReasonEvidence
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class ReasonEvidenceRepository(BaseRepository[ReasonEvidence]):
    model_type = ReasonEvidence
