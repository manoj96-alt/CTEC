"""Thin CLI wrapper around lifecycle_controller.py so GitHub Actions
workflow YAML (bash) can invoke the pure decision logic without embedding
Python state-machine code inline in every workflow file. Every subcommand
prints one JSON object to stdout and exits 0 on success; exits 1 with a
JSON `{"error": ...}` object on any refusal (TransitionRefused,
LockConflict, ValueError) -- the calling workflow step checks the exit
code, never re-derives the decision itself.

Noetva R4-I: adds `apply-transition` and `persist-metadata`, the two
subcommands that expose lifecycle_controller.py's `apply_transition()` --
previously defined but never reachable from any workflow (R4-DRG's D1
root cause) -- and a general non-transition metadata-merge path (TTL
extension, HOLD expiry, restart-monitor classification memory), so a
shell caller can obtain a complete, persistable next-row value without
lifecycle_controller.py itself ever performing I/O. `lifecycle_controller.
py` is NOT modified by this change; every field this file merges in
beyond what `apply_transition()` returns (ttlExpiresAt, dbAutoRestartRiskAt,
holdUntil, lastError) is plain dataclass field replacement in THIS file,
not new state-machine semantics.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone

from lifecycle_controller import (
    DemoReadinessResult,
    LifecycleRow,
    LifecycleState,
    LockConflict,
    StopPreconditions,
    TTL_MAX_HOURS,
    TTL_MIN_HOURS,
    TransitionRefused,
    apply_transition,
    can_extend,
    classify_unexpected_postgres_state,
    compute_db_auto_restart_risk_at,
    compute_hold_until,
    compute_ttl_expiry,
    evaluate_demo_ready,
    evaluate_stop_preconditions,
    extend_ttl,
    should_suppress_availability_alerts,
    validate_transition,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


# ---- shared row <-> entity-JSON translation ------------------------------
# The exact field set is lifecycle_controller.py's own documented schema
# (its module docstring) -- no second schema is invented here. `etag` is
# deliberately excluded from the emitted entity: it is an HTTP-level Azure
# Table Storage concept (`--if-match`), never a stored user-data property
# (Noetva R4-DRG Section AL).

def _row_from_dict(environment: str, data: dict) -> tuple[LifecycleRow, bool]:
    """Returns (row, is_new_row). `is_new_row` is True exactly when the
    caller's `lifecycle_table_read` found no existing entity (Noetva
    R4-DRG Section O: the first-ever Start for an environment IS the
    bootstrap -- there is no separate initialization step). A missing row
    is represented, by the same convention used everywhere else in this
    codebase, as an empty dict; a genuinely-read row always carries the
    `etag` Azure returned."""
    is_new = "etag" not in data
    return (
        LifecycleRow(
            environment=environment,
            state=LifecycleState(data.get("state", "DORMANT")),
            etag=data.get("etag", ""),
            ttl_expires_at=_parse_dt(data.get("ttlExpiresAt")),
            hold_until=_parse_dt(data.get("holdUntil")),
            last_actor=data.get("lastActor"),
            last_transition_at=_parse_dt(data.get("lastTransitionAt")),
            lock_owner=data.get("lockOwner"),
            lock_token=data.get("lockToken"),
            db_auto_restart_risk_at=_parse_dt(data.get("dbAutoRestartRiskAt")),
            last_workflow_run_id=data.get("lastWorkflowRunId"),
            last_error=data.get("lastError"),
        ),
        is_new,
    )


def _row_to_entity(row: LifecycleRow) -> dict:
    return {
        "environment": row.environment,
        "state": row.state.value,
        "ttlExpiresAt": _iso(row.ttl_expires_at),
        "holdUntil": _iso(row.hold_until),
        "lastActor": row.last_actor,
        "lastTransitionAt": _iso(row.last_transition_at),
        "lockOwner": row.lock_owner,
        "lockToken": row.lock_token,
        "dbAutoRestartRiskAt": _iso(row.db_auto_restart_risk_at),
        "lastWorkflowRunId": row.last_workflow_run_id,
        "lastError": row.last_error,
    }


def cmd_validate_transition(args: argparse.Namespace) -> dict:
    validate_transition(LifecycleState(args.current), LifecycleState(args.target))
    return {"allowed": True}


def cmd_compute_ttl_expiry(args: argparse.Namespace) -> dict:
    expiry = compute_ttl_expiry(_now(), args.ttl_hours)
    return {"ttlExpiresAt": expiry.isoformat()}


def cmd_should_suppress_alerts(args: argparse.Namespace) -> dict:
    state = None if args.lifecycle_state in (None, "unknown") else LifecycleState(args.lifecycle_state)
    return {"suppress": should_suppress_availability_alerts(state)}


def cmd_extend_ttl(args: argparse.Namespace) -> dict:
    current = datetime.fromisoformat(args.current_expiry) if args.current_expiry else None
    new_expiry = extend_ttl(current, args.additional_hours, _now())
    return {"ttlExpiresAt": new_expiry.isoformat()}


def cmd_compute_hold_until(args: argparse.Namespace) -> dict:
    until = compute_hold_until(_now(), args.hold_hours)
    return {"holdUntil": until.isoformat()}


def cmd_compute_restart_risk(args: argparse.Namespace) -> dict:
    stopped_at = datetime.fromisoformat(args.stopped_at)
    risk_at = compute_db_auto_restart_risk_at(stopped_at)
    return {"dbAutoRestartRiskAt": risk_at.isoformat()}


def cmd_evaluate_stop_preconditions(args: argparse.Namespace) -> dict:
    reasons = evaluate_stop_preconditions(StopPreconditions(
        migration_job_running=args.migration_job_running,
        deployment_in_progress=args.deployment_in_progress,
        hold_active=args.hold_active,
        unsafe_long_running_session=args.unsafe_long_running_session,
    ))
    return {"canStop": len(reasons) == 0, "reasons": reasons}


def cmd_evaluate_demo_ready(args: argparse.Namespace) -> dict:
    def _tri(value: str | None) -> bool | None:
        if value is None or value == "unknown":
            return None
        return value == "true"

    result = evaluate_demo_ready(DemoReadinessResult(
        frontend_reachable=args.frontend_reachable == "true",
        backend_healthy=args.backend_healthy == "true",
        db_reachable=args.db_reachable == "true",
        migration_head_correct=args.migration_head_correct == "true",
        authenticated_request_succeeds=_tri(args.authenticated_request_succeeds),
        demo_tenant_exists=_tri(args.demo_tenant_exists),
        golden_thread_finding_exists=_tri(args.golden_thread_finding_exists),
    ))
    return {"result": result}


def cmd_classify_postgres_state(args: argparse.Namespace) -> dict:
    def _tri(value: str | None) -> bool | None:
        if value is None or value == "unknown":
            return None
        return value == "true"

    result = classify_unexpected_postgres_state(
        lifecycle_state=LifecycleState(args.lifecycle_state),
        postgres_reports_ready=args.postgres_reports_ready == "true",
        now=_now(),
        stopped_at=datetime.fromisoformat(args.stopped_at) if args.stopped_at else None,
        maintenance_window_recheck_passed=_tri(args.recheck_passed),
    )
    return {"result": result}


def cmd_apply_transition(args: argparse.Namespace) -> dict:
    """Noetva R4-I: the only CLI surface for lifecycle_controller.py's
    apply_transition() -- the pure function that has always been "the one
    function every workflow step calls to move a row forward" per its own
    docstring, but that no workflow could previously reach (R4-DRG D1).
    `--current-row-json` is exactly `lifecycle_table_read`'s own stdout
    shape: `{}` for a genuinely missing row, or the full read entity
    (including `etag`) otherwise. `--ttl-expires-at`/
    `--db-auto-restart-risk-at` are optional companions for the two
    terminal transitions (READY, DORMANT) that must persist an extra
    field atomically alongside the state change -- layered on via a plain
    dataclass replace() AFTER apply_transition() itself has already
    validated and produced the transition; this is CLI-layer field
    merging, not new transition semantics."""
    data = json.loads(args.current_row_json)
    row, is_new = _row_from_dict(args.environment, data)
    new_row = apply_transition(
        row,
        LifecycleState(args.target),
        expected_etag=row.etag,
        new_etag="pending",
        actor=args.actor,
        now=_now(),
        workflow_run_id=args.workflow_run_id,
        error=args.error,
    )
    if args.ttl_expires_at is not None:
        new_row = replace(new_row, ttl_expires_at=_parse_dt(args.ttl_expires_at))
    if args.db_auto_restart_risk_at is not None:
        new_row = replace(new_row, db_auto_restart_risk_at=_parse_dt(args.db_auto_restart_risk_at))
    return {"entity": _row_to_entity(new_row), "isNewRow": is_new}


def cmd_persist_metadata(args: argparse.Namespace) -> dict:
    """Noetva R4-I: persists a metadata-only update that does NOT change
    lifecycle state -- Extend's ttlExpiresAt, Hold's holdUntil, and the
    restart-monitor's bounded-recheck lastError memory all go through
    here rather than apply-transition, because none of them corresponds
    to an edge in lifecycle_controller.py's `_ALLOWED_TRANSITIONS` graph
    (there is no "stay in the same state" transition). Each of
    --ttl-expires-at/--hold-until/--last-error is independently optional:
    omitted means "leave this field unchanged"; --last-error "" (empty
    string) explicitly clears it, matching how every reader in this
    codebase already treats a missing/empty lastError as "no error"."""
    data = json.loads(args.current_row_json)
    row, is_new = _row_from_dict(args.environment, data)
    updates: dict = {}
    if args.ttl_expires_at is not None:
        updates["ttl_expires_at"] = _parse_dt(args.ttl_expires_at)
    if args.hold_until is not None:
        updates["hold_until"] = _parse_dt(args.hold_until)
    if args.last_error is not None:
        updates["last_error"] = args.last_error or None
    new_row = replace(
        row,
        last_actor=args.actor,
        last_transition_at=_now(),
        last_workflow_run_id=args.workflow_run_id or row.last_workflow_run_id,
        **updates,
    )
    return {"entity": _row_to_entity(new_row), "isNewRow": is_new}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lifecycle_cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate-transition")
    p.add_argument("--current", required=True)
    p.add_argument("--target", required=True)
    p.set_defaults(func=cmd_validate_transition)

    p = sub.add_parser("compute-ttl-expiry")
    p.add_argument("--ttl-hours", type=int, required=True)
    p.set_defaults(func=cmd_compute_ttl_expiry)

    p = sub.add_parser("should-suppress-alerts")
    p.add_argument("--lifecycle-state", default="unknown", help="A LifecycleState name, or 'unknown'/omitted if the row could not be read")
    p.set_defaults(func=cmd_should_suppress_alerts)

    p = sub.add_parser("extend-ttl")
    p.add_argument("--current-expiry", default=None)
    p.add_argument("--additional-hours", type=float, required=True)
    p.set_defaults(func=cmd_extend_ttl)

    p = sub.add_parser("compute-hold-until")
    p.add_argument("--hold-hours", type=float, required=True)
    p.set_defaults(func=cmd_compute_hold_until)

    p = sub.add_parser("compute-restart-risk")
    p.add_argument("--stopped-at", required=True)
    p.set_defaults(func=cmd_compute_restart_risk)

    p = sub.add_parser("evaluate-stop-preconditions")
    p.add_argument("--migration-job-running", action="store_true")
    p.add_argument("--deployment-in-progress", action="store_true")
    p.add_argument("--hold-active", action="store_true")
    p.add_argument("--unsafe-long-running-session", action="store_true")
    p.set_defaults(func=cmd_evaluate_stop_preconditions)

    p = sub.add_parser("evaluate-demo-ready")
    p.add_argument("--frontend-reachable", required=True)
    p.add_argument("--backend-healthy", required=True)
    p.add_argument("--db-reachable", required=True)
    p.add_argument("--migration-head-correct", required=True)
    p.add_argument("--authenticated-request-succeeds", default="unknown")
    p.add_argument("--demo-tenant-exists", default="unknown")
    p.add_argument("--golden-thread-finding-exists", default="unknown")
    p.set_defaults(func=cmd_evaluate_demo_ready)

    p = sub.add_parser("classify-postgres-state")
    p.add_argument("--lifecycle-state", required=True)
    p.add_argument("--postgres-reports-ready", required=True)
    p.add_argument("--stopped-at", default=None)
    p.add_argument("--recheck-passed", default="unknown")
    p.set_defaults(func=cmd_classify_postgres_state)

    p = sub.add_parser("apply-transition")
    p.add_argument("--environment", required=True)
    p.add_argument("--current-row-json", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--workflow-run-id", default=None)
    p.add_argument("--error", default=None)
    p.add_argument("--ttl-expires-at", default=None)
    p.add_argument("--db-auto-restart-risk-at", default=None)
    p.set_defaults(func=cmd_apply_transition)

    p = sub.add_parser("persist-metadata")
    p.add_argument("--environment", required=True)
    p.add_argument("--current-row-json", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--workflow-run-id", default=None)
    p.add_argument("--ttl-expires-at", default=None)
    p.add_argument("--hold-until", default=None)
    p.add_argument("--last-error", default=None)
    p.set_defaults(func=cmd_persist_metadata)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except (TransitionRefused, LockConflict, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
