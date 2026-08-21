"""Internal Gate N -- Blueprint Information-Element Context Availability
Composition application service (CDD-024 §8-§15; Context Availability
Composition Artifact Authorization). For every `InformationElementCoverageResult`
already produced by Gate I, composes it with its corresponding
`InformationElementEvidenceAvailabilityResult` already produced by H4 (when
one exists), returning the frozen four-field
`InformationElementContextAvailabilityResult` contract -- a lossless
passthrough of `CoverageStatus` and `EvidenceAvailabilityStatus`, never a
new synthesized state and never a trust, confidence, freshness, or
readiness judgment. Performs zero I/O of any kind: both inputs are
already-produced, already-in-memory results supplied by the caller. Does
not call Gate I, H2, or H4, and does not consume Gate J's output."""

from dataclasses import dataclass
from uuid import UUID

from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityResult,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    InformationElementCoverageResult,
    SemanticCoverageEvaluationResult,
)
from app.domain.blueprint import Obligation
from app.domain.shared.exceptions import ValidationException


@dataclass(frozen=True, slots=True)
class InformationElementContextAvailabilityResult:
    information_element_requirement_id: UUID
    obligation: Obligation
    coverage_status: CoverageStatus
    evidence_availability_status: EvidenceAvailabilityStatus | None


class InformationElementContextAvailabilityApplicationService:
    def compose(
        self,
        *,
        coverage_result: SemanticCoverageEvaluationResult,
        evidence_availability_results: tuple[InformationElementEvidenceAvailabilityResult, ...],
    ) -> tuple[InformationElementContextAvailabilityResult, ...]:
        h4_by_id = self._h4_lookup(evidence_availability_results)
        self._reject_orphans(h4_by_id, coverage_result)

        results = [
            self._compose_one(element, h4_by_id)
            for element in coverage_result.information_element_results
        ]
        return self._sorted(results)

    @staticmethod
    def _h4_lookup(
        evidence_availability_results: tuple[InformationElementEvidenceAvailabilityResult, ...],
    ) -> dict[UUID, InformationElementEvidenceAvailabilityResult]:
        h4_by_id: dict[UUID, InformationElementEvidenceAvailabilityResult] = {}
        for h4_result in evidence_availability_results:
            if h4_result.information_element_requirement_id in h4_by_id:
                raise ValidationException(
                    "Context availability composition integrity violation: more than "
                    "one H4 result supplied for one InformationElementRequirement "
                    f"({h4_result.information_element_requirement_id})"
                )
            h4_by_id[h4_result.information_element_requirement_id] = h4_result
        return h4_by_id

    @staticmethod
    def _reject_orphans(
        h4_by_id: dict[UUID, InformationElementEvidenceAvailabilityResult],
        coverage_result: SemanticCoverageEvaluationResult,
    ) -> None:
        coverage_ids = {
            element.information_element_requirement_id
            for element in coverage_result.information_element_results
        }
        for requirement_id in h4_by_id:
            if requirement_id not in coverage_ids:
                raise ValidationException(
                    "Context availability composition integrity violation: H4 result "
                    f"references InformationElementRequirement {requirement_id}, which "
                    "is not present in the supplied coverage_result"
                )

    @staticmethod
    def _compose_one(
        element: InformationElementCoverageResult,
        h4_by_id: dict[UUID, InformationElementEvidenceAvailabilityResult],
    ) -> InformationElementContextAvailabilityResult:
        h4_result = h4_by_id.get(element.information_element_requirement_id)

        if element.status is CoverageStatus.MAPPED:
            if h4_result is None:
                raise ValidationException(
                    "Context availability composition integrity violation: MAPPED "
                    f"InformationElementRequirement {element.information_element_requirement_id} "
                    "has no corresponding H4 result"
                )
            assert element.resolution is not None
            if h4_result.source_field_id != element.resolution.source_field_id:
                raise ValidationException(
                    "Context availability composition integrity violation: H4 result "
                    "provenance disagrees with Gate I resolution for "
                    f"InformationElementRequirement {element.information_element_requirement_id}"
                )
            evidence_availability_status = h4_result.evidence_availability_status
        else:
            if h4_result is not None:
                raise ValidationException(
                    "Context availability composition integrity violation: UNMAPPED "
                    f"InformationElementRequirement {element.information_element_requirement_id} "
                    "has an H4 result present"
                )
            evidence_availability_status = None

        return InformationElementContextAvailabilityResult(
            information_element_requirement_id=element.information_element_requirement_id,
            obligation=element.obligation,
            coverage_status=element.status,
            evidence_availability_status=evidence_availability_status,
        )

    @staticmethod
    def _sorted(
        results: list[InformationElementContextAvailabilityResult],
    ) -> tuple[InformationElementContextAvailabilityResult, ...]:
        return tuple(sorted(results, key=lambda result: result.information_element_requirement_id))
