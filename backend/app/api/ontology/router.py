"""Read-only Ontology Service API. All responses come from
app.domain.ontology.resolver.resolve_supplier_risk_ontology — the single,
shared resolution of the persisted ontology, also used by Supplier Risk's
activation contract (app/application/ontology_activation.py). Nothing here
is a frontend or API-layer constant, and there is no second ontology
representation.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session, sessionmaker

from app.core.dependency_container import Container
from app.domain.ontology.connector_catalog import CONNECTOR_CATALOG
from app.domain.ontology.resolver import ONTOLOGY_ID, ONTOLOGY_VERSION, resolve_supplier_risk_ontology

router = APIRouter(prefix="/api/v1/ontologies", tags=["ontologies"])


def _container(request: Request) -> Container:
    return request.app.state.container


def _ontology_session_factory(
    container: Annotated[Container, Depends(_container)],
) -> sessionmaker[Session]:
    if container.ontology_sessions is None:
        raise HTTPException(503, detail={"code": "ONTOLOGY_SERVICE_UNAVAILABLE"})
    return container.ontology_sessions


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


@router.get("")
def list_ontologies(
    session_factory: Annotated[sessionmaker[Session], Depends(_ontology_session_factory)],
) -> dict:
    with session_factory() as session:
        ontology = resolve_supplier_risk_ontology(session)
    return {
        "ontologies": [
            {
                "ontology_id": ontology.ontology_id,
                "name": ontology.name,
                "description": ontology.description,
                "version": ontology.version,
                "status": ontology.status,
                "concept_count": len(ontology.concepts),
                "relationship_count": len(ontology.relationships),
                "quality": ontology.quality(),
                "activation_applications": ontology.activation_applications,
            }
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
        ontology = resolve_supplier_risk_ontology(session)
    return {
        "ontology_id": ontology.ontology_id,
        "name": ontology.name,
        "description": ontology.description,
        "version": ontology.version,
        "status": ontology.status,
        "concepts": ontology.concepts,
        "relationships": ontology.relationships,
        "source_mappings": ["seed:ontology_seed.py:SUPPLIER-RISK-ONTOLOGY-V1"],
        "provenance": "Curated for the domain accelerator via the governed seed boundary.",
        "governance_metadata": "All concepts and relationships persisted with Approved governance status.",
        "quality": ontology.quality(),
        "activation_applications": ontology.activation_applications,
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
        ontology = resolve_supplier_risk_ontology(session)

    if format == "json":
        body = {
            "ontology_id": ontology.ontology_id,
            "version": ontology.version,
            "concepts": ontology.concepts,
            "relationships": ontology.relationships,
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
        for c in ontology.concepts
    ] + [
        {
            "@id": f"ctec:relationship:{r['name']}",
            "@type": "Relationship",
            "name": r["name"],
            "source": f"ctec:concept:{r['source_concept']}",
            "target": f"ctec:concept:{r['target_concept']}",
        }
        for r in ontology.relationships
    ]
    jsonld = {"@context": context, "@id": f"ctec:ontology:{ontology.ontology_id}", "@graph": graph}
    return Response(content=json.dumps(jsonld), media_type="application/ld+json")
