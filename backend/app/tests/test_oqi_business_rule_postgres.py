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
from typing import Any
from uuid import UUID, uuid4

import alembic.command
from alembic.script import ScriptDirectory
import pytest
from alembic.config import Config
from sqlalchemy import Engine, event, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_business_rule_evaluation_service import (
    OqiBusinessRuleEvaluationService,
    SingleRecordSubject,
    determine_outcome,
    select_input_frontier,
)
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.oqi.evaluation import EvaluationMode
from app.domain.oqi_business_rule.evaluation import (
    SUBJECT_TYPE_SINGLE_RECORD,
    BusinessRuleEvaluation,
    BusinessRuleEvaluationInputEntry,
    EvaluationOutcome,
    canonical_single_record_subject_identity,
    derive_business_rule_evaluation_id,
    input_evidence_digest,
)
from app.domain.oqi_business_rule.rule import (
    BusinessRule,
    BusinessRuleInputBinding,
    BusinessRuleStatus,
    ComparandKind,
    ComparatorNode,
    CompositionNode,
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
    _build_evidence_frontier_statement,
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


def _multi_required_rule(
    *,
    tenant_id: str,
    status_field_id: UUID,
    group_field_id: UUID,
    type_field_id: UUID,
    condition_id: str,
) -> BusinessRule:
    """CDD-041 §4.2/§4.5 (OQI3-G2/I2-R): AND-compound CONDITIONAL_REQUIRED
    -- one governed policy, two independently observable required-input
    clauses."""
    applicability = ComparatorNode(
        clause_id="applicable-active",
        operator=Operator.EQ,
        input_role="lifecycle_status",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="ACTIVE",
    )
    predicate = CompositionNode(
        operator=Operator.AND,
        children=(
            ComparatorNode(
                clause_id="planning-group-required",
                operator=Operator.IS_NOT_NULL,
                input_role="planning_group",
                comparand_kind=ComparandKind.NONE,
            ),
            ComparatorNode(
                clause_id="procurement-type-required",
                operator=Operator.IS_NOT_NULL,
                input_role="procurement_type",
                comparand_kind=ComparandKind.NONE,
            ),
        ),
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="lifecycle_status",
            source_field_id=status_field_id,
            required=True,
            expected_type=ExpectedType.STRING,
        ),
        BusinessRuleInputBinding(
            input_role="planning_group",
            source_field_id=group_field_id,
            required=False,
            expected_type=ExpectedType.STRING,
        ),
        BusinessRuleInputBinding(
            input_role="procurement_type",
            source_field_id=type_field_id,
            required=False,
            expected_type=ExpectedType.STRING,
        ),
    )
    return BusinessRule.new(
        business_condition_id=condition_id,
        version=1,
        tenant_id=tenant_id,
        rule_family=RuleFamily.CONDITIONAL_REQUIRED,
        applicability=applicability,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
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
    # CDD-048 §14 (OQI-H2-I-R1 narrow correction, disclosed in the OQI-H2-I
    # final report): "dimension" is a new, additive column (migration 0030).
    assert business_rule_columns == {
        "rule_id",
        "dimension",
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
    alembic.command.upgrade(alembic_cfg, "head")
    with migrated_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    current_head = ScriptDirectory.from_config(alembic_cfg).get_current_head()
    assert revision == current_head


def test_table_count_is_86(migrated_engine: Engine) -> None:
    # Mechanical migration-head consequence (CDD-042 Artifact Authorization
    # §2 row 13): this file's own literal table-count expectation, distinct
    # from `test_persistence_integration.py`'s, must track the current head
    # the same way its Alembic-head literal already does. CDD-048
    # (OQI-H2-I-R1 narrow correction, disclosed in the OQI-H2-I final
    # report; OQI-H3-I-R1 amendment): mechanically re-pinned from 109 to 114.
    with migrated_engine.connect() as connection:
        table_count = connection.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
    assert table_count == 120


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
        assert loaded is not None
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
        assert active is not None
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


def test_evaluation_reconstructs_source_object_id_when_all_consequence_inputs_are_empty(
    migrated_engine: Engine,
) -> None:
    """CDD-041 §3-§3.1 (OQI3-G2/I2-R), P2-A closure: the case indirect
    reconstruction could never handle -- the bound consequence input has
    zero qualifying evidence (EMPTY, no evidence-link row at all), so
    `EvaluationInput -> SourceField -> SourceObject` has no path. Read-back
    must still reconstruct the exact original `source_object_id` because it
    is persisted directly on `business_rule_evaluations`, not derived from
    evidence links."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        object_id, material_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="MATERIAL_TYPE"
        )
        _, classification_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="HAZMAT_CLASSIFICATION"
        )
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
                source_field_id=material_field,
                required=True,
                expected_type=ExpectedType.STRING,
            ),
            BusinessRuleInputBinding(
                input_role="hazmat_classification",
                source_field_id=classification_field,
                required=False,
                expected_type=ExpectedType.STRING,
            ),
        )
        rule = BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=applicability,
            predicate=predicate,
            input_bindings=bindings,
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        _admit_evidence(
            session,
            source_field_id=material_field,
            source_record_reference="MAT-100",
            observed_representation="HAZMAT",
        )
        # Deliberately no evidence at all for hazmat_classification -- the
        # required consequence input is completely EMPTY.
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
    assert evaluation.source_object_id == object_id  # write-time value, in-memory

    with factory() as session:
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        reloaded = repository.get_evaluation(evaluation.evaluation_id)
    assert reloaded is not None
    # Read-back reconstruction: not derived from any evidence-link FK path
    # (there is none -- the consequence input is EMPTY), purely from the
    # persisted source_object_id column.
    assert reloaded.source_object_id == object_id
    assert reloaded.subject_identity == evaluation.subject_identity


def test_evaluation_source_object_id_is_the_subjects_not_derived_from_bindings(
    migrated_engine: Engine,
) -> None:
    """CDD-041 §3 (OQI3-G2/I2-R), P2-A closure: proves no cross-SourceObject
    ambiguity route exists -- a rule's bound consequence field may belong
    to a SourceObject entirely different from the evaluation subject's own
    `source_object_id` (nothing in publication validation or the evaluator
    enforces they match); the persisted/read-back `source_object_id` must
    always be exactly the subject's explicit value, never inferred from
    whichever bound field happens to have evidence."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        subject_object_id, gate_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="GATE"
        )
        # A deliberately DIFFERENT SourceObject owns the bound consequence
        # field -- nothing prevents this today, and the persisted subject
        # identity must not be affected by it either way.
        _other_object_id, target_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="TARGET"
        )
        applicability = ComparatorNode(
            clause_id="applicable-gate",
            operator=Operator.EQ,
            input_role="gate",
            comparand_kind=ComparandKind.LITERAL,
            literal_type=ExpectedType.STRING,
            literal_value="YES",
        )
        predicate = ComparatorNode(
            clause_id="target-required",
            operator=Operator.IS_NOT_NULL,
            input_role="target",
            comparand_kind=ComparandKind.NONE,
        )
        bindings = (
            BusinessRuleInputBinding(
                input_role="gate",
                source_field_id=gate_field,
                required=True,
                expected_type=ExpectedType.STRING,
            ),
            BusinessRuleInputBinding(
                input_role="target",
                source_field_id=target_field,
                required=False,
                expected_type=ExpectedType.STRING,
            ),
        )
        rule = BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=applicability,
            predicate=predicate,
            input_bindings=bindings,
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        _admit_evidence(
            session,
            source_field_id=gate_field,
            source_record_reference="MAT-100",
            observed_representation="YES",
        )
        # target field's evidence, if any, would belong to the OTHER
        # SourceObject -- deliberately none admitted (EMPTY), so there is
        # no evidence-link path to any SourceObject at all.
        session.commit()

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=subject_object_id, source_record_reference="MAT-100"
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
    assert evaluation.source_object_id == subject_object_id

    with factory() as session:
        reloaded = OqiBusinessRuleEvaluationRepositoryImpl(session).get_evaluation(
            evaluation.evaluation_id
        )
    assert reloaded is not None
    assert reloaded.source_object_id == subject_object_id


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


def test_concurrent_identical_historical_replay_converges_without_integrity_error(
    migrated_engine: Engine,
) -> None:
    """CDD-041 §5.1-§5.2 (OQI3-G2/I2-R): two truly concurrent identical
    `evaluate_historical` replays must converge on one immutable ledger
    row-set and never expose a uniqueness `IntegrityError` to the caller.
    The parent-gated `INSERT ... ON CONFLICT (evaluation_id) DO NOTHING
    RETURNING` pattern closes the race the previous (pre-I2-R) check-then-
    insert implementation could not: both workers now commit successfully,
    and exactly one complete, non-duplicated child row-set exists."""
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

    assert outcomes["a"][0] == "committed"
    assert outcomes["b"][0] == "committed"
    assert outcomes["a"][1] == outcomes["b"][1]  # same deterministic evaluation_id

    with factory() as session:
        evaluation_count = session.execute(
            text("SELECT count(*) FROM business_rule_evaluations WHERE evaluation_id = :id"),
            {"id": outcomes["a"][1]},
        ).scalar_one()
        input_count = session.execute(
            text("SELECT count(*) FROM business_rule_evaluation_inputs WHERE evaluation_id = :id"),
            {"id": outcomes["a"][1]},
        ).scalar_one()
    assert evaluation_count == 1
    assert input_count == 2  # one row per bound input, never duplicated


def test_concurrent_identical_historical_replay_violated_compound_converges(
    migrated_engine: Engine,
) -> None:
    """CDD-041 §5.1-§5.2/§4 (OQI3-G2/I2-R): the strongest historical-replay
    regression -- two concurrent identical replays of a compound VIOLATED
    rule converge on one Evaluation with the complete expected multi-
    observation set, never a partial or duplicated child ledger."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        object_id, status_field = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="LIFECYCLE_STATUS"
        )
        _, group_field = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="PLANNING_GROUP"
        )
        _, type_field = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="PROCUREMENT_TYPE"
        )
        rule = _multi_required_rule(
            tenant_id=tenant_id,
            status_field_id=status_field,
            group_field_id=group_field,
            type_field_id=type_field,
            condition_id=condition_id,
        )
        OqiBusinessRuleRepositoryImpl(setup_session).create(rule)
        _admit_evidence(
            setup_session,
            source_field_id=status_field,
            source_record_reference="MAT-100",
            observed_representation="ACTIVE",
        )
        # Deliberately no evidence for planning_group/procurement_type --
        # both must be independently observed as missing.
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

    assert outcomes["a"][0] == "committed"
    assert outcomes["b"][0] == "committed"
    assert outcomes["a"][1] == outcomes["b"][1]

    with factory() as session:
        observation_rows = (
            session.query(BusinessRuleEvaluationObservationORM)
            .filter_by(evaluation_id=outcomes["a"][1])
            .all()
        )
    assert {row.input_role for row in observation_rows} == {"planning_group", "procurement_type"}


def test_rollback_after_parent_ownership_leaves_no_poisoned_parent(
    migrated_engine: Engine,
) -> None:
    """CDD-041 §5.2 (OQI3-G2/I2-R): a transaction that wins parent
    ownership via `ON CONFLICT DO NOTHING RETURNING` but fails before
    inserting its children must roll back completely -- the parent row
    must not survive without its children (no poisoned parent). A retry
    must then be able to become the new owner and persist the complete
    ledger."""
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
    with factory() as session:
        active_rule = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert active_rule is not None
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        inputs = select_input_frontier(
            rule=active_rule, subject=subject, evaluation_horizon=NOW, repository=repository
        )
        assert inputs is not None
        raw_values = OqiBusinessRuleEvidenceValueReader(session).read_values(inputs)
        result = determine_outcome(rule=active_rule, inputs=inputs, raw_values=raw_values)
        assert result is not None
        outcome, observations = result
        subject_identity = canonical_single_record_subject_identity(
            source_object_id=object_id, source_record_reference="MAT-100"
        )
        digest = input_evidence_digest(inputs)
        evaluation_id = derive_business_rule_evaluation_id(
            tenant_id=tenant_id,
            business_condition_id=condition_id,
            rule_version=active_rule.version,
            subject_type=SUBJECT_TYPE_SINGLE_RECORD,
            subject_identity=subject_identity,
            evaluation_mode=EvaluationMode.HISTORICAL,
            evaluation_horizon=NOW,
            input_evidence_digest_value=digest,
        )
        evaluation = BusinessRuleEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            business_condition_id=condition_id,
            rule_id=active_rule.rule_id,
            rule_version=active_rule.version,
            subject_type=SUBJECT_TYPE_SINGLE_RECORD,
            subject_identity=subject_identity,
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_mode=EvaluationMode.HISTORICAL,
            evaluation_horizon=NOW,
            inputs=inputs,
            outcome=outcome,
            observations=observations,
            evaluated_at=NOW,
        )
        won = repository.insert_evaluation_idempotent(evaluation)
        assert won
        # Force failure before commit -- e.g. a bogus, never-admitted
        # evidence id smuggled into a second orphan input row that
        # violates the evidence FK -- proving the whole transaction,
        # including the already-"owned" parent row, rolls back together.
        session.add(
            BusinessRuleEvaluationInputORM(
                evaluation_id=evaluation_id,
                input_role="__poison__",
                field_value_evidence_id=uuid4(),  # references no FieldValueEvidence row
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM business_rule_evaluations WHERE evaluation_id = :id"),
            {"id": evaluation_id},
        ).scalar_one()
    assert count == 0  # no poisoned parent survives

    # Retry: a fresh insert_evaluation_idempotent call must be able to
    # become the new owner and persist the complete ledger.
    with factory() as session:
        active_rule = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert active_rule is not None
        retried_evaluation = _service(session).evaluate_historical(
            rule=active_rule, subject=subject, evaluation_horizon=NOW
        )
        session.commit()
    assert retried_evaluation is not None
    assert retried_evaluation.evaluation_id == evaluation_id
    with factory() as session:
        input_count = session.execute(
            text("SELECT count(*) FROM business_rule_evaluation_inputs WHERE evaluation_id = :id"),
            {"id": evaluation_id},
        ).scalar_one()
    assert input_count == 2


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
        assert active is not None
        retired = OqiBusinessRuleRepositoryImpl(session).get_by_id(rule_v1.rule_id)
        assert retired is not None
    assert active is not None and active.version == 2
    assert retired is not None and retired.status is BusinessRuleStatus.RETIRED


# --- CDD-041 Atomic Multi-Field Evidence Frontier Amendment (OQI3-I2-R3):
# `select_input_frontier`/`repository.select_evidence_frontier` now obtain
# every mutable evidence-state fact (subject-known + all bound roles'
# latest qualifying evidence) from exactly one PostgreSQL statement, closing
# the evaluator-vs-evidence-writer coherence gap OQI3-I3/OQI3-R3 discovered.
# The regressions below prove: (1) the new algorithm is logically
# equivalent to the retired sequential algorithm for unchanged state
# (frontier/digest/Evaluation-ID equivalence); (2) EMPTY/UNKNOWN-subject/
# tenant/SourceObject/horizon semantics are preserved exactly; (3) the
# statement genuinely executes as ONE PostgreSQL round trip; (4) it is
# genuinely N-ary; and, most importantly, (5) a concurrent writer's commit
# landing strictly DURING the atomic statement's execution is NOT visible
# to that statement -- proven on real PostgreSQL via a deterministic
# `pg_sleep`-forced delay, not by assertion or by luck.


def _old_sequential_frontier(
    session: Session,
    *,
    source_object_id: UUID,
    source_record_reference: str,
    evaluation_horizon: datetime,
    bindings: tuple[tuple[str, UUID], ...],
) -> dict[str, UUID | None] | None:
    """Local re-implementation of the RETIRED pre-OQI3-I2-R3 algorithm
    (two sequential SELECT categories: one known-lineage check, then one
    per-role latest-evidence SELECT) -- kept here, not in production code,
    purely as an equivalence oracle for the mandatory unchanged-state
    equivalence regression (CDD-041 Atomic Multi-Field Evidence Frontier
    Amendment §10 item 1). Byte-identical filter/order predicates to the
    real (removed) `select_known_lineage`/`select_latest_field_value`."""
    from sqlalchemy import select as _select

    from app.infrastructure.persistence.models.field_value_evidence import (
        FieldValueEvidenceORM as _FVE,
    )
    from app.infrastructure.persistence.models.source_field import SourceFieldORM as _SF

    known = (
        session.execute(
            _select(_FVE.field_value_evidence_id)
            .join(_SF, _SF.source_field_id == _FVE.source_field_id)
            .where(
                _SF.source_object_id == source_object_id,
                _FVE.source_record_reference == source_record_reference,
                _FVE.observed_representation != "",
                _FVE.received_at <= evaluation_horizon,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )
    if not known:
        return None
    result: dict[str, UUID | None] = {}
    for role, field_id in bindings:
        row = session.execute(
            _select(_FVE.field_value_evidence_id)
            .where(
                _FVE.source_field_id == field_id,
                _FVE.source_record_reference == source_record_reference,
                _FVE.observed_representation != "",
                _FVE.received_at <= evaluation_horizon,
            )
            .order_by(_FVE.observed_at.desc(), _FVE.received_at.desc())
            .limit(1)
        ).first()
        result[role] = None if row is None else row[0]
    return result


def test_atomic_frontier_equivalent_to_retired_sequential_algorithm_for_unchanged_state(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 items 1-3: for unchanged DB state, the new one-
    statement selector returns the identical logical `(role, evidence_id)`
    frontier as the retired sequential algorithm, and therefore produces
    an identical evidence digest and Evaluation ID -- both formulas are
    pure functions of that frontier (CDD-041 §17, §16)."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, start_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="EFFECTIVE_START"
        )
        _, end_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="EFFECTIVE_END"
        )
        _admit_evidence(
            session,
            source_field_id=start_field,
            source_record_reference="MAT-100",
            observed_representation="2026-01-01",
        )
        session.commit()

        bindings = (("effective_start", start_field), ("effective_end", end_field))
        old_result = _old_sequential_frontier(
            session,
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=bindings,
        )
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        new_known, new_result = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=bindings,
        )
    assert old_result is not None
    assert new_known is True
    assert old_result == new_result

    old_entries = tuple(
        BusinessRuleEvaluationInputEntry(input_role=role, evidence_id=old_result[role])
        for role, _ in bindings
    )
    new_entries = tuple(
        BusinessRuleEvaluationInputEntry(input_role=role, evidence_id=new_result[role])
        for role, _ in bindings
    )
    assert input_evidence_digest(old_entries) == input_evidence_digest(new_entries)
    subject_identity = canonical_single_record_subject_identity(
        source_object_id=object_id, source_record_reference="MAT-100"
    )
    old_id = derive_business_rule_evaluation_id(
        tenant_id=tenant_id,
        business_condition_id="cond-x",
        rule_version=1,
        subject_type=SUBJECT_TYPE_SINGLE_RECORD,
        subject_identity=subject_identity,
        evaluation_mode=EvaluationMode.HISTORICAL,
        evaluation_horizon=NOW,
        input_evidence_digest_value=input_evidence_digest(old_entries),
    )
    new_id = derive_business_rule_evaluation_id(
        tenant_id=tenant_id,
        business_condition_id="cond-x",
        rule_version=1,
        subject_type=SUBJECT_TYPE_SINGLE_RECORD,
        subject_identity=subject_identity,
        evaluation_mode=EvaluationMode.HISTORICAL,
        evaluation_horizon=NOW,
        input_evidence_digest_value=input_evidence_digest(new_entries),
    )
    assert old_id == new_id


def test_atomic_frontier_all_bound_roles_empty_for_known_subject(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 item 4: known subject (lineage established via one
    field), but the target consequence fields have zero qualifying
    evidence -- every such role must still appear with the EMPTY (`None`)
    sentinel, never silently dropped."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, status_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="LIFECYCLE_STATUS"
        )
        _, group_field = _seed_field_with_object(session, tenant_id=tenant_id, field_label="GROUP")
        _, type_field = _seed_field_with_object(session, tenant_id=tenant_id, field_label="TYPE")
        _admit_evidence(
            session,
            source_field_id=status_field,
            source_record_reference="MAT-100",
            observed_representation="ACTIVE",
        )
        session.commit()
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known, frontier = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(
                ("lifecycle_status", status_field),
                ("planning_group", group_field),
                ("procurement_type", type_field),
            ),
        )
    assert known is True
    assert frontier == {
        "lifecycle_status": frontier["lifecycle_status"],
        "planning_group": None,
        "procurement_type": None,
    }
    assert frontier["lifecycle_status"] is not None


def test_atomic_frontier_unknown_subject_returns_no_roles(migrated_engine: Engine) -> None:
    """Amendment §10 item 5: zero evidence anywhere for the SourceObject --
    `subject_known` is False and the frontier mapping is empty; the caller
    (`select_input_frontier`) must treat this as `NOT_EVALUABLE`, never
    manufacture EMPTY entries for an unknown subject."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, field_a = _seed_field_with_object(session, tenant_id=tenant_id, field_label="A")
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known, frontier = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-NEVER-SEEN",
            evaluation_horizon=NOW,
            bindings=(("role_a", field_a),),
        )
    assert known is False
    assert frontier == {}


def test_atomic_frontier_mixed_value_and_empty_roles(migrated_engine: Engine) -> None:
    """Amendment §10 item 6: a known subject with some bound roles having
    evidence and others EMPTY in the same frontier -- exact role
    cardinality and correct evidence identity per role."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, field_a = _seed_field_with_object(session, tenant_id=tenant_id, field_label="A")
        _, field_b = _seed_field_with_object(session, tenant_id=tenant_id, field_label="B")
        _, field_c = _seed_field_with_object(session, tenant_id=tenant_id, field_label="C")
        _, field_d = _seed_field_with_object(session, tenant_id=tenant_id, field_label="D")
        eid_a = _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="va",
        )
        eid_c = _admit_evidence(
            session,
            source_field_id=field_c,
            source_record_reference="MAT-100",
            observed_representation="vc",
        )
        session.commit()
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known, frontier = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(
                ("a", field_a),
                ("b", field_b),
                ("c", field_c),
                ("d", field_d),
            ),
        )
    assert known is True
    assert frontier == {"a": eid_a, "b": None, "c": eid_c, "d": None}


def test_atomic_frontier_equal_timestamp_tie_is_inherited_undefined_not_asserted(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 item 7 / OQI-P3-006: two qualifying evidence rows for
    the same role with identical `observed_at` AND `received_at` -- the
    window-function replacement has no third tiebreaker, exactly like the
    retired OQI1-derived selector. This test documents the inherited
    undefined-winner behavior (the frontier deterministically names ONE of
    the two evidence IDs, never both, never neither) -- it does NOT assert
    which one, since that would fabricate a guarantee CDD-041 does not
    make (Amendment §5)."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, field_a = _seed_field_with_object(session, tenant_id=tenant_id, field_label="A")
        eid_1 = _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v1",
            received_at=NOW,
        )
        eid_2 = _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v2",
            received_at=NOW,
        )
        session.commit()
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known, frontier = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("a", field_a),),
        )
    assert known is True
    assert frontier["a"] in {eid_1, eid_2}


def test_atomic_frontier_source_object_boundary_not_mere_reference_match(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 item 19: same tenant, same `source_record_reference`,
    but a DIFFERENT `SourceObject` -- evidence must not leak across the
    object boundary merely because the reference string matches."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_1, field_1 = _seed_field_with_object(session, tenant_id=tenant_id, field_label="F1")
        _object_2, field_2 = _seed_field_with_object(session, tenant_id=tenant_id, field_label="F2")
        _admit_evidence(
            session,
            source_field_id=field_2,
            source_record_reference="MAT-100",
            observed_representation="belongs-to-object-2",
        )
        session.commit()
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known, frontier = repository.select_evidence_frontier(
            source_object_id=object_1,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("role_a", field_1),),
        )
    assert known is False
    assert frontier == {}


def test_atomic_frontier_horizon_boundary_matches_existing_inclusion_semantics(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 item 20: `received_at <= evaluation_horizon` boundary
    -- evidence exactly AT the horizon is included; evidence strictly
    after it is excluded. Unchanged from the retired selector."""
    from datetime import timedelta

    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    horizon = NOW
    with factory() as session:
        object_id, field_a = _seed_field_with_object(session, tenant_id=tenant_id, field_label="A")
        eid_at_horizon = _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="on-time",
            received_at=horizon,
        )
        _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="too-late",
            received_at=horizon + timedelta(seconds=1),
        )
        session.commit()
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known, frontier = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=horizon,
            bindings=(("a", field_a),),
        )
    assert known is True
    assert frontier["a"] == eid_at_horizon


def test_atomic_frontier_executes_exactly_one_sql_statement(migrated_engine: Engine) -> None:
    """Amendment §10 item 21 (ORM lazy-load firewall): the atomic frontier
    call must be exactly one round trip to PostgreSQL -- no lazy-loaded
    ORM access afterward may supply a mutable evidence-state fact."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, field_a = _seed_field_with_object(session, tenant_id=tenant_id, field_label="A")
        _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v1",
        )
        session.commit()

        statement_count = 0

        def _count(*_args: object, **_kwargs: object) -> None:
            nonlocal statement_count
            statement_count += 1

        event.listen(session.connection().engine, "before_cursor_execute", _count)
        try:
            repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
            repository.select_evidence_frontier(
                source_object_id=object_id,
                source_record_reference="MAT-100",
                evaluation_horizon=NOW,
                bindings=(("a", field_a),),
            )
        finally:
            event.remove(session.connection().engine, "before_cursor_execute", _count)
    assert statement_count == 1


def test_atomic_frontier_scales_to_ten_bound_roles_end_to_end(migrated_engine: Engine) -> None:
    """Amendment §10 item 9: a real 10-clause AND-compound
    `CONDITIONAL_REQUIRED` rule (well under the 64-node AST bound) proves
    N=10 end to end through the real evaluator, mixing satisfied and
    missing roles."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        object_id, status_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="LIFECYCLE_STATUS"
        )
        target_fields = [
            _seed_field_with_object(session, tenant_id=tenant_id, field_label=f"F{i}")[1]
            for i in range(10)
        ]
        applicability = ComparatorNode(
            clause_id="applicable-active",
            operator=Operator.EQ,
            input_role="lifecycle_status",
            comparand_kind=ComparandKind.LITERAL,
            literal_type=ExpectedType.STRING,
            literal_value="ACTIVE",
        )
        predicate = CompositionNode(
            operator=Operator.AND,
            children=tuple(
                ComparatorNode(
                    clause_id=f"f{i}-required",
                    operator=Operator.IS_NOT_NULL,
                    input_role=f"role_{i}",
                    comparand_kind=ComparandKind.NONE,
                )
                for i in range(10)
            ),
        )
        bindings = (
            BusinessRuleInputBinding(
                input_role="lifecycle_status",
                source_field_id=status_field,
                required=True,
                expected_type=ExpectedType.STRING,
            ),
            *(
                BusinessRuleInputBinding(
                    input_role=f"role_{i}",
                    source_field_id=target_fields[i],
                    required=False,
                    expected_type=ExpectedType.STRING,
                )
                for i in range(10)
            ),
        )
        rule = BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=applicability,
            predicate=predicate,
            input_bindings=bindings,
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        _admit_evidence(
            session,
            source_field_id=status_field,
            source_record_reference="MAT-100",
            observed_representation="ACTIVE",
        )
        # 7 of 10 target roles get evidence; 3 remain EMPTY.
        for i in range(7):
            _admit_evidence(
                session,
                source_field_id=target_fields[i],
                source_record_reference="MAT-100",
                observed_representation=f"v{i}",
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
    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert len(evaluation.observations) == 3
    assert {obs.input_role for obs in evaluation.observations} == {
        f"role_{i}" for i in range(7, 10)
    }


def test_atomic_frontier_scales_to_hundred_bound_roles(migrated_engine: Engine) -> None:
    """Amendment §10 item 10: N=100 bound roles at the repository/query
    layer directly (bypassing the unrelated 64-node AST publication bound,
    which governs rule SHAPE, not frontier-query arity) -- proves the
    atomic statement itself has no hard-coded arity. Half the roles get
    evidence, half remain EMPTY; every one of the 100 roles must appear."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, anchor_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="ANCHOR"
        )
        _admit_evidence(
            session,
            source_field_id=anchor_field,
            source_record_reference="MAT-100",
            observed_representation="known",
        )
        fields = [
            _seed_field_with_object(session, tenant_id=tenant_id, field_label=f"F{i}")[1]
            for i in range(100)
        ]
        expected_evidence: dict[str, UUID] = {}
        for i in range(0, 100, 2):
            expected_evidence[f"role_{i}"] = _admit_evidence(
                session,
                source_field_id=fields[i],
                source_record_reference="MAT-100",
                observed_representation=f"v{i}",
            )
        session.commit()
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known, frontier = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=tuple((f"role_{i}", fields[i]) for i in range(100)),
        )
    assert known is True
    assert len(frontier) == 100
    for i in range(100):
        expected = expected_evidence.get(f"role_{i}")
        assert frontier[f"role_{i}"] == expected


def test_atomic_frontier_compound_crown_regression_false_false_unknown(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 items 8, 24 -- the crown regression: strong Kleene
    `FALSE AND FALSE AND UNKNOWN = FALSE`. Two AND-compound
    CONDITIONAL_PROHIBITED clauses deterministically detect a prohibited
    value present; a third clause's evidence is malformed (UNKNOWN). Note:
    CONDITIONAL_REQUIRED's frozen shape restricts every clause to
    IS_NOT_NULL (evidence-presence only, which is NEVER UNKNOWN once the
    subject is known) -- so a genuine UNKNOWN leaf can only arise in
    CONDITIONAL_PROHIBITED, whose leaf_check permits any comparator
    (CDD-041 §4.2). Outcome must be VIOLATED with observations for exactly
    the two known failures -- the UNKNOWN clause gets no observation, but
    does not block the overall VIOLATED determination either."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        object_id, status_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="LIFECYCLE_STATUS"
        )
        _, group_field = _seed_field_with_object(session, tenant_id=tenant_id, field_label="GROUP")
        _, type_field = _seed_field_with_object(session, tenant_id=tenant_id, field_label="TYPE")
        _, uom_field = _seed_field_with_object(session, tenant_id=tenant_id, field_label="UOM")
        applicability = ComparatorNode(
            clause_id="applicable-active",
            operator=Operator.EQ,
            input_role="lifecycle_status",
            comparand_kind=ComparandKind.LITERAL,
            literal_type=ExpectedType.STRING,
            literal_value="ACTIVE",
        )
        predicate = CompositionNode(
            operator=Operator.AND,
            children=(
                ComparatorNode(
                    clause_id="group-not-obsolete",
                    operator=Operator.NE,
                    input_role="planning_group",
                    comparand_kind=ComparandKind.LITERAL,
                    literal_type=ExpectedType.STRING,
                    literal_value="OBSOLETE",
                ),
                ComparatorNode(
                    clause_id="type-not-blocked",
                    operator=Operator.NE,
                    input_role="procurement_type",
                    comparand_kind=ComparandKind.LITERAL,
                    literal_type=ExpectedType.STRING,
                    literal_value="BLOCKED",
                ),
                ComparatorNode(
                    clause_id="uom-within-limit",
                    operator=Operator.LTE,
                    input_role="base_uom_qty",
                    comparand_kind=ComparandKind.LITERAL,
                    literal_type=ExpectedType.DECIMAL,
                    literal_value="1000",
                ),
            ),
        )
        bindings = (
            BusinessRuleInputBinding(
                input_role="lifecycle_status",
                source_field_id=status_field,
                required=True,
                expected_type=ExpectedType.STRING,
            ),
            BusinessRuleInputBinding(
                input_role="planning_group",
                source_field_id=group_field,
                required=False,
                expected_type=ExpectedType.STRING,
            ),
            BusinessRuleInputBinding(
                input_role="procurement_type",
                source_field_id=type_field,
                required=False,
                expected_type=ExpectedType.STRING,
            ),
            BusinessRuleInputBinding(
                input_role="base_uom_qty",
                source_field_id=uom_field,
                required=False,
                expected_type=ExpectedType.DECIMAL,
            ),
        )
        rule = BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
            applicability=applicability,
            predicate=predicate,
            input_bindings=bindings,
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        _admit_evidence(
            session,
            source_field_id=status_field,
            source_record_reference="MAT-100",
            observed_representation="ACTIVE",
        )
        # planning_group == OBSOLETE and procurement_type == BLOCKED: both
        # deterministically violate their NE clauses (FALSE). base_uom_qty:
        # malformed DECIMAL evidence -> UNKNOWN.
        _admit_evidence(
            session,
            source_field_id=group_field,
            source_record_reference="MAT-100",
            observed_representation="OBSOLETE",
        )
        _admit_evidence(
            session,
            source_field_id=type_field,
            source_record_reference="MAT-100",
            observed_representation="BLOCKED",
        )
        _admit_evidence(
            session,
            source_field_id=uom_field,
            source_record_reference="MAT-100",
            observed_representation="NOT-A-NUMBER",
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
    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert len(evaluation.observations) == 2
    assert {obs.input_role for obs in evaluation.observations} == {
        "planning_group",
        "procurement_type",
    }


def test_atomic_frontier_true_and_unknown_yields_not_evaluable_zero_persistence(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 items 24, 25: strong Kleene `TRUE AND UNKNOWN =
    UNKNOWN` -- one AND-compound CONDITIONAL_PROHIBITED clause
    deterministically allowed (not the prohibited value), the other
    malformed (UNKNOWN). Overall result must be NOT_EVALUABLE with ZERO
    rows written to any of the four governed tables and zero Finding
    rows -- OQI3 must never fabricate a VIOLATED/SATISFIED conclusion from
    an unknown clause."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        object_id, status_field = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="LIFECYCLE_STATUS"
        )
        _, group_field = _seed_field_with_object(session, tenant_id=tenant_id, field_label="GROUP")
        _, uom_field = _seed_field_with_object(session, tenant_id=tenant_id, field_label="UOM")
        applicability = ComparatorNode(
            clause_id="applicable-active",
            operator=Operator.EQ,
            input_role="lifecycle_status",
            comparand_kind=ComparandKind.LITERAL,
            literal_type=ExpectedType.STRING,
            literal_value="ACTIVE",
        )
        predicate = CompositionNode(
            operator=Operator.AND,
            children=(
                ComparatorNode(
                    clause_id="group-not-obsolete",
                    operator=Operator.NE,
                    input_role="planning_group",
                    comparand_kind=ComparandKind.LITERAL,
                    literal_type=ExpectedType.STRING,
                    literal_value="OBSOLETE",
                ),
                ComparatorNode(
                    clause_id="uom-within-limit",
                    operator=Operator.LTE,
                    input_role="base_uom_qty",
                    comparand_kind=ComparandKind.LITERAL,
                    literal_type=ExpectedType.DECIMAL,
                    literal_value="1000",
                ),
            ),
        )
        bindings = (
            BusinessRuleInputBinding(
                input_role="lifecycle_status",
                source_field_id=status_field,
                required=True,
                expected_type=ExpectedType.STRING,
            ),
            BusinessRuleInputBinding(
                input_role="planning_group",
                source_field_id=group_field,
                required=False,
                expected_type=ExpectedType.STRING,
            ),
            BusinessRuleInputBinding(
                input_role="base_uom_qty",
                source_field_id=uom_field,
                required=False,
                expected_type=ExpectedType.DECIMAL,
            ),
        )
        rule = BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
            applicability=applicability,
            predicate=predicate,
            input_bindings=bindings,
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        _admit_evidence(
            session,
            source_field_id=status_field,
            source_record_reference="MAT-100",
            observed_representation="ACTIVE",
        )
        # planning_group != OBSOLETE: deterministically allowed (TRUE).
        # base_uom_qty: malformed DECIMAL evidence -> UNKNOWN.
        _admit_evidence(
            session,
            source_field_id=group_field,
            source_record_reference="MAT-100",
            observed_representation="GROUP-A",
        )
        _admit_evidence(
            session,
            source_field_id=uom_field,
            source_record_reference="MAT-100",
            observed_representation="NOT-A-NUMBER",
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
    assert evaluation is None

    with factory() as session:
        # Scoped to this test's own tenant/condition -- the migrated_engine
        # fixture is shared across the whole test module's session, so an
        # unscoped table-wide count would spuriously include other tests'
        # rows. Zero rows for THIS governed condition is the actual claim.
        evaluations_count = session.execute(
            text(
                "SELECT count(*) FROM business_rule_evaluations "
                "WHERE tenant_id = :tenant_id AND business_condition_id = :condition_id"
            ),
            {"tenant_id": tenant_id, "condition_id": condition_id},
        ).scalar_one()
        findings_count = session.execute(
            text(
                "SELECT count(*) FROM business_rule_findings "
                "WHERE tenant_id = :tenant_id AND business_condition_id = :condition_id"
            ),
            {"tenant_id": tenant_id, "condition_id": condition_id},
        ).scalar_one()
    assert evaluations_count == 0
    assert findings_count == 0
    # No evaluation_id was ever created for this condition, so by FK
    # construction no input/observation row referencing it can exist
    # either -- confirmed structurally, not by an unscoped table count.


def test_atomic_frontier_writer_before_statement_is_visible(migrated_engine: Engine) -> None:
    """Amendment §10 item 11: evidence committed strictly BEFORE the
    atomic statement's snapshot is taken must be visible, subject to the
    horizon."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, field_a = _seed_field_with_object(session, tenant_id=tenant_id, field_label="A")
        eid = _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v1",
        )
        session.commit()
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known, frontier = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("a", field_a),),
        )
    assert known is True
    assert frontier["a"] == eid


def test_atomic_frontier_writer_after_statement_visible_only_to_next_evaluation(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 item 13: evidence committed AFTER the atomic
    statement completes is correctly absent from that Evaluation, but
    visible to the next one -- normal transaction sequencing, not
    staleness."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        object_id, field_a = _seed_field_with_object(session, tenant_id=tenant_id, field_label="A")
        session.commit()

    with factory() as session:
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known_before, _frontier_before = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("a", field_a),),
        )
    assert known_before is False

    with factory() as session:
        _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v1",
        )
        session.commit()

    with factory() as session:
        repository = OqiBusinessRuleEvaluationRepositoryImpl(session)
        known_after, frontier_after = repository.select_evidence_frontier(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("a", field_a),),
        )
    assert known_after is True
    assert frontier_after["a"] is not None


def test_atomic_frontier_writer_during_statement_is_not_visible(
    migrated_engine: Engine,
) -> None:
    """RELEASE-BLOCKING TEST (Amendment §10 item 12; CDD-041 Atomic
    Multi-Field Evidence Frontier Amendment, OQI3-I3/OQI3-R3 P1 closure
    condition) -- the single most important regression in this repair.

    Forces the real atomic frontier statement (the exact production
    `_build_evidence_frontier_statement`, via its `_test_only_delay_seconds`
    test seam -- zero effect on production behavior, no production caller
    ever sets it) to remain in-flight for 0.6s via a `pg_sleep`-gated CTE.
    A concurrent writer commits new evidence for one of the two bound
    roles at t~0.2s -- strictly DURING the reader statement's execution
    window, proven by wall-clock timing, not by luck. The reader's single
    statement must NOT observe that commit: this is the actual PostgreSQL
    one-statement-one-snapshot property the whole repair depends on,
    proven empirically against real PostgreSQL, not merely asserted."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as setup_session:
        object_id, field_a = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="A"
        )
        _, field_b = _seed_field_with_object(setup_session, tenant_id=tenant_id, field_label="B")
        _admit_evidence(
            setup_session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v1",
        )
        # Deliberately no evidence admitted yet for field_b.
        setup_session.commit()

    statement_started = threading.Event()
    results: dict[str, Any] = {}

    def _reader(session: Session) -> None:
        stmt = _build_evidence_frontier_statement(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("a", field_a), ("b", field_b)),
            _test_only_delay_seconds=0.6,
        )
        t0 = time.monotonic()
        statement_started.set()
        rows = session.execute(stmt).all()
        results["elapsed"] = time.monotonic() - t0
        results["rows"] = {row[1]: row[2] for row in rows}

    def _concurrent_writer(session: Session) -> None:
        assert statement_started.wait(timeout=5)
        time.sleep(0.2)  # strictly inside the reader's 0.6s statement window
        _admit_evidence(
            session,
            source_field_id=field_b,
            source_record_reference="MAT-100",
            observed_representation="v2",
        )
        session.commit()
        results["writer_committed_at"] = time.monotonic()

    session_reader, session_writer = factory(), factory()
    thread_reader = threading.Thread(target=_reader, args=(session_reader,))
    thread_writer = threading.Thread(target=_concurrent_writer, args=(session_writer,))
    thread_reader.start()
    thread_writer.start()
    thread_reader.join(timeout=10)
    thread_writer.join(timeout=10)
    session_reader.close()
    session_writer.close()

    assert results["elapsed"] >= 0.5, "the statement must genuinely have stayed in-flight"
    assert results["rows"]["a"] is not None
    # The concurrent commit landed strictly during statement execution --
    # the atomic statement's one snapshot must NOT reflect it.
    assert results["rows"]["b"] is None


def test_atomic_frontier_two_concurrent_writers_all_or_nothing_visibility(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 item 14: two concurrent writers commit evidence for
    two DIFFERENT bound roles during one delayed statement -- the reader
    must observe a coherent all-or-nothing result (both absent, since both
    commits land during the statement window), never a split frontier."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as setup_session:
        object_id, field_a = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="A"
        )
        _, field_b = _seed_field_with_object(setup_session, tenant_id=tenant_id, field_label="B")
        _, field_c = _seed_field_with_object(setup_session, tenant_id=tenant_id, field_label="C")
        _admit_evidence(
            setup_session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v1",
        )
        setup_session.commit()

    statement_started = threading.Event()
    results: dict[str, Any] = {}

    def _reader(session: Session) -> None:
        stmt = _build_evidence_frontier_statement(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("a", field_a), ("b", field_b), ("c", field_c)),
            _test_only_delay_seconds=0.6,
        )
        statement_started.set()
        rows = session.execute(stmt).all()
        results["rows"] = {row[1]: row[2] for row in rows}

    def _writer(session: Session, *, field_id: UUID, value: str) -> None:
        assert statement_started.wait(timeout=5)
        time.sleep(0.2)
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference="MAT-100",
            observed_representation=value,
        )
        session.commit()

    session_reader, session_writer_b, session_writer_c = factory(), factory(), factory()
    thread_reader = threading.Thread(target=_reader, args=(session_reader,))
    thread_writer_b = threading.Thread(
        target=_writer, args=(session_writer_b,), kwargs={"field_id": field_b, "value": "vb"}
    )
    thread_writer_c = threading.Thread(
        target=_writer, args=(session_writer_c,), kwargs={"field_id": field_c, "value": "vc"}
    )
    thread_reader.start()
    thread_writer_b.start()
    thread_writer_c.start()
    thread_reader.join(timeout=10)
    thread_writer_b.join(timeout=10)
    thread_writer_c.join(timeout=10)
    session_reader.close()
    session_writer_b.close()
    session_writer_c.close()

    assert results["rows"]["a"] is not None
    # Both concurrent commits land during the same statement's execution
    # window -- the one shared snapshot must exclude both, coherently.
    assert results["rows"]["b"] is None
    assert results["rows"]["c"] is None


def test_atomic_frontier_known_lineage_creation_race_resolves_to_one_snapshot(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 item 15: the subject is COMPLETELY unknown (zero
    evidence anywhere for the SourceObject). A concurrent writer commits
    the first-ever evidence -- establishing lineage -- strictly during the
    delayed statement. The result must resolve cleanly to the pre-commit
    snapshot's answer (subject still unknown), never a hybrid of
    known-lineage-from-one-snapshot plus evidence-from-another."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as setup_session:
        object_id, field_a = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="A"
        )
        setup_session.commit()

    statement_started = threading.Event()
    results: dict[str, Any] = {}

    def _reader(session: Session) -> None:
        stmt = _build_evidence_frontier_statement(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("a", field_a),),
            _test_only_delay_seconds=0.6,
        )
        statement_started.set()
        rows = session.execute(stmt).all()
        results["subject_known"] = bool(rows[0][0]) if rows else False
        results["rows"] = {row[1]: row[2] for row in rows}

    def _concurrent_writer(session: Session) -> None:
        assert statement_started.wait(timeout=5)
        time.sleep(0.2)
        _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="first-ever-evidence",
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

    # The commit establishing lineage landed strictly during the
    # statement's execution -- the pre-commit snapshot's answer (unknown)
    # must be what this Evaluation sees, coherently for both the
    # subject-known fact AND the per-role evidence (never a hybrid).
    assert results["subject_known"] is False
    assert results["rows"]["a"] is None


def test_atomic_frontier_value_to_new_value_race_is_snapshot_consistent(
    migrated_engine: Engine,
) -> None:
    """Amendment §10 item 17: role already has qualifying evidence v1; a
    concurrent writer appends v2 for the SAME role strictly during the
    delayed statement. The reader must consistently select v1 (the
    pre-statement snapshot's latest), never v2."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as setup_session:
        object_id, field_a = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="A"
        )
        eid_v1 = _admit_evidence(
            setup_session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v1",
        )
        setup_session.commit()

    statement_started = threading.Event()
    results: dict[str, Any] = {}

    def _reader(session: Session) -> None:
        stmt = _build_evidence_frontier_statement(
            source_object_id=object_id,
            source_record_reference="MAT-100",
            evaluation_horizon=NOW,
            bindings=(("a", field_a),),
            _test_only_delay_seconds=0.6,
        )
        statement_started.set()
        rows = session.execute(stmt).all()
        results["rows"] = {row[1]: row[2] for row in rows}

    def _concurrent_writer(session: Session) -> None:
        assert statement_started.wait(timeout=5)
        time.sleep(0.2)
        _admit_evidence(
            session,
            source_field_id=field_a,
            source_record_reference="MAT-100",
            observed_representation="v2",
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

    assert results["rows"]["a"] == eid_v1


# --- OQI3-I3: CURRENT-STATE BusinessRuleFinding lifecycle + seed-3 authority
# (CDD-041 §14-§15, §21, §24; Artifact Authorization §9, §14-§15 remainder).
# Fake-repo lifecycle/counter/compound/Kleene tests live in
# test_oqi_business_rule_evaluation_service.py; these are the real-Postgres
# concurrency and atomicity proofs that fake repo cannot provide.


def _current_state_service(session: Session) -> OqiBusinessRuleEvaluationService:
    return _service(session)


def test_current_state_first_violation_race_creates_exactly_one_finding(
    migrated_engine: Engine,
) -> None:
    """CDD-041 §21: two concurrent CURRENT_STATE evaluators, identical
    evidence, no existing Finding. Seed-3 serializes them -- the second
    worker only proceeds after the first commits, so no duplicate Finding,
    no lost update, and no caller-visible IntegrityError from the Finding
    table itself."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        object_id, field_id = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="MATERIAL_TYPE"
        )
        classification_field_id = _seed_field(
            setup_session, tenant_id=tenant_id, field_label="HAZMAT_CLASSIFICATION"
        )
        rule = BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="applicable-hazmat",
                operator=Operator.EQ,
                input_role="material_type",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value="HAZMAT",
            ),
            predicate=ComparatorNode(
                clause_id="classification-required",
                operator=Operator.IS_NOT_NULL,
                input_role="hazmat_classification",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="material_type",
                    source_field_id=field_id,
                    required=True,
                    expected_type=ExpectedType.STRING,
                ),
                BusinessRuleInputBinding(
                    input_role="hazmat_classification",
                    source_field_id=classification_field_id,
                    required=True,
                    expected_type=ExpectedType.STRING,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
        OqiBusinessRuleRepositoryImpl(setup_session).create(rule)
        _admit_evidence(
            setup_session,
            source_field_id=field_id,
            source_record_reference="MAT-100",
            observed_representation="HAZMAT",
        )
        # hazmat_classification deliberately never admitted -> EMPTY -> VIOLATED.
        setup_session.commit()

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=object_id, source_record_reference="MAT-100"
    )
    barrier = threading.Barrier(2)
    outcomes: dict[str, tuple[str, object]] = {}

    def _worker(session: Session, key: str) -> None:
        # Defensive: ANY exception (not just IntegrityError) must still
        # release the transaction-scoped seed-3 lock via rollback in the
        # `finally` clause -- an unhandled exception left uncaught here
        # would leave the session "idle in transaction" holding the lock
        # forever, deadlocking the sibling worker.
        try:
            rule_local = OqiBusinessRuleRepositoryImpl(session).get_active(
                tenant_id=tenant_id, business_condition_id=condition_id
            )
            assert rule_local is not None
            barrier.wait(timeout=5)
            evaluation = _current_state_service(session).evaluate_current_state(
                rule=rule_local, subject=subject
            )
            assert evaluation is not None
            session.commit()
            outcomes[key] = ("committed", evaluation.evaluation_id)
        except IntegrityError:
            outcomes[key] = ("integrity_error", None)
        except BaseException as exc:  # noqa: BLE001
            outcomes[key] = ("error", repr(exc))
        finally:
            session.rollback()

    session_a, session_b = factory(), factory()
    thread_a = threading.Thread(target=_worker, args=(session_a, "a"))
    thread_b = threading.Thread(target=_worker, args=(session_b, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=15)
    thread_b.join(timeout=15)
    session_a.close()
    session_b.close()

    assert outcomes["a"][0] == "committed", outcomes["a"]
    assert outcomes["b"][0] == "committed", outcomes["b"]
    assert outcomes["a"][1] == outcomes["b"][1]  # identical evidence -> identical evaluation_id

    with factory() as session:
        finding_count = session.execute(
            text(
                "SELECT count(*) FROM business_rule_findings WHERE tenant_id = :t "
                "AND business_condition_id = :c"
            ),
            {"t": tenant_id, "c": condition_id},
        ).scalar_one()
        finding_row = session.execute(
            text(
                "SELECT status, occurrence_count, reopen_count, state_revision "
                "FROM business_rule_findings WHERE tenant_id = :t AND business_condition_id = :c"
            ),
            {"t": tenant_id, "c": condition_id},
        ).one()
    assert finding_count == 1
    # Both workers computed the identical evaluation_id (unchanged evidence);
    # only the transaction that won parent ownership mutates the Finding --
    # exactly one OPEN Finding at revision 1, never a lost/duplicated update.
    assert finding_row[0] == "OPEN"
    assert finding_row[1] == 1  # occurrence_count
    assert finding_row[2] == 0  # reopen_count
    assert finding_row[3] == 1  # state_revision


def test_current_state_reopen_race_increments_reopen_count_exactly_once(
    migrated_engine: Engine,
) -> None:
    """CDD-041 §14, §21: a Finding resolved via NOT_APPLICABLE (material
    reclassified STANDARD), then two concurrent CURRENT_STATE evaluators
    submit identical evidence re-establishing HAZMAT applicability with
    classification still never admitted (permanently EMPTY) -> VIOLATED.
    Seed-3 serializes the reopen -- only the transaction that wins parent
    ownership of the (identical) Evaluation mutates the Finding, so
    reopen_count increments exactly once, never twice."""
    from datetime import timedelta

    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    ref = "MAT-REOPEN-1"
    # A single fixed CURRENT_STATE horizon, later than every admitted
    # evidence timestamp below (NOW, NOW+1h, NOW+2h) -- the service's clock
    # must not itself be `NOW` (a `_service()` default), since evidence
    # admitted at `NOW+1h`/`NOW+2h` would otherwise fall after the horizon
    # and never be selected by the frontier's `received_at <= horizon`
    # boundary.
    horizon = NOW + timedelta(hours=10)

    def _horizoned_service(session: Session) -> OqiBusinessRuleEvaluationService:
        return OqiBusinessRuleEvaluationService(
            evaluation_repository=OqiBusinessRuleEvaluationRepositoryImpl(session),
            evidence_value_reader=OqiBusinessRuleEvidenceValueReader(session),
            clock=lambda: horizon,
        )

    def _rule(field_id: UUID, classification_field_id: UUID) -> BusinessRule:
        return BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="applicable-hazmat",
                operator=Operator.EQ,
                input_role="material_type",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value="HAZMAT",
            ),
            predicate=ComparatorNode(
                clause_id="classification-required",
                operator=Operator.IS_NOT_NULL,
                input_role="hazmat_classification",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="material_type",
                    source_field_id=field_id,
                    required=True,
                    expected_type=ExpectedType.STRING,
                ),
                BusinessRuleInputBinding(
                    input_role="hazmat_classification",
                    source_field_id=classification_field_id,
                    required=True,
                    expected_type=ExpectedType.STRING,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )

    with factory() as session:
        object_id, field_id = _seed_field_with_object(
            session, tenant_id=tenant_id, field_label="MATERIAL_TYPE"
        )
        classification_field_id = _seed_field(
            session, tenant_id=tenant_id, field_label="HAZMAT_CLASSIFICATION"
        )
        OqiBusinessRuleRepositoryImpl(session).create(_rule(field_id, classification_field_id))
        # T1: HAZMAT, classification never admitted -> VIOLATED -> OPEN.
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference=ref,
            observed_representation="HAZMAT",
            received_at=NOW,
        )
        session.commit()

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=object_id, source_record_reference=ref
    )
    with factory() as session:
        rule_local = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert rule_local is not None
        evaluation = _horizoned_service(session).evaluate_current_state(
            rule=rule_local, subject=subject
        )
        assert evaluation is not None
        assert evaluation.outcome is EvaluationOutcome.VIOLATED
        session.commit()

    # T2: reclassify STANDARD (newer evidence) -> NOT_APPLICABLE -> RESOLVED.
    with factory() as session:
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference=ref,
            observed_representation="STANDARD",
            received_at=NOW + timedelta(hours=1),
        )
        session.commit()
    with factory() as session:
        rule_local = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert rule_local is not None
        evaluation = _horizoned_service(session).evaluate_current_state(
            rule=rule_local, subject=subject
        )
        assert evaluation is not None
        assert evaluation.outcome is EvaluationOutcome.NOT_APPLICABLE
        session.commit()
    with factory() as session:
        row = session.execute(
            text(
                "SELECT status, resolution_basis, reopen_count FROM business_rule_findings "
                "WHERE tenant_id = :t AND business_condition_id = :c"
            ),
            {"t": tenant_id, "c": condition_id},
        ).one()
        assert row[0] == "RESOLVED" and row[1] == "NOT_APPLICABLE" and row[2] == 0

    # T3: reclassify HAZMAT again (even newer evidence), classification
    # still never admitted -> VIOLATED again -> REOPEN. Race this step.
    with factory() as session:
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference=ref,
            observed_representation="HAZMAT",
            received_at=NOW + timedelta(hours=2),
        )
        session.commit()

    barrier = threading.Barrier(2)
    outcomes: dict[str, tuple[str, object]] = {}

    def _worker(session: Session, key: str) -> None:
        # Defensive: ANY exception must still release the transaction-scoped
        # seed-3 lock via rollback in `finally` -- an unhandled exception
        # left uncaught here would leave the session "idle in transaction"
        # holding the lock forever, deadlocking the sibling worker.
        try:
            rule_local = OqiBusinessRuleRepositoryImpl(session).get_active(
                tenant_id=tenant_id, business_condition_id=condition_id
            )
            assert rule_local is not None
            barrier.wait(timeout=5)
            evaluation = _horizoned_service(session).evaluate_current_state(
                rule=rule_local, subject=subject
            )
            assert evaluation is not None
            session.commit()
            outcomes[key] = ("committed", evaluation.evaluation_id)
        except IntegrityError:
            outcomes[key] = ("integrity_error", None)
        except BaseException as exc:  # noqa: BLE001
            outcomes[key] = ("error", repr(exc))
        finally:
            session.rollback()

    session_a, session_b = factory(), factory()
    thread_a = threading.Thread(target=_worker, args=(session_a, "a"))
    thread_b = threading.Thread(target=_worker, args=(session_b, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=15)
    thread_b.join(timeout=15)
    session_a.close()
    session_b.close()

    assert outcomes["a"][0] == "committed", outcomes["a"]
    assert outcomes["b"][0] == "committed", outcomes["b"]
    assert outcomes["a"][1] == outcomes["b"][1]  # identical evidence -> identical evaluation_id

    with factory() as session:
        row = session.execute(
            text(
                "SELECT status, reopen_count, occurrence_count, state_revision "
                "FROM business_rule_findings WHERE tenant_id = :t AND business_condition_id = :c"
            ),
            {"t": tenant_id, "c": condition_id},
        ).one()
    assert row[0] == "OPEN"
    assert row[1] == 1  # reopen_count incremented exactly once, not twice
    assert row[2] == 2  # occurrence_count: original violation + this reopen
    assert row[3] == 3  # state_revision: OPEN(1) -> RESOLVED(2) -> OPEN(3)


def test_current_state_evaluation_and_finding_atomicity_rollback(
    migrated_engine: Engine,
) -> None:
    """CDD-041 §21 step 16: a forced failure between Evaluation persistence
    and Finding mutation must roll back the entire transaction -- no
    orphan Evaluation, no partial Finding. A clean retry afterward succeeds
    normally with no residue from the failed attempt."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        object_id, field_id = _seed_field_with_object(
            setup_session, tenant_id=tenant_id, field_label="MATERIAL_TYPE"
        )
        classification_field_id = _seed_field(
            setup_session, tenant_id=tenant_id, field_label="HAZMAT_CLASSIFICATION"
        )
        rule = BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_id,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="applicable-hazmat",
                operator=Operator.EQ,
                input_role="material_type",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value="HAZMAT",
            ),
            predicate=ComparatorNode(
                clause_id="classification-required",
                operator=Operator.IS_NOT_NULL,
                input_role="hazmat_classification",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="material_type",
                    source_field_id=field_id,
                    required=True,
                    expected_type=ExpectedType.STRING,
                ),
                BusinessRuleInputBinding(
                    input_role="hazmat_classification",
                    source_field_id=classification_field_id,
                    required=True,
                    expected_type=ExpectedType.STRING,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
        OqiBusinessRuleRepositoryImpl(setup_session).create(rule)
        _admit_evidence(
            setup_session,
            source_field_id=field_id,
            source_record_reference="MAT-500",
            observed_representation="HAZMAT",
        )
        # hazmat_classification deliberately never admitted -> EMPTY -> VIOLATED.
        setup_session.commit()

    subject = SingleRecordSubject(
        tenant_id=tenant_id, source_object_id=object_id, source_record_reference="MAT-500"
    )

    class _FailingUpsertRepo(OqiBusinessRuleEvaluationRepositoryImpl):
        def upsert_finding(self, finding: Any) -> None:
            raise RuntimeError("forced failure between Evaluation persistence and Finding mutation")

    with factory() as session:
        rule_local = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert rule_local is not None
        failing_repo = _FailingUpsertRepo(session)
        service = OqiBusinessRuleEvaluationService(
            evaluation_repository=failing_repo,
            evidence_value_reader=OqiBusinessRuleEvidenceValueReader(session),
            clock=lambda: NOW,
        )
        with pytest.raises(RuntimeError):
            service.evaluate_current_state(rule=rule_local, subject=subject)
        session.rollback()

    with factory() as session:
        evaluation_count = session.execute(
            text(
                "SELECT count(*) FROM business_rule_evaluations WHERE tenant_id = :t "
                "AND business_condition_id = :c"
            ),
            {"t": tenant_id, "c": condition_id},
        ).scalar_one()
        finding_count = session.execute(
            text(
                "SELECT count(*) FROM business_rule_findings WHERE tenant_id = :t "
                "AND business_condition_id = :c"
            ),
            {"t": tenant_id, "c": condition_id},
        ).scalar_one()
    assert evaluation_count == 0  # entire transaction rolled back
    assert finding_count == 0

    # Clean retry succeeds normally, no residue from the failed attempt.
    with factory() as session:
        rule_local = OqiBusinessRuleRepositoryImpl(session).get_active(
            tenant_id=tenant_id, business_condition_id=condition_id
        )
        assert rule_local is not None
        evaluation = _current_state_service(session).evaluate_current_state(
            rule=rule_local, subject=subject
        )
        assert evaluation is not None
        session.commit()
    with factory() as session:
        evaluation_count = session.execute(
            text(
                "SELECT count(*) FROM business_rule_evaluations WHERE tenant_id = :t "
                "AND business_condition_id = :c"
            ),
            {"t": tenant_id, "c": condition_id},
        ).scalar_one()
        finding_count = session.execute(
            text(
                "SELECT count(*) FROM business_rule_findings WHERE tenant_id = :t "
                "AND business_condition_id = :c"
            ),
            {"t": tenant_id, "c": condition_id},
        ).scalar_one()
    assert evaluation_count == 1
    assert finding_count == 1


def test_current_state_tenant_isolation_distinct_findings(migrated_engine: Engine) -> None:
    """CDD-041 §15, §24: one BusinessRule/SourceObject/subject reference,
    evaluated with two different `subject.tenant_id` values. Finding
    identity includes `tenant_id` as its own dimension (independent of
    `business_condition_id`/`subject_identity`), so the two evaluations
    must never collide into one Finding row -- two structurally
    independent Finding identities must exist, each keyed to its own
    tenant_id, never a shared/overwritten row."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    condition_id = f"cond-{uuid4()}"
    tenant_a, tenant_b = f"tenant-a-{uuid4()}", f"tenant-b-{uuid4()}"
    reference = "SHARED-REF-1"

    with factory() as session:
        object_id, field_id = _seed_field_with_object(
            session, tenant_id=tenant_a, field_label="MATERIAL_TYPE"
        )
        classification_field_id = _seed_field(
            session, tenant_id=tenant_a, field_label="HAZMAT_CLASSIFICATION"
        )
        rule = BusinessRule.new(
            business_condition_id=condition_id,
            version=1,
            tenant_id=tenant_a,
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="applicable-hazmat",
                operator=Operator.EQ,
                input_role="material_type",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value="HAZMAT",
            ),
            predicate=ComparatorNode(
                clause_id="classification-required",
                operator=Operator.IS_NOT_NULL,
                input_role="hazmat_classification",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(
                BusinessRuleInputBinding(
                    input_role="material_type",
                    source_field_id=field_id,
                    required=True,
                    expected_type=ExpectedType.STRING,
                ),
                BusinessRuleInputBinding(
                    input_role="hazmat_classification",
                    source_field_id=classification_field_id,
                    required=True,
                    expected_type=ExpectedType.STRING,
                ),
            ),
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
        OqiBusinessRuleRepositoryImpl(session).create(rule)
        _admit_evidence(
            session,
            source_field_id=field_id,
            source_record_reference=reference,
            observed_representation="HAZMAT",
        )
        # hazmat_classification deliberately never admitted -> EMPTY -> VIOLATED.
        session.commit()

    findings = {}
    for tenant_id in (tenant_a, tenant_b):
        with factory() as session:
            rule_local = OqiBusinessRuleRepositoryImpl(session).get_by_id(rule.rule_id)
            assert rule_local is not None
            subject = SingleRecordSubject(
                tenant_id=tenant_id, source_object_id=object_id, source_record_reference=reference
            )
            evaluation = _current_state_service(session).evaluate_current_state(
                rule=rule_local, subject=subject
            )
            assert evaluation is not None
            session.commit()
            findings[tenant_id] = evaluation

    assert findings[tenant_a].tenant_id != findings[tenant_b].tenant_id
    with factory() as session:
        finding_rows = session.execute(
            text(
                "SELECT tenant_id, finding_id FROM business_rule_findings "
                "WHERE business_condition_id = :c"
            ),
            {"c": condition_id},
        ).all()
    assert len(finding_rows) == 2
    finding_ids = {row[1] for row in finding_rows}
    assert len(finding_ids) == 2  # two structurally distinct Finding identities
    tenant_ids_present = {row[0] for row in finding_rows}
    assert tenant_ids_present == {tenant_a, tenant_b}
