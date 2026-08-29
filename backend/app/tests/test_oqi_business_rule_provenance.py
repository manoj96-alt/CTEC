"""OQI3-I2 full evidence-chain reconstruction (CDD-041 §20, §34; Artifact
Authorization §5, §9). Proves, from persisted state alone -- with zero
generated prose -- the explanation chain: `BusinessRuleEvaluation ->
Observation(clause_id, input_role) -> input snapshot -> FieldValueEvidence
-> SourceField -> SourceObject -> SourceSystem`. Also proves the I3
firewall: no `BusinessRuleFinding` row is ever created by any OQI3-I2 code
path, under any outcome."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import sessionmaker

from app.application.oqi_business_rule_evaluation_service import SingleRecordSubject
from app.domain.oqi_business_rule.evaluation import EvaluationOutcome, ObservationType
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_business_rule_evaluation import (
    BusinessRuleEvaluationInputORM,
    BusinessRuleEvaluationObservationORM,
)
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.oqi_business_rule_repository import (
    OqiBusinessRuleRepositoryImpl,
)
from app.tests.test_oqi_business_rule_postgres import (
    _admit_evidence,
    _effective_dates_rule,
    _seed_field_with_object,
    _service,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_full_provenance_chain_reconstructable_for_a_violated_evaluation(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        object_id, start_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="EFFECTIVE_START"
        )
        _, end_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="EFFECTIVE_END"
        )
        rule = _effective_dates_rule(
            tenant_id=tenant_id,
            start_field_id=start_field,
            end_field_id=end_field,
            condition_id=condition_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        _admit_evidence(
            session,
            source_field_id=start_field,
            source_record_reference="MAT-100",
            observed_representation="2026-12-31",
        )
        _admit_evidence(
            session,
            source_field_id=end_field,
            source_record_reference="MAT-100",
            observed_representation="2026-01-01",
        )
        session.commit()

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=object_id, source_record_reference="MAT-100"
    )
    with factory() as session:
        active_rule = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert active_rule is not None
        evaluation = _service(session).evaluate_historical(
            rule=active_rule, subject=subject, evaluation_horizon=NOW
        )
        session.commit()

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED

    # Reconstruct end to end, from persisted state alone, no generated text.
    with factory() as session:
        observations = (
            session.execute(
                select(BusinessRuleEvaluationObservationORM).where(
                    BusinessRuleEvaluationObservationORM.evaluation_id == evaluation.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert len(observations) == 1
        observation = observations[0]
        assert observation.observation_type == ObservationType.CLAUSE_VIOLATED.value
        assert observation.input_role == "effective_start"
        assert observation.clause_id == "start-before-end"

        input_row = session.execute(
            select(BusinessRuleEvaluationInputORM).where(
                BusinessRuleEvaluationInputORM.evaluation_id == evaluation.evaluation_id,
                BusinessRuleEvaluationInputORM.input_role == observation.input_role,
            )
        ).scalar_one()
        assert input_row.field_value_evidence_id is not None

        evidence = session.get(FieldValueEvidenceORM, input_row.field_value_evidence_id)
        assert evidence is not None
        assert evidence.observed_representation == "2026-12-31"

        source_field = session.get(SourceFieldORM, evidence.source_field_id)
        assert source_field is not None
        source_object = session.get(SourceObjectORM, source_field.source_object_id)
        assert source_object is not None
        assert source_object.tenant_id == tenant_id


def test_current_state_style_violated_evaluation_creates_no_finding_row(
    migrated_engine: Engine,
) -> None:
    """I3 firewall: OQI3-I2 implements no Finding lifecycle at all -- proven
    directly against the real `business_rule_findings` table, not merely
    asserted, for a VIOLATED outcome (the one case that would eventually
    open a Finding once OQI3-I3 exists)."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        object_id, start_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="EFFECTIVE_START"
        )
        _, end_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="EFFECTIVE_END"
        )
        rule = _effective_dates_rule(
            tenant_id=tenant_id,
            start_field_id=start_field,
            end_field_id=end_field,
            condition_id=condition_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        _admit_evidence(
            session,
            source_field_id=start_field,
            source_record_reference="MAT-100",
            observed_representation="2026-12-31",
        )
        _admit_evidence(
            session,
            source_field_id=end_field,
            source_record_reference="MAT-100",
            observed_representation="2026-01-01",
        )
        session.commit()

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=object_id, source_record_reference="MAT-100"
    )
    with factory() as session:
        active_rule = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert active_rule is not None
        before = session.execute(text("SELECT count(*) FROM business_rule_findings")).scalar_one()
        evaluation = _service(session).evaluate_historical(
            rule=active_rule, subject=subject, evaluation_horizon=NOW
        )
        session.commit()
        after = session.execute(text("SELECT count(*) FROM business_rule_findings")).scalar_one()

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert before == after  # zero Finding rows created, regardless of how many already existed
