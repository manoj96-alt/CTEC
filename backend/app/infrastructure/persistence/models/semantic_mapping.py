"""ORM model for `semantic_mappings` (Gate H H1; CDD-019 §8, §10, §11, H1
Source Field / Semantic Mapping Artifact Authorization companion). Direct
correspondence `source_field_id` <-> `information_element_requirement_id` --
no intermediate identity, no `tenant_id` column (tenant is resolved
transitively through `source_field_id`, CDD-019 §18).

`uq_semantic_mappings_approved_source_field` is a PostgreSQL partial unique
index (`WHERE governance_status = 'Approved'`) -- the durable,
database-enforced half of CDD-019 §11's source-side uniqueness rule: at most
one Approved row may reference a given `source_field_id`. The target-side
rule (`information_element_requirement_id` + tenant) is intentionally NOT
expressed here -- tenant is join-derived, not a stored column, so a bare
database constraint would be incorrect, not merely insufficient (CDD-019
§11); it is enforced in `SemanticMappingRepositoryImpl.create()` instead."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class SemanticMappingORM(BaseEntity):
    __tablename__ = "semantic_mappings"

    __table_args__ = (
        Index("idx_semantic_mappings_source_field_id", "source_field_id"),
        Index(
            "idx_semantic_mappings_information_element_requirement_id",
            "information_element_requirement_id",
        ),
        Index("idx_semantic_mappings_lifecycle_state", "lifecycle_state"),
        Index("idx_semantic_mappings_governance_status", "governance_status"),
        Index("idx_semantic_mappings_created_by", "created_by"),
        Index("idx_semantic_mappings_created_on", "created_on"),
        Index("idx_semantic_mappings_modified_by", "modified_by"),
        Index("idx_semantic_mappings_modified_on", "modified_on"),
        Index(
            "uq_semantic_mappings_approved_source_field",
            "source_field_id",
            unique=True,
            postgresql_where=text("governance_status = 'Approved'"),
        ),
    )

    semantic_mapping_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("source_fields.source_field_id", name="fk_semantic_mappings_source_field_id"),
        nullable=False,
    )
    information_element_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "information_element_requirements.information_element_requirement_id",
            name="fk_semantic_mappings_information_element_requirement_id",
        ),
        nullable=False,
    )
    lifecycle_state: Mapped[str] = mapped_column(
        Enum("Draft", "Active", "Suspended", "Archived", name="lifecyclestate_t"),
        nullable=False,
    )
    governance_status: Mapped[str] = mapped_column(
        Enum("Proposed", "Approved", "Retired", "Archived", name="governancestatus_t"),
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id", name="fk_semantic_mappings_created_by"
        ),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id", name="fk_semantic_mappings_modified_by"
        ),
        nullable=True,
    )
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
