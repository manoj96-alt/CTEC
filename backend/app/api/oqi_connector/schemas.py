"""CDD-059 SS50 -- Pydantic request/response contracts for
`/api/v1/oqi/connectors`. No request schema carries a `tenant_id` field
(`extra="forbid"` rejects one) -- tenant authority is sourced exclusively
from the authenticated `TrustedPrincipal` (CDD-059 SS38). No response
schema ever carries the connector's own credential value or its
environment-variable-name reference (CDD-059 SS50/SS15: even the
variable *name* is redacted from ordinary reads)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConfigureConnectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system_id: UUID
    display_name: str
    connector_type: str
    endpoint_url: str
    auth_mechanism: str
    auth_header_name: str | None = None
    credential_env_var_name: str
    pagination_style: str


class ConnectorConfigurationResponse(BaseModel):
    connector_id: UUID
    source_system_id: UUID
    display_name: str
    connector_type: str
    endpoint_url: str
    auth_mechanism: str
    pagination_style: str
    status: str


class ConnectorListResponse(BaseModel):
    items: tuple[ConnectorConfigurationResponse, ...]


class ConfigureFieldMappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_field_path: str
    source_field_id: UUID
    is_external_record_id: bool = False


class FieldMappingResponse(BaseModel):
    mapping_id: UUID
    external_field_path: str
    source_field_id: UUID
    is_external_record_id: bool


class FieldMappingListResponse(BaseModel):
    items: tuple[FieldMappingResponse, ...]


class RunConnectorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: UUID | None = None


class ConnectorRunResponse(BaseModel):
    run_id: UUID
    correlation_id: UUID
    status: str
    fetched_records: int
    accepted_records: int
    rejected_records: int
    duplicate_records: int
    evidence_written: int
    started_on: datetime
    completed_on: datetime | None
    failure_kind: str | None


class ConnectorRunListResponse(BaseModel):
    items: tuple[ConnectorRunResponse, ...]
