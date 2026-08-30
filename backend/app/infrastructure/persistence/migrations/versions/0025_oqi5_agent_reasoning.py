"""Create OQI5-I2 Governed Real Agent Reasoning persistence (CDD-043
§18-§22; Artifact Authorization §3 row 9).

Four new tables: `oqi_remediation_agent_roles`, `oqi_remediation_agent_runs`,
`oqi_remediation_agent_assessments`, `oqi_remediation_agent_recommendations`.

No existing table (OQI1/OQI2/OQI3/OQI4, OQI5-I1, Gate S, Gate V, or any
other) is altered by this migration."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025_oqi5_agent_reasoning"
down_revision: str | None = "0024_oqi5_remediation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_remediation_agent_roles",
        sa.Column("role_id", sa.String(64), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("allowed_recommendation_types", sa.JSON(), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_oqi_remediation_agent_roles_role_version",
        "oqi_remediation_agent_roles",
        ["role_id", "version"],
        unique=True,
    )

    op.create_table(
        "oqi_remediation_agent_runs",
        sa.Column("run_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_remediation_cases.case_id",
                name="fk_oqi_remediation_agent_runs_case_id",
            ),
            nullable=False,
        ),
        sa.Column("role_id", sa.String(64), nullable=False),
        sa.Column("role_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("evidence_packet_digest", sa.String(64), nullable=False),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("result_state", sa.String(32), nullable=False),
        sa.Column("failure_reason", sa.String(200), nullable=True),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_oqi_remediation_agent_runs_tenant_id", "oqi_remediation_agent_runs", ["tenant_id"]
    )
    op.create_index(
        "idx_oqi_remediation_agent_runs_case_id", "oqi_remediation_agent_runs", ["case_id"]
    )

    op.create_table(
        "oqi_remediation_agent_assessments",
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_remediation_agent_runs.run_id",
                name="fk_oqi_remediation_agent_assessments_run_id",
            ),
            primary_key=True,
        ),
        sa.Column("role_id", sa.String(64), nullable=False),
        sa.Column("recommendation_type", sa.String(32), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
        sa.Column("supporting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("conflicting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("impact_evaluation_ids", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.String(2000), nullable=False),
    )
    op.create_index(
        "idx_oqi_remediation_agent_assessments_run_id",
        "oqi_remediation_agent_assessments",
        ["run_id"],
    )

    op.create_table(
        "oqi_remediation_agent_recommendations",
        sa.Column("recommendation_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_remediation_agent_runs.run_id",
                name="fk_oqi_remediation_agent_recommendations_run_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_remediation_cases.case_id",
                name="fk_oqi_remediation_agent_recommendations_case_id",
            ),
            nullable=False,
        ),
        sa.Column("recommendation_type", sa.String(32), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
        sa.Column("supporting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("conflicting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.String(2000), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_oqi_remediation_agent_recommendations_case_id",
        "oqi_remediation_agent_recommendations",
        ["case_id"],
    )
    op.create_index(
        "idx_oqi_remediation_agent_recommendations_run_id",
        "oqi_remediation_agent_recommendations",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_table("oqi_remediation_agent_recommendations")
    op.drop_table("oqi_remediation_agent_assessments")
    op.drop_table("oqi_remediation_agent_runs")
    op.drop_table("oqi_remediation_agent_roles")
