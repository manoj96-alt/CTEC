"""LOCAL / MOCKED CONTROL-LOGIC TESTS ONLY (Noetva I-R2 Section 39).

Every test here exercises lifecycle_controller.py directly, in-process, with
no network access and no Azure SDK. None of these prove Azure runtime
behavior — they prove the state-machine/lock/TTL/precondition *logic* is
correct. Azure runtime verification remains NOT_RUN / AZURE_RUNTIME_REQUIRED
until a real subscription exists (see the final report's AT/BC sections).
"""

from datetime import datetime, timedelta, timezone

import pytest

from lifecycle_controller import (
    DemoReadinessResult,
    LifecycleRow,
    LifecycleState,
    LockConflict,
    StopPreconditions,
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
    is_hold_active,
    is_ttl_expired,
    should_suppress_availability_alerts,
    validate_transition,
    LIFECYCLE_MANAGED_ENVIRONMENTS,
)

NOW = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)


def make_row(state: LifecycleState, **overrides) -> LifecycleRow:
    base = dict(environment="demo", state=state, etag="etag-1")
    base.update(overrides)
    return LifecycleRow(**base)


# ---- production structurally excluded --------------------------------
def test_no_production_in_allowed_environments():
    assert "prod" not in LIFECYCLE_MANAGED_ENVIRONMENTS
    assert "production" not in LIFECYCLE_MANAGED_ENVIRONMENTS
    assert LIFECYCLE_MANAGED_ENVIRONMENTS == {"dev", "staging", "demo"}


# ---- successful start state transitions -------------------------------
def test_successful_start_state_transitions():
    row = make_row(LifecycleState.DORMANT)
    for target in (
        LifecycleState.START_REQUESTED,
        LifecycleState.STARTING_DATABASE,
        LifecycleState.STARTING_APPLICATION,
        LifecycleState.VERIFYING,
        LifecycleState.READY,
    ):
        row = apply_transition(row, target, expected_etag=row.etag, new_etag=f"etag-{target}", actor="ci", now=NOW)
        assert row.state == target


# ---- DB-start failure --------------------------------------------------
def test_db_start_failure_transitions_to_failed_start():
    row = make_row(LifecycleState.STARTING_DATABASE)
    row = apply_transition(row, LifecycleState.FAILED_START, expected_etag=row.etag, new_etag="e2", actor="ci", now=NOW, error="db did not become Ready")
    assert row.state == LifecycleState.FAILED_START
    assert row.last_error == "db did not become Ready"


# ---- DB readiness timeout is just a FAILED_START with a reason --------
def test_db_readiness_timeout_is_failed_start():
    row = make_row(LifecycleState.STARTING_DATABASE)
    row = apply_transition(row, LifecycleState.FAILED_START, expected_etag=row.etag, new_etag="e2", actor="ci", now=NOW, error="timed out waiting for Ready")
    assert row.state == LifecycleState.FAILED_START


# ---- migration-head mismatch / canonical-data missing -> FAILED_START --
def test_migration_head_mismatch_is_failed_start():
    result = DemoReadinessResult(
        frontend_reachable=True, backend_healthy=True, db_reachable=True,
        migration_head_correct=False,
        authenticated_request_succeeds=None, demo_tenant_exists=None, golden_thread_finding_exists=None,
    )
    assert evaluate_demo_ready(result) == "FAILED_START"


# ---- demo-data missing -> DEMO_DATA_NOT_READY, never auto-repaired ----
def test_demo_data_missing_is_not_ready_not_repaired():
    result = DemoReadinessResult(
        frontend_reachable=True, backend_healthy=True, db_reachable=True, migration_head_correct=True,
        authenticated_request_succeeds=True, demo_tenant_exists=False, golden_thread_finding_exists=True,
    )
    assert evaluate_demo_ready(result) == "DEMO_DATA_NOT_READY"


# ---- backend-start / frontend-start failure ---------------------------
def test_backend_not_healthy_is_failed_start():
    result = DemoReadinessResult(
        frontend_reachable=True, backend_healthy=False, db_reachable=True, migration_head_correct=True,
        authenticated_request_succeeds=None, demo_tenant_exists=None, golden_thread_finding_exists=None,
    )
    assert evaluate_demo_ready(result) == "FAILED_START"


def test_frontend_unreachable_is_failed_start():
    result = DemoReadinessResult(
        frontend_reachable=False, backend_healthy=True, db_reachable=True, migration_head_correct=True,
        authenticated_request_succeeds=None, demo_tenant_exists=None, golden_thread_finding_exists=None,
    )
    assert evaluate_demo_ready(result) == "FAILED_START"


# ---- auth runtime-required behavior, never faked -----------------------
def test_auth_unknown_is_azure_runtime_required_not_faked_success():
    result = DemoReadinessResult(
        frontend_reachable=True, backend_healthy=True, db_reachable=True, migration_head_correct=True,
        authenticated_request_succeeds=None, demo_tenant_exists=None, golden_thread_finding_exists=None,
    )
    assert evaluate_demo_ready(result) == "AZURE_RUNTIME_REQUIRED"


def test_auth_fails_is_failed_start_not_ready():
    result = DemoReadinessResult(
        frontend_reachable=True, backend_healthy=True, db_reachable=True, migration_head_correct=True,
        authenticated_request_succeeds=False, demo_tenant_exists=None, golden_thread_finding_exists=None,
    )
    assert evaluate_demo_ready(result) == "FAILED_START"


def test_full_success_is_ready():
    result = DemoReadinessResult(
        frontend_reachable=True, backend_healthy=True, db_reachable=True, migration_head_correct=True,
        authenticated_request_succeeds=True, demo_tenant_exists=True, golden_thread_finding_exists=True,
    )
    assert evaluate_demo_ready(result) == "READY"


# ---- successful stop ----------------------------------------------------
def test_successful_stop_state_transitions():
    row = make_row(LifecycleState.READY)
    for target in (
        LifecycleState.DRAIN_REQUESTED,
        LifecycleState.STOPPING_APPLICATION,
        LifecycleState.STOPPING_DATABASE,
        LifecycleState.DORMANT,
    ):
        row = apply_transition(row, target, expected_etag=row.etag, new_etag=f"etag-{target}", actor="ci", now=NOW)
        assert row.state == target


# ---- migration-running stop refusal ------------------------------------
def test_stop_refused_while_migration_running():
    reasons = evaluate_stop_preconditions(StopPreconditions(
        migration_job_running=True, deployment_in_progress=False, hold_active=False, unsafe_long_running_session=False,
    ))
    assert "migration Job is currently running" in reasons


# ---- deployment-running stop refusal -----------------------------------
def test_stop_refused_while_deployment_in_progress():
    reasons = evaluate_stop_preconditions(StopPreconditions(
        migration_job_running=False, deployment_in_progress=True, hold_active=False, unsafe_long_running_session=False,
    ))
    assert reasons and "deployment" in reasons[0]


# ---- active hold stop refusal -------------------------------------------
def test_stop_refused_while_hold_active():
    reasons = evaluate_stop_preconditions(StopPreconditions(
        migration_job_running=False, deployment_in_progress=False, hold_active=True, unsafe_long_running_session=False,
    ))
    assert any("HOLD" in r for r in reasons)


# ---- long DB transaction stop refusal ------------------------------------
def test_stop_refused_on_unsafe_long_running_session():
    reasons = evaluate_stop_preconditions(StopPreconditions(
        migration_job_running=False, deployment_in_progress=False, hold_active=False, unsafe_long_running_session=True,
    ))
    assert any("long-running" in r for r in reasons)


def test_stop_allowed_when_all_clear():
    reasons = evaluate_stop_preconditions(StopPreconditions(
        migration_job_running=False, deployment_in_progress=False, hold_active=False, unsafe_long_running_session=False,
    ))
    assert reasons == []


# ---- Postgres stop failure / revision deactivate failure -> FAILED_STOP
def test_postgres_stop_failure_is_failed_stop_not_dormant():
    row = make_row(LifecycleState.STOPPING_DATABASE)
    row = apply_transition(row, LifecycleState.FAILED_STOP, expected_etag=row.etag, new_etag="e2", actor="ci", now=NOW, error="postgres stop timed out")
    assert row.state == LifecycleState.FAILED_STOP
    assert row.state != LifecycleState.DORMANT


def test_revision_deactivate_failure_is_failed_stop():
    row = make_row(LifecycleState.DRAIN_REQUESTED)
    row = apply_transition(row, LifecycleState.FAILED_STOP, expected_etag=row.etag, new_etag="e2", actor="ci", now=NOW, error="backend revision failed to deactivate")
    assert row.state == LifecycleState.FAILED_STOP


# ---- FAILED_STOP is a real, distinct, reachable state -------------------
def test_failed_stop_exists_and_is_reachable():
    assert LifecycleState.FAILED_STOP in list(LifecycleState)
    validate_transition(LifecycleState.STOPPING_DATABASE, LifecycleState.FAILED_STOP)  # does not raise


# ---- TTL expiry / not expired / extension -------------------------------
def test_ttl_expiry_computation_and_bounds():
    assert compute_ttl_expiry(NOW, 4) == NOW + timedelta(hours=4)
    with pytest.raises(ValueError):
        compute_ttl_expiry(NOW, 0)
    with pytest.raises(ValueError):
        compute_ttl_expiry(NOW, 13)


def test_ttl_is_expired():
    row = make_row(LifecycleState.READY, ttl_expires_at=NOW - timedelta(minutes=1))
    assert is_ttl_expired(row, NOW) is True


def test_ttl_not_expired():
    row = make_row(LifecycleState.READY, ttl_expires_at=NOW + timedelta(hours=1))
    assert is_ttl_expired(row, NOW) is False


def test_ttl_extension_only_from_ready_or_in_use():
    assert can_extend(make_row(LifecycleState.READY)) is True
    assert can_extend(make_row(LifecycleState.IN_USE)) is True
    for blocked in (
        LifecycleState.DORMANT, LifecycleState.FAILED_START, LifecycleState.FAILED_STOP,
        LifecycleState.STOPPING_APPLICATION, LifecycleState.STOPPING_DATABASE,
        LifecycleState.STARTING_DATABASE, LifecycleState.STARTING_APPLICATION,
    ):
        assert can_extend(make_row(blocked)) is False


# ---- hold expiry / no permanent hold ------------------------------------
def test_hold_expiry():
    row = make_row(LifecycleState.READY, hold_until=NOW - timedelta(minutes=1))
    assert is_hold_active(row, NOW) is False
    row2 = make_row(LifecycleState.READY, hold_until=NOW + timedelta(hours=2))
    assert is_hold_active(row2, NOW) is True


def test_no_permanent_hold_is_representable():
    with pytest.raises(ValueError):
        compute_hold_until(NOW, 0)
    with pytest.raises(ValueError):
        compute_hold_until(NOW, -1)
    # A very large but still finite value is accepted -- there is simply no
    # way to express "forever" through this function's contract.
    assert compute_hold_until(NOW, 24) == NOW + timedelta(hours=24)


# ---- ETag conflict -------------------------------------------------------
def test_etag_conflict_raises_lock_conflict():
    row = make_row(LifecycleState.DORMANT, etag="etag-A")
    with pytest.raises(LockConflict):
        apply_transition(row, LifecycleState.START_REQUESTED, expected_etag="etag-STALE", new_etag="etag-B", actor="ci", now=NOW)


def test_invalid_transition_refused():
    row = make_row(LifecycleState.DORMANT)
    with pytest.raises(TransitionRefused):
        apply_transition(row, LifecycleState.READY, expected_etag=row.etag, new_etag="e2", actor="ci", now=NOW)


# ---- restart monitor: legitimate-active case (do nothing) ---------------
def test_restart_monitor_legitimate_active_case_is_ok():
    result = classify_unexpected_postgres_state(
        lifecycle_state=LifecycleState.READY, postgres_reports_ready=True, now=NOW,
        stopped_at=None, maintenance_window_recheck_passed=None,
    )
    assert result == "OK"


# ---- restart monitor: DORMANT + running (first sighting) ----------------
def test_restart_monitor_dormant_and_running_first_sighting_is_suspected_not_alarmed():
    result = classify_unexpected_postgres_state(
        lifecycle_state=LifecycleState.DORMANT, postgres_reports_ready=True, now=NOW,
        stopped_at=NOW - timedelta(days=8), maintenance_window_recheck_passed=None,
    )
    assert result == "TRANSIENT_MAINTENANCE_SUSPECTED"


# ---- restart monitor: transient maintenance case (self-resolves) --------
def test_restart_monitor_maintenance_transient_case_resolves_to_ok():
    result = classify_unexpected_postgres_state(
        lifecycle_state=LifecycleState.DORMANT, postgres_reports_ready=True, now=NOW,
        stopped_at=NOW - timedelta(days=2), maintenance_window_recheck_passed=True,
    )
    assert result == "OK"


# ---- restart monitor: sustained DORMANT+Ready is a genuine anomaly ------
def test_restart_monitor_sustained_dormant_running_is_unexpected_restart():
    result = classify_unexpected_postgres_state(
        lifecycle_state=LifecycleState.DORMANT, postgres_reports_ready=True, now=NOW,
        stopped_at=NOW - timedelta(days=8), maintenance_window_recheck_passed=False,
    )
    assert result == "UNEXPECTED_RESTART"


def test_extend_ttl_adds_to_existing_future_expiry():
    current = NOW + timedelta(hours=1)  # e.g. 15:00 when now is 14:00
    result = extend_ttl(current, 2, NOW)
    assert result == current + timedelta(hours=2)  # 17:00, not now+2h


def test_extend_ttl_falls_back_to_now_if_expiry_already_past():
    stale = NOW - timedelta(hours=5)
    result = extend_ttl(stale, 2, NOW)
    assert result == NOW + timedelta(hours=2)


def test_extend_ttl_rejects_non_positive_duration():
    with pytest.raises(ValueError):
        extend_ttl(NOW + timedelta(hours=1), 0, NOW)


# ---- alert-suppression semantics (Noetva G-R3 Section 16) -- ALL LOCAL / STATIC / MOCKED,
# no real Azure Monitor call is made or claimed by any of these. ----------

def test_dormant_suppresses_availability_alerts():
    assert should_suppress_availability_alerts(LifecycleState.DORMANT) is True


def test_ready_enables_availability_alerts():
    assert should_suppress_availability_alerts(LifecycleState.READY) is False


def test_in_use_enables_availability_alerts():
    assert should_suppress_availability_alerts(LifecycleState.IN_USE) is False


def test_failed_start_enables_availability_alerts():
    assert should_suppress_availability_alerts(LifecycleState.FAILED_START) is False


def test_failed_stop_enables_availability_alerts():
    assert should_suppress_availability_alerts(LifecycleState.FAILED_STOP) is False


def test_unknown_state_enables_availability_alerts_fail_safe():
    # None represents "the row could not be read at all" -- Section 13's
    # explicit fail-safe: missing/corrupt/unreadable/lock-conflicted state
    # must never default to suppression.
    assert should_suppress_availability_alerts(None) is False


def test_starting_states_remain_suppressed_as_bounded_grace():
    for state in (
        LifecycleState.START_REQUESTED,
        LifecycleState.STARTING_DATABASE,
        LifecycleState.STARTING_APPLICATION,
        LifecycleState.VERIFYING,
    ):
        assert should_suppress_availability_alerts(state) is True


def test_stopping_states_remain_suppressed():
    for state in (
        LifecycleState.DRAIN_REQUESTED,
        LifecycleState.STOPPING_APPLICATION,
        LifecycleState.STOPPING_DATABASE,
    ):
        assert should_suppress_availability_alerts(state) is True


def test_start_sequence_ends_with_alerts_restored():
    # The frozen start sequence's final transition is ...VERIFYING->READY;
    # confirm the suppression decision actually flips at that exact edge.
    assert should_suppress_availability_alerts(LifecycleState.VERIFYING) is True
    assert should_suppress_availability_alerts(LifecycleState.READY) is False


def test_stop_failure_restores_alerting_not_suppression():
    # A failed stop must not be left silently suppressed just because the
    # stop sequence had suppression active up to that point.
    assert should_suppress_availability_alerts(LifecycleState.STOPPING_DATABASE) is True
    assert should_suppress_availability_alerts(LifecycleState.FAILED_STOP) is False


def test_db_auto_restart_risk_is_seven_days_out():
    stopped_at = NOW
    assert compute_db_auto_restart_risk_at(stopped_at) == stopped_at + timedelta(days=7)
