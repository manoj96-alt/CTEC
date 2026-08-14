"""Add tenant ownership to the identity-resolution substrate and extend
Enterprise Entity Resolution records with multi-attribute evidence, a
tenant-owned policy reference, and steward-authorship fields.

Tenant ownership rationale: source_systems, source_objects, and
enterprise_entities hold per-customer instance data but carry no ownership
column in the released ECOM Physical Data Model (v1.3 through v1.5). The
Entity Resolution Steward workspace is the first surface that discloses this
content directly to an authenticated caller, so this migration establishes
the smallest coherent ownership boundary: an opaque `tenant_id` column
(mirroring the existing `runtime_executions.tenant_id` precedent), not the
unrelated `enterprises` governance table. Reference/taxonomy tables
(entity_types, institutional_concepts, relationship_types, business_domains,
enterprises) are intentionally left unscoped.

Database-enforced isolation: filtering alone is not trusted. Every
relationship between tenant-owned rows is tenant-qualified at the database
level via composite unique constraints (tenant_id, primary_key) on the
referenced side and composite foreign keys (tenant_id, reference_column) on
the referencing side, so a cross-tenant reference is structurally rejected
even if application code contains a defect:

  source_objects(tenant_id, source_system_id)
    -> source_systems(tenant_id, source_system_id)
  enterprise_entity_resolution_records(tenant_id, enterprise_entity_id)
    -> enterprise_entities(tenant_id, enterprise_entity_id)
  enterprise_entity_resolution_records(tenant_id, policy_id)
    -> resolution_policies(tenant_id, policy_id)
  enterprise_entity_resolution_history(tenant_id, active_record_id)
    -> enterprise_entity_resolution_records(tenant_id, record_id)

Known, disclosed limitation: `supporting_source_object_ids` on
enterprise_entity_resolution_records and `archived_record_ids` on
enterprise_entity_resolution_history are pre-existing JSON arrays (added in
0002, predating this increment), not relational columns. PostgreSQL cannot
express a foreign key against elements of a JSON array, so tenant
consistency for those specific fields is enforced at the application
boundary (EntityResolutionStore validates every referenced id against the
record's own tenant before insert) and proven by test, not by a database
constraint. Every reference newly introduced by this increment (source
system, enterprise entity, policy, history-to-record) is a real column and
does get a database-enforced composite foreign key.

resolution_policies.tenant_id is always a real tenant id, never a shared
"platform" sentinel: Conservative/Balanced/Exploratory exist as in-code
templates (app.domain.identity_resolution.policy) and are materialized as
tenant-owned rows on first use, so a normal resolution record's composite
foreign key can only ever point at a policy version owned by its own
tenant.

Existing-row backfill: all pre-migration rows are labeled with
BOOTSTRAP_DEMO_TENANT_ID ("ctec-demo-tenant") as an explicit, one-time,
single-tenant demo-data compatibility backfill (EDT-001 seed content; no
production EnterpriseEntity/resolution rows exist prior to this migration).
This is applied via a column DEFAULT on ADD COLUMN, which PostgreSQL
resolves without rewriting rows and without invoking the
enterprise_entity_resolution_records immutability trigger (ADD COLUMN is
DDL, not an UPDATE). Every default is dropped immediately after backfill:
BOOTSTRAP_DEMO_TENANT_ID is never used as an application-level or runtime
fallback, and every future insert must supply tenant_id explicitly from the
trusted authority boundary.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID

revision: str = "0011_erm_tenant_and_evidence"
down_revision: str | None = "0010_ontology_bindings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_backfilled_tenant_column(table: str) -> None:
    op.add_column(
        table,
        sa.Column(
            "tenant_id", sa.String(200), nullable=False, server_default=BOOTSTRAP_DEMO_TENANT_ID
        ),
    )
    op.alter_column(table, "tenant_id", server_default=None)


def upgrade() -> None:
    # ---- 1. Backfill tenant_id onto existing instance-data tables ----
    _add_backfilled_tenant_column("source_systems")
    _add_backfilled_tenant_column("source_objects")
    _add_backfilled_tenant_column("enterprise_entities")
    _add_backfilled_tenant_column("enterprise_entity_resolution_records")
    _add_backfilled_tenant_column("enterprise_entity_resolution_history")

    # ---- 1b. Standalone tenant_id indexes matching physical model v1.6 ----
    op.create_index("idx_source_systems_tenant_id", "source_systems", ["tenant_id"])
    op.create_index("idx_source_objects_tenant_id", "source_objects", ["tenant_id"])
    op.create_index("idx_enterprise_entities_tenant_id", "enterprise_entities", ["tenant_id"])

    # ---- 2. New tenant-owned resolution_policies table ----
    op.create_table(
        "resolution_policies",
        sa.Column(
            "policy_id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("policy_name", sa.String(100), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("preset_kind", sa.String(32), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "policy_name", "policy_version", name="uq_resolution_policies_identity"
        ),
        sa.UniqueConstraint("tenant_id", "policy_id", name="uq_resolution_policies_tenant_pk"),
    )

    # ---- 3. Composite-unique the referenced side of every FK we add ----
    op.create_unique_constraint(
        "uq_enterprise_entities_tenant_pk",
        "enterprise_entities",
        ["tenant_id", "enterprise_entity_id"],
    )
    op.create_unique_constraint(
        "uq_source_systems_tenant_pk", "source_systems", ["tenant_id", "source_system_id"]
    )
    op.create_unique_constraint(
        "uq_eer_records_tenant_pk",
        "enterprise_entity_resolution_records",
        ["tenant_id", "record_id"],
    )

    # ---- 4. Replace global-unique business names with tenant-scoped ones ----
    op.drop_constraint(
        "enterprise_entities_enterprise_entity_name_key", "enterprise_entities", type_="unique"
    )
    op.create_unique_constraint(
        "uq_enterprise_entities_tenant_name",
        "enterprise_entities",
        ["tenant_id", "enterprise_entity_name"],
    )
    op.drop_constraint("source_systems_source_system_name_key", "source_systems", type_="unique")
    op.create_unique_constraint(
        "uq_source_systems_tenant_name", "source_systems", ["tenant_id", "source_system_name"]
    )
    op.drop_constraint("source_objects_source_object_name_key", "source_objects", type_="unique")
    op.create_unique_constraint(
        "uq_source_objects_tenant_name", "source_objects", ["tenant_id", "source_object_name"]
    )

    # ---- 5. New columns on enterprise_entity_resolution_records ----
    op.add_column(
        "enterprise_entity_resolution_records",
        sa.Column("evidence_profile", sa.JSON(), nullable=True),
    )
    op.add_column(
        "enterprise_entity_resolution_records", sa.Column("policy_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "enterprise_entity_resolution_records",
        sa.Column("actor_id", sa.String(200), nullable=True),
    )
    op.add_column(
        "enterprise_entity_resolution_records",
        sa.Column("decision_rationale", sa.String(2000), nullable=True),
    )

    # ---- 6. Replace single-column FKs with tenant-qualified composite FKs ----
    op.drop_constraint("fk_source_objects_source_system_id", "source_objects", type_="foreignkey")
    op.create_foreign_key(
        "fk_source_objects_tenant_source_system",
        "source_objects",
        "source_systems",
        ["tenant_id", "source_system_id"],
        ["tenant_id", "source_system_id"],
    )

    op.drop_constraint(
        "enterprise_entity_resolution_records_enterprise_entity_id_fkey",
        "enterprise_entity_resolution_records",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_eer_records_tenant_enterprise_entity",
        "enterprise_entity_resolution_records",
        "enterprise_entities",
        ["tenant_id", "enterprise_entity_id"],
        ["tenant_id", "enterprise_entity_id"],
    )
    op.create_foreign_key(
        "fk_eer_records_tenant_policy",
        "enterprise_entity_resolution_records",
        "resolution_policies",
        ["tenant_id", "policy_id"],
        ["tenant_id", "policy_id"],
    )

    op.drop_constraint(
        "enterprise_entity_resolution_history_active_record_id_fkey",
        "enterprise_entity_resolution_history",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_eer_history_tenant_active_record",
        "enterprise_entity_resolution_history",
        "enterprise_entity_resolution_records",
        ["tenant_id", "active_record_id"],
        ["tenant_id", "record_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_eer_history_tenant_active_record",
        "enterprise_entity_resolution_history",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "enterprise_entity_resolution_history_active_record_id_fkey",
        "enterprise_entity_resolution_history",
        "enterprise_entity_resolution_records",
        ["active_record_id"],
        ["record_id"],
    )

    op.drop_constraint(
        "fk_eer_records_tenant_policy",
        "enterprise_entity_resolution_records",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_eer_records_tenant_enterprise_entity",
        "enterprise_entity_resolution_records",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "enterprise_entity_resolution_records_enterprise_entity_id_fkey",
        "enterprise_entity_resolution_records",
        "enterprise_entities",
        ["enterprise_entity_id"],
        ["enterprise_entity_id"],
    )

    op.drop_constraint(
        "fk_source_objects_tenant_source_system", "source_objects", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_source_objects_source_system_id",
        "source_objects",
        "source_systems",
        ["source_system_id"],
        ["source_system_id"],
    )

    op.drop_column("enterprise_entity_resolution_records", "decision_rationale")
    op.drop_column("enterprise_entity_resolution_records", "actor_id")
    op.drop_column("enterprise_entity_resolution_records", "policy_id")
    op.drop_column("enterprise_entity_resolution_records", "evidence_profile")

    op.drop_constraint("uq_source_objects_tenant_name", "source_objects", type_="unique")
    op.create_unique_constraint(
        "source_objects_source_object_name_key", "source_objects", ["source_object_name"]
    )
    op.drop_constraint("uq_source_systems_tenant_name", "source_systems", type_="unique")
    op.create_unique_constraint(
        "source_systems_source_system_name_key", "source_systems", ["source_system_name"]
    )
    op.drop_constraint("uq_enterprise_entities_tenant_name", "enterprise_entities", type_="unique")
    op.create_unique_constraint(
        "enterprise_entities_enterprise_entity_name_key",
        "enterprise_entities",
        ["enterprise_entity_name"],
    )

    op.drop_constraint(
        "uq_eer_records_tenant_pk", "enterprise_entity_resolution_records", type_="unique"
    )
    op.drop_constraint("uq_source_systems_tenant_pk", "source_systems", type_="unique")
    op.drop_constraint("uq_enterprise_entities_tenant_pk", "enterprise_entities", type_="unique")

    op.drop_table("resolution_policies")

    op.drop_index("idx_enterprise_entities_tenant_id", table_name="enterprise_entities")
    op.drop_index("idx_source_objects_tenant_id", table_name="source_objects")
    op.drop_index("idx_source_systems_tenant_id", table_name="source_systems")

    op.drop_column("enterprise_entity_resolution_history", "tenant_id")
    op.drop_column("enterprise_entity_resolution_records", "tenant_id")
    op.drop_column("enterprise_entities", "tenant_id")
    op.drop_column("source_objects", "tenant_id")
    op.drop_column("source_systems", "tenant_id")
