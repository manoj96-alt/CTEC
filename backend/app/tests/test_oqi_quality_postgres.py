"""Real-PostgreSQL acceptance evidence for OQI1 (CDD-039 §18, §21, §24-§25,
§39; OQI1 Artifact Authorization §4; Concurrency Hardening Amendment §11-
§14). Proves what a fake repository cannot: migration schema correctness;
the `pg_advisory_xact_lock(hashtextextended(...))` mechanism genuinely
serializes concurrent `evaluate_current_state()` calls for the same
Finding lineage, including the critical case where no `QualityFinding` row
exists yet; evidence is never selected before authority is held (proven
directly, not merely asserted, by admitting new evidence while a second
worker waits); transaction rollback releases the lock; identical replay
under real concurrency does not double-mutate; different tenants/subjects
never block each other; and every "one ACTIVE rule version per condition"
database-level invariant genuinely holds."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_quality_evaluation_service import OqiQualityEvaluationService
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.oqi.evaluation import EvaluationSubject, SourceRecordLineageIdentity
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.oqi_quality_evaluation import QualityEvaluationORM
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_quality_rule import QualityRuleORM
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OqiQualityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.tests.test_source_field_persistence_postgres import _seed_source_object, _source_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _seed_field(
    session: Session, *, tenant_id: str, field_label: str = "LFA1-COUNTRY"
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
    observed_representation: str = "US",
) -> UUID:
    evidence = FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference=source_record_reference,
        observed_representation=observed_representation,
        observed_at=NOW,
        received_at=NOW,
    )
    FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(evidence)
    return evidence.field_value_evidence_id.value


def _completeness_rule(*, quality_condition_id: str) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=quality_condition_id,
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


def _subject(
    *, tenant_id: str, source_object_id: UUID, source_field_id: UUID, reference: str
) -> EvaluationSubject:
    return EvaluationSubject(
        lineage=SourceRecordLineageIdentity(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_record_reference=reference,
        ),
        source_field_id=source_field_id,
    )


def _service(
    session: Session, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
) -> OqiQualityEvaluationService:
    return OqiQualityEvaluationService(
        evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=clock
    )


# --- schema ---


def test_migration_creates_expected_schema(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    tables = set(inspector.get_table_names())
    assert {
        "quality_rules",
        "quality_evaluations",
        "quality_evaluation_evidence",
        "quality_findings",
    } <= tables

    rule_columns = {c["name"] for c in inspector.get_columns("quality_rules")}
    assert rule_columns == {
        "rule_id",
        "quality_condition_id",
        "version",
        "dimension",
        "finding_type",
        "validity_primitive",
        "information_element_requirement_id",
        "rule_parameters",
        "status",
        "created_by",
        "created_on",
        "retired_on",
    }

    evaluation_columns = {c["name"] for c in inspector.get_columns("quality_evaluations")}
    assert evaluation_columns == {
        "evaluation_id",
        "tenant_id",
        "quality_condition_id",
        "rule_id",
        "rule_version",
        "subject_type",
        "source_object_id",
        "source_record_reference",
        "source_field_id",
        "evaluation_mode",
        "evaluation_origin",
        "evaluation_horizon",
        "evidence_set_digest",
        "outcome",
        "applied_current_state_authority",
        "state_revision_applied",
        "evaluated_on",
    }

    finding_columns = {c["name"] for c in inspector.get_columns("quality_findings")}
    assert finding_columns == {
        "finding_id",
        "tenant_id",
        "quality_condition_id",
        "subject_type",
        "source_object_id",
        "source_record_reference",
        "source_field_id",
        "finding_type",
        "status",
        "state_revision",
        "first_seen_at",
        "last_seen_at",
        "last_evaluated_horizon",
        "occurrence_count",
        "reopen_count",
    }


def test_migration_head_revision(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "0021_oqi2_cross_source"


# --- database constraints ---


def test_one_active_rule_version_per_condition_enforced_by_database(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        repo = OqiQualityRuleRepositoryImpl(session)
        repo.create(_completeness_rule(quality_condition_id=condition_id))
        session.commit()

    with factory() as session:
        second_version = QualityRule.new(
            quality_condition_id=condition_id,
            version=2,
            dimension=QualityDimension.COMPLETENESS,
            finding_type=QualityFindingType.MISSING_VALUE,
            validity_primitive=None,
            information_element_requirement_id="req-1",
            rule_parameters={},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        session.add(
            QualityRuleORM(
                rule_id=second_version.rule_id,
                quality_condition_id=second_version.quality_condition_id,
                version=second_version.version,
                dimension=second_version.dimension.value,
                finding_type=second_version.finding_type.value,
                validity_primitive=None,
                information_element_requirement_id="req-1",
                rule_parameters={},
                status="ACTIVE",
                created_by="steward",
                created_on=NOW,
                retired_on=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_activate_new_version_retires_previous_active(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    condition_id = f"cond-{uuid4()}"
    with factory() as session:
        repo = OqiQualityRuleRepositoryImpl(session)
        v1 = _completeness_rule(quality_condition_id=condition_id)
        repo.create(v1)
        session.commit()

    with factory() as session:
        repo = OqiQualityRuleRepositoryImpl(session)
        v2 = QualityRule.new(
            quality_condition_id=condition_id,
            version=2,
            dimension=QualityDimension.COMPLETENESS,
            finding_type=QualityFindingType.MISSING_VALUE,
            validity_primitive=None,
            information_element_requirement_id="req-1",
            rule_parameters={},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        repo.activate_new_version(v2, retired_on=NOW)
        session.commit()

    with factory() as session:
        active = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        assert active is not None
        assert active.version == 2
        retired_row = session.get(QualityRuleORM, v1.rule_id)
        assert retired_row is not None
        assert retired_row.status == "RETIRED"
        assert retired_row.retired_on is not None


def test_evaluation_fk_integrity_rejects_unknown_rule(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    with factory() as session:
        tenant_id = f"tenant-{uuid4()}"
        source_object_id, source_field_id = _seed_field(session, tenant_id=tenant_id)
        session.commit()
    with factory() as session:
        session.add(
            QualityEvaluationORM(
                evaluation_id=uuid4(),
                tenant_id=tenant_id,
                quality_condition_id="cond-x",
                rule_id=uuid4(),
                rule_version=1,
                subject_type="SOURCE_FIELD_RECORD",
                source_object_id=source_object_id,
                source_record_reference="100045",
                evaluation_mode="CURRENT_STATE",
                evaluation_origin="RULE_DETERMINISTIC",
                evaluation_horizon=NOW,
                evidence_set_digest="x" * 64,
                outcome="VIOLATED",
                applied_current_state_authority=True,
                state_revision_applied=1,
                evaluated_on=NOW,
                source_field_id=source_field_id,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


# --- first-Finding concurrency (the core proof) ---


def test_concurrent_first_violation_serializes_to_one_finding(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        source_object_id, source_field_id = _seed_field(setup_session, tenant_id=tenant_id)
        OqiQualityRuleRepositoryImpl(setup_session).create(
            _completeness_rule(quality_condition_id=condition_id)
        )
        setup_session.commit()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="100045",
    )
    rule = _completeness_rule(quality_condition_id=condition_id)
    # Establish the lineage as known via a sibling field's evidence, but
    # leave the *target* field with zero evidence -- MISSING_VALUE for both
    # workers.
    with factory() as evidence_session:
        _admit_evidence(
            evidence_session,
            source_field_id=source_field_id,
            source_record_reference="100045",
            observed_representation="",
        )
        # A different SourceField under the same SourceObject establishes
        # known lineage without qualifying the target field itself.
        sibling_field = _source_field(source_object_id=source_object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(evidence_session).create(sibling_field)
        evidence_session.flush()
        _admit_evidence(
            evidence_session,
            source_field_id=sibling_field.source_field_id.value,
            source_record_reference="100045",
            observed_representation="Acme Ltd",
        )
        evidence_session.commit()

    lock_held = threading.Event()
    outcomes: dict[str, str] = {}
    horizons = {"a": NOW, "b": NOW}

    def _first(session: Session, label: str) -> None:
        service = _service(session, clock=lambda: horizons[label])
        service.evaluate_current_state(rule=rule, subject=subject)
        lock_held.set()
        time.sleep(0.3)
        session.commit()
        outcomes[label] = "done"

    def _second(session: Session, label: str) -> None:
        assert lock_held.wait(timeout=5)
        service = _service(session, clock=lambda: horizons[label])
        service.evaluate_current_state(rule=rule, subject=subject)
        session.commit()
        outcomes[label] = "done"

    session_a = factory()
    session_b = factory()
    horizons["b"] = NOW.replace(microsecond=1)  # distinct evaluation_id from "a"
    thread_a = threading.Thread(target=_first, args=(session_a, "a"))
    thread_b = threading.Thread(target=_second, args=(session_b, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    assert outcomes == {"a": "done", "b": "done"}

    with factory() as verify_session:
        findings = (
            verify_session.execute(
                select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert len(findings) == 1
        finding = findings[0]
        assert finding.status == "OPEN"
        assert finding.state_revision == 2  # both evaluations genuinely, serially applied

        evaluations = (
            verify_session.execute(
                select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert len(evaluations) == 2  # two distinct genuine evaluation attempts


def test_concurrent_violated_then_satisfied_race(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        source_object_id, source_field_id = _seed_field(setup_session, tenant_id=tenant_id)
        OqiQualityRuleRepositoryImpl(setup_session).create(
            _completeness_rule(quality_condition_id=condition_id)
        )
        setup_session.commit()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="100046",
    )
    rule = _completeness_rule(quality_condition_id=condition_id)

    # Seed an existing OPEN finding first (sequential, no evidence yet on
    # the target field, but known lineage via a sibling field's real
    # evidence -- an empty-row observation does not establish known
    # lineage, CDD-039 §12).
    with factory() as session:
        service = _service(session, clock=lambda: NOW)
        sibling_field = _source_field(source_object_id=source_object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(sibling_field)
        session.flush()
        _admit_evidence(
            session,
            source_field_id=sibling_field.source_field_id.value,
            source_record_reference="100046",
            observed_representation="Acme Ltd",
        )
        service.evaluate_current_state(rule=rule, subject=subject)
        session.commit()

    # Now add qualifying evidence, then race two evaluations against the
    # now-OPEN finding.
    with factory() as session:
        _admit_evidence(session, source_field_id=source_field_id, source_record_reference="100046")
        session.commit()

    lock_held = threading.Event()
    outcomes: dict[str, str] = {}
    horizons = {"a": NOW.replace(hour=1), "b": NOW.replace(hour=2)}

    def _first(session: Session, label: str) -> None:
        service = _service(session, clock=lambda: horizons[label])
        service.evaluate_current_state(rule=rule, subject=subject)
        lock_held.set()
        time.sleep(0.3)
        session.commit()
        outcomes[label] = "done"

    def _second(session: Session, label: str) -> None:
        assert lock_held.wait(timeout=5)
        service = _service(session, clock=lambda: horizons[label])
        service.evaluate_current_state(rule=rule, subject=subject)
        session.commit()
        outcomes[label] = "done"

    session_a = factory()
    session_b = factory()
    thread_a = threading.Thread(target=_first, args=(session_a, "a"))
    thread_b = threading.Thread(target=_second, args=(session_b, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    assert outcomes == {"a": "done", "b": "done"}

    with factory() as verify_session:
        findings = (
            verify_session.execute(
                select(QualityFindingORM).where(
                    QualityFindingORM.tenant_id == tenant_id,
                    QualityFindingORM.source_record_reference == "100046",
                )
            )
            .scalars()
            .all()
        )
        assert len(findings) == 1
        assert findings[0].status == "RESOLVED"
        assert findings[0].state_revision == 3  # create(1) + resolve(2) + reconfirm(3)


def test_evidence_arrival_while_second_worker_waits(migrated_engine: Engine) -> None:
    """The single most important OQI1 concurrency test: proves evidence is
    genuinely selected *after* authority is acquired, not before."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        source_object_id, source_field_id = _seed_field(setup_session, tenant_id=tenant_id)
        OqiQualityRuleRepositoryImpl(setup_session).create(
            _completeness_rule(quality_condition_id=condition_id)
        )
        # Establish known lineage via a sibling field's real evidence --
        # the target field itself carries zero evidence rows at all
        # (an empty-row observation would NOT establish known lineage,
        # CDD-039 §12).
        sibling_field = _source_field(source_object_id=source_object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(setup_session).create(sibling_field)
        setup_session.flush()
        _admit_evidence(
            setup_session,
            source_field_id=sibling_field.source_field_id.value,
            source_record_reference="100047",
            observed_representation="Acme Ltd",
        )
        setup_session.commit()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="100047",
    )
    rule = _completeness_rule(quality_condition_id=condition_id)

    lock_held = threading.Event()
    results: dict[str, str] = {}

    def _worker_a(session: Session) -> None:
        service = _service(session, clock=lambda: NOW.replace(hour=1))
        evaluation = service.evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is not None
        results["a_outcome"] = evaluation.outcome.value
        lock_held.set()
        time.sleep(0.4)
        session.commit()

    def _worker_b(session: Session) -> None:
        assert lock_held.wait(timeout=5)
        service = _service(session, clock=lambda: NOW.replace(hour=2))
        evaluation = service.evaluate_current_state(rule=rule, subject=subject)
        assert evaluation is not None
        results["b_outcome"] = evaluation.outcome.value
        session.commit()

    session_a = factory()
    session_b = factory()
    thread_a = threading.Thread(target=_worker_a, args=(session_a,))
    thread_b = threading.Thread(target=_worker_b, args=(session_b,))
    thread_a.start()
    thread_b.start()

    # While B is blocked waiting for the lock, admit new qualifying
    # evidence via an independent, committed transaction.
    assert lock_held.wait(timeout=5)
    with factory() as evidence_session:
        _admit_evidence(
            evidence_session,
            source_field_id=source_field_id,
            source_record_reference="100047",
            observed_representation="Newly Admitted Value",
        )
        evidence_session.commit()

    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    assert results["a_outcome"] == "VIOLATED"  # A saw only the empty-row evidence
    assert (
        results["b_outcome"] == "SATISFIED"
    )  # B, evaluating after authority, saw the new evidence


def test_rollback_releases_authority_immediately(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as setup_session:
        source_object_id, source_field_id = _seed_field(setup_session, tenant_id=tenant_id)
        setup_session.commit()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="100048",
    )
    from app.domain.oqi.evaluation import canonical_subject_identity, finding_identity_material

    identity = finding_identity_material(
        tenant_id=subject.lineage.tenant_id,
        quality_condition_id="cond-rollback",
        subject_type=subject.subject_type,
        subject_identity=canonical_subject_identity(subject),
    )

    with factory() as session_a:
        repo = OqiQualityEvaluationRepositoryImpl(session_a)
        repo.acquire_evaluation_authority(identity)
        session_a.rollback()

    with factory() as session_b:
        repo = OqiQualityEvaluationRepositoryImpl(session_b)
        started = time.monotonic()
        repo.acquire_evaluation_authority(identity)
        elapsed = time.monotonic() - started
        session_b.rollback()
    assert elapsed < 2.0  # released immediately by A's rollback, not held


def test_different_tenants_do_not_block_each_other(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        tenant_a = f"tenant-a-{uuid4()}"
        tenant_b = f"tenant-b-{uuid4()}"
        object_a, field_a = _seed_field(setup_session, tenant_id=tenant_a)
        object_b, field_b = _seed_field(setup_session, tenant_id=tenant_b)
        OqiQualityRuleRepositoryImpl(setup_session).create(
            _completeness_rule(quality_condition_id=condition_id)
        )
        setup_session.commit()

    rule = _completeness_rule(quality_condition_id=condition_id)
    subject_a = _subject(
        tenant_id=tenant_a, source_object_id=object_a, source_field_id=field_a, reference="R"
    )
    subject_b = _subject(
        tenant_id=tenant_b, source_object_id=object_b, source_field_id=field_b, reference="R"
    )

    lock_held = threading.Event()
    durations: dict[str, float] = {}

    def _holder(session: Session) -> None:
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule, subject=subject_a)
        lock_held.set()
        time.sleep(0.5)
        session.commit()

    def _other_tenant(session: Session) -> None:
        assert lock_held.wait(timeout=5)
        started = time.monotonic()
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule, subject=subject_b)
        durations["b"] = time.monotonic() - started
        session.commit()

    session_a = factory()
    session_b = factory()
    thread_a = threading.Thread(target=_holder, args=(session_a,))
    thread_b = threading.Thread(target=_other_tenant, args=(session_b,))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    assert durations["b"] < 0.3  # did not wait for tenant A's held lock


def test_different_subjects_same_tenant_do_not_block_each_other(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        tenant_id = f"tenant-{uuid4()}"
        object_id, field_id = _seed_field(setup_session, tenant_id=tenant_id)
        OqiQualityRuleRepositoryImpl(setup_session).create(
            _completeness_rule(quality_condition_id=condition_id)
        )
        setup_session.commit()

    rule = _completeness_rule(quality_condition_id=condition_id)
    subject_a = _subject(
        tenant_id=tenant_id, source_object_id=object_id, source_field_id=field_id, reference="X"
    )
    subject_b = _subject(
        tenant_id=tenant_id, source_object_id=object_id, source_field_id=field_id, reference="Y"
    )

    lock_held = threading.Event()
    durations: dict[str, float] = {}

    def _holder(session: Session) -> None:
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule, subject=subject_a)
        lock_held.set()
        time.sleep(0.5)
        session.commit()

    def _other_subject(session: Session) -> None:
        assert lock_held.wait(timeout=5)
        started = time.monotonic()
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule, subject=subject_b)
        durations["b"] = time.monotonic() - started
        session.commit()

    session_a = factory()
    session_b = factory()
    thread_a = threading.Thread(target=_holder, args=(session_a,))
    thread_b = threading.Thread(target=_other_subject, args=(session_b,))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    assert durations["b"] < 0.3


def test_identical_evaluation_replayed_under_real_concurrency_does_not_double_mutate(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    with factory() as setup_session:
        source_object_id, source_field_id = _seed_field(setup_session, tenant_id=tenant_id)
        OqiQualityRuleRepositoryImpl(setup_session).create(
            _completeness_rule(quality_condition_id=condition_id)
        )
        # Known lineage via a sibling field's real evidence; the target
        # field itself stays empty -> MISSING_VALUE.
        sibling_field = _source_field(source_object_id=source_object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(setup_session).create(sibling_field)
        setup_session.flush()
        _admit_evidence(
            setup_session,
            source_field_id=sibling_field.source_field_id.value,
            source_record_reference="R1",
            observed_representation="Acme Ltd",
        )
        setup_session.commit()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="R1",
    )
    rule = _completeness_rule(quality_condition_id=condition_id)
    fixed_horizon = NOW.replace(hour=5)

    lock_held = threading.Event()

    def _first(session: Session) -> None:
        service = _service(session, clock=lambda: fixed_horizon)
        service.evaluate_current_state(rule=rule, subject=subject)
        lock_held.set()
        time.sleep(0.3)
        session.commit()

    def _second(session: Session) -> None:
        assert lock_held.wait(timeout=5)
        service = _service(session, clock=lambda: fixed_horizon)
        service.evaluate_current_state(rule=rule, subject=subject)
        session.commit()

    session_a = factory()
    session_b = factory()
    thread_a = threading.Thread(target=_first, args=(session_a,))
    thread_b = threading.Thread(target=_second, args=(session_b,))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    with factory() as verify_session:
        evaluations = (
            verify_session.execute(
                select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert len(evaluations) == 1  # identical evaluation_id -> one row
        findings = (
            verify_session.execute(
                select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert len(findings) == 1
        assert findings[0].state_revision == 1  # not double-incremented
        assert findings[0].occurrence_count == 1
