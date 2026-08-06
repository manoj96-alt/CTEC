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


class InstitutionalConcept(BaseEntity):
    __tablename__ = "institutional_concepts"

    __table_args__ = (
        Index(
            "idx_institutional_concepts_institutional_concept_name",
            "institutional_concept_name",
        ),
        Index("idx_institutional_concepts_lifecycle_state", "lifecycle_state"),
        Index("idx_institutional_concepts_effective_from", "effective_from"),
        Index("idx_institutional_concepts_effective_to", "effective_to"),
        Index("idx_institutional_concepts_governance_status", "governance_status"),
        Index("idx_institutional_concepts_created_by", "created_by"),
        Index("idx_institutional_concepts_created_on", "created_on"),
        Index("idx_institutional_concepts_modified_by", "modified_by"),
        Index("idx_institutional_concepts_modified_on", "modified_on"),
        Index("idx_institutional_concepts_version_number", "version_number"),
        Index("idx_institutional_concepts_previous_version_id", "previous_version_id"),
        Index("idx_institutional_concepts_enterprise_id", "enterprise_id"),
    )

    institutional_concept_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    institutional_concept_name: Mapped[str] = mapped_column(
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
            name="fk_institutional_concepts_created_by",
        ),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_institutional_concepts_modified_by",
        ),
        nullable=True,
    )
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("1"))
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "institutional_concepts.institutional_concept_id",
            name="fk_institutional_concepts_previous_version_id",
        ),
        nullable=True,
    )
    enterprise_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("enterprises.enterprise_id", name="fk_institutional_concepts_enterprise_id"),
        nullable=False,
    )
