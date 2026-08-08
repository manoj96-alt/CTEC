import hashlib

from sqlalchemy.orm import Session

from app.domain.semantic_resolution import SemanticResolutionRecord
from app.infrastructure.persistence.models.semantic_resolution import (
    SemanticResolutionHistoryModel,
    SemanticResolutionRecordModel,
)


class SemanticResolutionStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def understanding_key(record: SemanticResolutionRecord) -> str:
        value = f"{record.enterprise_entity_id}:{record.context_id}"
        return hashlib.sha256(value.encode()).hexdigest()

    def append(self, record: SemanticResolutionRecord) -> None:
        candidates = [
            {
                "institutional_concept_id": str(item.institutional_concept_id),
                "business_confidence": item.business_confidence.value,
                "structured_reasons": list(item.structured_reasons),
                "narrative_explanation": item.narrative_explanation,
            }
            for item in record.candidate_interpretations
        ]
        self.session.add(
            SemanticResolutionRecordModel(
                record_id=record.record_id,
                enterprise_entity_id=record.enterprise_entity_id,
                context_id=record.context_id,
                semantic_interpretation_id=record.semantic_interpretation_id,
                candidate_interpretations=candidates,
                supporting_entity_resolution_record_ids=[
                    str(x) for x in record.supporting_entity_resolution_record_ids
                ],
                supporting_source_object_ids=[str(x) for x in record.supporting_source_object_ids],
                outcome=record.outcome.value,
                business_confidence=record.business_confidence.value,
                structured_reasons=list(record.structured_reasons),
                narrative_explanation=record.narrative_explanation,
                policy_version=record.policy_version,
                produced_at=record.produced_at,
            )
        )
        key = self.understanding_key(record)
        history = self.session.get(SemanticResolutionHistoryModel, key)
        if history is None:
            self.session.add(
                SemanticResolutionHistoryModel(
                    understanding_key=key,
                    active_record_id=record.record_id,
                    archived_record_ids=[],
                    updated_at=record.produced_at,
                )
            )
        else:
            history.archived_record_ids = [
                *history.archived_record_ids,
                str(history.active_record_id),
            ]
            history.active_record_id = record.record_id
            history.updated_at = record.produced_at
