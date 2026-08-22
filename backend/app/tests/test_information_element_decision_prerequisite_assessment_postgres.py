"""Postgres-backed acceptance evidence for Gate K (CDD-026 §23 acceptance
criteria 1 and 4; Decision-Prerequisite Assessment Artifact Authorization
§10). Composes the real, unmodified `SemanticCoverageEvaluationApplicationService`
(for a real Gate I result), the real, unmodified
`InformationElementEvidenceAvailabilityApplicationService` (for a real H4
result), and the real, unmodified `InformationElementContextAvailabilityApplicationService`
(for a real Gate N result) -- against the existing H3/CDD-022 demo fixture
(`DemoFieldValueEvidenceSeeder`, reused by call only, no new seeder) --
exactly mirroring `test_information_element_context_availability_postgres.py`'s
own structure.

Gate K's own `assess()` itself performs zero I/O -- these two tests exist
because CDD-026 §23 acceptance criteria 1 and 4 explicitly require proof
against the real demo fixture ("Supplier Legal Name", "Risk Event
Severity"), and those two named elements exist only via Postgres-backed
seeding. This authorization does not make Gate K itself database-aware:
Gate K's own production module never imports any of the classes this file
imports.
"""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.application.information_element_context_availability import (
    InformationElementContextAvailabilityApplicationService,
)
from app.application.information_element_decision_prerequisite_assessment import (
    InformationElementDecisionPrerequisiteAssessmentApplicationService,
    PrerequisiteReasonCode,
    PrerequisiteStatus,
)
from app.application.information_element_evidence_availability import (
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import SemanticMappingResolutionApplicationService
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    DemoFieldValueEvidenceSeeder,
)
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl


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


def test_supplier_legal_name_assesses_prerequisites_present(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        evidence_availability_results = _h4_service(session).evaluate(
            coverage_result=coverage_result
        )

    context_results = InformationElementContextAvailabilityApplicationService().compose(
        coverage_result=coverage_result, evidence_availability_results=evidence_availability_results
    )
    mapped_contexts = [r for r in context_results if r.coverage_status is CoverageStatus.MAPPED]
    assert len(mapped_contexts) == 1

    result = InformationElementDecisionPrerequisiteAssessmentApplicationService().assess(
        context=mapped_contexts[0]
    )

    assert result.prerequisite_status is PrerequisiteStatus.PREREQUISITES_PRESENT
    assert result.reason_code is PrerequisiteReasonCode.APPROVED_MAPPING_WITH_EVIDENCE_OBSERVED


def test_risk_event_severity_assesses_not_evaluable(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        coverage_result = _coverage_service(session).evaluate(
            blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID
        )
        evidence_availability_results = _h4_service(session).evaluate(
            coverage_result=coverage_result
        )

    context_results = InformationElementContextAvailabilityApplicationService().compose(
        coverage_result=coverage_result, evidence_availability_results=evidence_availability_results
    )
    unmapped_contexts = [r for r in context_results if r.coverage_status is CoverageStatus.UNMAPPED]
    assert len(unmapped_contexts) >= 1

    service = InformationElementDecisionPrerequisiteAssessmentApplicationService()
    results = [service.assess(context=context) for context in unmapped_contexts]

    assert all(r.prerequisite_status is PrerequisiteStatus.NOT_EVALUABLE for r in results)
    assert all(r.reason_code is PrerequisiteReasonCode.NO_APPROVED_MAPPING for r in results)
