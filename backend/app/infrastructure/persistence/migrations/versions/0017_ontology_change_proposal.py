"""Create Gate M `ontology_change_proposals` persistence (Gate M; CDD-028
§12, §28; Gate M Artifact Authorization v1.1 §9).

Adds `ontology_change_proposals` -- a new, non-canonical table, never read
by `app.domain.ontology.resolver`. No `tenant_id` column (CDD-028 §10 --
canonical ontology carries no tenant dimension). New `proposalkind_t`
("CreateConcept"/"CreateRelationship") and `proposalstatus_t`
("Proposed"/"Approved"/"Rejected"/"Published") Postgres ENUM types, distinct
from `governancestatus_t` (AA v1.1 §12 -- a proposal's own workflow state is
not a canonical row's `GovernanceStatus`).

`uq_ontology_change_proposals_approved_concept_name` and
`uq_ontology_change_proposals_approved_relationship_name` are PostgreSQL
partial unique indexes (`WHERE status IN ('Approved','Published')`),
mirroring `uq_semantic_mappings_approved_source_field`'s own technique.

`proposed_source_entity_type_id`/`proposed_target_entity_type_id`/
`published_entity_type_id`/`published_relationship_type_id` carry
read-only-reference FKs into the existing `entity_types`/`relationship_types`
tables -- no column, index, constraint, or type on any existing canonical
table (`entity_types`, `relationship_types`, `institutional_concepts`,
`ontology_relationship_bindings`) is added, altered, or dropped by this
migration."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017_ontology_change_proposal"
down_revision: str | None = "0016_field_value_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ontology_change_proposals",
        sa.Column(
            "ontology_change_proposal_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "proposal_kind",
            postgresql.ENUM(
                "CreateConcept",
                "CreateRelationship",
                name="proposalkind_t",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "Proposed",
                "Approved",
                "Rejected",
                "Published",
                name="proposalstatus_t",
            ),
            nullable=False,
        ),
        sa.Column("proposed_entity_type_name", sa.String(200), nullable=True),
        sa.Column("proposed_definition", sa.String(2000), nullable=True),
        sa.Column("proposed_relationship_type_name", sa.String(200), nullable=True),
        sa.Column(
            "proposed_source_entity_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "entity_types.entity_type_id",
                name="fk_ontology_change_proposals_proposed_source_entity_type_id",
            ),
            nullable=True,
        ),
        sa.Column(
            "proposed_target_entity_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "entity_types.entity_type_id",
                name="fk_ontology_change_proposals_proposed_target_entity_type_id",
            ),
            nullable=True,
        ),
        sa.Column("proposed_by", sa.String(200), nullable=False),
        sa.Column("proposed_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(200), nullable=True),
        sa.Column("approved_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(200), nullable=True),
        sa.Column("rejected_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(1000), nullable=True),
        sa.Column("published_by", sa.String(200), nullable=True),
        sa.Column("published_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "published_entity_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "entity_types.entity_type_id",
                name="fk_ontology_change_proposals_published_entity_type_id",
            ),
            nullable=True,
        ),
        sa.Column(
            "published_relationship_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_types.relationship_type_id",
                name="fk_ontology_change_proposals_published_relationship_type_id",
            ),
            nullable=True,
        ),
    )
    op.create_index("idx_ontology_change_proposals_status", "ontology_change_proposals", ["status"])
    op.create_index(
        "idx_ontology_change_proposals_proposal_kind",
        "ontology_change_proposals",
        ["proposal_kind"],
    )
    op.create_index(
        "idx_ontology_change_proposals_proposed_by",
        "ontology_change_proposals",
        ["proposed_by"],
    )
    op.create_index(
        "idx_ontology_change_proposals_proposed_on",
        "ontology_change_proposals",
        ["proposed_on"],
    )
    op.create_index(
        "uq_ontology_change_proposals_approved_concept_name",
        "ontology_change_proposals",
        ["proposed_entity_type_name"],
        unique=True,
        postgresql_where=sa.text(
            "proposal_kind = 'CreateConcept' AND status IN ('Approved', 'Published')"
        ),
    )
    op.create_index(
        "uq_ontology_change_proposals_approved_relationship_name",
        "ontology_change_proposals",
        ["proposed_relationship_type_name"],
        unique=True,
        postgresql_where=sa.text(
            "proposal_kind = 'CreateRelationship' AND status IN ('Approved', 'Published')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_ontology_change_proposals_approved_relationship_name",
        table_name="ontology_change_proposals",
        postgresql_where=sa.text(
            "proposal_kind = 'CreateRelationship' AND status IN ('Approved', 'Published')"
        ),
    )
    op.drop_index(
        "uq_ontology_change_proposals_approved_concept_name",
        table_name="ontology_change_proposals",
        postgresql_where=sa.text(
            "proposal_kind = 'CreateConcept' AND status IN ('Approved', 'Published')"
        ),
    )
    op.drop_index(
        "idx_ontology_change_proposals_proposed_on", table_name="ontology_change_proposals"
    )
    op.drop_index(
        "idx_ontology_change_proposals_proposed_by", table_name="ontology_change_proposals"
    )
    op.drop_index(
        "idx_ontology_change_proposals_proposal_kind", table_name="ontology_change_proposals"
    )
    op.drop_index("idx_ontology_change_proposals_status", table_name="ontology_change_proposals")
    op.drop_table("ontology_change_proposals")
    postgresql.ENUM(name="proposalstatus_t").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="proposalkind_t").drop(op.get_bind(), checkfirst=True)
