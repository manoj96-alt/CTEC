"""Create OQI-H4 Reference Integrity persistence (CDD-050 §10.2, §12, §23;
Artifact Authorization row 13).

Two tables: `oqi_integrity_reference_evaluations` (the tenant-owned,
append-only evaluation ledger, FK to the exact
`enterprise_entity_resolution_records` row consulted) and
`oqi_integrity_reference_findings` (the tenant-owned current-state Finding
lineage, `ORPHAN_REFERENCE` only). `source_object_id` uses a plain
single-column FK to `source_objects.source_object_id`, mirroring
`QualityFindingORM.source_object_id`'s own established precedent exactly --
`source_objects` carries no unique constraint on `(tenant_id,
source_object_id)` to target a tenant-qualified composite FK."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036_oqi_h4_integrity_reference"
down_revision: str | None = "0035_oqi_h4_integrity_structural"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_integrity_reference_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "relationship_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_requirements.relationship_requirement_id",
                name="fk_oqi_integrity_reference_evaluations_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "source_object_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_objects.source_object_id",
                name="fk_oqi_integrity_reference_evaluations_source_object_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "resolution_record_id",
            sa.Uuid(),
            sa.ForeignKey(
                "enterprise_entity_resolution_records.record_id",
                name="fk_oqi_integrity_reference_evaluations_resolution_record_id",
            ),
            nullable=False,
        ),
        sa.Column("resolution_outcome", sa.String(32), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("evaluation_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_on", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "resolution_outcome IN ('Resolved', 'Unresolved')",
            name="ck_oqi_integrity_reference_evaluations_resolution_outcome",
        ),
        sa.CheckConstraint(
            "outcome IN ('SATISFIED', 'VIOLATED')",
            name="ck_oqi_integrity_reference_evaluations_outcome",
        ),
    )
    op.create_index(
        "idx_oqi_integrity_reference_evaluations_tenant_id",
        "oqi_integrity_reference_evaluations",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_integrity_reference_evaluations_subject",
        "oqi_integrity_reference_evaluations",
        ["tenant_id", "source_object_id", "relationship_requirement_id"],
    )

    op.create_table(
        "oqi_integrity_reference_findings",
        sa.Column("finding_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "relationship_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "relationship_requirements.relationship_requirement_id",
                name="fk_oqi_integrity_reference_findings_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "source_object_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_objects.source_object_id",
                name="fk_oqi_integrity_reference_findings_source_object_id",
            ),
            nullable=False,
        ),
        sa.Column("finding_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "finding_type = 'ORPHAN_REFERENCE'",
            name="ck_oqi_integrity_reference_findings_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')", name="ck_oqi_integrity_reference_findings_status"
        ),
    )
    op.create_index(
        "idx_oqi_integrity_reference_findings_tenant_id",
        "oqi_integrity_reference_findings",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_integrity_reference_findings_status",
        "oqi_integrity_reference_findings",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("oqi_integrity_reference_findings")
    op.drop_table("oqi_integrity_reference_evaluations")
