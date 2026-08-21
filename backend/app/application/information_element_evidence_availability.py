"""Internal H4 -- Blueprint Information-Element Evidence Availability
Evaluation application service (CDD-023 §8-§17; H4 Evidence Availability
Artifact Authorization). For each `InformationElementCoverageResult` in an
already-produced Gate I `SemanticCoverageEvaluationResult` classified
`MAPPED`, retrieves the resolved `SourceField`'s persisted
`FieldValueEvidence` set (CDD-022, unmodified) and classifies
`NO_EVIDENCE` / `EVIDENCE_EMPTY` / `EVIDENCE_PRESENT`. Performs no I/O for
mapping resolution (Gate I's result is supplied by the caller); performs
real I/O for evidence retrieval only, via the narrow `EvidenceProvider`
Protocol. Does not call H2, does not query `SemanticMapping`, and never
reinterprets raw evidence as semantically correct -- this is FACT
availability classification only, never semantic satisfaction."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    InformationElementCoverageResult,
    SemanticCoverageEvaluationResult,
)
from app.domain.blueprint import Obligation
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingResolution


class EvidenceProvider(Protocol):
    """Structural contract satisfied by `FieldValueEvidenceRepositoryImpl`
    (unmodified) -- the sole evidence-retrieval path this service depends
    on. Narrowed to exactly `get_by_source_field`; `get_by_id` and
    `create_or_get_existing` are deliberately excluded, since this service
    has no legitimate use for either."""

    def get_by_source_field(
        self, *, tenant_id: str, source_field_id: UUID
    ) -> tuple[FieldValueEvidence, ...]: ...


class EvidenceAvailabilityStatus(StrEnum):
    NO_EVIDENCE = "NO_EVIDENCE"
    EVIDENCE_EMPTY = "EVIDENCE_EMPTY"
    EVIDENCE_PRESENT = "EVIDENCE_PRESENT"


@dataclass(frozen=True, slots=True)
class InformationElementEvidenceAvailabilityResult:
    information_element_requirement_id: UUID
    obligation: Obligation
    semantic_mapping_resolution: SemanticMappingResolution
    source_field_id: UUID
    evidence_availability_status: EvidenceAvailabilityStatus
    field_value_evidence_ids: tuple[UUID, ...]
    evaluated_at: datetime


class InformationElementEvidenceAvailabilityApplicationService:
    def __init__(self, *, evidence_provider: EvidenceProvider) -> None:
        self.evidence_provider = evidence_provider

    def evaluate(
        self, *, coverage_result: SemanticCoverageEvaluationResult
    ) -> tuple[InformationElementEvidenceAvailabilityResult, ...]:
        invocation_evaluated_at = datetime.now(UTC)

        results = [
            self._evaluate_one(element, coverage_result.tenant_id, invocation_evaluated_at)
            for element in coverage_result.information_element_results
            if element.status is CoverageStatus.MAPPED
        ]
        return self._sorted(results)

    def _evaluate_one(
        self,
        element: InformationElementCoverageResult,
        tenant_id: str,
        evaluated_at: datetime,
    ) -> InformationElementEvidenceAvailabilityResult:
        assert element.resolution is not None
        resolution = element.resolution
        source_field_id = resolution.source_field_id

        evidence_rows = self.evidence_provider.get_by_source_field(
            tenant_id=tenant_id, source_field_id=source_field_id
        )

        field_value_evidence_ids = self._provenance_ids(evidence_rows)
        status = self._classify(evidence_rows)

        return InformationElementEvidenceAvailabilityResult(
            information_element_requirement_id=element.information_element_requirement_id,
            obligation=element.obligation,
            semantic_mapping_resolution=resolution,
            source_field_id=source_field_id,
            evidence_availability_status=status,
            field_value_evidence_ids=field_value_evidence_ids,
            evaluated_at=evaluated_at,
        )

    @staticmethod
    def _classify(evidence_rows: tuple[FieldValueEvidence, ...]) -> EvidenceAvailabilityStatus:
        if len(evidence_rows) == 0:
            return EvidenceAvailabilityStatus.NO_EVIDENCE
        if all(row.observed_representation == "" for row in evidence_rows):
            return EvidenceAvailabilityStatus.EVIDENCE_EMPTY
        return EvidenceAvailabilityStatus.EVIDENCE_PRESENT

    @staticmethod
    def _provenance_ids(evidence_rows: tuple[FieldValueEvidence, ...]) -> tuple[UUID, ...]:
        ids = [row.field_value_evidence_id.value for row in evidence_rows]
        if len(ids) != len(set(ids)):
            raise ValidationException(
                "Field Value Evidence provenance integrity violation: duplicate "
                "field_value_evidence_id values retrieved for one SourceField"
            )
        return tuple(sorted(ids, key=str))

    @staticmethod
    def _sorted(
        results: list[InformationElementEvidenceAvailabilityResult],
    ) -> tuple[InformationElementEvidenceAvailabilityResult, ...]:
        return tuple(sorted(results, key=lambda result: result.information_element_requirement_id))
