"""Domain contract for a generic enterprise data connector (CDD-059 SS8).
`ConnectorRecord` is the transport-neutral envelope one externally-fetched
logical record is normalized into before mapping/tenant-proof/admission --
never persisted verbatim, never carrying authoritative tenant identity.
Tenant/run/connector context is supplied exclusively by the trusted
orchestration layer (`ConnectorIngestionService`), never derived from a
`ConnectorRecord`'s own content.

`EnterpriseConnector` is the narrow transport contract every concrete
adapter (real or fake) implements identically -- mirrors the established
`ModelProvider` Protocol precedent (CDD-043 SS23) exactly: a closed
interface, a closed failure-kind taxonomy, no domain/evaluation logic of
any kind. HTTP/TLS/SSRF/pagination/retry behavior belongs entirely to the
infrastructure-layer adapter (`RestConnector`), never to this contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from app.domain.shared.exceptions import ValidationException


class ConnectorFailureKind(StrEnum):
    """Closed classification (CDD-059 SS25) -- exactly these seven, no
    evaluation-related code belongs here since evaluation is out of scope
    for this capability (CDD-059 SS28)."""

    CONNECTOR_UNAVAILABLE = "CONNECTOR_UNAVAILABLE"
    CONNECTOR_AUTHENTICATION_FAILED = "CONNECTOR_AUTHENTICATION_FAILED"
    CONNECTOR_TIMEOUT = "CONNECTOR_TIMEOUT"
    CONNECTOR_RESPONSE_INVALID = "CONNECTOR_RESPONSE_INVALID"
    MAPPING_INVALID = "MAPPING_INVALID"
    RECORD_REJECTED = "RECORD_REJECTED"
    EVIDENCE_ADMISSION_FAILED = "EVIDENCE_ADMISSION_FAILED"


@dataclass(frozen=True, slots=True)
class ConnectorRecord:
    """CDD-059 SS8: the exact, transport-neutral envelope. `fields` maps a
    mapped external field's own label to its raw string value, or `None`
    for a JSON `null`/explicitly-empty value (CDD-059 SS11/SS24 -- present-
    null); a field key entirely absent from this mapping means the source
    payload omitted that field for this record (true absence, SS11). No
    `tenant_id`, no run/connector identifier, no credential material of
    any kind."""

    external_record_id: str
    observed_at: datetime
    fields: Mapping[str, str | None]

    def __post_init__(self) -> None:
        if not isinstance(self.external_record_id, str) or not self.external_record_id.strip():
            raise ValidationException("ConnectorRecord.external_record_id must be non-empty text")
        if not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None:
            raise ValidationException(
                "ConnectorRecord.observed_at must be a timezone-aware datetime"
            )
        for key, value in self.fields.items():
            if not isinstance(key, str) or not key:
                raise ValidationException("ConnectorRecord field label must be non-empty text")
            if value is not None and not isinstance(value, str):
                raise ValidationException(
                    f"ConnectorRecord field {key!r} value must be text or None, "
                    "never a structured (array/object) value -- CDD-059 SS17 rejects those at "
                    "the mapping/normalization boundary before a ConnectorRecord is ever "
                    "constructed"
                )


@dataclass(frozen=True, slots=True)
class ConnectorPage:
    """One fetched, parsed page: zero or more successfully-envelope-able
    records, plus per-record rejection reasons for records that could not
    even be turned into a `ConnectorRecord` (CDD-059 SS23/SS36), plus the
    opaque next-page descriptor (`None` when this was the last page)."""

    records: Sequence[ConnectorRecord]
    rejected_count: int
    next_page_token: str | None


@dataclass(frozen=True, slots=True)
class ConnectorFetchFailure:
    """A page-level or request-level transport failure (CDD-059 SS25/SS37)
    -- never raised as a bare exception across the `EnterpriseConnector`
    boundary, always returned as data, mirroring `ModelInvocationResult`'s
    own established fail-safe-return precedent."""

    kind: ConnectorFailureKind
    detail: str  # bounded, human-readable, NEVER contains credential material (CDD-059 SS31)
    retryable: bool


class EnterpriseConnector(Protocol):
    """CDD-059 SS8/SS58: the one narrow transport contract every concrete
    adapter implements identically. A concrete adapter is constructed once
    per run, already carrying its own fixed configuration (endpoint,
    authentication, extraction plan, resource bounds) -- `fetch_page`
    itself takes only what genuinely varies call-to-call: which page
    (`None` for the first page, meaning "the adapter's own configured
    initial endpoint"; an opaque token/URL for a subsequent page) and the
    run's single frozen `observed_at` fallback (CDD-059 SS10). Never
    writes evidence. Never performs DQ/OQI evaluation. Never establishes
    tenant authority -- the tenant context that gates whether this
    connector may run at all is decided entirely by the caller
    (`ConnectorIngestionService`), before this contract's own `fetch_page`
    is ever invoked."""

    def fetch_page(
        self, *, page_token: str | None, fallback_observed_at: datetime
    ) -> ConnectorPage | ConnectorFetchFailure: ...
