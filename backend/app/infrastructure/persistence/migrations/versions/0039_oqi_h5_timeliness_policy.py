"""Create OQI-H5 governed Timeliness policy persistence (CDD-051 §8, §9,
§28; Artifact Authorization row 8).

One table: `oqi_timeliness_policies` -- the versioned, tenant-owned
Timeliness policy anchored to `(information_element_requirement_id,
business_process_id, business_process_version)`. A PostgreSQL partial
unique index enforces exactly one `ACTIVE` policy per exact anchor tuple.

Also corrects a narrow, pre-existing, disclosed OQI6 tenant-isolation gap
(CDD-051 §9): `oqi_business_processes` carried `tenant_id` but no
`UNIQUE(tenant_id, process_id, version)` composite candidate key, so its
existing consumer (`oqi_business_dependencies`) has always used a plain,
non-tenant-qualified composite FK on `(process_id, version)` -- the
identical defect class H4-R1 corrected elsewhere. This migration adds ONLY
the additive parent-side constraint, required so `oqi_timeliness_policies`
can compose a proper tenant-qualified FK; it is safe by construction and
requires no data backfill, since `(process_id, version)` is already that
table's primary key, making `(tenant_id, process_id, version)` trivially
unique as a superset of an already-unique key. `oqi_business_dependencies`'
own existing FK is explicitly NOT corrected here (CDD-051 §9 -- out of H5
scope, recommended as a future, separately-governed OQI6-R1)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0039_oqi_h5_timeliness_policy"
down_revision: str | None = "0038_oqi_h4_reference_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # CDD-051 §9: additive-only parent-side correction. Safe without a
    # duplicate-data precondition check: (process_id, version) is already
    # this table's primary key, so (tenant_id, process_id, version) is
    # trivially unique as a superset of an already-unique key.
    op.create_unique_constraint(
        "uq_oqi_business_processes_tenant_pk",
        "oqi_business_processes",
        ["tenant_id", "process_id", "version"],
    )

    op.create_table(
        "oqi_timeliness_policies",
        sa.Column("policy_id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column(
            "information_element_requirement_id",
            sa.Uuid(),
            sa.ForeignKey(
                "information_element_requirements.information_element_requirement_id",
                name="fk_oqi_timeliness_policies_information_element_requirement_id",
            ),
            nullable=False,
        ),
        sa.Column("business_process_id", sa.Uuid(), nullable=False),
        sa.Column("business_process_version", sa.Integer(), nullable=False),
        sa.Column("freshness_window_seconds", sa.Integer(), nullable=True),
        sa.Column("ingestion_sla_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "policy_id", "version", name="uq_oqi_timeliness_policies_tenant_pk"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "business_process_id", "business_process_version"],
            [
                "oqi_business_processes.tenant_id",
                "oqi_business_processes.process_id",
                "oqi_business_processes.version",
            ],
            name="fk_oqi_timeliness_policies_tenant_business_process",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_timeliness_policies_status"
        ),
        sa.CheckConstraint(
            "freshness_window_seconds IS NULL OR freshness_window_seconds > 0",
            name="ck_oqi_timeliness_policies_freshness_positive",
        ),
        sa.CheckConstraint(
            "ingestion_sla_seconds IS NULL OR ingestion_sla_seconds > 0",
            name="ck_oqi_timeliness_policies_ingestion_sla_positive",
        ),
        sa.CheckConstraint(
            "freshness_window_seconds IS NOT NULL OR ingestion_sla_seconds IS NOT NULL",
            name="ck_oqi_timeliness_policies_at_least_one_threshold",
        ),
    )
    op.create_index(
        "idx_oqi_timeliness_policies_tenant_id", "oqi_timeliness_policies", ["tenant_id"]
    )
    op.create_index(
        "idx_oqi_timeliness_policies_anchor",
        "oqi_timeliness_policies",
        ["tenant_id", "information_element_requirement_id", "business_process_id"],
    )
    op.create_index(
        "uq_oqi_timeliness_policies_one_active_per_anchor",
        "oqi_timeliness_policies",
        [
            "tenant_id",
            "information_element_requirement_id",
            "business_process_id",
            "business_process_version",
        ],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_table("oqi_timeliness_policies")
    op.drop_constraint(
        "uq_oqi_business_processes_tenant_pk", "oqi_business_processes", type_="unique"
    )
