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
from datetime import UTC, datetime
from uuid import UUID, uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
from app.infrastructure.persistence.models.oqi_business_rule import BusinessRuleORM
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
