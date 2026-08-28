"""ORM models for `quality_evaluations` (the immutable evaluation ledger)
and `quality_evaluation_evidence` (its evidence-reference association)
(CDD-039 §19-§21, §39; OQI1 Artifact Authorization §4). `evaluation_id` is
deterministically application-supplied -- see
`app.domain.oqi.evaluation.derive_evaluation_id`. Foreign keys to
`source_objects`/`source_fields`/`field_value_evidence` are read-only
references; this migration never alters those tables (CDD-039 §7, §29,
§36)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class QualityEvaluationORM(BaseEntity):
    __tablename__ = "quality_evaluations"

    __table_args__ = (
        Index("idx_quality_evaluations_tenant_id", "tenant_id"),
        Index("idx_quality_evaluations_source_field_id", "source_field_id"),
        Index(
            "idx_quality_evaluations_subject_history",
            "quality_condition_id",
            "source_object_id",
            "source_record_reference",
            "source_field_id",
            "evaluation_mode",
            "evaluation_horizon",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    quality_condition_id: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("quality_rules.rule_id", name="fk_quality_evaluations_rule_id"),
        nullable=False,
    )
    rule_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_object_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_objects.source_object_id", name="fk_quality_evaluations_source_object_id"
        ),
        nullable=False,
    )
    source_record_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("source_fields.source_field_id", name="fk_quality_evaluations_source_field_id"),
        nullable=False,
    )
    evaluation_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluation_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluation_horizon: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_set_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    applied_current_state_authority: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    state_revision_applied: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    evaluated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QualityEvaluationEvidenceORM(BaseEntity):
    __tablename__ = "quality_evaluation_evidence"

    __table_args__ = (
        Index("idx_quality_evaluation_evidence_field_value_evidence_id", "field_value_evidence_id"),
    )

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "quality_evaluations.evaluation_id",
            name="fk_quality_evaluation_evidence_evaluation_id",
        ),
        primary_key=True,
    )
    field_value_evidence_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "field_value_evidence.field_value_evidence_id",
            name="fk_quality_evaluation_evidence_field_value_evidence_id",
        ),
        primary_key=True,
    )
    sequence_index: Mapped[int] = mapped_column(Integer(), nullable=False)
