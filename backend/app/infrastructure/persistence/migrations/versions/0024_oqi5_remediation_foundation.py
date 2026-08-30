"""Create OQI5-I1 Deterministic Remediation Foundation persistence
(CDD-043 §11-§14; Artifact Authorization §2 row 8).

Four new tables: `oqi_remediation_cases`, `oqi_remediation_candidates`,
`oqi_remediation_instructions`, `oqi_remediation_authorizations`.

No existing table (OQI1/OQI2/OQI3/OQI4, Gate S, Gate V, or any other) is
altered by this migration -- OQI5-I1 reads existing OQI1/OQI2/OQI3
evidence and finding facts, it never writes them, and it introduces its
own structurally independent authorization table rather than extending
`gate_s_approval_requests` (CDD-043 §9)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024_oqi5_remediation"
down_revision: str | None = "0023_oqi4_ontology_impact"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_remediation_cases",
        sa.Column("case_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("finding_family", sa.String(16), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "external_execution_claimed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("external_execution_claimed_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_on", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "finding_family",
            "finding_id",
            name="uq_oqi_remediation_cases_finding",
        ),
    )
    op.create_index("idx_oqi_remediation_cases_tenant_id", "oqi_remediation_cases", ["tenant_id"])
    op.create_index("idx_oqi_remediation_cases_status", "oqi_remediation_cases", ["status"])

    op.create_table(
        "oqi_remediation_candidates",
        sa.Column("candidate_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_remediation_cases.case_id",
                name="fk_oqi_remediation_candidates_case_id",
            ),
            nullable=False,
        ),
        sa.Column("target_source_object_id", sa.Uuid(), nullable=False),
        sa.Column("target_source_field_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_value", sa.String(4000), nullable=False),
        sa.Column(
            "supporting_evidence_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "conflicting_evidence_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "missing_participant_roles",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("authority_participant_role", sa.String(64), nullable=True),
        sa.Column("basis", sa.String(32), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_oqi_remediation_candidates_case_id", "oqi_remediation_candidates", ["case_id"]
    )

    op.create_table(
        "oqi_remediation_instructions",
        sa.Column("instruction_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("finding_state_revision", sa.Integer(), nullable=False),
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_remediation_cases.case_id",
                name="fk_oqi_remediation_instructions_case_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_remediation_candidates.candidate_id",
                name="fk_oqi_remediation_instructions_candidate_id",
            ),
            nullable=False,
        ),
        sa.Column("target_source_object_id", sa.Uuid(), nullable=False),
        sa.Column("target_source_field_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("agent_recommendation_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_oqi_remediation_instructions_case_id", "oqi_remediation_instructions", ["case_id"]
    )

    op.create_table(
        "oqi_remediation_authorizations",
        sa.Column(
            "authorization_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "instruction_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_remediation_instructions.instruction_id",
                name="fk_oqi_remediation_authorizations_instruction_id",
            ),
            nullable=False,
        ),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("requested_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("decided_by", sa.String(200), nullable=True),
        sa.Column("decided_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(1000), nullable=True),
        sa.Column("consumed_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_execution_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "idx_oqi_remediation_authorizations_tenant_id",
        "oqi_remediation_authorizations",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_remediation_authorizations_status", "oqi_remediation_authorizations", ["status"]
    )
    op.create_index(
        "idx_oqi_remediation_authorizations_instruction_id",
        "oqi_remediation_authorizations",
        ["instruction_id"],
    )


def downgrade() -> None:
    op.drop_table("oqi_remediation_authorizations")
    op.drop_table("oqi_remediation_instructions")
    op.drop_table("oqi_remediation_candidates")
    op.drop_table("oqi_remediation_cases")
