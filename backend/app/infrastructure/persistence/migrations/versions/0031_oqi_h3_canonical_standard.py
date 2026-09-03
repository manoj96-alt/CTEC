"""Create OQI-H3 governed Canonical Standard persistence (CDD-049 §9-§11,
§28; Artifact Authorization row 6).

Three tables: `oqi_canonical_standards` (the versioned, shared-platform
envelope, anchored to a governed Information Element -- never a
`SourceField`, PO-H3-01), `oqi_canonical_standard_values` (normalized
canonical-value children), `oqi_canonical_standard_aliases` (normalized
alias children). No `tenant_id` on any of the three -- shared platform
structure, identical classification to `information_element_requirements`
and `QualityRule` itself (CDD-046 erratum). A PostgreSQL partial unique
index enforces exactly one `ACTIVE` `CanonicalStandard` version per
Information Element; per-standard-version `UNIQUE` constraints on the two
child tables make ambiguous resolution structurally impossible (CDD-049
§11-§12)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031_oqi_h3_canonical_standard"
down_revision: str | None = "0030_oqi_h2_reasonableness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_canonical_standards",
        sa.Column("canonical_standard_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "information_element_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "information_element_requirements.information_element_requirement_id",
                name="fk_oqi_canonical_standards_information_element_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "previous_version_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_canonical_standards.canonical_standard_id",
                name="fk_oqi_canonical_standards_previous_version_id",
            ),
            nullable=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_on", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_canonical_standards_status"
        ),
    )
    op.create_index(
        "idx_oqi_canonical_standards_information_element_requirement_id",
        "oqi_canonical_standards",
        ["information_element_requirement_id"],
    )
    op.create_index(
        "uq_oqi_canonical_standards_one_active",
        "oqi_canonical_standards",
        ["information_element_requirement_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "oqi_canonical_standard_values",
        sa.Column("canonical_value_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "canonical_standard_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_canonical_standards.canonical_standard_id",
                name="fk_oqi_canonical_standard_values_standard_id",
            ),
            nullable=False,
        ),
        sa.Column("canonical_representation", sa.String(4000), nullable=False),
    )
    op.create_index(
        "idx_oqi_canonical_standard_values_standard_id",
        "oqi_canonical_standard_values",
        ["canonical_standard_id"],
    )
    op.create_index(
        "uq_oqi_canonical_standard_values_representation",
        "oqi_canonical_standard_values",
        ["canonical_standard_id", "canonical_representation"],
        unique=True,
    )

    op.create_table(
        "oqi_canonical_standard_aliases",
        sa.Column("canonical_alias_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "canonical_value_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_canonical_standard_values.canonical_value_id",
                name="fk_oqi_canonical_standard_aliases_value_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "canonical_standard_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_canonical_standards.canonical_standard_id",
                name="fk_oqi_canonical_standard_aliases_standard_id",
            ),
            nullable=False,
        ),
        sa.Column("alias_representation", sa.String(4000), nullable=False),
    )
    op.create_index(
        "idx_oqi_canonical_standard_aliases_value_id",
        "oqi_canonical_standard_aliases",
        ["canonical_value_id"],
    )
    op.create_index(
        "idx_oqi_canonical_standard_aliases_standard_id",
        "oqi_canonical_standard_aliases",
        ["canonical_standard_id"],
    )
    op.create_index(
        "uq_oqi_canonical_standard_aliases_representation",
        "oqi_canonical_standard_aliases",
        ["canonical_standard_id", "alias_representation"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("oqi_canonical_standard_aliases")
    op.drop_table("oqi_canonical_standard_values")
    op.drop_table("oqi_canonical_standards")
