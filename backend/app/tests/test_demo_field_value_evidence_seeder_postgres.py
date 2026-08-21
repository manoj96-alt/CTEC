"""Postgres-backed proof of the CDD-022 demo Field-Value Evidence seeder
(CDD-022 §20, §21; Field-Value Evidence Artifact Authorization §11):
idempotency, and that the seeded demonstration fact reuses the real,
unmodified H3 `SourceField` identity (via `DemoSemanticMappingSeeder`) and
retrieves through the real, unmodified `FieldValueEvidenceRepositoryImpl`.
"""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    OBSERVED_REPRESENTATION,
    SOURCE_RECORD_REFERENCE,
    DemoFieldValueEvidenceSeeder,
    DemoFieldValueEvidenceSeedSummary,
)
from app.infrastructure.persistence.demo_semantic_mapping_seeder import DemoSemanticMappingSeeder
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)


def _seed(factory: "sessionmaker[Session]") -> DemoFieldValueEvidenceSeedSummary:
    with factory() as session:
        summary = DemoFieldValueEvidenceSeeder(session).seed()
        session.commit()
    return summary


def test_seeder_is_idempotent(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    first = _seed(factory)
    second = _seed(factory)
    assert first == second


def test_seeded_evidence_reuses_the_real_h3_source_field_identity(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        mapping_summary = DemoSemanticMappingSeeder(session).seed()

    assert summary.source_field_id == mapping_summary.source_field_id


def test_seeded_evidence_round_trips_through_the_real_repository(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        loaded = FieldValueEvidenceRepositoryImpl(session).get_by_id(
            summary.field_value_evidence_id
        )

    assert loaded is not None
    assert loaded.source_record_reference == SOURCE_RECORD_REFERENCE
    assert loaded.observed_representation == OBSERVED_REPRESENTATION
    assert loaded.source_field_id.value == summary.source_field_id


def test_seeded_evidence_is_retrievable_by_tenant_and_source_field(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        results = FieldValueEvidenceRepositoryImpl(session).get_by_source_field(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            source_field_id=summary.source_field_id,
        )

    assert len(results) == 1
    assert results[0].field_value_evidence_id.value == summary.field_value_evidence_id


def test_second_seed_call_does_not_create_a_second_evidence_row(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    _seed(factory)

    with factory() as session:
        mapping_summary = DemoSemanticMappingSeeder(session).seed()
        results = FieldValueEvidenceRepositoryImpl(session).get_by_source_field(
            tenant_id=mapping_summary.tenant_id,
            source_field_id=mapping_summary.source_field_id,
        )

    assert len(results) == 1
