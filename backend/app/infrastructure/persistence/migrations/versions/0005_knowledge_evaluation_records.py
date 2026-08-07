"""Add immutable Knowledge Evaluation Record persistence."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_knowledge_evaluation_records"
down_revision: str | None = "0004_assertion_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_evaluation_records",
        sa.Column("record_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "assertion_record_id",
            sa.Uuid(),
            sa.ForeignKey("assertion_records.record_id"),
            nullable=False,
        ),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("structured_reasons", sa.String(2000), nullable=False),
        sa.Column("narrative_explanation", sa.String(2000), nullable=False),
        sa.Column("acceptance_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("rejection_explanation", sa.String(2000), nullable=True),
        sa.Column("knowledge_confidence", sa.String(16), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("produced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_knowledge_evaluation_currentness",
        "knowledge_evaluation_records",
        ["assertion_record_id", "effective_from", "produced_at", "record_id"],
    )
    op.execute(
        "CREATE FUNCTION reject_knowledge_evaluation_mutation() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'Knowledge Evaluation Records are immutable'; END; $$ "
        "LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER knowledge_evaluation_records_immutable BEFORE UPDATE OR DELETE "
        "ON knowledge_evaluation_records FOR EACH ROW "
        "EXECUTE FUNCTION reject_knowledge_evaluation_mutation()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER knowledge_evaluation_records_immutable ON knowledge_evaluation_records"
    )
    op.execute("DROP FUNCTION reject_knowledge_evaluation_mutation")
    op.drop_index(
        "idx_knowledge_evaluation_currentness",
        table_name="knowledge_evaluation_records",
    )
    op.drop_table("knowledge_evaluation_records")
