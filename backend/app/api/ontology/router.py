"""Read-only Ontology Service API. All responses are generated from ontology
data persisted through the existing governed EntityType / RelationshipType /
InstitutionalConcept model — nothing here is a frontend or API-layer
constant. See app/infrastructure/persistence/ontology_seed.py for the
seeding boundary this data enters through, and app/domain/ontology/
quality_score.py for the deterministic scoring method.
"""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.dependency_container import Container
from app.domain.ontology.connector_catalog import CONNECTOR_CATALOG
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

router = APIRouter(prefix="/api/v1/ontologies", tags=["ontologies"])

ONTOLOGY_ID = "supplier-risk"
ONTOLOGY_VERSION = "1.0"
ONTOLOGY_NAME = "Supplier Risk Enterprise Ontology"
ONTOLOGY_DESCRIPTION = (
    "Governed concepts and relationships connecting suppliers, materials, "
    "products, facilities, contracts, risk events, and revenue exposure, "
    "activating the Supplier Risk application."
)
ACTIVATION_APPLICATIONS = ["Supplier Risk"]


def _container(request: Request) -> Container:
    return request.app.state.container


def _ontology_session_factory(container: Annotated[Container, Depends(_container)]) -> sessionmaker[Session]:
    if container.ontology_sessions is None:
        raise HTTPException(503, detail={"code": "ONTOLOGY_SERVICE_UNAVAILABLE"})
    return container.ontology_sessions


def _discovery_label(name: str) -> str:
    # MVP labelling: everything seeded through ontology_seed.py is curated
    # for the domain accelerator, not yet source-discovered or mapping-derived.
    return "curated" if name in CONCEPT_DEFINITIONS or name in {n for n, _, _ in REQUIRED_RELATIONSHIPS} else "unknown"


def _load_ontology_data(session: Session) -> dict:
    concept_rows = session.scalars(
        select(EntityType, InstitutionalConcept)
        .join(InstitutionalConcept, EntityType.institutional_concept_id == InstitutionalConcept.institutional_concept_id)
    ).all()
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

    return {"concepts": concepts, "relationships": relationships}


def _quality_response(data: dict) -> dict:
    concept_names = {c["name"] for c in data["concepts"]}
    relationship_triples = {
        (r["name"], r["source_concept"], r["target_concept"]) for r in data["relationships"]
    }
    concept_statuses = {c["name"]: c["governance_status"] for c in data["concepts"]}
    relationship_statuses = {r["name"]: r["governance_status"] for r in data["relationships"]}

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


def _ontology_status(data: dict) -> str:
    concept_names = {c["name"] for c in data["concepts"]}
    relationship_triples = {(r["name"], r["source_concept"], r["target_concept"]) for r in data["relationships"]}
    complete = set(REQUIRED_CONCEPTS) <= concept_names and set(REQUIRED_RELATIONSHIPS) <= relationship_triples
    return "Published" if complete else "Draft"


@router.get("")
def list_ontologies(session_factory: Annotated[sessionmaker[Session], Depends(_ontology_session_factory)]) -> dict:
    with session_factory() as session:
        data = _load_ontology_data(session)
    quality = _quality_response(data)
    return {
        "ontologies": [
            {
                "ontology_id": ONTOLOGY_ID,
                "name": ONTOLOGY_NAME,
                "description": ONTOLOGY_DESCRIPTION,
                "version": ONTOLOGY_VERSION,
                "status": _ontology_status(data),
                "concept_count": len(data["concepts"]),
                "relationship_count": len(data["relationships"]),
                "quality": quality,
                "activation_applications": ACTIVATION_APPLICATIONS,
            }
        ]
    }


@router.get("/connectors/catalog")
def list_connectors() -> dict:
    return {
        "connectors": [
            {
                "connector_id": c.connector_id,
                "display_name": c.display_name,
                "source_system_type": c.source_system_type,
                "authentication_type": c.authentication_type,
                "supported_object_categories": list(c.supported_object_categories),
                "configuration_schema_reference": c.configuration_schema_reference,
                "mapping_template_reference": c.mapping_template_reference,
                "health_status": c.health_status,
                "maturity": c.maturity,
            }
            for c in CONNECTOR_CATALOG
        ]
    }


@router.get("/{ontology_id}")
def get_ontology(
    ontology_id: str,
    session_factory: Annotated[sessionmaker[Session], Depends(_ontology_session_factory)],
) -> dict:
    if ontology_id != ONTOLOGY_ID:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND"})
    with session_factory() as session:
        data = _load_ontology_data(session)
    quality = _quality_response(data)
    return {
        "ontology_id": ONTOLOGY_ID,
        "name": ONTOLOGY_NAME,
        "description": ONTOLOGY_DESCRIPTION,
        "version": ONTOLOGY_VERSION,
        "status": _ontology_status(data),
        "concepts": data["concepts"],
        "relationships": data["relationships"],
        "source_mappings": ["seed:ontology_seed.py:SUPPLIER-RISK-ONTOLOGY-V1"],
        "provenance": "Curated for the domain accelerator via the governed seed boundary.",
        "governance_metadata": "All concepts and relationships persisted with Approved governance status.",
        "quality": quality,
        "activation_applications": ACTIVATION_APPLICATIONS,
    }


@router.get("/{ontology_id}/versions/{version}")
def get_ontology_version(
    ontology_id: str,
    version: str,
    session_factory: Annotated[sessionmaker[Session], Depends(_ontology_session_factory)],
) -> dict:
    if ontology_id != ONTOLOGY_ID or version != ONTOLOGY_VERSION:
        raise HTTPException(404, detail={"code": "ONTOLOGY_VERSION_NOT_FOUND"})
    return get_ontology(ontology_id, session_factory)


@router.get("/{ontology_id}/export")
def export_ontology(
    ontology_id: str,
    session_factory: Annotated[sessionmaker[Session], Depends(_ontology_session_factory)],
    format: Annotated[str, Query()] = "json",
) -> Response:
    if ontology_id != ONTOLOGY_ID:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND"})
    if format not in {"json", "json-ld"}:
        raise HTTPException(400, detail={"code": "UNSUPPORTED_EXPORT_FORMAT"})

    with session_factory() as session:
        data = _load_ontology_data(session)

    if format == "json":
        body = {
            "ontology_id": ONTOLOGY_ID,
            "version": ONTOLOGY_VERSION,
            "concepts": data["concepts"],
            "relationships": data["relationships"],
        }
        return Response(content=json.dumps(body), media_type="application/json")

    context = {
        "@vocab": "https://ctec.example/ontology/supplier-risk#",
        "name": "https://schema.org/name",
        "definition": "https://schema.org/description",
    }
    graph = [
        {
            "@id": f"ctec:concept:{c['name']}",
            "@type": "Concept",
            "name": c["name"],
            "definition": c["definition"],
            "governanceStatus": c["governance_status"],
        }
        for c in data["concepts"]
    ] + [
        {
            "@id": f"ctec:relationship:{r['name']}",
            "@type": "Relationship",
            "name": r["name"],
            "source": f"ctec:concept:{r['source_concept']}",
            "target": f"ctec:concept:{r['target_concept']}",
        }
        for r in data["relationships"]
    ]
    jsonld = {"@context": context, "@id": f"ctec:ontology:{ONTOLOGY_ID}", "@graph": graph}
    return Response(content=json.dumps(jsonld), media_type="application/ld+json")
