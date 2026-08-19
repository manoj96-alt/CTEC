"""Seeds the canonical Supply Chain Blueprint (Gate G G3.5; CDD-017 §3, §13;
G3.5 Canonical Blueprint Seed Artifact Authorization).

Deterministic and idempotent: every requirement identifier is derived via
`uuid5` under the existing `BOOTSTRAP_SEED_NAMESPACE`, exactly matching
`OntologySeeder._stable_id()`'s convention, so re-running this loader against
an already-seeded database creates nothing new. Persisted through the
unmodified G2 `BlueprintRepositoryImpl.create()` in one transaction.

References the already-governed ontology only, by name lookup against
`entity_types`/`relationship_types` -- creates no `EntityType`,
`RelationshipType`, or `InstitutionalConcept`. If a required governed
identity cannot be resolved, seeding fails explicitly (raises
`ValidationException`) rather than substituting or silently skipping it
(CDD-017 §7).

Canonical content is exactly what the G3.5 Product Owner decisions approved:
the full existing ten-concept/ten-relationship governed vocabulary at
`REQUIRED` obligation, plus exactly two `InformationElementRequirement`s
(`Supplier Legal Name` `REQUIRED`, `Risk Event Severity` `CONDITIONAL`). No
additional canonical content is authorized.
"""

from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.bootstrap import (
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    SEED_TIMESTAMP,
)
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
    RelationshipRequirement,
)
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.models.blueprint import BlueprintORM
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.relationship_type import RelationshipType

BLUEPRINT_SEED_VERSION = "CANONICAL-BLUEPRINT-V1"

CANONICAL_BLUEPRINT_NAME = "CTEC Semiconductor Supply Chain Blueprint"

REQUIRED_CONCEPT_NAMES: tuple[str, ...] = (
    "Supplier",
    "Material",
    "BOM",
    "Product",
    "Facility",
    "Region",
    "Contract",
    "Risk Event",
    "Revenue Exposure",
    "Alternate Supplier",
)

# (relationship name, source concept, target concept) -- matches
# ontology_seed.py::REQUIRED_RELATIONSHIPS exactly.
REQUIRED_RELATIONSHIP_TUPLES: tuple[tuple[str, str, str], ...] = (
    ("supplies", "Supplier", "Material"),
    ("usedIn", "Material", "BOM"),
    ("defines", "BOM", "Product"),
    ("generatesRevenue", "Product", "Revenue Exposure"),
    ("locatedIn", "Supplier", "Region"),
    ("exposedTo", "Region", "Risk Event"),
    ("boundBy", "Supplier", "Contract"),
    ("assembledAt", "Product", "Facility"),
    ("coveredBy", "Material", "Contract"),
    ("candidateFor", "Alternate Supplier", "Material"),
)

# (owning concept name, element name, description, obligation)
INFORMATION_ELEMENT_DEFINITIONS: tuple[tuple[str, str, str, Obligation], ...] = (
    (
        "Supplier",
        "Supplier Legal Name",
        "The supplier's registered legal entity name.",
        Obligation.REQUIRED,
    ),
    (
        "Risk Event",
        "Risk Event Severity",
        "The severity classification of an observed or reported risk event, where captured.",
        Obligation.CONDITIONAL,
    ),
)


@dataclass(frozen=True, slots=True)
class BlueprintSeedSummary:
    blueprint_seed_version: str
    blueprint_id: UUID
    created: bool


class BlueprintSeeder:
    """Deterministically persists the canonical Supply Chain Blueprint.
    Idempotent: safe to call repeatedly."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self) -> BlueprintSeedSummary:
        blueprint_id = self._stable_id("blueprint", CANONICAL_BLUEPRINT_NAME)
        if self._session.get(BlueprintORM, blueprint_id) is not None:
            return BlueprintSeedSummary(
                blueprint_seed_version=BLUEPRINT_SEED_VERSION,
                blueprint_id=blueprint_id,
                created=False,
            )

        concept_requirement_ids = {
            name: Identifier(self._stable_id("concept-requirement", name))
            for name in REQUIRED_CONCEPT_NAMES
        }

        relationship_requirements_by_concept: dict[str, list[RelationshipRequirement]] = {
            name: [] for name in REQUIRED_CONCEPT_NAMES
        }
        for relationship_name, source, target in REQUIRED_RELATIONSHIP_TUPLES:
            relationship_requirements_by_concept[source].append(
                RelationshipRequirement(
                    relationship_requirement_id=Identifier(
                        self._stable_id("relationship-requirement", relationship_name)
                    ),
                    concept_requirement_id=concept_requirement_ids[source],
                    relationship_type_id=self._relationship_type_id(relationship_name),
                    target_entity_type_id=self._entity_type_id(target),
                    obligation=Obligation.REQUIRED,
                )
            )

        information_elements_by_concept: dict[str, list[InformationElementRequirement]] = {
            name: [] for name in REQUIRED_CONCEPT_NAMES
        }
        for concept_name, element_name, description, obligation in INFORMATION_ELEMENT_DEFINITIONS:
            information_elements_by_concept[concept_name].append(
                InformationElementRequirement(
                    information_element_requirement_id=Identifier(
                        self._stable_id("information-element-requirement", element_name)
                    ),
                    concept_requirement_id=concept_requirement_ids[concept_name],
                    element_name=CanonicalName(element_name),
                    description=Description(description),
                    obligation=obligation,
                )
            )

        concept_requirements = tuple(
            ConceptRequirement(
                concept_requirement_id=concept_requirement_ids[concept_name],
                blueprint_id=Identifier(blueprint_id),
                entity_type_id=self._entity_type_id(concept_name),
                obligation=Obligation.REQUIRED,
                relationship_requirements=tuple(relationship_requirements_by_concept[concept_name]),
                information_element_requirements=tuple(
                    information_elements_by_concept[concept_name]
                ),
            )
            for concept_name in REQUIRED_CONCEPT_NAMES
        )

        blueprint = Blueprint(
            blueprint_id=Identifier(blueprint_id),
            blueprint_name=CanonicalName(CANONICAL_BLUEPRINT_NAME),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=SEED_TIMESTAMP,
            concept_requirements=concept_requirements,
        )

        BlueprintRepositoryImpl(self._session).create(blueprint)
        self._session.flush()

        return BlueprintSeedSummary(
            blueprint_seed_version=BLUEPRINT_SEED_VERSION,
            blueprint_id=blueprint_id,
            created=True,
        )

    def _entity_type_id(self, name: str) -> Identifier:
        value = self._session.scalar(
            select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
        )
        if value is None:
            raise ValidationException(f"Required governed entity type not found: {name}")
        return Identifier(value)

    def _relationship_type_id(self, name: str) -> Identifier:
        value = self._session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == name
            )
        )
        if value is None:
            raise ValidationException(f"Required governed relationship type not found: {name}")
        return Identifier(value)

    @staticmethod
    def _stable_id(kind: str, name: str) -> UUID:
        return uuid5(BOOTSTRAP_SEED_NAMESPACE, f"{BLUEPRINT_SEED_VERSION}:{kind}:{name}")
