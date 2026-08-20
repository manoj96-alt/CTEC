"""Postgres-backed acceptance evidence for Gate I I1 (CDD-020 §16, §27
items 2, 3, 8; I1 Semantic Coverage Evaluation Artifact Authorization).
Composes the real, unmodified `BlueprintApplicationService` and the real,
unmodified `SemanticMappingResolutionApplicationService` into the new
`SemanticCoverageEvaluationApplicationService`, proving the H3 deterministic
demonstration ("Supplier Legal Name" MAPPED, "Risk Event Severity"
UNMAPPED), tenant isolation, and determinism against real PostgreSQL.
"""

from uuid import uuid4

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import (
    SemanticMappingResolutionApplicationService,
)
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_semantic_mapping_seeder import (
    DemoSemanticMappingSeeder,
    DemoSemanticMappingSeedSummary,
)
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)


def _seed(factory: "sessionmaker[Session]") -> DemoSemanticMappingSeedSummary:
    with factory() as session:
        summary = DemoSemanticMappingSeeder(session).seed()
        session.commit()
    return summary


def _service(session: Session) -> SemanticCoverageEvaluationApplicationService:
    return SemanticCoverageEvaluationApplicationService(
        blueprint_service=BlueprintApplicationService(repository=BlueprintRepositoryImpl(session)),
        resolver=SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        ),
    )


def test_h3_acceptance_supplier_legal_name_mapped_risk_event_severity_unmapped(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        result = _service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=summary.tenant_id
        )

    by_id = {
        element_result.information_element_requirement_id: element_result
        for element_result in result.information_element_results
    }

    supplier_legal_name = by_id[summary.information_element_requirement_id]
    assert supplier_legal_name.status is CoverageStatus.MAPPED
    assert supplier_legal_name.resolution is not None
    assert supplier_legal_name.resolution.semantic_mapping_id == summary.semantic_mapping_id
    assert supplier_legal_name.resolution.source_field_id == summary.source_field_id
    assert supplier_legal_name.resolution.source_object_id == summary.source_object_id
    assert supplier_legal_name.resolution.source_system_id == summary.source_system_id

    risk_event_severity_results = [
        element_result
        for element_result in result.information_element_results
        if element_result.information_element_requirement_id
        != summary.information_element_requirement_id
    ]
    assert len(risk_event_severity_results) == 1
    risk_event_severity = risk_event_severity_results[0]
    assert risk_event_severity.status is CoverageStatus.UNMAPPED
    assert risk_event_severity.resolution is None


def test_tenant_isolation_h3_demo_data_does_not_leak(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    other_tenant_id = f"i1-isolation-tenant-{uuid4()}"

    with factory() as session:
        result = _service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=other_tenant_id
        )

    assert len(result.information_element_results) == 2
    assert all(
        element_result.status is CoverageStatus.UNMAPPED
        for element_result in result.information_element_results
    )
    assert all(
        element_result.resolution is None for element_result in result.information_element_results
    )


def test_evaluation_is_deterministic_across_repeated_calls(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        service = _service(session)
        first = service.evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=summary.tenant_id
        )
        second = service.evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=summary.tenant_id
        )

    assert first.information_element_results == second.information_element_results
    assert first.blueprint_id == second.blueprint_id
    assert first.blueprint_version_number == second.blueprint_version_number
