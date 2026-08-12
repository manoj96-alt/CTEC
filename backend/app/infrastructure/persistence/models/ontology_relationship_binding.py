"""ORM mapping for ontology_relationship_bindings. Domain/range binding between
two governed entity types via a governed relationship type. Introduced for the
Ontology Studio MVP; not part of the generated ECOM Physical Data Model v1.3."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class OntologyRelationshipBinding(BaseEntity):
    __tablename__ = "ontology_relationship_bindings"

    __table_args__ = (Index("idx_ontology_bindings_relationship_type_id", "relationship_type_id"),)

    binding_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    relationship_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_types.relationship_type_id",
            name="fk_ontology_bindings_relationship_type_id",
        ),
        nullable=False,
    )
    source_entity_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "entity_types.entity_type_id",
            name="fk_ontology_bindings_source_entity_type_id",
        ),
        nullable=False,
    )
    target_entity_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "entity_types.entity_type_id",
            name="fk_ontology_bindings_target_entity_type_id",
        ),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
