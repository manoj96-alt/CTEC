# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class InstitutionalRelationshipRepository(BaseRepository[InstitutionalRelationship]):
    model_type = InstitutionalRelationship
