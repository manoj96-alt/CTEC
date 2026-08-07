from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class AssertionRecordModel(BaseEntity):
    __tablename__ = "assertion_records"
    __table_args__ = (
        Index(
            "idx_assertion_record_identity",
            "subject_entity_id",
            "predicate_relationship_type_id",
            "object_institutional_concept_id",
            "context_id",
        ),
    )

    record_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    subject_entity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("enterprise_entities.enterprise_entity_id")
    )
    predicate_relationship_type_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("relationship_types.relationship_type_id")
    )
    object_institutional_concept_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("institutional_concepts.institutional_concept_id")
    )
    context_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("contexts.context_id"))
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    business_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    structured_reasons: Mapped[str] = mapped_column(String(2000), nullable=False)
    narrative_explanation: Mapped[str] = mapped_column(String(2000), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssertionRecordEntityResolutionEvidenceModel(BaseEntity):
    __tablename__ = "assertion_record_entity_resolution_evidence"
    assertion_record_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("assertion_records.record_id"), primary_key=True
    )
    entity_resolution_record_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("enterprise_entity_resolution_records.record_id"), primary_key=True
    )


class AssertionRecordSemanticResolutionEvidenceModel(BaseEntity):
    __tablename__ = "assertion_record_semantic_resolution_evidence"
    assertion_record_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("assertion_records.record_id"), primary_key=True
    )
    semantic_resolution_record_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("semantic_resolution_records.record_id"), primary_key=True
    )


class AssertionRecordHistoryModel(BaseEntity):
    __tablename__ = "assertion_record_history"
    assertion_identity_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    active_record_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("assertion_records.record_id")
    )
    archived_record_ids: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
