"""Create Gate H H1 Source Field / Semantic Mapping persistence (Gate H H1;
CDD-019 §7, §8, §11, H1 Source Field / Semantic Mapping Artifact
Authorization companion).

Adds `source_fields` (references `source_objects.source_object_id`; global
identity within one `SourceObject`, no `tenant_id` column -- CDD-019 §7,
§18) and `semantic_mappings` (references `source_fields.source_field_id` and
`information_element_requirements.information_element_requirement_id`; no
`tenant_id` column -- CDD-019 §8, §18).

`uq_source_fields_object_label` enforces CDD-019 §7's physical-field
identity: within one `SourceObject`, a `field_label` identifies at most one
`SourceField` row.

`uq_semantic_mappings_approved_source_field` is a PostgreSQL partial unique
index (`WHERE governance_status = 'Approved'`) -- the durable,
database-enforced half of CDD-019 §11's bidirectional Approved-mapping
uniqueness rule (source-side). The target-side rule is intentionally not
expressed here (CDD-019 §11 -- tenant is join-derived, not a stored column;
see `semantic_mapping_repository.py`).

Both new tables reuse the existing `lifecyclestate_t`/`governancestatus_t`
Postgres ENUM types verbatim via `create_type=False` -- no new lifecycle/
governance-status vocabulary. No `tenant_id` column is added anywhere. No
Blueprint schema change. No H2/H3/H4 schema.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015_source_field_semantic"
down_revision: str | None = "0014_blueprint_requirement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_fields",
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source_object_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_objects.source_object_id", name="fk_source_fields_source_object_id"
            ),
            nullable=False,
        ),
        sa.Column("field_label", sa.String(200), nullable=False),
        sa.Column(
            "lifecycle_state",
            postgresql.ENUM(
                "Draft",
                "Active",
                "Suspended",
                "Archived",
                name="lifecyclestate_t",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "governance_status",
            postgresql.ENUM(
                "Proposed",
                "Approved",
                "Retired",
                "Archived",
                name="governancestatus_t",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey(
                "enterprise_entities.enterprise_entity_id", name="fk_source_fields_created_by"
            ),
            nullable=False,
        ),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "modified_by",
            sa.Uuid(),
            sa.ForeignKey(
                "enterprise_entities.enterprise_entity_id", name="fk_source_fields_modified_by"
            ),
            nullable=True,
        ),
        sa.Column("modified_on", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_source_fields_source_object_id", "source_fields", ["source_object_id"])
    op.create_index("idx_source_fields_lifecycle_state", "source_fields", ["lifecycle_state"])
    op.create_index("idx_source_fields_governance_status", "source_fields", ["governance_status"])
    op.create_index("idx_source_fields_created_by", "source_fields", ["created_by"])
    op.create_index("idx_source_fields_created_on", "source_fields", ["created_on"])
    op.create_index("idx_source_fields_modified_by", "source_fields", ["modified_by"])
    op.create_index("idx_source_fields_modified_on", "source_fields", ["modified_on"])
    op.create_unique_constraint(
        "uq_source_fields_object_label",
        "source_fields",
        ["source_object_id", "field_label"],
    )

    op.create_table(
        "semantic_mappings",
        sa.Column(
            "semantic_mapping_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_fields.source_field_id", name="fk_semantic_mappings_source_field_id"
            ),
            nullable=False,
        ),
        sa.Column(
            "information_element_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "information_element_requirements.information_element_requirement_id",
                name="fk_semantic_mappings_information_element_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "lifecycle_state",
            postgresql.ENUM(
                "Draft",
                "Active",
                "Suspended",
                "Archived",
                name="lifecyclestate_t",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "governance_status",
            postgresql.ENUM(
                "Proposed",
                "Approved",
                "Retired",
                "Archived",
                name="governancestatus_t",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey(
                "enterprise_entities.enterprise_entity_id", name="fk_semantic_mappings_created_by"
            ),
            nullable=False,
        ),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "modified_by",
            sa.Uuid(),
            sa.ForeignKey(
                "enterprise_entities.enterprise_entity_id", name="fk_semantic_mappings_modified_by"
            ),
            nullable=True,
        ),
        sa.Column("modified_on", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_semantic_mappings_source_field_id", "semantic_mappings", ["source_field_id"]
    )
    op.create_index(
        "idx_semantic_mappings_information_element_requirement_id",
        "semantic_mappings",
        ["information_element_requirement_id"],
    )
    op.create_index(
        "idx_semantic_mappings_lifecycle_state", "semantic_mappings", ["lifecycle_state"]
    )
    op.create_index(
        "idx_semantic_mappings_governance_status", "semantic_mappings", ["governance_status"]
    )
    op.create_index("idx_semantic_mappings_created_by", "semantic_mappings", ["created_by"])
    op.create_index("idx_semantic_mappings_created_on", "semantic_mappings", ["created_on"])
    op.create_index("idx_semantic_mappings_modified_by", "semantic_mappings", ["modified_by"])
    op.create_index("idx_semantic_mappings_modified_on", "semantic_mappings", ["modified_on"])
    op.create_index(
        "uq_semantic_mappings_approved_source_field",
        "semantic_mappings",
        ["source_field_id"],
        unique=True,
        postgresql_where=sa.text("governance_status = 'Approved'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_semantic_mappings_approved_source_field",
        table_name="semantic_mappings",
        postgresql_where=sa.text("governance_status = 'Approved'"),
    )
    op.drop_index("idx_semantic_mappings_modified_on", table_name="semantic_mappings")
    op.drop_index("idx_semantic_mappings_modified_by", table_name="semantic_mappings")
    op.drop_index("idx_semantic_mappings_created_on", table_name="semantic_mappings")
    op.drop_index("idx_semantic_mappings_created_by", table_name="semantic_mappings")
    op.drop_index("idx_semantic_mappings_governance_status", table_name="semantic_mappings")
    op.drop_index("idx_semantic_mappings_lifecycle_state", table_name="semantic_mappings")
    op.drop_index(
        "idx_semantic_mappings_information_element_requirement_id",
        table_name="semantic_mappings",
    )
    op.drop_index("idx_semantic_mappings_source_field_id", table_name="semantic_mappings")
    op.drop_table("semantic_mappings")

    op.drop_constraint("uq_source_fields_object_label", "source_fields", type_="unique")
    op.drop_index("idx_source_fields_modified_on", table_name="source_fields")
    op.drop_index("idx_source_fields_modified_by", table_name="source_fields")
    op.drop_index("idx_source_fields_created_on", table_name="source_fields")
    op.drop_index("idx_source_fields_created_by", table_name="source_fields")
    op.drop_index("idx_source_fields_governance_status", table_name="source_fields")
    op.drop_index("idx_source_fields_lifecycle_state", table_name="source_fields")
    op.drop_index("idx_source_fields_source_object_id", table_name="source_fields")
    op.drop_table("source_fields")
