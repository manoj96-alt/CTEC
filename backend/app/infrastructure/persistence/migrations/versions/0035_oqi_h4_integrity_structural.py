"""Create OQI-H4 Structural Integrity persistence (CDD-050 §10.1, §12, §23;
Artifact Authorization row 12).

Three tables: `oqi_integrity_structural_evaluations` (the tenant-owned,
append-only evaluation ledger), `oqi_integrity_structural_evaluation_
relationships` (the link table pinning exactly which qualifying
`InstitutionalRelationship` rows each evaluation counted -- reconstructable
distinct-target provenance), and `oqi_integrity_structural_findings` (the
tenant-owned current-state Finding lineage, `MISSING_REQUIRED_RELATIONSHIP` /
`RELATIONSHIP_CARDINALITY_VIOLATION` only). `enterprise_entity_id` uses
RFC-016's tenant-qualified composite FK to `enterprise_entities`."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0035_oqi_h4_integrity_structural"
down_revision: str | None = "0034_oqi_h4_integrity_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_integrity_structural_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "relationship_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_requirements.relationship_requirement_id",
                name="fk_oqi_integrity_structural_evaluations_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "integrity_relationship_cardinality_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_integrity_relationship_cardinalities.integrity_relationship_cardinality_id",
                name="fk_oqi_integrity_structural_evaluations_cardinality_id",
            ),
            nullable=False,
        ),
        sa.Column("enterprise_entity_id", sa.Uuid(), nullable=False),
        sa.Column("qualifying_target_count", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("evaluation_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_on", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enterprise_entity_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_integrity_structural_evaluations_entity",
        ),
        sa.CheckConstraint(
            "outcome IN ('SATISFIED', 'VIOLATED')",
            name="ck_oqi_integrity_structural_evaluations_outcome",
        ),
        sa.CheckConstraint(
            "qualifying_target_count >= 0",
            name="ck_oqi_integrity_structural_evaluations_count_nonneg",
        ),
    )
    op.create_index(
        "idx_oqi_integrity_structural_evaluations_tenant_id",
        "oqi_integrity_structural_evaluations",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_integrity_structural_evaluations_subject",
        "oqi_integrity_structural_evaluations",
        ["tenant_id", "enterprise_entity_id", "relationship_requirement_id"],
    )

    op.create_table(
        "oqi_integrity_structural_evaluation_relationships",
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_integrity_structural_evaluations.evaluation_id",
                name="fk_oqi_integrity_structural_eval_rel_evaluation_id",
            ),
            primary_key=True,
        ),
        sa.Column(
            "institutional_relationship_id",
            sa.Uuid(),
            sa.ForeignKey(
                "institutional_relationships.institutional_relationship_id",
                name="fk_oqi_integrity_structural_eval_rel_relationship_id",
            ),
            primary_key=True,
        ),
    )

    op.create_table(
        "oqi_integrity_structural_findings",
        sa.Column("finding_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "relationship_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_requirements.relationship_requirement_id",
                name="fk_oqi_integrity_structural_findings_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column("enterprise_entity_id", sa.Uuid(), nullable=False),
        sa.Column("finding_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enterprise_entity_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_integrity_structural_findings_entity",
        ),
        sa.CheckConstraint(
            "finding_type IN ('MISSING_REQUIRED_RELATIONSHIP', "
            "'RELATIONSHIP_CARDINALITY_VIOLATION')",
            name="ck_oqi_integrity_structural_findings_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')", name="ck_oqi_integrity_structural_findings_status"
        ),
    )
    op.create_index(
        "idx_oqi_integrity_structural_findings_tenant_id",
        "oqi_integrity_structural_findings",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_integrity_structural_findings_status",
        "oqi_integrity_structural_findings",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("oqi_integrity_structural_findings")
    op.drop_table("oqi_integrity_structural_evaluation_relationships")
    op.drop_table("oqi_integrity_structural_evaluations")
