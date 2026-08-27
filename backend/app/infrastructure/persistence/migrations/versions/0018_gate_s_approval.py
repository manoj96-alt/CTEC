"""Create Gate S `gate_s_approval_requests` and `gate_s_governed_notes`
persistence (Gate S; CDD-036 §19, §35; Gate S Artifact Authorization §4).

Two new, non-canonical tables. `gate_s_approval_requests` carries the
approval workflow record (tenant-scoped, digest-bound, one-time
consumption tracking via `consumed_on`/`consumed_execution_id`).
`gate_s_governed_notes` is the append-only consequential-action ledger,
written exclusively by `GateSApprovalService.execute()` -- no other code
path constructs a row here (CDD-036 §21-§22). `requested_by`/`decided_by`/
`created_by` are plain strings, no FK -- following
`ontology_change_proposals`' own provenance-field convention. No existing
table is added to, altered, or dropped by this migration."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_gate_s_approval"
down_revision: str | None = "0017_ontology_change_proposal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gate_s_approval_requests",
        sa.Column(
            "approval_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("action_id", sa.String(200), nullable=False),
        sa.Column("note_text", sa.String(500), nullable=False),
        sa.Column("action_input_digest", sa.String(64), nullable=False),
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
        "idx_gate_s_approval_requests_tenant_id", "gate_s_approval_requests", ["tenant_id"]
    )
    op.create_index("idx_gate_s_approval_requests_status", "gate_s_approval_requests", ["status"])
    op.create_index(
        "idx_gate_s_approval_requests_requested_by",
        "gate_s_approval_requests",
        ["requested_by"],
    )

    op.create_table(
        "gate_s_governed_notes",
        sa.Column(
            "governed_note_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "approval_id",
            sa.Uuid(),
            sa.ForeignKey(
                "gate_s_approval_requests.approval_id",
                name="fk_gate_s_governed_notes_approval_id",
            ),
            nullable=False,
        ),
        sa.Column("note_text", sa.String(500), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_gate_s_governed_notes_tenant_id", "gate_s_governed_notes", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("idx_gate_s_governed_notes_tenant_id", table_name="gate_s_governed_notes")
    op.drop_table("gate_s_governed_notes")
    op.drop_index(
        "idx_gate_s_approval_requests_requested_by", table_name="gate_s_approval_requests"
    )
    op.drop_index("idx_gate_s_approval_requests_status", table_name="gate_s_approval_requests")
    op.drop_index("idx_gate_s_approval_requests_tenant_id", table_name="gate_s_approval_requests")
    op.drop_table("gate_s_approval_requests")
