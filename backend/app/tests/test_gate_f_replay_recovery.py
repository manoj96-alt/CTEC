"""Gate F replay/recovery compatibility tests (CDD-015 §20 F2.2 addition,
§35). Gate F's new adapters plug into the existing six-port CDD-010/CDD-012
durable-execution and replay model unmodified (no seventh stage, no change
to `runtime/recovery.py`); no admission entrypoint for Gate F exists yet,
so there is no live runtime execution to actually replay. What CDD-015 §20
requires -- and what is implemented here -- is the persistence-layer
contract a future replay-aware caller depends on: a resume MUST look up
and reuse the same `decision_evaluation_id` for a logical decision via the
`logical_execution_id` audit-trail column, rather than minting a new one.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.domain.decision_engine import DecisionEvaluationGroupModel
from app.infrastructure.persistence.decision_repository import DecisionEvaluationRepositoryImpl

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_fresh_evaluation_mints_a_new_group_and_logical_execution_id(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"gate-f-replay-{uuid4()}"
    logical_execution_id = uuid4()
    decision_evaluation_id = uuid4()

    with factory() as session:
        DecisionEvaluationRepositoryImpl(session).create_group(
            DecisionEvaluationGroupModel(
                decision_evaluation_id=decision_evaluation_id,
                tenant_id=tenant_id,
                created_at=NOW,
                logical_execution_id=logical_execution_id,
            )
        )
        session.commit()

    with factory() as session:
        repository = DecisionEvaluationRepositoryImpl(session)
        by_id = repository.group_by_id(decision_evaluation_id, tenant_id=tenant_id)
        by_logical_execution = repository.group_by_logical_execution_id(
            logical_execution_id, tenant_id=tenant_id
        )

    assert by_id is not None
    assert by_logical_execution is not None
    assert by_id.decision_evaluation_id == by_logical_execution.decision_evaluation_id


def test_resume_reuses_the_same_decision_evaluation_id(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"gate-f-replay-{uuid4()}"
    logical_execution_id = uuid4()
    original_decision_evaluation_id = uuid4()

    with factory() as session:
        DecisionEvaluationRepositoryImpl(session).create_group(
            DecisionEvaluationGroupModel(
                decision_evaluation_id=original_decision_evaluation_id,
                tenant_id=tenant_id,
                created_at=NOW,
                logical_execution_id=logical_execution_id,
            )
        )
        session.commit()

    with factory() as session:
        existing = DecisionEvaluationRepositoryImpl(session).group_by_logical_execution_id(
            logical_execution_id, tenant_id=tenant_id
        )
    resumed_decision_evaluation_id = (
        existing.decision_evaluation_id if existing is not None else uuid4()
    )

    assert resumed_decision_evaluation_id == original_decision_evaluation_id


def test_different_logical_execution_ids_do_not_collide(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"gate-f-replay-{uuid4()}"
    first_logical_execution_id = uuid4()
    second_logical_execution_id = uuid4()

    with factory() as session:
        repository = DecisionEvaluationRepositoryImpl(session)
        repository.create_group(
            DecisionEvaluationGroupModel(
                decision_evaluation_id=uuid4(),
                tenant_id=tenant_id,
                created_at=NOW,
                logical_execution_id=first_logical_execution_id,
            )
        )
        repository.create_group(
            DecisionEvaluationGroupModel(
                decision_evaluation_id=uuid4(),
                tenant_id=tenant_id,
                created_at=NOW,
                logical_execution_id=second_logical_execution_id,
            )
        )
        session.commit()

    with factory() as session:
        repository = DecisionEvaluationRepositoryImpl(session)
        first = repository.group_by_logical_execution_id(
            first_logical_execution_id, tenant_id=tenant_id
        )
        second = repository.group_by_logical_execution_id(
            second_logical_execution_id, tenant_id=tenant_id
        )

    assert first is not None
    assert second is not None
    assert first.decision_evaluation_id != second.decision_evaluation_id


def test_logical_execution_id_lookup_is_tenant_scoped(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_a = f"gate-f-replay-a-{uuid4()}"
    tenant_b = f"gate-f-replay-b-{uuid4()}"
    logical_execution_id = uuid4()

    with factory() as session:
        DecisionEvaluationRepositoryImpl(session).create_group(
            DecisionEvaluationGroupModel(
                decision_evaluation_id=uuid4(),
                tenant_id=tenant_a,
                created_at=NOW,
                logical_execution_id=logical_execution_id,
            )
        )
        session.commit()

    with factory() as session:
        repository = DecisionEvaluationRepositoryImpl(session)
        assert (
            repository.group_by_logical_execution_id(logical_execution_id, tenant_id=tenant_a)
            is not None
        )
        assert (
            repository.group_by_logical_execution_id(logical_execution_id, tenant_id=tenant_b)
            is None
        )
