from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.domain.identity_resolution import EntityResolutionEngine, ResolutionPolicy
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionHistoryModel,
    EnterpriseEntityResolutionRecordModel,
)


def test_append_preserves_record_and_archives_previous_understanding(
    migrated_engine: Engine,
) -> None:
    source_id = uuid4()
    engine = EntityResolutionEngine(ResolutionPolicy(version="integration-policy"))
    first = engine.resolve(
        supporting_source_object_ids=(source_id,),
        candidates=(),
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = engine.resolve(
        supporting_source_object_ids=(source_id,),
        candidates=(),
        produced_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    with Session(migrated_engine) as session, session.begin():
        store = EntityResolutionStore(session)
        store.append(first)
        session.flush()
        store.append(second)

    with Session(migrated_engine) as session:
        records = session.scalars(select(EnterpriseEntityResolutionRecordModel)).all()
        history = session.get(
            EnterpriseEntityResolutionHistoryModel,
            EntityResolutionStore.understanding_key((source_id,)),
        )

    assert {record.record_id for record in records} == {first.record_id, second.record_id}
    assert history is not None
    assert history.current_record_identifier == second.record_id
    assert history.historical_record_references == [str(first.record_id)]
