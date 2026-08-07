from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class DecisionEvaluationORM(BaseEntity):
    __tablename__ = "decision_evaluation_records"
    __table_args__ = (
        Index(
            "idx_decision_evaluation_currentness",
            "decision_identity_key",
            "effective_from",
            "produced_timestamp",
            "record_identifier",
        ),
        Index(
            "idx_decision_evaluation_policy_traceability",
            "governing_policy_reference",
            "policy_version",
        ),
    )

    record_identifier: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    knowledge_references: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    decision_recommendation: Mapped[str] = mapped_column(String(1000), nullable=False)
    evaluation_outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    decision_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    structured_reasons: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    narrative_explanation: Mapped[str] = mapped_column(String(4000), nullable=False)
    governing_policy_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    produced_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision_identity_key: Mapped[str] = mapped_column(String(64), nullable=False)
    business_context_reference: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    enterprise_constraint_references: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    policy_satisfied: Mapped[bool] = mapped_column(Boolean(), nullable=False)
