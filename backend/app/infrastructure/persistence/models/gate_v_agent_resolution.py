"""ORM model for Gate V's governed agent resolution (CDD-037 §15). One
table, `gate_v_agent_resolutions` -- insert-only, no update lifecycle
(CDD-037 §13, §22). `approval_id` is a read-only reference into Gate S's
existing `gate_s_approval_requests` table; declaring this foreign key does
not modify that table's own definition (CDD-037 §15, §27)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class GateVAgentResolutionORM(BaseEntity):
    __tablename__ = "gate_v_agent_resolutions"

    __table_args__ = (Index("idx_gate_v_agent_resolutions_tenant_id", "tenant_id"),)

    resolution_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    observation_text: Mapped[str] = mapped_column(String(500), nullable=False)
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    approval_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "gate_s_approval_requests.approval_id",
            name="fk_gate_v_agent_resolutions_approval_id",
        ),
        nullable=True,
    )
    resolved_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
