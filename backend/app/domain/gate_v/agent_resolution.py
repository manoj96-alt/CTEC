"""Domain model for Gate V's governed agent resolution (CDD-037 §7-§9,
§14). `GateVAgentResolution` is a frozen, one-shot domain object -- there is
no decision/approval lifecycle here (Gate S owns that entirely, CDD-037
§20); this record only durably explains what the named, deterministic agent
observed and decided (CDD-037 §2, §13). `AGENT_ID` and `PRIORITY_THRESHOLD`
are fixed domain constants, not runtime configuration (CDD-037 §6, §14)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

AGENT_ID = "gate-v-deterministic-notifier-agent"
PRIORITY_THRESHOLD = 50
_MAX_OBSERVATION_TEXT_LENGTH = 500


class AgentResolutionOutcome(StrEnum):
    PROPOSED = "PROPOSED"
    SUPPRESSED = "SUPPRESSED"


@dataclass(frozen=True, slots=True)
class GateVAgentResolution:
    resolution_id: UUID
    tenant_id: str
    agent_id: str
    requested_by: str
    observation_text: str
    priority_score: int
    outcome: AgentResolutionOutcome
    resolved_on: datetime
    approval_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, AgentResolutionOutcome):
            raise ValidationException("outcome must be an AgentResolutionOutcome")
        if self.agent_id != AGENT_ID:
            raise ValidationException(f"Unknown agent_id: {self.agent_id!r}")
        if not isinstance(self.observation_text, str) or not (
            1 <= len(self.observation_text) <= _MAX_OBSERVATION_TEXT_LENGTH
        ):
            raise ValidationException(
                f"observation_text must be a string of length 1..{_MAX_OBSERVATION_TEXT_LENGTH}"
            )
        if not isinstance(self.priority_score, int) or isinstance(self.priority_score, bool):
            raise ValidationException("priority_score must be an integer")
        if not (0 <= self.priority_score <= 100):
            raise ValidationException("priority_score must be between 0 and 100")

        for field_name, actor_value in (("requested_by", self.requested_by),):
            if not isinstance(actor_value, str) or not actor_value.strip():
                raise ValidationException(f"{field_name} must be a non-blank plain string")

        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id is required")

        if self.outcome is AgentResolutionOutcome.PROPOSED and self.approval_id is None:
            raise ValidationException("PROPOSED resolutions must carry an approval_id")
        if self.outcome is AgentResolutionOutcome.SUPPRESSED and self.approval_id is not None:
            raise ValidationException("SUPPRESSED resolutions must not carry an approval_id")

        if self.resolved_on is None or self.resolved_on.tzinfo is None:
            raise ValidationException("resolved_on must include a timezone")
