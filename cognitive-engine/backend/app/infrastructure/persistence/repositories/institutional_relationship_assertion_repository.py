# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.institutional_relationship_assertion import (
    InstitutionalRelationshipAssertions,
)
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class InstitutionalRelationshipAssertionsRepository(
    BaseRepository[InstitutionalRelationshipAssertions]
):
    model_type = InstitutionalRelationshipAssertions
