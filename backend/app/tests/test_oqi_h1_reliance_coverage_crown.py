"""CDD-047 Artifact Authorization row 9: the H1 crown proofs, real
PostgreSQL, exercised through the actual integration point
(`OqiBusinessImpactService.evaluate_reliance_for_subject`), never a raw
repository call in isolation.

Proves: PARTIAL REQUIRED COVERAGE ≠ SUPPORTED (CDD-047 §20); the full §18
backward-compatibility truth table as executable no-policy-branch identity
proofs; NO FINDINGS ≠ TRUSTED unaffected; §15's relationship-anchor-never-
achieves-True boundary."""

# isort: skip_file
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_business_impact_service import OqiBusinessImpactService
from app.application.oqi_quality_evaluation_service import OqiQualityEvaluationService
from app.domain.oqi.quality_rule import QualityRuleStatus
from app.domain.oqi_business_impact.reliance import ReasonCode, RelianceState
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_quality_coverage.policy import (
    CoverageDimension,
    create_quality_coverage_policy,
)
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OqiQualityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import (
    OqiQualityRuleRepositoryImpl,
)
from app.tests.test_oqi_ontology_impact_postgres import _entity, _resolve_entity
from app.tests.test_oqi_quality_postgres import (
    _admit_evidence,
    _completeness_rule,
    _seed_field as _seed_oqi1_field,
    _subject,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine)


@pytest.fixture()
def session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with factory() as session:
        yield session
        session.rollback()


def _seed_covered_completeness_entity(session: Session, *, tenant_id: str) -> UUID:
    """Seeds one ENTITY with a real, persisted, SATISFIED OQI1 Completeness
    evaluation -- never a raw evaluation-table insert -- so COMPLETENESS
    coverage is genuinely proven, not asserted."""
    source_object_id, source_field_id = _seed_oqi1_field(session, tenant_id=tenant_id)
    entity_id = _entity(session, tenant_id=tenant_id, name="crown-entity")
    _resolve_entity(
        session, tenant_id=tenant_id, source_object_id=source_object_id, entity_id=entity_id
    )

    quality_condition_id = f"condition-{uuid4()}"
    rule = _completeness_rule(quality_condition_id=quality_condition_id)
    rule = type(rule)(
        rule_id=rule.rule_id,
        quality_condition_id=rule.quality_condition_id,
        version=rule.version,
        dimension=rule.dimension,
        finding_type=rule.finding_type,
        validity_primitive=rule.validity_primitive,
        information_element_requirement_id=rule.information_element_requirement_id,
        rule_parameters=rule.rule_parameters,
        status=QualityRuleStatus.ACTIVE,
        created_by=rule.created_by,
        created_on=rule.created_on,
    )
    OqiQualityRuleRepositoryImpl(session).create(rule)
    session.flush()

    _admit_evidence(
        session,
        source_field_id=source_field_id,
        source_record_reference="REC-1",
        observed_representation="US",
    )
    session.flush()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="REC-1",
    )
    evaluation_service = OqiQualityEvaluationService(
        evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
    )
    evaluation = evaluation_service.evaluate_current_state(rule=rule, subject=subject)
    assert evaluation is not None, "seeding fixture must produce a real, persisted evaluation"
    session.flush()
    return entity_id


# ---------------------------------------------------------------------
# CDD-047 §20: PARTIAL REQUIRED COVERAGE ≠ SUPPORTED (the crown proof).
# ---------------------------------------------------------------------


def test_crown_partial_required_coverage_never_yields_supported(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    entity_id = _seed_covered_completeness_entity(session, tenant_id=tenant_id)

    # ACTIVE policy requires all three currently-implemented dimensions;
    # only COMPLETENESS has been genuinely evaluated (seeded above).
    policy = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        required_dimensions=frozenset(
            {
                CoverageDimension.COMPLETENESS,
                CoverageDimension.VALIDITY,
                CoverageDimension.CONSISTENCY,
            }
        ),
        created_by="steward",
        created_on=NOW,
    )
    OqiQualityCoveragePolicyRepositoryImpl(session).insert_policy(policy)
    session.flush()

    evaluation = OqiBusinessImpactService(session).evaluate_reliance_for_subject(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        evaluated_at=NOW,
    )

    assert evaluation.state is RelianceState.RELIANCE_UNKNOWN, (
        "RELIANCE_SUPPORTED is FORBIDDEN when an ACTIVE policy's required "
        "coverage is only partially satisfied (CDD-047 §20)"
    )
    assert ReasonCode.INSUFFICIENT_QUALITY_COVERAGE in evaluation.reason_codes


def test_crown_complete_required_coverage_reproduces_legacy_supported_shape(
    session: Session,
) -> None:
    """A policy requiring only the one dimension that is genuinely
    covered, with zero open Findings, must reach RELIANCE_SUPPORTED --
    proving the ALL-of semantics is satisfiable, not merely never-True."""
    tenant_id = f"tenant-{uuid4()}"
    entity_id = _seed_covered_completeness_entity(session, tenant_id=tenant_id)

    policy = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
        created_by="steward",
        created_on=NOW,
    )
    OqiQualityCoveragePolicyRepositoryImpl(session).insert_policy(policy)
    session.flush()

    evaluation = OqiBusinessImpactService(session).evaluate_reliance_for_subject(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        evaluated_at=NOW,
    )
    assert evaluation.state is RelianceState.RELIANCE_SUPPORTED
    assert evaluation.reason_codes == ()


def test_crown_unsupported_required_dimension_blocks_supported(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    entity_id = _seed_covered_completeness_entity(session, tenant_id=tenant_id)

    policy = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS, CoverageDimension.ACCURACY}),
        created_by="steward",
        created_on=NOW,
    )
    OqiQualityCoveragePolicyRepositoryImpl(session).insert_policy(policy)
    session.flush()

    evaluation = OqiBusinessImpactService(session).evaluate_reliance_for_subject(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        evaluated_at=NOW,
    )
    assert evaluation.state is RelianceState.RELIANCE_UNKNOWN


# ---------------------------------------------------------------------
# CDD-047 §18: backward-compatibility truth table, no-policy branch.
# ---------------------------------------------------------------------


def test_no_policy_no_evaluation_yields_legacy_unknown(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    entity_id = _entity(session, tenant_id=tenant_id, name="bare-entity")
    session.flush()

    evaluation = OqiBusinessImpactService(session).evaluate_reliance_for_subject(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        evaluated_at=NOW,
    )
    assert evaluation.state is RelianceState.RELIANCE_UNKNOWN
    assert ReasonCode.INSUFFICIENT_QUALITY_COVERAGE in evaluation.reason_codes


def test_no_policy_with_evaluation_no_findings_yields_legacy_supported(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    entity_id = _seed_covered_completeness_entity(session, tenant_id=tenant_id)

    # No ACTIVE QualityCoveragePolicy exists for this subject at all.
    evaluation = OqiBusinessImpactService(session).evaluate_reliance_for_subject(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        evaluated_at=NOW,
    )
    assert evaluation.state is RelianceState.RELIANCE_SUPPORTED
    assert evaluation.reason_codes == ()


# ---------------------------------------------------------------------
# NO FINDINGS ≠ TRUSTED (unaffected by H1).
# ---------------------------------------------------------------------


def test_no_findings_not_trusted_when_zero_evaluations_ever_ran(session: Session) -> None:
    """A subject with genuinely zero Findings and zero evaluations must
    never read RELIANCE_SUPPORTED -- proven independent of any coverage
    policy, exactly as CDD-044 §8.3(a) already established."""
    tenant_id = f"tenant-{uuid4()}"
    entity_id = _entity(session, tenant_id=tenant_id, name="untouched-entity")
    session.flush()

    evaluation = OqiBusinessImpactService(session).evaluate_reliance_for_subject(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        evaluated_at=NOW,
    )
    assert evaluation.state is not RelianceState.RELIANCE_SUPPORTED
    assert evaluation.state is RelianceState.RELIANCE_UNKNOWN


# ---------------------------------------------------------------------
# CDD-047 §15: RELATIONSHIP-anchored ACTIVE policy never achieves True.
# ---------------------------------------------------------------------


def test_relationship_active_policy_never_achieves_supported(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    relationship_id = uuid4()  # no real InstitutionalRelationship row needed --
    # coverage for RELATIONSHIP subjects is proven unconditionally False
    # regardless of whether the anchor itself resolves to a real row,
    # since no evidence-resolution mechanism exists for it at all (CDD-047 §15).

    policy = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.RELATIONSHIP,
        ontology_element_id=relationship_id,
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
        created_by="steward",
        created_on=NOW,
    )
    OqiQualityCoveragePolicyRepositoryImpl(session).insert_policy(policy)
    session.flush()

    evaluation = OqiBusinessImpactService(session).evaluate_reliance_for_subject(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.RELATIONSHIP,
        ontology_element_id=relationship_id,
        evaluated_at=NOW,
    )
    assert evaluation.state is RelianceState.RELIANCE_UNKNOWN
    assert ReasonCode.INSUFFICIENT_QUALITY_COVERAGE in evaluation.reason_codes


def test_relationship_no_policy_preserves_legacy_behavior(session: Session) -> None:
    """No ACTIVE policy -> unaffected by H1 at all for a RELATIONSHIP
    subject, exactly as for ENTITY (CDD-047 §15's no-policy case)."""
    tenant_id = f"tenant-{uuid4()}"
    relationship_id = uuid4()

    evaluation = OqiBusinessImpactService(session).evaluate_reliance_for_subject(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.RELATIONSHIP,
        ontology_element_id=relationship_id,
        evaluated_at=NOW,
    )
    assert evaluation.state is RelianceState.RELIANCE_UNKNOWN
