"""Create Production Governed Enterprise REST Ingestion persistence
(CDD-059 §12-§14, §40; Artifact Authorization row 7).

Three new tables: `oqi_connector_configurations`,
`oqi_connector_field_mappings`, `oqi_connector_runs`.

No existing table is altered. Every tenant-owned table here is
structurally tenant-isolated from this, its first migration, via a
composite tenant-qualified foreign key into its own tenant-owned parent
-- `oqi_connector_configurations` into `source_systems`,
`oqi_connector_field_mappings`/`oqi_connector_runs` into
`oqi_connector_configurations` -- mirroring
`fk_source_objects_tenant_source_system`'s own established-correct
precedent (CDD-059 §40)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0045_oqi_connector_ingestion"
down_revision: str | None = "0044_oqi4_r1_current_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oqi_connector_configurations",
        sa.Column("connector_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("source_system_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("connector_type", sa.String(32), nullable=False),
        sa.Column("endpoint_url", sa.String(2000), nullable=False),
        sa.Column("auth_mechanism", sa.String(32), nullable=False),
        sa.Column("auth_header_name", sa.String(200), nullable=True),
        sa.Column("credential_env_var_name", sa.String(200), nullable=False),
        sa.Column("pagination_style", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_by", sa.String(200), nullable=True),
        sa.Column("modified_on", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "tenant_id",
            "connector_id",
            name="uq_oqi_connector_configurations_tenant_pk",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_system_id"],
            ["source_systems.tenant_id", "source_systems.source_system_id"],
            name="fk_oqi_connector_configurations_tenant_source_system",
        ),
    )
    op.create_index(
        "idx_oqi_connector_configurations_tenant_id",
        "oqi_connector_configurations",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_connector_configurations_source_system_id",
        "oqi_connector_configurations",
        ["source_system_id"],
    )
    op.create_index(
        "idx_oqi_connector_configurations_status", "oqi_connector_configurations", ["status"]
    )

    op.create_table(
        "oqi_connector_field_mappings",
        sa.Column("mapping_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("external_field_path", sa.String(500), nullable=False),
        sa.Column("source_field_id", sa.Uuid(), nullable=False),
        sa.Column(
            "is_external_record_id",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "mapping_id",
            name="uq_oqi_connector_field_mappings_tenant_pk",
        ),
        sa.UniqueConstraint(
            "connector_id",
            "external_field_path",
            name="uq_oqi_connector_field_mappings_connector_path",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connector_id"],
            [
                "oqi_connector_configurations.tenant_id",
                "oqi_connector_configurations.connector_id",
            ],
            name="fk_oqi_connector_field_mappings_tenant_connector",
        ),
    )
    op.create_index(
        "idx_oqi_connector_field_mappings_tenant_id", "oqi_connector_field_mappings", ["tenant_id"]
    )
    op.create_index(
        "idx_oqi_connector_field_mappings_connector_id",
        "oqi_connector_field_mappings",
        ["connector_id"],
    )
    # CDD-059 §13: at most one mapping per connector may designate the
    # external-record-identity path -- a partial unique index.
    op.create_index(
        "uq_oqi_connector_field_mappings_one_record_id_per_connector",
        "oqi_connector_field_mappings",
        ["connector_id"],
        unique=True,
        postgresql_where=sa.text("is_external_record_id"),
    )

    op.create_table(
        "oqi_connector_runs",
        sa.Column("run_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkpoint_page_token", sa.String(2000), nullable=True),
        sa.Column("fetched_records", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("accepted_records", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rejected_records", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duplicate_records", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("evidence_written", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failure_kind", sa.String(40), nullable=True),
        sa.Column("failure_summary", sa.String(500), nullable=True),
        sa.Column("triggered_by", sa.String(200), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "run_id",
            name="uq_oqi_connector_runs_tenant_pk",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "connector_id"],
            [
                "oqi_connector_configurations.tenant_id",
                "oqi_connector_configurations.connector_id",
            ],
            name="fk_oqi_connector_runs_tenant_connector",
        ),
    )
    op.create_index("idx_oqi_connector_runs_tenant_id", "oqi_connector_runs", ["tenant_id"])
    op.create_index(
        "idx_oqi_connector_runs_connector_id_status",
        "oqi_connector_runs",
        ["connector_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("oqi_connector_runs")
    op.drop_table("oqi_connector_field_mappings")
    op.drop_table("oqi_connector_configurations")
