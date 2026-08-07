# Generated from ECOM Physical Data Model v1.3. Do not edit manually.
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class ReasonDecisionObjectives(BaseEntity):
    __tablename__ = "reason_decision_objectives"

    reason_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("reasons.reason_id"), nullable=False, primary_key=True
    )
    decision_objective_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("decision_objectives.decision_objective_id"),
        nullable=False,
        primary_key=True,
    )
