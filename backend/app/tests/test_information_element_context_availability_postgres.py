"""Postgres-backed acceptance evidence for Gate N (CDD-024 §8-§15, §26;
Context Availability Composition Artifact Authorization). Composes the
real, unmodified `SemanticCoverageEvaluationApplicationService` (for a real
Gate I result), the real, unmodified
`InformationElementEvidenceAvailabilityApplicationService` (for a real H4
result), and the new `InformationElementContextAvailabilityApplicationService`
-- against the existing H3/CDD-022 demo fixture
(`DemoFieldValueEvidenceSeeder`, reused by call only, no new seeder).

Gate N itself performs zero I/O -- these tests primarily prove composition
correctness against realistically-produced upstream results, not any I/O
path of Gate N's own (it has none).
"""

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.application.information_element_context_availability import (
    InformationElementContextAvailabilityApplicationService,
)
from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import (
    SemanticMappingResolutionApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    DemoFieldValueEvidenceSeeder,
)
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)


def _seed(factory: "sessionmaker[Session]") -> None:
    with factory() as session:
        DemoFieldValueEvidenceSeeder(session).seed()
        session.commit()


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


def _field_value_evidence_row_count(session: Session) -> int:
    return len(session.execute(select(FieldValueEvidenceORM)).all())


def test_supplier_legal_name_composes_mapped_evidence_present(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        evidence_availability_results = _h4_service(session).evaluate(
            coverage_result=coverage_result
        )

    result = InformationElementContextAvailabilityApplicationService().compose(
        coverage_result=coverage_result, evidence_availability_results=evidence_availability_results
    )

    mapped_results = [r for r in result if r.coverage_status is CoverageStatus.MAPPED]
    assert len(mapped_results) == 1
    assert (
        mapped_results[0].evidence_availability_status
        is EvidenceAvailabilityStatus.EVIDENCE_PRESENT
    )


def test_risk_event_severity_composes_unmapped_none(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        evidence_availability_results = _h4_service(session).evaluate(
            coverage_result=coverage_result
        )

    result = InformationElementContextAvailabilityApplicationService().compose(
        coverage_result=coverage_result, evidence_availability_results=evidence_availability_results
    )

    unmapped_results = [r for r in result if r.coverage_status is CoverageStatus.UNMAPPED]
    assert len(unmapped_results) >= 1
    assert all(r.evidence_availability_status is None for r in unmapped_results)


def test_repeated_composition_of_unchanged_real_fixture_is_identical(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        evidence_availability_results = _h4_service(session).evaluate(
            coverage_result=coverage_result
        )

    service = InformationElementContextAvailabilityApplicationService()
    first = service.compose(
        coverage_result=coverage_result, evidence_availability_results=evidence_availability_results
    )
    second = service.compose(
        coverage_result=coverage_result, evidence_availability_results=evidence_availability_results
    )

    assert first == second


def test_no_persistence_side_effect(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        before = _field_value_evidence_row_count(session)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        evidence_availability_results = _h4_service(session).evaluate(
            coverage_result=coverage_result
        )
        InformationElementContextAvailabilityApplicationService().compose(
            coverage_result=coverage_result,
            evidence_availability_results=evidence_availability_results,
        )
        session.commit()

    with factory() as session:
        after = _field_value_evidence_row_count(session)

    assert after == before
