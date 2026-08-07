"""Add immutable Decision Evaluation Record persistence."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_decision_evaluation"
down_revision: str | None = "0005_knowledge_evaluation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_evaluation_records",
        sa.Column("record_identifier", sa.Uuid(), primary_key=True),
        sa.Column("knowledge_references", postgresql.JSONB(), nullable=False),
        sa.Column("decision_recommendation", sa.String(1000), nullable=False),
        sa.Column("evaluation_outcome", sa.String(24), nullable=False),
        sa.Column("decision_confidence", sa.String(16), nullable=False),
        sa.Column("structured_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("narrative_explanation", sa.String(4000), nullable=False),
        sa.Column("governing_policy_reference", sa.String(200), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("produced_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_identity_key", sa.String(64), nullable=False),
        sa.Column("business_context_reference", sa.Uuid(), nullable=True),
        sa.Column("enterprise_constraint_references", postgresql.JSONB(), nullable=False),
        sa.Column("policy_satisfied", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "idx_decision_evaluation_currentness",
        "decision_evaluation_records",
        [
            "decision_identity_key",
            "effective_from",
            "produced_timestamp",
            "record_identifier",
        ],
    )
    op.create_index(
        "idx_decision_evaluation_policy_traceability",
        "decision_evaluation_records",
        ["governing_policy_reference", "policy_version"],
    )
    op.execute(
        "CREATE FUNCTION reject_decision_evaluation_mutation() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'Decision Evaluation Records are immutable'; END; $$ "
        "LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER decision_evaluation_records_immutable BEFORE UPDATE OR DELETE "
        "ON decision_evaluation_records FOR EACH ROW "
        "EXECUTE FUNCTION reject_decision_evaluation_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER decision_evaluation_records_immutable ON decision_evaluation_records")
    op.execute("DROP FUNCTION reject_decision_evaluation_mutation")
    op.drop_index(
        "idx_decision_evaluation_policy_traceability",
        table_name="decision_evaluation_records",
    )
    op.drop_index(
        "idx_decision_evaluation_currentness",
        table_name="decision_evaluation_records",
    )
    op.drop_table("decision_evaluation_records")
