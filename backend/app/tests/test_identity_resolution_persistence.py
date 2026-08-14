from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.identity_resolution import EntityResolutionEngine, ResolutionPolicy
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionHistoryModel,
    EnterpriseEntityResolutionRecordModel,
)
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _seed_source_object(session: Session, *, tenant_id: str, source_object_id: UUID) -> None:
    system_id = uuid4()
    session.add(
        SourceSystem(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=f"Source System {system_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
        )
    )
    session.flush()
    session.add(
        SourceObject(
            source_object_id=source_object_id,
            tenant_id=tenant_id,
            source_object_name=f"Source Object {source_object_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            source_system_id=system_id,
        )
    )
    session.flush()


def test_append_preserves_record_and_archives_previous_understanding(
    migrated_engine: Engine,
) -> None:
    # A tenant id unique to this test run: migrated_engine is a session-scoped
    # fixture shared with other test modules, so a literal like "tenant-a"
    # could collide with data another module writes under the same name.
    tenant_id = f"tenant-a-{uuid4()}"
    source_id = uuid4()
    with Session(migrated_engine) as seed_session, seed_session.begin():
        _seed_source_object(seed_session, tenant_id=tenant_id, source_object_id=source_id)

    engine = EntityResolutionEngine(ResolutionPolicy(version="integration-policy"))
    first = engine.resolve(
        tenant_id=tenant_id,
        supporting_source_object_ids=(source_id,),
        candidates=(),
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = engine.resolve(
        tenant_id=tenant_id,
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
        # Scoped to this test's own record ids and tenant, not an unfiltered
        # scan of the whole table: other tests writing to the same
        # session-scoped database must not affect this assertion.
        records = session.scalars(
            select(EnterpriseEntityResolutionRecordModel).where(
                EnterpriseEntityResolutionRecordModel.record_id.in_(
                    (first.record_id, second.record_id)
                ),
                EnterpriseEntityResolutionRecordModel.tenant_id == tenant_id,
            )
        ).all()
        history = session.get(
            EnterpriseEntityResolutionHistoryModel,
            EntityResolutionStore.understanding_key((source_id,)),
        )

    assert {record.record_id for record in records} == {first.record_id, second.record_id}
    assert history is not None
    assert history.tenant_id == tenant_id
    assert history.current_record_identifier == second.record_id
    assert history.historical_record_references == [str(first.record_id)]
