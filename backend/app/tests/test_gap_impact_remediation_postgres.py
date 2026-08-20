"""Postgres-backed acceptance evidence for Gate J J1/J2 (CDD-021 §16, §28
items 2, 8; J1/J2 Gap Impact Context and Remediation Artifact Authorization
§8). Composes the real, unmodified `BlueprintApplicationService`, the real,
unmodified `SemanticMappingResolutionApplicationService`, and the real,
unmodified `SemanticCoverageEvaluationApplicationService` (exactly as CDD-020
I1's own Postgres test already does) against the existing, unmodified H3
fixture, then passes the resulting real `SemanticCoverageEvaluationResult`
and `Blueprint` into the new `GapImpactRemediationApplicationService.derive(...)`,
proving the H3 deterministic demonstration ("Supplier Legal Name" ->
no remediation; "Risk Event Severity" -> `REVIEW_SEMANTIC_MAPPING` with the
real, governed `Region --exposedTo--> Risk Event` relationship context) and
determinism against real PostgreSQL.
"""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.application.gap_impact_remediation import (
    Direction,
    GapImpactRemediationApplicationService,
    RemediationAction,
)
from app.application.semantic_coverage_evaluation import (
    SemanticCoverageEvaluationApplicationService,
    SemanticCoverageEvaluationResult,
)
from app.application.semantic_mapping_resolution import (
    SemanticMappingResolutionApplicationService,
)
from app.domain.blueprint import Blueprint
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


def _blueprint(session: Session) -> Blueprint:
    blueprint = BlueprintApplicationService(
        repository=BlueprintRepositoryImpl(session)
    ).get_approved_by_name(CANONICAL_BLUEPRINT_NAME)
    assert blueprint is not None
    return blueprint


def _coverage_result(session: Session, tenant_id: str) -> SemanticCoverageEvaluationResult:
    return SemanticCoverageEvaluationApplicationService(
        blueprint_service=BlueprintApplicationService(repository=BlueprintRepositoryImpl(session)),
        resolver=SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        ),
    ).evaluate(blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=tenant_id)


def test_h3_acceptance_supplier_mapped_no_remediation_risk_event_unmapped_remediation(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        coverage_result = _coverage_result(session, summary.tenant_id)
        blueprint = _blueprint(session)
        results = GapImpactRemediationApplicationService().derive(
            coverage_result=coverage_result, blueprint=blueprint
        )

    by_id = {
        result.coverage_result.information_element_requirement_id: result for result in results
    }

    supplier_legal_name = by_id[summary.information_element_requirement_id]
    assert supplier_legal_name.remediation_action is None
    supplier_concept = next(
        concept
        for concept in blueprint.concept_requirements
        if concept.concept_requirement_id.value == supplier_legal_name.concept_requirement_id
    )
    assert supplier_concept.entity_type_id.value == supplier_legal_name.entity_type_id

    risk_event_severity_results = [
        result
        for result in results
        if result.coverage_result.information_element_requirement_id
        != summary.information_element_requirement_id
    ]
    assert len(risk_event_severity_results) == 1
    risk_event_severity = risk_event_severity_results[0]
    assert risk_event_severity.remediation_action is RemediationAction.REVIEW_SEMANTIC_MAPPING

    risk_event_concept = next(
        concept
        for concept in blueprint.concept_requirements
        if concept.concept_requirement_id.value == risk_event_severity.concept_requirement_id
    )
    assert risk_event_concept.entity_type_id.value == risk_event_severity.entity_type_id

    region_concept = next(
        concept
        for concept in blueprint.concept_requirements
        for relationship in concept.relationship_requirements
        if relationship.target_entity_type_id.value == risk_event_severity.entity_type_id
    )
    assert any(
        entry.direction is Direction.INCOMING
        and entry.other_entity_type_id == region_concept.entity_type_id.value
        for entry in risk_event_severity.relationship_context
    )


def test_derivation_is_deterministic_across_repeated_calls(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        coverage_result = _coverage_result(session, summary.tenant_id)
        blueprint = _blueprint(session)
        service = GapImpactRemediationApplicationService()
        first = service.derive(coverage_result=coverage_result, blueprint=blueprint)
        second = service.derive(coverage_result=coverage_result, blueprint=blueprint)

    assert first == second
