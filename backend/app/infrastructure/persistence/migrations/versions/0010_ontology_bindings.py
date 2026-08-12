"""Add ontology relationship domain/range bindings for the Ontology Studio MVP."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_ontology_bindings"
down_revision: str | None = "0009_api_security_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ontology_relationship_bindings",
        sa.Column("binding_id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "relationship_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_types.relationship_type_id",
                name="fk_ontology_bindings_relationship_type_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "source_entity_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "entity_types.entity_type_id",
                name="fk_ontology_bindings_source_entity_type_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "target_entity_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "entity_types.entity_type_id",
                name="fk_ontology_bindings_target_entity_type_id",
            ),
            nullable=False,
        ),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "relationship_type_id",
            "source_entity_type_id",
            "target_entity_type_id",
            name="uq_ontology_bindings_triple",
        ),
    )
    op.create_index(
        "idx_ontology_bindings_relationship_type_id",
        "ontology_relationship_bindings",
        ["relationship_type_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_ontology_bindings_relationship_type_id", table_name="ontology_relationship_bindings")
    op.drop_table("ontology_relationship_bindings")
