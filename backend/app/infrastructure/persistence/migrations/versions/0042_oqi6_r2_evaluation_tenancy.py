"""Structurally enforce OQI6 BusinessImpactEvaluation->BusinessDependency
tenant isolation at the database level (CDD-053 SS9, SS13).

`oqi_business_impact_evaluations.fk_oqi_business_impact_evaluations_dependency`
previously carried a plain (non-tenant-qualified) foreign key to
`oqi_business_dependencies(dependency_id, version)` -- proving only that the
referenced dependency exists, never that it belongs to the evaluation's own
tenant, discovered by OQI6-R2-DR's real-PostgreSQL adversarial verification
to let a tenant A row directly reference a tenant B-owned BusinessDependency.
Reuses the identical, already-proven-safe migration-0038/0041 (H4-R1/OQI6-R1)
pattern: add a tenant-qualified composite candidate key to the parent table,
then replace the plain child FK with a tenant-qualified composite FK.

Constraint-only correction: zero new/dropped table, zero new/dropped
column, zero data rewrite, zero backfill. Governed table count remains 123
before and after. `0001`-`0041` are unmodified by this migration."""

from collections.abc import Sequence

from alembic import op

revision: str = "0042_oqi6_r2_evaluation_tenancy"
down_revision: str | None = "0041_oqi6_r1_dependency_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_oqi_business_dependencies_tenant_pk",
        "oqi_business_dependencies",
        ["tenant_id", "dependency_id", "version"],
    )
    op.drop_constraint(
        "fk_oqi_business_impact_evaluations_dependency",
        "oqi_business_impact_evaluations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_business_impact_evaluations_tenant_dependency",
        "oqi_business_impact_evaluations",
        "oqi_business_dependencies",
        ["tenant_id", "business_dependency_id", "business_dependency_version"],
        ["tenant_id", "dependency_id", "version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_oqi_business_impact_evaluations_tenant_dependency",
        "oqi_business_impact_evaluations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_business_impact_evaluations_dependency",
        "oqi_business_impact_evaluations",
        "oqi_business_dependencies",
        ["business_dependency_id", "business_dependency_version"],
        ["dependency_id", "version"],
    )
    op.drop_constraint(
        "uq_oqi_business_dependencies_tenant_pk", "oqi_business_dependencies", type_="unique"
    )
