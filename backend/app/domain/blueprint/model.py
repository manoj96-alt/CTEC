"""Domain model for the CDD-017 canonical Supply Chain Blueprint requirement
contract (Gate G G2; CDD-017 §6-9). `Blueprint` references, never
redefines, governed ontology identities: `ConceptRequirement.entity_type_id`
and `RelationshipRequirement.relationship_type_id`/`target_entity_type_id`
are opaque `Identifier`s resolved against `entity_types`/`relationship_types`
by the repository layer, not re-validated here (CDD-017 §7). No
`InformationElementRequirement` type system or validation rule is
introduced (CDD-017 §11)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Description, Identifier


class Obligation(StrEnum):
    REQUIRED = "REQUIRED"
    CONDITIONAL = "CONDITIONAL"
    OPTIONAL = "OPTIONAL"


@dataclass(frozen=True, slots=True)
class InformationElementRequirement:
    information_element_requirement_id: Identifier
    concept_requirement_id: Identifier
    element_name: CanonicalName
    description: Description
    obligation: Obligation

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Information Element Requirement ID", self.information_element_requirement_id),
            ("Concept Requirement", self.concept_requirement_id),
        ):
            if not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.element_name, CanonicalName):
            raise ValidationException("Element Name must be a Canonical Name")
        if not isinstance(self.description, Description):
            raise ValidationException("Description must be a Description")
        if not isinstance(self.obligation, Obligation):
            raise ValidationException("Obligation must be an Obligation")


@dataclass(frozen=True, slots=True)
class RelationshipRequirement:
    relationship_requirement_id: Identifier
    concept_requirement_id: Identifier
    relationship_type_id: Identifier
    target_entity_type_id: Identifier
    obligation: Obligation

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Relationship Requirement ID", self.relationship_requirement_id),
            ("Concept Requirement", self.concept_requirement_id),
            ("Relationship Type", self.relationship_type_id),
            ("Target Entity Type", self.target_entity_type_id),
        ):
            if not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.obligation, Obligation):
            raise ValidationException("Obligation must be an Obligation")


@dataclass(frozen=True, slots=True)
class ConceptRequirement:
    concept_requirement_id: Identifier
    blueprint_id: Identifier
    entity_type_id: Identifier
    obligation: Obligation
    domain_label: str | None = None
    relationship_requirements: tuple[RelationshipRequirement, ...] = ()
    information_element_requirements: tuple[InformationElementRequirement, ...] = ()

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Concept Requirement ID", self.concept_requirement_id),
            ("Blueprint", self.blueprint_id),
            ("Entity Type", self.entity_type_id),
        ):
            if not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.obligation, Obligation):
            raise ValidationException("Obligation must be an Obligation")


@dataclass(frozen=True, slots=True)
class Blueprint:
    blueprint_id: Identifier
    blueprint_name: CanonicalName
    lifecycle_state: LifecycleState
    governance_status: GovernanceStatus
    created_by: Identifier
    created_on: datetime
    version_number: int = 1
    previous_version_id: Identifier | None = None
    modified_by: Identifier | None = None
    modified_on: datetime | None = None
    concept_requirements: tuple[ConceptRequirement, ...] = ()

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Blueprint ID", self.blueprint_id),
            ("Created By", self.created_by),
            ("Modified By", self.modified_by),
            ("Previous Version", self.previous_version_id),
        ):
            if identifier_value is not None and not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.blueprint_name, CanonicalName):
            raise ValidationException("Blueprint Name must be a Canonical Name")
        if not isinstance(self.lifecycle_state, LifecycleState):
            raise ValidationException("Lifecycle State must be a Lifecycle State")
        if not isinstance(self.governance_status, GovernanceStatus):
            raise ValidationException("Governance Status must be a Governance Status")
        if self.created_on.tzinfo is None:
            raise ValidationException("Created On must include a timezone")
        if self.modified_on is not None and self.modified_on.tzinfo is None:
            raise ValidationException("Modified On must include a timezone")
        if not isinstance(self.version_number, int) or isinstance(self.version_number, bool):
            raise ValidationException("Version Number must be an integer")
