"""Single, shared resolver for the persisted supplier-risk ontology. Reused
by the Ontology Service API (app/api/ontology/router.py) and by Supplier
Risk's ontology activation contract
(app/application/ontology_activation.py) — there is exactly one ontology
representation, read from the same persisted tables both times.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.ontology.quality_score import calculate_quality_score
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_concept import InstitutionalConcept
from app.infrastructure.persistence.models.ontology_relationship_binding import (
    OntologyRelationshipBinding,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.ontology_seed import (
    CONCEPT_DEFINITIONS,
    REQUIRED_CONCEPTS,
    REQUIRED_RELATIONSHIPS,
)

ONTOLOGY_ID = "supplier-risk"
ONTOLOGY_VERSION = "1.0"
ONTOLOGY_NAME = "Supplier Risk Enterprise Ontology"
ONTOLOGY_DESCRIPTION = (
    "Governed concepts and relationships connecting suppliers, materials, "
    "products, facilities, contracts, risk events, and revenue exposure, "
    "activating the Supplier Risk application."
)
ACTIVATION_APPLICATIONS = ["Supplier Risk"]


def _discovery_label(name: str) -> str:
    return (
        "curated"
        if name in CONCEPT_DEFINITIONS or name in {n for n, _, _ in REQUIRED_RELATIONSHIPS}
        else "unknown"
    )


@dataclass(frozen=True, slots=True)
class ResolvedOntology:
    ontology_id: str
    name: str
    description: str
    version: str
    status: str
    concepts: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    activation_applications: list[str] = field(default_factory=list)

    def concept_id_by_name(self, name: str) -> str | None:
        for concept in self.concepts:
            if concept["name"] == name:
                return concept["entity_type_id"]
        return None

    def relationship_id_by_name(self, name: str) -> str | None:
        for relationship in self.relationships:
            if relationship["name"] == name:
                return relationship["relationship_type_id"]
        return None

    def relationship_by_name(self, name: str) -> dict | None:
        for relationship in self.relationships:
            if relationship["name"] == name:
                return relationship
        return None

    def quality(self) -> dict:
        concept_names = {c["name"] for c in self.concepts}
        relationship_triples = {
            (r["name"], r["source_concept"], r["target_concept"]) for r in self.relationships
        }
        concept_statuses = {c["name"]: c["governance_status"] for c in self.concepts}
        relationship_statuses = {r["name"]: r["governance_status"] for r in self.relationships}
        result = calculate_quality_score(
            concept_names=concept_names,
            relationship_triples=relationship_triples,
            concept_governance_statuses=concept_statuses,
            relationship_governance_statuses=relationship_statuses,
        )
        return {
            "overall_score": result.overall_score,
            "method": result.method,
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "score": d.score,
                    "passed": d.passed,
                    "explanation": d.explanation,
                }
                for d in result.dimensions
            ],
            "passed_checks": list(result.passed_checks),
            "failed_checks": list(result.failed_checks),
        }


def resolve_supplier_risk_ontology(session: Session) -> ResolvedOntology:
    """The single, authoritative resolution of the persisted supplier-risk
    ontology. Both the Ontology Service API and Supplier Risk's activation
    contract call this function — neither computes its own copy."""
    entity_types = session.execute(select(EntityType)).scalars().all()
    entity_type_by_id = {row.entity_type_id: row for row in entity_types}
    relationship_types = session.execute(select(RelationshipType)).scalars().all()
    relationship_type_by_id = {row.relationship_type_id: row for row in relationship_types}
    bindings = session.execute(select(OntologyRelationshipBinding)).scalars().all()

    concepts = [
        {
            "entity_type_id": str(row.entity_type_id),
            "name": row.entity_type_name,
            "definition": CONCEPT_DEFINITIONS.get(row.entity_type_name, ""),
            "definition_source": "curated",
            "lifecycle_state": row.lifecycle_state,
            "governance_status": row.governance_status,
            "version_number": row.version_number,
            "discovery_label": _discovery_label(row.entity_type_name),
        }
        for row in entity_types
        if row.entity_type_name in REQUIRED_CONCEPTS
    ]

    relationships = []
    for binding in bindings:
        relationship_type = relationship_type_by_id.get(binding.relationship_type_id)
        source = entity_type_by_id.get(binding.source_entity_type_id)
        target = entity_type_by_id.get(binding.target_entity_type_id)
        if relationship_type is None or source is None or target is None:
            continue
        if relationship_type.relationship_type_name not in {n for n, _, _ in REQUIRED_RELATIONSHIPS}:
            continue
        relationships.append(
            {
                "relationship_type_id": str(relationship_type.relationship_type_id),
                "name": relationship_type.relationship_type_name,
                "source_concept": source.entity_type_name,
                "target_concept": target.entity_type_name,
                "lifecycle_state": relationship_type.lifecycle_state,
                "governance_status": relationship_type.governance_status,
                "discovery_label": _discovery_label(relationship_type.relationship_type_name),
            }
        )

    concept_names = {c["name"] for c in concepts}
    relationship_triples = {(r["name"], r["source_concept"], r["target_concept"]) for r in relationships}
    complete = set(REQUIRED_CONCEPTS) <= concept_names and set(REQUIRED_RELATIONSHIPS) <= relationship_triples
    status = "Published" if complete else "Draft"

    return ResolvedOntology(
        ontology_id=ONTOLOGY_ID,
        name=ONTOLOGY_NAME,
        description=ONTOLOGY_DESCRIPTION,
        version=ONTOLOGY_VERSION,
        status=status,
        concepts=concepts,
        relationships=relationships,
        activation_applications=ACTIVATION_APPLICATIONS,
    )
