from app.runtime.persistence.repository import SqlAlchemyExecutionStore
from app.tests.test_durable_execution_store import request, store


def test_work_queue_is_tenant_scoped_and_deterministic() -> None:
    execution_store: SqlAlchemyExecutionStore = store()
    admitted = execution_store.admit(request(), b"queue-fingerprint")
    assert admitted.execution_identifier is not None
    values = execution_store.list_executions("tenant", offset=0, limit=25)
    assert len(values) == 1
    assert values[0].logical_execution_id == admitted.execution_identifier
    assert execution_store.list_executions("other-tenant", offset=0, limit=25) == ()


def test_work_queue_status_filter_and_page_bounds() -> None:
    execution_store: SqlAlchemyExecutionStore = store()
    execution_store.admit(request(), b"queue-filter")
    assert execution_store.list_executions("tenant", offset=0, limit=1, state="Accepted")
    assert execution_store.list_executions("tenant", offset=0, limit=1, state="Failed") == ()
