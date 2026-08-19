"""Blueprint structural conformance evaluation (Gate G G4; CDD-018 §6-16;
G4 Blueprint Conformance Artifact Authorization). Given a tenant's canonical
enterprise context, determines whether that context satisfies the canonical
Blueprint's `ConceptRequirement`/`RelationshipRequirement` declarations.
Every `InformationElementRequirement` reports `NOT_EVALUATED` regardless of
obligation (CDD-018 §10) and never enters the overall structural-conformance
aggregate (CDD-018 §11). Ephemeral: performs no persistence of any kind
(CDD-018 §15). Resolves the Blueprint exclusively through
`BlueprintApplicationService.get_approved_by_name()` -- no import of
`blueprint_seed.py`/`BlueprintSeeder` or any seed/bootstrap module (binding,
Product Owner correction during G4 artifact-authorization review)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
    RelationshipRequirement,
)
from app.domain.shared.exceptions import ValidationException


class BlueprintLookup(Protocol):
    """Structural contract satisfied by `BlueprintApplicationService`
    (unmodified) -- the only method this service depends on."""

    def get_approved_by_name(self, blueprint_name: str) -> Blueprint | None: ...


class ConformanceContextReader(Protocol):
    """Structural contract satisfied by `BlueprintConformanceContextStore`
    (unmodified) -- the only methods this service depends on."""

    def entity_type_ids_present(self, tenant_id: str) -> frozenset[UUID]: ...

    def relationship_triples_present(
        self, tenant_id: str
    ) -> frozenset[tuple[UUID, UUID, UUID]]: ...


class RequirementStatus(StrEnum):
    SATISFIED = "SATISFIED"
    MISSING = "MISSING"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True, slots=True)
class RequirementResult:
    requirement_id: UUID
    requirement_kind: str
    obligation: Obligation
    status: RequirementStatus
    evidence: str


@dataclass(frozen=True, slots=True)
class ConformanceResult:
    blueprint_id: UUID
    blueprint_version_number: int
    tenant_id: str
    evaluated_at: datetime
    concept_results: tuple[RequirementResult, ...]
    relationship_results: tuple[RequirementResult, ...]
    information_element_results: tuple[RequirementResult, ...]
    overall_conformant: bool


class BlueprintConformanceApplicationService:
    def __init__(
        self,
        *,
        blueprint_service: BlueprintLookup,
        context_store: ConformanceContextReader,
    ) -> None:
        self.blueprint_service = blueprint_service
        self.context_store = context_store

    def evaluate(self, *, blueprint_name: str, tenant_id: str) -> ConformanceResult:
        blueprint = self.blueprint_service.get_approved_by_name(blueprint_name)
        if blueprint is None:
            raise ValidationException(f"No Approved Blueprint found for name: {blueprint_name}")

        entity_type_ids = self.context_store.entity_type_ids_present(tenant_id)
        relationship_triples = self.context_store.relationship_triples_present(tenant_id)

        concept_results: list[RequirementResult] = []
        relationship_results: list[RequirementResult] = []
        information_element_results: list[RequirementResult] = []

        for concept in blueprint.concept_requirements:
            concept_results.append(self._evaluate_concept(concept, entity_type_ids))
            for relationship in concept.relationship_requirements:
                relationship_results.append(
                    self._evaluate_relationship(concept, relationship, relationship_triples)
                )
            for element in concept.information_element_requirements:
                information_element_results.append(self._evaluate_information_element(element))

        overall_conformant = all(
            result.status is RequirementStatus.SATISFIED
            for result in (*concept_results, *relationship_results)
            if result.obligation is Obligation.REQUIRED
        )

        return ConformanceResult(
            blueprint_id=blueprint.blueprint_id.value,
            blueprint_version_number=blueprint.version_number,
            tenant_id=tenant_id,
            evaluated_at=datetime.now(UTC),
            concept_results=self._sorted(concept_results),
            relationship_results=self._sorted(relationship_results),
            information_element_results=self._sorted(information_element_results),
            overall_conformant=overall_conformant,
        )

    @staticmethod
    def _sorted(results: list[RequirementResult]) -> tuple[RequirementResult, ...]:
        return tuple(sorted(results, key=lambda result: result.requirement_id))

    @staticmethod
    def _evaluate_concept(
        concept: ConceptRequirement, entity_type_ids: frozenset[UUID]
    ) -> RequirementResult:
        if concept.entity_type_id.value in entity_type_ids:
            status = RequirementStatus.SATISFIED
            evidence = f"Matching enterprise entity of type {concept.entity_type_id.value} found."
        else:
            status = RequirementStatus.MISSING
            evidence = f"No enterprise entity of type {concept.entity_type_id.value} found for this tenant."
        return RequirementResult(
            requirement_id=concept.concept_requirement_id.value,
            requirement_kind="ConceptRequirement",
            obligation=concept.obligation,
            status=status,
            evidence=evidence,
        )

    @staticmethod
    def _evaluate_relationship(
        concept: ConceptRequirement,
        relationship: RelationshipRequirement,
        relationship_triples: frozenset[tuple[UUID, UUID, UUID]],
    ) -> RequirementResult:
        triple = (
            relationship.relationship_type_id.value,
            concept.entity_type_id.value,
            relationship.target_entity_type_id.value,
        )
        if triple in relationship_triples:
            status = RequirementStatus.SATISFIED
            evidence = (
                f"Matching institutional relationship of type "
                f"{relationship.relationship_type_id.value} found from entity type "
                f"{concept.entity_type_id.value} to {relationship.target_entity_type_id.value}."
            )
        else:
            status = RequirementStatus.MISSING
            evidence = (
                f"No institutional relationship of type {relationship.relationship_type_id.value} "
                f"found from entity type {concept.entity_type_id.value} to "
                f"{relationship.target_entity_type_id.value} for this tenant."
            )
        return RequirementResult(
            requirement_id=relationship.relationship_requirement_id.value,
            requirement_kind="RelationshipRequirement",
            obligation=relationship.obligation,
            status=status,
            evidence=evidence,
        )

    @staticmethod
    def _evaluate_information_element(
        element: InformationElementRequirement,
    ) -> RequirementResult:
        return RequirementResult(
            requirement_id=element.information_element_requirement_id.value,
            requirement_kind="InformationElementRequirement",
            obligation=element.obligation,
            status=RequirementStatus.NOT_EVALUATED,
            evidence=(
                "InformationElementRequirement evaluation is deferred to a future, "
                "separately-governed capability (Source-to-Blueprint Semantic Mapping)."
            ),
        )
