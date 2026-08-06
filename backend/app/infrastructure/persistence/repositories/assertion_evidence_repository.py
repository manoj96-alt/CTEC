# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.assertion_evidence import AssertionEvidence
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class AssertionEvidenceRepository(BaseRepository[AssertionEvidence]):
    model_type = AssertionEvidence
