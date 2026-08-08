import hashlib
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.identity_resolution import EnterpriseEntityResolutionRecord
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionHistoryModel,
    EnterpriseEntityResolutionRecordModel,
)


class EntityResolutionStore:
    """Append immutable records and maintain currentness outside record state."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def understanding_key(source_ids: tuple[UUID, ...]) -> str:
        canonical = ",".join(sorted(str(value) for value in source_ids))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def append(self, record: EnterpriseEntityResolutionRecord) -> None:
        model = EnterpriseEntityResolutionRecordModel(
            record_id=record.record_id,
            enterprise_entity_id=record.enterprise_entity_id,
            supporting_source_object_ids=[
                str(value) for value in record.supporting_source_object_ids
            ],
            outcome=record.outcome.value,
            business_confidence=record.business_confidence.value,
            structured_reasons=list(record.structured_reasons),
            narrative_explanation=record.narrative_explanation,
            produced_at=record.produced_at,
            policy_version=record.policy_version,
        )
        self.session.add(model)
        key = self.understanding_key(record.supporting_source_object_ids)
        record_history = self.session.get(EnterpriseEntityResolutionHistoryModel, key)
        if record_history is None:
            self.session.add(
                EnterpriseEntityResolutionHistoryModel(
                    understanding_key=key,
                    current_record_identifier=record.record_id,
                    historical_record_references=[],
                    updated_at=record.produced_at,
                )
            )
        else:
            record_history.historical_record_references = [
                *record_history.historical_record_references,
                str(record_history.current_record_identifier),
            ]
            record_history.current_record_identifier = record.record_id
            record_history.updated_at = record.produced_at
