"""Repository for Gate V's governed agent resolution (CDD-037 §15, §24;
Gate V Artifact Authorization §4, §15). `create` is the sole method in this
entire module -- and, per CDD-037 §24, in the entire codebase -- that ever
writes a `GateVAgentResolutionORM` row. There is no update/delete method:
resolutions are insert-only (CDD-037 §13, §22)."""

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.gate_v.agent_resolution import AgentResolutionOutcome, GateVAgentResolution
from app.infrastructure.persistence.models.gate_v_agent_resolution import (
    GateVAgentResolutionORM,
)


class GateVAgentResolutionRepository(Protocol):
    def create(self, resolution: GateVAgentResolution) -> None: ...

    def get_by_id(self, resolution_id: UUID) -> GateVAgentResolution | None: ...


class GateVAgentResolutionRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, resolution: GateVAgentResolution) -> None:
        self.session.add(
            GateVAgentResolutionORM(
                resolution_id=resolution.resolution_id,
                tenant_id=resolution.tenant_id,
                agent_id=resolution.agent_id,
                requested_by=resolution.requested_by,
                observation_text=resolution.observation_text,
                priority_score=resolution.priority_score,
                outcome=resolution.outcome.value,
                approval_id=resolution.approval_id,
                resolved_on=resolution.resolved_on,
            )
        )

    def get_by_id(self, resolution_id: UUID) -> GateVAgentResolution | None:
        model = self.session.get(GateVAgentResolutionORM, resolution_id)
        if model is None:
            return None
        return GateVAgentResolution(
            resolution_id=model.resolution_id,
            tenant_id=model.tenant_id,
            agent_id=model.agent_id,
            requested_by=model.requested_by,
            observation_text=model.observation_text,
            priority_score=model.priority_score,
            outcome=AgentResolutionOutcome(model.outcome),
            approval_id=model.approval_id,
            resolved_on=model.resolved_on,
        )
