"""Structurally enforce OQI4 CurrentOntologyImpact pointer tenant isolation
at the database level (CDD-055 SS12, SS13).

`current_ontology_impacts.fk_current_ontology_impacts_latest_evaluation_id`
previously carried a plain (non-tenant-qualified) foreign key to
`ontology_impact_evaluations`' globally-unique `evaluation_id` primary key
-- proving only that the referenced evaluation exists, never that it
belongs to the pointer's own tenant, discovered by OQI4-R1-DR's real-
PostgreSQL adversarial verification to let a tenant A CurrentOntologyImpact
row directly point at a tenant B-owned evaluation. Reuses the identical,
already-proven-safe migration-0041/0042/0043 (OQI6-R1/R2/R3) pattern: add a
tenant-qualified composite candidate key to the parent evaluation table,
then replace the plain child FK with a tenant-qualified composite FK.
`ontology_impact_evaluations` carries no version column, so the new
candidate key is `(tenant_id, evaluation_id)` -- two columns, matching
OQI6-R3's own non-versioned shape.

Constraint-only correction: zero new/dropped table, zero new/dropped
column, zero data rewrite, zero backfill. Governed table count remains 123
before and after. `0001`-`0043` are unmodified by this migration."""

from collections.abc import Sequence

from alembic import op

revision: str = "0044_oqi4_r1_current_tenancy"
down_revision: str | None = "0043_oqi6_r3_current_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_ontology_impact_evaluations_tenant_pk",
        "ontology_impact_evaluations",
        ["tenant_id", "evaluation_id"],
    )
    op.drop_constraint(
        "fk_current_ontology_impacts_latest_evaluation_id",
        "current_ontology_impacts",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_current_ontology_impacts_tenant_evaluation",
        "current_ontology_impacts",
        "ontology_impact_evaluations",
        ["tenant_id", "latest_evaluation_id"],
        ["tenant_id", "evaluation_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_current_ontology_impacts_tenant_evaluation",
        "current_ontology_impacts",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_current_ontology_impacts_latest_evaluation_id",
        "current_ontology_impacts",
        "ontology_impact_evaluations",
        ["latest_evaluation_id"],
        ["evaluation_id"],
    )
    op.drop_constraint(
        "uq_ontology_impact_evaluations_tenant_pk",
        "ontology_impact_evaluations",
        type_="unique",
    )
