"""CDD-084 OQI-H6 Governed EnterpriseEntity Uniqueness -- Artifact
Authorization row 13: domain-level unit tests (no PostgreSQL) for pair
canonicalization, Finding/evaluation identity, and the four-branch
evaluation-driven + two-branch adjudication-driven Finding transitions in
isolation. Mirrors `test_oqi_timeliness_evaluation_domain.py`'s established
precedent exactly."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.oqi_uniqueness.candidate import (
    UniquenessAdjudicationAction,
    canonicalize_pair,
)
from app.domain.oqi_uniqueness.evaluation import (
    UniquenessFinding,
    UniquenessFindingStatus,
    UniquenessNotEvaluableReason,
    UniquenessOutcome,
    apply_uniqueness_adjudication_transition,
    apply_uniqueness_finding_transition,
    derive_uniqueness_evaluation_id,
    derive_uniqueness_finding_id,
    uniqueness_finding_identity_material,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TENANT = "tenant-domain-test"


def test_canonicalize_pair_orders_by_uuid() -> None:
    low, high = sorted((uuid4(), uuid4()))
    a, b = canonicalize_pair(high, low)
    assert (a, b) == (low, high)
    assert a < b


def test_canonicalize_pair_rejects_self_pair() -> None:
    entity_id = uuid4()
    with pytest.raises(ValidationException):
        canonicalize_pair(entity_id, entity_id)


def test_canonicalize_pair_is_order_independent() -> None:
    entity_a, entity_b = sorted((uuid4(), uuid4()))
    assert canonicalize_pair(entity_a, entity_b) == canonicalize_pair(entity_b, entity_a)


def test_finding_identity_excludes_policy_and_evidence() -> None:
    """CDD-084 §24: identity depends only on (tenant, member_a, member_b) --
    a policy-version bump never fabricates a new semantic Finding."""
    member_a, member_b = sorted((uuid4(), uuid4()))
    first = derive_uniqueness_finding_id(
        tenant_id=TENANT, member_a_id=member_a, member_b_id=member_b
    )
    second = derive_uniqueness_finding_id(
        tenant_id=TENANT, member_a_id=member_a, member_b_id=member_b
    )
    assert first == second


def test_finding_identity_requires_canonical_order() -> None:
    member_a, member_b = sorted((uuid4(), uuid4()))
    with pytest.raises(ValidationException):
        uniqueness_finding_identity_material(
            tenant_id=TENANT, member_a_id=member_b, member_b_id=member_a
        )


def test_finding_identity_differs_by_pair() -> None:
    a1, b1 = sorted((uuid4(), uuid4()))
    a2, b2 = sorted((uuid4(), uuid4()))
    id1 = derive_uniqueness_finding_id(tenant_id=TENANT, member_a_id=a1, member_b_id=b1)
    id2 = derive_uniqueness_finding_id(tenant_id=TENANT, member_a_id=a2, member_b_id=b2)
    assert id1 != id2


def test_finding_identity_differs_by_tenant() -> None:
    member_a, member_b = sorted((uuid4(), uuid4()))
    id1 = derive_uniqueness_finding_id(
        tenant_id="tenant-a", member_a_id=member_a, member_b_id=member_b
    )
    id2 = derive_uniqueness_finding_id(
        tenant_id="tenant-b", member_a_id=member_a, member_b_id=member_b
    )
    assert id1 != id2


def test_evaluation_identity_stable_for_identical_result() -> None:
    """CDD-084 §19-§20, U10: a repeated run producing the identical logical
    result converges to the same evaluation row."""
    policy_id = uuid4()
    entity_id = uuid4()
    first = derive_uniqueness_evaluation_id(
        tenant_id=TENANT,
        policy_id=policy_id,
        policy_version=1,
        enterprise_entity_id=entity_id,
        outcome=UniquenessOutcome.SATISFIED,
        candidate_count=0,
        not_evaluable_reason=None,
    )
    second = derive_uniqueness_evaluation_id(
        tenant_id=TENANT,
        policy_id=policy_id,
        policy_version=1,
        enterprise_entity_id=entity_id,
        outcome=UniquenessOutcome.SATISFIED,
        candidate_count=0,
        not_evaluable_reason=None,
    )
    assert first == second


def test_evaluation_identity_differs_for_different_result() -> None:
    policy_id = uuid4()
    entity_id = uuid4()
    satisfied = derive_uniqueness_evaluation_id(
        tenant_id=TENANT,
        policy_id=policy_id,
        policy_version=1,
        enterprise_entity_id=entity_id,
        outcome=UniquenessOutcome.SATISFIED,
        candidate_count=0,
        not_evaluable_reason=None,
    )
    violated = derive_uniqueness_evaluation_id(
        tenant_id=TENANT,
        policy_id=policy_id,
        policy_version=1,
        enterprise_entity_id=entity_id,
        outcome=UniquenessOutcome.VIOLATED,
        candidate_count=1,
        not_evaluable_reason=None,
    )
    assert satisfied != violated


def test_uniqueness_evaluation_satisfied_requires_zero_candidates() -> None:
    from app.domain.oqi_uniqueness.evaluation import UniquenessEvaluation

    with pytest.raises(ValidationException):
        UniquenessEvaluation(
            evaluation_id=derive_uniqueness_evaluation_id(
                tenant_id=TENANT,
                policy_id=uuid4(),
                policy_version=1,
                enterprise_entity_id=uuid4(),
                outcome=UniquenessOutcome.SATISFIED,
                candidate_count=1,
                not_evaluable_reason=None,
            ),
            tenant_id=TENANT,
            policy_id=uuid4(),
            policy_version=1,
            enterprise_entity_id=uuid4(),
            outcome=UniquenessOutcome.SATISFIED,
            not_evaluable_reason=None,
            candidate_count=1,
            evaluated_on=NOW,
        )


def _new_finding(member_a: UUID, member_b: UUID, *, moment: datetime = NOW) -> UniquenessFinding:
    return UniquenessFinding(
        finding_id=derive_uniqueness_finding_id(
            tenant_id=TENANT, member_a_id=member_a, member_b_id=member_b
        ),
        tenant_id=TENANT,
        candidate_id=uuid4(),
        member_a_id=member_a,
        member_b_id=member_b,
        status=UniquenessFindingStatus.OPEN,
        state_revision=1,
        first_seen_at=moment,
        last_seen_at=moment,
        occurrence_count=1,
        reopen_count=0,
    )


class TestFindingTransitionLifecycle:
    """CDD-084 §25: the exact four-branch evaluation-driven transition."""

    def test_no_existing_no_candidate_stays_none(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        result = apply_uniqueness_finding_transition(
            existing=None,
            candidate_qualifies=False,
            candidate_id=uuid4(),
            moment=NOW,
            tenant_id=TENANT,
            member_a_id=member_a,
            member_b_id=member_b,
        )
        assert result is None

    def test_no_existing_qualifying_candidate_opens(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        candidate_id = uuid4()
        result = apply_uniqueness_finding_transition(
            existing=None,
            candidate_qualifies=True,
            candidate_id=candidate_id,
            moment=NOW,
            tenant_id=TENANT,
            member_a_id=member_a,
            member_b_id=member_b,
        )
        assert result is not None
        assert result.status is UniquenessFindingStatus.OPEN
        assert result.state_revision == 1
        assert result.occurrence_count == 1
        assert result.reopen_count == 0
        assert result.candidate_id == candidate_id

    def test_open_reaffirmed_by_continued_qualification(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        existing = _new_finding(member_a, member_b)
        result = apply_uniqueness_finding_transition(
            existing=existing,
            candidate_qualifies=True,
            candidate_id=uuid4(),
            moment=NOW,
            tenant_id=TENANT,
            member_a_id=member_a,
            member_b_id=member_b,
        )
        assert result is not None
        assert result.status is UniquenessFindingStatus.OPEN
        assert result.state_revision == 2
        assert result.occurrence_count == 1
        assert result.reopen_count == 0

    def test_open_closes_when_no_longer_qualifying(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        existing = _new_finding(member_a, member_b)
        result = apply_uniqueness_finding_transition(
            existing=existing,
            candidate_qualifies=False,
            candidate_id=existing.candidate_id,
            moment=NOW,
            tenant_id=TENANT,
            member_a_id=member_a,
            member_b_id=member_b,
        )
        assert result is not None
        assert result.status is UniquenessFindingStatus.RESOLVED
        assert result.state_revision == 2

    def test_resolved_reaffirmed_by_continued_non_qualification(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        existing = apply_uniqueness_finding_transition(
            existing=_new_finding(member_a, member_b),
            candidate_qualifies=False,
            candidate_id=uuid4(),
            moment=NOW,
            tenant_id=TENANT,
            member_a_id=member_a,
            member_b_id=member_b,
        )
        assert existing is not None
        result = apply_uniqueness_finding_transition(
            existing=existing,
            candidate_qualifies=False,
            candidate_id=existing.candidate_id,
            moment=NOW,
            tenant_id=TENANT,
            member_a_id=member_a,
            member_b_id=member_b,
        )
        assert result is not None
        assert result.status is UniquenessFindingStatus.RESOLVED
        assert result.state_revision == existing.state_revision + 1

    def test_resolved_reopens_on_fresh_qualification(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        resolved = apply_uniqueness_finding_transition(
            existing=_new_finding(member_a, member_b),
            candidate_qualifies=False,
            candidate_id=uuid4(),
            moment=NOW,
            tenant_id=TENANT,
            member_a_id=member_a,
            member_b_id=member_b,
        )
        assert resolved is not None
        new_candidate_id = uuid4()
        reopened = apply_uniqueness_finding_transition(
            existing=resolved,
            candidate_qualifies=True,
            candidate_id=new_candidate_id,
            moment=NOW,
            tenant_id=TENANT,
            member_a_id=member_a,
            member_b_id=member_b,
        )
        assert reopened is not None
        assert reopened.status is UniquenessFindingStatus.OPEN
        assert reopened.occurrence_count == 2
        assert reopened.reopen_count == 1
        assert reopened.candidate_id == new_candidate_id

    def test_mismatched_existing_identity_rejected(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        other_a, other_b = sorted((uuid4(), uuid4()))
        existing = _new_finding(member_a, member_b)
        with pytest.raises(ValidationException):
            apply_uniqueness_finding_transition(
                existing=existing,
                candidate_qualifies=True,
                candidate_id=uuid4(),
                moment=NOW,
                tenant_id=TENANT,
                member_a_id=other_a,
                member_b_id=other_b,
            )


class TestAdjudicationTransition:
    """CDD-084 §21, §25, §28: the independent adjudication-driven half of
    the Finding lifecycle."""

    def test_reject_not_duplicate_closes_open_finding(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        existing = _new_finding(member_a, member_b)
        result = apply_uniqueness_adjudication_transition(
            existing=existing, action=UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE, moment=NOW
        )
        assert result.status is UniquenessFindingStatus.RESOLVED
        assert result.state_revision == existing.state_revision + 1

    def test_confirm_duplicate_never_changes_status(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        existing = _new_finding(member_a, member_b)
        result = apply_uniqueness_adjudication_transition(
            existing=existing, action=UniquenessAdjudicationAction.CONFIRM_DUPLICATE, moment=NOW
        )
        assert result.status is UniquenessFindingStatus.OPEN
        assert result.state_revision == existing.state_revision + 1
        # No EnterpriseEntity/relationship field exists on this dataclass
        # at all -- confirmation cannot mutate what this object cannot
        # even represent (CDD-084 §28, §2 PO-2).

    def test_reject_not_duplicate_on_already_resolved_is_idempotent_in_status(self) -> None:
        member_a, member_b = sorted((uuid4(), uuid4()))
        existing = _new_finding(member_a, member_b)
        resolved = apply_uniqueness_adjudication_transition(
            existing=existing, action=UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE, moment=NOW
        )
        result = apply_uniqueness_adjudication_transition(
            existing=resolved, action=UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE, moment=NOW
        )
        assert result.status is UniquenessFindingStatus.RESOLVED
        assert result.state_revision == resolved.state_revision + 1


class TestNotEvaluableReasonInvariant:
    def test_bucket_exceeded_reason_requires_not_evaluable_outcome(self) -> None:
        from app.domain.oqi_uniqueness.evaluation import UniquenessEvaluation

        with pytest.raises(ValidationException):
            UniquenessEvaluation(
                evaluation_id=uuid4(),
                tenant_id=TENANT,
                policy_id=uuid4(),
                policy_version=1,
                enterprise_entity_id=uuid4(),
                outcome=UniquenessOutcome.SATISFIED,
                not_evaluable_reason=UniquenessNotEvaluableReason.BUCKET_EXCEEDED_CAP,
                candidate_count=0,
                evaluated_on=NOW,
            )

    def test_not_evaluable_outcome_requires_reason(self) -> None:
        from app.domain.oqi_uniqueness.evaluation import UniquenessEvaluation

        with pytest.raises(ValidationException):
            UniquenessEvaluation(
                evaluation_id=uuid4(),
                tenant_id=TENANT,
                policy_id=uuid4(),
                policy_version=1,
                enterprise_entity_id=uuid4(),
                outcome=UniquenessOutcome.NOT_EVALUABLE,
                not_evaluable_reason=None,
                candidate_count=0,
                evaluated_on=NOW,
            )
