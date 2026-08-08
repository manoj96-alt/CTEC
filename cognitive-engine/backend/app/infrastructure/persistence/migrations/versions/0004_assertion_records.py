"""Add governed, append-only Assertion Record persistence."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_assertion_records"
down_revision: str | None = "0003_semantic_resolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assertion_records",
        sa.Column("record_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "subject_entity_id",
            sa.Uuid(),
            sa.ForeignKey("enterprise_entities.enterprise_entity_id"),
            nullable=False,
        ),
        sa.Column(
            "predicate_relationship_type_id",
            sa.Uuid(),
            sa.ForeignKey("relationship_types.relationship_type_id"),
            nullable=False,
        ),
        sa.Column(
            "object_institutional_concept_id",
            sa.Uuid(),
            sa.ForeignKey("institutional_concepts.institutional_concept_id"),
            nullable=False,
        ),
        sa.Column("context_id", sa.Uuid(), sa.ForeignKey("contexts.context_id"), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("business_confidence", sa.String(16), nullable=False),
        sa.Column("structured_reasons", sa.String(2000), nullable=False),
        sa.Column("narrative_explanation", sa.String(2000), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("produced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_assertion_record_identity",
        "assertion_records",
        [
            "subject_entity_id",
            "predicate_relationship_type_id",
            "object_institutional_concept_id",
            "context_id",
        ],
    )
    op.create_table(
        "assertion_record_entity_resolution_evidence",
        sa.Column(
            "assertion_record_id",
            sa.Uuid(),
            sa.ForeignKey("assertion_records.record_id"),
            primary_key=True,
        ),
        sa.Column(
            "entity_resolution_record_id",
            sa.Uuid(),
            sa.ForeignKey("enterprise_entity_resolution_records.record_id"),
            primary_key=True,
        ),
    )
    op.create_table(
        "assertion_record_semantic_resolution_evidence",
        sa.Column(
            "assertion_record_id",
            sa.Uuid(),
            sa.ForeignKey("assertion_records.record_id"),
            primary_key=True,
        ),
        sa.Column(
            "semantic_resolution_record_id",
            sa.Uuid(),
            sa.ForeignKey("semantic_resolution_records.record_id"),
            primary_key=True,
        ),
    )
    op.create_table(
        "assertion_record_history",
        sa.Column("assertion_identity_key", sa.String(64), primary_key=True),
        sa.Column(
            "active_record_id",
            sa.Uuid(),
            sa.ForeignKey("assertion_records.record_id"),
            nullable=False,
        ),
        sa.Column("archived_record_ids", sa.String(4000), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "CREATE FUNCTION reject_assertion_record_mutation() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'Assertion Records are immutable'; END; $$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER assertion_records_immutable BEFORE UPDATE OR DELETE ON assertion_records FOR EACH ROW EXECUTE FUNCTION reject_assertion_record_mutation()"
    )


def downgrade() -> None:
    op.drop_table("assertion_record_history")
    op.drop_table("assertion_record_semantic_resolution_evidence")
    op.drop_table("assertion_record_entity_resolution_evidence")
    op.execute("DROP TRIGGER assertion_records_immutable ON assertion_records")
    op.execute("DROP FUNCTION reject_assertion_record_mutation")
    op.drop_index("idx_assertion_record_identity", table_name="assertion_records")
    op.drop_table("assertion_records")
