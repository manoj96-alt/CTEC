"""Gate O -- Governed Blueprint Information-Element Context-as-a-Service
application service (CDD-029; Gate O Artifact Authorization v1.0). Resolves
exactly one Blueprint `InformationElementRequirement`, identified by
Blueprint name and Information Element name, by orchestrating -- by call
only, in this fixed order -- the existing, unmodified
`BlueprintApplicationService`, Gate I
`SemanticCoverageEvaluationApplicationService`, H4
`InformationElementEvidenceAvailabilityApplicationService`, and Gate N
`InformationElementContextAvailabilityApplicationService`. Performs zero
persistence writes and never recomputes, overrides, defaults, or
reinterprets any of those authorities' outputs (CDD-029 §7). Gate P's own
`ontology_copilot_api.py` orchestration is useful precedent for this shape
but is never imported or depended upon (Gate O Artifact Authorization v1.0
§5) -- Gate P itself is never modified."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.blueprint_service import BlueprintApplicationService
from app.application.information_element_context_availability import (
    InformationElementContextAvailabilityApplicationService,
)
from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import SemanticMappingResolutionApplicationService
from app.domain.blueprint import Obligation
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl


class InformationElementContextResolutionStatus(StrEnum):
    """Gate O's own transport/application outcome taxonomy (CDD-029 §15) --
    distinct from Gate P's `GatePAskStatus`, never reused. `RESOLVED` is the
    only outcome ever rendered as a successful (HTTP 200) response; the
    other four are used exclusively as non-200 `detail.code` values by the
    router -- never as a field on a successful response body."""

    RESOLVED = "RESOLVED"
    BLUEPRINT_NOT_FOUND = "BLUEPRINT_NOT_FOUND"
    INFORMATION_ELEMENT_NOT_FOUND = "INFORMATION_ELEMENT_NOT_FOUND"
    INFORMATION_ELEMENT_NAME_AMBIGUOUS = "INFORMATION_ELEMENT_NAME_AMBIGUOUS"
    UPSTREAM_INTEGRITY_FAILURE = "UPSTREAM_INTEGRITY_FAILURE"


@dataclass(frozen=True, slots=True)
class InformationElementContextResolutionResult:
    """Internal typed result -- an implementation detail, not itself frozen
    architecture (Gate O Artifact Authorization v1.0 §5). Every field other
    than `status` is `None` unless `status` is `RESOLVED`."""

    status: InformationElementContextResolutionStatus
    blueprint_id: UUID | None
    blueprint_version_number: int | None
    information_element_requirement_id: UUID | None
    information_element_name: str | None
    obligation: Obligation | None
    coverage_status: CoverageStatus | None
    evidence_availability_status: EvidenceAvailabilityStatus | None


class InformationElementContextResolutionApplicationService:
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
    ) -> InformationElementContextResolutionResult:
        try:
            blueprint = self._blueprint_service.get_approved_by_name(blueprint_name)
        except ValidationException:
            # More than one Approved Blueprint sharing this name is a governed-data
            # integrity violation (BlueprintRepositoryImpl's own contract), never an
            # ordinary "not found" outcome (CDD-029 §15).
            return self._failure(
                InformationElementContextResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
            )
        if blueprint is None:
            return self._failure(InformationElementContextResolutionStatus.BLUEPRINT_NOT_FOUND)

        matches = [
            element
            for concept in blueprint.concept_requirements
            for element in concept.information_element_requirements
            if element.element_name.value == information_element_name
        ]
        if len(matches) == 0:
            return self._failure(
                InformationElementContextResolutionStatus.INFORMATION_ELEMENT_NOT_FOUND
            )
        if len(matches) > 1:
            # Blueprint's own domain model does not guarantee element-name uniqueness
            # across concept_requirements -- this is a client-resolvable-in-principle
            # under-specified request, not a governed-data integrity violation
            # (CDD-029 §15's own explicit integrity/ambiguity correction).
            return self._failure(
                InformationElementContextResolutionStatus.INFORMATION_ELEMENT_NAME_AMBIGUOUS
            )

        requirement = matches[0]

        try:
            coverage_result = SemanticCoverageEvaluationApplicationService(
                blueprint_service=self._blueprint_service,
                resolver=SemanticMappingResolutionApplicationService(
                    repository=SemanticMappingRepositoryImpl(self._session)
                ),
            ).evaluate(blueprint_name=blueprint_name, tenant_id=principal.tenant_id)
            evidence_availability_results = (
                InformationElementEvidenceAvailabilityApplicationService(
                    evidence_provider=FieldValueEvidenceRepositoryImpl(self._session)
                ).evaluate(coverage_result=coverage_result)
            )
            composed = InformationElementContextAvailabilityApplicationService().compose(
                coverage_result=coverage_result,
                evidence_availability_results=evidence_availability_results,
            )
        except ValidationException:
            return self._failure(
                InformationElementContextResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
            )

        matched = next(
            (
                c
                for c in composed
                if c.information_element_requirement_id
                == requirement.information_element_requirement_id.value
            ),
            None,
        )
        if matched is None:
            # Structural invariant, not an expected runtime path: Gate I's own
            # coverage_result always includes every InformationElementRequirement of
            # the resolved Blueprint, and Gate N returns exactly one composed result
            # per element it is supplied. Handled identically for defense in depth,
            # never as a silently fabricated answer.
            return self._failure(
                InformationElementContextResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
            )

        return InformationElementContextResolutionResult(
            status=InformationElementContextResolutionStatus.RESOLVED,
            blueprint_id=blueprint.blueprint_id.value,
            blueprint_version_number=blueprint.version_number,
            information_element_requirement_id=matched.information_element_requirement_id,
            information_element_name=requirement.element_name.value,
            obligation=matched.obligation,
            coverage_status=matched.coverage_status,
            evidence_availability_status=matched.evidence_availability_status,
        )

    @staticmethod
    def _failure(
        status: InformationElementContextResolutionStatus,
    ) -> InformationElementContextResolutionResult:
        return InformationElementContextResolutionResult(
            status=status,
            blueprint_id=None,
            blueprint_version_number=None,
            information_element_requirement_id=None,
            information_element_name=None,
            obligation=None,
            coverage_status=None,
            evidence_availability_status=None,
        )
