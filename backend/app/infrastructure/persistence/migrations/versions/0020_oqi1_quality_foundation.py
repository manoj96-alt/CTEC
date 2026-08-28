"""Create OQI1 deterministic quality foundation persistence (CDD-039 §39;
OQI1 Artifact Authorization §4). Four new tables: `quality_rules`,
`quality_evaluations`, `quality_evaluation_evidence`,
`quality_findings`. No existing table is altered -- all foreign keys into
`source_objects`, `source_fields`, and `field_value_evidence` are read-only
references."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_oqi1_quality_foundation"
down_revision: str | None = "0019_gate_v_agent_resolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quality_rules",
        sa.Column("rule_id", sa.Uuid(), primary_key=True),
        sa.Column("quality_condition_id", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("dimension", sa.String(16), nullable=False),
        sa.Column("finding_type", sa.String(32), nullable=False),
        sa.Column("validity_primitive", sa.String(32), nullable=True),
        sa.Column("information_element_requirement_id", sa.String(200), nullable=False),
        sa.Column("rule_parameters", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_on", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "quality_condition_id", "version", name="uq_quality_rules_condition_version"
        ),
    )
    op.create_index(
        "uq_quality_rules_one_active_per_condition",
        "quality_rules",
        ["quality_condition_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "quality_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("quality_condition_id", sa.String(200), nullable=False),
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey("quality_rules.rule_id", name="fk_quality_evaluations_rule_id"),
            nullable=False,
        ),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column(
            "source_object_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_objects.source_object_id",
                name="fk_quality_evaluations_source_object_id",
            ),
            nullable=False,
        ),
        sa.Column("source_record_reference", sa.String(1000), nullable=False),
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_fields.source_field_id", name="fk_quality_evaluations_source_field_id"
            ),
            nullable=False,
        ),
        sa.Column("evaluation_mode", sa.String(16), nullable=False),
        sa.Column("evaluation_origin", sa.String(32), nullable=False),
        sa.Column("evaluation_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_set_digest", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("applied_current_state_authority", sa.Boolean(), nullable=False),
        sa.Column("state_revision_applied", sa.Integer(), nullable=True),
        sa.Column("evaluated_on", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_quality_evaluations_tenant_id", "quality_evaluations", ["tenant_id"])
    op.create_index(
        "idx_quality_evaluations_source_field_id", "quality_evaluations", ["source_field_id"]
    )
    op.create_index(
        "idx_quality_evaluations_subject_history",
        "quality_evaluations",
        [
            "quality_condition_id",
            "source_object_id",
            "source_record_reference",
            "source_field_id",
            "evaluation_mode",
            "evaluation_horizon",
        ],
    )

    op.create_table(
        "quality_evaluation_evidence",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "quality_evaluations.evaluation_id",
                name="fk_quality_evaluation_evidence_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column(
            "field_value_evidence_id",
            sa.Uuid(),
            sa.ForeignKey(
                "field_value_evidence.field_value_evidence_id",
                name="fk_quality_evaluation_evidence_field_value_evidence_id",
            ),
            primary_key=True,
        ),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
    )
    op.create_index(
        "idx_quality_evaluation_evidence_field_value_evidence_id",
        "quality_evaluation_evidence",
        ["field_value_evidence_id"],
    )

    op.create_table(
        "quality_findings",
        sa.Column("finding_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("quality_condition_id", sa.String(200), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column(
            "source_object_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_objects.source_object_id", name="fk_quality_findings_source_object_id"
            ),
            nullable=False,
        ),
        sa.Column("source_record_reference", sa.String(1000), nullable=False),
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_fields.source_field_id", name="fk_quality_findings_source_field_id"
            ),
            nullable=False,
        ),
        sa.Column("finding_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
    )
    op.create_index("idx_quality_findings_tenant_id", "quality_findings", ["tenant_id"])
    op.create_index("idx_quality_findings_source_field_id", "quality_findings", ["source_field_id"])
    op.create_index("idx_quality_findings_status", "quality_findings", ["status"])


def downgrade() -> None:
    op.drop_index("idx_quality_findings_status", table_name="quality_findings")
    op.drop_index("idx_quality_findings_source_field_id", table_name="quality_findings")
    op.drop_index("idx_quality_findings_tenant_id", table_name="quality_findings")
    op.drop_table("quality_findings")

    op.drop_index(
        "idx_quality_evaluation_evidence_field_value_evidence_id",
        table_name="quality_evaluation_evidence",
    )
    op.drop_table("quality_evaluation_evidence")

    op.drop_index("idx_quality_evaluations_subject_history", table_name="quality_evaluations")
    op.drop_index("idx_quality_evaluations_source_field_id", table_name="quality_evaluations")
    op.drop_index("idx_quality_evaluations_tenant_id", table_name="quality_evaluations")
    op.drop_table("quality_evaluations")

    op.drop_index("uq_quality_rules_one_active_per_condition", table_name="quality_rules")
    op.drop_table("quality_rules")
