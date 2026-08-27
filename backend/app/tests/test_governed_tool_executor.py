"""Focused Gate R (CDD-035) test suite for `GovernedToolExecutor`."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application import governed_tool_executor as gte
from app.application.governed_tool_executor import (
    GOVERNED_TOOL_REGISTRY,
    TOOL_EXECUTION_SCOPE,
    GovernedToolDefinition,
    GovernedToolExecutionStatus,
    GovernedToolExecutor,
    TextDigestInput,
    TextDigestOutput,
)
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditEvent

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeAuditRepository:
    def __init__(self) -> None:
        self.events: list[ApiSecurityAuditEvent] = []

    def append(self, event: ApiSecurityAuditEvent) -> UUID:
        self.events.append(event)
        return uuid4()


class RaisingAuditRepository:
    def append(self, event: ApiSecurityAuditEvent) -> UUID:
        raise RuntimeError("durable provenance write failed")


def make_principal(*, scopes: tuple[str, ...], tenant_id: str = "tenant-a") -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="analyst-jane",
        tenant_id=tenant_id,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


@pytest.fixture
def spy_tool(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Wraps the real, registered tool function with a call-counting spy,
    installed in place of the module-level registry so invocation-count
    assertions are exact without duplicating executor logic."""
    mock = Mock(wraps=gte._compute_text_digest)
    definition = GovernedToolDefinition(
        tool_id="gate-r-text-digest",
        description="test",
        required_scope=TOOL_EXECUTION_SCOPE,
        side_effect_class="READ_ONLY",
        input_type=TextDigestInput,
        output_type=TextDigestOutput,
        execution_reference=mock,
    )
    monkeypatch.setattr(gte, "GOVERNED_TOOL_REGISTRY", (definition,))
    return mock


def test_authorized_principal_executes_and_receives_normalized_success(
    spy_tool: Mock,
) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    result = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
    )

    expected_digest = hashlib.sha256(b"hello").hexdigest()
    assert result.status == GovernedToolExecutionStatus.EXECUTED
    assert result.result == {"algorithm": "sha256", "digest_hex": expected_digest}
    assert result.execution_id is not None
    assert result.diagnostic_code is None
    assert spy_tool.call_count == 1


def test_deterministic_input_produces_deterministic_output(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    first = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "repeatable"}
    )
    second = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "repeatable"}
    )

    assert first.result == second.result


def test_missing_execution_scope_fails_closed_with_zero_invocation(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=())

    result = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
    )

    assert result.status == GovernedToolExecutionStatus.AUTHORIZATION_SCOPE_REQUIRED
    assert result.execution_id is None
    assert spy_tool.call_count == 0


def test_discovery_scope_alone_cannot_execute(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=("mcp-connector:read",))

    result = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
    )

    assert result.status == GovernedToolExecutionStatus.AUTHORIZATION_SCOPE_REQUIRED
    assert spy_tool.call_count == 0


def test_unknown_tool_fails_closed_with_zero_invocation(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    result = executor.execute(
        principal=principal, tool_id="does-not-exist", input_fields={"text": "hello"}
    )

    assert result.status == GovernedToolExecutionStatus.UNKNOWN_TOOL
    assert spy_tool.call_count == 0


def test_ineligible_non_read_only_registration_cannot_execute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = Mock(wraps=gte._compute_text_digest)
    ineligible_definition = GovernedToolDefinition(
        tool_id="gate-r-text-digest",
        description="test",
        required_scope=TOOL_EXECUTION_SCOPE,
        side_effect_class="WRITE",  # type: ignore[arg-type]
        input_type=TextDigestInput,
        output_type=TextDigestOutput,
        execution_reference=mock,
    )
    monkeypatch.setattr(gte, "GOVERNED_TOOL_REGISTRY", (ineligible_definition,))
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    result = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
    )

    assert result.status == GovernedToolExecutionStatus.TOOL_INELIGIBLE
    assert mock.call_count == 0


def test_malformed_input_fails_closed_with_zero_invocation(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    result = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": ""}
    )

    assert result.status == GovernedToolExecutionStatus.INVALID_INPUT
    assert spy_tool.call_count == 0


def test_unexpected_input_field_fails_closed(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    result = executor.execute(
        principal=principal,
        tool_id="gate-r-text-digest",
        input_fields={"text": "hello", "extra_field": "unexpected"},
    )

    assert result.status == GovernedToolExecutionStatus.INVALID_INPUT
    assert spy_tool.call_count == 0


def test_identity_and_tenant_authority_cannot_be_injected_through_input(
    spy_tool: Mock,
) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,), tenant_id="tenant-a")

    result = executor.execute(
        principal=principal,
        tool_id="gate-r-text-digest",
        input_fields={"text": "hello", "tenant_id": "attacker-tenant", "principal_id": "root"},
    )

    assert result.status == GovernedToolExecutionStatus.INVALID_INPUT
    assert spy_tool.call_count == 0


def test_invocation_failure_is_normalized_and_no_raw_exception_escapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failing = Mock(side_effect=RuntimeError("boom"))
    definition = GovernedToolDefinition(
        tool_id="gate-r-text-digest",
        description="test",
        required_scope=TOOL_EXECUTION_SCOPE,
        side_effect_class="READ_ONLY",
        input_type=TextDigestInput,
        output_type=TextDigestOutput,
        execution_reference=failing,
    )
    monkeypatch.setattr(gte, "GOVERNED_TOOL_REGISTRY", (definition,))
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    result = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
    )

    assert result.status == GovernedToolExecutionStatus.INVOCATION_FAILED
    assert result.result is None
    assert result.execution_id is not None


def test_tenant_and_principal_provenance_come_from_trusted_principal(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,), tenant_id="tenant-xyz")

    executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
    )

    assert len(repository.events) == 1
    event = repository.events[0]
    assert event.tenant_id == "tenant-xyz"
    assert event.principal_reference == "analyst-jane"


def test_tool_identity_execution_id_authorization_outcome_and_correlation_are_durable(
    spy_tool: Mock,
) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    result = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
    )

    assert len(repository.events) == 1
    event = repository.events[0]
    assert event.evidence_resource_reference == "gate-r-text-digest"
    assert event.execution_id == result.execution_id
    assert event.authorization_decision_reference == TOOL_EXECUTION_SCOPE
    assert event.outcome == "SUCCESS"
    assert event.diagnostic_code == "EXECUTED"
    assert event.correlation_id == result.correlation_id
    assert event.operation == "EXECUTE_GOVERNED_TOOL"


def test_denial_audit_has_no_execution_id(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=())

    executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
    )

    assert len(repository.events) == 1
    assert repository.events[0].execution_id is None
    assert repository.events[0].outcome == "DENIED"


def test_raw_input_and_output_are_absent_from_audit(spy_tool: Mock) -> None:
    repository = FakeAuditRepository()
    executor = GovernedToolExecutor(repository)
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))
    secret_text = "unique-marker-payload-should-never-be-audited"

    result = executor.execute(
        principal=principal, tool_id="gate-r-text-digest", input_fields={"text": secret_text}
    )

    assert len(repository.events) == 1
    event = repository.events[0]
    for value in asdict(event).values():
        assert secret_text not in str(value)
        assert result.result["digest_hex"] not in str(value)


def test_provenance_recording_failure_prevents_success_result(spy_tool: Mock) -> None:
    executor = GovernedToolExecutor(RaisingAuditRepository())
    principal = make_principal(scopes=(TOOL_EXECUTION_SCOPE,))

    with pytest.raises(RuntimeError):
        executor.execute(
            principal=principal, tool_id="gate-r-text-digest", input_fields={"text": "hello"}
        )


def test_exactly_one_tool_is_registered() -> None:
    assert len(GOVERNED_TOOL_REGISTRY) == 1
    assert GOVERNED_TOOL_REGISTRY[0].tool_id == "gate-r-text-digest"
    assert GOVERNED_TOOL_REGISTRY[0].side_effect_class == "READ_ONLY"
