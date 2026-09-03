"""Structurally enforce OQI-H4 Reference Integrity tenant isolation at the
database level (CDD-050 SS12/SS27; CDD-050-Artifact-Authorization-H4-R1-
Reference-Tenant-Isolation-Correction-Amendment.md SS9-SS10).

`oqi_integrity_reference_evaluations.source_object_id`,
`oqi_integrity_reference_evaluations.resolution_record_id`, and
`oqi_integrity_reference_findings.source_object_id` previously carried plain
(non-tenant-qualified) foreign keys, discovered by OQI-H4-VM's real-
PostgreSQL adversarial verification to let a tenant A row directly reference
a tenant B-owned `SourceObject`/resolution record. `source_objects` lacked
the tenant-qualified candidate key required for a composite FK
(`UNIQUE(tenant_id, source_object_id)`, added here as
`uq_source_objects_tenant_pk`); `enterprise_entity_resolution_records`
already carries one (`uq_eer_records_tenant_pk`, added by migration `0011`),
reused unmodified. Reuses the identical, already-proven-safe RFC-016/
migration-`0011` pattern: add the missing parent candidate key, then replace
each single-column child FK with a tenant-qualified composite FK.

Constraint-only correction: zero new/dropped table, zero new/dropped column,
zero data rewrite, zero backfill. Governed table count remains 120 before and
after. `0034`-`0037` are unmodified by this migration."""

from collections.abc import Sequence

from alembic import op

revision: str = "0038_oqi_h4_reference_tenancy"
down_revision: str | None = "0037_oqi_h4_impact_width"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_source_objects_tenant_pk",
        "source_objects",
        ["tenant_id", "source_object_id"],
    )

    op.drop_constraint(
        "fk_oqi_integrity_reference_evaluations_source_object_id",
        "oqi_integrity_reference_evaluations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_integrity_ref_eval_tenant_source_object",
        "oqi_integrity_reference_evaluations",
        "source_objects",
        ["tenant_id", "source_object_id"],
        ["tenant_id", "source_object_id"],
    )

    op.drop_constraint(
        "fk_oqi_integrity_reference_evaluations_resolution_record_id",
        "oqi_integrity_reference_evaluations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_integrity_ref_eval_tenant_resolution_record",
        "oqi_integrity_reference_evaluations",
        "enterprise_entity_resolution_records",
        ["tenant_id", "resolution_record_id"],
        ["tenant_id", "record_id"],
    )

    op.drop_constraint(
        "fk_oqi_integrity_reference_findings_source_object_id",
        "oqi_integrity_reference_findings",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_integrity_ref_finding_tenant_source_object",
        "oqi_integrity_reference_findings",
        "source_objects",
        ["tenant_id", "source_object_id"],
        ["tenant_id", "source_object_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_oqi_integrity_ref_finding_tenant_source_object",
        "oqi_integrity_reference_findings",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_integrity_reference_findings_source_object_id",
        "oqi_integrity_reference_findings",
        "source_objects",
        ["source_object_id"],
        ["source_object_id"],
    )

    op.drop_constraint(
        "fk_oqi_integrity_ref_eval_tenant_resolution_record",
        "oqi_integrity_reference_evaluations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_integrity_reference_evaluations_resolution_record_id",
        "oqi_integrity_reference_evaluations",
        "enterprise_entity_resolution_records",
        ["resolution_record_id"],
        ["record_id"],
    )

    op.drop_constraint(
        "fk_oqi_integrity_ref_eval_tenant_source_object",
        "oqi_integrity_reference_evaluations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_integrity_reference_evaluations_source_object_id",
        "oqi_integrity_reference_evaluations",
        "source_objects",
        ["source_object_id"],
        ["source_object_id"],
    )

    op.drop_constraint("uq_source_objects_tenant_pk", "source_objects", type_="unique")
