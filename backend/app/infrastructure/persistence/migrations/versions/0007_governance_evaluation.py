"""Add immutable Governance Evaluation Record persistence."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_governance_eval"
down_revision: str | None = "0006_decision_evaluation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "governance_evaluation_records",
        sa.Column("record_identifier", sa.Uuid(), primary_key=True),
        sa.Column("governed_record_reference", sa.Uuid(), nullable=False),
        sa.Column("governed_record_type", sa.String(48), nullable=False),
        sa.Column("governance_outcome", sa.String(24), nullable=False),
        sa.Column("governance_confidence", sa.String(16), nullable=False),
        sa.Column("structured_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("narrative_explanation", sa.String(4000), nullable=False),
        sa.Column("governing_policy_reference", sa.String(200), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("exception_authorization_reference", sa.Uuid(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("produced_timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_governance_evaluation_currentness",
        "governance_evaluation_records",
        [
            "governed_record_reference",
            "governing_policy_reference",
            "effective_from",
            "produced_timestamp",
            "record_identifier",
        ],
    )
    op.create_index(
        "idx_governance_evaluation_policy_traceability",
        "governance_evaluation_records",
        ["governing_policy_reference", "policy_version"],
    )
    op.execute(
        "CREATE FUNCTION reject_governance_evaluation_mutation() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'Governance Evaluation Records are immutable'; END; $$ "
        "LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER governance_evaluation_records_immutable BEFORE UPDATE OR DELETE "
        "ON governance_evaluation_records FOR EACH ROW "
        "EXECUTE FUNCTION reject_governance_evaluation_mutation()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER governance_evaluation_records_immutable " "ON governance_evaluation_records"
    )
    op.execute("DROP FUNCTION reject_governance_evaluation_mutation")
    op.drop_index(
        "idx_governance_evaluation_policy_traceability",
        table_name="governance_evaluation_records",
    )
    op.drop_index(
        "idx_governance_evaluation_currentness",
        table_name="governance_evaluation_records",
    )
    op.drop_table("governance_evaluation_records")
