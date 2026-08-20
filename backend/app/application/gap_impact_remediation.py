"""Internal Blueprint Semantic Gap Impact Context and Remediation
Recommendation application service (Gate J J1/J2; CDD-021 §6-§24; J1/J2 Gap
Impact Context and Remediation Artifact Authorization). For each
`InformationElementCoverageResult` in an already-produced Gate I
`SemanticCoverageEvaluationResult`, derives the owning `ConceptRequirement`'s
governed identity plus bounded governed relationship context (J1), and,
for `UNMAPPED` results only, exactly one `RemediationAction.REVIEW_SEMANTIC_MAPPING`
recommendation (J2). Performs no I/O of any kind: a pure function over two
already-in-memory objects (a `SemanticCoverageEvaluationResult` and the same
`Blueprint` Gate I already retrieved), supplied by the caller. Does not call
H2, does not query `SemanticMapping`/`SourceField`, and does not touch
CDD-018's `NOT_EVALUATED` status in any way."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    InformationElementCoverageResult,
    SemanticCoverageEvaluationResult,
)
from app.domain.blueprint import Blueprint, ConceptRequirement
from app.domain.shared.exceptions import ValidationException


class Direction(StrEnum):
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"


class RemediationAction(StrEnum):
    REVIEW_SEMANTIC_MAPPING = "REVIEW_SEMANTIC_MAPPING"


@dataclass(frozen=True, slots=True)
class RelationshipContextEntry:
    relationship_type_id: UUID
    direction: Direction
    other_entity_type_id: UUID


@dataclass(frozen=True, slots=True)
class GapImpactContext:
    coverage_result: InformationElementCoverageResult
    concept_requirement_id: UUID
    entity_type_id: UUID
    relationship_context: tuple[RelationshipContextEntry, ...]
    remediation_action: RemediationAction | None


class GapImpactRemediationApplicationService:
    def derive(
        self,
        *,
        coverage_result: SemanticCoverageEvaluationResult,
        blueprint: Blueprint,
    ) -> tuple[GapImpactContext, ...]:
        results = [
            self._derive_one(element, blueprint)
            for element in coverage_result.information_element_results
        ]
        return self._sorted(results)

    @staticmethod
    def _sorted(results: list[GapImpactContext]) -> tuple[GapImpactContext, ...]:
        return tuple(
            sorted(
                results,
                key=lambda result: result.coverage_result.information_element_requirement_id,
            )
        )

    def _derive_one(
        self, element: InformationElementCoverageResult, blueprint: Blueprint
    ) -> GapImpactContext:
        owning_concept = self._find_owning_concept(
            element.information_element_requirement_id, blueprint
        )
        remediation_action = (
            RemediationAction.REVIEW_SEMANTIC_MAPPING
            if element.status is CoverageStatus.UNMAPPED
            else None
        )
        return GapImpactContext(
            coverage_result=element,
            concept_requirement_id=owning_concept.concept_requirement_id.value,
            entity_type_id=owning_concept.entity_type_id.value,
            relationship_context=self._relationship_context(owning_concept, blueprint),
            remediation_action=remediation_action,
        )

    @staticmethod
    def _find_owning_concept(
        information_element_requirement_id: UUID, blueprint: Blueprint
    ) -> ConceptRequirement:
        for concept in blueprint.concept_requirements:
            for information_element in concept.information_element_requirements:
                if (
                    information_element.information_element_requirement_id.value
                    == information_element_requirement_id
                ):
                    return concept
        raise ValidationException(
            "No owning ConceptRequirement found in the supplied Blueprint for "
            f"InformationElementRequirement {information_element_requirement_id}"
        )

    @staticmethod
    def _relationship_context(
        owning_concept: ConceptRequirement, blueprint: Blueprint
    ) -> tuple[RelationshipContextEntry, ...]:
        entries: list[RelationshipContextEntry] = []
        for relationship in owning_concept.relationship_requirements:
            entries.append(
                RelationshipContextEntry(
                    relationship_type_id=relationship.relationship_type_id.value,
                    direction=Direction.OUTGOING,
                    other_entity_type_id=relationship.target_entity_type_id.value,
                )
            )
        for concept in blueprint.concept_requirements:
            for relationship in concept.relationship_requirements:
                if relationship.target_entity_type_id.value == owning_concept.entity_type_id.value:
                    entries.append(
                        RelationshipContextEntry(
                            relationship_type_id=relationship.relationship_type_id.value,
                            direction=Direction.INCOMING,
                            other_entity_type_id=concept.entity_type_id.value,
                        )
                    )
        return tuple(entries)
