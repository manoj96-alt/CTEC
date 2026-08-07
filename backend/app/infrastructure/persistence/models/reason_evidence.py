# Generated from ECOM Physical Data Model v1.3. Do not edit manually.
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class ReasonEvidence(BaseEntity):
    __tablename__ = "reason_evidence"

    reason_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("reasons.reason_id"), nullable=False, primary_key=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("evidences.evidence_id"), nullable=False, primary_key=True
    )
