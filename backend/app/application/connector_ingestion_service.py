"""Application service for Production Governed Enterprise REST Ingestion
(CDD-059; Artifact Authorization row 4). Owns: trusted tenant
orchestration, the mandatory SourceField two-hop tenant-authority proof
(CDD-059 SS39) at both configuration-time and run-time, mapping
application, per-page transaction boundaries (CDD-059 SS21), and run
accounting (CDD-059 SS37). Never invokes `/api/v1/oqi/evaluate` (CDD-059
SS28). Never creates `SourceSystem`/`SourceObject`/`SourceField`/
`SemanticMapping`/`ComparisonSubjectCorrespondence` (CDD-059 SS27)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.integration.enterprise_connector import ConnectorFetchFailure, EnterpriseConnector
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.connectors.rest_connector import (
    FieldExtractionPlan,
    RestConnector,
    SSRFRejected,
    validate_endpoint_url,
)
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_connector_repository import (
    ConnectorConfiguration,
    ConnectorFieldMapping,
    ConnectorRun,
    OqiConnectorRepositoryImpl,
)

_MAX_PAGES_PER_RUN = 200
_MAX_RUN_DURATION_SECONDS = 600
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_RECORDS_PER_PAGE = 500
_MAX_FIELDS_PER_RECORD = 200
_REQUEST_TIMEOUT_SECONDS = 30

_VALID_CONNECTOR_TYPES = frozenset({"GENERIC_REST"})
_VALID_AUTH_MECHANISMS = frozenset({"API_KEY", "BEARER_TOKEN"})
_VALID_PAGINATION_STYLES = frozenset({"NONE", "CURSOR"})


class ConnectorIngestionServiceError(Exception):
    """Carries one of this module's closed diagnostic codes -- mirrors
    every prior OQI service's own established shape; no raw internal
    exception escapes a public method."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: UUID
    correlation_id: UUID
    status: str
    fetched_records: int
    accepted_records: int
    rejected_records: int
    duplicate_records: int
    evidence_written: int
    started_on: datetime
    completed_on: datetime
    failure_kind: str | None


class ConnectorIngestionService:
    def __init__(
        self,
        session: Session,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        connector_factory: Callable[..., EnterpriseConnector] = RestConnector,
    ) -> None:
        self.session = session
        self._clock = clock
        self._connector_factory = connector_factory

    # ------------------------------------------------------------------
    # Configuration (CDD-059 SS12/SS32 config-time SSRF check)
    # ------------------------------------------------------------------

    def configure_connector(
        self,
        *,
        tenant_id: str,
        source_system_id: UUID,
        display_name: str,
        connector_type: str,
        endpoint_url: str,
        auth_mechanism: str,
        auth_header_name: str | None,
        credential_env_var_name: str,
        pagination_style: str,
        created_by: str,
    ) -> ConnectorConfiguration:
        if connector_type not in _VALID_CONNECTOR_TYPES:
            raise ConnectorIngestionServiceError("MAPPING_INVALID")
        if auth_mechanism not in _VALID_AUTH_MECHANISMS:
            raise ConnectorIngestionServiceError("MAPPING_INVALID")
        if auth_mechanism == "API_KEY" and not auth_header_name:
            raise ConnectorIngestionServiceError("MAPPING_INVALID")
        if pagination_style not in _VALID_PAGINATION_STYLES:
            raise ConnectorIngestionServiceError("MAPPING_INVALID")

        repository = OqiConnectorRepositoryImpl(self.session)
        if not repository.is_source_system_owned_by_tenant(
            tenant_id=tenant_id, source_system_id=source_system_id
        ):
            raise ConnectorIngestionServiceError("CONNECTOR_SOURCE_SYSTEM_NOT_FOUND")

        try:
            validate_endpoint_url(endpoint_url)
        except SSRFRejected as exc:
            raise ConnectorIngestionServiceError("CONNECTOR_ENDPOINT_REJECTED") from exc

        now = self._clock()
        configuration = ConnectorConfiguration(
            connector_id=uuid4(),
            tenant_id=tenant_id,
            source_system_id=source_system_id,
            display_name=display_name,
            connector_type=connector_type,
            endpoint_url=endpoint_url,
            auth_mechanism=auth_mechanism,
            auth_header_name=auth_header_name,
            credential_env_var_name=credential_env_var_name,
            pagination_style=pagination_style,
            status="ACTIVE",
            created_by=created_by,
            created_on=now,
            modified_by=None,
            modified_on=None,
        )
        repository.create_configuration(configuration)
        return configuration

    def get_connector(self, *, tenant_id: str, connector_id: UUID) -> ConnectorConfiguration | None:
        return OqiConnectorRepositoryImpl(self.session).get_configuration(
            tenant_id=tenant_id, connector_id=connector_id
        )

    def list_connectors(self, *, tenant_id: str) -> tuple[ConnectorConfiguration, ...]:
        return OqiConnectorRepositoryImpl(self.session).list_configurations(tenant_id=tenant_id)

    def disable_connector(
        self, *, tenant_id: str, connector_id: UUID, modified_by: str
    ) -> ConnectorConfiguration:
        result = OqiConnectorRepositoryImpl(self.session).disable_configuration(
            tenant_id=tenant_id,
            connector_id=connector_id,
            modified_by=modified_by,
            now=self._clock(),
        )
        if result is None:
            raise ConnectorIngestionServiceError("CONNECTOR_NOT_FOUND")
        return result

    # ------------------------------------------------------------------
    # Field mapping (CDD-059 SS13/SS39 -- the mandatory two-hop tenant proof)
    # ------------------------------------------------------------------

    def add_field_mapping(
        self,
        *,
        tenant_id: str,
        connector_id: UUID,
        external_field_path: str,
        source_field_id: UUID,
        is_external_record_id: bool,
        created_by: str,
    ) -> ConnectorFieldMapping:
        repository = OqiConnectorRepositoryImpl(self.session)
        configuration = repository.get_configuration(tenant_id=tenant_id, connector_id=connector_id)
        if configuration is None:
            raise ConnectorIngestionServiceError("CONNECTOR_NOT_FOUND")
        if not repository.is_source_field_owned_by_tenant(
            tenant_id=tenant_id, source_field_id=source_field_id
        ):
            raise ConnectorIngestionServiceError("MAPPING_INVALID")

        mapping = ConnectorFieldMapping(
            mapping_id=uuid4(),
            tenant_id=tenant_id,
            connector_id=connector_id,
            external_field_path=external_field_path,
            source_field_id=source_field_id,
            is_external_record_id=is_external_record_id,
            created_by=created_by,
            created_on=self._clock(),
        )
        repository.create_field_mapping(mapping)
        return mapping

    def list_field_mappings(
        self, *, tenant_id: str, connector_id: UUID
    ) -> tuple[ConnectorFieldMapping, ...]:
        return OqiConnectorRepositoryImpl(self.session).list_field_mappings(
            tenant_id=tenant_id, connector_id=connector_id
        )

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def get_run(self, *, tenant_id: str, run_id: UUID) -> ConnectorRun | None:
        return OqiConnectorRepositoryImpl(self.session).get_run(tenant_id=tenant_id, run_id=run_id)

    def list_runs(self, *, tenant_id: str, connector_id: UUID) -> tuple[ConnectorRun, ...]:
        return OqiConnectorRepositoryImpl(self.session).list_runs(
            tenant_id=tenant_id, connector_id=connector_id
        )

    def run_connector(
        self,
        *,
        tenant_id: str,
        connector_id: UUID,
        triggered_by: str,
        correlation_id: UUID | None = None,
    ) -> RunResult:
        repository = OqiConnectorRepositoryImpl(self.session)
        configuration = repository.get_configuration(tenant_id=tenant_id, connector_id=connector_id)
        if configuration is None:
            raise ConnectorIngestionServiceError("CONNECTOR_NOT_FOUND")
        if configuration.status != "ACTIVE":
            raise ConnectorIngestionServiceError("CONNECTOR_DISABLED")

        mappings = repository.list_field_mappings(tenant_id=tenant_id, connector_id=connector_id)
        record_id_mappings = [m for m in mappings if m.is_external_record_id]
        if len(record_id_mappings) != 1:
            raise ConnectorIngestionServiceError("MAPPING_INVALID")

        # CDD-059 SS39: re-prove every mapping's tenant ownership at RUN
        # TIME too -- never trust the configuration-time proof alone.
        for mapping in mappings:
            if not repository.is_source_field_owned_by_tenant(
                tenant_id=tenant_id, source_field_id=mapping.source_field_id
            ):
                raise ConnectorIngestionServiceError("MAPPING_INVALID")

        run_id = uuid4()
        run_correlation_id = correlation_id if correlation_id is not None else run_id
        run_started_on = self._clock()
        run = ConnectorRun(
            run_id=run_id,
            tenant_id=tenant_id,
            connector_id=connector_id,
            correlation_id=run_correlation_id,
            status="RUNNING",
            started_on=run_started_on,
            completed_on=None,
            checkpoint_page_token=None,
            fetched_records=0,
            accepted_records=0,
            rejected_records=0,
            duplicate_records=0,
            evidence_written=0,
            failure_kind=None,
            failure_summary=None,
            triggered_by=triggered_by,
        )
        repository.create_run(run)
        self.session.commit()  # durable RUNNING row before any network I/O (CDD-059 SS21)

        extraction_plan = FieldExtractionPlan(
            external_record_id_path=record_id_mappings[0].external_field_path,
            field_paths={str(m.source_field_id): m.external_field_path for m in mappings},
        )
        connector = self._connector_factory(
            endpoint_url=configuration.endpoint_url,
            extraction_plan=extraction_plan,
            auth_mechanism=configuration.auth_mechanism,
            auth_header_name=configuration.auth_header_name,
            credential_env_var_name=configuration.credential_env_var_name,
            max_response_bytes=_MAX_RESPONSE_BYTES,
            max_records_per_page=_MAX_RECORDS_PER_PAGE,
            max_fields_per_record=_MAX_FIELDS_PER_RECORD,
            request_timeout_seconds=_REQUEST_TIMEOUT_SECONDS,
        )

        fetched = accepted = rejected = duplicate = written = 0
        page_token: str | None = None
        pages_fetched = 0
        overall_status = "SUCCEEDED"
        failure_kind: str | None = None
        failure_summary: str | None = None
        run_start_monotonic = monotonic()

        while True:
            pages_fetched += 1
            if pages_fetched > _MAX_PAGES_PER_RUN:
                overall_status = "PARTIAL" if accepted > 0 else "FAILED"
                failure_kind = "CONNECTOR_RESPONSE_INVALID"
                failure_summary = "max pages per run exceeded"
                break
            if monotonic() - run_start_monotonic > _MAX_RUN_DURATION_SECONDS:
                overall_status = "PARTIAL" if accepted > 0 else "FAILED"
                failure_kind = "CONNECTOR_TIMEOUT"
                failure_summary = "max run duration exceeded"
                break

            outcome = connector.fetch_page(
                page_token=page_token, fallback_observed_at=run_started_on
            )
            if isinstance(outcome, ConnectorFetchFailure):
                overall_status = "PARTIAL" if accepted > 0 else "FAILED"
                failure_kind = outcome.kind.value
                failure_summary = outcome.detail
                break

            fetched += len(outcome.records) + outcome.rejected_count
            rejected += outcome.rejected_count

            # SHORT DB TRANSACTION (CDD-059 SS21): admit exactly this
            # page's evidence, then commit -- never held open across the
            # next page's own remote fetch.
            page_accepted = page_duplicate = page_written = 0
            for record in outcome.records:
                admission = self._admit_record(
                    tenant_id=tenant_id,
                    mappings=mappings,
                    record_fields=record.fields,
                    external_record_id=record.external_record_id,
                    observed_at=record.observed_at,
                    received_at=self._clock(),
                    correlation_id=run_correlation_id,
                )
                if admission is None:
                    rejected += 1
                    continue
                page_accepted += 1
                if admission:
                    page_written += 1
                else:
                    page_duplicate += 1
            accepted += page_accepted
            duplicate += page_duplicate
            written += page_written

            repository.update_run_progress(
                run_id=run_id,
                checkpoint_page_token=outcome.next_page_token,
                fetched_records=fetched,
                accepted_records=accepted,
                rejected_records=rejected,
                duplicate_records=duplicate,
                evidence_written=written,
            )
            self.session.commit()

            if outcome.next_page_token is None:
                break
            page_token = outcome.next_page_token

        completed_on = self._clock()
        final = repository.complete_run(
            run_id=run_id,
            status=overall_status,
            completed_on=completed_on,
            failure_kind=failure_kind,
            failure_summary=failure_summary,
        )
        self.session.commit()
        return RunResult(
            run_id=final.run_id,
            correlation_id=final.correlation_id,
            status=final.status,
            fetched_records=final.fetched_records,
            accepted_records=final.accepted_records,
            rejected_records=final.rejected_records,
            duplicate_records=final.duplicate_records,
            evidence_written=final.evidence_written,
            started_on=final.started_on,
            completed_on=completed_on,
            failure_kind=final.failure_kind,
        )

    def _admit_record(
        self,
        *,
        tenant_id: str,
        mappings: tuple[ConnectorFieldMapping, ...],
        record_fields: Mapping[str, str | None],
        external_record_id: str,
        observed_at: datetime,
        received_at: datetime,
        correlation_id: UUID,
    ) -> bool | None:
        """Returns `True` if this record produced at least one genuinely
        new evidence row, `False` if every one of its mapped fields
        already existed as evidence (a pure idempotent replay of this
        exact record -- CDD-059 SS37's `duplicate_records`), or `None` if
        the record could not be admitted at all (CDD-059 SS23,
        `RECORD_REJECTED`/`EVIDENCE_ADMISSION_FAILED`, never a page-wide
        failure)."""
        evidence_repository = FieldValueEvidenceRepositoryImpl(self.session)
        any_new = False
        any_admitted = False
        try:
            for mapping in mappings:
                if mapping.is_external_record_id:
                    continue
                field_key = str(mapping.source_field_id)
                if field_key not in record_fields:
                    continue  # true absence (CDD-059 SS11) -- no evidence row this run
                raw_value = record_fields[field_key]
                observed_representation = "" if raw_value is None else raw_value
                evidence = FieldValueEvidence.new(
                    source_field_id=Identifier(mapping.source_field_id),
                    source_record_reference=external_record_id,
                    observed_representation=observed_representation,
                    observed_at=observed_at,
                    received_at=received_at,
                    evidence_reference=str(correlation_id),
                )
                existed_before = (
                    evidence_repository.get_by_id(evidence.field_value_evidence_id.value)
                    is not None
                )
                try:
                    with self.session.begin_nested():
                        evidence_repository.create_or_get_existing(evidence)
                except IntegrityError:
                    # A genuine concurrent writer (CDD-059's own same-
                    # connector concurrency crown) committed this exact
                    # evidence identity between our own existence check and
                    # insert. The savepoint above rolls back only this one
                    # insert, never the outer per-page transaction; the
                    # other writer's now-committed row is the correct
                    # current state -- re-read it rather than treat this as
                    # a genuine failure.
                    if (
                        evidence_repository.get_by_id(evidence.field_value_evidence_id.value)
                        is None
                    ):
                        raise
                any_admitted = True
                if not existed_before:
                    any_new = True
        except ValidationException:
            return None
        if not any_admitted:
            return False
        return any_new
