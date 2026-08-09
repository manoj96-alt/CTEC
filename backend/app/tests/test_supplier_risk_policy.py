from uuid import uuid4

from app.integration.contracts import (
    GovernanceStanding,
    RiskSeverity,
    SourcingRecommendation,
    SourcingStatus,
    SupplierEligibility,
)
from app.integration.supplier_risk_policy import SupplierRiskPolicy


def supplier(*, ready: bool = True) -> SupplierEligibility:
    return SupplierEligibility(uuid4(), True, True, True, True, ready)


def test_sourcing_status_and_recommendation_matrix() -> None:
    policy = SupplierRiskPolicy()
    one, two = (supplier(),), (supplier(), supplier())
    assert policy.sourcing_status((), evidence_complete=True) is SourcingStatus.NO_QUALIFIED_SOURCE
    assert policy.sourcing_status(one, evidence_complete=True) is SourcingStatus.SINGLE_SOURCE
    assert policy.sourcing_status(two, evidence_complete=True) is SourcingStatus.DUAL_SOURCE
    assert policy.sourcing_status(one, evidence_complete=False) is SourcingStatus.INDETERMINATE
    assert (
        policy.recommend(RiskSeverity.LOW, SourcingStatus.DUAL_SOURCE, two, exceptional=False)
        is SourcingRecommendation.CONTINUE_MONITORING
    )
    assert (
        policy.recommend(
            RiskSeverity.MATERIAL, SourcingStatus.SINGLE_SOURCE, one, exceptional=False
        )
        is SourcingRecommendation.QUALIFY_SECOND_SOURCE
    )
    assert (
        policy.recommend(RiskSeverity.HIGH, SourcingStatus.DUAL_SOURCE, two, exceptional=False)
        is SourcingRecommendation.ACTIVATE_APPROVED_SECOND_SOURCE
    )
    assert (
        policy.recommend(RiskSeverity.HIGH, SourcingStatus.INDETERMINATE, one, exceptional=False)
        is SourcingRecommendation.ESCALATE_FOR_HUMAN_REVIEW
    )


def test_conditional_standing_is_actionable_only_after_all_conditions() -> None:
    policy = SupplierRiskPolicy()
    standing, verified = policy.standing(
        compliant=True, requires_review=False, conditions=("A", "B"), verified=("A",)
    )
    assert standing is GovernanceStanding.CONDITIONALLY_APPROVED and not verified
    standing, verified = policy.standing(
        compliant=True, requires_review=False, conditions=("A", "B"), verified=("A", "B")
    )
    assert standing is GovernanceStanding.CONDITIONALLY_APPROVED and verified
