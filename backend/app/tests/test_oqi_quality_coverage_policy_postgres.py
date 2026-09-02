"""CDD-047 Artifact Authorization row 8: real-Postgres proofs for
`QualityCoveragePolicy` persistence -- the partial active-uniqueness
index, the dimension child-table closed-vocabulary constraint, migration
round-trip, and tenant isolation."""

# isort: skip_file
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_quality_coverage.policy import (
    CoverageDimension,
    create_quality_coverage_policy,
)
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
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


def test_migration_creates_exactly_two_new_tables(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name LIKE 'oqi_quality_coverage%'"
                )
            )
        }
    assert tables == {
        "oqi_quality_coverage_policies",
        "oqi_quality_coverage_policy_dimensions",
    }


def test_migration_round_trip_delta_is_exactly_two(migrated_engine: Engine) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    def _count() -> int:
        with migrated_engine.connect() as connection:
            return int(
                connection.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_type='BASE TABLE' "
                        "AND table_name != 'alembic_version'"
                    )
                ).scalar_one()
            )

    post_h1 = _count()
    alembic.command.downgrade(config, "0026_oqi6_reliance")
    pre_h1 = _count()
    assert post_h1 - pre_h1 == 2
    alembic.command.upgrade(config, "head")
    assert _count() == post_h1


def test_insert_and_retrieve_active_policy(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    anchor_id = uuid4()
    policy = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=anchor_id,
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS, CoverageDimension.VALIDITY}),
        created_by="steward",
        created_on=NOW,
    )
    repo = OqiQualityCoveragePolicyRepositoryImpl(session)
    repo.insert_policy(policy)
    session.flush()

    retrieved = repo.get_active_policy(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=anchor_id,
    )
    assert retrieved is not None
    assert retrieved.policy_id == policy.policy_id
    assert retrieved.required_dimensions == policy.required_dimensions


def test_two_active_policies_same_anchor_rejected_by_database(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    anchor_id = uuid4()
    repo = OqiQualityCoveragePolicyRepositoryImpl(session)
    first = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=anchor_id,
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
        created_by="steward",
        created_on=NOW,
    )
    repo.insert_policy(first)
    session.flush()

    second = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=anchor_id,
        required_dimensions=frozenset({CoverageDimension.VALIDITY}),
        created_by="steward",
        created_on=NOW,
    )
    with pytest.raises(IntegrityError):
        repo.insert_policy(second)


def test_different_tenant_may_independently_activate_same_anchor(session: Session) -> None:
    anchor_id = uuid4()
    tenant_a = f"tenant-a-{uuid4()}"
    tenant_b = f"tenant-b-{uuid4()}"
    repo = OqiQualityCoveragePolicyRepositoryImpl(session)
    repo.insert_policy(
        create_quality_coverage_policy(
            policy_id=uuid4(),
            tenant_id=tenant_a,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=anchor_id,
            required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
            created_by="steward",
            created_on=NOW,
        )
    )
    # Must not raise -- a different tenant, same anchor, is independent.
    repo.insert_policy(
        create_quality_coverage_policy(
            policy_id=uuid4(),
            tenant_id=tenant_b,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=anchor_id,
            required_dimensions=frozenset({CoverageDimension.VALIDITY}),
            created_by="steward",
            created_on=NOW,
        )
    )
    session.flush()
    assert (
        repo.get_active_policy(
            tenant_id=tenant_a,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=anchor_id,
        )
        is not None
    )
    assert (
        repo.get_active_policy(
            tenant_id=tenant_b,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=anchor_id,
        )
        is not None
    )


def test_different_anchor_may_independently_activate_same_tenant(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    repo = OqiQualityCoveragePolicyRepositoryImpl(session)
    repo.insert_policy(
        create_quality_coverage_policy(
            policy_id=uuid4(),
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
            created_by="steward",
            created_on=NOW,
        )
    )
    # Must not raise -- a different anchor, same tenant, is independent.
    repo.insert_policy(
        create_quality_coverage_policy(
            policy_id=uuid4(),
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            required_dimensions=frozenset({CoverageDimension.VALIDITY}),
            created_by="steward",
            created_on=NOW,
        )
    )
    session.flush()


def test_retired_and_active_versions_coexist(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    anchor_id = uuid4()
    repo = OqiQualityCoveragePolicyRepositoryImpl(session)
    v1 = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=anchor_id,
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
        created_by="steward",
        created_on=NOW,
    )
    repo.insert_policy(v1)
    session.flush()

    from app.domain.oqi_quality_coverage.policy import (
        QualityCoveragePolicyStatus,
        new_quality_coverage_policy_version,
    )

    # Cannot mutate in place; simulate retirement via a raw update since
    # `insert_policy` only ever inserts (immutability, CDD-047 §8, §10) --
    # retiring a specific row in isolation (without also activating a
    # successor) is exercised here purely to prove RETIRED + a later
    # ACTIVE version of a DIFFERENT policy_id can coexist for the anchor.
    session.execute(
        text("UPDATE oqi_quality_coverage_policies SET status = 'RETIRED' WHERE policy_id = :pid"),
        {"pid": v1.policy_id},
    )
    session.flush()

    v2 = new_quality_coverage_policy_version(
        v1,
        new_policy_id=uuid4(),
        status=QualityCoveragePolicyStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )
    repo.insert_policy(v2)
    session.flush()

    active = repo.get_active_policy(
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=anchor_id,
    )
    assert active is not None
    assert active.policy_id == v2.policy_id
    assert active.version_number == 2


def test_dimension_child_table_rejects_unknown_value_at_database_level(session: Session) -> None:
    tenant_id = f"tenant-{uuid4()}"
    policy_id = uuid4()
    session.execute(
        text(
            "INSERT INTO oqi_quality_coverage_policies "
            "(policy_id, tenant_id, ontology_element_type, ontology_element_id, status, "
            "version_number, previous_version_id, created_by, created_on) "
            "VALUES (:pid, :tid, 'ENTITY', :oid, 'ACTIVE', 1, NULL, 'steward', :now)"
        ),
        {"pid": policy_id, "tid": tenant_id, "oid": uuid4(), "now": NOW},
    )
    session.flush()
    with pytest.raises(IntegrityError):
        # Short enough to fit String(16) so the CHECK constraint itself
        # is what rejects it, not a column-width DataError first.
        session.execute(
            text(
                "INSERT INTO oqi_quality_coverage_policy_dimensions (policy_id, dimension) "
                "VALUES (:pid, 'BOGUS_VALUE')"
            ),
            {"pid": policy_id},
        )
        session.flush()


def test_dimension_child_table_rejects_duplicate_dimension_for_same_policy(
    session: Session,
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    policy = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
        created_by="steward",
        created_on=NOW,
    )
    OqiQualityCoveragePolicyRepositoryImpl(session).insert_policy(policy)
    session.flush()
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO oqi_quality_coverage_policy_dimensions (policy_id, dimension) "
                "VALUES (:pid, 'COMPLETENESS')"
            ),
            {"pid": policy.policy_id},
        )
        session.flush()


def test_cross_tenant_active_policy_lookup_returns_none(session: Session) -> None:
    tenant_a = f"tenant-a-{uuid4()}"
    tenant_b = f"tenant-b-{uuid4()}"
    anchor_id = uuid4()
    repo = OqiQualityCoveragePolicyRepositoryImpl(session)
    repo.insert_policy(
        create_quality_coverage_policy(
            policy_id=uuid4(),
            tenant_id=tenant_a,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=anchor_id,
            required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
            created_by="steward",
            created_on=NOW,
        )
    )
    session.flush()
    assert (
        repo.get_active_policy(
            tenant_id=tenant_b,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=anchor_id,
        )
        is None
    )
