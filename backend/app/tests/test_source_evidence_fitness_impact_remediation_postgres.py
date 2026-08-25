"""Postgres-backed acceptance evidence for Gate T impact/remediation
(CDD-031 §15-§16, §28; Gate T Artifact Authorization §9, item 31). This
service performs zero I/O (CDD-031 §15) -- what genuinely needs real
PostgreSQL coverage is the owning-`ConceptRequirement`/relationship-context
traversal against a real, Postgres-sourced `Blueprint`, not the freshness/
conflict computation (already proven against real evidence in
`test_source_evidence_fitness_evaluation_postgres.py`). Fitness results here
are therefore constructed directly, pinned to the real "Supplier Legal Name"
`information_element_requirement_id` resolved from the real, unmodified
mapping chain -- deliberately not derived by re-running fitness evaluation
against the shared demo tenant's evidence, which other already-frozen tests
elsewhere in this suite (e.g. H4's own `test_persisted_multiplicity_full_provenance`)
permanently and legitimately mutate to be conflicting for the remainder of
any shared test session, by design of this repository's append-only,
session-scoped Postgres fixture."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.blueprint_service import BlueprintApplicationService
from app.application.semantic_coverage_evaluation import (
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import (
    SemanticMappingResolutionApplicationService,
)
from app.application.source_evidence_fitness_evaluation import (
    EvidenceFitnessStatus,
    InformationElementEvidenceFitnessResult,
)
from app.application.source_evidence_fitness_impact_remediation import (
    EvidenceFitnessRemediationAction,
    SourceEvidenceFitnessImpactRemediationApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.domain.blueprint import Blueprint
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    DemoFieldValueEvidenceSeeder,
    DemoFieldValueEvidenceSeedSummary,
)
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _seed(factory: "sessionmaker[Session]") -> DemoFieldValueEvidenceSeedSummary:
    with factory() as session:
        summary = DemoFieldValueEvidenceSeeder(session).seed()
        session.commit()
    return summary


def _blueprint(session: Session) -> Blueprint:
    blueprint = BlueprintApplicationService(
        repository=BlueprintRepositoryImpl(session)
    ).get_approved_by_name(CANONICAL_BLUEPRINT_NAME)
    assert blueprint is not None
    return blueprint


def _supplier_legal_name_requirement_id(
    session: Session, summary: DemoFieldValueEvidenceSeedSummary
) -> UUID:
    coverage_result = SemanticCoverageEvaluationApplicationService(
        blueprint_service=BlueprintApplicationService(repository=BlueprintRepositoryImpl(session)),
        resolver=SemanticMappingResolutionApplicationService(
            repository=SemanticMappingRepositoryImpl(session)
        ),
    ).evaluate(blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID)
    matches = [
        element
        for element in coverage_result.information_element_results
        if element.resolution is not None
        and element.resolution.source_field_id == summary.source_field_id
    ]
    assert len(matches) == 1
    return matches[0].information_element_requirement_id


def _fitness_result(
    *, information_element_requirement_id: UUID, fitness_status: EvidenceFitnessStatus | None
) -> InformationElementEvidenceFitnessResult:
    return InformationElementEvidenceFitnessResult(
        information_element_requirement_id=information_element_requirement_id,
        source_field_id=information_element_requirement_id,
        fitness_status=fitness_status,
    )


def test_h3_acceptance_supplier_legal_name_fit_yields_no_remediation_with_real_context(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        requirement_id = _supplier_legal_name_requirement_id(session, summary)
        blueprint = _blueprint(session)
        fitness_results = (
            _fitness_result(
                information_element_requirement_id=requirement_id,
                fitness_status=EvidenceFitnessStatus.FIT,
            ),
        )
        contexts = SourceEvidenceFitnessImpactRemediationApplicationService().derive(
            fitness_results=fitness_results, blueprint=blueprint
        )

    assert len(contexts) == 1
    supplier_legal_name = contexts[0]
    assert supplier_legal_name.remediation_action is None

    supplier_concept = next(
        concept
        for concept in blueprint.concept_requirements
        if concept.concept_requirement_id.value == supplier_legal_name.concept_requirement_id
    )
    assert supplier_concept.entity_type_id.value == supplier_legal_name.entity_type_id


def test_derivation_is_deterministic_across_repeated_calls(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        requirement_id = _supplier_legal_name_requirement_id(session, summary)
        blueprint = _blueprint(session)
        fitness_results = (
            _fitness_result(
                information_element_requirement_id=requirement_id,
                fitness_status=EvidenceFitnessStatus.CONFLICTING,
            ),
        )
        service = SourceEvidenceFitnessImpactRemediationApplicationService()
        first = service.derive(fitness_results=fitness_results, blueprint=blueprint)
        second = service.derive(fitness_results=fitness_results, blueprint=blueprint)

    assert first == second


def test_stale_evaluation_yields_refresh_source_evidence_recommendation(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    summary = _seed(factory)

    with factory() as session:
        requirement_id = _supplier_legal_name_requirement_id(session, summary)
        blueprint = _blueprint(session)
        fitness_results = (
            _fitness_result(
                information_element_requirement_id=requirement_id,
                fitness_status=EvidenceFitnessStatus.STALE,
            ),
        )
        contexts = SourceEvidenceFitnessImpactRemediationApplicationService().derive(
            fitness_results=fitness_results, blueprint=blueprint
        )

    assert (
        contexts[0].remediation_action is EvidenceFitnessRemediationAction.REFRESH_SOURCE_EVIDENCE
    )
