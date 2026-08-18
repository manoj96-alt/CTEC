"""Add Decision Evaluation group persistence (Gate F F-I1 / CDD-015 §16, §33).

Adds `decision_evaluations`: the stable identity of one governed decision
evaluation whose result may require multiple persisted decision records
(CDD-015 §16 item 1). Carries direct, DB-constrained `tenant_id` (following
the `institutional_relationships`/`runtime_executions` precedent for tables
that own their own tenant scoping from the start, per Gate F F2.2/F4/F5
architecture) and an optional, non-FK `logical_execution_id` audit-trail
column (Gate F F5 §8 recommendation: `runtime_executions.logical_execution_id`
is not this row's primary key and carries its own 7-year retention/purge
lifecycle, so it is deliberately not referenced by a foreign key here --
see CDD-015 §20 and the Gate F F5 report §8 for the full evidentiary basis).

Adds a nullable `decision_evaluation_records.decision_evaluation_id` foreign
key so existing (CDD-011) rows remain valid unchanged (CDD-015 §16 item 2,
§33 exclusions: "No NOT NULL retrofit of existing rows"). No column is added
to `governance_evaluation_records` -- its existing polymorphic
`governed_record_reference`/`governed_record_type` columns already support
referencing a `decision_evaluations` row (CDD-015 §16 item 5).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_decision_evaluation_group"
down_revision: str | None = "0012_ir_tenant_ownership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_evaluations",
        sa.Column("decision_evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("logical_execution_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_decision_evaluations_tenant_id",
        "decision_evaluations",
        ["tenant_id"],
    )
    op.add_column(
        "decision_evaluation_records",
        sa.Column("decision_evaluation_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_decision_evaluation_records_decision_evaluation_id",
        "decision_evaluation_records",
        "decision_evaluations",
        ["decision_evaluation_id"],
        ["decision_evaluation_id"],
    )
    op.create_index(
        "idx_decision_evaluation_records_decision_evaluation_id",
        "decision_evaluation_records",
        ["decision_evaluation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_decision_evaluation_records_decision_evaluation_id",
        table_name="decision_evaluation_records",
    )
    op.drop_constraint(
        "fk_decision_evaluation_records_decision_evaluation_id",
        "decision_evaluation_records",
        type_="foreignkey",
    )
    op.drop_column("decision_evaluation_records", "decision_evaluation_id")
    op.drop_index("idx_decision_evaluations_tenant_id", table_name="decision_evaluations")
    op.drop_table("decision_evaluations")
