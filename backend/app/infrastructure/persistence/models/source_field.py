"""ORM model for `source_fields` (Gate H H1; CDD-019 §7, H1 Source Field /
Semantic Mapping Artifact Authorization companion). Global identity within
one `SourceObject` -- no `tenant_id` column; tenant is resolved transitively
through `source_object_id` (CDD-019 §18). `UniqueConstraint(source_object_id,
field_label)` enforces the physical-field identity CDD-019 §7 requires:
within one `SourceObject`, a `field_label` identifies at most one row."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class SourceFieldORM(BaseEntity):
    __tablename__ = "source_fields"

    __table_args__ = (
        Index("idx_source_fields_source_object_id", "source_object_id"),
        Index("idx_source_fields_lifecycle_state", "lifecycle_state"),
        Index("idx_source_fields_governance_status", "governance_status"),
        Index("idx_source_fields_created_by", "created_by"),
        Index("idx_source_fields_created_on", "created_on"),
        Index("idx_source_fields_modified_by", "modified_by"),
        Index("idx_source_fields_modified_on", "modified_on"),
        UniqueConstraint(
            "source_object_id",
            "field_label",
            name="uq_source_fields_object_label",
        ),
    )

    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_object_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("source_objects.source_object_id", name="fk_source_fields_source_object_id"),
        nullable=False,
    )
    field_label: Mapped[str] = mapped_column(String(200), nullable=False)
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
        ForeignKey("enterprise_entities.enterprise_entity_id", name="fk_source_fields_created_by"),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("enterprise_entities.enterprise_entity_id", name="fk_source_fields_modified_by"),
        nullable=True,
    )
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
