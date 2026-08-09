"""Add the six bounded CDD-012 runtime persistence records."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_durable_execution"
down_revision: str | None = "0007_governance_eval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_executions",
        sa.Column("execution_id", sa.Uuid(), primary_key=True),
        sa.Column("logical_execution_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("protocol_version", sa.String(32), nullable=False),
        sa.Column("integration_contract_version", sa.String(32), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("request_classification", sa.String(100), nullable=False),
        sa.Column("payload_fingerprint", sa.LargeBinary(), nullable=False),
        sa.Column("control_fingerprint", sa.LargeBinary(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("terminal_at", sa.DateTime(timezone=True)),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retention_until", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "protocol_version", "request_id"),
    )
    op.create_index(
        "idx_runtime_executions_recovery",
        "runtime_executions",
        ["tenant_id", "state", "admitted_at"],
    )
    op.create_table(
        "runtime_stages",
        sa.Column("stage_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "execution_id",
            sa.Uuid(),
            sa.ForeignKey("runtime_executions.execution_id"),
            nullable=False,
        ),
        sa.Column("stage_name", sa.String(16), nullable=False),
        sa.Column("stage_ordinal", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("input_handoff_id", sa.Uuid()),
        sa.Column("output_handoff_id", sa.Uuid()),
        sa.Column("safe_failure_code", sa.String(100)),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.UniqueConstraint("execution_id", "stage_ordinal"),
    )
    op.create_table(
        "runtime_handoffs",
        sa.Column("handoff_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "execution_id",
            sa.Uuid(),
            sa.ForeignKey("runtime_executions.execution_id"),
            nullable=False,
        ),
        sa.Column("source_stage", sa.String(16)),
        sa.Column("target_stage", sa.String(16)),
        sa.Column("contract_version", sa.String(32), nullable=False),
        sa.Column("protected_payload", sa.LargeBinary(), nullable=False),
        sa.Column("content_hash", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "runtime_artifact_references",
        sa.Column("artifact_reference_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "execution_id",
            sa.Uuid(),
            sa.ForeignKey("runtime_executions.execution_id"),
            nullable=False,
        ),
        sa.Column("stage_id", sa.Uuid(), sa.ForeignKey("runtime_stages.stage_id")),
        sa.Column("artifact_role", sa.String(40), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("source_capability", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("execution_id", "artifact_role", "artifact_id"),
    )
    op.create_table(
        "runtime_results",
        sa.Column("result_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "execution_id",
            sa.Uuid(),
            sa.ForeignKey("runtime_executions.execution_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("terminal_capability", sa.String(16)),
        sa.Column("disposition", sa.String(40), nullable=False),
        sa.Column("result_code", sa.String(100)),
        sa.Column("result_value", sa.String(200)),
        sa.Column("actionable", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "runtime_recovery_attempts",
        sa.Column("recovery_id", sa.Uuid(), primary_key=True),
        sa.Column("logical_execution_id", sa.Uuid(), nullable=False),
        sa.Column(
            "original_execution_id",
            sa.Uuid(),
            sa.ForeignKey("runtime_executions.execution_id"),
            nullable=False,
        ),
        sa.Column(
            "replay_execution_id",
            sa.Uuid(),
            sa.ForeignKey("runtime_executions.execution_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("checkpoint_stage_id", sa.Uuid(), sa.ForeignKey("runtime_stages.stage_id")),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("replay_principal_id", sa.String(200), nullable=False),
        sa.Column("original_authorization_reference", sa.String(200), nullable=False),
        sa.Column("replay_authorization_reference", sa.String(200), nullable=False),
        sa.Column("replay_reason", sa.String(1000), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "runtime_recovery_attempts",
        "runtime_results",
        "runtime_artifact_references",
        "runtime_handoffs",
        "runtime_stages",
    ):
        op.drop_table(table)
    op.drop_index("idx_runtime_executions_recovery", table_name="runtime_executions")
    op.drop_table("runtime_executions")
