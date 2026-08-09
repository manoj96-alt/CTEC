from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.integration.contracts import AuthorityContext, RiskSeverity, SourceObservation


def authority() -> AuthorityContext:
    now = datetime.now(UTC)
    request_id, correlation_id = uuid4(), uuid4()
    return AuthorityContext(
        "principal",
        "Service",
        "enterprise",
        ("risk-analyst",),
        ("supplier-risk:execute",),
        "AUTHORIZED",
        "authz-1",
        "trusted-gateway",
        request_id,
        correlation_id,
        now - timedelta(seconds=1),
        now + timedelta(minutes=5),
    )


def test_authority_context_is_bound_to_invocation_and_utc() -> None:
    value = authority()
    value.validate_for(
        request_id=value.request_id, correlation_id=value.correlation_id, now=datetime.now(UTC)
    )
    with pytest.raises(ValueError, match="conflict"):
        value.validate_for(
            request_id=uuid4(), correlation_id=value.correlation_id, now=datetime.now(UTC)
        )
    with pytest.raises(ValueError, match="Unsupported"):
        replace(value, schema_version="99").validate_for(
            request_id=value.request_id, correlation_id=value.correlation_id, now=datetime.now(UTC)
        )


def test_source_observation_rejects_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="UTC"):
        SourceObservation(
            uuid4(),
            uuid4(),
            "record",
            "Supplier",
            uuid4(),
            "Risk",
            "active",
            RiskSeverity.HIGH,
            datetime(2026, 1, 1),  # noqa: DTZ001 - deliberately naive negative fixture
            datetime.now(UTC),
            "evidence",
        )
