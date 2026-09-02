"""Add OQI-H2 Reasonableness dimension/purpose tagging to `business_rules`
and `business_rule_findings` (CDD-048 §14, §20; Artifact Authorization row
9).

Two additive columns: `business_rules.dimension` (governed purpose --
LEGACY_UNCLASSIFIED_BUSINESS_RULE by default for every existing row,
REASONABLENESS, or ACCURACY_REFERENCE_DERIVATION) and
`business_rule_findings.violation_type` (the finding-type-equivalent for a
`dimension=REASONABLENESS` violation, NULL for every legacy/ACCURACY_
REFERENCE_DERIVATION-purpose Finding). No existing row's meaning changes:
`server_default` covers every pre-H2 `business_rules` row without any
`UPDATE` statement, and `violation_type` is nullable, unset for every
existing Finding (CDD-048 §13: never fabricate historical/cross-purpose
semantic precision that does not exist)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030_oqi_h2_reasonableness"
down_revision: str | None = "0029_oqi_h2_accuracy_dimension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "business_rules",
        sa.Column(
            "dimension",
            sa.String(48),
            nullable=False,
            server_default="LEGACY_UNCLASSIFIED_BUSINESS_RULE",
        ),
    )
    op.create_check_constraint(
        "ck_business_rules_dimension",
        "business_rules",
        "dimension IN ('LEGACY_UNCLASSIFIED_BUSINESS_RULE', 'REASONABLENESS', "
        "'ACCURACY_REFERENCE_DERIVATION')",
    )
    op.add_column(
        "business_rule_findings",
        sa.Column("violation_type", sa.String(48), nullable=True),
    )
    op.create_check_constraint(
        "ck_business_rule_findings_violation_type",
        "business_rule_findings",
        "status = 'OPEN' OR violation_type IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_business_rule_findings_violation_type", "business_rule_findings", type_="check"
    )
    op.drop_column("business_rule_findings", "violation_type")
    op.drop_constraint("ck_business_rules_dimension", "business_rules", type_="check")
    op.drop_column("business_rules", "dimension")
