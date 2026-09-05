"""`RestConnector` -- the one infrastructure adapter CDD-059 SS9/SS58
authorizes: a generic, vendor-neutral, stdlib-only (`urllib.request`) HTTPS
REST transport. No `if SAP`/`if Snowflake`/`if Databricks` branching of any
kind belongs here or anywhere in this module (CDD-059 SS9). Mirrors
`AnthropicMessagesProvider`'s own established precedent exactly: stdlib
HTTP only (no new production dependency), a closed failure-kind taxonomy,
credentials read from `os.environ` only, never logged.

Owns exactly: HTTPS transport, authentication header construction, the
complete SSRF policy (CDD-059 SS32, applied identically to the initial
endpoint and to every subsequent next-link), TLS verification, bounded
reads, pagination, retry/backoff, response parsing, and `ConnectorRecord`
construction via the frozen dotted-path extraction contract (CDD-059
SS36). Never writes evidence. Never performs DQ/OQI evaluation. Never
establishes tenant authority -- the caller (`ConnectorIngestionService`)
decides whether this adapter may run at all, before `fetch_page` is ever
invoked."""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.integration.enterprise_connector import (
    ConnectorFailureKind,
    ConnectorFetchFailure,
    ConnectorPage,
    ConnectorRecord,
)

_MAX_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 1.0
_RETRY_BACKOFF_FACTOR = 2.0
_TEST_CA_BUNDLE_ENV_VAR = "CTEC_CONNECTOR_TEST_CA_BUNDLE"

_RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
_NON_RETRYABLE_AUTH_STATUSES = {401, 403}


class SSRFRejected(Exception):
    """Raised the moment a URL (initial endpoint or next-link) fails the
    frozen CDD-059 SS32 policy. Never retried, never followed."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True, slots=True)
class FieldExtractionPlan:
    """CDD-059 SS36: the narrowest possible transport-neutral extraction
    plan, derived by `ConnectorIngestionService` from governed field
    mappings -- never vendor-specific. `field_paths` maps an output key
    (the string form of the target `source_field_id`, chosen by the
    caller so downstream mapping lookup is unambiguous) to the raw
    dotted-path external field location. `external_record_id_path` is the
    one path CDD-059 SS16 requires every connector record to supply a
    stable identity from."""

    external_record_id_path: str
    field_paths: Mapping[str, str]


def _is_prohibited_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """CDD-059 SS32: loopback, link-local (includes 169.254.169.254),
    RFC1918/private (IPv4) and unique-local (IPv6 fc00::/7), multicast,
    reserved, and unspecified -- covers every prohibited range the policy
    names, via the standard library's own well-tested range predicates
    rather than a hand-rolled CIDR table."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


_ABSOLUTE_DENY_NETWORKS = (
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
)

_EXEMPTIBLE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("fc00::/7"),
)


def _is_absolute_deny(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """I-R1 SSRF Test-Boundary Correction Amendment SS6.5: link-local
    (169.254.0.0/16 / fe80::/10 -- subsumes every cloud metadata address
    of every vendor), multicast, reserved, and unspecified remain
    unconditionally prohibited. No exception mechanism of any kind --
    including an active `FixtureEndpointSecurityPolicy` -- may ever
    override this, regardless of any allowlisted-address content."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        any(ip in net for net in _ABSOLUTE_DENY_NETWORKS)
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _is_exemptible_range(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """I-R1 amendment SS6.5: only loopback and RFC1918-private(IPv4)/
    IPv6-unique-local may ever be exempted by an active
    `FixtureEndpointSecurityPolicy` -- these are the only ranges the
    mandated Docker-bridge and host-loopback fixture topologies actually
    use (Artifact Authorization SS8). Never link-local, multicast,
    reserved, or unspecified (`_is_absolute_deny` above)."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback or any(ip in net for net in _EXEMPTIBLE_NETWORKS)


def _resolve_and_validate(url: str, *, allowed_addresses: frozenset[str]) -> None:
    """CDD-059 SS32: scheme + fresh-DNS-resolution + full-resolved-
    address-set range check, evaluated fresh for THIS call -- never
    cached from a prior check, so DNS rebinding between two calls can
    never bypass this policy. Applied identically to the initial endpoint
    and to every subsequent next-link (CDD-059 SS29/SS35).

    `allowed_addresses` is empty for `ProductionEndpointSecurityPolicy`
    (zero exceptions, ever -- production code never supplies a non-empty
    set here; see that class below). A non-empty set, constructible only
    by `FixtureEndpointSecurityPolicy` (test-only), exempts an exact
    resolved-address match ONLY when that same address is also within
    `_is_exemptible_range` -- never for an address `_is_absolute_deny`
    names, regardless of `allowed_addresses` content (I-R1 amendment
    SS6.5). Matching is exact resolved-IP-string equality only: no CIDR,
    no hostname, no wildcard; a malformed entry in `allowed_addresses`
    simply never matches anything (fails closed)."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https":
        raise SSRFRejected(f"scheme {parsed.scheme!r} is not https")
    host = parsed.hostname
    if not host:
        raise SSRFRejected("URL has no resolvable hostname")
    port = parsed.port or 443
    try:
        addrinfo = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise SSRFRejected(f"DNS resolution failed for {host!r}: {exc}") from exc
    resolved = {str(info[4][0]) for info in addrinfo}
    if not resolved:
        raise SSRFRejected(f"DNS resolution for {host!r} returned no addresses")
    for ip_str in resolved:
        ip_str_clean = ip_str.split("%", 1)[0]  # strip IPv6 zone id before parsing
        ip = ipaddress.ip_address(ip_str_clean)
        if (
            ip_str_clean in allowed_addresses
            and _is_exemptible_range(ip)
            and not _is_absolute_deny(ip)
        ):
            continue
        if _is_prohibited_address(ip):
            raise SSRFRejected(f"resolved address {ip_str_clean} for host {host!r} is prohibited")


class EndpointSecurityPolicy(Protocol):
    """CDD-059 SS32 boundary, structurally separated from any single
    implementation (I-R1 SSRF Test-Boundary Correction Amendment SS6.2).
    Production code may only ever default-construct
    `ProductionEndpointSecurityPolicy`. `FixtureEndpointSecurityPolicy` is
    test-only and is defined in
    `app/tests/test_oqi_connector_ingestion_postgres.py`, never in this
    module -- no production file may import or construct it."""

    def validate(self, url: str) -> None:
        """Raises `SSRFRejected` if `url` fails policy. Evaluated fresh
        for every call -- initial endpoint and every next-link alike."""
        ...


class ProductionEndpointSecurityPolicy:
    """The ONLY policy any production code path may construct. Reads no
    environment variable, accepts no allowlist of any kind, from any
    source (request body, query, header, connector configuration row, or
    process environment). Behaviorally identical to CDD-059 SS32 as
    originally frozen: zero exceptions."""

    def validate(self, url: str) -> None:
        _resolve_and_validate(url, allowed_addresses=frozenset())


_DEFAULT_ENDPOINT_SECURITY_POLICY = ProductionEndpointSecurityPolicy()


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """CDD-059 SS32 point 6: redirect-following is disabled. Returning
    `None` here causes `HTTPRedirectHandler`'s own error handlers to hand
    back the raw 3xx response instead of silently re-issuing the request
    against an unvalidated destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _read_bounded(response: object, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(65536)  # type: ignore[attr-defined]
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"response exceeded max_bytes={max_bytes}")
        chunks.append(chunk)
    return b"".join(chunks)


def _extract_path(document: object, path: str) -> tuple[bool, object]:
    """CDD-059 SS36: dotted-path traversal. Returns `(present, value)`;
    `present=False` means the path is genuinely absent (a missing object
    key or an out-of-range array index) -- never an error. Raises
    `ValueError` only for a structurally invalid traversal (indexing into
    a non-container), which the caller maps to `MAPPING_INVALID`."""
    current = document
    for segment in path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                return False, None
            current = current[segment]
        elif isinstance(current, list):
            if not segment.isdigit():
                raise ValueError(f"array segment {segment!r} is not a valid index")
            index = int(segment)
            if index < 0 or index >= len(current):
                return False, None
            current = current[index]
        else:
            raise ValueError(  # noqa: TRY004 -- ValueError is this module's own uniform
                # "cannot use this raw path" signal (mirrors the sibling malformed-index
                # branch above), caught uniformly by every caller; TypeError would require
                # widening every except clause in this file for no behavioral benefit.
                f"cannot traverse segment {segment!r} into a non-container value"
            )
    return True, current


def _normalize_value(value: object) -> str | None:
    """CDD-059 SS17/SS29: canonical V1 datatype normalization. Raises
    `ValueError` for array/object results (out of V1) so the caller can
    reject that specific field, never ambiguously stringify a structured
    value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):  # noqa: PLR0124 (NaN check)
            raise ValueError("non-finite decimal value is not representable")
        return repr(value)
    if isinstance(value, (dict, list)):
        raise ValueError(  # noqa: TRY004 -- uniform ValueError signal, see _extract_path above
            "array/object values are out of V1 scope (CDD-059 SS17)"
        )
    raise ValueError(f"unsupported value type {type(value)!r}")


class RestConnector:
    """CDD-059 SS9's one concrete adapter. `endpoint_url`/`auth_mechanism`/
    `auth_header_name`/`credential_env_var_name` come from an already
    tenant-proven `ConnectorConfiguration` row -- this class itself never
    touches tenant authority."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        extraction_plan: FieldExtractionPlan,
        auth_mechanism: str,
        auth_header_name: str | None,
        credential_env_var_name: str,
        max_response_bytes: int = 2 * 1024 * 1024,
        max_records_per_page: int = 500,
        max_fields_per_record: int = 200,
        request_timeout_seconds: int = 30,
        endpoint_security_policy: EndpointSecurityPolicy = _DEFAULT_ENDPOINT_SECURITY_POLICY,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._extraction_plan = extraction_plan
        self._auth_mechanism = auth_mechanism
        self._auth_header_name = auth_header_name
        self._credential_env_var_name = credential_env_var_name
        self._max_response_bytes = max_response_bytes
        self._max_records_per_page = max_records_per_page
        self._max_fields_per_record = max_fields_per_record
        self._request_timeout_seconds = request_timeout_seconds
        self._endpoint_security_policy = endpoint_security_policy
        self._seen_page_urls: set[str] = set()
        test_ca_bundle = os.environ.get(_TEST_CA_BUNDLE_ENV_VAR)
        self._ssl_context = (
            ssl.create_default_context(cafile=test_ca_bundle)
            if test_ca_bundle
            else ssl.create_default_context()
        )
        self._opener = urllib.request.build_opener(
            _NoRedirectHandler, urllib.request.HTTPSHandler(context=self._ssl_context)
        )

    def _auth_headers(self) -> dict[str, str]:
        secret = os.environ.get(self._credential_env_var_name, "")
        if not secret:
            return {}
        if self._auth_mechanism == "API_KEY":
            header_name = self._auth_header_name or "X-API-Key"
            return {header_name: secret}
        if self._auth_mechanism == "BEARER_TOKEN":
            return {"Authorization": f"Bearer {secret}"}
        return {}

    def fetch_page(
        self, *, page_token: str | None, fallback_observed_at: datetime
    ) -> ConnectorPage | ConnectorFetchFailure:
        """`page_token=None` fetches this connector's own configured
        initial `endpoint_url`; any other value is treated as an absolute
        next-page URL and is subject to the identical SSRF policy as the
        initial endpoint (CDD-059 SS29/SS35) -- never trusted merely
        because a prior page from the same run already passed. Loop
        detection tracks every URL fetched across this adapter instance's
        own lifetime (one instance per run, CDD-059 SS21)."""
        url = page_token if page_token is not None else self._endpoint_url
        extraction_plan = self._extraction_plan
        if url in self._seen_page_urls:
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                detail="pagination loop detected: identical page URL repeated",
                retryable=False,
            )
        self._seen_page_urls.add(url)

        try:
            self._endpoint_security_policy.validate(url)
        except SSRFRejected as exc:
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_UNAVAILABLE,
                detail=f"rejected by SSRF policy: {exc.detail}",
                retryable=False,
            )

        last_failure: ConnectorFetchFailure | None = None
        for attempt in range(1, _MAX_RETRY_ATTEMPTS + 1):
            outcome = self._attempt_fetch(url)
            if not isinstance(outcome, ConnectorFetchFailure):
                return self._parse_page(outcome, extraction_plan, fallback_observed_at)
            last_failure = outcome
            if not outcome.retryable or attempt == _MAX_RETRY_ATTEMPTS:
                return outcome
            time.sleep(_RETRY_BASE_DELAY_SECONDS * (_RETRY_BACKOFF_FACTOR ** (attempt - 1)))
        assert last_failure is not None
        return last_failure

    def _attempt_fetch(self, url: str) -> bytes | ConnectorFetchFailure:
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"Accept": "application/json", **self._auth_headers()},
        )
        try:
            with self._opener.open(request, timeout=self._request_timeout_seconds) as response:
                status = response.status
                if 300 <= status < 400:
                    return ConnectorFetchFailure(
                        kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                        detail=f"redirect (HTTP {status}) is never followed (CDD-059 SS32)",
                        retryable=False,
                    )
                content_length = response.headers.get("Content-Length")
                if content_length is not None and int(content_length) > self._max_response_bytes:
                    return ConnectorFetchFailure(
                        kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                        detail="declared Content-Length exceeds max_response_bytes",
                        retryable=False,
                    )
                try:
                    return _read_bounded(response, self._max_response_bytes)
                except ValueError as exc:
                    return ConnectorFetchFailure(
                        kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                        detail=str(exc),
                        retryable=False,
                    )
        except urllib.error.HTTPError as exc:
            if exc.code in _NON_RETRYABLE_AUTH_STATUSES:
                return ConnectorFetchFailure(
                    kind=ConnectorFailureKind.CONNECTOR_AUTHENTICATION_FAILED,
                    detail=f"HTTP {exc.code}",
                    retryable=False,
                )
            retryable = exc.code in _RETRYABLE_HTTP_STATUSES
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                if retry_after is not None:
                    try:
                        time.sleep(min(float(retry_after), 60.0))
                    except ValueError:
                        pass
            return ConnectorFetchFailure(
                kind=(
                    ConnectorFailureKind.CONNECTOR_UNAVAILABLE
                    if retryable
                    else ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID
                ),
                detail=f"HTTP {exc.code}",
                retryable=retryable,
            )
        except TimeoutError:
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_TIMEOUT,
                detail="request timed out",
                retryable=True,
            )
        except urllib.error.URLError as exc:
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_UNAVAILABLE,
                detail=str(exc.reason),
                retryable=True,
            )

    def _parse_page(
        self,
        body: bytes,
        extraction_plan: FieldExtractionPlan,
        fallback_observed_at: datetime,
    ) -> ConnectorPage | ConnectorFetchFailure:
        try:
            document = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                detail=f"malformed JSON page: {exc}",
                retryable=False,
            )
        if not isinstance(document, dict) or "records" not in document:
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                detail="page envelope missing required 'records' key",
                retryable=False,
            )
        raw_records = document["records"]
        if not isinstance(raw_records, list):
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                detail="'records' must be a JSON array",
                retryable=False,
            )
        if len(raw_records) > self._max_records_per_page:
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                detail=f"page contains more than max_records_per_page={self._max_records_per_page}",
                retryable=False,
            )
        next_page = document.get("next")
        if next_page is not None and not isinstance(next_page, str):
            return ConnectorFetchFailure(
                kind=ConnectorFailureKind.CONNECTOR_RESPONSE_INVALID,
                detail="'next' must be a string URL or null",
                retryable=False,
            )

        records: list[ConnectorRecord] = []
        rejected = 0
        for raw_record in raw_records:
            record_or_none = self._extract_record(raw_record, extraction_plan, fallback_observed_at)
            if record_or_none is None:
                rejected += 1
            else:
                records.append(record_or_none)
        return ConnectorPage(
            records=tuple(records), rejected_count=rejected, next_page_token=next_page
        )

    def _extract_record(
        self,
        raw_record: object,
        extraction_plan: FieldExtractionPlan,
        fallback_observed_at: datetime,
    ) -> ConnectorRecord | None:
        if not isinstance(raw_record, dict):
            return None
        try:
            present, raw_id = _extract_path(raw_record, extraction_plan.external_record_id_path)
        except ValueError:
            return None
        if not present or raw_id is None or not isinstance(raw_id, (str, int)):
            return None
        external_record_id = str(raw_id)
        if not external_record_id.strip():
            return None

        observed_at_raw = raw_record.get("__observed_at__")
        observed_at = fallback_observed_at
        if isinstance(observed_at_raw, str):
            try:
                parsed_observed_at = datetime.fromisoformat(observed_at_raw)
            except ValueError:
                return None
            if parsed_observed_at.tzinfo is None:
                return None
            observed_at = parsed_observed_at

        if len(extraction_plan.field_paths) > self._max_fields_per_record:
            return None

        fields: dict[str, str | None] = {}
        for output_key, raw_path in extraction_plan.field_paths.items():
            try:
                present, value = _extract_path(raw_record, raw_path)
            except ValueError:
                return None
            if not present:
                continue  # true absence -- no entry at all (CDD-059 SS11)
            try:
                fields[output_key] = _normalize_value(value)
            except ValueError:
                return None

        try:
            return ConnectorRecord(
                external_record_id=external_record_id, observed_at=observed_at, fields=fields
            )
        except Exception:  # noqa: BLE001 -- any residual domain-level validation failure is a
            # genuine record rejection (CDD-059 SS23), never an uncaught exception escaping
            # into the page-parsing loop.
            return None
