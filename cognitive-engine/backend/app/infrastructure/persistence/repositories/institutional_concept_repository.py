# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.institutional_concept import (
    InstitutionalConcept,
)
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class InstitutionalConceptRepository(BaseRepository[InstitutionalConcept]):
    model_type = InstitutionalConcept
