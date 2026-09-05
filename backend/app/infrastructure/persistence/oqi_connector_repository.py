"""Repository for Production Governed Enterprise REST Ingestion (CDD-059
SS12-SS14, SS39-SS40; Artifact Authorization row 6). Persists connector
configuration/field-mapping/run-ledger rows; every read is tenant-scoped
at the query itself, never merely tenant-checked after an untenanted
lookup (CDD-059 SS38).

`is_source_field_owned_by_tenant` implements the mandatory two-hop
tenant-authority proof CDD-059 SS39 requires -- reusing the exact join
`FieldValueEvidenceRepositoryImpl.get_by_source_field` already establishes
as correct precedent (`source_field_id -> source_fields.source_object_id
-> source_objects.tenant_id`), never a new or weaker mechanism."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.oqi_connector import (
    OqiConnectorConfigurationORM,
    OqiConnectorFieldMappingORM,
    OqiConnectorRunORM,
)
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.models.source_system import SourceSystem as SourceSystemORM


@dataclass(frozen=True, slots=True)
class ConnectorConfiguration:
    connector_id: UUID
    tenant_id: str
    source_system_id: UUID
    display_name: str
    connector_type: str
    endpoint_url: str
    auth_mechanism: str
    auth_header_name: str | None
    credential_env_var_name: str
    pagination_style: str
    status: str
    created_by: str
    created_on: datetime
    modified_by: str | None
    modified_on: datetime | None


@dataclass(frozen=True, slots=True)
class ConnectorFieldMapping:
    mapping_id: UUID
    tenant_id: str
    connector_id: UUID
    external_field_path: str
    source_field_id: UUID
    is_external_record_id: bool
    created_by: str
    created_on: datetime


@dataclass(frozen=True, slots=True)
class ConnectorRun:
    run_id: UUID
    tenant_id: str
    connector_id: UUID
    correlation_id: UUID
    status: str
    started_on: datetime
    completed_on: datetime | None
    checkpoint_page_token: str | None
    fetched_records: int
    accepted_records: int
    rejected_records: int
    duplicate_records: int
    evidence_written: int
    failure_kind: str | None
    failure_summary: str | None
    triggered_by: str


def _configuration_to_domain(model: OqiConnectorConfigurationORM) -> ConnectorConfiguration:
    return ConnectorConfiguration(
        connector_id=model.connector_id,
        tenant_id=model.tenant_id,
        source_system_id=model.source_system_id,
        display_name=model.display_name,
        connector_type=model.connector_type,
        endpoint_url=model.endpoint_url,
        auth_mechanism=model.auth_mechanism,
        auth_header_name=model.auth_header_name,
        credential_env_var_name=model.credential_env_var_name,
        pagination_style=model.pagination_style,
        status=model.status,
        created_by=model.created_by,
        created_on=model.created_on,
        modified_by=model.modified_by,
        modified_on=model.modified_on,
    )


def _mapping_to_domain(model: OqiConnectorFieldMappingORM) -> ConnectorFieldMapping:
    return ConnectorFieldMapping(
        mapping_id=model.mapping_id,
        tenant_id=model.tenant_id,
        connector_id=model.connector_id,
        external_field_path=model.external_field_path,
        source_field_id=model.source_field_id,
        is_external_record_id=model.is_external_record_id,
        created_by=model.created_by,
        created_on=model.created_on,
    )


def _run_to_domain(model: OqiConnectorRunORM) -> ConnectorRun:
    return ConnectorRun(
        run_id=model.run_id,
        tenant_id=model.tenant_id,
        connector_id=model.connector_id,
        correlation_id=model.correlation_id,
        status=model.status,
        started_on=model.started_on,
        completed_on=model.completed_on,
        checkpoint_page_token=model.checkpoint_page_token,
        fetched_records=model.fetched_records,
        accepted_records=model.accepted_records,
        rejected_records=model.rejected_records,
        duplicate_records=model.duplicate_records,
        evidence_written=model.evidence_written,
        failure_kind=model.failure_kind,
        failure_summary=model.failure_summary,
        triggered_by=model.triggered_by,
    )


class OqiConnectorRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Tenant-authority proofs (CDD-059 SS39/SS40) -- read-only, reused by
    # both configuration-time and run-time validation.
    # ------------------------------------------------------------------

    def is_source_system_owned_by_tenant(self, *, tenant_id: str, source_system_id: UUID) -> bool:
        owner = self.session.execute(
            select(SourceSystemORM.tenant_id).where(
                SourceSystemORM.source_system_id == source_system_id
            )
        ).scalar_one_or_none()
        return owner == tenant_id

    def is_source_field_owned_by_tenant(self, *, tenant_id: str, source_field_id: UUID) -> bool:
        """CDD-059 SS39, the mandatory two-hop proof: `source_fields` and
        `source_objects` are joined explicitly because `source_fields`
        itself carries no `tenant_id` column -- mirrors
        `FieldValueEvidenceRepositoryImpl.get_by_source_field`'s own
        established-correct join exactly."""
        source_field = self.session.get(SourceFieldORM, source_field_id)
        if source_field is None:
            return False
        owner = self.session.execute(
            select(SourceObjectORM.tenant_id).where(
                SourceObjectORM.source_object_id == source_field.source_object_id
            )
        ).scalar_one_or_none()
        return owner == tenant_id

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def create_configuration(self, configuration: ConnectorConfiguration) -> None:
        self.session.add(
            OqiConnectorConfigurationORM(
                connector_id=configuration.connector_id,
                tenant_id=configuration.tenant_id,
                source_system_id=configuration.source_system_id,
                display_name=configuration.display_name,
                connector_type=configuration.connector_type,
                endpoint_url=configuration.endpoint_url,
                auth_mechanism=configuration.auth_mechanism,
                auth_header_name=configuration.auth_header_name,
                credential_env_var_name=configuration.credential_env_var_name,
                pagination_style=configuration.pagination_style,
                status=configuration.status,
                created_by=configuration.created_by,
                created_on=configuration.created_on,
                modified_by=configuration.modified_by,
                modified_on=configuration.modified_on,
            )
        )
        self.session.flush()

    def get_configuration(
        self, *, tenant_id: str, connector_id: UUID
    ) -> ConnectorConfiguration | None:
        model = self.session.execute(
            select(OqiConnectorConfigurationORM).where(
                OqiConnectorConfigurationORM.tenant_id == tenant_id,
                OqiConnectorConfigurationORM.connector_id == connector_id,
            )
        ).scalar_one_or_none()
        return None if model is None else _configuration_to_domain(model)

    def list_configurations(self, *, tenant_id: str) -> tuple[ConnectorConfiguration, ...]:
        models = (
            self.session.execute(
                select(OqiConnectorConfigurationORM)
                .where(OqiConnectorConfigurationORM.tenant_id == tenant_id)
                .order_by(OqiConnectorConfigurationORM.created_on)
            )
            .scalars()
            .all()
        )
        return tuple(_configuration_to_domain(model) for model in models)

    def disable_configuration(
        self, *, tenant_id: str, connector_id: UUID, modified_by: str, now: datetime
    ) -> ConnectorConfiguration | None:
        model = self.session.execute(
            select(OqiConnectorConfigurationORM).where(
                OqiConnectorConfigurationORM.tenant_id == tenant_id,
                OqiConnectorConfigurationORM.connector_id == connector_id,
            )
        ).scalar_one_or_none()
        if model is None:
            return None
        model.status = "DISABLED"
        model.modified_by = modified_by
        model.modified_on = now
        self.session.flush()
        return _configuration_to_domain(model)

    # ------------------------------------------------------------------
    # Field mapping
    # ------------------------------------------------------------------

    def create_field_mapping(self, mapping: ConnectorFieldMapping) -> None:
        self.session.add(
            OqiConnectorFieldMappingORM(
                mapping_id=mapping.mapping_id,
                tenant_id=mapping.tenant_id,
                connector_id=mapping.connector_id,
                external_field_path=mapping.external_field_path,
                source_field_id=mapping.source_field_id,
                is_external_record_id=mapping.is_external_record_id,
                created_by=mapping.created_by,
                created_on=mapping.created_on,
            )
        )
        self.session.flush()

    def list_field_mappings(
        self, *, tenant_id: str, connector_id: UUID
    ) -> tuple[ConnectorFieldMapping, ...]:
        models = (
            self.session.execute(
                select(OqiConnectorFieldMappingORM).where(
                    OqiConnectorFieldMappingORM.tenant_id == tenant_id,
                    OqiConnectorFieldMappingORM.connector_id == connector_id,
                )
            )
            .scalars()
            .all()
        )
        return tuple(_mapping_to_domain(model) for model in models)

    # ------------------------------------------------------------------
    # Run ledger
    # ------------------------------------------------------------------

    def create_run(self, run: ConnectorRun) -> None:
        self.session.add(
            OqiConnectorRunORM(
                run_id=run.run_id,
                tenant_id=run.tenant_id,
                connector_id=run.connector_id,
                correlation_id=run.correlation_id,
                status=run.status,
                started_on=run.started_on,
                completed_on=run.completed_on,
                checkpoint_page_token=run.checkpoint_page_token,
                fetched_records=run.fetched_records,
                accepted_records=run.accepted_records,
                rejected_records=run.rejected_records,
                duplicate_records=run.duplicate_records,
                evidence_written=run.evidence_written,
                failure_kind=run.failure_kind,
                failure_summary=run.failure_summary,
                triggered_by=run.triggered_by,
            )
        )
        self.session.flush()

    def update_run_progress(
        self,
        *,
        run_id: UUID,
        checkpoint_page_token: str | None,
        fetched_records: int,
        accepted_records: int,
        rejected_records: int,
        duplicate_records: int,
        evidence_written: int,
    ) -> None:
        model = self.session.get(OqiConnectorRunORM, run_id)
        assert model is not None
        model.checkpoint_page_token = checkpoint_page_token
        model.fetched_records = fetched_records
        model.accepted_records = accepted_records
        model.rejected_records = rejected_records
        model.duplicate_records = duplicate_records
        model.evidence_written = evidence_written
        self.session.flush()

    def complete_run(
        self,
        *,
        run_id: UUID,
        status: str,
        completed_on: datetime,
        failure_kind: str | None,
        failure_summary: str | None,
    ) -> ConnectorRun:
        model = self.session.get(OqiConnectorRunORM, run_id)
        assert model is not None
        model.status = status
        model.completed_on = completed_on
        model.failure_kind = failure_kind
        model.failure_summary = failure_summary
        self.session.flush()
        return _run_to_domain(model)

    def get_run(self, *, tenant_id: str, run_id: UUID) -> ConnectorRun | None:
        model = self.session.execute(
            select(OqiConnectorRunORM).where(
                OqiConnectorRunORM.tenant_id == tenant_id,
                OqiConnectorRunORM.run_id == run_id,
            )
        ).scalar_one_or_none()
        return None if model is None else _run_to_domain(model)

    def list_runs(self, *, tenant_id: str, connector_id: UUID) -> tuple[ConnectorRun, ...]:
        models = (
            self.session.execute(
                select(OqiConnectorRunORM)
                .where(
                    OqiConnectorRunORM.tenant_id == tenant_id,
                    OqiConnectorRunORM.connector_id == connector_id,
                )
                .order_by(OqiConnectorRunORM.started_on.desc())
            )
            .scalars()
            .all()
        )
        return tuple(_run_to_domain(model) for model in models)
