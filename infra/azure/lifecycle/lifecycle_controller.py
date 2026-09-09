"""Noetva Azure environment lifecycle — pure control-plane logic.

This module contains ONLY decision logic: valid state transitions, TTL/hold
bounds and expiry, optimistic-lock semantics, and stop/start precondition
evaluation. It deliberately contains NO Azure SDK calls and NO network I/O —
every fact it reasons about (Postgres state, migration-Job state, deployment
state, DB session safety) is supplied by the caller as plain data, gathered
by the surrounding GitHub Actions workflow's own `az`/`gh` CLI steps.

This is what makes NOETVA-AZURE-COST-LIFECYCLE-I-R2 Section 39's exhaustive
test list runnable locally, today, with no Azure subscription: every test in
test_lifecycle_controller.py exercises this module directly, in-process, and
is labeled LOCAL / MOCKED CONTROL-LOGIC TEST, never claimed as an Azure
runtime result.

Durable state is modeled as a plain dict matching one Azure Table Storage
entity (Noetva I-R2 Section 9): environment, state, ttlExpiresAt, holdUntil,
lastActor, lastTransitionAt, lockOwner, lockToken, dbAutoRestartRiskAt,
lastWorkflowRunId, lastError, and the entity's ETag. The real workflow layer
is responsible for translating this dict to/from an actual azure-data-tables
`TableClient.get_entity`/`update_entity(..., etag=..., match_condition=...)`
call; this module only computes what the NEXT entity value and HTTP-level
match-condition should be, and never talks to Azure itself.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum


class LifecycleState(str, Enum):
    DORMANT = "DORMANT"
    START_REQUESTED = "START_REQUESTED"
    STARTING_DATABASE = "STARTING_DATABASE"
    STARTING_APPLICATION = "STARTING_APPLICATION"
    VERIFYING = "VERIFYING"
    READY = "READY"
    IN_USE = "IN_USE"
    DRAIN_REQUESTED = "DRAIN_REQUESTED"
    STOPPING_APPLICATION = "STOPPING_APPLICATION"
    STOPPING_DATABASE = "STOPPING_DATABASE"
    FAILED_START = "FAILED_START"
    FAILED_STOP = "FAILED_STOP"


# Noetva D0/G-R2/I-R2: production is never a member of this enum's caller-
# facing surface. This set exists so a static test can assert it directly —
# see test_lifecycle_controller.py::test_no_production_in_allowed_environments.
LIFECYCLE_MANAGED_ENVIRONMENTS = frozenset({"dev", "staging", "demo"})

TTL_MIN_HOURS = 1
TTL_MAX_HOURS = 12
TTL_DEFAULT_HOURS = 4

# The valid state graph (Noetva G-R2 Section P / I-R2 Section 1). Any
# transition not listed here is refused by `validate_transition`.
_ALLOWED_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.DORMANT: frozenset({LifecycleState.START_REQUESTED}),
    LifecycleState.START_REQUESTED: frozenset({LifecycleState.STARTING_DATABASE, LifecycleState.FAILED_START}),
    LifecycleState.STARTING_DATABASE: frozenset({LifecycleState.STARTING_APPLICATION, LifecycleState.FAILED_START}),
    LifecycleState.STARTING_APPLICATION: frozenset({LifecycleState.VERIFYING, LifecycleState.FAILED_START}),
    LifecycleState.VERIFYING: frozenset({LifecycleState.READY, LifecycleState.FAILED_START}),
    LifecycleState.READY: frozenset({LifecycleState.IN_USE, LifecycleState.DRAIN_REQUESTED}),
    LifecycleState.IN_USE: frozenset({LifecycleState.DRAIN_REQUESTED}),
    LifecycleState.DRAIN_REQUESTED: frozenset({LifecycleState.STOPPING_APPLICATION, LifecycleState.FAILED_STOP}),
    LifecycleState.STOPPING_APPLICATION: frozenset({LifecycleState.STOPPING_DATABASE, LifecycleState.FAILED_STOP}),
    LifecycleState.STOPPING_DATABASE: frozenset({LifecycleState.DORMANT, LifecycleState.FAILED_STOP}),
    # Failure states require a human/operator-triggered re-entry: a fresh
    # START_REQUESTED (to retry starting) or an explicit stop attempt (to
    # tear down a half-started environment). Never silently self-heals.
    LifecycleState.FAILED_START: frozenset({LifecycleState.START_REQUESTED, LifecycleState.DRAIN_REQUESTED}),
    LifecycleState.FAILED_STOP: frozenset({LifecycleState.DRAIN_REQUESTED}),
}


class TransitionRefused(Exception):
    pass


class LockConflict(Exception):
    """Raised when the caller's known ETag no longer matches — someone else
    (another workflow run, or a human `az`/`gh` action) changed this
    environment's row first. Optimistic-lock layer 2 (Noetva I-R2 Section 10)."""


@dataclass(frozen=True, slots=True)
class LifecycleRow:
    environment: str
    state: LifecycleState
    etag: str
    ttl_expires_at: datetime | None = None
    hold_until: datetime | None = None
    last_actor: str | None = None
    last_transition_at: datetime | None = None
    lock_owner: str | None = None
    lock_token: str | None = None
    db_auto_restart_risk_at: datetime | None = None
    last_workflow_run_id: str | None = None
    last_error: str | None = None


def validate_transition(current: LifecycleState, target: LifecycleState) -> None:
    allowed = _ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise TransitionRefused(f"{current} -> {target} is not an allowed transition")


def apply_transition(
    row: LifecycleRow,
    target: LifecycleState,
    *,
    expected_etag: str,
    new_etag: str,
    actor: str,
    now: datetime,
    workflow_run_id: str | None = None,
    error: str | None = None,
) -> LifecycleRow:
    """The one function every workflow step calls to move a row forward.
    Raises LockConflict if `expected_etag` is stale (Noetva I-R2 Section 10)
    and TransitionRefused if the target state isn't reachable from the
    current one (Noetva I-R2 Section 1's frozen state graph)."""
    if row.etag != expected_etag:
        raise LockConflict(f"expected etag {expected_etag!r}, row is at {row.etag!r}")
    validate_transition(row.state, target)
    return replace(
        row,
        state=target,
        etag=new_etag,
        last_actor=actor,
        last_transition_at=now,
        last_workflow_run_id=workflow_run_id or row.last_workflow_run_id,
        last_error=error,
    )


def compute_ttl_expiry(now: datetime, ttl_hours: int) -> datetime:
    if not (TTL_MIN_HOURS <= ttl_hours <= TTL_MAX_HOURS):
        raise ValueError(f"ttl_hours must be between {TTL_MIN_HOURS} and {TTL_MAX_HOURS}, got {ttl_hours}")
    return now + timedelta(hours=ttl_hours)


def is_ttl_expired(row: LifecycleRow, now: datetime) -> bool:
    return row.ttl_expires_at is not None and now >= row.ttl_expires_at


def is_hold_active(row: LifecycleRow, now: datetime) -> bool:
    return row.hold_until is not None and now < row.hold_until


def compute_hold_until(now: datetime, hold_hours: float) -> datetime:
    """Noetva G-R2/I-R2 Section 19: no permanent hold is ever representable
    — this function has no "forever" input and always returns a bounded,
    absolute timestamp."""
    if hold_hours <= 0:
        raise ValueError("hold_hours must be a positive, bounded duration — permanent holds are not supported")
    return now + timedelta(hours=hold_hours)


def extend_ttl(current_expiry: datetime | None, additional_hours: float, now: datetime) -> datetime:
    """Noetva I-R2 Section 18/23: "current expiry 15:00 -> extend +2h ->
    new expiry 17:00" — extends from the EXISTING expiry, not from `now`,
    so a mid-session extension doesn't shorten remaining time. Falls back
    to extending from `now` if the current expiry is missing or already in
    the past (e.g. a stale row), rather than compounding onto a bygone
    timestamp."""
    if additional_hours <= 0:
        raise ValueError("additional_hours must be positive")
    base = current_expiry if (current_expiry is not None and current_expiry > now) else now
    return base + timedelta(hours=additional_hours)


def can_extend(row: LifecycleRow) -> bool:
    """Noetva I-R2 Section 18: extension is only ever valid from READY/IN_USE."""
    return row.state in (LifecycleState.READY, LifecycleState.IN_USE)


@dataclass(frozen=True, slots=True)
class StopPreconditions:
    migration_job_running: bool
    deployment_in_progress: bool
    hold_active: bool
    unsafe_long_running_session: bool


def evaluate_stop_preconditions(pre: StopPreconditions) -> list[str]:
    """Returns a list of refusal reasons; empty list means the stop may
    proceed. Noetva I-R2 Section 23/24: never terminates a session
    automatically, never races a migration or deployment — refuses and
    reports why instead."""
    reasons = []
    if pre.migration_job_running:
        reasons.append("migration Job is currently running")
    if pre.deployment_in_progress:
        reasons.append("a deployment workflow is currently in progress")
    if pre.hold_active:
        reasons.append("an active HOLD prevents automatic shutdown")
    if pre.unsafe_long_running_session:
        reasons.append("an unsafe long-running database session was detected")
    return reasons


@dataclass(frozen=True, slots=True)
class DemoReadinessResult:
    frontend_reachable: bool
    backend_healthy: bool
    db_reachable: bool
    migration_head_correct: bool
    authenticated_request_succeeds: bool | None  # None == AZURE_RUNTIME_REQUIRED, not fabricated
    demo_tenant_exists: bool | None
    golden_thread_finding_exists: bool | None


def evaluate_demo_ready(result: DemoReadinessResult) -> str:
    """Returns one of: READY, FAILED_START, DEMO_DATA_NOT_READY,
    AZURE_RUNTIME_REQUIRED. Never mutates data (Noetva I-R2 Section 27) —
    this function only classifies inputs it was given."""
    if not (result.frontend_reachable and result.backend_healthy and result.db_reachable):
        return "FAILED_START"
    if not result.migration_head_correct:
        return "FAILED_START"
    if result.authenticated_request_succeeds is None:
        return "AZURE_RUNTIME_REQUIRED"
    if not result.authenticated_request_succeeds:
        return "FAILED_START"
    if result.demo_tenant_exists is None or result.golden_thread_finding_exists is None:
        return "AZURE_RUNTIME_REQUIRED"
    if not (result.demo_tenant_exists and result.golden_thread_finding_exists):
        return "DEMO_DATA_NOT_READY"
    return "READY"


# Noetva G-R3 Section 10-13: exactly which lifecycle states intentionally
# suppress Container Apps availability alerts (via
# modules/lifecycle-alert-suppression.bicep's toggle). Deliberately an
# explicit allow-list, not a deny-list -- anything not enumerated here
# (including a future state this module doesn't yet know about) falls
# through to "alerts enabled", never the reverse. This is what makes the
# fail-safe/fail-open guarantee in `should_suppress_availability_alerts`
# structural rather than a matter of remembering to update a blocklist.
_SUPPRESSION_STATES = frozenset({
    LifecycleState.DORMANT,
    LifecycleState.START_REQUESTED,
    LifecycleState.STARTING_DATABASE,
    LifecycleState.STARTING_APPLICATION,
    LifecycleState.VERIFYING,
    LifecycleState.DRAIN_REQUESTED,
    LifecycleState.STOPPING_APPLICATION,
    LifecycleState.STOPPING_DATABASE,
})


def should_suppress_availability_alerts(state: LifecycleState | None) -> bool:
    """Noetva G-R3 Section 12/13 truth contract, implemented exactly:

    - DORMANT and every state on the path to/from it (START_REQUESTED
      through VERIFYING, DRAIN_REQUESTED through STOPPING_DATABASE):
      suppressed. This also delivers the "bounded startup grace" Section
      12 asks for -- suppression simply doesn't lift until READY is
      actually reached, however long starting takes.
    - READY / IN_USE: never suppressed.
    - FAILED_START / FAILED_STOP: never suppressed -- a failure must
      always be alertable, exactly per Section 12/37/38.
    - `None` (the caller could not determine the state at all -- a
      missing, corrupt, unreadable, or lock-conflicted row) or any value
      this function does not explicitly recognize: never suppressed.
      This is the fail-safe default from Section 13 ("never default to
      suppression"), achieved structurally: only the explicit
      `_SUPPRESSION_STATES` allow-list can return True.

    This function only decides the boolean the caller should pass to
    `az monitor alert-processing-rule update --enabled`; it never talks
    to Azure itself.
    """
    if state is None:
        return False
    return state in _SUPPRESSION_STATES


def compute_db_auto_restart_risk_at(stopped_at: datetime) -> datetime:
    """Noetva G-R2 Section J: Postgres Flexible Server auto-restarts after
    7 days if not manually restarted — directly quoted from current
    Microsoft documentation during that phase. This is the date the
    restart-monitor workflow treats as "past this point, an unexpected
    Ready state is not a maintenance blip, it's the 7-day auto-restart.\""""
    return stopped_at + timedelta(days=7)


def classify_unexpected_postgres_state(
    *,
    lifecycle_state: LifecycleState,
    postgres_reports_ready: bool,
    now: datetime,
    stopped_at: datetime | None,
    maintenance_window_recheck_passed: bool | None,
) -> str:
    """Noetva I-R2 Section 15/16: distinguishes a genuine 7-day auto-restart
    (or an otherwise-unexplained restart) from a transient monthly-
    maintenance blip that self-resolves back to Stopped.

    Returns one of: "OK" (nothing to do), "TRANSIENT_MAINTENANCE_SUSPECTED"
    (recheck later, do not alarm yet), "UNEXPECTED_RESTART" (safely re-stop
    and record an anomaly)."""
    if lifecycle_state != LifecycleState.DORMANT or not postgres_reports_ready:
        return "OK"
    if maintenance_window_recheck_passed is None:
        # First observation of DORMANT+Ready: bounded recheck logic (Section
        # 16) — don't alarm on the very first sighting, ask the caller to
        # recheck after a bounded delay before concluding anything.
        return "TRANSIENT_MAINTENANCE_SUSPECTED"
    if maintenance_window_recheck_passed:
        # It went back to Stopped on its own within the bounded recheck
        # window — a transient maintenance restart, not an anomaly.
        return "OK"
    return "UNEXPECTED_RESTART"
