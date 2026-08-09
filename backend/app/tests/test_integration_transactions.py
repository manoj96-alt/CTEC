from app.runtime.execution_state import ExecutionState
from app.tests.test_supplier_risk_pipeline import (
    RecordingPersistence,
    build_request,
    invoke,
    runtime_and_persistence,
)


class AssertionFailurePersistence(RecordingPersistence):
    def assertion(self, record: object) -> None:
        raise RuntimeError("database unavailable")


def test_technical_failure_preserves_prior_capability_commits() -> None:
    runtime, original = runtime_and_persistence()
    failing = AssertionFailurePersistence()
    dependencies = runtime._orchestrator._ports.erm._dependencies  # type: ignore[attr-defined]
    object.__setattr__(dependencies, "persistence", failing)
    _, snapshot = invoke(runtime, build_request())
    assert snapshot.state is ExecutionState.FAILED
    assert len(failing.records) == 2
    assert not original.records
