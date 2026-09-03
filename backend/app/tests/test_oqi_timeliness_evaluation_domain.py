"""Pure domain unit tests for `app.domain.oqi_timeliness.policy` and
`app.domain.oqi_timeliness.evaluation` (CDD-051 §3-§4, §8, §17-§19;
Artifact Authorization row 12): the governed Timeliness policy envelope,
the Evaluation/Finding dataclasses, deterministic identity derivation, and
the Finding-lifecycle transition function -- all in isolation, no
PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi.quality_rule import OQI_NAMESPACE
from app.domain.oqi_integrity.structural import OQI_INTEGRITY_NAMESPACE
from app.domain.oqi_timeliness.evaluation import (
    OQI_TIMELINESS_NAMESPACE,
    TimelinessEvaluation,
    TimelinessFinding,
    TimelinessFindingStatus,
    TimelinessFindingType,
    apply_timeliness_finding_transition,
    derive_timeliness_evaluation_id,
    derive_timeliness_finding_id,
    timeliness_finding_identity_material,
)
from app.domain.oqi_timeliness.policy import (
    TimelinessPolicy,
    TimelinessPolicyStatus,
    new_timeliness_policy,
    new_timeliness_policy_version,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TENANT = "tenant-a"


def _policy(
    *,
    policy_id: UUID | None = None,
    version: int = 1,
    freshness_window_seconds: int | None = 1800,
    ingestion_sla_seconds: int | None = None,
    status: TimelinessPolicyStatus = TimelinessPolicyStatus.ACTIVE,
) -> TimelinessPolicy:
    return TimelinessPolicy(
        policy_id=policy_id or uuid4(),
        version=version,
        tenant_id=TENANT,
        information_element_requirement_id=uuid4(),
        business_process_id=uuid4(),
        business_process_version=1,
        freshness_window_seconds=freshness_window_seconds,
        ingestion_sla_seconds=ingestion_sla_seconds,
        status=status,
        created_by="steward",
        created_on=NOW,
    )


# --- TimelinessPolicy validation ---


def test_policy_requires_at_least_one_threshold() -> None:
    with pytest.raises(ValidationException):
        _policy(freshness_window_seconds=None, ingestion_sla_seconds=None)


def test_policy_allows_freshness_only() -> None:
    policy = _policy(freshness_window_seconds=1800, ingestion_sla_seconds=None)
    assert policy.freshness_window_seconds == 1800
    assert policy.ingestion_sla_seconds is None


def test_policy_allows_ingestion_sla_only() -> None:
    policy = _policy(freshness_window_seconds=None, ingestion_sla_seconds=900)
    assert policy.ingestion_sla_seconds == 900


def test_policy_allows_both_thresholds() -> None:
    policy = _policy(freshness_window_seconds=1800, ingestion_sla_seconds=900)
    assert policy.freshness_window_seconds == 1800
    assert policy.ingestion_sla_seconds == 900


def test_policy_rejects_zero_threshold() -> None:
    with pytest.raises(ValidationException):
        _policy(freshness_window_seconds=0)


def test_policy_rejects_negative_threshold() -> None:
    with pytest.raises(ValidationException):
        _policy(ingestion_sla_seconds=-1)


def test_policy_rejects_naive_created_on() -> None:
    with pytest.raises(ValidationException):
        TimelinessPolicy(
            policy_id=uuid4(),
            version=1,
            tenant_id=TENANT,
            information_element_requirement_id=uuid4(),
            business_process_id=uuid4(),
            business_process_version=1,
            freshness_window_seconds=1800,
            ingestion_sla_seconds=None,
            status=TimelinessPolicyStatus.ACTIVE,
            created_by="steward",
            created_on=datetime(2026, 1, 1),  # noqa: DTZ001 -- deliberately naive
        )


def test_policy_rejects_version_below_one() -> None:
    with pytest.raises(ValidationException):
        _policy(version=0)


def test_new_timeliness_policy_is_version_one_active() -> None:
    policy = new_timeliness_policy(
        policy_id=uuid4(),
        tenant_id=TENANT,
        information_element_requirement_id=uuid4(),
        business_process_id=uuid4(),
        business_process_version=1,
        freshness_window_seconds=1800,
        ingestion_sla_seconds=None,
        created_by="steward",
        created_on=NOW,
    )
    assert policy.version == 1
    assert policy.status is TimelinessPolicyStatus.ACTIVE


def test_new_policy_version_preserves_stable_policy_id_and_anchor() -> None:
    v1 = new_timeliness_policy(
        policy_id=uuid4(),
        tenant_id=TENANT,
        information_element_requirement_id=uuid4(),
        business_process_id=uuid4(),
        business_process_version=1,
        freshness_window_seconds=1800,
        ingestion_sla_seconds=None,
        created_by="steward",
        created_on=NOW,
    )
    v2 = new_timeliness_policy_version(
        v1,
        freshness_window_seconds=3600,
        status=TimelinessPolicyStatus.RETIRED,
        created_by="steward",
        created_on=NOW,
    )
    assert v2.policy_id == v1.policy_id
    assert v2.version == 2
    assert v2.information_element_requirement_id == v1.information_element_requirement_id
    assert v2.business_process_id == v1.business_process_id
    assert v2.freshness_window_seconds == 3600
    assert v2.status is TimelinessPolicyStatus.RETIRED
    # v1 itself is byte-unchanged (immutable, frozen dataclass).
    assert v1.version == 1
    assert v1.status is TimelinessPolicyStatus.ACTIVE


# --- Namespace distinctness (CDD-051 §17-§18) ---


def test_timeliness_namespace_distinct_from_every_other_oqi_namespace() -> None:
    assert OQI_TIMELINESS_NAMESPACE != OQI_NAMESPACE
    assert OQI_TIMELINESS_NAMESPACE != OQI_INTEGRITY_NAMESPACE


# --- Finding identity (CDD-051 §17) ---


def test_finding_identity_is_deterministic() -> None:
    tenant_id = TENANT
    policy_id = uuid4()
    source_object_id = uuid4()
    a = derive_timeliness_finding_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
    )
    b = derive_timeliness_finding_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
    )
    assert a == b


def test_finding_identity_excludes_evaluation_horizon_and_evaluated_on() -> None:
    """CDD-051 §17, Principle 14: age advancing every minute must never
    churn Finding identity. Finding identity does not even accept these
    inputs -- proven by construction, not by comparing two derivations."""
    tenant_id = TENANT
    policy_id = uuid4()
    source_object_id = uuid4()
    material_1 = timeliness_finding_identity_material(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
    )
    material_2 = timeliness_finding_identity_material(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
    )
    assert material_1 == material_2


def test_finding_identity_excludes_policy_version() -> None:
    """A policy threshold tuning (new version, same policy_id) must never
    create a duplicate current Finding for the same governed subject."""
    tenant_id = TENANT
    policy_id = uuid4()
    source_object_id = uuid4()
    finding_id_v1_material = timeliness_finding_identity_material(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
    )
    # No policy_version parameter exists on this function at all -- the
    # absence itself is the proof.
    assert "policy_version" not in finding_id_v1_material


def test_two_finding_types_never_collide_for_same_subject() -> None:
    tenant_id = TENANT
    policy_id = uuid4()
    source_object_id = uuid4()
    stale = derive_timeliness_finding_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
    )
    latency = derive_timeliness_finding_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=TimelinessFindingType.INGESTION_LATENCY_EXCEEDED,
        source_object_id=source_object_id,
    )
    assert stale != latency


def test_different_tenant_never_collides() -> None:
    policy_id = uuid4()
    source_object_id = uuid4()
    a = derive_timeliness_finding_id(
        tenant_id="tenant-a",
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
    )
    b = derive_timeliness_finding_id(
        tenant_id="tenant-b",
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
    )
    assert a != b


# --- Evaluation identity (CDD-051 §18) ---


def test_evaluation_identity_includes_horizon_version_and_evidence() -> None:
    tenant_id = TENANT
    policy_id = uuid4()
    source_object_id = uuid4()
    field_value_evidence_id = uuid4()

    base = derive_timeliness_evaluation_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        policy_version=1,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
        field_value_evidence_id=field_value_evidence_id,
        evaluation_horizon=NOW,
    )
    different_horizon = derive_timeliness_evaluation_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        policy_version=1,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
        field_value_evidence_id=field_value_evidence_id,
        evaluation_horizon=NOW + timedelta(hours=1),
    )
    different_version = derive_timeliness_evaluation_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        policy_version=2,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
        field_value_evidence_id=field_value_evidence_id,
        evaluation_horizon=NOW,
    )
    different_evidence = derive_timeliness_evaluation_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        policy_version=1,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
        field_value_evidence_id=uuid4(),
        evaluation_horizon=NOW,
    )
    repeat = derive_timeliness_evaluation_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        policy_version=1,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=source_object_id,
        field_value_evidence_id=field_value_evidence_id,
        evaluation_horizon=NOW,
    )
    assert base == repeat  # idempotent replay
    assert base != different_horizon
    assert base != different_version
    assert base != different_evidence


def test_evaluation_identity_rejects_naive_horizon() -> None:
    with pytest.raises(ValidationException):
        derive_timeliness_evaluation_id(
            tenant_id=TENANT,
            policy_id=uuid4(),
            policy_version=1,
            finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
            source_object_id=uuid4(),
            field_value_evidence_id=uuid4(),
            evaluation_horizon=datetime(2026, 1, 1),  # noqa: DTZ001
        )


def test_evaluation_rejects_id_inconsistent_with_its_own_inputs() -> None:
    with pytest.raises(ValidationException):
        TimelinessEvaluation(
            evaluation_id=uuid4(),  # wrong -- not derived from the fields below
            tenant_id=TENANT,
            policy_id=uuid4(),
            policy_version=1,
            finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
            source_object_id=uuid4(),
            field_value_evidence_id=uuid4(),
            outcome=EvaluationOutcome.SATISFIED,
            evaluation_horizon=NOW,
            evaluated_on=NOW,
        )


def test_finding_rejects_id_inconsistent_with_its_own_inputs() -> None:
    with pytest.raises(ValidationException):
        TimelinessFinding(
            finding_id=uuid4(),  # wrong
            tenant_id=TENANT,
            policy_id=uuid4(),
            finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
            source_object_id=uuid4(),
            status=TimelinessFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
        )


# --- Finding lifecycle transition (CDD-051 §19) ---


def _transition(
    *,
    existing: TimelinessFinding | None,
    outcome: EvaluationOutcome,
    horizon: datetime = NOW,
    policy_id: UUID | None = None,
    source_object_id: UUID | None = None,
) -> TimelinessFinding | None:
    return apply_timeliness_finding_transition(
        existing=existing,
        outcome=outcome,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        evaluation_horizon=horizon,
        tenant_id=TENANT,
        policy_id=policy_id or uuid4(),
        source_object_id=source_object_id or uuid4(),
    )


def test_no_finding_satisfied_stays_none() -> None:
    assert _transition(existing=None, outcome=EvaluationOutcome.SATISFIED) is None


def test_no_finding_violated_opens_new_finding() -> None:
    finding = _transition(existing=None, outcome=EvaluationOutcome.VIOLATED)
    assert finding is not None
    assert finding.status is TimelinessFindingStatus.OPEN
    assert finding.state_revision == 1
    assert finding.occurrence_count == 1
    assert finding.reopen_count == 0


def test_open_violated_stays_open_and_advances_revision() -> None:
    policy_id, source_object_id = uuid4(), uuid4()
    opened = _transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    assert opened is not None
    still_open = _transition(
        existing=opened,
        outcome=EvaluationOutcome.VIOLATED,
        horizon=NOW + timedelta(hours=1),
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    assert still_open is not None
    assert still_open.status is TimelinessFindingStatus.OPEN
    assert still_open.state_revision == opened.state_revision + 1
    assert still_open.first_seen_at == opened.first_seen_at  # unchanged
    assert still_open.last_seen_at == NOW + timedelta(hours=1)


def test_open_satisfied_resolves() -> None:
    policy_id, source_object_id = uuid4(), uuid4()
    opened = _transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    assert opened is not None
    resolved = _transition(
        existing=opened,
        outcome=EvaluationOutcome.SATISFIED,
        horizon=NOW + timedelta(hours=1),
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    assert resolved is not None
    assert resolved.status is TimelinessFindingStatus.RESOLVED
    assert resolved.state_revision == opened.state_revision + 1


def test_resolved_satisfied_stays_resolved() -> None:
    policy_id, source_object_id = uuid4(), uuid4()
    opened = _transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    resolved = _transition(
        existing=opened,
        outcome=EvaluationOutcome.SATISFIED,
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    assert resolved is not None
    still_resolved = _transition(
        existing=resolved,
        outcome=EvaluationOutcome.SATISFIED,
        horizon=NOW + timedelta(hours=2),
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    assert still_resolved is not None
    assert still_resolved.status is TimelinessFindingStatus.RESOLVED
    assert still_resolved.occurrence_count == resolved.occurrence_count
    assert still_resolved.reopen_count == resolved.reopen_count


def test_resolved_violated_reopens() -> None:
    policy_id, source_object_id = uuid4(), uuid4()
    opened = _transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    resolved = _transition(
        existing=opened,
        outcome=EvaluationOutcome.SATISFIED,
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    assert resolved is not None
    reopened = _transition(
        existing=resolved,
        outcome=EvaluationOutcome.VIOLATED,
        horizon=NOW + timedelta(hours=3),
        policy_id=policy_id,
        source_object_id=source_object_id,
    )
    assert reopened is not None
    assert reopened.status is TimelinessFindingStatus.OPEN
    assert reopened.occurrence_count == resolved.occurrence_count + 1
    assert reopened.reopen_count == resolved.reopen_count + 1


def test_transition_rejects_mismatched_existing_finding_identity() -> None:
    own_policy_id, own_source_object_id = uuid4(), uuid4()
    unrelated = TimelinessFinding(
        finding_id=derive_timeliness_finding_id(
            tenant_id=TENANT,
            policy_id=own_policy_id,
            finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
            source_object_id=own_source_object_id,
        ),
        tenant_id=TENANT,
        policy_id=own_policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=own_source_object_id,
        status=TimelinessFindingStatus.OPEN,
        state_revision=1,
        first_seen_at=NOW,
        last_seen_at=NOW,
        last_evaluated_horizon=NOW,
        occurrence_count=1,
        reopen_count=0,
    )
    with pytest.raises(ValidationException):
        apply_timeliness_finding_transition(
            existing=unrelated,
            outcome=EvaluationOutcome.VIOLATED,
            finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
            evaluation_horizon=NOW,
            tenant_id=TENANT,
            policy_id=uuid4(),  # different policy_id -- identity mismatch
            source_object_id=uuid4(),
        )
