"""Thin CLI wrapper around lifecycle_controller.py so GitHub Actions
workflow YAML (bash) can invoke the pure decision logic without embedding
Python state-machine code inline in every workflow file. Every subcommand
prints one JSON object to stdout and exits 0 on success; exits 1 with a
JSON `{"error": ...}` object on any refusal (TransitionRefused,
LockConflict, ValueError) -- the calling workflow step checks the exit
code, never re-derives the decision itself.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from lifecycle_controller import (
    DemoReadinessResult,
    StopPreconditions,
    TTL_MAX_HOURS,
    TTL_MIN_HOURS,
    classify_unexpected_postgres_state,
    compute_db_auto_restart_risk_at,
    compute_hold_until,
    compute_ttl_expiry,
    evaluate_demo_ready,
    evaluate_stop_preconditions,
    extend_ttl,
    should_suppress_availability_alerts,
    validate_transition,
    LifecycleState,
    TransitionRefused,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except (TransitionRefused, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
