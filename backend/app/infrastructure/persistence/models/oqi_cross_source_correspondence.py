"""ORM models for `comparison_subject_correspondences` and
`comparison_subject_correspondence_members` (CDD-040 §9-§13, §52).
`correspondence_id` is deterministically application-supplied -- see
`app.domain.oqi_cross_source.correspondence.derive_correspondence_id`. The
partial unique index enforces "exactly one ACTIVE version per
(tenant_id, comparison_subject_id)" at the database level, mirroring
`QualityRuleORM`'s own `uq_quality_rules_one_active_per_condition`
pattern exactly."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class ComparisonSubjectCorrespondenceORM(BaseEntity):
    __tablename__ = "comparison_subject_correspondences"

    __table_args__ = (
        Index("idx_comparison_subject_correspondences_tenant_id", "tenant_id"),
        Index(
            "idx_comparison_subject_correspondences_subject_id",
            "comparison_subject_id",
        ),
        Index(
            "uq_comparison_subject_correspondences_one_active",
            "tenant_id",
            "comparison_subject_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    correspondence_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    comparison_subject_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ComparisonSubjectCorrespondenceMemberORM(BaseEntity):
    __tablename__ = "comparison_subject_correspondence_members"

    __table_args__ = (
        UniqueConstraint(
            "correspondence_id",
            "source_object_id",
            "source_record_reference",
            name="uq_correspondence_members_lineage",
        ),
        Index(
            "idx_correspondence_members_correspondence_id",
            "correspondence_id",
        ),
    )

    correspondence_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "comparison_subject_correspondences.correspondence_id",
            name="fk_correspondence_members_correspondence_id",
        ),
        primary_key=True,
    )
    participant_role: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_object_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_objects.source_object_id",
            name="fk_correspondence_members_source_object_id",
        ),
        nullable=False,
    )
    source_record_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
