"""CDD-087 §28 CREATE 4: real-PostgreSQL integration tests for
golden-demo-restore's database-requiring safety-predicate checks (4/5),
its exact four-table scoped delete + reseed, transactionality, and the
three new demo-verify assertions (CDD-087 §13). Unit-level, no-database
checks (Checks 1-3, the environment Literal) live in
test_database_cli.py.

golden_demo_restore() commits for real against its own, separate session
-- it is not compatible with the savepoint-rollback isolation every other
`_postgres.py` file uses against the shared, session-scoped
`migrated_engine`, and a first implementation of this file proved, via an
isolated before/after full-suite comparison, that letting it commit real
`ctec-demo-tenant` context rows (EnterpriseEntity, SourceSystem, etc. --
DemoOqiSeeder's own intentionally-permanent, never-deleted context) into
that SHARED database corrupts other, unrelated test files that assume it
stays exactly as they left it for the rest of the pytest session.

This module therefore never touches the shared `migrated_engine` at all:
every test in it runs against its own dedicated, disposable PostgreSQL
database -- created fresh at module setup (migrated to head, Ontology/
Blueprint-seeded, then one initial golden_demo_restore()) and dropped at
module teardown. No other test file can ever observe anything this module
does."""

# isort: skip_file
from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, delete, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_remediation_service import OqiRemediationService
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.core.config import get_settings
from app.domain.oqi_cross_source.evaluation import derive_comparison_finding_id
from app.domain.oqi_remediation.case import FindingFamily
from app.infrastructure.persistence.blueprint_seed import BlueprintSeeder
from app.infrastructure.persistence.database_cli import (
    _GOLDEN_RESTORE_EXPECTED_MIGRATION_HEAD,
    GoldenDemoRestoreNotAllowedError,
    demo_verify,
    golden_demo_restore,
)
from app.infrastructure.persistence.demo_oqi_seeder import (
    _COMPARISON_SUBJECT_ID,
    _QUALITY_CONDITION_ID,
)
from app.infrastructure.persistence.models.oqi_business_impact import CurrentRelianceORM
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationAuthorizationORM,
    OqiRemediationCaseORM,
    OqiRemediationInstructionORM,
)
from app.infrastructure.persistence.models.oqi_uniqueness import (
    UniquenessAdjudicationORM,
    UniquenessCandidateORM,
    UniquenessEvaluationORM,
)
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)
from app.infrastructure.persistence.session import create_session_factory

FINDING_ID: UUID = derive_comparison_finding_id(
    tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
    quality_condition_id=_QUALITY_CONDITION_ID,
    comparison_subject_id=_COMPARISON_SUBJECT_ID,
)


@pytest.fixture(scope="module")
def dedicated_engine(test_database_url: str) -> Generator[Engine, None, None]:
    """A throwaway PostgreSQL database, private to this module: created
    here, migrated to head, dropped at teardown. Never the shared
    `migrated_engine` every other `_postgres.py` file uses -- see this
    module's own docstring for why golden_demo_restore()'s real commits
    make that unsafe to share."""
    base_url = make_url(test_database_url)
    db_name = f"ctec_golden_restore_i1_{uuid.uuid4().hex[:12]}"
    admin_engine = create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{db_name}"'))

    dedicated_url = base_url.set(database=db_name).render_as_string(hide_password=False)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", dedicated_url)
    # CDD-087: the project's own alembic env.py reads CTEC_DATABASE_URL from
    # the environment, not from Config.set_main_option -- confirmed by
    # mirroring conftest.py's own migrated_engine fixture exactly, the
    # established precedent for every other _postgres.py file.
    previous_database_url = os.environ.get("CTEC_DATABASE_URL")
    os.environ["CTEC_DATABASE_URL"] = dedicated_url
    alembic.command.upgrade(config, "head")

    engine = create_engine(dedicated_url)
    try:
        yield engine
    finally:
        engine.dispose()
        if previous_database_url is None:
            os.environ.pop("CTEC_DATABASE_URL", None)
        else:
            os.environ["CTEC_DATABASE_URL"] = previous_database_url
        with admin_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid <> pg_backend_pid()"
                ),
                {"db": db_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin_engine.dispose()


@pytest.fixture(scope="module", autouse=True)
def _pristine_golden_bracket(dedicated_engine: Engine) -> Generator[None, None, None]:
    """Points CTEC_DATABASE_URL (dedicated_engine already keeps this env
    var pointed at the dedicated database for its own whole lifetime) and
    golden-demo-restore's own three env vars at that database for this
    module's entire lifetime (manual save/restore -- `monkeypatch` is
    function-scoped only), seeds Ontology/Blueprint once (DemoOqiSeeder's
    own prerequisite), then calls golden_demo_restore() to establish the
    pristine baseline every test in this module starts from."""
    host = dedicated_engine.url.host
    previous = {
        name: os.environ.get(name)
        for name in (
            "CTEC_GOLDEN_DEMO_RESTORE_ALLOWED",
            "CTEC_ENVIRONMENT",
            "CTEC_GOLDEN_RESTORE_EXPECTED_HOST",
        )
    }
    os.environ["CTEC_GOLDEN_DEMO_RESTORE_ALLOWED"] = "true"
    os.environ["CTEC_ENVIRONMENT"] = "demo"
    os.environ["CTEC_GOLDEN_RESTORE_EXPECTED_HOST"] = host or ""
    get_settings.cache_clear()

    with create_session_factory(dedicated_engine)() as session:
        OntologySeeder(session).load()
        session.commit()
        BlueprintSeeder(session).load()
        session.commit()

    golden_demo_restore()
    yield

    for name, value in previous.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    get_settings.cache_clear()


@pytest.fixture()
def factory(dedicated_engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(dedicated_engine)


def _progress_one_candidate_to_approved(factory: sessionmaker[Session]) -> None:
    """Real production remediation service, real commits (never the
    savepoint-joined fixture pattern -- golden_demo_restore opens its own,
    separate session/connection, so state must be genuinely committed for
    it to see and clean up). One committed session per step, mirroring
    how these are actually invoked as separate HTTP requests in
    production -- `create_session_factory`'s own `autoflush=False`
    (unlike the golden-story suite's own dedicated, autoflush-enabled
    fixture) means a single shared, uncommitted session cannot chain
    these calls the way test_noetva_demo_readiness_golden_story.py's own
    `session` fixture can."""
    with factory() as session:
        repo = OqiRemediationRepositoryImpl(session)
        service = OqiRemediationService(
            repository=repo, participant_reader=OqiRemediationParticipantReader(session)
        )
        _case, candidates = service.extract_candidates(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            finding_family=FindingFamily.OQI2,
            finding_id=FINDING_ID,
        )
        chosen = candidates[0]
        instruction = service.construct_instruction(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            candidate_id=chosen.candidate_id,
            created_by="test-database-cli-postgres",
        )
        session.commit()

    with factory() as session:
        repo = OqiRemediationRepositoryImpl(session)
        service = OqiRemediationService(
            repository=repo, participant_reader=OqiRemediationParticipantReader(session)
        )
        authorization = service.request_authorization(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            instruction_id=instruction.instruction_id,
            requested_by="requester",
        )
        session.commit()

    with factory() as session:
        repo = OqiRemediationRepositoryImpl(session)
        service = OqiRemediationService(
            repository=repo, participant_reader=OqiRemediationParticipantReader(session)
        )
        service.approve(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            authorization_id=authorization.authorization_id,
            decided_by="approver",
        )
        session.commit()


def _remediation_row_counts(session: Session) -> dict[str, int]:
    return {
        "cases": session.scalar(
            select(text("count(*)"))
            .select_from(OqiRemediationCaseORM)
            .where(OqiRemediationCaseORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        )
        or 0,
        "instructions": session.scalar(
            select(text("count(*)"))
            .select_from(OqiRemediationInstructionORM)
            .where(OqiRemediationInstructionORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        )
        or 0,
        "authorizations": session.scalar(
            select(text("count(*)"))
            .select_from(OqiRemediationAuthorizationORM)
            .where(OqiRemediationAuthorizationORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        )
        or 0,
    }


# ----------------------------------------------------------------------
# Refusal paths (Checks 4/5 -- database-requiring).
# ----------------------------------------------------------------------


def test_check4_wrong_migration_head_refuses(dedicated_engine: Engine) -> None:
    with dedicated_engine.connect() as connection:
        original: str = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        connection.execute(
            text("UPDATE alembic_version SET version_num = :v"), {"v": "not_the_real_head"}
        )
        connection.commit()
    try:
        with pytest.raises(GoldenDemoRestoreNotAllowedError, match="migration head"):
            golden_demo_restore()
    finally:
        with dedicated_engine.connect() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": original})
            connection.commit()
    assert original == _GOLDEN_RESTORE_EXPECTED_MIGRATION_HEAD


def test_check5_foreign_tenant_present_refuses(factory: sessionmaker[Session]) -> None:
    now = datetime.now(UTC)
    foreign_case_id = derive_comparison_finding_id(
        tenant_id="a-foreign-tenant",
        quality_condition_id=_QUALITY_CONDITION_ID,
        comparison_subject_id=_COMPARISON_SUBJECT_ID,
    )
    with factory() as session:
        session.add(
            OqiRemediationCaseORM(
                case_id=foreign_case_id,
                tenant_id="a-foreign-tenant",
                finding_family="OQI2",
                finding_id=FINDING_ID,
                status="AWAITING_AUTHORITY",
                external_execution_claimed=False,
                external_execution_claimed_on=None,
                created_on=now,
                updated_on=now,
            )
        )
        session.commit()
    try:
        with pytest.raises(GoldenDemoRestoreNotAllowedError, match="unexpected tenant"):
            golden_demo_restore()
    finally:
        with factory() as session:
            session.execute(
                delete(OqiRemediationCaseORM).where(
                    OqiRemediationCaseORM.case_id == foreign_case_id
                )
            )
            session.commit()


# ----------------------------------------------------------------------
# Restore success, uniqueness-ledger preservation, repeatability.
# ----------------------------------------------------------------------


def test_restore_cleans_remediation_state_and_leaves_uniqueness_ledger_untouched(
    factory: sessionmaker[Session],
) -> None:
    _progress_one_candidate_to_approved(factory)
    with factory() as session:
        progressed = _remediation_row_counts(session)
        uniqueness_candidates_before = (
            session.execute(
                select(UniquenessCandidateORM.candidate_id).where(
                    UniquenessCandidateORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
                )
            )
            .scalars()
            .all()
        )
        uniqueness_evaluations_before = session.scalar(
            select(text("count(*)"))
            .select_from(UniquenessEvaluationORM)
            .where(UniquenessEvaluationORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        )
    assert progressed["authorizations"] > 0, "setup must have produced an APPROVED authorization"

    golden_demo_restore()

    with factory() as session:
        restored = _remediation_row_counts(session)
        # DemoOqiSeeder never creates a oqi_remediation_cases row itself
        # (confirmed directly: a completely fresh golden-demo-restore
        # yields zero cases) -- OqiRemediationService.extract_candidates()
        # lazily get-or-creates the case on its own first call. A
        # correctly restored Golden environment therefore has ZERO
        # remediation cases/instructions/authorizations: nothing has been
        # prepared/requested/decided yet.
        assert restored["cases"] == 0
        assert restored["instructions"] == 0
        assert restored["authorizations"] == 0

        uniqueness_candidates_after = (
            session.execute(
                select(UniquenessCandidateORM.candidate_id).where(
                    UniquenessCandidateORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
                )
            )
            .scalars()
            .all()
        )
        uniqueness_evaluations_after = session.scalar(
            select(text("count(*)"))
            .select_from(UniquenessEvaluationORM)
            .where(UniquenessEvaluationORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID)
        )
        stale_adjudications = (
            session.execute(
                select(UniquenessAdjudicationORM).where(
                    UniquenessAdjudicationORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
                )
            )
            .scalars()
            .all()
        )

    # The append-only uniqueness ledger is never touched by restore: the
    # candidate identity set is unchanged, and the evaluation ledger only
    # ever grows (idempotent re-evaluation), never shrinks.
    assert set(uniqueness_candidates_after) == set(uniqueness_candidates_before)
    assert uniqueness_evaluations_after >= uniqueness_evaluations_before
    assert stale_adjudications == []

    assert demo_verify() is True


def test_restore_is_repeatable(factory: sessionmaker[Session]) -> None:
    golden_demo_restore()
    assert demo_verify() is True
    with factory() as session:
        first = _remediation_row_counts(session)

    _progress_one_candidate_to_approved(factory)
    golden_demo_restore()
    assert demo_verify() is True
    with factory() as session:
        second = _remediation_row_counts(session)

    assert first == second == {"cases": 0, "instructions": 0, "authorizations": 0}


# ----------------------------------------------------------------------
# Transactionality.
# ----------------------------------------------------------------------


def test_restore_leaves_no_partial_cleanup_on_mid_operation_failure(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    _progress_one_candidate_to_approved(factory)
    with factory() as session:
        before = _remediation_row_counts(session)
    assert before["authorizations"] > 0

    from app.infrastructure.persistence import demo_oqi_seeder as demo_oqi_seeder_module

    def _boom(self: object, *, tenant_id: str) -> None:
        del self, tenant_id
        raise RuntimeError("injected mid-restore failure")

    monkeypatch.setattr(demo_oqi_seeder_module.DemoOqiSeeder, "seed", _boom)

    with pytest.raises(RuntimeError, match="injected mid-restore failure"):
        golden_demo_restore()

    with factory() as session:
        after = _remediation_row_counts(session)
    assert after == before, (
        "a failure after the scoped DELETE but before the final commit must leave the "
        "database completely unchanged -- not partially cleaned"
    )


# ----------------------------------------------------------------------
# demo-verify: the three new investor-critical assertions.
# ----------------------------------------------------------------------


def test_demo_verify_asserts_business_impact_high_and_reliance_at_risk_and_ask_noetva() -> None:
    golden_demo_restore()
    assert demo_verify() is True


def test_demo_verify_fails_when_reliance_state_is_corrupted(
    factory: sessionmaker[Session],
) -> None:
    golden_demo_restore()
    assert demo_verify() is True

    with factory() as session:
        session.execute(
            delete(CurrentRelianceORM).where(
                CurrentRelianceORM.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
            )
        )
        session.commit()
    try:
        assert demo_verify() is False
    finally:
        golden_demo_restore()  # leave the module's own bracket a clean baseline
