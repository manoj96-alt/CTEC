"""Create OQI6-I Criticality, Business Impact & Explainable Reliance
persistence (CDD-044 §45-§48; Artifact Authorization §2.1 row 9).

Six new tables: `oqi_business_processes`, `oqi_business_dependencies`,
`oqi_business_impact_evaluations`, `current_business_impacts`,
`oqi_reliance_evaluations`, `current_reliance`.

No existing table (OQI1/OQI2/OQI3/OQI4, OQI5-I1/I2, Gate S, Gate V, or any
other) is altered by this migration."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026_oqi6_reliance"
down_revision: str | None = "0025_oqi5_agent_reasoning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_business_processes",
        sa.Column("process_id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("category", sa.String(16), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_oqi_business_processes_tenant_id", "oqi_business_processes", ["tenant_id"])
    op.create_index(
        "idx_oqi_business_processes_process_id", "oqi_business_processes", ["process_id"]
    )

    op.create_table(
        "oqi_business_dependencies",
        sa.Column("dependency_id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("business_process_id", sa.Uuid(), nullable=False),
        sa.Column("business_process_version", sa.Integer(), nullable=False),
        sa.Column("ontology_element_type", sa.String(16), nullable=False),
        sa.Column("ontology_element_id", sa.Uuid(), nullable=False),
        sa.Column("criticality", sa.String(16), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_process_id", "business_process_version"],
            ["oqi_business_processes.process_id", "oqi_business_processes.version"],
            name="fk_oqi_business_dependencies_process",
        ),
    )
    op.create_index(
        "idx_oqi_business_dependencies_tenant_id", "oqi_business_dependencies", ["tenant_id"]
    )
    op.create_index(
        "idx_oqi_business_dependencies_dependency_id",
        "oqi_business_dependencies",
        ["dependency_id"],
    )
    op.create_index(
        "idx_oqi_business_dependencies_subject",
        "oqi_business_dependencies",
        ["tenant_id", "ontology_element_type", "ontology_element_id"],
    )

    op.create_table(
        "oqi_business_impact_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("business_dependency_id", sa.Uuid(), nullable=False),
        sa.Column("business_dependency_version", sa.Integer(), nullable=False),
        sa.Column("ontology_element_type", sa.String(16), nullable=False),
        sa.Column("ontology_element_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("considered_current_impact_id", sa.Uuid(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_dependency_id", "business_dependency_version"],
            ["oqi_business_dependencies.dependency_id", "oqi_business_dependencies.version"],
            name="fk_oqi_business_impact_evaluations_dependency",
        ),
        sa.ForeignKeyConstraint(
            ["considered_current_impact_id"],
            ["current_ontology_impacts.current_impact_id"],
            name="fk_oqi_business_impact_evaluations_current_impact",
        ),
    )
    op.create_index(
        "idx_oqi_business_impact_evaluations_tenant_id",
        "oqi_business_impact_evaluations",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_business_impact_evaluations_dependency",
        "oqi_business_impact_evaluations",
        ["business_dependency_id"],
    )

    op.create_table(
        "current_business_impacts",
        sa.Column("tenant_id", sa.String(200), primary_key=True),
        sa.Column("business_dependency_id", sa.Uuid(), primary_key=True),
        sa.Column("latest_evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["latest_evaluation_id"],
            ["oqi_business_impact_evaluations.evaluation_id"],
            name="fk_current_business_impacts_latest_evaluation_id",
        ),
    )
    op.create_index(
        "idx_current_business_impacts_tenant_id", "current_business_impacts", ["tenant_id"]
    )

    op.create_table(
        "oqi_reliance_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("ontology_element_type", sa.String(16), nullable=False),
        sa.Column("ontology_element_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("contributing_state_digest", sa.String(64), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_oqi_reliance_evaluations_tenant_id", "oqi_reliance_evaluations", ["tenant_id"]
    )
    op.create_index(
        "idx_oqi_reliance_evaluations_subject",
        "oqi_reliance_evaluations",
        ["tenant_id", "ontology_element_type", "ontology_element_id"],
    )

    op.create_table(
        "current_reliance",
        sa.Column("tenant_id", sa.String(200), primary_key=True),
        sa.Column("ontology_element_type", sa.String(16), primary_key=True),
        sa.Column("ontology_element_id", sa.Uuid(), primary_key=True),
        sa.Column("latest_evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["latest_evaluation_id"],
            ["oqi_reliance_evaluations.evaluation_id"],
            name="fk_current_reliance_latest_evaluation_id",
        ),
    )
    op.create_index("idx_current_reliance_tenant_id", "current_reliance", ["tenant_id"])


def downgrade() -> None:
    # Current-projection tables before their evaluation-ledger parents;
    # oqi_business_dependencies before oqi_business_processes.
    op.drop_table("current_reliance")
    op.drop_table("oqi_reliance_evaluations")
    op.drop_table("current_business_impacts")
    op.drop_table("oqi_business_impact_evaluations")
    op.drop_table("oqi_business_dependencies")
    op.drop_table("oqi_business_processes")
