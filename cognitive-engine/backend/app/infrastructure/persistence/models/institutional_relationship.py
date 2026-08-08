# Generated from ECOM Physical Data Model v1.3. Do not edit manually.
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class InstitutionalRelationship(BaseEntity):
    __tablename__ = "institutional_relationships"

    __table_args__ = (
        Index(
            "idx_institutional_relationships_institutional_relationship_name",
            "institutional_relationship_name",
        ),
        Index("idx_institutional_relationships_lifecycle_state", "lifecycle_state"),
        Index("idx_institutional_relationships_effective_from", "effective_from"),
        Index("idx_institutional_relationships_effective_to", "effective_to"),
        Index("idx_institutional_relationships_governance_status", "governance_status"),
        Index("idx_institutional_relationships_created_by", "created_by"),
        Index("idx_institutional_relationships_created_on", "created_on"),
        Index("idx_institutional_relationships_modified_by", "modified_by"),
        Index("idx_institutional_relationships_modified_on", "modified_on"),
        Index("idx_institutional_relationships_version_number", "version_number"),
        Index("idx_institutional_relationships_previous_version_id", "previous_version_id"),
        Index(
            "idx_institutional_relationships_relationship_type_id",
            "relationship_type_id",
        ),
        Index("idx_institutional_relationships_from_entity_id", "from_entity_id"),
        Index("idx_institutional_relationships_to_entity_id", "to_entity_id"),
        Index("idx_institutional_relationships_superseded_by_id", "superseded_by_id"),
    )

    institutional_relationship_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    institutional_relationship_name: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True
    )
    lifecycle_state: Mapped[str] = mapped_column(
        Enum("Draft", "Active", "Suspended", "Archived", name="lifecyclestate_t"),
        nullable=False,
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    governance_status: Mapped[str] = mapped_column(
        Enum("Proposed", "Approved", "Retired", "Archived", name="governancestatus_t"),
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_institutional_relationships_created_by",
        ),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_institutional_relationships_modified_by",
        ),
        nullable=True,
    )
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("1"))
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "institutional_relationships.institutional_relationship_id",
            name="fk_institutional_relationships_previous_version_id",
        ),
        nullable=True,
    )
    relationship_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_types.relationship_type_id",
            name="fk_institutional_relationships_relationship_type_id",
        ),
        nullable=False,
    )
    from_entity_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_institutional_relationships_from_entity_id",
        ),
        nullable=False,
    )
    to_entity_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_institutional_relationships_to_entity_id",
        ),
        nullable=False,
    )
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "institutional_relationships.institutional_relationship_id",
            name="fk_institutional_relationships_superseded_by_id",
        ),
        nullable=True,
    )
