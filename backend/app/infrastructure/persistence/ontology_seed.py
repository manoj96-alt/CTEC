"""Seeds the supplier-risk ontology (concepts and relationships) through the
existing governed EntityType / RelationshipType / InstitutionalConcept model.

Deterministic and idempotent: every identifier is derived via uuid5 under the
existing BOOTSTRAP_SEED_NAMESPACE, so re-running this loader against an
already-seeded database creates nothing new and reports zero-created counts.

Curated concept definitions and relationship domain/range pairings are
declared as static metadata below. The physical entity_types /
relationship_types tables (ECOM Physical Data Model v1.3) do not carry a
free-text definition column; definitions are therefore MVP-curated metadata
here, not a database-governed field, and are labelled as such wherever they
are surfaced.
"""

from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy.orm import Session

from app.core.bootstrap import (
    BOOTSTRAP_ENTERPRISE_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    SEED_TIMESTAMP,
)
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_concept import InstitutionalConcept
from app.infrastructure.persistence.models.ontology_relationship_binding import (
    OntologyRelationshipBinding,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType

ONTOLOGY_SEED_VERSION = "SUPPLIER-RISK-ONTOLOGY-V1"

# Curated MVP concept definitions. Not a database-governed field (see module
# docstring): the physical model has no definition column on entity_types.
CONCEPT_DEFINITIONS: dict[str, str] = {
    "Supplier": "An organization that provides materials or services to the enterprise.",
    "Material": "A raw material, component, or input consumed in production.",
    "BOM": "A bill of materials defining which materials compose a product.",
    "Product": "A finished good produced by the enterprise for sale or use.",
    "Facility": "A physical site where production, assembly, or storage occurs.",
    "Region": "A geographic area used to associate suppliers and risk exposure with location.",
    "Contract": "A binding agreement governing the terms of a supplier relationship.",
    "Risk Event": "An observed or reported disruption affecting a supplier or region.",
    "Revenue Exposure": "The business revenue dependent on a product, facility, or material.",
    "Alternate Supplier": "A qualified backup supplier capable of covering a shortfall.",
}

REQUIRED_CONCEPTS: tuple[str, ...] = tuple(CONCEPT_DEFINITIONS.keys())

# (relationship name, source concept, target concept)
REQUIRED_RELATIONSHIPS: tuple[tuple[str, str, str], ...] = (
    ("supplies", "Supplier", "Material"),
    ("usedIn", "Material", "BOM"),
    ("defines", "BOM", "Product"),
    ("generatesRevenue", "Product", "Revenue Exposure"),
    ("locatedIn", "Supplier", "Region"),
    ("exposedTo", "Region", "Risk Event"),
    ("boundBy", "Supplier", "Contract"),
)


@dataclass(frozen=True, slots=True)
class OntologySeedSummary:
    ontology_seed_version: str
    concepts_created: int
    concepts_total: int
    relationships_created: int
    relationships_total: int
    bindings_created: int
    bindings_total: int


class OntologySeeder:
    """Deterministically persists the supplier-risk ontology's governed
    concept and relationship types. Idempotent: safe to call repeatedly."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self) -> OntologySeedSummary:
        concepts_created = 0
        concept_ids: dict[str, UUID] = {}
        entity_type_ids: dict[str, UUID] = {}

        for name in REQUIRED_CONCEPTS:
            concept_id = self._stable_id("institutional-concept", name)
            entity_type_id = self._stable_id("entity-type", name)
            concept_ids[name] = concept_id
            entity_type_ids[name] = entity_type_id

            if self._session.get(InstitutionalConcept, concept_id) is None:
                self._session.add(
                    InstitutionalConcept(
                        institutional_concept_id=concept_id,
                        institutional_concept_name=name,
                        lifecycle_state="Active",
                        effective_from=SEED_TIMESTAMP,
                        effective_to=None,
                        governance_status="Approved",
                        created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                        created_on=SEED_TIMESTAMP,
                        modified_by=None,
                        modified_on=None,
                        version_number=1,
                        previous_version_id=None,
                        enterprise_id=BOOTSTRAP_ENTERPRISE_ID,
                    )
                )
                self._session.flush()
                concepts_created += 1

            if self._session.get(EntityType, entity_type_id) is None:
                self._session.add(
                    EntityType(
                        entity_type_id=entity_type_id,
                        entity_type_name=name,
                        lifecycle_state="Active",
                        effective_from=SEED_TIMESTAMP,
                        effective_to=None,
                        governance_status="Approved",
                        created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                        created_on=SEED_TIMESTAMP,
                        modified_by=None,
                        modified_on=None,
                        version_number=1,
                        previous_version_id=None,
                        institutional_concept_id=concept_id,
                    )
                )
                self._session.flush()

        relationships_created = 0
        bindings_created = 0
        relationship_type_ids: dict[str, UUID] = {}

        for name, source, target in REQUIRED_RELATIONSHIPS:
            relationship_type_id = self._stable_id("relationship-type", name)
            relationship_type_ids[name] = relationship_type_id

            if self._session.get(RelationshipType, relationship_type_id) is None:
                self._session.add(
                    RelationshipType(
                        relationship_type_id=relationship_type_id,
                        relationship_type_name=name,
                        lifecycle_state="Active",
                        effective_from=SEED_TIMESTAMP,
                        effective_to=None,
                        governance_status="Approved",
                        created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                        created_on=SEED_TIMESTAMP,
                        modified_by=None,
                        modified_on=None,
                        version_number=1,
                        previous_version_id=None,
                    )
                )
                self._session.flush()
                relationships_created += 1

            binding_id = self._stable_id("ontology-binding", name)
            if self._session.get(OntologyRelationshipBinding, binding_id) is None:
                self._session.add(
                    OntologyRelationshipBinding(
                        binding_id=binding_id,
                        relationship_type_id=relationship_type_id,
                        source_entity_type_id=entity_type_ids[source],
                        target_entity_type_id=entity_type_ids[target],
                        created_on=SEED_TIMESTAMP,
                    )
                )
                self._session.flush()
                bindings_created += 1

        return OntologySeedSummary(
            ontology_seed_version=ONTOLOGY_SEED_VERSION,
            concepts_created=concepts_created,
            concepts_total=len(REQUIRED_CONCEPTS),
            relationships_created=relationships_created,
            relationships_total=len(REQUIRED_RELATIONSHIPS),
            bindings_created=bindings_created,
            bindings_total=len(REQUIRED_RELATIONSHIPS),
        )

    @staticmethod
    def _stable_id(kind: str, name: str) -> UUID:
        return uuid5(BOOTSTRAP_SEED_NAMESPACE, f"{ONTOLOGY_SEED_VERSION}:{kind}:{name}")
