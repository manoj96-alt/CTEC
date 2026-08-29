"""ORM models for `quality_comparison_evaluations` (the immutable
cross-source evaluation ledger), `quality_comparison_evaluation_participants`
(the immutable per-evaluation participant snapshot),
`quality_comparison_evaluation_evidence` (its participant-scoped evidence
association), and `quality_comparison_evaluation_observations` (the
immutable per-evaluation deterministic quality facts) (CDD-040 §37, §39,
§49, §52; N-Source Finding Representation Amendment §9-10). `evaluation_id`
is deterministically application-supplied -- see
`app.domain.oqi_cross_source.evaluation.derive_comparison_evaluation_id`.

`quality_comparison_evaluation_evidence` declares two chained composite
foreign keys (CDD-040 §49): one back to its own evaluation's participant
snapshot row (proving the claimed `source_field_id` matches the governed
participant), and one to `field_value_evidence` itself via the additive
`UNIQUE(field_value_evidence_id, source_field_id)` constraint authorized by
the separate `CDD-022-Artifact-Authorization-OQI2-Evidence-Composite-
Uniqueness-Amendment` companion. Together these make it structurally
impossible at the database level to associate evidence that does not
genuinely belong to the exact SourceField the governed participant
snapshot recorded for that role -- no trigger required.

`quality_comparison_evaluation_observations` extends the same chained-FK
provenance-integrity discipline (amendment §10): a composite FK to its own
evaluation's participant snapshot proves an observation can never claim a
`participant_role` that was not genuinely part of that evaluation. Its
natural key `(evaluation_id, observation_type, participant_role)` is its
entire identity -- no independent `uuid5` derivation, no lifecycle columns
(amendment §15)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class QualityComparisonEvaluationORM(BaseEntity):
    __tablename__ = "quality_comparison_evaluations"

    __table_args__ = (
        Index("idx_quality_comparison_evaluations_tenant_id", "tenant_id"),
        Index(
            "idx_quality_comparison_evaluations_subject_history",
            "quality_condition_id",
            "comparison_subject_id",
            "evaluation_mode",
            "evaluation_horizon",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    quality_condition_id: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("quality_rules.rule_id", name="fk_quality_comparison_evaluations_rule_id"),
        nullable=False,
    )
    rule_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    comparison_subject_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    comparison_subject_correspondence_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "comparison_subject_correspondences.correspondence_id",
            name="fk_quality_comparison_evaluations_correspondence_id",
        ),
        nullable=False,
    )
    evaluation_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluation_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluation_horizon: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    participant_evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    applied_current_state_authority: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    state_revision_applied: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    evaluated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QualityComparisonEvaluationParticipantORM(BaseEntity):
    __tablename__ = "quality_comparison_evaluation_participants"

    __table_args__ = (
        UniqueConstraint(
            "evaluation_id",
            "participant_role",
            "source_field_id",
            name="uq_comparison_eval_participants_role_field",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "quality_comparison_evaluations.evaluation_id",
            name="fk_comparison_eval_participants_evaluation_id",
        ),
        primary_key=True,
    )
    participant_role: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_fields.source_field_id", name="fk_comparison_eval_participants_source_field_id"
        ),
        nullable=False,
    )
    source_object_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_objects.source_object_id",
            name="fk_comparison_eval_participants_source_object_id",
        ),
        nullable=False,
    )
    source_record_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    expected: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    authoritative: Mapped[bool] = mapped_column(Boolean(), nullable=False)


class QualityComparisonEvaluationEvidenceORM(BaseEntity):
    __tablename__ = "quality_comparison_evaluation_evidence"

    __table_args__ = (
        ForeignKeyConstraint(
            ["evaluation_id", "participant_role", "source_field_id"],
            [
                "quality_comparison_evaluation_participants.evaluation_id",
                "quality_comparison_evaluation_participants.participant_role",
                "quality_comparison_evaluation_participants.source_field_id",
            ],
            name="fk_comparison_eval_evidence_participant",
        ),
        ForeignKeyConstraint(
            ["field_value_evidence_id", "source_field_id"],
            [
                "field_value_evidence.field_value_evidence_id",
                "field_value_evidence.source_field_id",
            ],
            name="fk_comparison_eval_evidence_field_value_evidence",
        ),
        Index(
            "idx_comparison_eval_evidence_field_value_evidence_id",
            "field_value_evidence_id",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    participant_role: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_field_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    field_value_evidence_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    sequence_index: Mapped[int] = mapped_column(Integer(), nullable=False)


class QualityComparisonEvaluationObservationORM(BaseEntity):
    __tablename__ = "quality_comparison_evaluation_observations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["evaluation_id", "participant_role"],
            [
                "quality_comparison_evaluation_participants.evaluation_id",
                "quality_comparison_evaluation_participants.participant_role",
            ],
            name="fk_comparison_eval_observations_participant",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "quality_comparison_evaluations.evaluation_id",
            name="fk_comparison_eval_observations_evaluation_id",
        ),
        primary_key=True,
    )
    observation_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    participant_role: Mapped[str] = mapped_column(String(64), primary_key=True)
