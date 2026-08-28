"""ORM model for `quality_findings` (CDD-039 §27-§30, §39; OQI1 Artifact
Authorization §4). `finding_id` is deterministically application-supplied
-- see `app.domain.oqi.evaluation.derive_quality_finding_id`. This is the
current-state read-model; `quality_evaluations` is the immutable historical
ledger (CDD-039 §29)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class QualityFindingORM(BaseEntity):
    __tablename__ = "quality_findings"

    __table_args__ = (
        Index("idx_quality_findings_tenant_id", "tenant_id"),
        Index("idx_quality_findings_source_field_id", "source_field_id"),
        Index("idx_quality_findings_status", "status"),
    )

    finding_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    quality_condition_id: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_object_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("source_objects.source_object_id", name="fk_quality_findings_source_object_id"),
        nullable=False,
    )
    source_record_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("source_fields.source_field_id", name="fk_quality_findings_source_field_id"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_horizon: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer(), nullable=False)
