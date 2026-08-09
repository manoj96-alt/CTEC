"""PostgreSQL-backed atomic execution admission and durable observation."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.runtime.contracts import ExecutionSnapshot, InvocationRequest
from app.runtime.execution_state import ExecutionState, initial_transition, transition
from app.runtime.execution_store import AdmissionResult
from app.runtime.persistence.contracts import HandoffProtector, ReplayAuthorization
from app.runtime.persistence.models import (
    RuntimeArtifactReferenceORM,
    RuntimeExecutionORM,
    RuntimeHandoffORM,
    RuntimeRecoveryAttemptORM,
    RuntimeResultORM,
    RuntimeStageORM,
)


class SqlAlchemyExecutionStore:
    """Durable store with database-enforced admission and optimistic revision."""

    def __init__(
        self, session_factory: sessionmaker[Session], handoff_protector: HandoffProtector
    ) -> None:
        self._sessions = session_factory
        self._handoff_protector = handoff_protector

    def admit(self, request: InvocationRequest, payload_fingerprint: bytes) -> AdmissionResult:
        tenant = (
            request.authority_context.organization_id if request.authority_context else "legacy"
        )
        control = sha256(
            repr((request.control_metadata_version, request.authority_context)).encode()
        ).digest()
        session = self._sessions()
        try:
            existing = session.scalar(
                select(RuntimeExecutionORM).where(
                    RuntimeExecutionORM.tenant_id == tenant,
                    RuntimeExecutionORM.protocol_version == request.protocol_version,
                    RuntimeExecutionORM.request_id == request.request_identifier,
                )
            )
            if existing:
                conflict = (
                    existing.payload_fingerprint != payload_fingerprint
                    or existing.control_fingerprint != control
                )
                return AdmissionResult(None if conflict else existing.execution_id, False, conflict)
            execution_id = uuid4()
            session.add(
                RuntimeExecutionORM(
                    execution_id=execution_id,
                    logical_execution_id=execution_id,
                    tenant_id=tenant,
                    protocol_version=request.protocol_version,
                    integration_contract_version="1.1",
                    request_id=request.request_identifier,
                    correlation_id=request.correlation_identifier,
                    session_id=request.session_identifier,
                    request_classification=request.request_classification,
                    payload_fingerprint=payload_fingerprint,
                    control_fingerprint=control,
                    state=ExecutionState.ACCEPTED.value,
                    admitted_at=datetime.now(UTC),
                    revision=0,
                    legal_hold=False,
                    retention_until=None,
                )
            )
            session.commit()
            return AdmissionResult(execution_id, True, False)
        except IntegrityError:
            session.rollback()
            return self.admit(request, payload_fingerprint)
        finally:
            session.close()

    def get(self, execution_identifier: UUID) -> ExecutionSnapshot | None:
        session = self._sessions()
        try:
            row = session.get(RuntimeExecutionORM, execution_identifier)
            if row is None:
                return None
            result = session.scalar(
                select(RuntimeResultORM).where(
                    RuntimeResultORM.execution_id == execution_identifier
                )
            )
            return ExecutionSnapshot(
                execution_identifier=row.execution_id,
                execution_reference=row.logical_execution_id,
                protocol_version=row.protocol_version,
                correlation_identifier=row.correlation_id,
                request_identifier=row.request_id,
                session_identifier=row.session_id,
                state=ExecutionState(row.state),
                transition_history=(initial_transition(),),
                admitted_at=row.admitted_at,
                completed_at=row.terminal_at,
                result_code=result.result_code if result else None,
                result_value=result.result_value if result else None,
                actionable=result.actionable if result else False,
            )
        finally:
            session.close()

    def advance(self, execution_identifier: UUID, target_state: ExecutionState) -> None:
        session = self._sessions()
        try:
            row = session.get(RuntimeExecutionORM, execution_identifier)
            if row is None:
                raise KeyError(execution_identifier)
            transition(ExecutionState(row.state), target_state)
            expected = row.revision
            terminal = (
                datetime.now(UTC)
                if target_state in {ExecutionState.COMPLETED, ExecutionState.FAILED}
                else None
            )
            result = cast(
                CursorResult[Any],
                session.execute(
                    update(RuntimeExecutionORM)
                    .where(
                        RuntimeExecutionORM.execution_id == execution_identifier,
                        RuntimeExecutionORM.revision == expected,
                    )
                    .values(
                        state=target_state.value,
                        terminal_at=terminal,
                        revision=expected + 1,
                    )
                ),
            )
            if result.rowcount != 1:
                raise RuntimeError("Optimistic concurrency conflict")
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def checkpoint(
        self,
        execution_identifier: UUID,
        *,
        stage_name: str,
        stage_ordinal: int,
        input_payload: bytes,
        output_payload: bytes,
        artifact_references: tuple[UUID, ...],
        completed_at: datetime,
    ) -> None:
        """Atomically record a completed stage, handoffs, and produced references."""
        if completed_at.tzinfo is None:
            raise ValueError("Checkpoint timestamp must be timezone-aware")
        session = self._sessions()
        try:
            existing = session.scalar(
                select(RuntimeStageORM).where(
                    RuntimeStageORM.execution_id == execution_identifier,
                    RuntimeStageORM.stage_ordinal == stage_ordinal,
                )
            )
            if existing is not None:
                if existing.stage_name != stage_name or existing.status != "COMMITTED":
                    raise RuntimeError("Checkpoint conflict")
                return
            input_handoff = uuid4()
            output_handoff = uuid4()
            stage_id = uuid4()
            for handoff_id, source, target, payload in (
                (input_handoff, None if stage_ordinal == 0 else "PRIOR", stage_name, input_payload),
                (output_handoff, stage_name, None, output_payload),
            ):
                session.add(
                    RuntimeHandoffORM(
                        handoff_id=handoff_id,
                        execution_id=execution_identifier,
                        source_stage=source,
                        target_stage=target,
                        contract_version="CIM-001-v1.1",
                        protected_payload=self._handoff_protector.protect(payload),
                        content_hash=sha256(payload).digest(),
                        created_at=completed_at,
                    )
                )
            session.add(
                RuntimeStageORM(
                    stage_id=stage_id,
                    execution_id=execution_identifier,
                    stage_name=stage_name,
                    stage_ordinal=stage_ordinal,
                    status="COMMITTED",
                    started_at=completed_at,
                    completed_at=completed_at,
                    input_handoff_id=input_handoff,
                    output_handoff_id=output_handoff,
                    safe_failure_code=None,
                    revision=0,
                )
            )
            for artifact_id in artifact_references:
                session.add(
                    RuntimeArtifactReferenceORM(
                        artifact_reference_id=uuid4(),
                        execution_id=execution_identifier,
                        stage_id=stage_id,
                        artifact_role="PRODUCED_RECORD",
                        artifact_id=artifact_id,
                        source_capability=stage_name,
                        created_at=completed_at,
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_result(
        self,
        execution_identifier: UUID,
        *,
        result_code: str | None,
        result_value: str | None,
        actionable: bool,
        completed_at: datetime,
    ) -> None:
        session = self._sessions()
        try:
            if (
                session.scalar(
                    select(RuntimeResultORM).where(
                        RuntimeResultORM.execution_id == execution_identifier
                    )
                )
                is None
            ):
                session.add(
                    RuntimeResultORM(
                        result_id=uuid4(),
                        execution_id=execution_identifier,
                        terminal_capability="GRM",
                        disposition="BUSINESS_RESULT",
                        result_code=result_code,
                        result_value=result_value,
                        actionable=actionable,
                        completed_at=completed_at,
                    )
                )
            session.commit()
        finally:
            session.close()

    def authorize_recovery(
        self,
        original_execution_id: UUID,
        replay_execution_id: UUID,
        authorization: ReplayAuthorization,
        *,
        checkpoint_stage_id: UUID | None = None,
    ) -> UUID:
        session = self._sessions()
        try:
            original = session.get(RuntimeExecutionORM, original_execution_id)
            replay = session.get(RuntimeExecutionORM, replay_execution_id)
            if original is None or replay is None:
                raise KeyError("Recovery execution is unknown")
            authorization.validate(original.tenant_id)
            recovery_id = uuid4()
            session.add(
                RuntimeRecoveryAttemptORM(
                    recovery_id=recovery_id,
                    logical_execution_id=original.logical_execution_id,
                    original_execution_id=original_execution_id,
                    replay_execution_id=replay_execution_id,
                    checkpoint_stage_id=checkpoint_stage_id,
                    tenant_id=original.tenant_id,
                    replay_principal_id=authorization.principal_id,
                    original_authorization_reference="retained-original-authority",
                    replay_authorization_reference=authorization.authorization_reference,
                    replay_reason=authorization.reason,
                    correlation_id=authorization.correlation_id,
                    authorized_at=authorization.authorized_at,
                )
            )
            session.commit()
            return recovery_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_legal_hold(self, execution_identifier: UUID, enabled: bool) -> None:
        session = self._sessions()
        try:
            row = session.get(RuntimeExecutionORM, execution_identifier)
            if row is None:
                raise KeyError(execution_identifier)
            row.legal_hold = enabled
            session.commit()
        finally:
            session.close()

    def apply_terminal_retention(self, execution_identifier: UUID) -> None:
        session = self._sessions()
        try:
            row = session.get(RuntimeExecutionORM, execution_identifier)
            if row is None or row.terminal_at is None:
                raise ValueError("Retention requires a terminal execution")
            row.retention_until = row.terminal_at + timedelta(days=365 * 7)
            session.commit()
        finally:
            session.close()
