"""CDD-048 Artifact Authorization row 19: the H2 crown proofs, real
PostgreSQL, exercised through the actual Accuracy/Reasonableness evaluator
entry points -- never a raw repository call in isolation.

Proves (a representative, real-execution subset of CDD-048 §31's full
matrix -- the remainder is deferred, disclosed in the OQI-H2-I final
report, not silently claimed done): A1-A3, A7, A9-A10; R1-R2, R8; C1
(VALID != ACCURATE), C2 (CONSISTENT != ACCURATE unaffected by construction
-- no Accuracy row exists absent Reference Evidence), C8 (PARTIAL REQUIRED
COVERAGE != SUPPORTED, reusing H1's own crown mechanism unmodified)."""

# isort: skip_file
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_accuracy_evaluation_service import OqiAccuracyEvaluationService
from app.application.oqi_business_rule_evaluation_service import (
    OqiBusinessRuleEvaluationService,
    SingleRecordSubject,
)
from app.application.oqi_reference_evidence_service import OqiReferenceEvidenceService
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
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
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_reference_evidence import (
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
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.oqi_reference_evidence_repository import (
    OqiReferenceEvidenceRepositoryImpl,
)
from app.tests.test_oqi_ontology_impact_postgres import _entity, _resolve_entity
from app.tests.test_oqi_quality_postgres import _admit_evidence, _subject
from app.tests.test_oqi_quality_postgres import _seed_field as _seed_oqi1_field

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
