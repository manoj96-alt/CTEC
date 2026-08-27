"""Gate R -- Governed Tool Execution (CDD-035). A provider-neutral executor
over exactly one deterministic, local, read-only, non-consequential tool:
resolve -> authorize -> check eligibility -> validate input -> generate
execution identity -> controlled invocation -> normalize -> record durable
provenance -> return (CDD-035 Sec5). No MCP, no external provider, no
persistence beyond the existing security-audit mechanism, no human
approval, no agent orchestration (CDD-035 Sec6, Sec29-36). This module is
entirely separate from `app.application.mcp_client` and
`app.application.mcp_connector_catalog` (Gate Q) -- never imported,
depended upon, or reinterpreted by either."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Literal, Protocol
from uuid import UUID, uuid4

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditEvent

TOOL_EXECUTION_SCOPE = "tool-execution:execute"


class AuditRepository(Protocol):
    """Structural type satisfied by the existing, unmodified
    `ApiSecurityAuditRepository` (CDD-035 Sec22) -- kept narrow so tests can
    supply a lightweight fake without depending on a live database
    session."""

    def append(self, event: ApiSecurityAuditEvent) -> UUID: ...


@dataclass(frozen=True, slots=True)
class TextDigestInput:
    """CDD-035 Sec9 -- the v1 tool's closed input contract. A caller
    supplying any field other than `text` receives a TypeError from the
    dataclass constructor itself, which `GovernedToolExecutor.execute`
    treats as INVALID_INPUT; there is structurally no field through which
    tenant, principal, scope, or role identity could be supplied."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not (1 <= len(self.text) <= 1024):
            raise ValueError("text must be a string of length 1..1024")


@dataclass(frozen=True, slots=True)
class TextDigestOutput:
    """CDD-035 Sec9 -- the v1 tool's closed output contract."""

    algorithm: Literal["sha256"]
    digest_hex: str


def _compute_text_digest(payload: TextDigestInput) -> TextDigestOutput:
    """CDD-035 Sec9: pure, deterministic, local -- no I/O, no network, no
    filesystem, no database, no system mutation."""
    digest_hex = hashlib.sha256(payload.text.encode("utf-8")).hexdigest()
    return TextDigestOutput(algorithm="sha256", digest_hex=digest_hex)


@dataclass(frozen=True, slots=True)
class GovernedToolDefinition:
    tool_id: str
    description: str
    required_scope: str
    side_effect_class: Literal["READ_ONLY"]
    input_type: type
    output_type: type
    execution_reference: Callable[..., object]


GOVERNED_TOOL_REGISTRY: tuple[GovernedToolDefinition, ...] = (
    GovernedToolDefinition(
        tool_id="gate-r-text-digest",
        description=(
            "Deterministic SHA-256 digest computation over caller-supplied, "
            "length-bounded text. Proves Gate R's governed invocation "
            "pipeline with a real, verifiable, side-effect-free computation "
            "-- not a business action of any existing Gate."
        ),
        required_scope=TOOL_EXECUTION_SCOPE,
        side_effect_class="READ_ONLY",
        input_type=TextDigestInput,
        output_type=TextDigestOutput,
        execution_reference=_compute_text_digest,
    ),
)


class GovernedToolExecutionStatus(str, Enum):
    """CDD-035 Sec20 -- the exact, closed six-value failure/error taxonomy."""

    EXECUTED = "EXECUTED"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    AUTHORIZATION_SCOPE_REQUIRED = "AUTHORIZATION_SCOPE_REQUIRED"
    TOOL_INELIGIBLE = "TOOL_INELIGIBLE"
    INVALID_INPUT = "INVALID_INPUT"
    INVOCATION_FAILED = "INVOCATION_FAILED"


@dataclass(frozen=True, slots=True)
class GovernedToolExecutionResult:
    """CDD-035 Sec19 -- a single, closed, unified result for every outcome."""

    execution_id: UUID | None
    tool_id: str
    status: GovernedToolExecutionStatus
    result: Mapping[str, object] | None
    correlation_id: UUID
    completed_at: datetime
    diagnostic_code: str | None


class GovernedToolExecutor:
    """CDD-035 Sec5. Reuses the existing `ApiSecurityAuditRepository`
    directly (not the narrower `SecurityAuditService` wrapper) because
    CDD-035 Sec22 requires `evidence_resource_reference` for tool identity,
    a field `SecurityAuditService.record` does not expose -- CDD-035 Sec22
    names the repository itself as an equally-authorized reuse target."""

    def __init__(self, audit_repository: AuditRepository) -> None:
        self._audit_repository = audit_repository

    def execute(
        self,
        *,
        principal: TrustedPrincipal,
        tool_id: str,
        input_fields: Mapping[str, object],
    ) -> GovernedToolExecutionResult:
        correlation_id = uuid4()

        tool = next((entry for entry in GOVERNED_TOOL_REGISTRY if entry.tool_id == tool_id), None)
        if tool is None:
            return self._deny(
                correlation_id=correlation_id,
                tool_id=tool_id,
                status=GovernedToolExecutionStatus.UNKNOWN_TOOL,
                principal=principal,
            )

        if tool.required_scope not in principal.scopes:
            return self._deny(
                correlation_id=correlation_id,
                tool_id=tool_id,
                status=GovernedToolExecutionStatus.AUTHORIZATION_SCOPE_REQUIRED,
                principal=principal,
            )

        if tool.side_effect_class != "READ_ONLY":
            return self._deny(
                correlation_id=correlation_id,
                tool_id=tool_id,
                status=GovernedToolExecutionStatus.TOOL_INELIGIBLE,
                principal=principal,
            )

        try:
            validated_input = tool.input_type(**input_fields)
        except (TypeError, ValueError):
            return self._deny(
                correlation_id=correlation_id,
                tool_id=tool_id,
                status=GovernedToolExecutionStatus.INVALID_INPUT,
                principal=principal,
            )

        execution_id = uuid4()

        try:
            output = tool.execution_reference(validated_input)
        except Exception:  # noqa: BLE001 -- CDD-035 Sec19/20: no raw internal
            # exception may escape; every invocation failure is normalized
            # to INVOCATION_FAILED regardless of its underlying cause.
            self._record(
                correlation_id=correlation_id,
                tool_id=tool_id,
                outcome="FAILED",
                diagnostic_code=GovernedToolExecutionStatus.INVOCATION_FAILED.value,
                principal=principal,
                execution_id=execution_id,
            )
            return GovernedToolExecutionResult(
                execution_id=execution_id,
                tool_id=tool_id,
                status=GovernedToolExecutionStatus.INVOCATION_FAILED,
                result=None,
                correlation_id=correlation_id,
                completed_at=datetime.now(UTC),
                diagnostic_code=GovernedToolExecutionStatus.INVOCATION_FAILED.value,
            )

        # `output` is statically `object` (the registry is generic over
        # future tools' output types), but every registered tool's
        # execution_reference is required to return a frozen dataclass
        # instance matching its declared output_type (CDD-035 Sec9).
        result_mapping = asdict(output)  # type: ignore[call-overload]

        # Fail-closed on audit failure (CDD-035 Sec21): if this raises, it
        # propagates out of execute() -- the caller never receives an
        # EXECUTED result for an execution whose provenance was not durably
        # recorded.
        self._record(
            correlation_id=correlation_id,
            tool_id=tool_id,
            outcome="SUCCESS",
            diagnostic_code=GovernedToolExecutionStatus.EXECUTED.value,
            principal=principal,
            execution_id=execution_id,
        )

        return GovernedToolExecutionResult(
            execution_id=execution_id,
            tool_id=tool_id,
            status=GovernedToolExecutionStatus.EXECUTED,
            result=result_mapping,
            correlation_id=correlation_id,
            completed_at=datetime.now(UTC),
            diagnostic_code=None,
        )

    def _deny(
        self,
        *,
        correlation_id: UUID,
        tool_id: str,
        status: GovernedToolExecutionStatus,
        principal: TrustedPrincipal,
    ) -> GovernedToolExecutionResult:
        self._record(
            correlation_id=correlation_id,
            tool_id=tool_id,
            outcome="DENIED",
            diagnostic_code=status.value,
            principal=principal,
            execution_id=None,
        )
        return GovernedToolExecutionResult(
            execution_id=None,
            tool_id=tool_id,
            status=status,
            result=None,
            correlation_id=correlation_id,
            completed_at=datetime.now(UTC),
            diagnostic_code=status.value,
        )

    def _record(
        self,
        *,
        correlation_id: UUID,
        tool_id: str,
        outcome: str,
        diagnostic_code: str,
        principal: TrustedPrincipal,
        execution_id: UUID | None,
    ) -> None:
        """CDD-035 Sec22 -- the exact, frozen audit-field mapping. Raw tool
        input/output never appears here (CDD-035 Sec23)."""
        self._audit_repository.append(
            ApiSecurityAuditEvent(
                operation="EXECUTE_GOVERNED_TOOL",
                endpoint_classification="GOVERNED_TOOL_EXECUTION_APPLICATION_V1",
                event_category="TOOL_EXECUTION",
                outcome=outcome,
                diagnostic_code=diagnostic_code,
                correlation_id=correlation_id,
                tenant_id=principal.tenant_id,
                principal_reference=principal.principal_id,
                execution_id=execution_id,
                attempt_id=None,
                authorization_decision_reference=TOOL_EXECUTION_SCOPE,
                evidence_resource_reference=tool_id,
                source_channel="APPLICATION_LAYER",
            )
        )
