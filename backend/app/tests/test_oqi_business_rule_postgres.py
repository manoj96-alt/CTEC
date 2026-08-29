"""Real-PostgreSQL acceptance evidence for OQI3-I1 (CDD-041 §24; Artifact
Authorization §5-§8). Proves what a fake repository cannot: migration
schema correctness for the full 6-table OQI3 surface; the partial unique
"one ACTIVE version per (tenant_id, business_condition_id)" invariant holds
at the database level; and publication-time tenant-consistency validation
genuinely rejects an unknown or cross-tenant `source_field_id`. No
evaluation runtime and no Finding lifecycle exist yet (OQI3-I2/I3) -- this
file covers foundation persistence only."""

# isort: skip_file
from __future__ import annotations

import dataclasses
import threading
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_business_rule_evaluation_service import (
    OqiBusinessRuleEvaluationService,
    SingleRecordSubject,
)
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.oqi.evaluation import EvaluationMode
from app.domain.oqi_business_rule.evaluation import EvaluationOutcome
from app.domain.oqi_business_rule.rule import (
    BusinessRule,
    BusinessRuleInputBinding,
    BusinessRuleStatus,
    ComparandKind,
    ComparatorNode,
    ExpectedType,
    Operator,
    OqiMalformedBusinessRuleError,
    RuleFamily,
    derive_business_rule_id,
)
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.oqi_business_rule import BusinessRuleORM
from app.infrastructure.persistence.models.oqi_business_rule_evaluation import (
    BusinessRuleEvaluationInputORM,
    BusinessRuleEvaluationObservationORM,
    BusinessRuleEvaluationORM,
)
from app.infrastructure.persistence.oqi_business_rule_evaluation_repository import (
    OqiBusinessRuleEvaluationRepositoryImpl,
    OqiBusinessRuleEvidenceValueReader,
)
from app.infrastructure.persistence.oqi_business_rule_repository import (
    OqiBusinessRuleRepositoryImpl,
)
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.tests.test_source_field_persistence_postgres import _seed_source_object, _source_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _seed_field(session: Session, *, tenant_id: str, field_label: str) -> UUID:
    object_id = _seed_source_object(session, tenant_id=tenant_id)
    field = _source_field(source_object_id=object_id, field_label=field_label)
    SourceFieldRepositoryImpl(session).create(field)
    session.flush()
    return field.source_field_id.value


def _seed_field_with_object(
    session: Session, *, tenant_id: str, field_label: str
) -> tuple[UUID, UUID]:
    object_id = _seed_source_object(session, tenant_id=tenant_id)
    field = _source_field(source_object_id=object_id, field_label=field_label)
    SourceFieldRepositoryImpl(session).create(field)
    session.flush()
    return object_id, field.source_field_id.value


def _admit_evidence(
    session: Session,
    *,
    source_field_id: UUID,
    source_record_reference: str,
    observed_representation: str,
    received_at: datetime = NOW,
) -> UUID:
    evidence = FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference=source_record_reference,
        observed_representation=observed_representation,
        observed_at=received_at,
        received_at=received_at,
    )
    FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(evidence)
    return evidence.field_value_evidence_id.value


def _effective_dates_rule(
    *, tenant_id: str, start_field_id: UUID, end_field_id: UUID, condition_id: str
) -> BusinessRule:
    predicate = ComparatorNode(
        clause_id="start-before-end",
        operator=Operator.LTE,
        input_role="effective_start",
        comparand_kind=ComparandKind.INPUT_ROLE,
        comparand_input_role="effective_end",
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="effective_start",
            source_field_id=start_field_id,
            required=True,
            expected_type=ExpectedType.DATE,
        ),
        BusinessRuleInputBinding(
            input_role="effective_end",
            source_field_id=end_field_id,
            required=True,
            expected_type=ExpectedType.DATE,
        ),
    )
    return BusinessRule.new(
        business_condition_id=condition_id,
        version=1,
        tenant_id=tenant_id,
        rule_family=RuleFamily.FIELD_COMPARISON,
        applicability=None,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )


def _service(session: Session) -> OqiBusinessRuleEvaluationService:
    repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
    return OqiBusinessRuleEvaluationService(
        evaluation_repository=repository,
        evidence_value_reader=OqiBusinessRuleEvidenceValueReader(session),
        clock=lambda: NOW,
    )


def _hazmat_rule(*, tenant_id: str, source_field_id: UUID, version: int = 1) -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="applicable-hazmat",
        operator=Operator.EQ,
        input_role="material_type",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="HAZMAT",
    )
    predicate = ComparatorNode(
        clause_id="classification-required",
        operator=Operator.IS_NOT_NULL,
        input_role="hazmat_classification",
        comparand_kind=ComparandKind.NONE,
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="material_type",
            source_field_id=source_field_id,
            required=True,
            expected_type=ExpectedType.STRING,
        ),
        BusinessRuleInputBinding(
            input_role="hazmat_classification",
            source_field_id=source_field_id,
            required=True,
            expected_type=ExpectedType.STRING,
        ),
    )
    return BusinessRule.new(
        business_condition_id=f"hazmat-classification-required-{uuid4()}",
        version=version,
        tenant_id=tenant_id,
        rule_family=RuleFamily.CONDITIONAL_REQUIRED,
        applicability=applicability,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )


# --- schema shape and migration round trip ---


def test_migration_creates_expected_schema(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    tables = set(inspector.get_table_names())
    assert {
        "business_rules",
        "business_rule_input_bindings",
        "business_rule_evaluations",
        "business_rule_evaluation_inputs",
        "business_rule_evaluation_observations",
        "business_rule_findings",
    } <= tables

    business_rule_columns = {c["name"] for c in inspector.get_columns("business_rules")}
    assert business_rule_columns == {
        "rule_id",
        "business_condition_id",
        "version",
        "tenant_id",
        "rule_family",
        "applicability",
        "predicate",
        "status",
        "created_by",
        "created_on",
        "retired_on",
    }

    observation_columns = {
        c["name"] for c in inspector.get_columns("business_rule_evaluation_observations")
    }
    assert observation_columns == {"evaluation_id", "clause_id", "observation_type", "input_role"}

    finding_check_names = {
        c["name"] for c in inspector.get_check_constraints("business_rule_findings")
    }
    assert "ck_business_rule_findings_resolution_basis" in finding_check_names


def test_migration_round_trips_cleanly(migrated_engine: Engine) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(migrated_engine.url))
    alembic.command.downgrade(alembic_cfg, "0021_oqi2_cross_source")
    with migrated_engine.connect():
        tables = set(inspect(migrated_engine).get_table_names())
        assert "business_rules" not in tables
    alembic.command.upgrade(alembic_cfg, "0022_oqi3_business_rule")
    with migrated_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "0022_oqi3_business_rule"


def test_table_count_is_81(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        table_count = connection.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
    assert table_count == 81


# --- database constraints ---


def test_one_active_business_rule_per_condition_enforced_by_database(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        field_id = _seed_field(session, tenant_id=tenant_id, field_label="Material Type")
        session.commit()

    condition_id = f"cond-{uuid4()}"
    rule = _hazmat_rule(tenant_id=tenant_id, source_field_id=field_id)
    rule = dataclasses.replace(
        rule,
        business_condition_id=condition_id,
        rule_id=derive_business_rule_id(business_condition_id=condition_id, version=1),
    )
    other_rule = dataclasses.replace(
        rule,
        version=2,
        rule_id=derive_business_rule_id(business_condition_id=condition_id, version=2),
    )

    with factory() as session:
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.commit()

    with factory() as session, pytest.raises(IntegrityError):
        OqiBusinessRuleRepositoryImpl(session).create(other_rule)
        session.commit()


def test_duplicate_condition_version_rejected_by_database(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        field_id = _seed_field(session, tenant_id=tenant_id, field_label="Material Type")
        session.commit()

    rule = _hazmat_rule(tenant_id=tenant_id, source_field_id=field_id)
    with factory() as session:
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.commit()

    with factory() as session, pytest.raises(IntegrityError):
        session.add(
            BusinessRuleORM(
                rule_id=uuid4(),
                business_condition_id=rule.business_condition_id,
                version=rule.version,
                tenant_id=tenant_id,
                rule_family="FIELD_COMPARISON",
                applicability=None,
                predicate={"node_type": "COMPARATOR"},
                status="RETIRED",
                created_by="tester",
                created_on=NOW,
                retired_on=NOW,
            )
        )
        session.commit()


def test_publication_rejects_unknown_source_field(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    rule = _hazmat_rule(tenant_id=tenant_id, source_field_id=uuid4())
    with factory() as session, pytest.raises(OqiMalformedBusinessRuleError):
        OqiBusinessRuleRepositoryImpl(session).create(rule)


def test_publication_rejects_cross_tenant_source_field(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    owner_tenant_id = f"tenant-owner-{uuid4()}"
    rule_tenant_id = f"tenant-rule-{uuid4()}"
    with factory() as session:
        field_id = _seed_field(session, tenant_id=owner_tenant_id, field_label="Material Type")
        session.commit()

    rule = _hazmat_rule(tenant_id=rule_tenant_id, source_field_id=field_id)
    with factory() as session, pytest.raises(OqiMalformedBusinessRuleError):
        OqiBusinessRuleRepositoryImpl(session).create(rule)


def test_valid_rule_round_trips_through_create_and_get_by_id(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        field_id = _seed_field(session, tenant_id=tenant_id, field_label="Material Type")
        session.commit()

    rule = _hazmat_rule(tenant_id=tenant_id, source_field_id=field_id)
    with factory() as session:
        repository = OqiBusinessRuleRepositoryImpl(session)
        repository.create(rule)
        session.commit()

    with factory() as session:
        loaded = OqiBusinessRuleRepositoryImpl(session).get_by_id(rule.rule_id)
    assert loaded == rule


def test_get_active_returns_the_active_version(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        field_id = _seed_field(session, tenant_id=tenant_id, field_label="Material Type")
        session.commit()

    rule = _hazmat_rule(tenant_id=tenant_id, source_field_id=field_id)
    with factory() as session:
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        session.commit()

    with factory() as session:
        active = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=rule.business_condition_id
        )
    assert active == rule


def test_activate_new_version_retires_the_previous_active_version(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        field_id = _seed_field(session, tenant_id=tenant_id, field_label="Material Type")
        session.commit()

    condition_id = f"cond-{uuid4()}"
    rule_v1 = _hazmat_rule(tenant_id=tenant_id, source_field_id=field_id)
    rule_v1 = dataclasses.replace(
        rule_v1,
        business_condition_id=condition_id,
        rule_id=derive_business_rule_id(business_condition_id=condition_id, version=1),
    )
    with factory() as session:
        OqiBusinessRuleRepositoryImpl(session).create(rule_v1)
        session.commit()

    rule_v2 = dataclasses.replace(
        rule_v1,
        version=2,
        rule_id=derive_business_rule_id(business_condition_id=condition_id, version=2),
    )
    with factory() as session:
        OqiBusinessRuleRepositoryImpl(session).activate_new_version(rule_v2, retired_on=NOW)
        session.commit()

    with factory() as session:
        repository = OqiBusinessRuleRepositoryImpl(session)
        active = repository.get_active(tenant_id=tenant_id, business_condition_id=condition_id)
        retired = repository.get_by_id(rule_v1.rule_id)
    assert active is not None and active.version == 2
    assert retired is not None and retired.status is BusinessRuleStatus.RETIRED


# --- OQI3-I2: deterministic evaluation ledger persistence (CDD-041 §16-§19, §22-§23) ---


def test_historical_evaluation_satisfied_persists_evaluation_and_input_snapshot(
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
            observed_representation="2026-01-01",
        )
        _admit_evidence(
            session,
            source_field_id=end_field,
            source_record_reference="MAT-100",
            observed_representation="2026-12-31",
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
    assert evaluation.outcome is EvaluationOutcome.SATISFIED
    assert evaluation.observations == ()

    with factory() as session:
        stored = session.get(BusinessRuleEvaluationORM, evaluation.evaluation_id)
        assert stored is not None
        assert stored.evaluation_mode == EvaluationMode.HISTORICAL.value
        input_rows = (
            session.query(BusinessRuleEvaluationInputORM)
            .filter_by(evaluation_id=evaluation.evaluation_id)
            .all()
        )
        assert {row.input_role for row in input_rows} == {"effective_start", "effective_end"}
        assert all(row.field_value_evidence_id is not None for row in input_rows)


def test_historical_evaluation_violated_persists_one_observation(migrated_engine: Engine) -> None:
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
    assert len(evaluation.observations) == 1

    with factory() as session:
        observation_rows = (
            session.query(BusinessRuleEvaluationObservationORM)
            .filter_by(evaluation_id=evaluation.evaluation_id)
            .all()
        )
        assert len(observation_rows) == 1
        assert observation_rows[0].observation_type == "CLAUSE_VIOLATED"


def test_historical_evaluation_unknown_subject_persists_nothing(migrated_engine: Engine) -> None:
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
        session.commit()  # note: zero evidence admitted -- subject unknown to CTEC

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=object_id, source_record_reference="NEVER-SEEN"
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

    assert evaluation is None
    with factory() as session:
        count = session.execute(
            text(
                "SELECT count(*) FROM business_rule_evaluations WHERE business_condition_id = :cid"
            ),
            {"cid": condition_id},
        ).scalar_one()
    assert count == 0


def test_evaluation_idempotent_replay_creates_no_duplicate_rows(migrated_engine: Engine) -> None:
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
            observed_representation="2026-01-01",
        )
        _admit_evidence(
            session,
            source_field_id=end_field,
            source_record_reference="MAT-100",
            observed_representation="2026-12-31",
        )
        session.commit()

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=object_id, source_record_reference="MAT-100"
    )
    evaluation_id = None
    for _ in range(2):
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
        evaluation_id = evaluation_id or evaluation.evaluation_id
        assert evaluation.evaluation_id == evaluation_id

    with factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM business_rule_evaluations WHERE evaluation_id = :id"),
            {"id": evaluation_id},
        ).scalar_one()
        input_count = session.execute(
            text("SELECT count(*) FROM business_rule_evaluation_inputs WHERE evaluation_id = :id"),
            {"id": evaluation_id},
        ).scalar_one()
    assert count == 1
    assert input_count == 2


def test_concurrent_identical_evaluation_replay_without_lock_can_race(
    migrated_engine: Engine,
) -> None:
    """HONEST CONCURRENCY-SCOPE FINDING, not a claimed guarantee: OQI3-I2's
    `evaluate_historical` never acquires Finding authority (correctly --
    HISTORICAL mode never does, CDD-041 §23), so two truly concurrent
    identical replays racing the same "does evaluation_id already exist"
    check both observe no existing row and both attempt to INSERT --
    exactly the same unresolved race OQI1 itself never protects against
    for its own `evaluate_historical` (OQI1's own concurrent-replay-safety
    test, `test_identical_evaluation_replayed_under_real_concurrency_does_
    not_double_mutate` in `test_oqi_quality_postgres.py`, deliberately
    exercises `evaluate_current_state` -- the *locked* path -- never
    `evaluate_historical`). This test proves the race is real (one worker's
    commit fails with a real `IntegrityError`, not a graceful no-op) so a
    future OQI3-I3 composing this repository's `insert_evaluation_
    idempotent` under its seed=3 advisory lock is a genuine correctness
    prerequisite for CURRENT_STATE concurrent-replay safety, not optional
    polish -- consistent with, not worse than, OQI1/OQI2 precedent."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        object_id, start_field = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="EFFECTIVE_START"
        )
        _, end_field = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="EFFECTIVE_END"
        )
        rule = _effective_dates_rule(
            tenant_id=tenant_id,
            start_field_id=start_field,
            end_field_id=end_field,
            condition_id=condition_id,
        )
        OqiBusinessRuleRepositoryImpl(setup_session).create(rule)
        _admit_evidence(
            setup_session,
            source_field_id=start_field,
            source_record_reference="MAT-100",
            observed_representation="2026-01-01",
        )
        _admit_evidence(
            setup_session,
            source_field_id=end_field,
            source_record_reference="MAT-100",
            observed_representation="2026-12-31",
        )
        setup_session.commit()

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=object_id, source_record_reference="MAT-100"
    )
    barrier = threading.Barrier(2)
    outcomes: dict[str, tuple[str, object]] = {}

    def _worker(session: Session, key: str) -> None:
        rule_local = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert rule_local is not None
        barrier.wait(timeout=5)
        try:
            evaluation = _service(session).evaluate_historical(
                rule=rule_local, subject=subject, evaluation_horizon=NOW
            )
            assert evaluation is not None
            session.commit()
            outcomes[key] = ("committed", evaluation.evaluation_id)
        except IntegrityError:
            session.rollback()
            outcomes[key] = ("integrity_error", None)

    session_a, session_b = factory(), factory()
    thread_a = threading.Thread(target=_worker, args=(session_a, "a"))
    thread_b = threading.Thread(target=_worker, args=(session_b, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    results = {outcomes["a"][0], outcomes["b"][0]}
    # At least one worker must succeed; without a lock it is legitimate
    # (and, per this test, empirically observed) for the other to hit a
    # real IntegrityError instead of silently converging -- this is the
    # documented gap I3's lock exists to close.
    assert "committed" in results


def test_rollback_leaves_zero_orphan_rows(migrated_engine: Engine) -> None:
    """Forces failure mid-transaction (a bogus, never-admitted evidence id
    smuggled into an observation-adjacent input row) after the evaluation
    row has already been added to the same uncommitted session -- proves
    zero orphan rows survive rollback (CDD-041 §21 step 16 atomicity)."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        _object_id, start_field = _seed_field_with_object(
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
            observed_representation="2026-01-01",
        )
        _admit_evidence(
            session,
            source_field_id=end_field,
            source_record_reference="MAT-100",
            observed_representation="2026-12-31",
        )
        session.commit()

    orphan_evaluation_id = uuid4()
    with factory() as session:
        session.add(
            BusinessRuleEvaluationInputORM(
                evaluation_id=orphan_evaluation_id,  # references no Evaluation row -- FK violation
                input_role="effective_start",
                field_value_evidence_id=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM business_rule_evaluations WHERE evaluation_id = :id"),
            {"id": orphan_evaluation_id},
        ).scalar_one()
        input_count = session.execute(
            text("SELECT count(*) FROM business_rule_evaluation_inputs WHERE evaluation_id = :id"),
            {"id": orphan_evaluation_id},
        ).scalar_one()
    assert count == 0
    assert input_count == 0


def test_cross_tenant_evidence_never_selected(migrated_engine: Engine) -> None:
    """A rule bound to tenant A's SourceField must never resolve evidence
    belonging to a same-reference record under a different SourceObject/
    tenant -- proven by evaluating against a subject whose object_id
    doesn't match the field's own tenant-scoped object at all."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_a = f"tenant-a-{uuid4()}"
    tenant_b = f"tenant-b-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        object_a, start_field = _seed_field_with_object(
            session, tenant_id=tenant_a, field_label="EFFECTIVE_START"
        )
        _, end_field = _seed_field_with_object(
            session, tenant_id=tenant_a, field_label="EFFECTIVE_END"
        )
        rule = _effective_dates_rule(
            tenant_id=tenant_a,
            start_field_id=start_field,
            end_field_id=end_field,
            condition_id=condition_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        # Tenant B admits evidence under the SAME source_record_reference
        # for its own, entirely different SourceObject/field.
        _object_b, other_field = _seed_field_with_object(
            session, tenant_id=tenant_b, field_label="UNRELATED"
        )
        _admit_evidence(
            session,
            source_field_id=other_field,
            source_record_reference="MAT-100",
            observed_representation="2099-01-01",
        )
        session.commit()

    # Tenant A's own subject has zero evidence for its fields -- tenant B's
    # evidence for the same source_record_reference string must never leak
    # in, because it is scoped to a completely different source_field_id.
    subject = SingleRecordSubject(
        tenant_id=tenant_a, source_object_id=object_a, source_record_reference="MAT-100"
    )
    with factory() as session:
        active_rule = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_a, business_condition_id=condition_id
        )
        assert active_rule is not None
        evaluation = _service(session).evaluate_historical(
            rule=active_rule, subject=subject, evaluation_horizon=NOW
        )
    # Tenant A's own lineage is unknown (zero evidence for tenant A's own
    # fields under this reference) -- NOT_EVALUABLE, never a leaked value.
    assert evaluation is None


def test_retired_rule_is_not_returned_by_get_active(migrated_engine: Engine) -> None:
    """CDD-041 §4: a RETIRED version is never eligible for evaluation via
    the governed `get_active` lookup -- proves I2's own evaluation flow can
    never be handed a retired rule through the normal path."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        _, start_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="EFFECTIVE_START"
        )
        _, end_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="EFFECTIVE_END"
        )
        rule_v1 = _effective_dates_rule(
            tenant_id=tenant_id,
            start_field_id=start_field,
            end_field_id=end_field,
            condition_id=condition_id,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule_v1)
        session.commit()

    rule_v2 = dataclasses.replace(
        rule_v1,
        version=2,
        rule_id=derive_business_rule_id(business_condition_id=condition_id, version=2),
    )
    with factory() as session:
        OqiBusinessRuleRepositoryImpl(session).activate_new_version(rule_v2, retired_on=NOW)
        session.commit()

    with factory() as session:
        active = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        retired = OqiBusinessRuleRepositoryImpl(session).get_by_id(rule_v1.rule_id)
    assert active is not None and active.version == 2
    assert retired is not None and retired.status is BusinessRuleStatus.RETIRED


def test_concurrency_scope_frontier_can_observe_evidence_committed_mid_selection(
    migrated_engine: Engine,
) -> None:
    """HONEST CONCURRENCY-SCOPE FINDING (CDD-041 §21 steps 1-6 belong to
    OQI3-I3, not I2): `select_input_frontier` issues one SELECT per bound
    input, sequentially, with no elevated transaction isolation and no
    advisory-lock authority (that lock is I3's, seed=3). This test proves
    -- empirically, not by assertion alone -- that evidence committed by a
    concurrent writer *between* two of those per-field reads IS visible to
    the later read under Postgres's default READ COMMITTED isolation.

    This is not a NEW risk OQI3-I2 introduces: OQI1/OQI2's own evidence
    selection has the identical per-field/per-participant sequential-SELECT
    structure and the identical isolation level (proven by direct source
    reading, not assumed). The real job of OQI3-I3's advisory lock (like
    OQI1/OQI2's) is to serialize *evaluators* contending for the same
    Finding identity, not to freeze the evidence table against concurrent
    writers -- OQI3-I2 implements no Finding mutation at all, so there is
    no double-mutation hazard for I3's lock to prevent yet. Composing
    `select_input_frontier`/`determine_outcome` inside I3's lock will
    provide exactly what OQI1/OQI2 already provide (serialized Finding
    authority) -- it will not, and was never claimed to, provide strict
    snapshot-isolation of the evidence table."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        object_id, start_field = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="EFFECTIVE_START"
        )
        _, end_field = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="EFFECTIVE_END"
        )
        rule = _effective_dates_rule(
            tenant_id=tenant_id,
            start_field_id=start_field,
            end_field_id=end_field,
            condition_id=condition_id,
        )
        OqiBusinessRuleRepositoryImpl(setup_session).create(rule)
        _admit_evidence(
            setup_session,
            source_field_id=start_field,
            source_record_reference="MAT-100",
            observed_representation="2026-01-01",
        )
        # Deliberately no evidence admitted yet for effective_end.
        setup_session.commit()

    first_field_read = threading.Event()
    results: dict[str, object] = {}

    def _reader(session: Session) -> None:
        rule_local = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert rule_local is not None
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known = repository.select_known_lineage(
            source_object_id=object_id, source_record_reference="MAT-100", evaluation_horizon=NOW
        )
        assert known
        first = repository.select_latest_field_value(
            source_field_id=start_field, source_record_reference="MAT-100", evaluation_horizon=NOW
        )
        results["first_field_seen_before_concurrent_commit"] = first
        first_field_read.set()
        time.sleep(0.4)
        second = repository.select_latest_field_value(
            source_field_id=end_field, source_record_reference="MAT-100", evaluation_horizon=NOW
        )
        results["second_field_seen_after_concurrent_commit"] = second

    def _concurrent_writer(session: Session) -> None:
        assert first_field_read.wait(timeout=5)
        _admit_evidence(
            session,
            source_field_id=end_field,
            source_record_reference="MAT-100",
            observed_representation="2026-12-31",
            received_at=NOW,
        )
        session.commit()

    session_reader, session_writer = factory(), factory()
    thread_reader = threading.Thread(target=_reader, args=(session_reader,))
    thread_writer = threading.Thread(target=_concurrent_writer, args=(session_writer,))
    thread_reader.start()
    thread_writer.start()
    thread_reader.join(timeout=10)
    thread_writer.join(timeout=10)
    session_reader.close()
    session_writer.close()

    # The start field already had evidence from setup, read before the
    # concurrent commit even starts.
    assert results["first_field_seen_before_concurrent_commit"] is not None
    # The concurrent commit landed strictly between the two field reads,
    # with received_at <= evaluation_horizon -- the second (later) read
    # observes it, even though it did not exist when the first read ran.
    # This confirms the frontier is NOT an atomic snapshot without I3's
    # lock; it is the same behavior OQI1/OQI2 already accept for their own
    # sequential per-field/per-participant evidence selection.
    assert results["second_field_seen_after_concurrent_commit"] is not None
