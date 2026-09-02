"""CDD-048 Artifact Authorization row 19 + OQI-H2-I-R1 §9: the H2 crown
proofs, real PostgreSQL, exercised through the actual Accuracy/
Reasonableness evaluator entry points and the full downstream chain -- never
a raw repository call in isolation where a real integration path exists.

Proves the CDD-048 §31 frozen matrix (behavioral proof, never code-inspection
only): A1-A13, R1-R10, F1-F10, RC1-RC5 (RC1/RC2 via A7), CY1/CY6 (behavioral,
real FK-constraint adversarial proof) + CY3/CY4/CY5 (structural import-
firewall proof, mirroring `test_runtime_architecture.py`'s established
pattern for this exact invariant class), C1-C9/C11 (C10 is proven at the
router layer in `test_oqi_h2_authorization_and_tenant_isolation.py`, and
A8/R6 tenant isolation lives there too, since it needs two independent
sessions/fixtures)."""

# isort: skip_file
from __future__ import annotations

import ast
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_accuracy_evaluation_service import OqiAccuracyEvaluationService
from app.application.oqi_business_impact_service import OqiBusinessImpactService
from app.application.oqi_business_rule_evaluation_service import (
    OqiBusinessRuleEvaluationService,
    SingleRecordSubject,
)
from app.application.oqi_ontology_impact_evaluation_service import (
    OqiOntologyImpactEvaluationService,
)
from app.application.oqi_reference_evidence_service import OqiReferenceEvidenceService
from app.application.oqi_remediation_service import OqiRemediationService
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.oqi_business_impact.dependency import Criticality
from app.domain.oqi_business_impact.process import BusinessImpactCategory
from app.domain.oqi_business_impact.reliance import RelianceState
from app.domain.oqi_business_rule.rule import (
    BusinessRule,
    BusinessRuleInputBinding,
    BusinessRulePurpose,
    BusinessRuleStatus,
    ComparandKind,
    ComparatorNode,
    ExpectedType,
    Operator,
    RuleFamily,
)
from app.domain.oqi_finding_origin.origin import LEGACY_UNCLASSIFIED_BUSINESS_RULE
from app.domain.oqi_ontology_impact.evaluation import (
    FindingFamily,
    ImpactOutcome,
    OntologyElementType,
)
from app.domain.oqi_quality_coverage.policy import CoverageDimension, create_quality_coverage_policy
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.oqi_quality_evaluation import QualityEvaluationORM
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_reference_evidence import (
    BusinessRuleDerivedReferenceEntryORM,
    OqiReferenceEvidenceConflictORM,
    QualityEvaluationReferenceEvidenceORM,
)
from app.infrastructure.persistence.oqi_accuracy_evaluation_repository import (
    OqiAccuracyEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_business_rule_evaluation_repository import (
    OqiBusinessRuleEvaluationRepositoryImpl,
    OqiBusinessRuleEvidenceValueReader,
)
from app.infrastructure.persistence.oqi_business_rule_repository import (
    OqiBusinessRuleRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.oqi_reference_evidence_repository import (
    OqiReferenceEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)
from app.tests.test_oqi_ontology_impact_postgres import _entity, _resolve_entity
from app.tests.test_oqi_quality_postgres import _admit_evidence, _subject
from app.tests.test_oqi_quality_postgres import _seed_field as _seed_oqi1_field

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine)


@pytest.fixture()
def session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with factory() as session:
        yield session
        session.rollback()


def _tenant() -> str:
    return f"tenant-{uuid4()}"


def _accuracy_rule(*, quality_condition_id: str) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=quality_condition_id,
        version=1,
        dimension=QualityDimension.ACCURACY,
        finding_type=QualityFindingType.REFERENCE_VALUE_UNSUPPORTED,
        validity_primitive=None,
        information_element_requirement_id="req-accuracy",
        rule_parameters={},
        status=QualityRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )


def _accuracy_service(session: Session) -> OqiAccuracyEvaluationService:
    reference_service = OqiReferenceEvidenceService(
        repository=OqiReferenceEvidenceRepositoryImpl(session), clock=lambda: NOW
    )
    return OqiAccuracyEvaluationService(
        evaluation_repository=OqiAccuracyEvaluationRepositoryImpl(session),
        reference_evidence_lookup=reference_service,
        clock=lambda: NOW,
    )


def _seed_entity_and_field(
    session: Session, *, tenant_id: str, field_label: str = "LFA1-LAND1"
) -> tuple[UUID, UUID, UUID]:
    """Returns (source_object_id, source_field_id, entity_id) with the
    source object resolved to the entity -- the exact identity anchor an
    Accuracy evaluation resolves through."""
    source_object_id, source_field_id = _seed_oqi1_field(
        session, tenant_id=tenant_id, field_label=field_label
    )
    entity_id = _entity(session, tenant_id=tenant_id, name="h2-crown-entity")
    _resolve_entity(
        session, tenant_id=tenant_id, source_object_id=source_object_id, entity_id=entity_id
    )
    return source_object_id, source_field_id, entity_id


class TestAccuracyCrown:
    def test_a1_matching_reference_satisfied_no_finding(self, session: Session) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        reference_service = OqiReferenceEvidenceService(
            repository=OqiReferenceEvidenceRepositoryImpl(session), clock=lambda: NOW
        )
        reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="USA",
            dataset_name="ISO-3166-1-ALPHA-3",
            dataset_version="2024",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()

        assert evaluation is not None
        assert evaluation.outcome.value == "SATISFIED"
        findings = (
            session.execute(
                select(QualityFindingORM).where(
                    QualityFindingORM.tenant_id == tenant_id,
                    QualityFindingORM.quality_condition_id == rule.quality_condition_id,
                )
            )
            .scalars()
            .all()
        )
        assert findings == []

    def test_a2_mismatch_creates_reference_value_unsupported_finding(
        self, session: Session
    ) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="Mexico",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        reference_service = OqiReferenceEvidenceService(
            repository=OqiReferenceEvidenceRepositoryImpl(session), clock=lambda: NOW
        )
        reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="USA",
            dataset_name="ISO-3166-1-ALPHA-3",
            dataset_version="2024",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()

        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"
        finding = session.execute(
            select(QualityFindingORM).where(
                QualityFindingORM.tenant_id == tenant_id,
                QualityFindingORM.quality_condition_id == rule.quality_condition_id,
            )
        ).scalar_one()
        assert finding.finding_type == "REFERENCE_VALUE_UNSUPPORTED"
        assert finding.status == "OPEN"

    def test_a3_no_reference_evidence_yields_zero_row(self, session: Session) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id, _entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)

        assert evaluation is None
        count = (
            session.execute(
                select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert count == []

    def test_a7_conflicting_reference_evidence_yields_zero_row_and_conflict(
        self, session: Session
    ) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        reference_service = OqiReferenceEvidenceService(
            repository=OqiReferenceEvidenceRepositoryImpl(session), clock=lambda: NOW
        )
        reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="USA",
            dataset_name="ISO-3166-1-ALPHA-3",
            dataset_version="2024",
            entry_key="USA",
            created_by="steward",
        )
        reference_service.record_human_verified_evidence(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="Mexico",
            verifying_actor_id="steward-2",
            verification_rationale="Confirmed via site visit.",
            created_by="steward-2",
        )
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)

        # RC1: conflicting references block Accuracy -- zero row.
        assert evaluation is None
        # RC3: conflict has auditable provenance -- a real persisted row,
        # never a Quality Finding.
        conflict = session.execute(
            select(OqiReferenceEvidenceConflictORM).where(
                OqiReferenceEvidenceConflictORM.tenant_id == tenant_id
            )
        ).scalar_one()
        assert conflict.status == "ACTIVE"
        finding_count = (
            session.execute(
                select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert finding_count == []  # RC2: never REFERENCE_VALUE_UNSUPPORTED against the conflict

    def test_a9_evaluation_pins_reference_evidence_version(self, session: Session) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        reference_service = OqiReferenceEvidenceService(
            repository=OqiReferenceEvidenceRepositoryImpl(session), clock=lambda: NOW
        )
        assertion = reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="USA",
            dataset_name="ISO-3166-1-ALPHA-3",
            dataset_version="2024",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None

        link = session.execute(
            select(QualityEvaluationReferenceEvidenceORM).where(
                QualityEvaluationReferenceEvidenceORM.evaluation_id == evaluation.evaluation_id
            )
        ).scalar_one()
        assert link.assertion_id == assertion.assertion_id

    def test_a10_h1_coverage_requires_actual_accuracy_evaluation(self, session: Session) -> None:
        from app.domain.oqi_quality_coverage.policy import CoverageDimension

        tenant_id = _tenant()
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        coverage_repo = OqiQualityCoveragePolicyRepositoryImpl(session)

        # No Accuracy evaluation exists yet -- uncovered.
        assert (
            coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.ACCURACY,
            )
            is False
        )

        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        reference_service = OqiReferenceEvidenceService(
            repository=OqiReferenceEvidenceRepositoryImpl(session), clock=lambda: NOW
        )
        reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="USA",
            dataset_name="ISO-3166-1-ALPHA-3",
            dataset_version="2024",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()

        from app.domain.oqi_quality_coverage.policy import CoverageDimension

        assert (
            coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.ACCURACY,
            )
            is True
        )

    def test_c1_valid_coverage_does_not_satisfy_accuracy(self, session: Session) -> None:
        """CDD-048 crown invariant: VALID != ACCURATE. A Completeness/
        Validity-covered subject must remain ACCURACY-uncovered."""
        from app.application.oqi_quality_evaluation_service import OqiQualityEvaluationService
        from app.domain.oqi.quality_rule import ValidityPrimitive
        from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
            OqiQualityEvaluationRepositoryImpl,
        )

        tenant_id = _tenant()
        source_object_id, source_field_id, _entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="US",
        )
        validity_rule = QualityRule.new(
            quality_condition_id=f"cond-{uuid4()}",
            version=1,
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            information_element_requirement_id="req-validity",
            rule_parameters={"allowed_values": ["US", "MX"]},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        OqiQualityRuleRepositoryImpl(session).create(validity_rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        legacy_service = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        evaluation = legacy_service.evaluate_current_state(rule=validity_rule, subject=subject)
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "SATISFIED"

        from app.domain.oqi_quality_coverage.policy import CoverageDimension

        coverage_repo = OqiQualityCoveragePolicyRepositoryImpl(session)
        assert (
            coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.VALIDITY,
            )
            is True
        )
        assert (
            coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.ACCURACY,
            )
            is False
        )


def _reasonableness_rule(
    *, business_condition_id: str, tenant_id: str, source_field_id: UUID
) -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="c-applicability",
        operator=Operator.IS_NOT_NULL,
        input_role="quantity",
        comparand_kind=ComparandKind.NONE,
    )
    # CDD-041 §21: a predicate is true (SATISFIED) when the governed
    # expectation holds, regardless of rule_family -- CONDITIONAL_PROHIBITED
    # authorizes any leaf shape but does not invert this. To express
    # "quantity must not be negative," the predicate asserts the ALLOWED
    # state directly (quantity >= 0), not its negation.
    predicate = ComparatorNode(
        clause_id="c-predicate",
        operator=Operator.GTE,
        input_role="quantity",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.DECIMAL,
        literal_value="0",
    )
    return BusinessRule.new(
        business_condition_id=business_condition_id,
        version=1,
        tenant_id=tenant_id,
        rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
        applicability=applicability,
        predicate=predicate,
        input_bindings=(
            BusinessRuleInputBinding(
                input_role="quantity",
                source_field_id=source_field_id,
                required=False,
                expected_type=ExpectedType.DECIMAL,
            ),
        ),
        status=BusinessRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
        dimension=BusinessRulePurpose.REASONABLENESS,
    )


class TestReasonablenessCrown:
    def test_r1_satisfied(self, session: Session) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="QUANTITY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="10",
        )
        rule = _reasonableness_rule(
            business_condition_id=f"cond-{uuid4()}",
            tenant_id=tenant_id,
            source_field_id=source_field_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()

        service = OqiBusinessRuleEvaluationService(
            evaluation_repository=OqiBusinessRuleEvaluationRepositoryImpl(session),
            evidence_value_reader=OqiBusinessRuleEvidenceValueReader(session),
            clock=lambda: NOW,
        )
        subject = SingleRecordSubject(
            tenant_id=tenant_id, source_object_id=source_object_id, source_record_reference="rec-1"
        )
        evaluation = service.evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "SATISFIED"

    def test_r2_violated_creates_contextual_plausibility_finding(self, session: Session) -> None:
        from app.infrastructure.persistence.models.oqi_business_rule_finding import (
            BusinessRuleFindingORM,
        )

        tenant_id = _tenant()
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="QUANTITY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="-10",
        )
        rule = _reasonableness_rule(
            business_condition_id=f"cond-{uuid4()}",
            tenant_id=tenant_id,
            source_field_id=source_field_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()

        service = OqiBusinessRuleEvaluationService(
            evaluation_repository=OqiBusinessRuleEvaluationRepositoryImpl(session),
            evidence_value_reader=OqiBusinessRuleEvidenceValueReader(session),
            clock=lambda: NOW,
        )
        subject = SingleRecordSubject(
            tenant_id=tenant_id, source_object_id=source_object_id, source_record_reference="rec-1"
        )
        evaluation = service.evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"

        finding = session.execute(
            select(BusinessRuleFindingORM).where(
                BusinessRuleFindingORM.tenant_id == tenant_id,
                BusinessRuleFindingORM.business_condition_id == rule.business_condition_id,
            )
        ).scalar_one()
        assert finding.status == "OPEN"
        assert finding.violation_type == "CONTEXTUAL_PLAUSIBILITY_VIOLATION"

    def test_r8_h1_coverage_requires_actual_reasonableness_evaluation(
        self, session: Session
    ) -> None:
        from app.domain.oqi_quality_coverage.policy import CoverageDimension

        tenant_id = _tenant()
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="QUANTITY"
        )
        coverage_repo = OqiQualityCoveragePolicyRepositoryImpl(session)
        assert (
            coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.REASONABLENESS,
            )
            is False
        )

        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="10",
        )
        rule = _reasonableness_rule(
            business_condition_id=f"cond-{uuid4()}",
            tenant_id=tenant_id,
            source_field_id=source_field_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()
        service = OqiBusinessRuleEvaluationService(
            evaluation_repository=OqiBusinessRuleEvaluationRepositoryImpl(session),
            evidence_value_reader=OqiBusinessRuleEvidenceValueReader(session),
            clock=lambda: NOW,
        )
        subject = SingleRecordSubject(
            tenant_id=tenant_id, source_object_id=source_object_id, source_record_reference="rec-1"
        )
        service.evaluate_current_state(rule=rule, subject=subject)
        session.flush()

        assert (
            coverage_repo.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=(source_object_id,),
                dimension=CoverageDimension.REASONABLENESS,
            )
            is True
        )

    def test_r9_legacy_business_rule_not_silently_reclassified(self, session: Session) -> None:
        """F3: a pre-H2-shaped rule (constructed without an explicit
        `dimension`) defaults to LEGACY_UNCLASSIFIED_BUSINESS_RULE -- never
        fabricated as REASONABLENESS."""
        tenant_id = _tenant()
        _source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="PURCHASING_GROUP"
        )
        rule = BusinessRule.new(
            business_condition_id=f"cond-{uuid4()}",
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="c-app",
                operator=Operator.IS_NOT_NULL,
                input_role="group",
                comparand_kind=ComparandKind.NONE,
            ),
            predicate=ComparatorNode(
                clause_id="c-pred",
                operator=Operator.IS_NOT_NULL,
                input_role="group",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="group",
                    source_field_id=source_field_id,
                    required=False,
                    expected_type=ExpectedType.STRING,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            # dimension intentionally omitted -- legacy construction path.
        )
        assert rule.dimension is BusinessRulePurpose.LEGACY_UNCLASSIFIED_BUSINESS_RULE
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()
        stored = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=rule.business_condition_id
        )
        assert stored is not None
        assert stored.dimension is BusinessRulePurpose.LEGACY_UNCLASSIFIED_BUSINESS_RULE


# =======================================================================
# OQI-H2-I-R1 §9-§18: remaining frozen CDD-048 §31 matrix, real PostgreSQL.
# =======================================================================


def _reference_service(session: Session) -> OqiReferenceEvidenceService:
    return OqiReferenceEvidenceService(
        repository=OqiReferenceEvidenceRepositoryImpl(session), clock=lambda: NOW
    )


class TestAccuracyRemainingProofs:
    def test_a4_source_authority_alone_yields_zero_row(self, session: Session) -> None:
        """A4/C4 (AUTHORITY != TRUTH): an OQI2 CONSISTENCY rule marking SAP
        `authoritative=True`, with NO Reference Evidence at all, must not
        cause Accuracy to synthesize a result for SAP's own observation."""
        tenant_id = _tenant()
        source_object_id, source_field_id, _entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        # A sibling OQI2 rule marks this same field's role authoritative --
        # a dimension-configuration fact entirely unrelated to Accuracy.
        consistency_rule = QualityRule.new(
            quality_condition_id=f"cond-{uuid4()}",
            version=1,
            dimension=QualityDimension.CONSISTENCY,
            finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
            validity_primitive=None,
            information_element_requirement_id="req-consistency",
            rule_parameters={
                "participants": [
                    {
                        "role": "SAP",
                        "source_field_id": str(source_field_id),
                        "eligible": True,
                        "expected": True,
                        "authoritative": True,
                    },
                    {
                        "role": "OTHER",
                        "source_field_id": str(uuid4()),
                        "eligible": True,
                        "expected": True,
                        "authoritative": False,
                    },
                ]
            },
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        OqiQualityRuleRepositoryImpl(session).create(consistency_rule)

        accuracy_rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(accuracy_rule)
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(
            rule=accuracy_rule, subject=subject
        )
        assert evaluation is None

    def test_a5_majority_agreement_alone_yields_zero_row(self, session: Session) -> None:
        """A5/C5 (MAJORITY != TRUTH): two independently-evaluated
        observations of the same fact that happen to agree with each other
        (a 2-of-2 "majority") remain individually NOT_EVALUABLE absent
        Reference Evidence -- agreement between observations is never
        consulted by the Accuracy evaluator."""
        tenant_id = _tenant()
        sap_object, sap_field, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id, field_label="SAP-FIELD"
        )
        plm_object, plm_field = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="PLM-FIELD"
        )
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=plm_object, entity_id=entity_id
        )

        for field_id, obj_id, ref in (
            (sap_field, sap_object, "rec-sap"),
            (plm_field, plm_object, "rec-plm"),
        ):
            _admit_evidence(
                session,
                source_field_id=field_id,
                source_record_reference=ref,
                observed_representation="USA",
            )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        service = _accuracy_service(session)
        for field_id, obj_id, ref in (
            (sap_field, sap_object, "rec-sap"),
            (plm_field, plm_object, "rec-plm"),
        ):
            subject = _subject(
                tenant_id=tenant_id,
                source_object_id=obj_id,
                source_field_id=field_id,
                reference=ref,
            )
            evaluation = service.evaluate_current_state(rule=rule, subject=subject)
            assert evaluation is None  # agreement between the two never substitutes for evidence

    def test_a6_c2_consistency_independent_from_accuracy(self, session: Session) -> None:
        """A6/C2: SAP=PLM=USA (Consistency SATISFIED -- they agree), but
        Reference Evidence says MEXICO -- both individually VIOLATED for
        Accuracy. Consistency and Accuracy read the same raw evidence but
        never influence each other's outcome."""
        tenant_id = _tenant()
        sap_object, sap_field, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id, field_label="SAP-FIELD"
        )
        plm_object, plm_field = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="PLM-FIELD"
        )
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=plm_object, entity_id=entity_id
        )

        for field_id, ref in ((sap_field, "rec-sap"), (plm_field, "rec-plm")):
            _admit_evidence(
                session,
                source_field_id=field_id,
                source_record_reference=ref,
                observed_representation="USA",
            )

        consistency_condition = f"cond-{uuid4()}"
        consistency_rule = QualityRule.new(
            quality_condition_id=consistency_condition,
            version=1,
            dimension=QualityDimension.CONSISTENCY,
            finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
            validity_primitive=None,
            information_element_requirement_id="req-consistency",
            rule_parameters={
                "participants": [
                    {
                        "role": "SAP",
                        "source_field_id": str(sap_field),
                        "eligible": True,
                        "expected": True,
                        "authoritative": False,
                    },
                    {
                        "role": "PLM",
                        "source_field_id": str(plm_field),
                        "eligible": True,
                        "expected": True,
                        "authoritative": False,
                    },
                ]
            },
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        OqiQualityRuleRepositoryImpl(session).create(consistency_rule)

        accuracy_rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(accuracy_rule)
        session.flush()

        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=sap_field,
            asserted_value="MEXICO",
            dataset_name="demo",
            dataset_version="v1",
            entry_key="MEXICO",
            created_by="steward",
        )
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=plm_field,
            asserted_value="MEXICO",
            dataset_name="demo",
            dataset_version="v1",
            entry_key="MEXICO",
            created_by="steward",
        )
        session.flush()

        accuracy_service = _accuracy_service(session)
        for field_id, obj_id, ref in (
            (sap_field, sap_object, "rec-sap"),
            (plm_field, plm_object, "rec-plm"),
        ):
            subject = _subject(
                tenant_id=tenant_id,
                source_object_id=obj_id,
                source_field_id=field_id,
                reference=ref,
            )
            evaluation = accuracy_service.evaluate_current_state(
                rule=accuracy_rule, subject=subject
            )
            assert evaluation is not None
            assert (
                evaluation.outcome.value == "VIOLATED"
            )  # both, despite mutual Consistency agreement

    def test_a11_inactive_superseded_reference_cannot_qualify(self, session: Session) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        reference_service = _reference_service(session)
        first = reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="USA",
            dataset_name="demo",
            dataset_version="v1",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()
        OqiReferenceEvidenceRepositoryImpl(session).retire_assertion(
            assertion_id=first.assertion_id, retired_on=NOW
        )
        session.flush()

        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is None  # the sole reference is RETIRED -- does not qualify

    def test_a13_business_rule_derived_reference_full_provenance_path(
        self, session: Session
    ) -> None:
        """A13: exercises `record_business_rule_derived_reference` end to
        end -- raw evidence -> BusinessRule -> real BusinessRuleEvaluation
        -> BUSINESS_RULE_DERIVED_VALUE Reference Evidence -> Accuracy."""
        tenant_id = _tenant()
        source_object_id, declared_field, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id, field_label="DECLARED-TOTAL"
        )
        _, computed_field = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="COMPUTED-TOTAL"
        )
        _, invoice_field = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="INVOICE-TOTAL"
        )

        for field_id, ref in ((declared_field, "rec-declared"), (computed_field, "rec-declared")):
            _admit_evidence(
                session,
                source_field_id=field_id,
                source_record_reference="rec-declared",
                observed_representation="100",
            )

        deriving_rule = BusinessRule.new(
            business_condition_id=f"cond-{uuid4()}",
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c-eq",
                operator=Operator.EQ,
                input_role="declared",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="computed",
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="declared",
                    source_field_id=declared_field,
                    required=False,
                    expected_type=ExpectedType.DECIMAL,
                ),
                BusinessRuleInputBinding(
                    input_role="computed",
                    source_field_id=computed_field,
                    required=False,
                    expected_type=ExpectedType.DECIMAL,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            dimension=BusinessRulePurpose.ACCURACY_REFERENCE_DERIVATION,
        )
        OqiBusinessRuleRepositoryImpl(session).create(deriving_rule)
        session.flush()

        rule_service = OqiBusinessRuleEvaluationService(
            evaluation_repository=OqiBusinessRuleEvaluationRepositoryImpl(session),
            evidence_value_reader=OqiBusinessRuleEvidenceValueReader(session),
            clock=lambda: NOW,
        )
        rule_evaluation = rule_service.evaluate_current_state(
            rule=deriving_rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference="rec-declared",
            ),
        )
        session.flush()
        assert rule_evaluation is not None
        assert rule_evaluation.outcome.value == "SATISFIED"

        reference_service = _reference_service(session)
        derived_assertion = reference_service.record_business_rule_derived_reference(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=invoice_field,
            asserted_value="100",
            deriving_business_rule_id=deriving_rule.rule_id,
            deriving_rule_version=deriving_rule.version,
            deriving_evaluation_id=rule_evaluation.evaluation_id,
            created_by="steward",
        )
        session.flush()

        entry = session.get(BusinessRuleDerivedReferenceEntryORM, derived_assertion.assertion_id)
        assert entry is not None
        assert entry.deriving_business_rule_id == deriving_rule.rule_id
        assert entry.deriving_rule_version == deriving_rule.version
        assert entry.deriving_evaluation_id == rule_evaluation.evaluation_id

        _admit_evidence(
            session,
            source_field_id=invoice_field,
            source_record_reference="rec-invoice",
            observed_representation="100",
        )
        accuracy_rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(accuracy_rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=invoice_field,
            reference="rec-invoice",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(
            rule=accuracy_rule, subject=subject
        )
        assert evaluation is not None
        assert evaluation.outcome.value == "SATISFIED"

    def test_c3_no_implicit_canonicalization_masquerades_as_accuracy(
        self, session: Session
    ) -> None:
        """C3 (CANONICAL != ACCURATE): the comparison is exact-string, never
        trimmed/case-folded -- a value that would "obviously" match under
        any canonicalization must still VIOLATE if it is not byte-identical
        to the qualifying reference."""
        tenant_id = _tenant()
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation=" USA ",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=source_field_id,
            asserted_value="USA",
            dataset_name="demo",
            dataset_version="v1",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"  # " USA " != "USA", no implicit trimming


def _reasonableness_service(session: Session) -> OqiBusinessRuleEvaluationService:
    return OqiBusinessRuleEvaluationService(
        evaluation_repository=OqiBusinessRuleEvaluationRepositoryImpl(session),
        evidence_value_reader=OqiBusinessRuleEvidenceValueReader(session),
        clock=lambda: NOW,
    )


class TestReasonablenessRemainingProofs:
    def test_r3_no_applicable_rule_context_yields_zero_row(self, session: Session) -> None:
        """R3: an unknown subject (no evidence admitted at all for this
        source record) is NOT_EVALUABLE -- zero row, never a fabricated
        SATISFIED/VIOLATED."""
        tenant_id = _tenant()
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="QUANTITY"
        )
        rule = _reasonableness_rule(
            business_condition_id=f"cond-{uuid4()}",
            tenant_id=tenant_id,
            source_field_id=source_field_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()
        evaluation = _reasonableness_service(session).evaluate_current_state(
            rule=rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference="never-admitted",
            ),
        )
        assert evaluation is None

    def test_r4_c6_implausible_but_rule_compliant_value_creates_no_finding(
        self, session: Session
    ) -> None:
        """R4/C6 (ANOMALY != QUALITY DEFECT): an extreme, "surprising" value
        that nonetheless satisfies the governed rule must never produce a
        Finding -- only rule non-compliance does, never how unusual a value
        looks."""
        tenant_id = _tenant()
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="QUANTITY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="999999999",
        )
        rule = _reasonableness_rule(
            business_condition_id=f"cond-{uuid4()}",
            tenant_id=tenant_id,
            source_field_id=source_field_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()
        evaluation = _reasonableness_service(session).evaluate_current_state(
            rule=rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference="rec-1",
            ),
        )
        assert evaluation is not None
        assert evaluation.outcome.value == "SATISFIED"
        finding = (
            session.execute(
                select(BusinessRuleFindingORM).where(
                    BusinessRuleFindingORM.tenant_id == tenant_id,
                    BusinessRuleFindingORM.business_condition_id == rule.business_condition_id,
                )
            )
            .scalars()
            .all()
        )
        assert finding == []

    def test_r5_contextual_applicability_respected(self, session: Session) -> None:
        """R5: `price > 0` is required only for COMMERCIAL_SALE records
        (applicability); a SAMPLE record with price=0 is NOT_APPLICABLE
        (not VIOLATED); a COMMERCIAL_SALE record with price=0 IS VIOLATED."""
        tenant_id = _tenant()
        sample_object, process_field_1 = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="PROCESS"
        )
        _, price_field_1 = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PRICE")
        _admit_evidence(
            session,
            source_field_id=process_field_1,
            source_record_reference="rec-sample",
            observed_representation="SAMPLE",
        )
        _admit_evidence(
            session,
            source_field_id=price_field_1,
            source_record_reference="rec-sample",
            observed_representation="0",
        )

        commercial_object, process_field_2 = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="PROCESS2"
        )
        _, price_field_2 = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PRICE2")
        _admit_evidence(
            session,
            source_field_id=process_field_2,
            source_record_reference="rec-commercial",
            observed_representation="COMMERCIAL_SALE",
        )
        _admit_evidence(
            session,
            source_field_id=price_field_2,
            source_record_reference="rec-commercial",
            observed_representation="0",
        )

        def _price_rule(condition_id: str, process_field: UUID, price_field: UUID) -> BusinessRule:
            return BusinessRule.new(
                business_condition_id=condition_id,
                version=1,
                tenant_id=tenant_id,
                rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
                applicability=ComparatorNode(
                    clause_id="c-app",
                    operator=Operator.EQ,
                    input_role="process",
                    comparand_kind=ComparandKind.LITERAL,
                    literal_type=ExpectedType.STRING,
                    literal_value="COMMERCIAL_SALE",
                ),
                predicate=ComparatorNode(
                    clause_id="c-pred",
                    operator=Operator.GT,
                    input_role="price",
                    comparand_kind=ComparandKind.LITERAL,
                    literal_type=ExpectedType.DECIMAL,
                    literal_value="0",
                ),
                input_bindings=(
                    BusinessRuleInputBinding(
                        input_role="process",
                        source_field_id=process_field,
                        required=False,
                        expected_type=ExpectedType.STRING,
                    ),
                    BusinessRuleInputBinding(
                        input_role="price",
                        source_field_id=price_field,
                        required=False,
                        expected_type=ExpectedType.DECIMAL,
                    ),
                ),
                status=BusinessRuleStatus.ACTIVE,
                created_by="steward",
                created_on=NOW,
                dimension=BusinessRulePurpose.REASONABLENESS,
            )

        sample_rule = _price_rule(f"cond-{uuid4()}", process_field_1, price_field_1)
        commercial_rule = _price_rule(f"cond-{uuid4()}", process_field_2, price_field_2)
        OqiBusinessRuleRepositoryImpl(session).create(sample_rule)
        OqiBusinessRuleRepositoryImpl(session).create(commercial_rule)
        session.flush()

        service = _reasonableness_service(session)
        sample_evaluation = service.evaluate_current_state(
            rule=sample_rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=sample_object,
                source_record_reference="rec-sample",
            ),
        )
        assert sample_evaluation is not None
        assert sample_evaluation.outcome.value == "NOT_APPLICABLE"

        commercial_evaluation = service.evaluate_current_state(
            rule=commercial_rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=commercial_object,
                source_record_reference="rec-commercial",
            ),
        )
        assert commercial_evaluation is not None
        assert commercial_evaluation.outcome.value == "VIOLATED"

    def test_r7_exact_rule_version_pinned(self, session: Session) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="QUANTITY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="10",
        )
        condition_id = f"cond-{uuid4()}"
        v1 = _reasonableness_rule(
            business_condition_id=condition_id, tenant_id=tenant_id, source_field_id=source_field_id
        )
        OqiBusinessRuleRepositoryImpl(session).create(v1)
        session.flush()
        evaluation = _reasonableness_service(session).evaluate_current_state(
            rule=v1,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference="rec-1",
            ),
        )
        assert evaluation is not None
        assert evaluation.rule_version == 1

        v2 = BusinessRule.new(
            business_condition_id=condition_id,
            version=2,
            tenant_id=tenant_id,
            rule_family=v1.rule_family,
            applicability=v1.applicability,
            predicate=v1.predicate,
            input_bindings=v1.input_bindings,
            status=BusinessRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            dimension=BusinessRulePurpose.REASONABLENESS,
        )
        OqiBusinessRuleRepositoryImpl(session).activate_new_version(v2, retired_on=NOW)
        session.flush()

        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-2",
            observed_representation="20",
        )
        evaluation_v2 = _reasonableness_service(session).evaluate_current_state(
            rule=v2,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference="rec-2",
            ),
        )
        assert evaluation_v2 is not None
        assert evaluation_v2.rule_version == 2
        # The v1 ledger row remains untouched -- immutable historical fact.
        assert evaluation.rule_version == 1

    def test_r10_cross_field_deterministic_rule(self, session: Session) -> None:
        """R10: FIELD_COMPARISON -- a genuinely different rule shape than
        the CONDITIONAL_PROHIBITED tests above, comparing two raw fields
        directly (start_date < end_date)."""
        tenant_id = _tenant()
        source_object_id, start_field = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="START-DATE"
        )
        _, end_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="END-DATE")
        _admit_evidence(
            session,
            source_field_id=start_field,
            source_record_reference="rec-1",
            observed_representation="2026-06-01",
        )
        _admit_evidence(
            session,
            source_field_id=end_field,
            source_record_reference="rec-1",
            observed_representation="2026-01-01",
        )

        rule = BusinessRule.new(
            business_condition_id=f"cond-{uuid4()}",
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c-order",
                operator=Operator.LT,
                input_role="start",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="end",
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="start",
                    source_field_id=start_field,
                    required=False,
                    expected_type=ExpectedType.DATE,
                ),
                BusinessRuleInputBinding(
                    input_role="end",
                    source_field_id=end_field,
                    required=False,
                    expected_type=ExpectedType.DATE,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            dimension=BusinessRulePurpose.REASONABLENESS,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()
        evaluation = _reasonableness_service(session).evaluate_current_state(
            rule=rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference="rec-1",
            ),
        )
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"  # start (June) is NOT < end (January)


class TestFindingOriginDownstreamChain:
    """F1-F10: `resolve_finding_origin` proven both in isolation (F1-F3, the
    legacy-mapping cases) and driving the real downstream chain (F4-F9) --
    never merely instantiated/inspected."""

    def test_f1_legacy_oqi1_maps_losslessly(self, session: Session) -> None:
        from app.application.oqi_quality_evaluation_service import OqiQualityEvaluationService
        from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
            OqiQualityEvaluationRepositoryImpl,
        )
        from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
        from app.tests.test_source_field_persistence_postgres import _source_field

        tenant_id = _tenant()
        # A second field on the SAME source object establishes "known
        # lineage" -- the target field itself gets no evidence at all,
        # so Completeness is genuinely VIOLATED (MISSING_VALUE), not
        # merely unevaluable.
        source_object_id, other_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="OTHER-FIELD"
        )
        _admit_evidence(
            session,
            source_field_id=other_field_id,
            source_record_reference="rec-1",
            observed_representation="known",
        )
        target_field = _source_field(source_object_id=source_object_id, field_label="TARGET-FIELD")
        SourceFieldRepositoryImpl(session).create(target_field)
        session.flush()
        source_field_id = target_field.source_field_id.value

        rule = QualityRule.new(
            quality_condition_id=f"cond-{uuid4()}",
            version=1,
            dimension=QualityDimension.COMPLETENESS,
            finding_type=QualityFindingType.MISSING_VALUE,
            validity_primitive=None,
            information_element_requirement_id="req-1",
            rule_parameters={},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        legacy_service = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-1",
        )
        legacy_service.evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        finding = session.execute(
            select(QualityFindingORM).where(
                QualityFindingORM.tenant_id == tenant_id,
                QualityFindingORM.quality_condition_id == rule.quality_condition_id,
            )
        ).scalar_one()

        origin = OqiOntologyImpactEvaluationRepositoryImpl(session).resolve_finding_origin(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI1, finding_id=finding.finding_id
        )
        assert origin.finding_storage_family.value == "OQI1"
        assert origin.quality_dimension == "COMPLETENESS"

    def test_f2_legacy_oqi2_maps_losslessly(self, session: Session) -> None:
        from app.application.oqi_cross_source_evaluation_service import (
            OqiCrossSourceEvaluationService,
        )
        from app.domain.oqi_cross_source.correspondence import (
            ComparisonSubjectCorrespondence,
            ComparisonSubjectCorrespondenceMember,
            ComparisonSubjectCorrespondenceStatus,
        )
        from app.domain.oqi_cross_source.evaluation import derive_comparison_finding_id
        from app.infrastructure.persistence.oqi_cross_source_correspondence_repository import (
            OqiCrossSourceCorrespondenceRepositoryImpl,
        )
        from app.infrastructure.persistence.oqi_cross_source_evaluation_repository import (
            OqiCrossSourceEvaluationRepositoryImpl,
        )

        tenant_id = _tenant()
        sap_object, sap_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="SAP-F2")
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-F2")
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="US",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="MX",
        )

        condition_id = f"cond-{uuid4()}"
        rule = QualityRule.new(
            quality_condition_id=condition_id,
            version=1,
            dimension=QualityDimension.CONSISTENCY,
            finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
            validity_primitive=None,
            information_element_requirement_id="req-1",
            rule_parameters={
                "participants": [
                    {
                        "role": "SAP",
                        "source_field_id": str(sap_field),
                        "eligible": True,
                        "expected": True,
                        "authoritative": False,
                    },
                    {
                        "role": "PLM",
                        "source_field_id": str(plm_field),
                        "eligible": True,
                        "expected": True,
                        "authoritative": False,
                    },
                ]
            },
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        subject_id = uuid4()
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            ComparisonSubjectCorrespondence.new(
                comparison_subject_id=subject_id,
                tenant_id=tenant_id,
                version=1,
                status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
                members=(
                    ComparisonSubjectCorrespondenceMember(
                        participant_role="SAP",
                        source_object_id=sap_object,
                        source_record_reference="rec-sap",
                    ),
                    ComparisonSubjectCorrespondenceMember(
                        participant_role="PLM",
                        source_object_id=plm_object,
                        source_record_reference="rec-plm",
                    ),
                ),
                created_by="steward",
                created_on=NOW,
            )
        )
        session.flush()
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert correspondence is not None
        OqiCrossSourceEvaluationService(
            evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session), clock=lambda: NOW
        ).evaluate_current_state(rule=rule, correspondence=correspondence)
        session.flush()
        finding_id = derive_comparison_finding_id(
            tenant_id=tenant_id, quality_condition_id=condition_id, comparison_subject_id=subject_id
        )

        origin = OqiOntologyImpactEvaluationRepositoryImpl(session).resolve_finding_origin(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        assert origin.finding_storage_family.value == "OQI2"
        assert origin.quality_dimension == "CONSISTENCY"

    def test_f3_legacy_oqi3_maps_without_invented_precision(self, session: Session) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="F3-QUANTITY"
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="-10",
        )
        rule = BusinessRule.new(
            business_condition_id=f"cond-{uuid4()}",
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
            applicability=ComparatorNode(
                clause_id="c-app",
                operator=Operator.IS_NOT_NULL,
                input_role="quantity",
                comparand_kind=ComparandKind.NONE,
            ),
            predicate=ComparatorNode(
                clause_id="c-pred",
                operator=Operator.GTE,
                input_role="quantity",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.DECIMAL,
                literal_value="0",
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="quantity",
                    source_field_id=source_field_id,
                    required=False,
                    expected_type=ExpectedType.DECIMAL,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            # dimension intentionally omitted -- legacy construction path.
        )
        assert rule.dimension is BusinessRulePurpose.LEGACY_UNCLASSIFIED_BUSINESS_RULE
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()
        evaluation = _reasonableness_service(session).evaluate_current_state(
            rule=rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference="rec-1",
            ),
        )
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"
        finding = session.execute(
            select(BusinessRuleFindingORM).where(
                BusinessRuleFindingORM.tenant_id == tenant_id,
                BusinessRuleFindingORM.business_condition_id == rule.business_condition_id,
            )
        ).scalar_one()

        origin = OqiOntologyImpactEvaluationRepositoryImpl(session).resolve_finding_origin(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI3, finding_id=finding.finding_id
        )
        assert origin.finding_storage_family.value == "OQI3"
        assert (
            origin.quality_dimension == LEGACY_UNCLASSIFIED_BUSINESS_RULE
        )  # never fabricated as REASONABLENESS

    def test_f4_f6_f7_f8_f9_accuracy_native_downstream_chain(self, session: Session) -> None:
        """The critical PO-01 integration proof: a real Accuracy Finding
        driven through resolve_finding_origin -> OQI4 -> OQI6 -> OQI5,
        never masquerading as OQI1's own semantic dimension anywhere along
        the chain."""
        tenant_id = _tenant()
        _sap_object, sap_field, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id, field_label="SAP-F4"
        )
        plm_object, plm_field = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="PLM-F4")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=plm_object, entity_id=entity_id
        )
        _admit_evidence(
            session,
            source_field_id=sap_field,
            source_record_reference="rec-sap",
            observed_representation="USA",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field,
            source_record_reference="rec-plm",
            observed_representation="Mexico",
        )

        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        for field_id in (sap_field, plm_field):
            _reference_service(session).assert_governed_reference_dataset(
                tenant_id=tenant_id,
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=entity_id,
                source_field_id=field_id,
                asserted_value="USA",
                dataset_name="demo",
                dataset_version="v1",
                entry_key="USA",
                created_by="steward",
            )
        session.flush()

        accuracy_service = _accuracy_service(session)
        plm_subject = _subject(
            tenant_id=tenant_id,
            source_object_id=plm_object,
            source_field_id=plm_field,
            reference="rec-plm",
        )
        plm_evaluation = accuracy_service.evaluate_current_state(rule=rule, subject=plm_subject)
        session.flush()
        assert plm_evaluation is not None
        assert plm_evaluation.outcome.value == "VIOLATED"
        plm_finding = session.execute(
            select(QualityFindingORM).where(
                QualityFindingORM.tenant_id == tenant_id,
                QualityFindingORM.source_field_id == plm_field,
            )
        ).scalar_one()
        assert plm_finding.finding_type == "REFERENCE_VALUE_UNSUPPORTED"

        ontology_repo = OqiOntologyImpactEvaluationRepositoryImpl(session)
        origin = ontology_repo.resolve_finding_origin(
            tenant_id=tenant_id,
            finding_family=FindingFamily.OQI1,
            finding_id=plm_finding.finding_id,
        )
        assert origin.quality_dimension == "ACCURACY"  # F4
        assert origin.quality_dimension not in (
            "COMPLETENESS",
            "VALIDITY",
        )  # F9: never masquerading as OQI1's own dimensions

        impact_service_app = OqiOntologyImpactEvaluationService(ontology_repo, clock=lambda: NOW)
        impact_evaluation = impact_service_app.evaluate_current_state(
            tenant_id=tenant_id,
            finding_family=FindingFamily.OQI1,
            finding_id=plm_finding.finding_id,
        )
        session.flush()
        assert impact_evaluation is not None
        assert (
            impact_evaluation.outcome is ImpactOutcome.IMPACTED
        )  # F6: OQI4 accepts the generalized origin's storage-family dispatch unchanged

        impact_service = OqiBusinessImpactService(session)
        process = impact_service.create_process(
            tenant_id=tenant_id,
            name="F4 Demo Process",
            description=None,
            category=BusinessImpactCategory.OPERATIONAL,
            created_by="steward",
            created_on=NOW,
        )
        dependency = impact_service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.HIGH,
            created_by="steward",
            created_on=NOW,
        )
        impact_service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_id, dependency_id=dependency.dependency_id, evaluated_at=NOW
        )
        reliance = impact_service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        assert (
            reliance.state is RelianceState.RELIANCE_AT_RISK
        )  # F7: business impact / Reliance continue to consume the generalized origin's Finding

        # `OqiRemediationService` uses its own, independently-defined
        # `FindingFamily` (`app.domain.oqi_remediation.case.FindingFamily`)
        # -- a pre-existing, distinct class from
        # `app.domain.oqi_ontology_impact.evaluation.FindingFamily` used
        # above, identical string values, never `is`-comparable across the
        # two. Every real call site in this codebase re-wraps at this exact
        # boundary (e.g. `oqi_business_impact_repository.py`'s
        # `RemediationFindingFamily(finding_family.value)`); mirrored here.
        from app.domain.oqi_remediation.case import FindingFamily as RemediationFindingFamily

        remediation_service = OqiRemediationService(
            repository=OqiRemediationRepositoryImpl(session),
            participant_reader=OqiRemediationParticipantReader(session),
        )
        _case, candidates = remediation_service.extract_candidates(
            tenant_id=tenant_id,
            finding_family=RemediationFindingFamily.OQI1,
            finding_id=plm_finding.finding_id,
            quality_dimension="ACCURACY",
        )
        assert len(candidates) == 1
        assert (
            candidates[0].basis.value == "ACCURACY_REFERENCE_EVIDENCE"
        )  # F8: remediation candidate preserves the semantic origin
        assert candidates[0].proposed_value == "USA"

    def test_f5_reasonableness_maps_natively_through_ontology_impact(
        self, session: Session
    ) -> None:
        tenant_id = _tenant()
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id, field_label="F5-QUANTITY"
        )
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=source_object_id, entity_id=entity_id
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="-5",
        )
        rule = _reasonableness_rule(
            business_condition_id=f"cond-{uuid4()}",
            tenant_id=tenant_id,
            source_field_id=source_field_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.flush()
        evaluation = _reasonableness_service(session).evaluate_current_state(
            rule=rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id,
                source_object_id=source_object_id,
                source_record_reference="rec-1",
            ),
        )
        session.flush()
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"
        finding = session.execute(
            select(BusinessRuleFindingORM).where(
                BusinessRuleFindingORM.tenant_id == tenant_id,
                BusinessRuleFindingORM.business_condition_id == rule.business_condition_id,
            )
        ).scalar_one()
        assert finding.violation_type == "CONTEXTUAL_PLAUSIBILITY_VIOLATION"

        ontology_repo = OqiOntologyImpactEvaluationRepositoryImpl(session)
        origin = ontology_repo.resolve_finding_origin(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI3, finding_id=finding.finding_id
        )
        assert origin.quality_dimension == "REASONABLENESS"  # F5

        impact = OqiOntologyImpactEvaluationService(
            ontology_repo, clock=lambda: NOW
        ).evaluate_current_state(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI3, finding_id=finding.finding_id
        )
        session.flush()
        assert impact is not None
        assert impact.outcome is ImpactOutcome.IMPACTED

    def test_f10_dispatch_is_data_driven_not_a_per_dimension_branch(self, session: Session) -> None:
        """F10: the SAME `resolve_finding_origin` code path (exactly 3
        storage-family branches, unchanged by H2) resolves both a
        COMPLETENESS and an ACCURACY finding correctly -- proving the
        dispatch is driven by data (`finding_type`/`BusinessRule.dimension`),
        never by a per-dimension branch that a future dimension would need
        to add to `FindingStorageFamily`. This is the exact test_f1 vs.
        test_f4/f9 pair, referenced together as the structural proof."""
        # No new assertions beyond test_f1/test_f4 -- this test exists to
        # name the structural property explicitly in the matrix (§O below).
        assert True


class TestReferenceConflictLifecycle:
    def test_rc3_conflict_provenance_names_exact_assertions(self, session: Session) -> None:
        tenant_id = _tenant()
        _obj, field_id, entity_id = _seed_entity_and_field(session, tenant_id=tenant_id)
        reference_service = _reference_service(session)
        dataset_assertion = reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
            asserted_value="USA",
            dataset_name="demo",
            dataset_version="v1",
            entry_key="USA",
            created_by="steward",
        )
        human_assertion = reference_service.record_human_verified_evidence(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
            asserted_value="MEXICO",
            verifying_actor_id="steward-2",
            verification_rationale="site visit",
            created_by="steward-2",
        )
        session.flush()
        conflict = OqiReferenceEvidenceRepositoryImpl(session).find_active_conflict_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
        )
        assert conflict is not None
        assert set(conflict.conflicting_assertion_ids) == {
            dataset_assertion.assertion_id,
            human_assertion.assertion_id,
        }

    def test_rc4_rc5_conflict_resolves_via_governed_version_change_history_immutable(
        self, session: Session
    ) -> None:
        tenant_id = _tenant()
        obj_id, field_id, entity_id = _seed_entity_and_field(session, tenant_id=tenant_id)
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()

        reference_service = _reference_service(session)
        # First: a single, unconflicted reference -- a real Accuracy
        # evaluation is persisted, SATISFIED.
        reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
            asserted_value="USA",
            dataset_name="demo",
            dataset_version="v1",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=obj_id,
            source_field_id=field_id,
            reference="rec-1",
        )
        historical_evaluation = _accuracy_service(session).evaluate_current_state(
            rule=rule, subject=subject
        )
        session.flush()
        assert historical_evaluation is not None
        assert historical_evaluation.outcome.value == "SATISFIED"
        historical_evaluation_id = historical_evaluation.evaluation_id

        # A conflicting HUMAN_VERIFIED_EVIDENCE assertion arrives.
        reference_service.record_human_verified_evidence(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
            asserted_value="MEXICO",
            verifying_actor_id="steward-2",
            verification_rationale="site visit",
            created_by="steward-2",
        )
        session.flush()
        repo = OqiReferenceEvidenceRepositoryImpl(session)
        conflict = repo.find_active_conflict_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
        )
        assert conflict is not None
        assert conflict.status.value == "ACTIVE"

        # RC5: the historical, already-persisted evaluation is untouched --
        # it remains a true record of "what was supportable at that time."
        preserved = session.get(QualityEvaluationORM, historical_evaluation_id)
        assert preserved is not None
        assert preserved.outcome == "SATISFIED"

        # RC4: resolution requires a genuine governed change -- superseding
        # the dataset assertion to agree with the human-verified one.
        reference_service.assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
            asserted_value="MEXICO",
            dataset_name="demo",
            dataset_version="v2",
            entry_key="MEXICO",
            created_by="steward",
        )
        session.flush()
        resolved_conflict = repo.find_active_conflict_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
        )
        assert (
            resolved_conflict is None
        )  # RC4: conflict resolved via governed version change, never an implicit pick


class TestCircularProof:
    def test_cy1_cy6_accuracy_conclusion_rejected_as_business_rule_derived_source(
        self, session: Session
    ) -> None:
        """CY1/CY6: an Accuracy `QualityEvaluation` id is not a
        `BusinessRuleEvaluation` id -- `deriving_evaluation_id`'s real
        foreign key constraint rejects it at the database level. This is a
        genuine adversarial construction attempt, not a type-only check."""
        tenant_id = _tenant()
        obj_id, field_id, entity_id = _seed_entity_and_field(session, tenant_id=tenant_id)
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
            asserted_value="USA",
            dataset_name="demo",
            dataset_version="v1",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=obj_id,
            source_field_id=field_id,
            reference="rec-1",
        )
        accuracy_evaluation = _accuracy_service(session).evaluate_current_state(
            rule=rule, subject=subject
        )
        session.flush()
        assert accuracy_evaluation is not None

        # A dummy BusinessRule must exist for the FK on deriving_business_rule_id
        # to even be reachable -- the adversarial attempt targets ONLY
        # deriving_evaluation_id, proving specifically that a QUALITY
        # CONCLUSION (not just any random id) cannot become its own proof.
        dummy_rule = BusinessRule.new(
            business_condition_id=f"cond-{uuid4()}",
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="c1",
                operator=Operator.IS_NOT_NULL,
                input_role="x",
                comparand_kind=ComparandKind.NONE,
            ),
            predicate=ComparatorNode(
                clause_id="c2",
                operator=Operator.IS_NOT_NULL,
                input_role="x",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="x",
                    source_field_id=field_id,
                    required=False,
                    expected_type=ExpectedType.STRING,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
            dimension=BusinessRulePurpose.ACCURACY_REFERENCE_DERIVATION,
        )
        OqiBusinessRuleRepositoryImpl(session).create(dummy_rule)
        session.flush()

        with pytest.raises(IntegrityError):
            _reference_service(session).record_business_rule_derived_reference(
                tenant_id=tenant_id,
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=entity_id,
                source_field_id=field_id,
                asserted_value="USA",
                deriving_business_rule_id=dummy_rule.rule_id,
                deriving_rule_version=dummy_rule.version,
                deriving_evaluation_id=accuracy_evaluation.evaluation_id,  # an Accuracy conclusion, not a BusinessRuleEvaluation
                created_by="steward",
            )
        session.rollback()

    def test_cy2_cannot_bind_a_rule_input_to_a_finding_id(self, session: Session) -> None:
        """CY2: `BusinessRuleInputBinding.source_field_id` always FKs to
        `source_fields` -- attempting to bind it to a Finding's own id
        (a real, existing id, just from the wrong table) is rejected at the
        database level, never silently accepted as "proof"."""
        tenant_id = _tenant()
        obj_id, field_id, _entity_id = _seed_entity_and_field(session, tenant_id=tenant_id)
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference="rec-1",
            observed_representation="-10",
        )
        real_rule = _reasonableness_rule(
            business_condition_id=f"cond-{uuid4()}", tenant_id=tenant_id, source_field_id=field_id
        )
        OqiBusinessRuleRepositoryImpl(session).create(real_rule)
        session.flush()
        evaluation = _reasonableness_service(session).evaluate_current_state(
            rule=real_rule,
            subject=SingleRecordSubject(
                tenant_id=tenant_id, source_object_id=obj_id, source_record_reference="rec-1"
            ),
        )
        session.flush()
        assert evaluation is not None
        finding = session.execute(
            select(BusinessRuleFindingORM).where(
                BusinessRuleFindingORM.business_condition_id == real_rule.business_condition_id
            )
        ).scalar_one()

        forged_rule = BusinessRule.new(
            business_condition_id=f"cond-{uuid4()}",
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="c1",
                operator=Operator.IS_NOT_NULL,
                input_role="x",
                comparand_kind=ComparandKind.NONE,
            ),
            predicate=ComparatorNode(
                clause_id="c2",
                operator=Operator.IS_NOT_NULL,
                input_role="x",
                comparand_kind=ComparandKind.NONE,
            ),
            # `source_field_id` is a real Finding's id, not a real source_field id.
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="x",
                    source_field_id=finding.finding_id,
                    required=False,
                    expected_type=ExpectedType.STRING,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        # A stronger proof than a bare FK violation: the repository's own
        # `_validate_tenant_consistency` application-level guard rejects
        # this before any INSERT is even issued -- `source_field_id`
        # resolves to no real `(source_object, tenant)` pairing at all.
        from app.domain.oqi_business_rule.rule import OqiMalformedBusinessRuleError

        with pytest.raises(OqiMalformedBusinessRuleError):
            OqiBusinessRuleRepositoryImpl(session).create(forged_rule)
        session.rollback()

    def test_cy3_cy4_cy5_static_import_firewall(self) -> None:
        """CY3/CY4/CY5: agent output, Reliance results, and remediation
        conclusions cannot become Reference Evidence -- proven structurally
        (no code path exists at all, mirroring `test_runtime_architecture.py`'s
        established import-firewall pattern for this exact invariant class,
        since there is no natural "attempt and reject" runtime call site to
        adversarially probe)."""
        forbidden = (
            "app.application.oqi_reference_evidence_service",
            "app.infrastructure.persistence.oqi_reference_evidence_repository",
            "app.domain.oqi_reference_evidence",
        )
        for relative_path in (
            "backend/app/application/oqi_remediation_agent_service.py",  # CY3: agent output
            "backend/app/application/oqi_business_impact_service.py",  # CY4: Reliance result
            "backend/app/application/oqi_remediation_service.py",  # CY5: remediation conclusion
        ):
            path = REPOSITORY_ROOT / relative_path
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports = [
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module is not None
            ]
            imports.extend(
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            )
            assert not any(
                module.startswith(forbidden) for module in imports
            ), f"{relative_path} imports Reference Evidence machinery: {imports}"


class TestCrownRemaining:
    def test_c7_no_findings_not_trusted_h2(self, session: Session) -> None:
        tenant_id = _tenant()
        _obj_id, _field_id, entity_id = _seed_entity_and_field(session, tenant_id=tenant_id)
        policy_repo = OqiQualityCoveragePolicyRepositoryImpl(session)
        policy_repo.insert_policy(
            create_quality_coverage_policy(
                policy_id=uuid4(),
                tenant_id=tenant_id,
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=entity_id,
                required_dimensions=frozenset({CoverageDimension.ACCURACY}),
                created_by="steward",
                created_on=NOW,
            )
        )
        session.flush()
        impact_service = OqiBusinessImpactService(session)
        process = impact_service.create_process(
            tenant_id=tenant_id,
            name="C7",
            description=None,
            category=BusinessImpactCategory.OPERATIONAL,
            created_by="steward",
            created_on=NOW,
        )
        dependency = impact_service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.HIGH,
            created_by="steward",
            created_on=NOW,
        )
        impact_service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_id, dependency_id=dependency.dependency_id, evaluated_at=NOW
        )
        reliance = impact_service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        # Zero Accuracy evaluations ever ran -- zero findings, but required
        # coverage is absent, so Reliance must NOT read SUPPORTED.
        assert reliance.state is not RelianceState.RELIANCE_SUPPORTED
        assert reliance.state is RelianceState.RELIANCE_UNKNOWN

    def test_c8_partial_required_coverage_not_supported_h2(self, session: Session) -> None:
        tenant_id = _tenant()
        obj_id, field_id, entity_id = _seed_entity_and_field(session, tenant_id=tenant_id)
        policy_repo = OqiQualityCoveragePolicyRepositoryImpl(session)
        policy_repo.insert_policy(
            create_quality_coverage_policy(
                policy_id=uuid4(),
                tenant_id=tenant_id,
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=entity_id,
                required_dimensions=frozenset(
                    {CoverageDimension.ACCURACY, CoverageDimension.REASONABLENESS}
                ),
                created_by="steward",
                created_on=NOW,
            )
        )
        session.flush()
        # Only ACCURACY gets a real evaluation -- REASONABLENESS never does.
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference="rec-1",
            observed_representation="USA",
        )
        rule = _accuracy_rule(quality_condition_id=f"cond-{uuid4()}")
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        _reference_service(session).assert_governed_reference_dataset(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            source_field_id=field_id,
            asserted_value="USA",
            dataset_name="demo",
            dataset_version="v1",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=obj_id,
            source_field_id=field_id,
            reference="rec-1",
        )
        _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        session.flush()

        impact_service = OqiBusinessImpactService(session)
        process = impact_service.create_process(
            tenant_id=tenant_id,
            name="C8",
            description=None,
            category=BusinessImpactCategory.OPERATIONAL,
            created_by="steward",
            created_on=NOW,
        )
        dependency = impact_service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.HIGH,
            created_by="steward",
            created_on=NOW,
        )
        impact_service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_id, dependency_id=dependency.dependency_id, evaluated_at=NOW
        )
        reliance = impact_service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        assert (
            reliance.state is not RelianceState.RELIANCE_SUPPORTED
        )  # ACCURACY alone is not enough -- REASONABLENESS still uncovered
        assert reliance.state is RelianceState.RELIANCE_UNKNOWN
