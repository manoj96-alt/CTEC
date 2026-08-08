from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.knowledge_engine import (
    KnowledgeConfidence,
    KnowledgeEvaluationRecord,
    KnowledgeOutcome,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.assertion_record import AssertionRecordModel
from app.infrastructure.persistence.models.knowledge_evaluation import (
    KnowledgeEvaluationRecordModel,
)


class KnowledgeEvaluationStore:
    """Append-only storage and RFC-011 currentness projection."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, record: KnowledgeEvaluationRecord) -> None:
        if self.session.get(AssertionRecordModel, record.assertion_record_id) is None:
            raise ValidationException("Knowledge Evaluation requires an existing Assertion Record")
        self.session.add(
            KnowledgeEvaluationRecordModel(
                record_id=record.record_id,
                assertion_record_id=record.assertion_record_id,
                outcome=record.outcome.value,
                structured_reasons="\n".join(record.structured_reasons),
                narrative_explanation=record.narrative_explanation,
                acceptance_evidence_id=record.acceptance_evidence_id,
                rejection_explanation=record.rejection_explanation,
                knowledge_confidence=record.knowledge_confidence.value,
                policy_version=record.policy_version,
                effective_from=record.effective_from,
                produced_at=record.produced_at,
            )
        )

    def history(self, assertion_record_id: UUID) -> tuple[KnowledgeEvaluationRecord, ...]:
        statement = self._ordered_statement(assertion_record_id)
        return tuple(self._to_domain(model) for model in self.session.scalars(statement))

    def current(
        self, assertion_record_id: UUID, *, as_of: datetime
    ) -> KnowledgeEvaluationRecord | None:
        if as_of.tzinfo is None:
            raise ValueError("Currentness timestamp must be timezone-aware")
        statement = self._ordered_statement(assertion_record_id).where(
            KnowledgeEvaluationRecordModel.effective_from <= as_of
        )
        model = self.session.scalars(statement.limit(1)).first()
        return self._to_domain(model) if model is not None else None

    @staticmethod
    def _ordered_statement(
        assertion_record_id: UUID,
    ) -> Select[tuple[KnowledgeEvaluationRecordModel]]:
        return (
            select(KnowledgeEvaluationRecordModel)
            .where(KnowledgeEvaluationRecordModel.assertion_record_id == assertion_record_id)
            .order_by(
                KnowledgeEvaluationRecordModel.effective_from.desc(),
                KnowledgeEvaluationRecordModel.produced_at.desc(),
                KnowledgeEvaluationRecordModel.record_id.desc(),
            )
        )

    @staticmethod
    def _to_domain(model: KnowledgeEvaluationRecordModel) -> KnowledgeEvaluationRecord:
        return KnowledgeEvaluationRecord(
            record_id=model.record_id,
            assertion_record_id=model.assertion_record_id,
            outcome=KnowledgeOutcome(model.outcome),
            structured_reasons=tuple(model.structured_reasons.splitlines()),
            narrative_explanation=model.narrative_explanation,
            acceptance_evidence_id=model.acceptance_evidence_id,
            rejection_explanation=model.rejection_explanation,
            knowledge_confidence=KnowledgeConfidence(model.knowledge_confidence),
            policy_version=model.policy_version,
            effective_from=model.effective_from,
            produced_at=model.produced_at,
        )
