"""ORM model for `quality_comparison_findings` (CDD-040 §31-§33, §52).
`finding_id` is deterministically application-supplied -- see
`app.domain.oqi_cross_source.evaluation.derive_comparison_finding_id`. This
is the current-state read-model, sibling to (never modifying) OQI1's own
`quality_findings`; `quality_comparison_evaluations` is the immutable
historical ledger."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class QualityComparisonFindingORM(BaseEntity):
    __tablename__ = "quality_comparison_findings"

    __table_args__ = (
        Index("idx_quality_comparison_findings_tenant_id", "tenant_id"),
        Index("idx_quality_comparison_findings_status", "status"),
    )

    finding_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    quality_condition_id: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    comparison_subject_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_horizon: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    latest_evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "quality_comparison_evaluations.evaluation_id",
            name="fk_quality_comparison_findings_latest_evaluation_id",
        ),
        nullable=False,
    )
