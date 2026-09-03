"""Create OQI-H4 governed relationship-cardinality policy persistence
(CDD-050 §7, §23; Artifact Authorization row 11).

One table: `oqi_integrity_relationship_cardinalities` -- the versioned,
shared-platform cardinality extension anchored exclusively to the existing,
unmodified `relationship_requirements.relationship_requirement_id`. No
`tenant_id` -- shared platform structure, identical classification to
`relationship_requirements` itself (CDD-017 §9, CDD-050 §7). A PostgreSQL
partial unique index enforces exactly one `ACTIVE` cardinality definition per
`RelationshipRequirement`."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034_oqi_h4_integrity_policy"
down_revision: str | None = "0033_oqi_h3_consistency_proj"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_integrity_relationship_cardinalities",
        sa.Column("integrity_relationship_cardinality_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "relationship_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_requirements.relationship_requirement_id",
                name="fk_oqi_integrity_cardinalities_relationship_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column("min_cardinality", sa.Integer(), nullable=False),
        sa.Column("max_cardinality", sa.Integer(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "previous_version_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_integrity_relationship_cardinalities.integrity_relationship_cardinality_id",
                name="fk_oqi_integrity_cardinalities_previous_version_id",
            ),
            nullable=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_on", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_integrity_cardinalities_status"
        ),
        sa.CheckConstraint(
            "min_cardinality >= 0", name="ck_oqi_integrity_cardinalities_min_nonneg"
        ),
        sa.CheckConstraint(
            "max_cardinality IS NULL OR max_cardinality >= min_cardinality",
            name="ck_oqi_integrity_cardinalities_max_ge_min",
        ),
    )
    op.create_index(
        "idx_oqi_integrity_cardinalities_relationship_requirement_id",
        "oqi_integrity_relationship_cardinalities",
        ["relationship_requirement_id"],
    )
    op.create_index(
        "uq_oqi_integrity_cardinalities_one_active",
        "oqi_integrity_relationship_cardinalities",
        ["relationship_requirement_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_table("oqi_integrity_relationship_cardinalities")
