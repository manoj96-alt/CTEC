from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class KnowledgeEvaluationRecordModel(BaseEntity):
    __tablename__ = "knowledge_evaluation_records"
    __table_args__ = (
        Index(
            "idx_knowledge_evaluation_currentness",
            "assertion_record_id",
            "effective_from",
            "produced_at",
            "record_id",
        ),
    )

    record_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    assertion_record_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("assertion_records.record_id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    structured_reasons: Mapped[str] = mapped_column(String(2000), nullable=False)
    narrative_explanation: Mapped[str] = mapped_column(String(2000), nullable=False)
    acceptance_evidence_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    rejection_explanation: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    knowledge_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
