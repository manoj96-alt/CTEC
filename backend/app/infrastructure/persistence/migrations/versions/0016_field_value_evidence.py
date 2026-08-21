"""Create Governed Source Field-Value Evidence persistence (CDD-022 §6, §15;
Field-Value Evidence Artifact Authorization).

Adds `field_value_evidence` (references `source_fields.source_field_id`;
global identity, deterministically application-supplied -- CDD-022 §6, §25;
no `tenant_id`, no `source_object_id`, no `source_system_id` column --
CDD-022 §7). `field_value_evidence_id` carries no compound uniqueness
constraint beyond its own primary key: because it is itself deterministically
equivalent to the four governed semantic identity inputs (`source_field_id`,
`source_record_reference`, `observed_representation`, `observed_at`), the
primary key alone enforces both identical-replay collision and legitimate
multi-observation coexistence (CDD-022 §6). No lifecycle/governance-status
column -- this is an immutable, append-only fact, not a governed-vocabulary
entity (CDD-022 §14). No Blueprint/SemanticMapping/H4 schema.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_field_value_evidence"
down_revision: str | None = "0015_source_field_semantic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "field_value_evidence",
        sa.Column(
            "field_value_evidence_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_fields.source_field_id", name="fk_field_value_evidence_source_field_id"
            ),
            nullable=False,
        ),
        sa.Column("source_record_reference", sa.String(1000), nullable=False),
        sa.Column("observed_representation", sa.String(1000), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_reference", sa.String(1000), nullable=True),
    )
    op.create_index(
        "idx_field_value_evidence_source_field_id",
        "field_value_evidence",
        ["source_field_id"],
    )
    op.create_index("idx_field_value_evidence_observed_at", "field_value_evidence", ["observed_at"])
    op.create_index("idx_field_value_evidence_received_at", "field_value_evidence", ["received_at"])


def downgrade() -> None:
    op.drop_index("idx_field_value_evidence_received_at", table_name="field_value_evidence")
    op.drop_index("idx_field_value_evidence_observed_at", table_name="field_value_evidence")
    op.drop_index("idx_field_value_evidence_source_field_id", table_name="field_value_evidence")
    op.drop_table("field_value_evidence")
