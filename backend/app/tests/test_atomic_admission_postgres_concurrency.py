"""PostgreSQL-backed concurrency verification for CDD-014 admission uniqueness.

Test-only. Does not modify runtime, application, or migration behavior. Each
worker runs in its own OS process so a permanently blocked worker can be
forcibly terminated without hanging pytest or leaking database state. IPC
uses a one-way multiprocessing.Pipe drained while workers run, avoiding any
dependency on OS pipe-buffer size.
"""

import hashlib
import multiprocessing
import sys
import threading
from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from threading import BrokenBarrierError
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, create_engine, delete, event, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.integration.contracts import AuthorityContext
from app.runtime.contracts import InvocationRequest
from app.runtime.persistence.contracts import ProtectionContext
from app.runtime.persistence.models import RuntimeExecutionORM, RuntimeHandoffORM
from app.runtime.persistence.repository import _HANDOFF_CONTRACT, SqlAlchemyExecutionStore
from app.runtime.recovery import STAGES

TENANT = "concurrency-test-tenant"
PROTOCOL_VERSION = "2.0"
MP_CONTEXT = multiprocessing.get_context("spawn")


class FakeHandoffProtector:
    def protect(self, plaintext: bytes, context: ProtectionContext) -> bytes:
        return b"protected:" + plaintext

    def recover(self, protected: bytes, context: ProtectionContext) -> bytes:
        if not protected.startswith(b"protected:"):
            raise ValueError("invalid protected test payload")
        return protected.removeprefix(b"protected:")


def _authority_context(request_id: UUID) -> AuthorityContext:
    now = datetime.now(UTC)
    return AuthorityContext(
        principal_id="principal",
        principal_type="Service",
        organization_id=TENANT,
        roles=("role",),
        scopes=("scope",),
        authorization_decision="AUTHORIZED",
        authorization_reference="auth-ref",
        trust_source="gateway",
        request_id=request_id,
        correlation_id=uuid4(),
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(hours=1),
    )


def _request(request_id: UUID, authority: AuthorityContext, payload: bytes) -> InvocationRequest:
    return InvocationRequest(
        protocol_version=PROTOCOL_VERSION,
        correlation_identifier=authority.correlation_id,
        request_identifier=request_id,
        session_identifier=uuid4(),
        request_classification="supplier-risk",
        opaque_payload=payload,
        authority_context=authority,
        control_metadata_version="1.0",
    )


@dataclass
class ConstraintInfo:
    schema_name: str
    constraint_name: str


def _discover_constraint(database_url: str) -> ConstraintInfo:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            current_schema = connection.execute(text("SELECT current_schema()")).scalar_one()
            row = connection.execute(
                text(
                    """
                    SELECT nsp.nspname, con.conname
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                    JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS key(attnum, ord) ON true
                    JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = key.attnum
                    WHERE nsp.nspname = :schema_name
                      AND rel.relname = 'runtime_executions'
                      AND con.contype = 'u'
                    GROUP BY nsp.nspname, con.conname
                    HAVING array_agg(att.attname::text ORDER BY key.ord) = ARRAY['tenant_id', 'protocol_version', 'request_id']
                    """
                ),
                {"schema_name": current_schema},
            ).one()
    finally:
        engine.dispose()
    schema_name, constraint_name = row
    assert schema_name, "resolved schema name must be non-empty"
    assert constraint_name, "resolved constraint name must be non-empty"
    return ConstraintInfo(schema_name=schema_name, constraint_name=constraint_name)


def _make_synchronizer(
    fired_flag: dict[str, bool], lock: threading.Lock, barrier: Any
) -> Callable[[Session], None]:
    def _before_commit(session: Session) -> None:
        should_wait = False
        with lock:
            if session.info.get("_concurrency_synchronized"):
                pass
            elif fired_flag["fired"]:
                session.info["_concurrency_synchronized"] = True
            else:
                fired_flag["fired"] = True
                session.info["_concurrency_synchronized"] = True
                should_wait = True
        if should_wait:
            barrier.wait()

    return _before_commit


def _make_handle_error(
    violations: list[dict[str, Any]],
) -> Callable[[Any], None]:
    def _handle_error(context: Any) -> None:
        original = context.original_exception
        sqlstate = getattr(original, "sqlstate", None) or getattr(
            getattr(original, "diag", None), "sqlstate", None
        )
        if sqlstate == "23505":
            violations.append(
                {
                    "sqlstate": sqlstate,
                    "constraint_name": getattr(
                        getattr(original, "diag", None), "constraint_name", None
                    ),
                    "statement": str(context.statement) if context.statement is not None else "",
                }
            )

    return _handle_error


def _placeholder_outcome() -> dict[str, Any]:
    return {
        "error": None,
        "broken_barrier": False,
        "teardown_errors": [],
        "violations": [],
        "execution_identifier": None,
        "is_new": None,
        "is_conflict": None,
        "admitted_payload": None,
        "admitted_at": None,
    }


def _worker_process_main(
    database_url: str,
    tenant: str,
    request_id_hex: str,
    correlation_id_hex: str,
    session_identifier_hex: str,
    issued_at_iso: str,
    expires_at_iso: str,
    payload: bytes,
    fingerprint: bytes,
    barrier: Any,
    child_conn: Connection,
) -> None:
    outcome = _placeholder_outcome()
    engine = None
    before_commit = None
    handle_error = None
    factory = None
    violations: list[dict[str, Any]] = []
    try:
        engine = create_engine(database_url)
        factory = sessionmaker(engine, expire_on_commit=False)
        fired_flag = {"fired": False}
        lock = threading.Lock()
        before_commit = _make_synchronizer(fired_flag, lock, barrier)
        handle_error = _make_handle_error(violations)
        event.listen(factory, "before_commit", before_commit)
        event.listen(engine, "handle_error", handle_error)

        request_id = UUID(request_id_hex)
        authority = AuthorityContext(
            principal_id="principal",
            principal_type="Service",
            organization_id=tenant,
            roles=("role",),
            scopes=("scope",),
            authorization_decision="AUTHORIZED",
            authorization_reference="auth-ref",
            trust_source="gateway",
            request_id=request_id,
            correlation_id=UUID(correlation_id_hex),
            issued_at=datetime.fromisoformat(issued_at_iso),
            expires_at=datetime.fromisoformat(expires_at_iso),
        )
        request_obj = InvocationRequest(
            protocol_version=PROTOCOL_VERSION,
            correlation_identifier=UUID(correlation_id_hex),
            request_identifier=request_id,
            session_identifier=UUID(session_identifier_hex),
            request_classification="supplier-risk",
            opaque_payload=payload,
            authority_context=authority,
            control_metadata_version="1.0",
        )
        store = SqlAlchemyExecutionStore(factory, FakeHandoffProtector())
        try:
            result = store.admit(request_obj, fingerprint)
            outcome.update(
                {
                    "execution_identifier": result.execution_identifier,
                    "is_new": result.is_new,
                    "is_conflict": result.is_conflict,
                    "admitted_payload": result.admitted_payload,
                    "admitted_at": result.admitted_at,
                }
            )
        except BrokenBarrierError as exc:
            outcome["error"] = f"BrokenBarrierError: {exc}"
            outcome["broken_barrier"] = True
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if before_commit is not None and factory is not None:
            try:
                event.remove(factory, "before_commit", before_commit)
            except Exception as exc:  # noqa: BLE001
                outcome["teardown_errors"].append(f"listener removal (before_commit): {exc}")
        if handle_error is not None and engine is not None:
            try:
                event.remove(engine, "handle_error", handle_error)
            except Exception as exc:  # noqa: BLE001
                outcome["teardown_errors"].append(f"listener removal (handle_error): {exc}")
        if engine is not None:
            try:
                engine.dispose()
            except Exception as exc:  # noqa: BLE001
                outcome["teardown_errors"].append(f"engine disposal: {exc}")

    outcome["violations"] = violations
    try:
        child_conn.send(outcome)
    except (BrokenPipeError, OSError):
        try:
            child_conn.close()
        except OSError:
            pass
        raise SystemExit(1)
    finally:
        try:
            child_conn.close()
        except OSError:
            pass


def _terminate_process(process: BaseProcess) -> dict[str, Any]:
    outcome: dict[str, Any] = {"contained": False, "method": None, "exitcode": None}
    process.join(timeout=10)
    if not process.is_alive():
        outcome.update(contained=True, method="graceful_join", exitcode=process.exitcode)
        return outcome
    process.terminate()
    process.join(timeout=5)
    if not process.is_alive():
        outcome.update(contained=True, method="terminate", exitcode=process.exitcode)
        return outcome
    process.kill()
    process.join(timeout=5)
    outcome.update(contained=not process.is_alive(), method="kill", exitcode=process.exitcode)
    return outcome


def _receive_once(conn: Connection) -> dict[str, Any]:
    try:
        outcome = cast(dict[str, Any], conn.recv())
        outcome["delivery"] = "delivered"
    except (EOFError, OSError) as exc:
        outcome = _placeholder_outcome()
        outcome["delivery"] = "ipc_read_failure"
        outcome["error"] = f"IPC read failure: {type(exc).__name__}: {exc}"
    return outcome


def _no_delivery_outcome() -> dict[str, Any]:
    outcome = _placeholder_outcome()
    outcome["delivery"] = "no_outcome_delivered"
    return outcome


class _ConcurrencyHarness:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.verify_engine = create_engine(database_url)
        self.verify_factory = sessionmaker(self.verify_engine, expire_on_commit=False)
        self.request_id = uuid4()
        self._active_processes: list[BaseProcess] = []
        self._active_connections: list[Connection] = []
        self._teardown_errors: list[BaseException] = []
        self._row_cleanup_done = False

    def _all_workers_contained(self) -> bool:
        return all(not p.is_alive() for p in self._active_processes)

    def _final_containment_backstop(self) -> None:
        for process in self._active_processes:
            if process.is_alive():
                result = _terminate_process(process)
                if not result["contained"]:
                    self._teardown_errors.append(
                        RuntimeError(f"Final containment backstop failed: {result}")
                    )

    def _close_connections(self) -> None:
        for conn in self._active_connections:
            try:
                conn.close()
            except BaseException as exc:  # noqa: BLE001
                self._teardown_errors.append(exc)

    def _cleanup_rows(self) -> None:
        self._final_containment_backstop()
        if not self._all_workers_contained():
            self._teardown_errors.append(
                RuntimeError(
                    "Row cleanup prohibited: a worker process remains alive after containment backstop."
                )
            )
            return
        if self._row_cleanup_done:
            return
        try:
            session = self.verify_factory()
        except BaseException as exc:  # noqa: BLE001
            self._teardown_errors.append(exc)
            return
        try:
            try:
                session.execute(
                    delete(RuntimeHandoffORM).where(
                        RuntimeHandoffORM.execution_id.in_(
                            select(RuntimeExecutionORM.execution_id).where(
                                RuntimeExecutionORM.tenant_id == TENANT,
                                RuntimeExecutionORM.protocol_version == PROTOCOL_VERSION,
                                RuntimeExecutionORM.request_id == self.request_id,
                            )
                        )
                    )
                )
                session.execute(
                    delete(RuntimeExecutionORM).where(
                        RuntimeExecutionORM.tenant_id == TENANT,
                        RuntimeExecutionORM.protocol_version == PROTOCOL_VERSION,
                        RuntimeExecutionORM.request_id == self.request_id,
                    )
                )
                session.commit()
                self._row_cleanup_done = True
            except BaseException as exc:  # noqa: BLE001
                try:
                    session.rollback()
                except BaseException as rollback_exc:  # noqa: BLE001
                    self._teardown_errors.append(rollback_exc)
                self._teardown_errors.append(exc)
        finally:
            try:
                session.close()
            except BaseException as close_exc:  # noqa: BLE001
                self._teardown_errors.append(close_exc)

    def _close_verify_engine(self) -> None:
        try:
            self.verify_engine.dispose()
        except BaseException as exc:  # noqa: BLE001
            self._teardown_errors.append(exc)

    def teardown(self, original_failure: BaseException | None) -> None:
        self._cleanup_rows()
        self._close_connections()
        self._close_verify_engine()

        if self._teardown_errors:
            base_only = [e for e in self._teardown_errors if not isinstance(e, Exception)]
            exc_only = [e for e in self._teardown_errors if isinstance(e, Exception)]
            if original_failure is not None:
                for err in self._teardown_errors:
                    original_failure.add_note(
                        f"Teardown failure during fixture cleanup (not the primary failure): "
                        f"{type(err).__name__}: {err}"
                    )
            else:
                if len(self._teardown_errors) == 1:
                    raise self._teardown_errors[0]
                if base_only:
                    raise BaseExceptionGroup("teardown failures", self._teardown_errors)
                raise ExceptionGroup("teardown failures", exc_only)


@pytest.fixture
def concurrency_harness(migrated_engine: Engine) -> Generator[_ConcurrencyHarness, None, None]:
    database_url = migrated_engine.url.render_as_string(hide_password=False)
    harness = _ConcurrencyHarness(database_url)
    original_failure: BaseException | None = None
    try:
        yield harness
    except BaseException as exc:
        original_failure = exc
        raise
    finally:
        harness.teardown(original_failure)


def _run_case(
    harness: _ConcurrencyHarness,
    req_a: InvocationRequest,
    req_b: InvocationRequest,
    fingerprint_a: bytes,
    fingerprint_b: bytes,
) -> dict[str, dict[str, Any]]:
    barrier = MP_CONTEXT.Barrier(2, timeout=5)
    parent_conn_a, child_conn_a = MP_CONTEXT.Pipe(duplex=False)
    parent_conn_b, child_conn_b = MP_CONTEXT.Pipe(duplex=False)
    endpoints: dict[str, Connection | None] = {
        "parent_conn_a": parent_conn_a,
        "child_conn_a": child_conn_a,
        "parent_conn_b": parent_conn_b,
        "child_conn_b": child_conn_b,
    }
    harness._active_connections = [parent_conn_a, parent_conn_b]

    def _close_endpoint(name: str) -> None:
        conn = endpoints.get(name)
        if conn is not None:
            try:
                conn.close()
            except OSError:
                pass
            endpoints[name] = None

    def _args_for(
        request_obj: InvocationRequest, fingerprint: bytes, child_conn: Connection
    ) -> tuple[Any, ...]:
        assert request_obj.authority_context is not None
        return (
            harness.database_url,
            TENANT,
            str(request_obj.request_identifier),
            str(request_obj.correlation_identifier),
            str(request_obj.session_identifier),
            request_obj.authority_context.issued_at.isoformat(),
            request_obj.authority_context.expires_at.isoformat(),
            request_obj.opaque_payload,
            fingerprint,
            barrier,
            child_conn,
        )

    process_a = MP_CONTEXT.Process(
        target=_worker_process_main, args=_args_for(req_a, fingerprint_a, child_conn_a)
    )
    process_b = MP_CONTEXT.Process(
        target=_worker_process_main, args=_args_for(req_b, fingerprint_b, child_conn_b)
    )
    harness._active_processes = [process_a, process_b]
    started: list[BaseProcess] = []
    outcome_a: dict[str, Any] | None = None
    outcome_b: dict[str, Any] | None = None

    try:
        process_a.start()
        started.append(process_a)
        _close_endpoint("child_conn_a")

        process_b.start()
        started.append(process_b)
        _close_endpoint("child_conn_b")

        for _ in range(5):
            if outcome_a is None and parent_conn_a.poll(timeout=2):
                outcome_a = _receive_once(parent_conn_a)
            if outcome_b is None and parent_conn_b.poll(timeout=2):
                outcome_b = _receive_once(parent_conn_b)
            if outcome_a is not None and outcome_b is not None:
                break

        containment_a = _terminate_process(process_a)
        containment_b = _terminate_process(process_b)
        if not (containment_a["contained"] and containment_b["contained"]):
            barrier.abort()
            containment_a = _terminate_process(process_a)
            containment_b = _terminate_process(process_b)

        if outcome_a is None:
            outcome_a = _no_delivery_outcome()
        if outcome_b is None:
            outcome_b = _no_delivery_outcome()
        outcome_a.update(
            process_exitcode=containment_a["exitcode"], containment_method=containment_a["method"]
        )
        outcome_b.update(
            process_exitcode=containment_b["exitcode"], containment_method=containment_b["method"]
        )

        assert containment_a["contained"], f"worker A containment failed: {containment_a}"
        assert containment_b["contained"], f"worker B containment failed: {containment_b}"
    finally:
        collected: list[BaseException] = []
        for process in started:
            if process.is_alive():
                result = _terminate_process(process)
                if not result["contained"]:
                    collected.append(
                        RuntimeError(f"process failed to terminate in finally backstop: {result}")
                    )
        for name in list(endpoints):
            try:
                _close_endpoint(name)
            except BaseException as exc:  # noqa: BLE001
                collected.append(exc)
        if collected:
            active = sys.exc_info()[1]
            if active is not None:
                for err in collected:
                    active.add_note(
                        f"_run_case finally cleanup failure: {type(err).__name__}: {err}"
                    )
            else:
                if len(collected) == 1:
                    raise collected[0]
                raise BaseExceptionGroup("_run_case cleanup failures", collected)

    outcomes = {"a": outcome_a, "b": outcome_b}
    for key, outcome in outcomes.items():
        assert not outcome.get(
            "broken_barrier"
        ), f"worker {key} observed a broken barrier: {outcome}"
        assert outcome.get("error") is None, f"worker {key} raised an error: {outcome['error']}"
        assert not outcome.get(
            "teardown_errors"
        ), f"worker {key} had teardown failures: {outcome['teardown_errors']}"
        assert (
            outcome.get("delivery") == "delivered"
        ), f"worker {key} outcome was not delivered: {outcome}"

    return outcomes


def test_identical_concurrent_admissions_reuse_the_single_stored_record(
    concurrency_harness: _ConcurrencyHarness,
) -> None:
    harness = concurrency_harness
    payload_a = payload_b = b"shared-complete-client-payload"
    fingerprint_a = fingerprint_b = hashlib.sha256(payload_a).digest()
    authority = _authority_context(harness.request_id)
    shared_request = _request(harness.request_id, authority, payload_a)
    req_a = shared_request
    req_b = shared_request

    assert req_a == req_b
    assert payload_a == payload_b
    assert fingerprint_a == fingerprint_b

    outcomes = _run_case(harness, req_a, req_b, fingerprint_a, fingerprint_b)

    new_flags = [outcomes["a"]["is_new"], outcomes["b"]["is_new"]]
    assert new_flags.count(True) == 1
    assert new_flags.count(False) == 1
    assert outcomes["a"]["is_conflict"] is False
    assert outcomes["b"]["is_conflict"] is False

    with harness.verify_factory() as verify:
        execution = verify.scalar(
            select(RuntimeExecutionORM).where(
                RuntimeExecutionORM.tenant_id == TENANT,
                RuntimeExecutionORM.protocol_version == PROTOCOL_VERSION,
                RuntimeExecutionORM.request_id == harness.request_id,
            )
        )
        assert execution is not None

        exec_count = verify.execute(
            select(func.count())
            .select_from(RuntimeExecutionORM)
            .where(
                RuntimeExecutionORM.tenant_id == TENANT,
                RuntimeExecutionORM.protocol_version == PROTOCOL_VERSION,
                RuntimeExecutionORM.request_id == harness.request_id,
            )
        ).scalar_one()
        assert exec_count == 1

        handoff_count = verify.execute(
            select(func.count())
            .select_from(RuntimeHandoffORM)
            .join(
                RuntimeExecutionORM,
                RuntimeHandoffORM.execution_id == RuntimeExecutionORM.execution_id,
            )
            .where(
                RuntimeExecutionORM.tenant_id == TENANT,
                RuntimeExecutionORM.protocol_version == PROTOCOL_VERSION,
                RuntimeExecutionORM.request_id == harness.request_id,
            )
        ).scalar_one()
        assert handoff_count == 1

        handoff = verify.scalar(
            select(RuntimeHandoffORM).where(
                RuntimeHandoffORM.execution_id == execution.execution_id
            )
        )
        assert handoff is not None
        assert isinstance(handoff.handoff_id, UUID)
        assert handoff.execution_id == execution.execution_id
        assert handoff.source_stage is None
        assert handoff.target_stage == STAGES[0]
        assert handoff.contract_version == _HANDOFF_CONTRACT
        assert handoff.protected_payload == b"protected:" + payload_a
        assert handoff.created_at == execution.admitted_at

        protection_context = ProtectionContext(
            tenant_id=TENANT,
            logical_execution_id=execution.logical_execution_id,
            attempt_id=execution.execution_id,
            stage_name=STAGES[0],
            direction="INPUT",
            contract_version=handoff.contract_version,
        )
        recovered = FakeHandoffProtector().recover(handoff.protected_payload, protection_context)
        assert handoff.content_hash == hashlib.sha256(recovered).digest()

    assert outcomes["a"]["execution_identifier"] == execution.execution_id
    assert outcomes["b"]["execution_identifier"] == execution.execution_id
    assert outcomes["a"]["admitted_at"] == execution.admitted_at
    assert outcomes["b"]["admitted_at"] == execution.admitted_at
    assert outcomes["a"]["admitted_payload"] == payload_a
    assert outcomes["b"]["admitted_payload"] == payload_a
    assert recovered == payload_a

    all_violations = outcomes["a"]["violations"] + outcomes["b"]["violations"]
    assert len(all_violations) == 1, f"expected exactly one 23505, got {all_violations}"
    observation = all_violations[0]
    constraint = _discover_constraint(harness.database_url)
    assert observation["sqlstate"] == "23505"
    assert observation["constraint_name"] == constraint.constraint_name
    assert "runtime_executions" in observation["statement"]


def test_conflicting_concurrent_admissions_reject_the_loser_atomically(
    concurrency_harness: _ConcurrencyHarness,
) -> None:
    harness = concurrency_harness
    payload_a = b"payload-a-complete-client-payload"
    payload_b = b"payload-b-complete-client-payload"
    fingerprint_a = hashlib.sha256(payload_a).digest()
    fingerprint_b = hashlib.sha256(payload_b).digest()
    payloads = {"a": payload_a, "b": payload_b}
    fingerprints = {"a": fingerprint_a, "b": fingerprint_b}

    authority = _authority_context(harness.request_id)
    req_a = _request(harness.request_id, authority, payload_a)
    req_b = _request(harness.request_id, authority, payload_b)

    assert req_a.authority_context is not None
    assert req_b.authority_context is not None
    assert (
        req_a.authority_context.organization_id == req_b.authority_context.organization_id == TENANT
    )
    assert req_a.protocol_version == req_b.protocol_version == PROTOCOL_VERSION
    assert req_a.request_identifier == req_b.request_identifier == harness.request_id
    assert payload_a != payload_b
    assert fingerprint_a != fingerprint_b

    outcomes = _run_case(harness, req_a, req_b, fingerprint_a, fingerprint_b)

    new_flags = [outcomes["a"]["is_new"], outcomes["b"]["is_new"]]
    conflict_flags = [outcomes["a"]["is_conflict"], outcomes["b"]["is_conflict"]]
    assert new_flags.count(True) == 1
    assert new_flags.count(False) == 1
    assert conflict_flags.count(True) == 1
    assert conflict_flags.count(False) == 1

    winner_key = "a" if outcomes["a"]["is_new"] else "b"
    loser_key = "b" if winner_key == "a" else "a"
    winner = outcomes[winner_key]
    loser = outcomes[loser_key]

    assert winner["is_new"] is True
    assert winner["is_conflict"] is False
    assert winner["execution_identifier"] is not None
    assert loser["is_new"] is False
    assert loser["is_conflict"] is True
    assert loser["execution_identifier"] is None
    assert loser["admitted_payload"] is None
    assert loser["admitted_at"] is None

    with harness.verify_factory() as verify:
        execution = verify.scalar(
            select(RuntimeExecutionORM).where(
                RuntimeExecutionORM.tenant_id == TENANT,
                RuntimeExecutionORM.protocol_version == PROTOCOL_VERSION,
                RuntimeExecutionORM.request_id == harness.request_id,
            )
        )
        assert execution is not None
        assert execution.execution_id == winner["execution_identifier"]

        exec_count = verify.execute(
            select(func.count())
            .select_from(RuntimeExecutionORM)
            .where(
                RuntimeExecutionORM.tenant_id == TENANT,
                RuntimeExecutionORM.protocol_version == PROTOCOL_VERSION,
                RuntimeExecutionORM.request_id == harness.request_id,
            )
        ).scalar_one()
        assert exec_count == 1

        handoff_count = verify.execute(
            select(func.count())
            .select_from(RuntimeHandoffORM)
            .join(
                RuntimeExecutionORM,
                RuntimeHandoffORM.execution_id == RuntimeExecutionORM.execution_id,
            )
            .where(
                RuntimeExecutionORM.tenant_id == TENANT,
                RuntimeExecutionORM.protocol_version == PROTOCOL_VERSION,
                RuntimeExecutionORM.request_id == harness.request_id,
            )
        ).scalar_one()
        assert handoff_count == 1

        handoff = verify.scalar(
            select(RuntimeHandoffORM).where(
                RuntimeHandoffORM.execution_id == execution.execution_id
            )
        )
        assert handoff is not None
        assert isinstance(handoff.handoff_id, UUID)
        assert handoff.execution_id == execution.execution_id
        assert handoff.source_stage is None
        assert handoff.target_stage == STAGES[0]
        assert handoff.contract_version == _HANDOFF_CONTRACT
        assert handoff.protected_payload == b"protected:" + payloads[winner_key]
        assert handoff.created_at == execution.admitted_at

        protection_context = ProtectionContext(
            tenant_id=TENANT,
            logical_execution_id=execution.logical_execution_id,
            attempt_id=execution.execution_id,
            stage_name=STAGES[0],
            direction="INPUT",
            contract_version=handoff.contract_version,
        )
        recovered = FakeHandoffProtector().recover(handoff.protected_payload, protection_context)
        assert handoff.content_hash == hashlib.sha256(recovered).digest()

    assert winner["execution_identifier"] == execution.execution_id
    assert winner["admitted_at"] == execution.admitted_at
    assert winner["admitted_payload"] == payloads[winner_key]
    assert execution.payload_fingerprint == fingerprints[winner_key]
    assert execution.payload_fingerprint != fingerprints[loser_key]
    assert recovered == payloads[winner_key]
    assert recovered != payloads[loser_key]

    all_violations = outcomes["a"]["violations"] + outcomes["b"]["violations"]
    assert len(all_violations) == 1, f"expected exactly one 23505, got {all_violations}"
    observation = all_violations[0]
    constraint = _discover_constraint(harness.database_url)
    assert observation["sqlstate"] == "23505"
    assert observation["constraint_name"] == constraint.constraint_name
    assert "runtime_executions" in observation["statement"]
