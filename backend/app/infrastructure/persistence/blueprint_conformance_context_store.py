"""Tenant-scoped, read-only queries over `enterprise_entities` and
`institutional_relationships` for Blueprint structural conformance
evaluation (Gate G G4; CDD-018 §7-§9; G4 Blueprint Conformance Artifact
Authorization). Read-only: mutates nothing. Every query is scoped by
`tenant_id` supplied by the caller. Matches by governed identity
(`entity_type_id`/`relationship_type_id`) exclusively -- never by name --
distinguishing this store from `institutional_relationship_store.py`
(Ask CTEC's own name-matching store, a different capability's domain
vocabulary, not reused here per the G4 artifact-authorization companion's
discovery findings).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)


class BlueprintConformanceContextStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def entity_type_ids_present(self, tenant_id: str) -> frozenset[UUID]:
        """Distinct `entity_type_id` values present in this tenant's
        `enterprise_entities`."""
        rows = self._session.scalars(
            select(EnterpriseEntity.entity_type_id)
            .where(EnterpriseEntity.tenant_id == tenant_id)
            .distinct()
        ).all()
        return frozenset(rows)

    def relationship_triples_present(self, tenant_id: str) -> frozenset[tuple[UUID, UUID, UUID]]:
        """Distinct `(relationship_type_id, from_entity_type_id,
        to_entity_type_id)` triples present in this tenant's
        `institutional_relationships`."""
        from_entity = aliased(EnterpriseEntity)
        to_entity = aliased(EnterpriseEntity)
        rows = self._session.execute(
            select(
                InstitutionalRelationship.relationship_type_id,
                from_entity.entity_type_id,
                to_entity.entity_type_id,
            )
            .join(
                from_entity,
                from_entity.enterprise_entity_id == InstitutionalRelationship.from_entity_id,
            )
            .join(
                to_entity,
                to_entity.enterprise_entity_id == InstitutionalRelationship.to_entity_id,
            )
            .where(InstitutionalRelationship.tenant_id == tenant_id)
            .distinct()
        ).all()
        return frozenset(
            (relationship_type_id, from_type_id, to_type_id)
            for relationship_type_id, from_type_id, to_type_id in rows
        )
