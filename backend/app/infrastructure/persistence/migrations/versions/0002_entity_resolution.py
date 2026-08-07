"""Add append-only Enterprise Entity Resolution persistence."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_entity_resolution"
down_revision: str | None = "0001_canonical_v1_3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enterprise_entity_resolution_records",
        sa.Column("record_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "enterprise_entity_id",
            sa.Uuid(),
            sa.ForeignKey("enterprise_entities.enterprise_entity_id"),
            nullable=True,
        ),
        sa.Column("supporting_source_object_ids", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("business_confidence", sa.String(16), nullable=False),
        sa.Column("structured_reasons", sa.JSON(), nullable=False),
        sa.Column("narrative_explanation", sa.String(2000), nullable=False),
        sa.Column("produced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
    )
    op.create_index(
        "idx_eer_records_produced_at",
        "enterprise_entity_resolution_records",
        ["produced_at"],
    )
    op.create_table(
        "enterprise_entity_resolution_history",
        sa.Column("understanding_key", sa.String(64), primary_key=True),
        sa.Column(
            "active_record_id",
            sa.Uuid(),
            sa.ForeignKey("enterprise_entity_resolution_records.record_id"),
            nullable=False,
        ),
        sa.Column("archived_record_ids", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        """
        CREATE FUNCTION reject_resolution_record_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Enterprise Entity Resolution Records are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER enterprise_entity_resolution_records_immutable
        BEFORE UPDATE OR DELETE ON enterprise_entity_resolution_records
        FOR EACH ROW EXECUTE FUNCTION reject_resolution_record_mutation()
        """
    )


def downgrade() -> None:
    op.drop_table("enterprise_entity_resolution_history")
    op.execute(
        "DROP TRIGGER enterprise_entity_resolution_records_immutable "
        "ON enterprise_entity_resolution_records"
    )
    op.execute("DROP FUNCTION reject_resolution_record_mutation")
    op.drop_index("idx_eer_records_produced_at", table_name="enterprise_entity_resolution_records")
    op.drop_table("enterprise_entity_resolution_records")
