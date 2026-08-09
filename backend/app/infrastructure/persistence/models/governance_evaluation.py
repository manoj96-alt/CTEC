from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class GovernanceEvaluationORM(BaseEntity):
    __tablename__ = "governance_evaluation_records"
    __table_args__ = (
        Index(
            "idx_governance_evaluation_currentness",
            "governed_record_reference",
            "governing_policy_reference",
            "effective_from",
            "produced_timestamp",
            "record_identifier",
        ),
        Index(
            "idx_governance_evaluation_policy_traceability",
            "governing_policy_reference",
            "policy_version",
        ),
    )

    record_identifier: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    governed_record_reference: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    governed_record_type: Mapped[str] = mapped_column(String(48), nullable=False)
    governance_outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    governance_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    structured_reasons: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    narrative_explanation: Mapped[str] = mapped_column(String(4000), nullable=False)
    governing_policy_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    exception_authorization_reference: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    produced_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
