"""CDD-058 Production Governed Remediation Orchestration -- real-PostgreSQL
crown suite. Proves `ProductionRemediationOrchestrationService` composes the
existing, unmodified OQI5-I1 `OqiRemediationService` and the existing,
unmodified per-dimension/OQI4/OQI6/Reliance entrypoints correctly: real
multi-source Consistency and Accuracy candidates route through a genuine
positive-remediation loop to a resolved Finding and a `SUPPORTED` Reliance
state; a genuine negative loop (no real correction) never falsely resolves
anything; zero-candidate Findings route to `STEWARD_INVESTIGATION` with zero
fabricated instructions/authorizations; concurrent preparation for the
identical Finding converges with zero uncaught `IntegrityError`; every hop is
tenant-scoped; and the agent-reasoning/authority boundary (`AGENT != AUTHORITY`,
CDD-058 SS5) is never crossed by this orchestrator alone.

Reuses this repository's own established sibling-test-file helper-import
precedent: `_seed_field`/`_admit_evidence`/`_rule`/`_correspondence`/
`_service` from `test_oqi_cross_source_postgres.py`; `_seed_entity_and_field`/
`_reference_service`/`_accuracy_rule`/`_accuracy_service`/`_reasonableness_
rule` from `test_oqi_h2_accuracy_reasonableness_crown.py`; `_seed_field as
_seed_oqi1_field`/`_admit_evidence as _admit_oqi1_evidence`/`_subject` from
`test_oqi_quality_postgres.py`; `_entity`/`_resolve_entity` from
`test_oqi_ontology_impact_postgres.py`."""

# isort: skip_file
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_business_impact_service import OqiBusinessImpactService
from app.application.oqi_business_rule_evaluation_service import (
    OqiBusinessRuleEvaluationService,
    SingleRecordSubject,
)
from app.application.oqi_remediation_service import OqiRemediationService
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.application.production_remediation_orchestration_service import (
    ProductionRemediationOrchestrationError,
    ProductionRemediationOrchestrationService,
)
from app.domain.oqi_business_impact.dependency import Criticality
from app.domain.oqi_business_impact.process import BusinessImpactCategory
from app.domain.oqi_business_impact.reliance import RelianceState
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_remediation.authorization import RemediationAuthorizationStatus
from app.domain.oqi_remediation.case import RemediationCaseStatus
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationAuthorizationORM,
    OqiRemediationCandidateORM,
    OqiRemediationCaseORM,
    OqiRemediationInstructionORM,
)
from app.infrastructure.persistence.models.oqi_remediation_agent import (
    AgentRecommendationORM,
    AgentRunORM,
)
from app.infrastructure.persistence.oqi_business_rule_evaluation_repository import (
    OqiBusinessRuleEvaluationRepositoryImpl,
    OqiBusinessRuleEvidenceValueReader,
)
from app.infrastructure.persistence.oqi_business_rule_repository import (
    OqiBusinessRuleRepositoryImpl,
)
from app.infrastructure.persistence.oqi_cross_source_correspondence_repository import (
    OqiCrossSourceCorrespondenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import (
    OqiQualityRuleRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)
from app.tests.test_oqi_cross_source_postgres import (
    _admit_evidence as _cs_admit_evidence,
)
from app.tests.test_oqi_cross_source_postgres import (
    _correspondence as _cs_correspondence,
)
from app.tests.test_oqi_cross_source_postgres import _rule as _cs_rule
from app.tests.test_oqi_cross_source_postgres import _seed_field as _seed_cs_field
from app.tests.test_oqi_cross_source_postgres import _service as _cs_service
from app.tests.test_oqi_h2_accuracy_reasonableness_crown import (
    _accuracy_rule,
    _accuracy_service,
    _reasonableness_rule,
    _reference_service,
    _seed_entity_and_field,
)
from app.tests.test_oqi_ontology_impact_postgres import _entity, _resolve_entity
from app.tests.test_oqi_quality_postgres import _admit_evidence as _admit_oqi1_evidence
from app.tests.test_oqi_quality_postgres import _seed_field as _seed_oqi1_field
from app.tests.test_oqi_quality_postgres import _subject

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(migrated_engine, expire_on_commit=False)


def _orchestrator(session: Session) -> ProductionRemediationOrchestrationService:
    return ProductionRemediationOrchestrationService(session, clock=lambda: NOW)


def _tenant() -> str:
    return f"tenant-{uuid4()}"


def _admit_evidence_at(
    session: Session,
    *,
    source_field_id: UUID,
    source_record_reference: str,
    observed_representation: str,
    moment: datetime,
) -> UUID:
    """Like the sibling test files' own `_admit_evidence`, but with an
    explicit, caller-controlled `observed_at`/`received_at` -- needed so a
    genuine later correction is unambiguously selected as "latest" over an
    earlier admitted value for the identical field/record, rather than
    tying on the sibling helpers' own fixed module-level `NOW` constant."""
    evidence = FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference=source_record_reference,
        observed_representation=observed_representation,
        observed_at=moment,
        received_at=moment,
    )
    FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(evidence)
    return evidence.field_value_evidence_id.value


# =====================================================================
# Migration/table-count invariant (CDD-058 SS4/SS39: zero new tables).
# =====================================================================


def test_production_remediation_orchestration_introduces_zero_new_tables(
    migrated_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))
    tables = set(inspect(migrated_engine).get_table_names()) - {"alembic_version"}
    assert len(tables) == 126


# =====================================================================
# Zero-candidate Finding (Reasonableness) -- CDD-058 SS12: routes to
# STEWARD_INVESTIGATION with zero fabricated instruction/authorization,
# and creates zero agent-reasoning rows (the agent firewall).
# =====================================================================


def test_prepare_zero_candidate_finding_yields_steward_investigation(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = _tenant()
    with factory() as session:
        source_object_id, source_field_id = _seed_oqi1_field(
            session, tenant_id=tenant_id, field_label="QUANTITY"
        )
        _admit_oqi1_evidence(
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
        assert evaluation is not None and evaluation.outcome.value == "VIOLATED"
        session.commit()

        finding_id = session.execute(
            select(BusinessRuleFindingORM.finding_id).where(
                BusinessRuleFindingORM.tenant_id == tenant_id
            )
        ).scalar_one()

    with factory() as session:
        result = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=finding_id, requested_by="steward-a"
        )

    assert result.case_status == RemediationCaseStatus.STEWARD_INVESTIGATION.value
    assert result.candidates == ()
    assert result.instructions == ()
    assert result.authorizations == ()
    assert result.agent_reasoning_status == "NOT_INVOKED"

    with factory() as session:
        assert (
            session.execute(
                select(OqiRemediationInstructionORM).where(
                    OqiRemediationInstructionORM.finding_id == finding_id
                )
            ).first()
            is None
        )
        assert (
            session.execute(select(AgentRunORM).where(AgentRunORM.tenant_id == tenant_id)).first()
            is None
        )
        case = session.execute(
            select(OqiRemediationCaseORM).where(OqiRemediationCaseORM.finding_id == finding_id)
        ).scalar_one()
        assert (
            session.execute(
                select(AgentRecommendationORM).where(AgentRecommendationORM.case_id == case.case_id)
            ).first()
            is None
        )


# =====================================================================
# Unknown / cross-tenant Finding -- fails closed (CDD-058 SS10).
# =====================================================================


def test_prepare_unknown_finding_not_found(factory: sessionmaker[Session]) -> None:
    tenant_id = _tenant()
    with factory() as session, pytest.raises(ProductionRemediationOrchestrationError) as excinfo:
        _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=uuid4(), requested_by="steward-a"
        )
    assert excinfo.value.code == "REMEDIATION_FINDING_NOT_FOUND"


def test_prepare_cross_tenant_finding_not_found(factory: sessionmaker[Session]) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    with factory() as session:
        source_object_id, source_field_id = _seed_oqi1_field(session, tenant_id=tenant_b)
        _admit_oqi1_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-1",
            observed_representation="-10",
        )
        rule = _reasonableness_rule(
            business_condition_id=f"cond-{uuid4()}",
            tenant_id=tenant_b,
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
            tenant_id=tenant_b, source_object_id=source_object_id, source_record_reference="rec-1"
        )
        service.evaluate_current_state(rule=rule, subject=subject)
        session.commit()
        finding_id = session.execute(
            select(BusinessRuleFindingORM.finding_id).where(
                BusinessRuleFindingORM.tenant_id == tenant_b
            )
        ).scalar_one()

    with factory() as session, pytest.raises(ProductionRemediationOrchestrationError) as excinfo:
        _orchestrator(session).prepare_remediation(
            tenant_id=tenant_a, finding_id=finding_id, requested_by="steward-a"
        )
    assert excinfo.value.code == "REMEDIATION_FINDING_NOT_FOUND"

    with factory() as session:
        assert (
            session.execute(
                select(OqiRemediationCaseORM).where(OqiRemediationCaseORM.finding_id == finding_id)
            ).first()
            is None
        )


# =====================================================================
# Multi-source Consistency crown -- positive (genuine correction resolves
# the Finding, case converges to RESOLVED, Reliance transitions to
# SUPPORTED) and negative (no real correction, nothing is ever falsely
# resolved) -- CDD-058 SS9/SS19-SS23.
# =====================================================================


def _seed_consistency_finding(
    session: Session, *, tenant_id: str
) -> tuple[str, UUID, UUID, UUID, UUID]:
    """Seeds a genuine two-participant Consistency rule/correspondence with
    SAP evidence present and PLM evidence absent -- the real evaluator's own
    MISSING-participant path -- and runs the real evaluator once to open a
    genuine `QualityComparisonFinding`. Returns (condition_id, subject_id,
    sap_object, plm_object, plm_field)."""
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    sap_object, sap_field = _seed_cs_field(session, tenant_id=tenant_id, field_label="SAP-MPN")
    plm_object, plm_field = _seed_cs_field(session, tenant_id=tenant_id, field_label="PLM-MPN")
    OqiQualityRuleRepositoryImpl(session).create(
        _cs_rule(condition_id=condition_id, sap_field=sap_field, plm_field=plm_field)
    )
    OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
        _cs_correspondence(
            tenant_id=tenant_id, subject_id=subject_id, sap_object=sap_object, plm_object=plm_object
        )
    )
    _cs_admit_evidence(
        session, source_field_id=sap_field, source_record_reference="MAT-100", value="X"
    )
    session.commit()

    rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
    correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
        tenant_id=tenant_id, comparison_subject_id=subject_id
    )
    assert rule is not None and correspondence is not None
    evaluation = _cs_service(session, clock=lambda: NOW).evaluate_current_state(
        rule=rule, correspondence=correspondence
    )
    assert evaluation is not None and evaluation.outcome.value == "VIOLATED"
    session.commit()
    return condition_id, subject_id, sap_object, plm_object, plm_field


def test_consistency_positive_remediation_crown_resolves_finding_and_reliance(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = _tenant()
    with factory() as session:
        _condition_id, _subject_id, _sap_object, plm_object, plm_field = _seed_consistency_finding(
            session, tenant_id=tenant_id
        )
        entity_id = _entity(session, tenant_id=tenant_id, name="consistency-crown")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=plm_object, entity_id=entity_id
        )
        impact_service = OqiBusinessImpactService(session)
        process = impact_service.create_process(
            tenant_id=tenant_id,
            name="Consistency Crown Process",
            description=None,
            category=BusinessImpactCategory.OPERATIONAL,
            created_by="steward",
            created_on=NOW,
        )
        impact_service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.HIGH,
            created_by="steward",
            created_on=NOW,
        )
        session.commit()
        finding_id = session.execute(
            select(QualityComparisonFindingORM.finding_id).where(
                QualityComparisonFindingORM.tenant_id == tenant_id
            )
        ).scalar_one()

    with factory() as session:
        prepared = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=finding_id, requested_by="steward-a"
        )
    assert prepared.case_status == RemediationCaseStatus.CANDIDATE_READY.value
    assert len(prepared.candidates) == 1
    candidate = prepared.candidates[0]
    assert candidate.proposed_value == "X"  # SAP's own known value, proposed for missing PLM
    assert len(prepared.authorizations) == 1
    authorization_id = prepared.authorizations[0].authorization_id
    assert prepared.authorizations[0].status == RemediationAuthorizationStatus.PENDING.value

    with factory() as session:
        service = OqiRemediationService(
            repository=OqiRemediationRepositoryImpl(session),
            participant_reader=OqiRemediationParticipantReader(session),
        )
        service.approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="steward-b", now=NOW
        )
        session.commit()

        # The genuine, real-world correction: PLM's own evidence now agrees
        # with SAP's -- never applied by this orchestrator itself (CDD-058
        # SS5 `REMEDIATION != RESOLUTION`), simulating the external system
        # having actually been corrected before execution was reported.
        _cs_admit_evidence(
            session, source_field_id=plm_field, source_record_reference="P-442", value="X"
        )
        session.commit()

        service.report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id, now=NOW
        )
        session.commit()

        reevaluation = _orchestrator(session).reevaluate_after_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        session.commit()

    assert reevaluation is not None
    assert reevaluation.dq.status == "EVALUATED"
    assert reevaluation.dq.outcome == "SATISFIED"
    assert reevaluation.ontology_impact.status == "EVALUATED"
    assert reevaluation.reliance.status == "EVALUATED"
    assert reevaluation.reliance.state == RelianceState.RELIANCE_SUPPORTED.value
    assert reevaluation.case_status == RemediationCaseStatus.RESOLVED.value

    with factory() as session:
        finding = session.get(QualityComparisonFindingORM, finding_id)
        assert finding is not None and finding.status == "RESOLVED"


def test_consistency_negative_remediation_crown_never_falsely_resolves(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = _tenant()
    with factory() as session:
        _seed_consistency_finding(session, tenant_id=tenant_id)
        session.commit()
        finding_id = session.execute(
            select(QualityComparisonFindingORM.finding_id).where(
                QualityComparisonFindingORM.tenant_id == tenant_id
            )
        ).scalar_one()

    with factory() as session:
        prepared = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=finding_id, requested_by="steward-a"
        )
    authorization_id = prepared.authorizations[0].authorization_id

    with factory() as session:
        service = OqiRemediationService(
            repository=OqiRemediationRepositoryImpl(session),
            participant_reader=OqiRemediationParticipantReader(session),
        )
        service.approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="steward-b", now=NOW
        )
        session.commit()
        # No real correction: PLM evidence is never admitted.
        service.report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id, now=NOW
        )
        session.commit()

        reevaluation = _orchestrator(session).reevaluate_after_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        session.commit()

    assert reevaluation is not None
    assert reevaluation.dq.status == "EVALUATED"
    assert reevaluation.dq.outcome == "VIOLATED"
    assert reevaluation.case_status != RemediationCaseStatus.RESOLVED.value

    with factory() as session:
        finding = session.get(QualityComparisonFindingORM, finding_id)
        assert finding is not None and finding.status == "OPEN"


# =====================================================================
# Accuracy crown -- the same positive-path proof for the Accuracy family
# (CDD-058 SS9, ACCURACY/CONFORMITY dispatch via `EvaluationSubject`
# reconstructed directly from `QualityFindingORM`'s own persisted
# `source_object_id`/`source_field_id`/`source_record_reference`).
# =====================================================================


def test_accuracy_positive_remediation_crown_resolves_finding_and_reliance(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = _tenant()
    with factory() as session:
        source_object_id, source_field_id, entity_id = _seed_entity_and_field(
            session, tenant_id=tenant_id, field_label="ACCURACY-CROWN"
        )
        _admit_evidence_at(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-acc",
            observed_representation="Mexico",
            moment=NOW - timedelta(minutes=10),
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
            dataset_name="crown",
            dataset_version="v1",
            entry_key="USA",
            created_by="steward",
        )
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
            reference="rec-acc",
        )
        evaluation = _accuracy_service(session).evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is not None and evaluation.outcome.value == "VIOLATED"
        session.commit()

        impact_service = OqiBusinessImpactService(session)
        process = impact_service.create_process(
            tenant_id=tenant_id,
            name="Accuracy Crown Process",
            description=None,
            category=BusinessImpactCategory.OPERATIONAL,
            created_by="steward",
            created_on=NOW,
        )
        impact_service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.HIGH,
            created_by="steward",
            created_on=NOW,
        )
        session.commit()

        from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM

        finding_id = session.execute(
            select(QualityFindingORM.finding_id).where(QualityFindingORM.tenant_id == tenant_id)
        ).scalar_one()

    with factory() as session:
        prepared = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=finding_id, requested_by="steward-a"
        )
    assert prepared.case_status == RemediationCaseStatus.CANDIDATE_READY.value
    assert len(prepared.candidates) == 1
    assert prepared.candidates[0].proposed_value == "USA"
    authorization_id = prepared.authorizations[0].authorization_id

    with factory() as session:
        service = OqiRemediationService(
            repository=OqiRemediationRepositoryImpl(session),
            participant_reader=OqiRemediationParticipantReader(session),
        )
        service.approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="steward-b", now=NOW
        )
        session.commit()

        _admit_evidence_at(
            session,
            source_field_id=source_field_id,
            source_record_reference="rec-acc",
            observed_representation="USA",
            moment=NOW,
        )
        session.commit()

        service.report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id, now=NOW
        )
        session.commit()

        reevaluation = _orchestrator(session).reevaluate_after_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        session.commit()

    assert reevaluation is not None
    assert reevaluation.dq.status == "EVALUATED"
    assert reevaluation.dq.outcome == "SATISFIED"
    assert reevaluation.reliance.status == "EVALUATED"
    assert reevaluation.reliance.state == RelianceState.RELIANCE_SUPPORTED.value
    assert reevaluation.case_status == RemediationCaseStatus.RESOLVED.value


# =====================================================================
# Idempotent repeated preparation converges -- CDD-058 SS14.
# =====================================================================


def test_repeated_prepare_is_idempotent(factory: sessionmaker[Session]) -> None:
    tenant_id = _tenant()
    with factory() as session:
        _condition_id, _subject_id, _sap_object, _plm_object, _plm_field = (
            _seed_consistency_finding(session, tenant_id=tenant_id)
        )
        session.commit()
        finding_id = session.execute(
            select(QualityComparisonFindingORM.finding_id).where(
                QualityComparisonFindingORM.tenant_id == tenant_id
            )
        ).scalar_one()

    with factory() as session:
        first = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=finding_id, requested_by="steward-a"
        )
    with factory() as session:
        second = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=finding_id, requested_by="steward-a"
        )

    assert first.case_id == second.case_id
    assert first.candidates == second.candidates
    assert [i.instruction_id for i in first.instructions] == [
        i.instruction_id for i in second.instructions
    ]
    assert [a.authorization_id for a in first.authorizations] == [
        a.authorization_id for a in second.authorizations
    ]

    with factory() as session:
        candidate_count = len(
            session.execute(
                select(OqiRemediationCandidateORM).where(
                    OqiRemediationCandidateORM.case_id == first.case_id
                )
            )
            .scalars()
            .all()
        )
        instruction_count = len(
            session.execute(
                select(OqiRemediationInstructionORM).where(
                    OqiRemediationInstructionORM.case_id == first.case_id
                )
            )
            .scalars()
            .all()
        )
        authorization_count = len(
            session.execute(
                select(OqiRemediationAuthorizationORM).where(
                    OqiRemediationAuthorizationORM.instruction_id.in_(
                        [i.instruction_id for i in first.instructions]
                    )
                )
            )
            .scalars()
            .all()
        )
    assert candidate_count == len(first.candidates) == 1
    assert instruction_count == 1
    assert authorization_count == 1


# =====================================================================
# Concurrent preparation for the identical Finding converges -- CDD-058
# SS14/SS21-SS23: zero uncaught IntegrityError, exactly one instruction
# and one authorization per candidate, even though the instruction table
# carries no unique constraint on `candidate_id`.
# =====================================================================


def test_concurrent_prepare_same_finding_converges(migrated_engine: Engine) -> None:
    factory_ = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = _tenant()
    with factory_() as session:
        _seed_consistency_finding(session, tenant_id=tenant_id)
        session.commit()
        finding_id = session.execute(
            select(QualityComparisonFindingORM.finding_id).where(
                QualityComparisonFindingORM.tenant_id == tenant_id
            )
        ).scalar_one()

    errors: list[BaseException] = []

    def _prepare(session: Session, requested_by: str) -> None:
        try:
            _orchestrator(session).prepare_remediation(
                tenant_id=tenant_id, finding_id=finding_id, requested_by=requested_by
            )
        except BaseException as exc:  # noqa: BLE001 -- captured for the assertion below
            errors.append(exc)

    session_a, session_b = factory_(), factory_()
    thread_a = threading.Thread(target=_prepare, args=(session_a, "steward-a"))
    thread_b = threading.Thread(target=_prepare, args=(session_b, "steward-b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=15)
    thread_b.join(timeout=15)
    session_a.close()
    session_b.close()

    assert errors == []

    with factory_() as session:
        cases = (
            session.execute(
                select(OqiRemediationCaseORM).where(OqiRemediationCaseORM.finding_id == finding_id)
            )
            .scalars()
            .all()
        )
        assert len(cases) == 1
        candidates = (
            session.execute(
                select(OqiRemediationCandidateORM).where(
                    OqiRemediationCandidateORM.case_id == cases[0].case_id
                )
            )
            .scalars()
            .all()
        )
        assert len(candidates) == 1
        instructions = (
            session.execute(
                select(OqiRemediationInstructionORM).where(
                    OqiRemediationInstructionORM.candidate_id == candidates[0].candidate_id
                )
            )
            .scalars()
            .all()
        )
        assert len(instructions) == 1
        authorizations = (
            session.execute(
                select(OqiRemediationAuthorizationORM).where(
                    OqiRemediationAuthorizationORM.instruction_id == instructions[0].instruction_id
                )
            )
            .scalars()
            .all()
        )
        assert len(authorizations) == 1


def test_concurrent_prepare_across_tenants_does_not_cross_contaminate(
    migrated_engine: Engine,
) -> None:
    factory_ = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_a, tenant_b = _tenant(), _tenant()
    finding_ids: dict[str, UUID] = {}
    for tenant_id in (tenant_a, tenant_b):
        with factory_() as session:
            _seed_consistency_finding(session, tenant_id=tenant_id)
            session.commit()
            finding_ids[tenant_id] = session.execute(
                select(QualityComparisonFindingORM.finding_id).where(
                    QualityComparisonFindingORM.tenant_id == tenant_id
                )
            ).scalar_one()

    results: dict[str, UUID] = {}

    def _prepare(session: Session, tenant_id: str) -> None:
        result = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=finding_ids[tenant_id], requested_by="steward"
        )
        results[tenant_id] = result.case_id

    session_a, session_b = factory_(), factory_()
    thread_a = threading.Thread(target=_prepare, args=(session_a, tenant_a))
    thread_b = threading.Thread(target=_prepare, args=(session_b, tenant_b))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=15)
    thread_b.join(timeout=15)
    session_a.close()
    session_b.close()

    assert results[tenant_a] != results[tenant_b]
    with factory_() as session:
        for tenant_id in (tenant_a, tenant_b):
            case = session.get(OqiRemediationCaseORM, results[tenant_id])
            assert case is not None and case.tenant_id == tenant_id


# =====================================================================
# Cross-tenant attack at the reevaluation hop -- CDD-058 SS19.
# =====================================================================


def test_reevaluate_cross_tenant_authorization_returns_none(
    factory: sessionmaker[Session],
) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    with factory() as session:
        _seed_consistency_finding(session, tenant_id=tenant_a)
        session.commit()
        finding_id = session.execute(
            select(QualityComparisonFindingORM.finding_id).where(
                QualityComparisonFindingORM.tenant_id == tenant_a
            )
        ).scalar_one()

    with factory() as session:
        prepared = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_a, finding_id=finding_id, requested_by="steward-a"
        )
    authorization_id = prepared.authorizations[0].authorization_id

    with factory() as session:
        result = _orchestrator(session).reevaluate_after_execution(
            tenant_id=tenant_b, authorization_id=authorization_id
        )
    assert result is None

    with factory() as session:
        finding = session.get(QualityComparisonFindingORM, finding_id)
        assert finding is not None and finding.status == "OPEN"


def test_reevaluate_unknown_authorization_returns_none(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        result = _orchestrator(session).reevaluate_after_execution(
            tenant_id=_tenant(), authorization_id=uuid4()
        )
    assert result is None


# =====================================================================
# Genuine connection-failure crown -- a real, non-mocked mid-flight
# connection loss during reevaluation must never falsely resolve the
# underlying Finding, and (CDD-058 SS28: "reevaluation failure never
# affects this endpoint's own response") must be safely absorbable by the
# router's own outer `except Exception: session.rollback()` around the
# whole `reevaluate_after_execution` call -- proven here directly by
# asserting the exact same real exception class the router's `except`
# clause is written to catch.
# =====================================================================


def test_reevaluate_genuine_connection_failure_never_falsely_resolves(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = _tenant()
    with factory() as session:
        _seed_consistency_finding(session, tenant_id=tenant_id)
        session.commit()
        finding_id = session.execute(
            select(QualityComparisonFindingORM.finding_id).where(
                QualityComparisonFindingORM.tenant_id == tenant_id
            )
        ).scalar_one()

    with factory() as session:
        prepared = _orchestrator(session).prepare_remediation(
            tenant_id=tenant_id, finding_id=finding_id, requested_by="steward-a"
        )
    authorization_id = prepared.authorizations[0].authorization_id

    with factory() as session:
        service = OqiRemediationService(
            repository=OqiRemediationRepositoryImpl(session),
            participant_reader=OqiRemediationParticipantReader(session),
        )
        service.approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="steward-b", now=NOW
        )
        session.commit()
        service.report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id, now=NOW
        )
        session.commit()

        # A genuine, real Postgres connection loss (not a mock): invalidate
        # the DBAPI connection this session is bound to mid-flight, so every
        # subsequent statement this method issues raises a real
        # `sqlalchemy.exc` error -- exactly the class of failure the
        # router's own outer `try/except Exception: session.rollback()`
        # around this call exists to absorb (CDD-058 SS28).
        session.connection().invalidate()

        orchestrator = _orchestrator(session)
        with pytest.raises(Exception):  # noqa: B017 -- a real, unmocked DBAPI/SQLAlchemy error
            orchestrator.reevaluate_after_execution(
                tenant_id=tenant_id, authorization_id=authorization_id
            )
        session.rollback()

    with factory() as session:
        finding = session.get(QualityComparisonFindingORM, finding_id)
        assert finding is not None and finding.status == "OPEN"
        case = session.execute(
            select(OqiRemediationCaseORM).where(OqiRemediationCaseORM.finding_id == finding_id)
        ).scalar_one()
        assert case.status != RemediationCaseStatus.RESOLVED.value


# =====================================================================
# POSTGRES-DATA-MODEL-CLOSURE-I -- CDD-061 SS9.1/SS38: one real-PostgreSQL
# adversarial test proving the remediation authority chain (Case ->
# Instruction -> Authorization, and Case -> Agent Run) is now structurally
# tenant-consistent. Before migration 0046, a single logical chain could
# carry three mutually inconsistent tenant labels with zero PostgreSQL
# rejection (adversarially proven, POSTGRES-DATA-MODEL-CLOSURE-DG SS9.1).
# This is a real, unmocked PostgreSQL constraint proof throughout -- no
# service-layer validation, no Python assertion standing in for a
# database check, no HTTP layer, no mock; every rejection below is a
# genuine `IntegrityError` raised by PostgreSQL's own composite
# foreign-key constraints (`fk_oqi_remediation_instructions_tenant_case`,
# `fk_oqi_remediation_authorizations_tenant_instruction`,
# `fk_oqi_remediation_agent_runs_tenant_case`).
# =====================================================================


def test_remediation_chain_tenant_integrity_enforced_by_real_postgresql(
    factory: sessionmaker[Session],
) -> None:
    # --- Part 1: a genuine, unmocked same-tenant chain persists cleanly. ---
    tenant_id = f"tenant-legit-{uuid4()}"
    legit_case_id = uuid4()
    legit_candidate_id = uuid4()
    legit_instruction_id = uuid4()
    legit_authorization_id = uuid4()
    legit_run_id = uuid4()

    with factory() as session:
        session.add(
            OqiRemediationCaseORM(
                case_id=legit_case_id,
                tenant_id=tenant_id,
                finding_family="BUSINESS_RULE",
                finding_id=uuid4(),
                status=RemediationCaseStatus.CANDIDATE_READY.value,
                created_on=NOW,
                updated_on=NOW,
            )
        )
        session.flush()
        session.add(
            OqiRemediationCandidateORM(
                candidate_id=legit_candidate_id,
                case_id=legit_case_id,
                target_source_object_id=uuid4(),
                target_source_field_id=uuid4(),
                proposed_value="X",
                basis="CROSS_SOURCE_MAJORITY",
                extracted_at=NOW,
            )
        )
        session.flush()
        session.add(
            OqiRemediationInstructionORM(
                instruction_id=legit_instruction_id,
                tenant_id=tenant_id,
                finding_id=uuid4(),
                finding_state_revision=1,
                case_id=legit_case_id,
                candidate_id=legit_candidate_id,
                target_source_object_id=uuid4(),
                target_source_field_id=uuid4(),
                action_type="FIELD_VALUE_UPDATE",
                payload_digest="digest-legit",
                created_by="test",
                created_on=NOW,
            )
        )
        session.flush()
        session.add(
            OqiRemediationAuthorizationORM(
                authorization_id=legit_authorization_id,
                tenant_id=tenant_id,
                instruction_id=legit_instruction_id,
                payload_digest="digest-legit",
                requested_by="test",
                requested_on=NOW,
                status=RemediationAuthorizationStatus.PENDING.value,
            )
        )
        # Raw SQL, not the OqiRemediationAgentRepository -- this proves the
        # PostgreSQL constraint itself, per CDD-043's single-construction-site
        # firewall for AgentRunORM (test_runtime_architecture.py).
        session.execute(
            text(
                "INSERT INTO oqi_remediation_agent_runs "
                "(run_id, tenant_id, case_id, role_id, role_version, provider, model, "
                "evidence_packet_digest, result_state, created_on) "
                "VALUES (:run_id, :tenant_id, :case_id, :role_id, :role_version, :provider, "
                ":model, :digest, :result_state, :created_on)"
            ),
            {
                "run_id": legit_run_id,
                "tenant_id": tenant_id,
                "case_id": legit_case_id,
                "role_id": "role1",
                "role_version": 1,
                "provider": "none",
                "model": "none",
                "digest": "digest-legit",
                "result_state": "SUCCEEDED",
                "created_on": NOW,
            },
        )
        session.commit()

    with factory() as session:
        assert session.get(OqiRemediationInstructionORM, legit_instruction_id) is not None
        assert session.get(OqiRemediationAuthorizationORM, legit_authorization_id) is not None
        assert session.get(AgentRunORM, legit_run_id) is not None

    # --- Part 2: cross-tenant Case -> Instruction is rejected. ---
    owner_tenant = f"tenant-owner-{uuid4()}"
    attacker_tenant = f"tenant-attacker-{uuid4()}"
    case_id = uuid4()
    candidate_id = uuid4()

    with factory() as session:
        session.add(
            OqiRemediationCaseORM(
                case_id=case_id,
                tenant_id=owner_tenant,
                finding_family="BUSINESS_RULE",
                finding_id=uuid4(),
                status=RemediationCaseStatus.CANDIDATE_READY.value,
                created_on=NOW,
                updated_on=NOW,
            )
        )
        session.flush()
        session.add(
            OqiRemediationCandidateORM(
                candidate_id=candidate_id,
                case_id=case_id,
                target_source_object_id=uuid4(),
                target_source_field_id=uuid4(),
                proposed_value="X",
                basis="CROSS_SOURCE_MAJORITY",
                extracted_at=NOW,
            )
        )
        session.flush()
        session.commit()

    with factory() as session:
        # ADVERSARIAL: this instruction claims attacker_tenant but points its
        # case_id at owner_tenant's own case -- the exact shape the original
        # DG adversarial sequence proved PostgreSQL previously accepted.
        session.add(
            OqiRemediationInstructionORM(
                instruction_id=uuid4(),
                tenant_id=attacker_tenant,
                finding_id=uuid4(),
                finding_state_revision=1,
                case_id=case_id,
                candidate_id=candidate_id,
                target_source_object_id=uuid4(),
                target_source_field_id=uuid4(),
                action_type="FIELD_VALUE_UPDATE",
                payload_digest="digest-attack",
                created_by="adversary",
                created_on=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with factory() as session:
        remaining_instructions = (
            session.execute(
                select(OqiRemediationInstructionORM).where(
                    OqiRemediationInstructionORM.case_id == case_id
                )
            )
            .scalars()
            .all()
        )
        assert remaining_instructions == []

    # --- Part 3: cross-tenant Instruction -> Authorization is rejected. ---
    owner_instruction_id = uuid4()
    with factory() as session:
        session.add(
            OqiRemediationInstructionORM(
                instruction_id=owner_instruction_id,
                tenant_id=owner_tenant,
                finding_id=uuid4(),
                finding_state_revision=1,
                case_id=case_id,
                candidate_id=candidate_id,
                target_source_object_id=uuid4(),
                target_source_field_id=uuid4(),
                action_type="FIELD_VALUE_UPDATE",
                payload_digest="digest-owner",
                created_by="test",
                created_on=NOW,
            )
        )
        session.flush()
        session.commit()

    with factory() as session:
        # ADVERSARIAL: this authorization claims attacker_tenant but points
        # its instruction_id at owner_tenant's own instruction.
        session.add(
            OqiRemediationAuthorizationORM(
                authorization_id=uuid4(),
                tenant_id=attacker_tenant,
                instruction_id=owner_instruction_id,
                payload_digest="digest-attack",
                requested_by="adversary",
                requested_on=NOW,
                status=RemediationAuthorizationStatus.PENDING.value,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with factory() as session:
        remaining_authorizations = (
            session.execute(
                select(OqiRemediationAuthorizationORM).where(
                    OqiRemediationAuthorizationORM.instruction_id == owner_instruction_id
                )
            )
            .scalars()
            .all()
        )
        assert remaining_authorizations == []

    # --- Part 4: cross-tenant Case -> Agent Run is rejected. ---
    with factory() as session:
        # ADVERSARIAL: this agent run claims attacker_tenant but points its
        # case_id at owner_tenant's own case. Raw SQL, not the
        # OqiRemediationAgentRepository or AgentRunORM's constructor -- this
        # proves the PostgreSQL constraint itself, per CDD-043's
        # single-construction-site firewall for AgentRunORM
        # (test_runtime_architecture.py).
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO oqi_remediation_agent_runs "
                    "(run_id, tenant_id, case_id, role_id, role_version, provider, model, "
                    "evidence_packet_digest, result_state, created_on) "
                    "VALUES (:run_id, :tenant_id, :case_id, :role_id, :role_version, :provider, "
                    ":model, :digest, :result_state, :created_on)"
                ),
                {
                    "run_id": uuid4(),
                    "tenant_id": attacker_tenant,
                    "case_id": case_id,
                    "role_id": "role1",
                    "role_version": 1,
                    "provider": "none",
                    "model": "none",
                    "digest": "digest-attack",
                    "result_state": "SUCCEEDED",
                    "created_on": NOW,
                },
            )
        session.rollback()

    with factory() as session:
        remaining = (
            session.execute(select(AgentRunORM).where(AgentRunORM.case_id == case_id))
            .scalars()
            .all()
        )
        assert remaining == []

    # --- Part 5: the original three-tenant attack chain (Case=tenant-A,
    # Instruction claims tenant-B, Authorization would have claimed
    # tenant-C) can no longer be persisted -- it is rejected at the very
    # first cross-tenant hop, exactly reproducing
    # POSTGRES-DATA-MODEL-CLOSURE-DG's own live adversarial sequence. ---
    tenant_a = f"tenant-a-{uuid4()}"
    tenant_b = f"tenant-b-{uuid4()}"
    three_tenant_case_id = uuid4()
    three_tenant_candidate_id = uuid4()

    with factory() as session:
        session.add(
            OqiRemediationCaseORM(
                case_id=three_tenant_case_id,
                tenant_id=tenant_a,
                finding_family="BUSINESS_RULE",
                finding_id=uuid4(),
                status=RemediationCaseStatus.CANDIDATE_READY.value,
                created_on=NOW,
                updated_on=NOW,
            )
        )
        session.flush()
        session.add(
            OqiRemediationCandidateORM(
                candidate_id=three_tenant_candidate_id,
                case_id=three_tenant_case_id,
                target_source_object_id=uuid4(),
                target_source_field_id=uuid4(),
                proposed_value="X",
                basis="CROSS_SOURCE_MAJORITY",
                extracted_at=NOW,
            )
        )
        session.flush()
        session.commit()

    with factory() as session:
        session.add(
            OqiRemediationInstructionORM(
                instruction_id=uuid4(),
                tenant_id=tenant_b,
                finding_id=uuid4(),
                finding_state_revision=1,
                case_id=three_tenant_case_id,
                candidate_id=three_tenant_candidate_id,
                target_source_object_id=uuid4(),
                target_source_field_id=uuid4(),
                action_type="FIELD_VALUE_UPDATE",
                payload_digest="digest-attack-3tenant",
                created_by="adversary",
                created_on=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
