"""PostgreSQL-backed atomic execution admission and durable observation."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import RLock
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select, text, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.integration.contracts import AuthorityContext
from app.runtime.contracts import ExecutionSnapshot, InvocationRequest
from app.runtime.execution_state import ExecutionState, initial_transition, transition
from app.runtime.execution_store import AdmissionResult
from app.runtime.persistence.contracts import (
    AttemptProjection,
    HandoffProtector,
    ProtectedPayloadIntegrityError,
    ProtectedPayloadMissingError,
    ProtectionContext,
    ReplayAuthorization,
    ResultProjection,
    RetryAuthorization,
    StageProjection,
)
from app.runtime.persistence.models import (
    RuntimeArtifactReferenceORM,
    RuntimeExecutionORM,
    RuntimeHandoffORM,
    RuntimeRecoveryAttemptORM,
    RuntimeResultORM,
    RuntimeStageORM,
)
from app.runtime.recovery import STAGES, ValidatedRecoveryInvocation, validated_recovery_invocation

_HANDOFF_CONTRACT = "CIM-001-v1.1"


class SqlAlchemyExecutionStore:
    """Durable store with database-enforced admission and optimistic revision."""

    def __init__(
        self, session_factory: sessionmaker[Session], handoff_protector: HandoffProtector
    ) -> None:
        self._sessions = session_factory
        self._handoff_protector = handoff_protector
        self._replay_lock = RLock()

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
            admitted_at = datetime.now(UTC)
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
                    admitted_at=admitted_at,
                    revision=0,
                    legal_hold=False,
                    retention_until=None,
                )
            )
            context = ProtectionContext(
                tenant_id=tenant,
                logical_execution_id=execution_id,
                attempt_id=execution_id,
                stage_name=STAGES[0],
                direction="INPUT",
                contract_version=_HANDOFF_CONTRACT,
            )
            session.add(
                RuntimeHandoffORM(
                    handoff_id=uuid4(),
                    execution_id=execution_id,
                    source_stage=None,
                    target_stage=STAGES[0],
                    contract_version=_HANDOFF_CONTRACT,
                    protected_payload=self._handoff_protector.protect(
                        request.opaque_payload, context
                    ),
                    content_hash=sha256(request.opaque_payload).digest(),
                    created_at=admitted_at,
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

    def tenant_owns(self, execution_identifier: UUID, tenant_id: str) -> bool:
        session = self._sessions()
        try:
            return (
                session.scalar(
                    select(RuntimeExecutionORM.execution_id).where(
                        RuntimeExecutionORM.execution_id == execution_identifier,
                        RuntimeExecutionORM.tenant_id == tenant_id,
                    )
                )
                is not None
            )
        finally:
            session.close()

    def list_attempts(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> tuple[AttemptProjection, ...]:
        session = self._sessions()
        try:
            rows = session.scalars(
                select(RuntimeExecutionORM)
                .where(
                    RuntimeExecutionORM.logical_execution_id == logical_execution_id,
                    RuntimeExecutionORM.tenant_id == tenant_id,
                )
                .order_by(RuntimeExecutionORM.admitted_at, RuntimeExecutionORM.execution_id)
            )
            return tuple(
                AttemptProjection(
                    row.execution_id,
                    row.logical_execution_id,
                    row.state,
                    row.admitted_at,
                    row.terminal_at,
                    row.revision,
                )
                for row in rows
            )
        finally:
            session.close()

    def list_stages(
        self, logical_execution_id: UUID, execution_id: UUID, tenant_id: str
    ) -> tuple[StageProjection, ...]:
        session = self._sessions()
        try:
            owned = session.scalar(
                select(RuntimeExecutionORM.execution_id).where(
                    RuntimeExecutionORM.execution_id == execution_id,
                    RuntimeExecutionORM.logical_execution_id == logical_execution_id,
                    RuntimeExecutionORM.tenant_id == tenant_id,
                )
            )
            if owned is None:
                return ()
            rows = tuple(
                session.scalars(
                    select(RuntimeStageORM)
                    .where(RuntimeStageORM.execution_id == execution_id)
                    .order_by(RuntimeStageORM.stage_ordinal)
                )
            )
            references = tuple(
                session.scalars(
                    select(RuntimeArtifactReferenceORM).where(
                        RuntimeArtifactReferenceORM.execution_id == execution_id
                    )
                )
            )
            by_stage: dict[UUID, list[UUID]] = {}
            for reference in references:
                if reference.stage_id is not None:
                    by_stage.setdefault(reference.stage_id, []).append(reference.artifact_id)
            return tuple(
                StageProjection(
                    row.stage_id,
                    row.stage_name,
                    row.stage_ordinal,
                    row.status,
                    row.started_at,
                    row.completed_at,
                    row.safe_failure_code,
                    tuple(by_stage.get(row.stage_id, ())),
                )
                for row in rows
            )
        finally:
            session.close()

    def get_result_for_logical(
        self, logical_execution_id: UUID, tenant_id: str
    ) -> ResultProjection | None:
        session = self._sessions()
        try:
            execution = session.scalar(
                select(RuntimeExecutionORM)
                .where(
                    RuntimeExecutionORM.logical_execution_id == logical_execution_id,
                    RuntimeExecutionORM.tenant_id == tenant_id,
                )
                .order_by(RuntimeExecutionORM.admitted_at.desc())
                .limit(1)
            )
            if execution is None:
                return None
            result = session.scalar(
                select(RuntimeResultORM).where(
                    RuntimeResultORM.execution_id == execution.execution_id
                )
            )
            if result is None:
                return None
            references = tuple(
                session.scalars(
                    select(RuntimeArtifactReferenceORM.artifact_id).where(
                        RuntimeArtifactReferenceORM.execution_id == execution.execution_id
                    )
                )
            )
            return ResultProjection(
                execution.execution_id,
                result.result_code,
                result.result_value,
                result.actionable,
                result.completed_at,
                references,
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
            execution = session.get(RuntimeExecutionORM, execution_identifier)
            if execution is None:
                raise KeyError(execution_identifier)
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
            if stage_ordinal == 0:
                input_row = session.scalar(
                    select(RuntimeHandoffORM).where(
                        RuntimeHandoffORM.execution_id == execution_identifier,
                        RuntimeHandoffORM.source_stage.is_(None),
                        RuntimeHandoffORM.target_stage == STAGES[0],
                    )
                )
            else:
                prior_stage = session.scalar(
                    select(RuntimeStageORM).where(
                        RuntimeStageORM.execution_id == execution_identifier,
                        RuntimeStageORM.stage_ordinal == stage_ordinal - 1,
                    )
                )
                input_row = (
                    session.get(RuntimeHandoffORM, prior_stage.output_handoff_id)
                    if prior_stage is not None and prior_stage.output_handoff_id is not None
                    else None
                )
            if input_row is None or input_row.content_hash != sha256(input_payload).digest():
                raise RuntimeError("Checkpoint input does not match the governed handoff")
            input_handoff = input_row.handoff_id
            output_handoff = uuid4()
            stage_id = uuid4()
            protection_context = ProtectionContext(
                tenant_id=execution.tenant_id,
                logical_execution_id=execution.logical_execution_id,
                attempt_id=execution_identifier,
                stage_name=stage_name,
                direction="OUTPUT",
                contract_version=_HANDOFF_CONTRACT,
            )
            session.add(
                RuntimeHandoffORM(
                    handoff_id=output_handoff,
                    execution_id=execution_identifier,
                    source_stage=stage_name,
                    target_stage=None,
                    contract_version=_HANDOFF_CONTRACT,
                    protected_payload=self._handoff_protector.protect(
                        output_payload, protection_context
                    ),
                    content_hash=sha256(output_payload).digest(),
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

    def prepare_replay(
        self,
        original_execution_id: UUID,
        authorization: ReplayAuthorization,
        authority_context: AuthorityContext,
    ) -> ValidatedRecoveryInvocation:
        return self._prepare_recovery(original_execution_id, authorization, authority_context)

    def prepare_retry(
        self,
        original_execution_id: UUID,
        authorization: RetryAuthorization,
        authority_context: AuthorityContext,
    ) -> ValidatedRecoveryInvocation:
        return self._prepare_recovery(original_execution_id, authorization, authority_context)

    def _prepare_recovery(
        self,
        original_execution_id: UUID,
        authorization: ReplayAuthorization | RetryAuthorization,
        authority_context: AuthorityContext,
    ) -> ValidatedRecoveryInvocation:
        """Validate a checkpoint and atomically create or return its linked replay."""
        with self._replay_lock:
            session = self._sessions()
            try:
                original = session.get(RuntimeExecutionORM, original_execution_id)
                if original is None:
                    raise KeyError("Recovery execution is unknown")
                if original.state not in {
                    ExecutionState.COMPLETED.value,
                    ExecutionState.FAILED.value,
                }:
                    raise RuntimeError("Only a terminal attempt can be replayed")
                authorization.validate(original.tenant_id)
                self._validate_replay_authority(authorization, authority_context)
                self._lock_replay_identity(session, original_execution_id, authorization)

                stages = tuple(
                    session.scalars(
                        select(RuntimeStageORM)
                        .where(RuntimeStageORM.execution_id == original_execution_id)
                        .order_by(RuntimeStageORM.stage_ordinal)
                    )
                )
                resume_ordinal, checkpoint, handoff = self._select_recovery_handoff(
                    session, original, stages
                )
                payload = self._recover_handoff(original, handoff, resume_ordinal)

                existing = session.scalar(
                    select(RuntimeRecoveryAttemptORM).where(
                        RuntimeRecoveryAttemptORM.original_execution_id == original_execution_id,
                        RuntimeRecoveryAttemptORM.replay_authorization_reference
                        == authorization.authorization_reference,
                        RuntimeRecoveryAttemptORM.correlation_id == authorization.correlation_id,
                    )
                )
                if existing is not None:
                    replay = session.get(RuntimeExecutionORM, existing.replay_execution_id)
                    if replay is None:
                        raise RuntimeError("Recovery linkage is incomplete")
                    return self._recovery_invocation(
                        replay, existing.recovery_id, authority_context, payload, resume_ordinal
                    )

                replay_execution_id = uuid4()
                recovery_id = uuid4()
                admitted_at = datetime.now(UTC)
                session.add(
                    RuntimeExecutionORM(
                        execution_id=replay_execution_id,
                        logical_execution_id=original.logical_execution_id,
                        tenant_id=original.tenant_id,
                        protocol_version=original.protocol_version,
                        integration_contract_version=original.integration_contract_version,
                        request_id=authority_context.request_id,
                        correlation_id=authorization.correlation_id,
                        session_id=original.session_id,
                        request_classification=original.request_classification,
                        payload_fingerprint=sha256(payload).digest(),
                        control_fingerprint=sha256(repr(authority_context).encode()).digest(),
                        state=ExecutionState.ACCEPTED.value,
                        admitted_at=admitted_at,
                        revision=0,
                        legal_hold=False,
                        retention_until=None,
                    )
                )
                session.add(
                    RuntimeRecoveryAttemptORM(
                        recovery_id=recovery_id,
                        logical_execution_id=original.logical_execution_id,
                        original_execution_id=original_execution_id,
                        replay_execution_id=replay_execution_id,
                        checkpoint_stage_id=checkpoint,
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
                replay = session.get(RuntimeExecutionORM, replay_execution_id)
                if replay is None:
                    raise RuntimeError("Replay admission was not persisted")
                return self._recovery_invocation(
                    replay, recovery_id, authority_context, payload, resume_ordinal
                )
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    @staticmethod
    def _validate_replay_authority(
        authorization: ReplayAuthorization | RetryAuthorization,
        authority_context: AuthorityContext,
    ) -> None:
        if (
            authority_context.principal_id != authorization.principal_id
            or authority_context.organization_id != authorization.tenant_id
            or authority_context.authorization_reference != authorization.authorization_reference
            or authority_context.correlation_id != authorization.correlation_id
        ):
            raise PermissionError("Replay authority contexts conflict")
        authority_context.validate_for(
            request_id=authority_context.request_id,
            correlation_id=authorization.correlation_id,
            now=datetime.now(UTC),
        )

    @staticmethod
    def _lock_replay_identity(
        session: Session,
        original_execution_id: UUID,
        authorization: ReplayAuthorization | RetryAuthorization,
    ) -> None:
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            identity = (
                f"{original_execution_id}:{authorization.authorization_reference}:"
                f"{authorization.correlation_id}"
            )
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
                {"identity": identity},
            )

    @staticmethod
    def _select_recovery_handoff(
        session: Session,
        original: RuntimeExecutionORM,
        stages: tuple[RuntimeStageORM, ...],
    ) -> tuple[int, UUID | None, RuntimeHandoffORM]:
        if not stages:
            handoff = session.scalar(
                select(RuntimeHandoffORM).where(
                    RuntimeHandoffORM.execution_id == original.execution_id,
                    RuntimeHandoffORM.source_stage.is_(None),
                    RuntimeHandoffORM.target_stage == STAGES[0],
                )
            )
            if handoff is None:
                raise ProtectedPayloadMissingError("Original admitted payload is absent")
            return 0, None, handoff
        for ordinal, stage in enumerate(stages):
            if (
                ordinal >= len(STAGES)
                or stage.stage_ordinal != ordinal
                or stage.stage_name != STAGES[ordinal]
                or stage.status != "COMMITTED"
                or stage.completed_at is None
                or stage.safe_failure_code is not None
            ):
                raise RuntimeError("Recovery checkpoint history is unsafe")
        resume_ordinal = len(stages)
        if resume_ordinal >= len(STAGES):
            raise RuntimeError("The original execution has no downstream stage to replay")
        checkpoint = stages[-1]
        if checkpoint.output_handoff_id is None:
            raise ProtectedPayloadMissingError("Recovery checkpoint payload is absent")
        handoff = session.get(RuntimeHandoffORM, checkpoint.output_handoff_id)
        if handoff is None or handoff.execution_id != original.execution_id:
            raise ProtectedPayloadMissingError("Recovery checkpoint payload is absent")
        return resume_ordinal, checkpoint.stage_id, handoff

    def _recover_handoff(
        self,
        original: RuntimeExecutionORM,
        handoff: RuntimeHandoffORM,
        resume_ordinal: int,
    ) -> bytes:
        expected_stage = STAGES[0] if resume_ordinal == 0 else STAGES[resume_ordinal - 1]
        expected_source = None if resume_ordinal == 0 else expected_stage
        expected_direction = "INPUT" if resume_ordinal == 0 else "OUTPUT"
        if handoff.contract_version != _HANDOFF_CONTRACT or handoff.source_stage != expected_source:
            raise ProtectedPayloadIntegrityError("Recovery checkpoint contract is incompatible")
        context = ProtectionContext(
            tenant_id=original.tenant_id,
            logical_execution_id=original.logical_execution_id,
            attempt_id=original.execution_id,
            stage_name=expected_stage,
            direction=expected_direction,
            contract_version=_HANDOFF_CONTRACT,
        )
        payload = self._handoff_protector.recover(handoff.protected_payload, context)
        if sha256(payload).digest() != handoff.content_hash:
            raise ProtectedPayloadIntegrityError("Recovery checkpoint content hash failed")
        return payload

    @staticmethod
    def _recovery_invocation(
        replay: RuntimeExecutionORM,
        recovery_id: UUID,
        authority_context: AuthorityContext,
        payload: bytes,
        resume_ordinal: int,
    ) -> ValidatedRecoveryInvocation:
        return validated_recovery_invocation(
            execution_identifier=replay.execution_id,
            logical_execution_identifier=replay.logical_execution_id,
            protocol_version=replay.protocol_version,
            correlation_identifier=replay.correlation_id,
            request_identifier=replay.request_id,
            session_identifier=replay.session_id,
            request_classification=replay.request_classification,
            opaque_payload=payload,
            authority_context=authority_context,
            admitted_at=replay.admitted_at,
            resume_stage_ordinal=resume_ordinal,
            recovery_identifier=recovery_id,
        )

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
