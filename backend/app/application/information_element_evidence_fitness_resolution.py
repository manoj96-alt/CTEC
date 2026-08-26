"""Governed Evidence Fitness Exposure application service (CDD-034;
CDD-031 Evidence Fitness Exposure Clarification and Remediation Report;
CDD-034 Artifact Authorization v1.0). Resolves exactly one Blueprint
`InformationElementRequirement`, identified by Blueprint name and
Information Element name, by orchestrating -- by call only, in this fixed
order -- the existing, unmodified `BlueprintApplicationService`, Gate I
`SemanticCoverageEvaluationApplicationService`, H4
`InformationElementEvidenceAvailabilityApplicationService`, and Gate T
`SourceEvidenceFitnessEvaluationApplicationService`. Performs zero
persistence writes and never reinterprets any of those authorities'
outputs (CDD-034 §14). Gate O's own `information_element_context_resolution
.py` orchestration is the direct precedent for this shape but is never
imported or depended upon (CDD-034 §14) -- Gate O itself is never modified.

For `UNMAPPED` Information Element Requirements, H4's own `evaluate()`
filters to `CoverageStatus.MAPPED` elements only, so no result entry could
ever exist for an `UNMAPPED` requirement -- this service therefore
short-circuits before H4 or Gate T are even constructed (CDD-034 §13
step 7)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.blueprint_service import BlueprintApplicationService
from app.application.information_element_evidence_availability import (
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import SemanticMappingResolutionApplicationService
from app.application.source_evidence_fitness_evaluation import (
    EvidenceFitnessStatus,
    SourceEvidenceFitnessEvaluationApplicationService,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl


class InformationElementEvidenceFitnessResolutionStatus(StrEnum):
    """This service's own transport/application outcome taxonomy (CDD-034
    §18) -- distinct from Gate O's `InformationElementContextResolutionStatus`,
    never reused. `RESOLVED` is the only outcome ever rendered as a
    successful (HTTP 200) response -- it covers all three legitimate
    null-adjacent states (CDD-034 §11) in addition to a real fitness
    classification; the other four are used exclusively as non-200
    `detail.code` values by the router."""

    RESOLVED = "RESOLVED"
    BLUEPRINT_NOT_FOUND = "BLUEPRINT_NOT_FOUND"
    INFORMATION_ELEMENT_NOT_FOUND = "INFORMATION_ELEMENT_NOT_FOUND"
    INFORMATION_ELEMENT_NAME_AMBIGUOUS = "INFORMATION_ELEMENT_NAME_AMBIGUOUS"
    UPSTREAM_INTEGRITY_FAILURE = "UPSTREAM_INTEGRITY_FAILURE"


@dataclass(frozen=True, slots=True)
class InformationElementEvidenceFitnessResolutionResult:
    """Internal typed result -- an implementation detail, not itself frozen
    architecture. Every field other than `status` is `None` unless `status`
    is `RESOLVED`; `information_element_requirement_id` and `evaluated_at`
    are always populated when `RESOLVED`, while `source_field_id` and
    `fitness_status` follow CDD-034 §11's three-state null-adjacency
    table."""

    status: InformationElementEvidenceFitnessResolutionStatus
    information_element_requirement_id: UUID | None
    source_field_id: UUID | None
    fitness_status: EvidenceFitnessStatus | None
    evaluated_at: datetime | None


class InformationElementEvidenceFitnessResolutionApplicationService:
    def __init__(self, *, session: Session) -> None:
        self._session = session
        self._blueprint_service = BlueprintApplicationService(
            repository=BlueprintRepositoryImpl(session)
        )

    def resolve(
        self,
        *,
        principal: TrustedPrincipal,
        blueprint_name: str,
        information_element_name: str,
    ) -> InformationElementEvidenceFitnessResolutionResult:
        evaluated_at = datetime.now(UTC)

        try:
            blueprint = self._blueprint_service.get_approved_by_name(blueprint_name)
        except ValidationException:
            # More than one Approved Blueprint sharing this name is a governed-data
            # integrity violation (BlueprintRepositoryImpl's own contract), never an
            # ordinary "not found" outcome -- mirrors Gate O's identical handling.
            return self._failure(
                InformationElementEvidenceFitnessResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
            )
        if blueprint is None:
            return self._failure(
                InformationElementEvidenceFitnessResolutionStatus.BLUEPRINT_NOT_FOUND
            )

        matches = [
            element
            for concept in blueprint.concept_requirements
            for element in concept.information_element_requirements
            if element.element_name.value == information_element_name
        ]
        if len(matches) == 0:
            return self._failure(
                InformationElementEvidenceFitnessResolutionStatus.INFORMATION_ELEMENT_NOT_FOUND
            )
        if len(matches) > 1:
            # Gate O's own identical, independently reimplemented mechanical
            # matching (CDD-034 §14's accepted composition-duplication trade-off,
            # not a semantic duplication) -- Gate O is never imported or modified.
            return self._failure(
                InformationElementEvidenceFitnessResolutionStatus.INFORMATION_ELEMENT_NAME_AMBIGUOUS
            )

        requirement = matches[0]
        requirement_id = requirement.information_element_requirement_id.value

        try:
            coverage_result = SemanticCoverageEvaluationApplicationService(
                blueprint_service=self._blueprint_service,
                resolver=SemanticMappingResolutionApplicationService(
                    repository=SemanticMappingRepositoryImpl(self._session)
                ),
            ).evaluate(blueprint_name=blueprint_name, tenant_id=principal.tenant_id)
        except ValidationException:
            return self._failure(
                InformationElementEvidenceFitnessResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
            )

        matched = next(
            (
                element
                for element in coverage_result.information_element_results
                if element.information_element_requirement_id == requirement_id
            ),
            None,
        )
        if matched is None:
            # Structural invariant, not an expected runtime path: Gate I's own
            # coverage_result always includes every InformationElementRequirement
            # of the resolved Blueprint (defense in depth, mirroring Gate O).
            return self._failure(
                InformationElementEvidenceFitnessResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
            )

        if matched.status is CoverageStatus.UNMAPPED:
            # CDD-034 §13 step 7 -- binding short-circuit. H4 and Gate T are never
            # constructed on this path.
            return InformationElementEvidenceFitnessResolutionResult(
                status=InformationElementEvidenceFitnessResolutionStatus.RESOLVED,
                information_element_requirement_id=requirement_id,
                source_field_id=None,
                fitness_status=None,
                evaluated_at=evaluated_at,
            )

        h4_results = InformationElementEvidenceAvailabilityApplicationService(
            evidence_provider=FieldValueEvidenceRepositoryImpl(self._session)
        ).evaluate(coverage_result=coverage_result)
        h4_match = next(
            (
                result
                for result in h4_results
                if result.information_element_requirement_id == requirement_id
            ),
            None,
        )
        if h4_match is None:
            # Structural invariant, not an expected runtime path: `matched.status`
            # is MAPPED, so H4's own filtering guarantees exactly one entry here.
            return self._failure(
                InformationElementEvidenceFitnessResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
            )

        fitness_results = SourceEvidenceFitnessEvaluationApplicationService(
            evidence_provider=FieldValueEvidenceRepositoryImpl(self._session)
        ).evaluate(
            evidence_availability_results=(h4_match,),
            tenant_id=principal.tenant_id,
            as_of=evaluated_at,
        )

        return InformationElementEvidenceFitnessResolutionResult(
            status=InformationElementEvidenceFitnessResolutionStatus.RESOLVED,
            information_element_requirement_id=requirement_id,
            source_field_id=h4_match.source_field_id,
            fitness_status=fitness_results[0].fitness_status,
            evaluated_at=evaluated_at,
        )

    @staticmethod
    def _failure(
        status: InformationElementEvidenceFitnessResolutionStatus,
    ) -> InformationElementEvidenceFitnessResolutionResult:
        return InformationElementEvidenceFitnessResolutionResult(
            status=status,
            information_element_requirement_id=None,
            source_field_id=None,
            fitness_status=None,
            evaluated_at=None,
        )
