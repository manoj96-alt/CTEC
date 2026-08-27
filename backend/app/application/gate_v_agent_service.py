"""Gate V -- Governed Agent Resolution application service (CDD-037 §2,
§8-§10, §12, §14, §20-§21). `GateVApplicationService.resolve()` implements
CDD-037's exact, frozen, deterministic decision rule (§14) and is the only
code path that calls `GateSApprovalService.request()` on the agent's
behalf -- it never calls `approve()`, `reject()`, `decide()`, or
`execute()` (§12, §20): the named agent has no path to human approval
authority. It is entirely independent of `GovernedToolExecutor`/
`GOVERNED_TOOL_REGISTRY` (Gate R) and of `mcp_client`/`mcp_connector_catalog`
(Gate Q): no import, no call, no shared code."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.gate_s_approval_service import GateSApprovalService
from app.domain.gate_v.agent_resolution import (
    AGENT_ID,
    PRIORITY_THRESHOLD,
    AgentResolutionOutcome,
    GateVAgentResolution,
)
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditEvent
from app.infrastructure.persistence.gate_v_agent_resolution_repository import (
    GateVAgentResolutionRepository,
)

_ENDPOINT_CLASSIFICATION = "GOVERNED_AGENT_ORCHESTRATION_API_V1"


class AuditRepository(Protocol):
    """Structural type satisfied by the existing, unmodified
    `ApiSecurityAuditRepository` -- kept narrow, and deliberately not
    imported from `gate_s_approval_service.py` or `governed_tool_executor.py`
    (CDD-037 §25-§27: Gate V shares no audit code with Gate Q, Gate R, or
    Gate S)."""

    def append(self, event: ApiSecurityAuditEvent) -> UUID: ...


class GateVApplicationService:
    def __init__(
        self,
        *,
        repository: GateVAgentResolutionRepository,
        gate_s_service: GateSApprovalService,
        audit_repository: AuditRepository,
    ) -> None:
        self._repository = repository
        self._gate_s_service = gate_s_service
        self._audit_repository = audit_repository

    def resolve(
        self,
        *,
        principal: TrustedPrincipal,
        observation_text: str,
        priority_score: int,
        now: datetime | None = None,
    ) -> GateVAgentResolution:
        moment = now if now is not None else datetime.now(UTC)

        if priority_score >= PRIORITY_THRESHOLD:
            outcome = AgentResolutionOutcome.PROPOSED
            note_text = f"Agent observation: {observation_text}"
            gate_s_request = self._gate_s_service.request(
                principal=principal, note_text=note_text, now=moment
            )
            approval_id = gate_s_request.approval_id
        else:
            outcome = AgentResolutionOutcome.SUPPRESSED
            approval_id = None

        resolution = GateVAgentResolution(
            resolution_id=uuid4(),
            tenant_id=principal.tenant_id,
            agent_id=AGENT_ID,
            requested_by=principal.principal_id,
            observation_text=observation_text,
            priority_score=priority_score,
            outcome=outcome,
            approval_id=approval_id,
            resolved_on=moment,
        )
        self._repository.create(resolution)
        self._record(
            outcome_status="SUCCESS",
            diagnostic_code=outcome.value,
            principal=principal,
            evidence_resource_reference=str(resolution.resolution_id),
        )
        return resolution

    def _record(
        self,
        *,
        outcome_status: str,
        diagnostic_code: str,
        principal: TrustedPrincipal,
        evidence_resource_reference: str,
    ) -> None:
        """CDD-037 §21 -- the exact, frozen audit-field mapping. Raw
        `observation_text` never appears here."""
        self._audit_repository.append(
            ApiSecurityAuditEvent(
                operation="GATE_V_AGENT_RESOLUTION",
                endpoint_classification=_ENDPOINT_CLASSIFICATION,
                event_category="AGENT_RESOLUTION",
                outcome=outcome_status,
                diagnostic_code=diagnostic_code,
                correlation_id=uuid4(),
                tenant_id=principal.tenant_id,
                principal_reference=principal.principal_id,
                execution_id=None,
                authorization_decision_reference="governed-agent:propose",
                evidence_resource_reference=evidence_resource_reference,
                source_channel="HTTP_API",
            )
        )
