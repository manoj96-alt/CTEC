from dataclasses import dataclass

from app.integration.contracts import (
    GovernanceStanding,
    RiskSeverity,
    SourcingRecommendation,
    SourcingStatus,
    SupplierEligibility,
)


@dataclass(frozen=True, slots=True)
class SupplierRiskPolicy:
    def sourcing_status(
        self, suppliers: tuple[SupplierEligibility, ...], *, evidence_complete: bool
    ) -> SourcingStatus:
        if not evidence_complete:
            return SourcingStatus.INDETERMINATE
        count = sum(item.eligible for item in suppliers)
        if count == 0:
            return SourcingStatus.NO_QUALIFIED_SOURCE
        if count == 1:
            return SourcingStatus.SINGLE_SOURCE
        return SourcingStatus.DUAL_SOURCE

    def recommend(
        self,
        severity: RiskSeverity,
        sourcing: SourcingStatus,
        suppliers: tuple[SupplierEligibility, ...],
        *,
        exceptional: bool,
    ) -> SourcingRecommendation:
        if exceptional or sourcing is SourcingStatus.INDETERMINATE:
            return SourcingRecommendation.ESCALATE_FOR_HUMAN_REVIEW
        if severity is RiskSeverity.LOW and sourcing in {
            SourcingStatus.SINGLE_SOURCE,
            SourcingStatus.DUAL_SOURCE,
        }:
            return SourcingRecommendation.CONTINUE_MONITORING
        if severity is RiskSeverity.MATERIAL and sourcing is SourcingStatus.SINGLE_SOURCE:
            return SourcingRecommendation.QUALIFY_SECOND_SOURCE
        if severity in {RiskSeverity.HIGH, RiskSeverity.CRITICAL} and any(
            supplier.eligible and supplier.operationally_ready for supplier in suppliers
        ):
            return SourcingRecommendation.ACTIVATE_APPROVED_SECOND_SOURCE
        return SourcingRecommendation.ESCALATE_FOR_HUMAN_REVIEW

    def standing(
        self,
        *,
        compliant: bool,
        requires_review: bool,
        conditions: tuple[str, ...],
        verified: tuple[str, ...],
    ) -> tuple[GovernanceStanding, bool]:
        if requires_review:
            return GovernanceStanding.PENDING_REVIEW, False
        if not compliant:
            return GovernanceStanding.REJECTED, False
        if conditions:
            satisfied = set(conditions) <= set(verified)
            return GovernanceStanding.CONDITIONALLY_APPROVED, satisfied
        return GovernanceStanding.APPROVED, True
