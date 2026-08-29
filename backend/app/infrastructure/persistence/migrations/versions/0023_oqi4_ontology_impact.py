"""Create OQI4 Ontology Impact Intelligence persistence (CDD-042 §8, §11;
Artifact Authorization §2 row 9).

Five new tables: `impact_propagation_policies`, `ontology_impact_evaluations`,
`ontology_impact_observations`, `ontology_impact_paths`,
`current_ontology_impacts`.

No existing table (OQI1/OQI2/OQI3, `enterprise_entities`,
`institutional_relationships`, `relationship_types`,
`enterprise_entity_resolution_records`, `assertions`, `semantic_mappings`,
or any other) is altered by this migration -- OQI4 reads governed ontology
and entity-resolution facts, it never writes them, and it introduces zero
new lineage tables (CDD-042 §4.7)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023_oqi4_ontology_impact"
down_revision: str | None = "0022_oqi3_business_rule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "impact_propagation_policies",
        sa.Column("policy_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "relationship_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_types.relationship_type_id",
                name="fk_impact_propagation_policies_relationship_type_id",
            ),
            nullable=False,
        ),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("max_depth", sa.Integer(), nullable=False),
        sa.Column("governance_status", sa.String(16), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "previous_version_id",
            sa.Uuid(),
            sa.ForeignKey(
                "impact_propagation_policies.policy_id",
                name="fk_impact_propagation_policies_previous_version_id",
            ),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "tenant_id", "policy_id", name="uq_impact_propagation_policies_tenant_pk"
        ),
        sa.CheckConstraint("max_depth >= 1 AND max_depth <= 10", name="ck_ipp_max_depth_bounded"),
    )
    op.create_index(
        "idx_impact_propagation_policies_tenant_id", "impact_propagation_policies", ["tenant_id"]
    )
    op.create_index(
        "idx_impact_propagation_policies_relationship_type_id",
        "impact_propagation_policies",
        ["relationship_type_id"],
    )
    op.create_index(
        "uq_impact_propagation_policies_one_active",
        "impact_propagation_policies",
        ["tenant_id", "relationship_type_id", "direction"],
        unique=True,
        postgresql_where=sa.text("governance_status = 'Active'"),
    )

    op.create_table(
        "ontology_impact_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("finding_family", sa.String(8), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("finding_state_revision", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column(
            "resolution_record_id",
            sa.Uuid(),
            sa.ForeignKey(
                "enterprise_entity_resolution_records.record_id",
                name="fk_ontology_impact_evaluations_resolution_record_id",
            ),
            nullable=True,
        ),
        sa.Column("traversed_state_digest", sa.String(64), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "finding_family",
            "finding_id",
            "finding_state_revision",
            "traversed_state_digest",
            name="uq_ontology_impact_evaluations_natural_key",
        ),
    )
    op.create_index(
        "idx_ontology_impact_evaluations_tenant_id", "ontology_impact_evaluations", ["tenant_id"]
    )
    op.create_index(
        "idx_ontology_impact_evaluations_finding",
        "ontology_impact_evaluations",
        ["tenant_id", "finding_family", "finding_id"],
    )

    op.create_table(
        "ontology_impact_observations",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "ontology_impact_evaluations.evaluation_id",
                name="fk_ontology_impact_observations_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column("ontology_element_type", sa.String(16), primary_key=True),
        sa.Column("ontology_element_id", sa.Uuid(), primary_key=True),
        sa.Column("impact_kind", sa.String(16), primary_key=True),
        sa.Column("basis", sa.String(40), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
    )
    op.create_index(
        "idx_ontology_impact_observations_evaluation_id",
        "ontology_impact_observations",
        ["evaluation_id"],
    )
    op.create_index(
        "idx_ontology_impact_observations_element",
        "ontology_impact_observations",
        ["ontology_element_type", "ontology_element_id"],
    )

    op.create_table(
        "ontology_impact_paths",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "ontology_impact_evaluations.evaluation_id",
                name="fk_ontology_impact_paths_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column("ontology_element_id", sa.Uuid(), primary_key=True),
        sa.Column("path_ordinal", sa.Integer(), primary_key=True),
        sa.Column(
            "institutional_relationship_id",
            sa.Uuid(),
            sa.ForeignKey(
                "institutional_relationships.institutional_relationship_id",
                name="fk_ontology_impact_paths_relationship_id",
            ),
            nullable=False,
        ),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column(
            "policy_id",
            sa.Uuid(),
            sa.ForeignKey(
                "impact_propagation_policies.policy_id",
                name="fk_ontology_impact_paths_policy_id",
            ),
            nullable=False,
        ),
        sa.Column("policy_version_number", sa.Integer(), nullable=False),
    )
    op.create_index(
        "idx_ontology_impact_paths_evaluation_id", "ontology_impact_paths", ["evaluation_id"]
    )

    op.create_table(
        "current_ontology_impacts",
        sa.Column("current_impact_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("finding_family", sa.String(8), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("ontology_element_type", sa.String(16), nullable=False),
        sa.Column("ontology_element_id", sa.Uuid(), nullable=False),
        sa.Column("impact_kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "latest_evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "ontology_impact_evaluations.evaluation_id",
                name="fk_current_ontology_impacts_latest_evaluation_id",
            ),
            nullable=False,
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "finding_family",
            "finding_id",
            "ontology_element_type",
            "ontology_element_id",
            "impact_kind",
            name="uq_current_ontology_impacts_natural_key",
        ),
    )
    op.create_index(
        "idx_current_ontology_impacts_tenant_id", "current_ontology_impacts", ["tenant_id"]
    )
    op.create_index(
        "idx_current_ontology_impacts_element",
        "current_ontology_impacts",
        ["ontology_element_type", "ontology_element_id"],
    )


def downgrade() -> None:
    op.drop_table("current_ontology_impacts")
    op.drop_table("ontology_impact_paths")
    op.drop_table("ontology_impact_observations")
    op.drop_table("ontology_impact_evaluations")
    op.drop_table("impact_propagation_policies")
