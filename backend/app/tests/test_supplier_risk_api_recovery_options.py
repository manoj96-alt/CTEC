from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.schemas import ReplayRequest
from app.application.supplier_risk_api import SupplierRiskApiService
from app.runtime.execution_state import ExecutionState
from app.runtime.persistence.contracts import (
    RECOVERY_SCOPE,
    AttemptProjection,
    ReplayAuthorization,
    ReplayOptionProjection,
)
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


class _ReplayValidationStore:
    def __init__(
        self,
        logical_id: UUID,
        execution_id: UUID,
        option_id: UUID,
        *,
        option_source: UUID | None = None,
    ) -> None:
        now = datetime.now(UTC)
        self.attempt = AttemptProjection(
            execution_id,
            logical_id,
            ExecutionState.COMPLETED.value,
            now,
            now,
            2,
        )
        self.option = ReplayOptionProjection(
            option_id,
            option_source or execution_id,
            "GRM",
            now,
            True,
            "REPLAY_ELIGIBLE",
            2,
        )
        self.prepared = False

    def list_attempts(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> tuple[AttemptProjection, ...]:
        return (self.attempt,) if tenant_id == "tenant" else ()

    def replay_options(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> tuple[ReplayOptionProjection, ...]:
        return (self.option,) if tenant_id == "tenant" else ()

    def prepare_replay(
        self,
        original_execution_id: UUID,
        authorization: ReplayAuthorization,
        authority: object,
    ) -> object:
        del original_execution_id, authority
        self.prepared = True
        assert RECOVERY_SCOPE in authorization.scopes
        raise RuntimeError("mapping-observed")


def _principal() -> TrustedPrincipal:
    now = datetime.now(UTC)
    return TrustedPrincipal(
        "operator",
        "tenant",
        ("supplier-risk:replay",),
        ("EXECUTION_RECOVERY_OPERATOR",),
        "issuer",
        now - timedelta(seconds=1),
        now + timedelta(hours=1),
    )


def _request(option_id: UUID, revision: int = 2) -> ReplayRequest:
    return ReplayRequest(
        request_identifier=uuid4(),
        correlation_identifier=uuid4(),
        reason="authorized recovery",
        replay_option_reference=option_id,
        expected_revision=revision,
    )


def test_product_replay_scope_maps_to_internal_recovery_authority() -> None:
    logical_id, execution_id, option_id = uuid4(), uuid4(), uuid4()
    replay_store = _ReplayValidationStore(logical_id, execution_id, option_id)
    service = SupplierRiskApiService(object(), replay_store)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="mapping-observed"):
        service.replay(logical_id, _request(option_id), _principal())
    assert replay_store.prepared


@pytest.mark.parametrize(
    "changed_reference,revision,cross_execution",
    [
        (True, 2, False),
        (False, 1, False),
        (False, 2, True),
    ],
)
def test_modified_stale_or_cross_execution_replay_option_is_rejected(
    changed_reference: bool, revision: int, cross_execution: bool
) -> None:
    logical_id, execution_id, option_id = uuid4(), uuid4(), uuid4()
    replay_store = _ReplayValidationStore(
        logical_id,
        execution_id,
        option_id,
        option_source=uuid4() if cross_execution else None,
    )
    service = SupplierRiskApiService(object(), replay_store)  # type: ignore[arg-type]
    submitted = uuid4() if changed_reference else option_id
    with pytest.raises(ValueError, match="REPLAY_OPTION_STALE_OR_INVALID"):
        service.replay(logical_id, _request(submitted, revision), _principal())
    assert not replay_store.prepared
