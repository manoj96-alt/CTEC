"""Create OQI-H3 Consistency canonical-projection provenance (CDD-049 §17,
§28; Artifact Authorization row 8).

One table, `oqi_comparison_participant_canonical_projection`: one row per
participant successfully canonicalized and consulted in a Case-B
cross-source comparison (CDD-049 §16.1) -- absent row means either no
applicable `CanonicalStandard` existed (Case A) or that participant was
missing/not part of the value-agreement computation. Raw participant value
is never duplicated here; it is reconstructable via the existing,
unmodified `quality_comparison_evaluation_evidence` link.

Revision id note (Artifact Authorization §5, mechanically pre-authorized):
the drafted candidate `0033_oqi_h3_consistency_projection` is 34 characters,
exceeding Alembic's 32-character limit -- shortened here to
`0033_oqi_h3_consistency_proj` (28 characters), mirroring the identical
precedent CDD-048's own `0030` migration required. No semantic change."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0033_oqi_h3_consistency_proj"
down_revision: str | None = "0032_oqi_h3_conformity_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_comparison_participant_canonical_projection",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "quality_comparison_evaluations.evaluation_id",
                name="fk_comparison_participant_canonical_projection_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column("participant_role", sa.String(64), primary_key=True),
        sa.Column(
            "canonical_value_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_canonical_standard_values.canonical_value_id",
                name="fk_comparison_participant_canonical_projection_value_id",
            ),
            nullable=False,
        ),
        sa.Column("standard_version", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("oqi_comparison_participant_canonical_projection")
