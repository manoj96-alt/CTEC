from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.institutional_concept import InstitutionalConcept
from app.infrastructure.persistence.models.ontology_relationship_binding import (
    OntologyRelationshipBinding,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.ontology_seed import (
    REQUIRED_CONCEPTS,
    REQUIRED_RELATIONSHIPS,
    OntologySeeder,
)


def test_ontology_seed_is_repeatable_and_idempotent(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        first = OntologySeeder(session).load()
        session.commit()

    # migrated_engine is session-scoped and shared across test files; another
    # test module may have already run the seeder against this same database
    # earlier in the session, so the first call here is not guaranteed to be
    # the very first ever. What idempotency actually requires — and what this
    # test verifies unconditionally — is that a second call always creates
    # nothing further, and that totals are correct regardless of ordering.
    assert first.concepts_total == len(REQUIRED_CONCEPTS)
    assert first.relationships_total == len(REQUIRED_RELATIONSHIPS)
    assert first.bindings_total == len(REQUIRED_RELATIONSHIPS)

    with factory() as session:
        second = OntologySeeder(session).load()
        session.commit()

    assert second.concepts_created == 0
    assert second.relationships_created == 0
    assert second.bindings_created == 0
    assert second.concepts_total == len(REQUIRED_CONCEPTS)

    with factory() as session:
        concept_count = len(session.scalars(select(InstitutionalConcept)).all())
        entity_type_count = len(session.scalars(select(EntityType)).all())
        relationship_type_count = len(session.scalars(select(RelationshipType)).all())
        binding_count = len(session.scalars(select(OntologyRelationshipBinding)).all())

    assert concept_count >= len(REQUIRED_CONCEPTS)
    assert entity_type_count >= len(REQUIRED_CONCEPTS)
    assert relationship_type_count >= len(REQUIRED_RELATIONSHIPS)
    assert binding_count >= len(REQUIRED_RELATIONSHIPS)


def test_ontology_seed_bindings_reference_correct_domain_and_range(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

    with factory() as session:
        entity_types_by_id = {
            row.entity_type_id: row.entity_type_name for row in session.scalars(select(EntityType)).all()
        }
        relationship_types_by_id = {
            row.relationship_type_id: row.relationship_type_name
            for row in session.scalars(select(RelationshipType)).all()
        }
        bindings = session.scalars(select(OntologyRelationshipBinding)).all()

    observed = {
        (
            relationship_types_by_id[binding.relationship_type_id],
            entity_types_by_id[binding.source_entity_type_id],
            entity_types_by_id[binding.target_entity_type_id],
        )
        for binding in bindings
    }
    expected = set(REQUIRED_RELATIONSHIPS)
    assert expected <= observed
