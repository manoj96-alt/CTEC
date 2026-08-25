"""Internal Gate T structural-impact and remediation application service
(CDD-031 §15-§16; Gate T Artifact Authorization §6). For each
`InformationElementEvidenceFitnessResult` already produced by
`SourceEvidenceFitnessEvaluationApplicationService`, derives the owning
`ConceptRequirement`'s governed identity plus bounded governed relationship
context, reproducing Gate J's own owning-concept/relationship-context
traversal PATTERN independently -- never importing from, extending, or
modifying `gap_impact_remediation.py` -- and, for `STALE`/`CONFLICTING`
fitness results only, exactly one deterministic remediation recommendation.
Performs no I/O of any kind: a pure function over two already-in-memory
objects (a tuple of `InformationElementEvidenceFitnessResult` and the same
`Blueprint` the caller already retrieved)."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.application.source_evidence_fitness_evaluation import (
    EvidenceFitnessStatus,
    InformationElementEvidenceFitnessResult,
)
from app.domain.blueprint import Blueprint, ConceptRequirement
from app.domain.shared.exceptions import ValidationException


class Direction(StrEnum):
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"


class EvidenceFitnessRemediationAction(StrEnum):
    REFRESH_SOURCE_EVIDENCE = "REFRESH_SOURCE_EVIDENCE"
    REVIEW_CONFLICTING_EVIDENCE = "REVIEW_CONFLICTING_EVIDENCE"


@dataclass(frozen=True, slots=True)
class EvidenceFitnessRelationshipContextEntry:
    relationship_type_id: UUID
    direction: Direction
    other_entity_type_id: UUID


@dataclass(frozen=True, slots=True)
class EvidenceFitnessImpactContext:
    fitness_result: InformationElementEvidenceFitnessResult
    concept_requirement_id: UUID
    entity_type_id: UUID
    relationship_context: tuple[EvidenceFitnessRelationshipContextEntry, ...]
    remediation_action: EvidenceFitnessRemediationAction | None


class SourceEvidenceFitnessImpactRemediationApplicationService:
    def derive(
        self,
        *,
        fitness_results: tuple[InformationElementEvidenceFitnessResult, ...],
        blueprint: Blueprint,
    ) -> tuple[EvidenceFitnessImpactContext, ...]:
        results = [self._derive_one(result, blueprint) for result in fitness_results]
        return self._sorted(results)

    def _derive_one(
        self, fitness_result: InformationElementEvidenceFitnessResult, blueprint: Blueprint
    ) -> EvidenceFitnessImpactContext:
        owning_concept = self._find_owning_concept(
            fitness_result.information_element_requirement_id, blueprint
        )
        return EvidenceFitnessImpactContext(
            fitness_result=fitness_result,
            concept_requirement_id=owning_concept.concept_requirement_id.value,
            entity_type_id=owning_concept.entity_type_id.value,
            relationship_context=self._relationship_context(owning_concept, blueprint),
            remediation_action=self._remediation_action(fitness_result.fitness_status),
        )

    @staticmethod
    def _remediation_action(
        fitness_status: EvidenceFitnessStatus | None,
    ) -> EvidenceFitnessRemediationAction | None:
        if fitness_status is EvidenceFitnessStatus.STALE:
            return EvidenceFitnessRemediationAction.REFRESH_SOURCE_EVIDENCE
        if fitness_status is EvidenceFitnessStatus.CONFLICTING:
            return EvidenceFitnessRemediationAction.REVIEW_CONFLICTING_EVIDENCE
        return None

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
    ) -> tuple[EvidenceFitnessRelationshipContextEntry, ...]:
        entries: list[EvidenceFitnessRelationshipContextEntry] = []
        for relationship in owning_concept.relationship_requirements:
            entries.append(
                EvidenceFitnessRelationshipContextEntry(
                    relationship_type_id=relationship.relationship_type_id.value,
                    direction=Direction.OUTGOING,
                    other_entity_type_id=relationship.target_entity_type_id.value,
                )
            )
        for concept in blueprint.concept_requirements:
            for relationship in concept.relationship_requirements:
                if relationship.target_entity_type_id.value == owning_concept.entity_type_id.value:
                    entries.append(
                        EvidenceFitnessRelationshipContextEntry(
                            relationship_type_id=relationship.relationship_type_id.value,
                            direction=Direction.INCOMING,
                            other_entity_type_id=concept.entity_type_id.value,
                        )
                    )
        return tuple(entries)

    @staticmethod
    def _sorted(
        results: list[EvidenceFitnessImpactContext],
    ) -> tuple[EvidenceFitnessImpactContext, ...]:
        return tuple(
            sorted(
                results,
                key=lambda result: result.fitness_result.information_element_requirement_id,
            )
        )
