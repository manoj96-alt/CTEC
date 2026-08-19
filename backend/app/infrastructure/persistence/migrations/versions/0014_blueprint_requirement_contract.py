"""Create the CDD-017 canonical Supply Chain Blueprint requirement-contract
persistence (Gate G G2; CDD-017 §6-9, G2 Persistence and Domain Artifact
Authorization companion).

Adds `blueprints` (global, product-owned, no `tenant_id` -- CDD-017 §9),
`concept_requirements` (references `entity_types.entity_type_id` --
CDD-017 §7), `relationship_requirements` (references
`relationship_types.relationship_type_id` and `entity_types.entity_type_id`
-- CDD-017 §7), and `information_element_requirements` (references
`concept_requirements` only -- CDD-017 §11; no generic attribute/property
identity mechanism is introduced).

`blueprints` reuses the existing `lifecyclestate_t`/`governancestatus_t`
Postgres ENUM types (created by migration 0001) verbatim via
`create_type=False` -- no new lifecycle/governance-status vocabulary
(CDD-017 §12). A new `blueprintobligation_t` ENUM (REQUIRED/CONDITIONAL/
OPTIONAL) is created for the one genuinely new closed vocabulary CDD-017
§6/§20 authorize, and reused with `create_type=False` on every subsequent
column that needs it.

`blueprints.blueprint_name` is deliberately NOT unique -- a naive
`unique=True` would make the row-level version chain
(`previous_version_id`) unusable the first time a second version is
minted (CDD-017 §8 honest precedent caveat; G2 companion migration-row
exclusion).

No `tenant_id` column is added anywhere. No production seed data is
inserted by this migration (CDD-017 §13 -- seeding is a separate future
phase).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014_blueprint_requirement_contract"
down_revision: str | None = "0013_decision_evaluation_group"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OBLIGATION_TYPE_NAME = "blueprintobligation_t"
_OBLIGATION_VALUES = ("REQUIRED", "CONDITIONAL", "OPTIONAL")


def _obligation_column() -> postgresql.ENUM:
    return postgresql.ENUM(*_OBLIGATION_VALUES, name=_OBLIGATION_TYPE_NAME, create_type=False)


def upgrade() -> None:
    postgresql.ENUM(*_OBLIGATION_VALUES, name=_OBLIGATION_TYPE_NAME).create(
        op.get_bind(), checkfirst=True
    )

    op.create_table(
        "blueprints",
        sa.Column(
            "blueprint_id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("blueprint_name", sa.String(200), nullable=False),
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
        sa.Column("version_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "previous_version_id",
            sa.Uuid(),
            sa.ForeignKey("blueprints.blueprint_id", name="fk_blueprints_previous_version_id"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey(
                "enterprise_entities.enterprise_entity_id", name="fk_blueprints_created_by"
            ),
            nullable=False,
        ),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "modified_by",
            sa.Uuid(),
            sa.ForeignKey(
                "enterprise_entities.enterprise_entity_id", name="fk_blueprints_modified_by"
            ),
            nullable=True,
        ),
        sa.Column("modified_on", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_blueprints_blueprint_name", "blueprints", ["blueprint_name"])
    op.create_index("idx_blueprints_lifecycle_state", "blueprints", ["lifecycle_state"])
    op.create_index("idx_blueprints_governance_status", "blueprints", ["governance_status"])
    op.create_index("idx_blueprints_previous_version_id", "blueprints", ["previous_version_id"])

    op.create_table(
        "concept_requirements",
        sa.Column(
            "concept_requirement_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "blueprint_id",
            sa.Uuid(),
            sa.ForeignKey("blueprints.blueprint_id", name="fk_concept_requirements_blueprint_id"),
            nullable=False,
        ),
        sa.Column(
            "entity_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "entity_types.entity_type_id", name="fk_concept_requirements_entity_type_id"
            ),
            nullable=False,
        ),
        sa.Column("domain_label", sa.String(200), nullable=True),
        sa.Column("obligation", _obligation_column(), nullable=False),
    )
    op.create_index(
        "idx_concept_requirements_blueprint_id", "concept_requirements", ["blueprint_id"]
    )
    op.create_index(
        "idx_concept_requirements_entity_type_id", "concept_requirements", ["entity_type_id"]
    )

    op.create_table(
        "relationship_requirements",
        sa.Column(
            "relationship_requirement_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "concept_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "concept_requirements.concept_requirement_id",
                name="fk_relationship_requirements_concept_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "relationship_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_types.relationship_type_id",
                name="fk_relationship_requirements_relationship_type_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "target_entity_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "entity_types.entity_type_id",
                name="fk_relationship_requirements_target_entity_type_id",
            ),
            nullable=False,
        ),
        sa.Column("obligation", _obligation_column(), nullable=False),
    )
    op.create_index(
        "idx_relationship_requirements_concept_requirement_id",
        "relationship_requirements",
        ["concept_requirement_id"],
    )
    op.create_index(
        "idx_relationship_requirements_relationship_type_id",
        "relationship_requirements",
        ["relationship_type_id"],
    )
    op.create_index(
        "idx_relationship_requirements_target_entity_type_id",
        "relationship_requirements",
        ["target_entity_type_id"],
    )

    op.create_table(
        "information_element_requirements",
        sa.Column(
            "information_element_requirement_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "concept_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "concept_requirements.concept_requirement_id",
                name="fk_information_element_requirements_concept_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column("element_name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("obligation", _obligation_column(), nullable=False),
    )
    op.create_index(
        "idx_information_element_requirements_concept_requirement_id",
        "information_element_requirements",
        ["concept_requirement_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_information_element_requirements_concept_requirement_id",
        table_name="information_element_requirements",
    )
    op.drop_table("information_element_requirements")

    op.drop_index(
        "idx_relationship_requirements_target_entity_type_id",
        table_name="relationship_requirements",
    )
    op.drop_index(
        "idx_relationship_requirements_relationship_type_id",
        table_name="relationship_requirements",
    )
    op.drop_index(
        "idx_relationship_requirements_concept_requirement_id",
        table_name="relationship_requirements",
    )
    op.drop_table("relationship_requirements")

    op.drop_index("idx_concept_requirements_entity_type_id", table_name="concept_requirements")
    op.drop_index("idx_concept_requirements_blueprint_id", table_name="concept_requirements")
    op.drop_table("concept_requirements")

    op.drop_index("idx_blueprints_previous_version_id", table_name="blueprints")
    op.drop_index("idx_blueprints_governance_status", table_name="blueprints")
    op.drop_index("idx_blueprints_lifecycle_state", table_name="blueprints")
    op.drop_index("idx_blueprints_blueprint_name", table_name="blueprints")
    op.drop_table("blueprints")

    postgresql.ENUM(name=_OBLIGATION_TYPE_NAME).drop(op.get_bind(), checkfirst=True)
