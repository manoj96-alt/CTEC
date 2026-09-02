"""Create OQI-H3 Conformity evidence-linkage persistence (CDD-049 §15, §28;
Artifact Authorization row 7).

One table, `oqi_quality_evaluation_canonical_standard`, mirroring
`oqi_quality_evaluation_reference_evidence` exactly (CDD-048 §7): pins the
exact `CanonicalValue`/version a Conformity `QualityEvaluation` consulted.
One row per evaluation (Conformity compares against exactly one qualifying
canonical value)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032_oqi_h3_conformity_evidence"
down_revision: str | None = "0031_oqi_h3_canonical_standard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_quality_evaluation_canonical_standard",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "quality_evaluations.evaluation_id",
                name="fk_oqi_qe_canonical_standard_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column(
            "canonical_value_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_canonical_standard_values.canonical_value_id",
                name="fk_oqi_qe_canonical_standard_value_id",
            ),
            primary_key=True,
        ),
        sa.Column("standard_version", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("oqi_quality_evaluation_canonical_standard")
