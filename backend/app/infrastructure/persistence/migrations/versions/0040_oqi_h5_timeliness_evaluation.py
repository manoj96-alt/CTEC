"""Create OQI-H5 Timeliness Evaluation/Finding persistence (CDD-051 §8,
§17-§19, §28; Artifact Authorization row 9).

Two tables: `oqi_timeliness_evaluations` (the tenant-owned, append-only
evaluation ledger) and `oqi_timeliness_findings` (the tenant-owned
current-state Finding lineage, `STALE_SOURCE_EVIDENCE` /
`INGESTION_LATENCY_EXCEEDED` only). Both use RFC-016's tenant-qualified
composite FK pattern against `oqi_timeliness_policies` and `source_objects`
-- never a plain single-column FK.

Revision id corrected from the originally-frozen `"0040_oqi_h5_timeliness_
evaluation"` (34 chars, exceeds alembic_version.version_num's VARCHAR(32))
to `"0040_oqi_h5_timeliness_eval"` (27 chars) by CDD-051-Artifact-
Authorization-Migration-Revision-Length-Correction.md -- filename
unchanged, identical in kind to the CDD-040 precedent for migration 0021."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0040_oqi_h5_timeliness_eval"
down_revision: str | None = "0039_oqi_h5_timeliness_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_timeliness_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("finding_type", sa.String(40), nullable=False),
        sa.Column("source_object_id", sa.Uuid(), nullable=False),
        sa.Column(
            "field_value_evidence_id",
            sa.Uuid(),
            sa.ForeignKey(
                "field_value_evidence.field_value_evidence_id",
                name="fk_oqi_timeliness_evaluations_field_value_evidence_id",
            ),
            nullable=False,
        ),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("evaluation_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_on", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "policy_id", "policy_version"],
            [
                "oqi_timeliness_policies.tenant_id",
                "oqi_timeliness_policies.policy_id",
                "oqi_timeliness_policies.version",
            ],
            name="fk_oqi_timeliness_evaluations_tenant_policy",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_object_id"],
            ["source_objects.tenant_id", "source_objects.source_object_id"],
            name="fk_oqi_timeliness_evaluations_tenant_source_object",
        ),
        sa.CheckConstraint(
            "finding_type IN ('STALE_SOURCE_EVIDENCE', 'INGESTION_LATENCY_EXCEEDED')",
            name="ck_oqi_timeliness_evaluations_finding_type",
        ),
        sa.CheckConstraint(
            "outcome IN ('SATISFIED', 'VIOLATED')",
            name="ck_oqi_timeliness_evaluations_outcome",
        ),
    )
    op.create_index(
        "idx_oqi_timeliness_evaluations_tenant_id", "oqi_timeliness_evaluations", ["tenant_id"]
    )
    op.create_index(
        "idx_oqi_timeliness_evaluations_subject",
        "oqi_timeliness_evaluations",
        ["tenant_id", "source_object_id", "policy_id", "finding_type"],
    )

    op.create_table(
        "oqi_timeliness_findings",
        sa.Column("finding_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("finding_type", sa.String(40), nullable=False),
        sa.Column("source_object_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_horizon", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "policy_id", "policy_version"],
            [
                "oqi_timeliness_policies.tenant_id",
                "oqi_timeliness_policies.policy_id",
                "oqi_timeliness_policies.version",
            ],
            name="fk_oqi_timeliness_findings_tenant_policy",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_object_id"],
            ["source_objects.tenant_id", "source_objects.source_object_id"],
            name="fk_oqi_timeliness_findings_tenant_source_object",
        ),
        sa.CheckConstraint(
            "finding_type IN ('STALE_SOURCE_EVIDENCE', 'INGESTION_LATENCY_EXCEEDED')",
            name="ck_oqi_timeliness_findings_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')", name="ck_oqi_timeliness_findings_status"
        ),
    )
    op.create_index(
        "idx_oqi_timeliness_findings_tenant_id", "oqi_timeliness_findings", ["tenant_id"]
    )
    op.create_index("idx_oqi_timeliness_findings_status", "oqi_timeliness_findings", ["status"])


def downgrade() -> None:
    op.drop_table("oqi_timeliness_findings")
    op.drop_table("oqi_timeliness_evaluations")
