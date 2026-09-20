"""Create OQI-H6 governed EnterpriseEntity Uniqueness persistence (CDD-084
§7, §11-§29; Artifact Authorization §6-§7, row 10).

Five tables: `oqi_uniqueness_policies` (tenant-owned, versioned, anchored to
`entity_type_id`), `oqi_uniqueness_evaluations` (tenant-owned, append-only
per-entity evaluation ledger), `oqi_uniqueness_candidates` (tenant-owned,
immutable canonical-pair candidate ledger), `oqi_uniqueness_adjudications`
(tenant-owned, append-only steward decision ledger), and
`oqi_uniqueness_findings` (tenant-owned, current-state Finding lineage,
`DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE` only).

No existing table is altered. `EnterpriseEntity`'s own tenant-qualified
candidate key (`uq_enterprise_entities_tenant_pk`) already exists on
current `origin/main` (CDD-084 §13) -- no parent-side correction is
required here, unlike `0039_oqi_h5_timeliness_policy`'s own
`oqi_business_processes` correction."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0047_oqi_h6_uniqueness"
down_revision: str | None = "0046_oqi5_remediation_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_uniqueness_policies",
        sa.Column("policy_id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "entity_type_id",
            sa.Uuid(),
            sa.ForeignKey(
                "entity_types.entity_type_id", name="fk_oqi_uniqueness_policies_entity_type_id"
            ),
            nullable=False,
        ),
        sa.Column("bucket_max_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "policy_id", "version", name="uq_oqi_uniqueness_policies_tenant_pk"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_uniqueness_policies_status"
        ),
        sa.CheckConstraint(
            "bucket_max_size > 0", name="ck_oqi_uniqueness_policies_bucket_max_size_positive"
        ),
    )
    op.create_index(
        "idx_oqi_uniqueness_policies_tenant_id", "oqi_uniqueness_policies", ["tenant_id"]
    )
    op.create_index(
        "uq_oqi_uniqueness_policies_one_active_per_type",
        "oqi_uniqueness_policies",
        ["tenant_id", "entity_type_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "oqi_uniqueness_candidates",
        sa.Column(
            "candidate_id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("member_a_id", sa.Uuid(), nullable=False),
        sa.Column("member_b_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("matched_normalized_name", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "member_a_id < member_b_id", name="ck_oqi_uniqueness_candidates_canonical_pair"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "member_a_id",
            "member_b_id",
            "policy_id",
            "policy_version",
            name="uq_oqi_uniqueness_candidates_idempotent",
        ),
        sa.UniqueConstraint(
            "tenant_id", "candidate_id", name="uq_oqi_uniqueness_candidates_tenant_pk"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "member_a_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_candidates_tenant_member_a",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "member_b_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_candidates_tenant_member_b",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "policy_id", "policy_version"],
            [
                "oqi_uniqueness_policies.tenant_id",
                "oqi_uniqueness_policies.policy_id",
                "oqi_uniqueness_policies.version",
            ],
            name="fk_oqi_uniqueness_candidates_tenant_policy",
        ),
    )
    op.create_index(
        "idx_oqi_uniqueness_candidates_tenant_id", "oqi_uniqueness_candidates", ["tenant_id"]
    )
    op.create_index(
        "idx_oqi_uniqueness_candidates_pair",
        "oqi_uniqueness_candidates",
        ["tenant_id", "member_a_id", "member_b_id"],
    )

    op.create_table(
        "oqi_uniqueness_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("enterprise_entity_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("not_evaluable_reason", sa.String(32), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("evaluated_on", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "policy_id", "policy_version"],
            [
                "oqi_uniqueness_policies.tenant_id",
                "oqi_uniqueness_policies.policy_id",
                "oqi_uniqueness_policies.version",
            ],
            name="fk_oqi_uniqueness_evaluations_tenant_policy",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enterprise_entity_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_evaluations_tenant_entity",
        ),
        sa.CheckConstraint(
            "outcome IN ('SATISFIED', 'VIOLATED', 'NOT_EVALUABLE')",
            name="ck_oqi_uniqueness_evaluations_outcome",
        ),
        sa.CheckConstraint(
            "(outcome = 'NOT_EVALUABLE' AND not_evaluable_reason = 'BUCKET_EXCEEDED_CAP') "
            "OR (outcome != 'NOT_EVALUABLE' AND not_evaluable_reason IS NULL)",
            name="ck_oqi_uniqueness_evaluations_not_evaluable_reason",
        ),
        sa.CheckConstraint(
            "candidate_count >= 0", name="ck_oqi_uniqueness_evaluations_candidate_count_nonneg"
        ),
    )
    op.create_index(
        "idx_oqi_uniqueness_evaluations_subject",
        "oqi_uniqueness_evaluations",
        ["tenant_id", "enterprise_entity_id"],
    )
    op.create_index(
        "idx_oqi_uniqueness_evaluations_policy",
        "oqi_uniqueness_evaluations",
        ["tenant_id", "policy_id"],
    )

    op.create_table(
        "oqi_uniqueness_adjudications",
        sa.Column(
            "adjudication_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("actor_id", sa.String(200), nullable=False),
        sa.Column("rationale", sa.String(2000), nullable=False),
        sa.Column("decided_on", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "candidate_id"],
            ["oqi_uniqueness_candidates.tenant_id", "oqi_uniqueness_candidates.candidate_id"],
            name="fk_oqi_uniqueness_adjudications_tenant_candidate",
        ),
        sa.CheckConstraint(
            "action IN ('REJECT_NOT_DUPLICATE', 'CONFIRM_DUPLICATE')",
            name="ck_oqi_uniqueness_adjudications_action",
        ),
    )
    op.create_index(
        "idx_oqi_uniqueness_adjudications_candidate",
        "oqi_uniqueness_adjudications",
        ["tenant_id", "candidate_id", "decided_on"],
    )

    op.create_table(
        "oqi_uniqueness_findings",
        sa.Column("finding_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("finding_type", sa.String(40), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("member_a_id", sa.Uuid(), nullable=False),
        sa.Column("member_b_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "member_a_id < member_b_id", name="ck_oqi_uniqueness_findings_canonical_pair"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "candidate_id"],
            ["oqi_uniqueness_candidates.tenant_id", "oqi_uniqueness_candidates.candidate_id"],
            name="fk_oqi_uniqueness_findings_tenant_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "member_a_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_findings_tenant_member_a",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "member_b_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_findings_tenant_member_b",
        ),
        sa.CheckConstraint(
            "finding_type = 'DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE'",
            name="ck_oqi_uniqueness_findings_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')", name="ck_oqi_uniqueness_findings_status"
        ),
    )
    op.create_index(
        "idx_oqi_uniqueness_findings_tenant_id", "oqi_uniqueness_findings", ["tenant_id"]
    )
    op.create_index("idx_oqi_uniqueness_findings_status", "oqi_uniqueness_findings", ["status"])
    op.create_index(
        "idx_oqi_uniqueness_findings_pair",
        "oqi_uniqueness_findings",
        ["tenant_id", "member_a_id", "member_b_id"],
    )


def downgrade() -> None:
    op.drop_table("oqi_uniqueness_findings")
    op.drop_table("oqi_uniqueness_adjudications")
    op.drop_table("oqi_uniqueness_evaluations")
    op.drop_table("oqi_uniqueness_candidates")
    op.drop_table("oqi_uniqueness_policies")
