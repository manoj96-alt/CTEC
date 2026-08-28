"""Create OQI2 cross-source Multi-Source Quality Intelligence persistence
(CDD-040 §49, §52-§53; CDD-040 Artifact Authorization §7; CDD-022
Artifact Authorization OQI2 Evidence Composite Uniqueness Amendment).

Six new tables: `comparison_subject_correspondences`,
`comparison_subject_correspondence_members`, `quality_comparison_evaluations`,
`quality_comparison_evaluation_participants`,
`quality_comparison_evaluation_evidence`, `quality_comparison_findings`.

One additive, non-destructive constraint on the existing CDD-022-governed
`field_value_evidence` table: `UNIQUE(field_value_evidence_id,
source_field_id)` -- no column added, no data mutated, no backfill;
authorized by the separate CDD-022 companion amendment, not by CDD-040
alone. No other existing table is altered."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_oqi2_cross_source"
down_revision: str | None = "0020_oqi1_quality_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # CDD-022 Artifact Authorization OQI2 Evidence Composite Uniqueness
    # Amendment §2: purely additive, no data mutation.
    op.create_unique_constraint(
        "uq_field_value_evidence_id_source_field",
        "field_value_evidence",
        ["field_value_evidence_id", "source_field_id"],
    )

    op.create_table(
        "comparison_subject_correspondences",
        sa.Column("correspondence_id", sa.Uuid(), primary_key=True),
        sa.Column("comparison_subject_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_on", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_comparison_subject_correspondences_tenant_id",
        "comparison_subject_correspondences",
        ["tenant_id"],
    )
    op.create_index(
        "idx_comparison_subject_correspondences_subject_id",
        "comparison_subject_correspondences",
        ["comparison_subject_id"],
    )
    op.create_index(
        "uq_comparison_subject_correspondences_one_active",
        "comparison_subject_correspondences",
        ["tenant_id", "comparison_subject_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "comparison_subject_correspondence_members",
        sa.Column(
            "correspondence_id",
            sa.Uuid(),
            sa.ForeignKey(
                "comparison_subject_correspondences.correspondence_id",
                name="fk_correspondence_members_correspondence_id",
            ),
            primary_key=True,
        ),
        sa.Column("participant_role", sa.String(64), primary_key=True),
        sa.Column(
            "source_object_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_objects.source_object_id",
                name="fk_correspondence_members_source_object_id",
            ),
            nullable=False,
        ),
        sa.Column("source_record_reference", sa.String(1000), nullable=False),
        sa.UniqueConstraint(
            "correspondence_id",
            "source_object_id",
            "source_record_reference",
            name="uq_correspondence_members_lineage",
        ),
    )
    op.create_index(
        "idx_correspondence_members_correspondence_id",
        "comparison_subject_correspondence_members",
        ["correspondence_id"],
    )

    op.create_table(
        "quality_comparison_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("quality_condition_id", sa.String(200), nullable=False),
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey(
                "quality_rules.rule_id", name="fk_quality_comparison_evaluations_rule_id"
            ),
            nullable=False,
        ),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("comparison_subject_id", sa.Uuid(), nullable=False),
        sa.Column(
            "comparison_subject_correspondence_id",
            sa.Uuid(),
            sa.ForeignKey(
                "comparison_subject_correspondences.correspondence_id",
                name="fk_quality_comparison_evaluations_correspondence_id",
            ),
            nullable=False,
        ),
        sa.Column("evaluation_mode", sa.String(16), nullable=False),
        sa.Column("evaluation_origin", sa.String(32), nullable=False),
        sa.Column("evaluation_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("participant_evidence_digest", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("applied_current_state_authority", sa.Boolean(), nullable=False),
        sa.Column("state_revision_applied", sa.Integer(), nullable=True),
        sa.Column("evaluated_on", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_quality_comparison_evaluations_tenant_id",
        "quality_comparison_evaluations",
        ["tenant_id"],
    )
    op.create_index(
        "idx_quality_comparison_evaluations_subject_history",
        "quality_comparison_evaluations",
        ["quality_condition_id", "comparison_subject_id", "evaluation_mode", "evaluation_horizon"],
    )

    op.create_table(
        "quality_comparison_evaluation_participants",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "quality_comparison_evaluations.evaluation_id",
                name="fk_comparison_eval_participants_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column("participant_role", sa.String(64), primary_key=True),
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_fields.source_field_id",
                name="fk_comparison_eval_participants_source_field_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "source_object_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_objects.source_object_id",
                name="fk_comparison_eval_participants_source_object_id",
            ),
            nullable=False,
        ),
        sa.Column("source_record_reference", sa.String(1000), nullable=False),
        sa.Column("expected", sa.Boolean(), nullable=False),
        sa.Column("authoritative", sa.Boolean(), nullable=False),
        sa.UniqueConstraint(
            "evaluation_id",
            "participant_role",
            "source_field_id",
            name="uq_comparison_eval_participants_role_field",
        ),
    )

    op.create_table(
        "quality_comparison_evaluation_evidence",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("participant_role", sa.String(64), primary_key=True),
        sa.Column("source_field_id", sa.Uuid(), nullable=False),
        sa.Column("field_value_evidence_id", sa.Uuid(), primary_key=True),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id", "participant_role", "source_field_id"],
            [
                "quality_comparison_evaluation_participants.evaluation_id",
                "quality_comparison_evaluation_participants.participant_role",
                "quality_comparison_evaluation_participants.source_field_id",
            ],
            name="fk_comparison_eval_evidence_participant",
        ),
        sa.ForeignKeyConstraint(
            ["field_value_evidence_id", "source_field_id"],
            [
                "field_value_evidence.field_value_evidence_id",
                "field_value_evidence.source_field_id",
            ],
            name="fk_comparison_eval_evidence_field_value_evidence",
        ),
    )
    op.create_index(
        "idx_comparison_eval_evidence_field_value_evidence_id",
        "quality_comparison_evaluation_evidence",
        ["field_value_evidence_id"],
    )

    op.create_table(
        "quality_comparison_findings",
        sa.Column("finding_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("quality_condition_id", sa.String(200), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("comparison_subject_id", sa.Uuid(), nullable=False),
        sa.Column("finding_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
        sa.Column(
            "latest_evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "quality_comparison_evaluations.evaluation_id",
                name="fk_quality_comparison_findings_latest_evaluation_id",
            ),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_quality_comparison_findings_tenant_id", "quality_comparison_findings", ["tenant_id"]
    )
    op.create_index(
        "idx_quality_comparison_findings_status", "quality_comparison_findings", ["status"]
    )


def downgrade() -> None:
    op.drop_index(
        "idx_quality_comparison_findings_status", table_name="quality_comparison_findings"
    )
    op.drop_index(
        "idx_quality_comparison_findings_tenant_id", table_name="quality_comparison_findings"
    )
    op.drop_table("quality_comparison_findings")

    op.drop_index(
        "idx_comparison_eval_evidence_field_value_evidence_id",
        table_name="quality_comparison_evaluation_evidence",
    )
    op.drop_table("quality_comparison_evaluation_evidence")

    op.drop_table("quality_comparison_evaluation_participants")

    op.drop_index(
        "idx_quality_comparison_evaluations_subject_history",
        table_name="quality_comparison_evaluations",
    )
    op.drop_index(
        "idx_quality_comparison_evaluations_tenant_id", table_name="quality_comparison_evaluations"
    )
    op.drop_table("quality_comparison_evaluations")

    op.drop_index(
        "idx_correspondence_members_correspondence_id",
        table_name="comparison_subject_correspondence_members",
    )
    op.drop_table("comparison_subject_correspondence_members")

    op.drop_index(
        "uq_comparison_subject_correspondences_one_active",
        table_name="comparison_subject_correspondences",
    )
    op.drop_index(
        "idx_comparison_subject_correspondences_subject_id",
        table_name="comparison_subject_correspondences",
    )
    op.drop_index(
        "idx_comparison_subject_correspondences_tenant_id",
        table_name="comparison_subject_correspondences",
    )
    op.drop_table("comparison_subject_correspondences")

    op.drop_constraint(
        "uq_field_value_evidence_id_source_field", "field_value_evidence", type_="unique"
    )
