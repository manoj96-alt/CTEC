"""Create OQI-H1 Governed Quality Coverage persistence (CDD-047 §8-§11;
Artifact Authorization row 5).

Two new tables: `oqi_quality_coverage_policies`,
`oqi_quality_coverage_policy_dimensions`. No existing table (OQI1-OQI7,
Gate S, Gate V, or any other) is altered by this migration. No row of
either new table is created by this migration -- CDD-047 §23 is a release
blocker forbidding any default/backfilled policy."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027_h1_coverage_policy"
down_revision: str | None = "0026_oqi6_reliance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COVERAGE_DIMENSION_VALUES = (
    "COMPLETENESS",
    "VALIDITY",
    "CONSISTENCY",
    "ACCURACY",
    "UNIQUENESS",
    "TIMELINESS",
    "INTEGRITY",
    "CONFORMITY",
    "REASONABLENESS",
)
_COVERAGE_DIMENSION_CHECK_SQL = "dimension IN ({})".format(
    ", ".join(f"'{value}'" for value in _COVERAGE_DIMENSION_VALUES)
)


def upgrade() -> None:
    op.create_table(
        "oqi_quality_coverage_policies",
        sa.Column("policy_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("ontology_element_type", sa.String(16), nullable=False),
        sa.Column("ontology_element_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "previous_version_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_quality_coverage_policies.policy_id",
                name="fk_oqi_quality_coverage_policies_previous_version_id",
            ),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "policy_id", name="uq_oqi_quality_coverage_policies_tenant_pk"
        ),
        sa.CheckConstraint(
            "ontology_element_type IN ('ENTITY', 'RELATIONSHIP')",
            name="ck_oqi_quality_coverage_policies_anchor_type",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_quality_coverage_policies_status"
        ),
    )
    op.create_index(
        "idx_oqi_quality_coverage_policies_tenant_id",
        "oqi_quality_coverage_policies",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_quality_coverage_policies_anchor",
        "oqi_quality_coverage_policies",
        ["tenant_id", "ontology_element_type", "ontology_element_id"],
    )
    op.create_index(
        "uq_oqi_quality_coverage_policies_one_active",
        "oqi_quality_coverage_policies",
        ["tenant_id", "ontology_element_type", "ontology_element_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "oqi_quality_coverage_policy_dimensions",
        sa.Column(
            "policy_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_quality_coverage_policies.policy_id",
                name="fk_oqi_qcp_dimensions_policy_id",
            ),
            primary_key=True,
        ),
        sa.Column("dimension", sa.String(16), primary_key=True),
        sa.CheckConstraint(
            _COVERAGE_DIMENSION_CHECK_SQL, name="ck_oqi_qcp_dimensions_closed_vocab"
        ),
    )
    op.create_index(
        "idx_oqi_quality_coverage_policy_dimensions_policy_id",
        "oqi_quality_coverage_policy_dimensions",
        ["policy_id"],
    )


def downgrade() -> None:
    # Child table before its parent.
    op.drop_table("oqi_quality_coverage_policy_dimensions")
    op.drop_table("oqi_quality_coverage_policies")
