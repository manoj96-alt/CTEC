"""Postgres-backed acceptance evidence for Gate T fitness evaluation
(CDD-031 §9, §26-§27; Gate T Artifact Authorization §9, items 30-31).
Composes the real, unmodified `SemanticCoverageEvaluationApplicationService`,
the real, unmodified `InformationElementEvidenceAvailabilityApplicationService`
(H4), and the real, unmodified `FieldValueEvidenceRepositoryImpl` into the
new `SourceEvidenceFitnessEvaluationApplicationService`, proving the H3/
CDD-022 deterministic demonstration ("Supplier Legal Name" EVIDENCE_PRESENT)
resolves to a real fitness classification, tenant isolation, conflict
detection against a second real persisted row, and determinism, against
real PostgreSQL."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.application.information_element_evidence_availability import (
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import (
    SemanticMappingResolutionApplicationService,
)
from app.application.source_evidence_fitness_evaluation import (
    EvidenceFitnessStatus,
    InformationElementEvidenceFitnessResult,
    SourceEvidenceFitnessEvaluationApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID, SEED_TIMESTAMP
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    DemoFieldValueEvidenceSeeder,
    DemoFieldValueEvidenceSeedSummary,
)
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)


def _seed(factory: "sessionmaker[Session]") -> DemoFieldValueEvidenceSeedSummary:
    with factory() as session:
        summary = DemoFieldValueEvidenceSeeder(session).seed()
        session.commit()
    return summary


def _coverage_service(session: Session) -> SemanticCoverageEvaluationApplicationService:
    return SemanticCoverageEvaluationApplicationService(
        blueprint_service=BlueprintApplicationService(repository=BlueprintRepositoryImpl(session)),
        resolver=SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        ),
    )


def _h4_service(session: Session) -> InformationElementEvidenceAvailabilityApplicationService:
    return InformationElementEvidenceAvailabilityApplicationService(
        evidence_provider=FieldValueEvidenceRepositoryImpl(session)
    )


def _fitness_service(session: Session) -> SourceEvidenceFitnessEvaluationApplicationService:
    return SourceEvidenceFitnessEvaluationApplicationService(
        evidence_provider=FieldValueEvidenceRepositoryImpl(session)
    )


def _field_value_evidence_row_count(session: Session) -> int:
    return len(session.execute(select(FieldValueEvidenceORM)).all())


def _find_by_source_field(
    fitness_results: tuple[InformationElementEvidenceFitnessResult, ...],
    source_field_id: UUID,
) -> InformationElementEvidenceFitnessResult:
    """The canonical demo Blueprint may have more than one MAPPED element by
    the time this test runs, depending on what other tests have persisted
    against the shared demo tenant earlier in the same session -- never
    assume `fitness_results[0]` is "Supplier Legal Name"; look it up by its
    known, seed-summary-supplied `source_field_id` instead."""
    matches = [result for result in fitness_results if result.source_field_id == source_field_id]
    assert len(matches) == 1
    return matches[0]


def test_h3_acceptance_supplier_legal_name_is_fit_when_evaluated_soon_after_seeding(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        h4_results = _h4_service(session).evaluate(coverage_result=coverage_result)
        fitness_results = _fitness_service(session).evaluate(
            evidence_availability_results=h4_results,
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            as_of=SEED_TIMESTAMP + timedelta(days=1),
        )

    supplier_legal_name = _find_by_source_field(fitness_results, summary.source_field_id)
    assert supplier_legal_name.fitness_status is EvidenceFitnessStatus.FIT


def test_h3_acceptance_supplier_legal_name_is_stale_when_evaluated_long_after_seeding(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        h4_results = _h4_service(session).evaluate(coverage_result=coverage_result)
        fitness_results = _fitness_service(session).evaluate(
            evidence_availability_results=h4_results,
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            as_of=SEED_TIMESTAMP + timedelta(days=30),
        )

    supplier_legal_name = _find_by_source_field(fitness_results, summary.source_field_id)
    assert supplier_legal_name.fitness_status is EvidenceFitnessStatus.STALE


def test_second_conflicting_persisted_row_yields_conflicting(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        conflicting = FieldValueEvidence.new(
            source_field_id=Identifier(summary.source_field_id),
            source_record_reference=summary.source_record_reference,
            observed_representation="Acme Taiwan Limited",
            observed_at=SEED_TIMESTAMP,
            received_at=SEED_TIMESTAMP,
        )
        FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(conflicting)
        session.commit()

        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        h4_results = _h4_service(session).evaluate(coverage_result=coverage_result)
        fitness_results = _fitness_service(session).evaluate(
            evidence_availability_results=h4_results,
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            as_of=SEED_TIMESTAMP + timedelta(days=1),
        )

    supplier_legal_name = _find_by_source_field(fitness_results, summary.source_field_id)
    assert supplier_legal_name.fitness_status is EvidenceFitnessStatus.CONFLICTING


def test_wrong_tenant_raises_explicitly(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    other_tenant_id = f"gate-t-isolation-tenant-{uuid4()}"

    with factory() as session:
        real_coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        h4_results = _h4_service(session).evaluate(coverage_result=real_coverage_result)

        with pytest.raises(ValidationException, match="tenant ownership mismatch"):
            _fitness_service(session).evaluate(
                evidence_availability_results=h4_results,
                tenant_id=other_tenant_id,
                as_of=SEED_TIMESTAMP + timedelta(days=1),
            )


def test_repeated_evaluation_is_deterministic(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        h4_results = _h4_service(session).evaluate(coverage_result=coverage_result)
        service = _fitness_service(session)
        as_of = SEED_TIMESTAMP + timedelta(days=1)
        first = service.evaluate(
            evidence_availability_results=h4_results,
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            as_of=as_of,
        )
        second = service.evaluate(
            evidence_availability_results=h4_results,
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            as_of=as_of,
        )

    assert first == second


def test_no_gate_t_persistence_side_effect(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        before = _field_value_evidence_row_count(session)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        h4_results = _h4_service(session).evaluate(coverage_result=coverage_result)
        _fitness_service(session).evaluate(
            evidence_availability_results=h4_results,
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            as_of=SEED_TIMESTAMP + timedelta(days=1),
        )
        session.commit()

    with factory() as session:
        after = _field_value_evidence_row_count(session)

    assert after == before
