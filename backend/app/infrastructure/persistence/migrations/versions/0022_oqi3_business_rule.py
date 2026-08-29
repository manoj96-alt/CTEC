"""Create OQI3 Business-Rule Quality Intelligence persistence (CDD-041 §24;
Artifact Authorization §5-§8).

Six new tables: `business_rules`, `business_rule_input_bindings`,
`business_rule_evaluations`, `business_rule_evaluation_inputs`,
`business_rule_evaluation_observations`, `business_rule_findings`.

No existing table (OQI1, OQI2, `source_fields`, `field_value_evidence`, or
any other) is altered by this migration -- `BusinessRule` is a first-class
sibling of `QualityRule`, never sharing a table (CDD-041 §3).

This is OQI3-I1 (foundation) scope: the migration creates the complete
6-table schema in one step (no ORM model exists yet for the Evaluation/
Observation/Finding tables -- those are created via raw DDL here and gain
ORM mapping in OQI3-I2/I3, mirroring how a migration's `op.create_table`
call never requires a pre-existing ORM class). No runtime code in this
phase reads or writes the Evaluation/Observation/Finding tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_oqi3_business_rule"
down_revision: str | None = "0021_oqi2_cross_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_rules",
        sa.Column("rule_id", sa.Uuid(), primary_key=True),
        sa.Column("business_condition_id", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("rule_family", sa.String(32), nullable=False),
        sa.Column("applicability", sa.JSON(), nullable=True),
        sa.Column("predicate", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_on", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "business_condition_id", "version", name="uq_business_rules_condition_version"
        ),
    )
    op.create_index("idx_business_rules_tenant_id", "business_rules", ["tenant_id"])
    op.create_index(
        "uq_business_rules_one_active_per_condition",
        "business_rules",
        ["tenant_id", "business_condition_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "business_rule_input_bindings",
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey("business_rules.rule_id", name="fk_business_rule_input_bindings_rule_id"),
            primary_key=True,
        ),
        sa.Column("input_role", sa.String(64), primary_key=True),
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_fields.source_field_id",
                name="fk_business_rule_input_bindings_source_field_id",
            ),
            nullable=False,
        ),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("expected_type", sa.String(16), nullable=False),
    )

    op.create_table(
        "business_rule_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("business_condition_id", sa.String(200), nullable=False),
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey("business_rules.rule_id", name="fk_business_rule_evaluations_rule_id"),
            nullable=False,
        ),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("source_record_reference", sa.String(1000), nullable=False),
        sa.Column("evaluation_mode", sa.String(16), nullable=False),
        sa.Column("evaluation_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_evidence_digest", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_business_rule_evaluations_tenant_id", "business_rule_evaluations", ["tenant_id"]
    )
    op.create_index(
        "idx_business_rule_evaluations_subject_history",
        "business_rule_evaluations",
        ["business_condition_id", "subject_type", "source_record_reference", "evaluation_mode"],
    )

    op.create_table(
        "business_rule_evaluation_inputs",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "business_rule_evaluations.evaluation_id",
                name="fk_business_rule_evaluation_inputs_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column("input_role", sa.String(64), primary_key=True),
        sa.Column(
            "field_value_evidence_id",
            sa.Uuid(),
            sa.ForeignKey(
                "field_value_evidence.field_value_evidence_id",
                name="fk_business_rule_evaluation_inputs_evidence_id",
            ),
            nullable=True,
        ),
    )

    op.create_table(
        "business_rule_evaluation_observations",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "business_rule_evaluations.evaluation_id",
                name="fk_business_rule_evaluation_observations_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column("clause_id", sa.String(64), primary_key=True),
        sa.Column("observation_type", sa.String(64), primary_key=True),
        sa.Column("input_role", sa.String(64), primary_key=True),
        sa.ForeignKeyConstraint(
            ["evaluation_id", "input_role"],
            [
                "business_rule_evaluation_inputs.evaluation_id",
                "business_rule_evaluation_inputs.input_role",
            ],
            name="fk_business_rule_evaluation_observations_input",
        ),
    )

    op.create_table(
        "business_rule_findings",
        sa.Column("finding_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("business_condition_id", sa.String(200), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_identity", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("resolution_basis", sa.String(16), nullable=True),
        sa.Column(
            "latest_evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "business_rule_evaluations.evaluation_id",
                name="fk_business_rule_findings_latest_evaluation_id",
            ),
            nullable=False,
        ),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "business_condition_id",
            "subject_type",
            "subject_identity",
            name="uq_business_rule_findings_subject",
        ),
        sa.CheckConstraint(
            "(status = 'OPEN' AND resolution_basis IS NULL) OR "
            "(status = 'RESOLVED' AND resolution_basis IS NOT NULL)",
            name="ck_business_rule_findings_resolution_basis",
        ),
    )
    op.create_index("idx_business_rule_findings_tenant_id", "business_rule_findings", ["tenant_id"])
    op.create_index("idx_business_rule_findings_status", "business_rule_findings", ["status"])


def downgrade() -> None:
    op.drop_table("business_rule_findings")
    op.drop_table("business_rule_evaluation_observations")
    op.drop_table("business_rule_evaluation_inputs")
    op.drop_table("business_rule_evaluations")
    op.drop_table("business_rule_input_bindings")
    op.drop_table("business_rules")
