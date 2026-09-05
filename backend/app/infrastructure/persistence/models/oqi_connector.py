"""ORM models for Production Governed Enterprise REST Ingestion (CDD-059
SS12-SS14, SS40; Artifact Authorization row 5). Three tables:
`oqi_connector_configurations`, `oqi_connector_field_mappings`,
`oqi_connector_runs`. No existing table is altered. Every tenant-owned
table here is structurally tenant-isolated from this, its first
migration, via a composite tenant-qualified FK into its own tenant-owned
parent -- mirroring `fk_source_objects_tenant_source_system`'s own
established-correct precedent, never the single-column-FK mistake OQI4/
OQI6 later had to retroactively correct (CDD-059 SS40). `source_field_id`
on `OqiConnectorFieldMappingORM` carries no structural FK-level tenant
proof because `source_fields` itself deliberately carries no `tenant_id`
column (CDD-019/CDD-022) -- tenant ownership of a mapping's target
SourceField is proven exclusively at the application layer (CDD-059
SS39), documented here as the honest limit of what this schema can
structurally enforce without modifying `source_fields` (out of scope,
CDD-059 SS5)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class OqiConnectorConfigurationORM(BaseEntity):
    __tablename__ = "oqi_connector_configurations"

    __table_args__ = (
        Index("idx_oqi_connector_configurations_tenant_id", "tenant_id"),
        Index("idx_oqi_connector_configurations_source_system_id", "source_system_id"),
        Index("idx_oqi_connector_configurations_status", "status"),
        UniqueConstraint(
            "tenant_id",
            "connector_id",
            name="uq_oqi_connector_configurations_tenant_pk",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "source_system_id"],
            ["source_systems.tenant_id", "source_systems.source_system_id"],
            name="fk_oqi_connector_configurations_tenant_source_system",
        ),
    )

    connector_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    source_system_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False)
    endpoint_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    auth_mechanism: Mapped[str] = mapped_column(String(32), nullable=False)
    auth_header_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    credential_env_var_name: Mapped[str] = mapped_column(String(200), nullable=False)
    pagination_style: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OqiConnectorFieldMappingORM(BaseEntity):
    __tablename__ = "oqi_connector_field_mappings"

    __table_args__ = (
        Index("idx_oqi_connector_field_mappings_tenant_id", "tenant_id"),
        Index("idx_oqi_connector_field_mappings_connector_id", "connector_id"),
        UniqueConstraint(
            "tenant_id",
            "mapping_id",
            name="uq_oqi_connector_field_mappings_tenant_pk",
        ),
        UniqueConstraint(
            "connector_id",
            "external_field_path",
            name="uq_oqi_connector_field_mappings_connector_path",
        ),
        # CDD-059 SS13: at most one mapping per connector may designate the
        # external-record-identity path. PostgreSQL partial unique index --
        # "at most one true per connector"; "at least one" is enforced at
        # configuration-save time by the application (a connector with zero
        # such mappings cannot be activated/run, MAPPING_INVALID).
        Index(
            "uq_oqi_connector_field_mappings_one_record_id_per_connector",
            "connector_id",
            unique=True,
            postgresql_where=text("is_external_record_id"),
        ),
        ForeignKeyConstraint(
            ["tenant_id", "connector_id"],
            [
                "oqi_connector_configurations.tenant_id",
                "oqi_connector_configurations.connector_id",
            ],
            name="fk_oqi_connector_field_mappings_tenant_connector",
        ),
    )

    mapping_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    connector_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    external_field_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_field_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    is_external_record_id: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("false")
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OqiConnectorRunORM(BaseEntity):
    __tablename__ = "oqi_connector_runs"

    __table_args__ = (
        Index("idx_oqi_connector_runs_tenant_id", "tenant_id"),
        Index("idx_oqi_connector_runs_connector_id_status", "connector_id", "status"),
        UniqueConstraint(
            "tenant_id",
            "run_id",
            name="uq_oqi_connector_runs_tenant_pk",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "connector_id"],
            [
                "oqi_connector_configurations.tenant_id",
                "oqi_connector_configurations.connector_id",
            ],
            name="fk_oqi_connector_runs_tenant_connector",
        ),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    connector_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checkpoint_page_token: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    fetched_records: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default=text("0")
    )
    accepted_records: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default=text("0")
    )
    rejected_records: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default=text("0")
    )
    duplicate_records: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default=text("0")
    )
    evidence_written: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default=text("0")
    )
    failure_kind: Mapped[str | None] = mapped_column(String(40), nullable=True)
    failure_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(200), nullable=False)
