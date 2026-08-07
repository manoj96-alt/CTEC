import hashlib
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.identity_resolution import EnterpriseEntityResolutionRecord
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionHistoryModel,
    EnterpriseEntityResolutionRecordModel,
)


class EntityResolutionStore:
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
        history = self.session.get(EnterpriseEntityResolutionHistoryModel, key)
        if history is None:
            self.session.add(
                EnterpriseEntityResolutionHistoryModel(
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
