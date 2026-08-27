"""Create Gate V `gate_v_agent_resolutions` persistence (Gate V; CDD-037
§15, §16; Gate V Artifact Authorization §4).

One new table. Insert-only -- no update/delete lifecycle exists for a
resolution (CDD-037 §13, §22). `approval_id` is a nullable foreign key
referencing Gate S's existing `gate_s_approval_requests.approval_id`; this
migration does not add to, alter, or drop that table, or any other existing
table."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_gate_v_agent_resolution"
down_revision: str | None = "0018_gate_s_approval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gate_v_agent_resolutions",
        sa.Column(
            "resolution_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("agent_id", sa.String(200), nullable=False),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("observation_text", sa.String(500), nullable=False),
        sa.Column("priority_score", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column(
            "approval_id",
            sa.Uuid(),
            sa.ForeignKey(
                "gate_s_approval_requests.approval_id",
                name="fk_gate_v_agent_resolutions_approval_id",
            ),
            nullable=True,
        ),
        sa.Column("resolved_on", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_gate_v_agent_resolutions_tenant_id", "gate_v_agent_resolutions", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_gate_v_agent_resolutions_tenant_id", table_name="gate_v_agent_resolutions")
    op.drop_table("gate_v_agent_resolutions")
