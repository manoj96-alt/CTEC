"""Tenant-scoped, read-only queries over institutional_relationships and
enterprise_entities for the Ask CTEC capability (Gate D). Read-only:
mutates nothing. Every query is scoped by tenant_id supplied by the caller
-- application code must always source it from TrustedPrincipal.tenant_id,
never from an unrestricted request field. Relies on RFC-016's
tenant-qualified composite foreign keys (architecture/released/v1.9/) for the
structural guarantee that a tenant's institutional_relationships rows can
only ever reference that same tenant's enterprise_entities.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.ontology_copilot.traversal import GraphEdge, GraphEntity
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType


class InstitutionalRelationshipStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_enterprise_entities_by_name(self, tenant_id: str, name: str) -> list[GraphEntity]:
        """Exact, case-insensitive name match within the tenant only. Never
        fuzzy, never scored -- this is a governed lookup, not a second
        Entity Resolution engine."""
        normalized = name.strip()
        if not normalized:
            return []
        rows = self._session.execute(
            select(EnterpriseEntity, EntityType.entity_type_name)
            .join(EntityType, EntityType.entity_type_id == EnterpriseEntity.entity_type_id)
            .where(
                EnterpriseEntity.tenant_id == tenant_id,
                func.lower(EnterpriseEntity.enterprise_entity_name) == normalized.lower(),
            )
            .order_by(EnterpriseEntity.enterprise_entity_id)
        ).all()
        return [
            GraphEntity(
                entity_id=entity.enterprise_entity_id,
                entity_name=entity.enterprise_entity_name,
                entity_type_name=entity_type_name,
            )
            for entity, entity_type_name in rows
        ]

    def load_tenant_graph(
        self, tenant_id: str
    ) -> tuple[dict[UUID, GraphEntity], tuple[GraphEdge, ...]]:
        """Every enterprise entity and institutional relationship owned by
        this tenant, as a plain in-memory graph. Bounded to one tenant's
        data only; never crosses the RFC-016 tenant boundary."""
        entity_rows = self._session.execute(
            select(EnterpriseEntity, EntityType.entity_type_name)
            .join(EntityType, EntityType.entity_type_id == EnterpriseEntity.entity_type_id)
            .where(EnterpriseEntity.tenant_id == tenant_id)
        ).all()
        entities_by_id = {
            entity.enterprise_entity_id: GraphEntity(
                entity_id=entity.enterprise_entity_id,
                entity_name=entity.enterprise_entity_name,
                entity_type_name=entity_type_name,
            )
            for entity, entity_type_name in entity_rows
        }

        edge_rows = self._session.execute(
            select(
                RelationshipType.relationship_type_name,
                InstitutionalRelationship.from_entity_id,
                InstitutionalRelationship.to_entity_id,
            )
            .join(
                RelationshipType,
                RelationshipType.relationship_type_id
                == InstitutionalRelationship.relationship_type_id,
            )
            .where(InstitutionalRelationship.tenant_id == tenant_id)
        ).all()
        edges = tuple(
            GraphEdge(relationship_name=name, from_entity_id=from_id, to_entity_id=to_id)
            for name, from_id, to_id in edge_rows
        )
        return entities_by_id, edges
