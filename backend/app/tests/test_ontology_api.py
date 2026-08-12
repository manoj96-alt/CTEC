from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.infrastructure.persistence.ontology_seed import (
    REQUIRED_CONCEPTS,
    REQUIRED_RELATIONSHIPS,
)
from app.main import create_app


def _seed_ontology() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    factory = sessionmaker(engine)
    from app.infrastructure.persistence.ontology_seed import OntologySeeder

    with factory() as session:
        OntologySeeder(session).load()
        session.commit()


def test_ontology_summary_reflects_persisted_data() -> None:
    _seed_ontology()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ontologies")
    assert response.status_code == 200
    body = response.json()
    assert len(body["ontologies"]) == 1
    summary = body["ontologies"][0]
    assert summary["ontology_id"] == "supplier-risk"
    assert summary["concept_count"] == len(REQUIRED_CONCEPTS)
    assert summary["relationship_count"] == len(REQUIRED_RELATIONSHIPS)
    assert summary["status"] == "Published"
    assert summary["quality"]["overall_score"] == 1.0


def test_ontology_detail_exposes_concepts_and_relationships_from_persisted_data() -> None:
    _seed_ontology()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ontologies/supplier-risk")
    assert response.status_code == 200
    body = response.json()
    concept_names = {c["name"] for c in body["concepts"]}
    assert set(REQUIRED_CONCEPTS) <= concept_names
    relationship_triples = {
        (r["name"], r["source_concept"], r["target_concept"]) for r in body["relationships"]
    }
    assert set(REQUIRED_RELATIONSHIPS) <= relationship_triples
    supplier = next(c for c in body["concepts"] if c["name"] == "Supplier")
    assert supplier["definition"]
    assert supplier["governance_status"] == "Approved"


def test_ontology_version_endpoint_matches_detail() -> None:
    _seed_ontology()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ontologies/supplier-risk/versions/1.0")
    assert response.status_code == 200
    assert response.json()["version"] == "1.0"


def test_ontology_version_endpoint_404s_for_unknown_version() -> None:
    _seed_ontology()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ontologies/supplier-risk/versions/9.9")
    assert response.status_code == 404


def test_ontology_export_json_ld_is_well_formed() -> None:
    _seed_ontology()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ontologies/supplier-risk/export?format=json-ld")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/ld+json")
    body = response.json()
    assert "@context" in body
    assert "@graph" in body
    concept_nodes = [node for node in body["@graph"] if node["@type"] == "Concept"]
    relationship_nodes = [node for node in body["@graph"] if node["@type"] == "Relationship"]
    assert len(concept_nodes) >= len(REQUIRED_CONCEPTS)
    assert len(relationship_nodes) >= len(REQUIRED_RELATIONSHIPS)


def test_ontology_export_rejects_unsupported_format() -> None:
    _seed_ontology()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ontologies/supplier-risk/export?format=owl")
    assert response.status_code == 400


def test_connector_catalog_uses_only_honest_maturity_labels() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/ontologies/connectors/catalog")
    assert response.status_code == 200
    body = response.json()
    connectors = body["connectors"]
    assert len(connectors) == 9
    allowed = {"Demo Connected", "Skeleton Available", "Roadmap"}
    assert all(c["maturity"] in allowed for c in connectors)
    names = {c["display_name"] for c in connectors}
    assert names == {
        "SAP S/4HANA",
        "SAP Ariba",
        "Salesforce",
        "Snowflake",
        "Databricks",
        "Microsoft Fabric",
        "Document Repository",
        "REST API",
        "MCP",
    }
    # No connector is claimed Demo Connected in this MVP: demo data enters
    # through the seed boundary directly, not a named external connector.
    assert not any(c["maturity"] == "Demo Connected" for c in connectors)
