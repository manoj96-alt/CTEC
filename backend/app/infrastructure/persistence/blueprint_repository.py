"""Blueprint persistence repository (Gate G G2; CDD-017 §6, §14). Global,
product-owned -- no tenant scoping. Minimal by design: `create()` and
`get_by_id()` only (G2 Persistence and Domain Artifact Authorization
companion, `blueprint_repository.py` row exclusions -- no `get_by_name`,
no "list all," no "create new version from existing"/re-parenting method,
no HTTP surface, no conformance/scoring method)."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
    RelationshipRequirement,
)
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.models.blueprint import (
    BlueprintORM,
    ConceptRequirementORM,
    InformationElementRequirementORM,
    RelationshipRequirementORM,
)


class BlueprintRepository(Protocol):
    def create(self, blueprint: Blueprint) -> None:
        """Persist a Blueprint and its child requirements in one
        transaction."""
        ...

    def get_by_id(self, blueprint_id: UUID) -> Blueprint | None: ...


class BlueprintRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, blueprint: Blueprint) -> None:
        self.session.add(
            BlueprintORM(
                blueprint_id=blueprint.blueprint_id.value,
                blueprint_name=blueprint.blueprint_name.value,
                lifecycle_state=blueprint.lifecycle_state.value,
                governance_status=blueprint.governance_status.value,
                version_number=blueprint.version_number,
                previous_version_id=(
                    blueprint.previous_version_id.value
                    if blueprint.previous_version_id is not None
                    else None
                ),
                created_by=blueprint.created_by.value,
                created_on=blueprint.created_on,
                modified_by=(
                    blueprint.modified_by.value if blueprint.modified_by is not None else None
                ),
                modified_on=blueprint.modified_on,
            )
        )
        for concept in blueprint.concept_requirements:
            self.session.add(
                ConceptRequirementORM(
                    concept_requirement_id=concept.concept_requirement_id.value,
                    blueprint_id=concept.blueprint_id.value,
                    entity_type_id=concept.entity_type_id.value,
                    domain_label=concept.domain_label,
                    obligation=concept.obligation.value,
                )
            )
            for relationship in concept.relationship_requirements:
                self.session.add(
                    RelationshipRequirementORM(
                        relationship_requirement_id=relationship.relationship_requirement_id.value,
                        concept_requirement_id=relationship.concept_requirement_id.value,
                        relationship_type_id=relationship.relationship_type_id.value,
                        target_entity_type_id=relationship.target_entity_type_id.value,
                        obligation=relationship.obligation.value,
                    )
                )
            for element in concept.information_element_requirements:
                self.session.add(
                    InformationElementRequirementORM(
                        information_element_requirement_id=(
                            element.information_element_requirement_id.value
                        ),
                        concept_requirement_id=element.concept_requirement_id.value,
                        element_name=element.element_name.value,
                        description=element.description.value,
                        obligation=element.obligation.value,
                    )
                )

    def get_by_id(self, blueprint_id: UUID) -> Blueprint | None:
        model = self.session.get(BlueprintORM, blueprint_id)
        if model is None:
            return None
        concept_models = self.session.scalars(
            select(ConceptRequirementORM).where(ConceptRequirementORM.blueprint_id == blueprint_id)
        ).all()
        return Blueprint(
            blueprint_id=Identifier(model.blueprint_id),
            blueprint_name=CanonicalName(model.blueprint_name),
            lifecycle_state=LifecycleState(model.lifecycle_state),
            governance_status=GovernanceStatus(model.governance_status),
            version_number=model.version_number,
            previous_version_id=(
                Identifier(model.previous_version_id)
                if model.previous_version_id is not None
                else None
            ),
            created_by=Identifier(model.created_by),
            created_on=model.created_on,
            modified_by=Identifier(model.modified_by) if model.modified_by is not None else None,
            modified_on=model.modified_on,
            concept_requirements=tuple(
                self._concept_to_domain(concept_model) for concept_model in concept_models
            ),
        )

    def _concept_to_domain(self, model: ConceptRequirementORM) -> ConceptRequirement:
        relationship_models = self.session.scalars(
            select(RelationshipRequirementORM).where(
                RelationshipRequirementORM.concept_requirement_id == model.concept_requirement_id
            )
        ).all()
        element_models = self.session.scalars(
            select(InformationElementRequirementORM).where(
                InformationElementRequirementORM.concept_requirement_id
                == model.concept_requirement_id
            )
        ).all()
        return ConceptRequirement(
            concept_requirement_id=Identifier(model.concept_requirement_id),
            blueprint_id=Identifier(model.blueprint_id),
            entity_type_id=Identifier(model.entity_type_id),
            obligation=Obligation(model.obligation),
            domain_label=model.domain_label,
            relationship_requirements=tuple(
                RelationshipRequirement(
                    relationship_requirement_id=Identifier(item.relationship_requirement_id),
                    concept_requirement_id=Identifier(item.concept_requirement_id),
                    relationship_type_id=Identifier(item.relationship_type_id),
                    target_entity_type_id=Identifier(item.target_entity_type_id),
                    obligation=Obligation(item.obligation),
                )
                for item in relationship_models
            ),
            information_element_requirements=tuple(
                InformationElementRequirement(
                    information_element_requirement_id=Identifier(
                        item.information_element_requirement_id
                    ),
                    concept_requirement_id=Identifier(item.concept_requirement_id),
                    element_name=CanonicalName(item.element_name),
                    description=Description(item.description),
                    obligation=Obligation(item.obligation),
                )
                for item in element_models
            ),
        )
