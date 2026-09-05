"""CDD-059 SS41/SS50 -- `/api/v1/oqi/connectors` governed API. Tenant
context comes exclusively from `TrustedPrincipal.tenant_id` (CDD-059
SS38). Exactly three scopes gate five capability groups: configure
connector, read/list connector (+ its field mappings and run history),
disable connector, configure field mapping, run connector -- neither
scope ever implies another."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.oqi.dependencies import authorize
from app.api.oqi.router import oqi_session
from app.api.oqi_connector.dependencies import record_success
from app.api.oqi_connector.schemas import (
    ConfigureConnectorRequest,
    ConfigureFieldMappingRequest,
    ConnectorConfigurationResponse,
    ConnectorListResponse,
    ConnectorRunListResponse,
    ConnectorRunResponse,
    FieldMappingListResponse,
    FieldMappingResponse,
    RunConnectorRequest,
)
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, correlation_id, principal
from app.application.connector_ingestion_service import (
    ConnectorIngestionService,
    ConnectorIngestionServiceError,
)
from app.core.dependency_container import Container

router = APIRouter(prefix="/api/v1/oqi/connectors", tags=["oqi-connectors"])

_ERROR_HTTP_STATUS: dict[str, int] = {
    "CONNECTOR_NOT_FOUND": 404,
    "CONNECTOR_SOURCE_SYSTEM_NOT_FOUND": 404,
    "CONNECTOR_DISABLED": 409,
    "CONNECTOR_ENDPOINT_REJECTED": 422,
    "MAPPING_INVALID": 422,
}


def connector_ingestion_service(
    session: Annotated[Session, Depends(oqi_session)],
) -> ConnectorIngestionService:
    return ConnectorIngestionService(session)


def _configuration_view(configuration: object) -> ConnectorConfigurationResponse:
    return ConnectorConfigurationResponse(
        connector_id=configuration.connector_id,  # type: ignore[attr-defined]
        source_system_id=configuration.source_system_id,  # type: ignore[attr-defined]
        display_name=configuration.display_name,  # type: ignore[attr-defined]
        connector_type=configuration.connector_type,  # type: ignore[attr-defined]
        endpoint_url=configuration.endpoint_url,  # type: ignore[attr-defined]
        auth_mechanism=configuration.auth_mechanism,  # type: ignore[attr-defined]
        pagination_style=configuration.pagination_style,  # type: ignore[attr-defined]
        status=configuration.status,  # type: ignore[attr-defined]
    )


def _mapping_view(mapping: object) -> FieldMappingResponse:
    return FieldMappingResponse(
        mapping_id=mapping.mapping_id,  # type: ignore[attr-defined]
        external_field_path=mapping.external_field_path,  # type: ignore[attr-defined]
        source_field_id=mapping.source_field_id,  # type: ignore[attr-defined]
        is_external_record_id=mapping.is_external_record_id,  # type: ignore[attr-defined]
    )


def _run_view(run: object) -> ConnectorRunResponse:
    return ConnectorRunResponse(
        run_id=run.run_id,  # type: ignore[attr-defined]
        correlation_id=run.correlation_id,  # type: ignore[attr-defined]
        status=run.status,  # type: ignore[attr-defined]
        fetched_records=run.fetched_records,  # type: ignore[attr-defined]
        accepted_records=run.accepted_records,  # type: ignore[attr-defined]
        rejected_records=run.rejected_records,  # type: ignore[attr-defined]
        duplicate_records=run.duplicate_records,  # type: ignore[attr-defined]
        evidence_written=run.evidence_written,  # type: ignore[attr-defined]
        started_on=run.started_on,  # type: ignore[attr-defined]
        completed_on=run.completed_on,  # type: ignore[attr-defined]
        failure_kind=run.failure_kind,  # type: ignore[attr-defined]
    )


@router.post("", response_model=ConnectorConfigurationResponse, status_code=201)
def configure_connector(
    body: ConfigureConnectorRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
) -> ConnectorConfigurationResponse:
    authorize(authenticated, "oqi-connector:configure", dependencies, correlation)
    try:
        configuration = service.configure_connector(
            tenant_id=authenticated.tenant_id,
            source_system_id=body.source_system_id,
            display_name=body.display_name,
            connector_type=body.connector_type,
            endpoint_url=body.endpoint_url,
            auth_mechanism=body.auth_mechanism,
            auth_header_name=body.auth_header_name,
            credential_env_var_name=body.credential_env_var_name,
            pagination_style=body.pagination_style,
            created_by=authenticated.principal_id,
        )
    except ConnectorIngestionServiceError as exc:
        raise HTTPException(
            _ERROR_HTTP_STATUS.get(exc.code, 409), detail={"code": exc.code}
        ) from exc
    record_success(
        dependencies,
        correlation,
        authenticated,
        operation="CONFIGURE_CONNECTOR",
        code=configuration.status,
    )
    return _configuration_view(configuration)


@router.get("", response_model=ConnectorListResponse)
def list_connectors(
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
) -> ConnectorListResponse:
    authorize(authenticated, "oqi-connector:read", dependencies, correlation)
    configurations = service.list_connectors(tenant_id=authenticated.tenant_id)
    return ConnectorListResponse(items=tuple(_configuration_view(c) for c in configurations))


@router.get("/{connector_id}", response_model=ConnectorConfigurationResponse)
def get_connector(
    connector_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
) -> ConnectorConfigurationResponse:
    authorize(authenticated, "oqi-connector:read", dependencies, correlation)
    configuration = service.get_connector(
        tenant_id=authenticated.tenant_id, connector_id=connector_id
    )
    if configuration is None:
        raise HTTPException(404, detail={"code": "CONNECTOR_NOT_FOUND"})
    return _configuration_view(configuration)


@router.post("/{connector_id}/disable", response_model=ConnectorConfigurationResponse)
def disable_connector(
    connector_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
) -> ConnectorConfigurationResponse:
    authorize(authenticated, "oqi-connector:configure", dependencies, correlation)
    try:
        configuration = service.disable_connector(
            tenant_id=authenticated.tenant_id,
            connector_id=connector_id,
            modified_by=authenticated.principal_id,
        )
    except ConnectorIngestionServiceError as exc:
        raise HTTPException(
            _ERROR_HTTP_STATUS.get(exc.code, 409), detail={"code": exc.code}
        ) from exc
    record_success(
        dependencies,
        correlation,
        authenticated,
        operation="DISABLE_CONNECTOR",
        code=configuration.status,
    )
    return _configuration_view(configuration)


@router.post("/{connector_id}/mappings", response_model=FieldMappingResponse, status_code=201)
def configure_field_mapping(
    connector_id: UUID,
    body: ConfigureFieldMappingRequest,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
) -> FieldMappingResponse:
    authorize(authenticated, "oqi-connector:configure", dependencies, correlation)
    try:
        mapping = service.add_field_mapping(
            tenant_id=authenticated.tenant_id,
            connector_id=connector_id,
            external_field_path=body.external_field_path,
            source_field_id=body.source_field_id,
            is_external_record_id=body.is_external_record_id,
            created_by=authenticated.principal_id,
        )
    except ConnectorIngestionServiceError as exc:
        raise HTTPException(
            _ERROR_HTTP_STATUS.get(exc.code, 409), detail={"code": exc.code}
        ) from exc
    record_success(
        dependencies,
        correlation,
        authenticated,
        operation="CONFIGURE_CONNECTOR",
        code="MAPPING_ADDED",
    )
    return _mapping_view(mapping)


@router.get("/{connector_id}/mappings", response_model=FieldMappingListResponse)
def list_field_mappings(
    connector_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
) -> FieldMappingListResponse:
    authorize(authenticated, "oqi-connector:read", dependencies, correlation)
    mappings = service.list_field_mappings(
        tenant_id=authenticated.tenant_id, connector_id=connector_id
    )
    return FieldMappingListResponse(items=tuple(_mapping_view(m) for m in mappings))


@router.post("/{connector_id}/run", response_model=ConnectorRunResponse, status_code=202)
def run_connector(
    connector_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
    body: RunConnectorRequest | None = None,
) -> ConnectorRunResponse:
    authorize(authenticated, "oqi-connector:run", dependencies, correlation)
    try:
        result = service.run_connector(
            tenant_id=authenticated.tenant_id,
            connector_id=connector_id,
            triggered_by=authenticated.principal_id,
            correlation_id=body.correlation_id if body is not None else None,
        )
    except ConnectorIngestionServiceError as exc:
        raise HTTPException(
            _ERROR_HTTP_STATUS.get(exc.code, 409), detail={"code": exc.code}
        ) from exc
    record_success(
        dependencies,
        correlation,
        authenticated,
        operation="CONNECTOR_RUN_" + result.status,
        code=result.status,
    )
    return ConnectorRunResponse(
        run_id=result.run_id,
        correlation_id=result.correlation_id,
        status=result.status,
        fetched_records=result.fetched_records,
        accepted_records=result.accepted_records,
        rejected_records=result.rejected_records,
        duplicate_records=result.duplicate_records,
        evidence_written=result.evidence_written,
        started_on=result.started_on,
        completed_on=result.completed_on,
        failure_kind=result.failure_kind,
    )


@router.get("/{connector_id}/runs", response_model=ConnectorRunListResponse)
def list_connector_runs(
    connector_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
) -> ConnectorRunListResponse:
    authorize(authenticated, "oqi-connector:read", dependencies, correlation)
    runs = service.list_runs(tenant_id=authenticated.tenant_id, connector_id=connector_id)
    return ConnectorRunListResponse(items=tuple(_run_view(r) for r in runs))


@router.get("/{connector_id}/runs/{run_id}", response_model=ConnectorRunResponse)
def get_connector_run(
    connector_id: UUID,
    run_id: UUID,
    authenticated: Annotated[TrustedPrincipal, Depends(principal)],
    dependencies: Annotated[Container, Depends(container)],
    correlation: Annotated[UUID, Depends(correlation_id)],
    service: Annotated[ConnectorIngestionService, Depends(connector_ingestion_service)],
) -> ConnectorRunResponse:
    authorize(authenticated, "oqi-connector:read", dependencies, correlation)
    run = service.get_run(tenant_id=authenticated.tenant_id, run_id=run_id)
    if run is None or run.connector_id != connector_id:
        raise HTTPException(404, detail={"code": "CONNECTOR_RUN_NOT_FOUND"})
    return _run_view(run)
