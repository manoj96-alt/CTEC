"""Internal Gate K -- Blueprint Information-Element Decision-Prerequisite
Assessment application service (CDD-026 §7-§14; Decision-Prerequisite
Assessment Artifact Authorization §6-§12). For one already-produced Gate N
`InformationElementContextAvailabilityResult`, deterministically classifies
the governed prerequisites as `PREREQUISITES_PRESENT`,
`PREREQUISITES_INCOMPLETE`, or `NOT_EVALUABLE` -- never a READY/NOT_READY
verdict, never a Blueprint-level aggregation, and never a Decision Readiness
judgment. Performs zero I/O of any kind: its sole input is an
already-produced, already-in-memory Gate N result supplied by the caller.
Does not call Gate I, H4, or Gate N, and does not consume Gate J's or Gate
P's output. `obligation` is carried through as passthrough labeling only --
classification is invariant across `REQUIRED`, `CONDITIONAL`, and
`OPTIONAL`."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.application.information_element_context_availability import (
    InformationElementContextAvailabilityResult,
)
from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
)
from app.application.semantic_coverage_evaluation import CoverageStatus
from app.domain.blueprint import Obligation
from app.domain.shared.exceptions import ValidationException


class PrerequisiteStatus(StrEnum):
    PREREQUISITES_PRESENT = "PREREQUISITES_PRESENT"
    PREREQUISITES_INCOMPLETE = "PREREQUISITES_INCOMPLETE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class PrerequisiteReasonCode(StrEnum):
    NO_APPROVED_MAPPING = "NO_APPROVED_MAPPING"
    APPROVED_MAPPING_WITH_NO_EVIDENCE_OBSERVED = "APPROVED_MAPPING_WITH_NO_EVIDENCE_OBSERVED"
    APPROVED_MAPPING_WITH_EMPTY_EVIDENCE = "APPROVED_MAPPING_WITH_EMPTY_EVIDENCE"
    APPROVED_MAPPING_WITH_EVIDENCE_OBSERVED = "APPROVED_MAPPING_WITH_EVIDENCE_OBSERVED"


@dataclass(frozen=True, slots=True)
class InformationElementDecisionPrerequisiteAssessmentResult:
    information_element_requirement_id: UUID
    obligation: Obligation
    coverage_status: CoverageStatus
    evidence_availability_status: EvidenceAvailabilityStatus | None
    prerequisite_status: PrerequisiteStatus
    reason_code: PrerequisiteReasonCode


class InformationElementDecisionPrerequisiteAssessmentApplicationService:
    def assess(
        self, *, context: InformationElementContextAvailabilityResult
    ) -> InformationElementDecisionPrerequisiteAssessmentResult:
        if context.coverage_status is CoverageStatus.UNMAPPED:
            prerequisite_status, reason_code = self._assess_unmapped(context)
        else:
            prerequisite_status, reason_code = self._assess_mapped(context)

        return InformationElementDecisionPrerequisiteAssessmentResult(
            information_element_requirement_id=context.information_element_requirement_id,
            obligation=context.obligation,
            coverage_status=context.coverage_status,
            evidence_availability_status=context.evidence_availability_status,
            prerequisite_status=prerequisite_status,
            reason_code=reason_code,
        )

    @staticmethod
    def _assess_unmapped(
        context: InformationElementContextAvailabilityResult,
    ) -> tuple[PrerequisiteStatus, PrerequisiteReasonCode]:
        if context.evidence_availability_status is not None:
            raise ValidationException(
                "Decision-prerequisite assessment integrity violation: UNMAPPED "
                f"InformationElementRequirement {context.information_element_requirement_id} "
                "has a non-None evidence_availability_status"
            )
        return PrerequisiteStatus.NOT_EVALUABLE, PrerequisiteReasonCode.NO_APPROVED_MAPPING

    @staticmethod
    def _assess_mapped(
        context: InformationElementContextAvailabilityResult,
    ) -> tuple[PrerequisiteStatus, PrerequisiteReasonCode]:
        if context.evidence_availability_status is None:
            raise ValidationException(
                "Decision-prerequisite assessment integrity violation: MAPPED "
                f"InformationElementRequirement {context.information_element_requirement_id} "
                "has no evidence_availability_status"
            )
        if context.evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_PRESENT:
            return (
                PrerequisiteStatus.PREREQUISITES_PRESENT,
                PrerequisiteReasonCode.APPROVED_MAPPING_WITH_EVIDENCE_OBSERVED,
            )
        if context.evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_EMPTY:
            return (
                PrerequisiteStatus.PREREQUISITES_INCOMPLETE,
                PrerequisiteReasonCode.APPROVED_MAPPING_WITH_EMPTY_EVIDENCE,
            )
        return (
            PrerequisiteStatus.PREREQUISITES_INCOMPLETE,
            PrerequisiteReasonCode.APPROVED_MAPPING_WITH_NO_EVIDENCE_OBSERVED,
        )
