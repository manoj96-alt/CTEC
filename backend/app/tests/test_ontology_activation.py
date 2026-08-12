from sqlalchemy import Engine, delete
from sqlalchemy.orm import sessionmaker

from app.application.ontology_activation import OntologyActivationService
from app.domain.ontology.resolver import resolve_supplier_risk_ontology
from app.domain.ontology.semantic_path import build_semantic_path, render_semantic_path_text
from app.infrastructure.persistence.models.ontology_relationship_binding import (
    OntologyRelationshipBinding,
)
from app.infrastructure.persistence.ontology_seed import OntologySeeder


def _seed(migrated_engine: Engine) -> sessionmaker:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
    return factory


def test_activation_resolves_backend_authoritative_ontology_identity(migrated_engine: Engine) -> None:
    factory = _seed(migrated_engine)
    service = OntologyActivationService(factory)

    activation = service.resolve()

    assert activation is not None
    assert activation.ontology_id == "supplier-risk"
    assert activation.ontology_version == "1.0"
    assert activation.ontology_status == "Published"


def test_activation_returns_none_when_no_session_factory_is_configured() -> None:
    service = OntologyActivationService(None)
    assert service.resolve() is None


def test_activation_applicable_ids_reference_real_persisted_records(migrated_engine: Engine) -> None:
    factory = _seed(migrated_engine)
    service = OntologyActivationService(factory)

    activation = service.resolve()

    assert activation is not None
    assert len(activation.applicable_concept_ids) > 0
    assert len(activation.applicable_relationship_ids) > 0
    # every id is a real, resolvable persisted identifier, not a placeholder
    with factory() as session:
        ontology = resolve_supplier_risk_ontology(session)
    persisted_concept_ids = {c["entity_type_id"] for c in ontology.concepts}
    persisted_relationship_ids = {r["relationship_type_id"] for r in ontology.relationships}
    assert set(activation.applicable_concept_ids) <= persisted_concept_ids
    assert set(activation.applicable_relationship_ids) <= persisted_relationship_ids


def test_semantic_path_uses_only_persisted_relationships(migrated_engine: Engine) -> None:
    factory = _seed(migrated_engine)
    with factory() as session:
        ontology = resolve_supplier_risk_ontology(session)

    path = build_semantic_path(ontology)

    assert len(path) == 4  # supplies, usedIn, defines, generatesRevenue
    assert path[0].source_concept == "Supplier"
    assert path[0].relationship_name == "supplies"
    assert path[0].target_concept == "Material"
    assert path[-1].target_concept == "Revenue Exposure"
    # every step's relationship and concept ids are real persisted identifiers
    persisted_relationship_ids = {r["relationship_type_id"] for r in ontology.relationships}
    persisted_concept_ids = {c["entity_type_id"] for c in ontology.concepts}
    for step in path:
        assert step.relationship_id in persisted_relationship_ids
        assert step.source_concept_id in persisted_concept_ids
        assert step.target_concept_id in persisted_concept_ids

    text = render_semantic_path_text(path)
    assert text == (
        "Supplier → supplies → Material → usedIn → BOM "
        "→ defines → Product → generatesRevenue → Revenue Exposure"
    )


def test_semantic_path_omits_a_step_whose_relationship_is_not_persisted(migrated_engine: Engine) -> None:
    factory = _seed(migrated_engine)
    with factory() as session:
        ontology = resolve_supplier_risk_ontology(session)
        # remove the "usedIn" binding to simulate an incompletely-published ontology
        session.execute(
            delete(OntologyRelationshipBinding).where(
                OntologyRelationshipBinding.relationship_type_id
                == next(r["relationship_type_id"] for r in ontology.relationships if r["name"] == "usedIn")
            )
        )
        session.commit()

    with factory() as session:
        degraded_ontology = resolve_supplier_risk_ontology(session)

    path = build_semantic_path(degraded_ontology)

    names = [step.relationship_name for step in path]
    assert "usedIn" not in names
    # the path never fabricates a step for a relationship that isn't persisted
    assert names == ["supplies", "defines", "generatesRevenue"]


def test_activation_quality_score_matches_the_ontology_services_own_score(migrated_engine: Engine) -> None:
    factory = _seed(migrated_engine)
    service = OntologyActivationService(factory)
    activation = service.resolve()

    with factory() as session:
        ontology = resolve_supplier_risk_ontology(session)

    assert activation is not None
    assert activation.quality_overall_score == ontology.quality()["overall_score"]
