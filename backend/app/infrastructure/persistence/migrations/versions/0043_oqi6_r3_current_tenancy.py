"""Structurally enforce OQI6 Current* pointer tenant isolation at the
database level (CDD-054 SS14, SS15).

`current_business_impacts.fk_current_business_impacts_latest_evaluation_id`
and `current_reliance.fk_current_reliance_latest_evaluation_id` previously
carried plain (non-tenant-qualified) foreign keys to their respective
evaluation ledgers' globally-unique `evaluation_id` primary keys -- proving
only that the referenced evaluation exists, never that it belongs to the
pointer's own tenant, discovered by OQI6-R3-DR's real-PostgreSQL adversarial
verification to let a tenant A Current* row directly point at a tenant
B-owned evaluation. Reuses the identical, already-proven-safe migration-
0041/0042 (OQI6-R1/R2) pattern: add a tenant-qualified composite candidate
key to each parent evaluation table, then replace the plain child FK with a
tenant-qualified composite FK. Neither evaluation table carries a version
column, so each new candidate key is `(tenant_id, evaluation_id)` -- two
columns, not the three-column `(tenant_id, id, version)` shape used by
OQI6-R1/R2's own BusinessProcess/BusinessDependency correction.

Constraint-only correction: zero new/dropped table, zero new/dropped
column, zero data rewrite, zero backfill. Governed table count remains 123
before and after. `0001`-`0042` are unmodified by this migration."""

from collections.abc import Sequence

from alembic import op

revision: str = "0043_oqi6_r3_current_tenancy"
down_revision: str | None = "0042_oqi6_r2_evaluation_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_oqi_business_impact_evaluations_tenant_pk",
        "oqi_business_impact_evaluations",
        ["tenant_id", "evaluation_id"],
    )
    op.create_unique_constraint(
        "uq_oqi_reliance_evaluations_tenant_pk",
        "oqi_reliance_evaluations",
        ["tenant_id", "evaluation_id"],
    )
    op.drop_constraint(
        "fk_current_business_impacts_latest_evaluation_id",
        "current_business_impacts",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_current_business_impacts_tenant_evaluation",
        "current_business_impacts",
        "oqi_business_impact_evaluations",
        ["tenant_id", "latest_evaluation_id"],
        ["tenant_id", "evaluation_id"],
    )
    op.drop_constraint(
        "fk_current_reliance_latest_evaluation_id",
        "current_reliance",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_current_reliance_tenant_evaluation",
        "current_reliance",
        "oqi_reliance_evaluations",
        ["tenant_id", "latest_evaluation_id"],
        ["tenant_id", "evaluation_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_current_reliance_tenant_evaluation",
        "current_reliance",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_current_reliance_latest_evaluation_id",
        "current_reliance",
        "oqi_reliance_evaluations",
        ["latest_evaluation_id"],
        ["evaluation_id"],
    )
    op.drop_constraint(
        "fk_current_business_impacts_tenant_evaluation",
        "current_business_impacts",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_current_business_impacts_latest_evaluation_id",
        "current_business_impacts",
        "oqi_business_impact_evaluations",
        ["latest_evaluation_id"],
        ["evaluation_id"],
    )
    op.drop_constraint(
        "uq_oqi_reliance_evaluations_tenant_pk", "oqi_reliance_evaluations", type_="unique"
    )
    op.drop_constraint(
        "uq_oqi_business_impact_evaluations_tenant_pk",
        "oqi_business_impact_evaluations",
        type_="unique",
    )
