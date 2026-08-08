from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class SemanticResolutionRecordModel(BaseEntity):
    __tablename__ = "semantic_resolution_records"
    __table_args__ = (
        Index("idx_semantic_records_entity_context", "enterprise_entity_id", "context_id"),
    )

    record_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    enterprise_entity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("enterprise_entities.enterprise_entity_id")
    )
    context_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("contexts.context_id"))
    semantic_interpretation_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("institutional_concepts.institutional_concept_id"), nullable=True
    )
    candidate_interpretations: Mapped[list[dict[str, object]]] = mapped_column(
        JSON(), nullable=False
    )
    supporting_entity_resolution_record_ids: Mapped[list[str]] = mapped_column(
        JSON(), nullable=False
    )
    supporting_source_object_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    business_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    structured_reasons: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    narrative_explanation: Mapped[str] = mapped_column(String(2000), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticResolutionHistoryModel(BaseEntity):
    """Externally maintained RFC-011 projection outside immutable SRM records.

    The mapped database column names are retained for migration compatibility only.
    Records never transition between active and archived business states.
    """

    __tablename__ = "semantic_resolution_history"
    understanding_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    current_record_identifier: Mapped[UUID] = mapped_column(
        "active_record_id", Uuid(), ForeignKey("semantic_resolution_records.record_id")
    )
    historical_record_references: Mapped[list[str]] = mapped_column(
        "archived_record_ids", JSON(), nullable=False, default=list
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
