"""Widen OQI4 `finding_family` columns to accommodate `FindingStorageFamily
.INTEGRITY` (CDD-050 §20, §23; Artifact Authorization row 14).

`ontology_impact_evaluations.finding_family` and
`current_ontology_impacts.finding_family` are `String(8)` -- sized for
`"OQI1"`/`"OQI2"`/`"OQI3"` (4 chars) but not `"INTEGRITY"` (9 chars). Widens
both to `String(16)` -- storage width only. Zero semantic change to
`FindingFamily`'s membership (CDD-042 §10, unmodified, unmodified by this
migration) and zero change to any existing OQI1/2/3 value."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0037_oqi_h4_impact_width"
down_revision: str | None = "0036_oqi_h4_integrity_reference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "ontology_impact_evaluations",
        "finding_family",
        existing_type=sa.String(8),
        type_=sa.String(16),
        existing_nullable=False,
    )
    op.alter_column(
        "current_ontology_impacts",
        "finding_family",
        existing_type=sa.String(8),
        type_=sa.String(16),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "current_ontology_impacts",
        "finding_family",
        existing_type=sa.String(16),
        type_=sa.String(8),
        existing_nullable=False,
    )
    op.alter_column(
        "ontology_impact_evaluations",
        "finding_family",
        existing_type=sa.String(16),
        type_=sa.String(8),
        existing_nullable=False,
    )
