"""Create OQI-H2 Accuracy evidence-linkage persistence (CDD-048 §7;
Artifact Authorization row 9).

One new table: `oqi_quality_evaluation_reference_evidence`, pinning every
qualifying `ReferenceEvidenceAssertion` version an Accuracy `QualityEvaluation`
consulted. No existing table is altered -- `QualityDimension.ACCURACY` and
`QualityFindingType.REFERENCE_VALUE_UNSUPPORTED` require no schema change:
`quality_rules.dimension` and `quality_findings.finding_type` are plain
`String` columns with no CHECK constraint (verified directly against the
`0020_oqi1_quality_foundation` migration), so their governed-vocabulary
enforcement is Python-only, exactly as it already is for every existing
member."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029_oqi_h2_accuracy_dimension"
down_revision: str | None = "0028_oqi_h2_reference_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_quality_evaluation_reference_evidence",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "quality_evaluations.evaluation_id",
                name="fk_oqi_qe_reference_evidence_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column(
            "assertion_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_reference_evidence_assertions.assertion_id",
                name="fk_oqi_qe_reference_evidence_assertion_id",
            ),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("oqi_quality_evaluation_reference_evidence")
