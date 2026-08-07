# Generated from ECOM Physical Data Model v1.3. Do not edit manually.
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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


class Assertion(BaseEntity):
    __tablename__ = "assertions"

    __table_args__ = (
        CheckConstraint(
            "(relationship_type_id IS NOT NULL AND object_entity_id IS NOT NULL AND predicate IS NULL AND object_value IS NULL) OR (relationship_type_id IS NULL AND object_entity_id IS NULL AND predicate IS NOT NULL)",
            name="chk_assertions_relational_xor_literal",
        ),
        Index("idx_assertions_assertion_name", "assertion_name"),
        Index("idx_assertions_lifecycle_state", "lifecycle_state"),
        Index("idx_assertions_effective_from", "effective_from"),
        Index("idx_assertions_effective_to", "effective_to"),
        Index("idx_assertions_governance_status", "governance_status"),
        Index("idx_assertions_created_by", "created_by"),
        Index("idx_assertions_created_on", "created_on"),
        Index("idx_assertions_modified_by", "modified_by"),
        Index("idx_assertions_modified_on", "modified_on"),
        Index("idx_assertions_version_number", "version_number"),
        Index("idx_assertions_previous_version_id", "previous_version_id"),
        Index("idx_assertions_subject_entity_id", "subject_entity_id"),
        Index("idx_assertions_predicate", "predicate"),
        Index("idx_assertions_object_value", "object_value"),
        Index("idx_assertions_object_entity_id", "object_entity_id"),
        Index("idx_assertions_source_system_id", "source_system_id"),
        Index("idx_assertions_source_object_id", "source_object_id"),
        Index("idx_assertions_asserted_on", "asserted_on"),
        Index("idx_assertions_prior_assertion_id", "prior_assertion_id"),
        Index("idx_assertions_knowledge_id", "knowledge_id"),
        Index("idx_assertions_assertion_type", "assertion_type"),
        Index("idx_assertions_relationship_type_id", "relationship_type_id"),
    )

    assertion_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    assertion_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
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
        ForeignKey("enterprise_entities.enterprise_entity_id", name="fk_assertions_created_by"),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("enterprise_entities.enterprise_entity_id", name="fk_assertions_modified_by"),
        nullable=True,
    )
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("1"))
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("assertions.assertion_id", name="fk_assertions_previous_version_id"),
        nullable=True,
    )
    subject_entity_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_assertions_subject_entity_id",
        ),
        nullable=False,
    )
    predicate: Mapped[str | None] = mapped_column(String(100), nullable=True)
    object_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    object_entity_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_assertions_object_entity_id",
        ),
        nullable=True,
    )
    source_system_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("source_systems.source_system_id", name="fk_assertions_source_system_id"),
        nullable=False,
    )
    source_object_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("source_objects.source_object_id", name="fk_assertions_source_object_id"),
        nullable=True,
    )
    asserted_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prior_assertion_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("assertions.assertion_id", name="fk_assertions_prior_assertion_id"),
        nullable=True,
    )
    knowledge_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("knowledges.knowledge_id", name="fk_assertions_knowledge_id"),
        nullable=True,
    )
    assertion_type: Mapped[str] = mapped_column(
        Enum("Evidence-backed", "Institutional", name="assertiontype_t"), nullable=False
    )
    relationship_type_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_types.relationship_type_id",
            name="fk_assertions_relationship_type_id",
        ),
        nullable=True,
    )
