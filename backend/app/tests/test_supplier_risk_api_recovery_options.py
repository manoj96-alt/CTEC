from datetime import UTC, datetime

from app.runtime.execution_state import ExecutionState
from app.runtime.persistence.repository import SqlAlchemyExecutionStore
from app.tests.test_durable_execution_store import request, store


def test_replay_options_are_tenant_scoped_and_reference_committed_stage() -> None:
    execution_store: SqlAlchemyExecutionStore = store()
    invocation = request()
    admitted = execution_store.admit(invocation, b"options")
    execution_id = admitted.execution_identifier
    assert execution_id is not None
    execution_store.advance(execution_id, ExecutionState.EXECUTING)
    execution_store.checkpoint(
        execution_id,
        stage_name="ERM",
        stage_ordinal=0,
        input_payload=invocation.opaque_payload,
        output_payload=invocation.opaque_payload,
        artifact_references=(),
        completed_at=datetime.now(UTC),
    )
    execution_store.advance(execution_id, ExecutionState.FAILED)
    options = execution_store.replay_options(execution_id, "tenant")
    assert len(options) == 1 and options[0].eligible
    assert options[0].stage_name == "ERM"
    assert execution_store.replay_options(execution_id, "other-tenant") == ()
