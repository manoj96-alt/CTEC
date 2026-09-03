"""Structurally enforce OQI6 BusinessDependency->BusinessProcess tenant
isolation at the database level (CDD-052 SS6, SS13).

`oqi_business_dependencies.fk_oqi_business_dependencies_process` previously
carried a plain (non-tenant-qualified) foreign key to
`oqi_business_processes(process_id, version)` -- proving only that the
referenced process exists, never that it belongs to the dependency's own
tenant, discovered by OQI6-R1-DR's real-PostgreSQL adversarial verification
to let a tenant A row directly reference a tenant B-owned BusinessProcess.
Reuses the identical, already-proven-safe migration-0038 (H4-R1) pattern:
replace the plain child FK with a tenant-qualified composite FK against an
already-existing tenant-qualified parent candidate key
(`uq_oqi_business_processes_tenant_pk`, added by migration 0039 for H5
Timeliness, reused here unmodified -- not recreated, not altered).

Constraint-only correction: zero new/dropped table, zero new/dropped
column, zero data rewrite, zero backfill. Governed table count remains 123
before and after. `0001`-`0040` are unmodified by this migration."""

from collections.abc import Sequence

from alembic import op

revision: str = "0041_oqi6_r1_dependency_tenancy"
down_revision: str | None = "0040_oqi_h5_timeliness_eval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_oqi_business_dependencies_process",
        "oqi_business_dependencies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_business_dependencies_tenant_process",
        "oqi_business_dependencies",
        "oqi_business_processes",
        ["tenant_id", "business_process_id", "business_process_version"],
        ["tenant_id", "process_id", "version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_oqi_business_dependencies_tenant_process",
        "oqi_business_dependencies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_business_dependencies_process",
        "oqi_business_dependencies",
        "oqi_business_processes",
        ["business_process_id", "business_process_version"],
        ["process_id", "version"],
    )
