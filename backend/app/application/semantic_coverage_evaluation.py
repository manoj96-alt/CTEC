"""Internal Semantic Coverage Evaluation application service (Gate I I1;
CDD-020 §7-§13; I1 Semantic Coverage Evaluation Artifact Authorization).
For a given tenant and the Approved canonical Blueprint, determines, for
every `InformationElementRequirement`, whether the existing H2
`SemanticMappingResolutionApplicationService.resolve_approved_source_field(...)`
resolves an Approved `SemanticMapping` to governed `SourceField` evidence --
classifying each requirement `MAPPED` or `UNMAPPED` while preserving its
`obligation` unchanged. Performs no persistence of its own: delegates
Blueprint resolution and mapping resolution entirely to the unmodified G3/H2
capabilities, matching `BlueprintConformanceApplicationService`'s
constructor-injection, two-`Protocol`-dependency shape. Does not touch
CDD-018's `NOT_EVALUATED` status or `RequirementStatus` in any way."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.domain.blueprint import Blueprint, Obligation
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingResolution,
)


class BlueprintLookup(Protocol):
    """Structural contract satisfied by `BlueprintApplicationService`
    (unmodified) -- the only method this service depends on."""

    def get_approved_by_name(self, blueprint_name: str) -> Blueprint | None: ...


class MappingResolver(Protocol):
    """Structural contract satisfied by
    `SemanticMappingResolutionApplicationService` (unmodified) -- the sole
    mapping-resolution path this service depends on."""

    def resolve_approved_source_field(
        self, information_element_requirement_id: UUID, tenant_id: str
    ) -> SemanticMappingResolution | None: ...


class CoverageStatus(StrEnum):
    MAPPED = "MAPPED"
    UNMAPPED = "UNMAPPED"


@dataclass(frozen=True, slots=True)
class InformationElementCoverageResult:
    information_element_requirement_id: UUID
    obligation: Obligation
    status: CoverageStatus
    resolution: SemanticMappingResolution | None


@dataclass(frozen=True, slots=True)
class SemanticCoverageEvaluationResult:
    blueprint_id: UUID
    blueprint_version_number: int
    tenant_id: str
    evaluated_at: datetime
    information_element_results: tuple[InformationElementCoverageResult, ...]


class SemanticCoverageEvaluationApplicationService:
    def __init__(
        self,
        *,
        blueprint_service: BlueprintLookup,
        resolver: MappingResolver,
    ) -> None:
        self.blueprint_service = blueprint_service
        self.resolver = resolver

    def evaluate(self, *, blueprint_name: str, tenant_id: str) -> SemanticCoverageEvaluationResult:
        blueprint = self.blueprint_service.get_approved_by_name(blueprint_name)
        if blueprint is None:
            raise ValidationException(f"No Approved Blueprint found for name: {blueprint_name}")

        results: list[InformationElementCoverageResult] = []
        for concept in blueprint.concept_requirements:
            for element in concept.information_element_requirements:
                resolution = self.resolver.resolve_approved_source_field(
                    element.information_element_requirement_id.value, tenant_id
                )
                status = (
                    CoverageStatus.MAPPED if resolution is not None else CoverageStatus.UNMAPPED
                )
                results.append(
                    InformationElementCoverageResult(
                        information_element_requirement_id=element.information_element_requirement_id.value,
                        obligation=element.obligation,
                        status=status,
                        resolution=resolution,
                    )
                )

        return SemanticCoverageEvaluationResult(
            blueprint_id=blueprint.blueprint_id.value,
            blueprint_version_number=blueprint.version_number,
            tenant_id=tenant_id,
            evaluated_at=datetime.now(UTC),
            information_element_results=self._sorted(results),
        )

    @staticmethod
    def _sorted(
        results: list[InformationElementCoverageResult],
    ) -> tuple[InformationElementCoverageResult, ...]:
        return tuple(sorted(results, key=lambda result: result.information_element_requirement_id))
