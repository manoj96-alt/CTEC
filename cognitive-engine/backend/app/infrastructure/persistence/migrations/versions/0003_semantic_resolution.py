"""Add immutable Semantic Resolution persistence."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_semantic_resolution"
down_revision: str | None = "0002_entity_resolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_resolution_records",
        sa.Column("record_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "enterprise_entity_id",
            sa.Uuid(),
            sa.ForeignKey("enterprise_entities.enterprise_entity_id"),
            nullable=False,
        ),
        sa.Column("context_id", sa.Uuid(), sa.ForeignKey("contexts.context_id"), nullable=False),
        sa.Column(
            "semantic_interpretation_id",
            sa.Uuid(),
            sa.ForeignKey("institutional_concepts.institutional_concept_id"),
            nullable=True,
        ),
        sa.Column("candidate_interpretations", sa.JSON(), nullable=False),
        sa.Column("supporting_entity_resolution_record_ids", sa.JSON(), nullable=False),
        sa.Column("supporting_source_object_ids", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("business_confidence", sa.String(16), nullable=False),
        sa.Column("structured_reasons", sa.JSON(), nullable=False),
        sa.Column("narrative_explanation", sa.String(2000), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("produced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_semantic_records_entity_context",
        "semantic_resolution_records",
        ["enterprise_entity_id", "context_id"],
    )
    op.create_table(
        "semantic_resolution_history",
        sa.Column("understanding_key", sa.String(64), primary_key=True),
        sa.Column(
            "active_record_id",
            sa.Uuid(),
            sa.ForeignKey("semantic_resolution_records.record_id"),
            nullable=False,
        ),
        sa.Column("archived_record_ids", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "CREATE FUNCTION reject_semantic_record_mutation() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'Semantic Resolution Records are immutable'; END; $$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER semantic_resolution_records_immutable BEFORE UPDATE OR DELETE ON semantic_resolution_records FOR EACH ROW EXECUTE FUNCTION reject_semantic_record_mutation()"
    )


def downgrade() -> None:
    op.drop_table("semantic_resolution_history")
    op.execute("DROP TRIGGER semantic_resolution_records_immutable ON semantic_resolution_records")
    op.execute("DROP FUNCTION reject_semantic_record_mutation")
    op.drop_index("idx_semantic_records_entity_context", table_name="semantic_resolution_records")
    op.drop_table("semantic_resolution_records")
