"""Real-PostgreSQL acceptance evidence for OQI2 (CDD-040 §46-§52; Artifact
Authorization §8). Proves what a fake repository cannot: migration schema
correctness; the chained composite-FK provenance-integrity design (CDD-040
§49) genuinely rejects mismatched participant/evidence associations at the
database level; the partial unique "one ACTIVE correspondence per subject"
invariant holds; and the `pg_advisory_xact_lock` mechanism genuinely
serializes concurrent cross-source evaluations, including the critical
evidence-arrives-while-waiting case."""

# isort: skip_file
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_cross_source_evaluation_service import OqiCrossSourceEvaluationService
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceMember,
    ComparisonSubjectCorrespondenceStatus,
)
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.oqi_cross_source_correspondence import (
    ComparisonSubjectCorrespondenceORM,
)
from app.infrastructure.persistence.models.oqi_cross_source_evaluation import (
    QualityComparisonEvaluationEvidenceORM,
    QualityComparisonEvaluationObservationORM,
    QualityComparisonEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.oqi_cross_source_correspondence_repository import (
    OqiCrossSourceCorrespondenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_cross_source_evaluation_repository import (
    OqiCrossSourceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.tests.test_source_field_persistence_postgres import _seed_source_object, _source_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _seed_field(session: Session, *, tenant_id: str, field_label: str) -> tuple[UUID, UUID]:
    object_id = _seed_source_object(session, tenant_id=tenant_id)
    field = _source_field(source_object_id=object_id, field_label=field_label)
    SourceFieldRepositoryImpl(session).create(field)
    session.flush()
    return object_id, field.source_field_id.value


def _admit_evidence(
    session: Session, *, source_field_id: UUID, source_record_reference: str, value: str = "ABC123"
) -> UUID:
    evidence = FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference=source_record_reference,
        observed_representation=value,
        observed_at=NOW,
        received_at=NOW,
    )
    FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(evidence)
    return evidence.field_value_evidence_id.value


def _rule(*, condition_id: str, sap_field: UUID, plm_field: UUID) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=condition_id,
        version=1,
        dimension=QualityDimension.CONSISTENCY,
        finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
        validity_primitive=None,
        information_element_requirement_id="ier-mpn",
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
                    "authoritative": True,
                },
            ]
        },
        status=QualityRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )


def _correspondence(
    *, tenant_id: str, subject_id: UUID, sap_object: UUID, plm_object: UUID
) -> ComparisonSubjectCorrespondence:
    return ComparisonSubjectCorrespondence.new(
        comparison_subject_id=subject_id,
        tenant_id=tenant_id,
        version=1,
        status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
        members=(
            ComparisonSubjectCorrespondenceMember(
                participant_role="SAP",
                source_object_id=sap_object,
                source_record_reference="MAT-100",
            ),
            ComparisonSubjectCorrespondenceMember(
                participant_role="PLM", source_object_id=plm_object, source_record_reference="P-442"
            ),
        ),
        created_by="steward",
        created_on=NOW,
    )


def _service(
    session: Session, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
) -> OqiCrossSourceEvaluationService:
    return OqiCrossSourceEvaluationService(
        evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session), clock=clock
    )


def _rule_n(*, condition_id: str, fields: dict[str, UUID]) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=condition_id,
        version=1,
        dimension=QualityDimension.CONSISTENCY,
        finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
        validity_primitive=None,
        information_element_requirement_id="ier-mpn",
        rule_parameters={
            "participants": [
                {
                    "role": role,
                    "source_field_id": str(field_id),
                    "eligible": True,
                    "expected": True,
                    "authoritative": False,
                }
                for role, field_id in fields.items()
            ]
        },
        status=QualityRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )


def _correspondence_n(
    *, tenant_id: str, subject_id: UUID, objects: dict[str, UUID]
) -> ComparisonSubjectCorrespondence:
    return ComparisonSubjectCorrespondence.new(
        comparison_subject_id=subject_id,
        tenant_id=tenant_id,
        version=1,
        status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
        members=tuple(
            ComparisonSubjectCorrespondenceMember(
                participant_role=role,
                source_object_id=object_id,
                source_record_reference=f"REF-{role}",
            )
            for role, object_id in objects.items()
        ),
        created_by="steward",
        created_on=NOW,
    )


# --- schema ---


def test_migration_creates_expected_schema(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    tables = set(inspector.get_table_names())
    assert {
        "comparison_subject_correspondences",
        "comparison_subject_correspondence_members",
        "quality_comparison_evaluations",
        "quality_comparison_evaluation_participants",
        "quality_comparison_evaluation_evidence",
        "quality_comparison_findings",
        "quality_comparison_evaluation_observations",
    } <= tables

    evidence_unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("field_value_evidence")
    }
    assert "uq_field_value_evidence_id_source_field" in evidence_unique_constraints

    finding_columns = {c["name"] for c in inspector.get_columns("quality_comparison_findings")}
    assert "finding_type" not in finding_columns

    observation_columns = {
        c["name"] for c in inspector.get_columns("quality_comparison_evaluation_observations")
    }
    assert observation_columns == {"evaluation_id", "observation_type", "participant_role"}


def test_migration_round_trips_cleanly(migrated_engine: Engine) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(migrated_engine.url))
    alembic.command.downgrade(alembic_cfg, "0020_oqi1_quality_foundation")
    with migrated_engine.connect():
        tables = set(inspect(migrated_engine).get_table_names())
        assert "comparison_subject_correspondences" not in tables
    alembic.command.upgrade(alembic_cfg, "0022_oqi3_business_rule")
    with migrated_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "0022_oqi3_business_rule"


# --- database constraints ---


def test_one_active_correspondence_per_subject_enforced_by_database(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    subject_id = uuid4()
    with factory() as session:
        sap_object, _ = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-MFRPN")
        plm_object, _ = _seed_field(session, tenant_id=tenant_id, field_label="PART-MPN")
        session.commit()

    with factory() as session:
        repo = OqiCrossSourceCorrespondenceRepositoryImpl(session)
        repo.create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.commit()

    with factory() as session:
        second = ComparisonSubjectCorrespondence.new(
            comparison_subject_id=subject_id,
            tenant_id=tenant_id,
            version=2,
            status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
            members=(
                ComparisonSubjectCorrespondenceMember(
                    participant_role="SAP",
                    source_object_id=sap_object,
                    source_record_reference="MAT-100",
                ),
                ComparisonSubjectCorrespondenceMember(
                    participant_role="PLM",
                    source_object_id=plm_object,
                    source_record_reference="P-442",
                ),
            ),
            created_by="steward",
            created_on=NOW,
        )
        session.add(
            ComparisonSubjectCorrespondenceORM(
                correspondence_id=second.correspondence_id,
                comparison_subject_id=second.comparison_subject_id,
                tenant_id=second.tenant_id,
                version=second.version,
                status="ACTIVE",
                created_by="steward",
                created_on=NOW,
                retired_on=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_evidence_association_rejects_evidence_from_a_different_source_field(
    migrated_engine: Engine,
) -> None:
    """CDD-040 §49: the chained composite FK rejects an evidence-
    association row whose evidence genuinely belongs to a different
    source_field_id than the one it claims -- the core provenance-
    integrity guarantee, proven directly against real Postgres."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    with factory() as session:
        sap_object, sap_field = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-MFRPN")
        plm_object, plm_field = _seed_field(session, tenant_id=tenant_id, field_label="PART-MPN")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule(condition_id=condition_id, sap_field=sap_field, plm_field=plm_field)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.commit()

    with factory() as session:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        _admit_evidence(session, source_field_id=sap_field, source_record_reference="MAT-100")
        # PLM evidence belongs to a genuinely different source_field_id.
        plm_evidence_id = _admit_evidence(
            session, source_field_id=plm_field, source_record_reference="P-442"
        )
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule, correspondence=correspondence)
        session.commit()

    # Now attempt to forge a participant-evidence row claiming SAP's
    # evidence actually belongs to a field it does not.
    with factory() as session:
        forged_field_id = uuid4()
        evaluation = session.execute(select(QualityComparisonEvaluationORM)).scalars().first()
        assert evaluation is not None
        session.add(
            QualityComparisonEvaluationEvidenceORM(
                evaluation_id=evaluation.evaluation_id,
                participant_role="PLM",
                source_field_id=forged_field_id,  # does not match plm_evidence_id's true field
                field_value_evidence_id=plm_evidence_id,
                sequence_index=99,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_evidence_association_rejects_role_not_matching_participant_snapshot(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    with factory() as session:
        sap_object, sap_field = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-MFRPN")
        plm_object, plm_field = _seed_field(session, tenant_id=tenant_id, field_label="PART-MPN")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule(condition_id=condition_id, sap_field=sap_field, plm_field=plm_field)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.commit()

    with factory() as session:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        sap_evidence_id = _admit_evidence(
            session, source_field_id=sap_field, source_record_reference="MAT-100"
        )
        _admit_evidence(session, source_field_id=plm_field, source_record_reference="P-442")
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule, correspondence=correspondence)
        session.commit()

    with factory() as session:
        evaluation = session.execute(select(QualityComparisonEvaluationORM)).scalars().first()
        assert evaluation is not None
        # "Nonexistent" role that has no matching participant snapshot row.
        session.add(
            QualityComparisonEvaluationEvidenceORM(
                evaluation_id=evaluation.evaluation_id,
                participant_role="Portal",
                source_field_id=sap_field,
                field_value_evidence_id=sap_evidence_id,
                sequence_index=99,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


# --- concurrency ---


def test_concurrent_first_evaluation_serializes_to_one_finding(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    with factory() as session:
        sap_object, sap_field = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-MFRPN")
        plm_object, plm_field = _seed_field(session, tenant_id=tenant_id, field_label="PART-MPN")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule(condition_id=condition_id, sap_field=sap_field, plm_field=plm_field)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        _admit_evidence(
            session, source_field_id=sap_field, source_record_reference="MAT-100", value="X"
        )
        # PLM left with zero evidence -> deterministic MISSING outcome for both workers.
        session.commit()

    lock_held = threading.Event()
    outcomes: dict[str, str] = {}
    horizons = {"a": NOW, "b": NOW.replace(microsecond=1)}

    def _first(session: Session, label: str) -> None:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        service = _service(session, clock=lambda: horizons[label])
        service.evaluate_current_state(rule=rule, correspondence=correspondence)
        lock_held.set()
        time.sleep(0.3)
        session.commit()
        outcomes[label] = "done"

    def _second(session: Session, label: str) -> None:
        assert lock_held.wait(timeout=5)
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        service = _service(session, clock=lambda: horizons[label])
        service.evaluate_current_state(rule=rule, correspondence=correspondence)
        session.commit()
        outcomes[label] = "done"

    session_a, session_b = factory(), factory()
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
                select(QualityComparisonFindingORM).where(
                    QualityComparisonFindingORM.tenant_id == tenant_id
                )
            )
            .scalars()
            .all()
        )
        assert len(findings) == 1
        assert findings[0].status == "OPEN"
        assert findings[0].state_revision == 2

        evaluations = (
            verify_session.execute(
                select(QualityComparisonEvaluationORM).where(
                    QualityComparisonEvaluationORM.tenant_id == tenant_id
                )
            )
            .scalars()
            .all()
        )
        assert len(evaluations) == 2


def test_evidence_arrival_while_second_worker_waits(migrated_engine: Engine) -> None:
    """The core OQI1 concurrency proof, extended to cross-source: PLM's
    evidence admitted while worker B waits for the lock is genuinely seen
    by B (selected after authority), never by A."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    with factory() as session:
        sap_object, sap_field = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-MFRPN")
        plm_object, plm_field = _seed_field(session, tenant_id=tenant_id, field_label="PART-MPN")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule(condition_id=condition_id, sap_field=sap_field, plm_field=plm_field)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        _admit_evidence(
            session, source_field_id=sap_field, source_record_reference="MAT-100", value="ABC"
        )
        session.commit()

    lock_held = threading.Event()
    results: dict[str, str] = {}

    def _worker_a(session: Session) -> None:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        service = _service(session, clock=lambda: NOW.replace(hour=1))
        evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)
        assert evaluation is not None
        results["a_outcome"] = evaluation.outcome.value
        lock_held.set()
        time.sleep(0.4)
        session.commit()

    def _worker_b(session: Session) -> None:
        assert lock_held.wait(timeout=5)
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        service = _service(session, clock=lambda: NOW.replace(hour=2))
        evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)
        assert evaluation is not None
        results["b_outcome"] = evaluation.outcome.value
        session.commit()

    session_a, session_b = factory(), factory()
    thread_a = threading.Thread(target=_worker_a, args=(session_a,))
    thread_b = threading.Thread(target=_worker_b, args=(session_b,))
    thread_a.start()
    thread_b.start()

    assert lock_held.wait(timeout=5)
    with factory() as evidence_session:
        _admit_evidence(
            evidence_session,
            source_field_id=plm_field,
            source_record_reference="P-442",
            value="ABC",
        )
        evidence_session.commit()

    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    # A: PLM had zero evidence yet -> MISSING/VIOLATED.
    assert results["a_outcome"] == "VIOLATED"
    # B: evaluating after authority, saw PLM's newly admitted agreeing value.
    assert results["b_outcome"] == "SATISFIED"


def test_rollback_releases_authority_immediately(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    from app.domain.oqi_cross_source.evaluation import finding_identity_material

    identity = finding_identity_material(
        tenant_id=f"tenant-{uuid4()}",
        quality_condition_id="cond-rollback",
        comparison_subject_id=uuid4(),
    )

    with factory() as session_a:
        repo = OqiCrossSourceEvaluationRepositoryImpl(session_a)
        repo.acquire_evaluation_authority(identity)
        session_a.rollback()

    with factory() as session_b:
        repo = OqiCrossSourceEvaluationRepositoryImpl(session_b)
        started = time.monotonic()
        repo.acquire_evaluation_authority(identity)
        elapsed = time.monotonic() - started
        session_b.rollback()
    assert elapsed < 2.0


def test_different_tenants_do_not_block_each_other(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    tenant_a, tenant_b = f"tenant-a-{uuid4()}", f"tenant-b-{uuid4()}"
    with factory() as session:
        sap_object_a, sap_field_a = _seed_field(session, tenant_id=tenant_a, field_label="F1")
        plm_object_a, plm_field_a = _seed_field(session, tenant_id=tenant_a, field_label="F2")
        sap_object_b, sap_field_b = _seed_field(session, tenant_id=tenant_b, field_label="F1")
        plm_object_b, plm_field_b = _seed_field(session, tenant_id=tenant_b, field_label="F2")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule(condition_id=condition_id, sap_field=sap_field_a, plm_field=plm_field_a)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_a,
                subject_id=subject_id,
                sap_object=sap_object_a,
                plm_object=plm_object_a,
            )
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_b,
                subject_id=subject_id,
                sap_object=sap_object_b,
                plm_object=plm_object_b,
            )
        )
        session.commit()

    rule_a = _rule(condition_id=condition_id, sap_field=sap_field_a, plm_field=plm_field_a)
    lock_held = threading.Event()
    durations: dict[str, float] = {}

    def _holder(session: Session) -> None:
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_a, comparison_subject_id=subject_id
        )
        assert correspondence is not None
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule_a, correspondence=correspondence)
        lock_held.set()
        time.sleep(0.5)
        session.commit()

    def _other_tenant(session: Session) -> None:
        assert lock_held.wait(timeout=5)
        rule_b = _rule(condition_id=condition_id, sap_field=sap_field_b, plm_field=plm_field_b)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_b, comparison_subject_id=subject_id
        )
        assert correspondence is not None
        started = time.monotonic()
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule_b, correspondence=correspondence)
        durations["b"] = time.monotonic() - started
        session.commit()

    session_a, session_b = factory(), factory()
    thread_a = threading.Thread(target=_holder, args=(session_a,))
    thread_b = threading.Thread(target=_other_tenant, args=(session_b,))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    assert durations["b"] < 0.3


# --- N-Source Finding Representation Amendment: observation persistence
# (Artifact Authorization Amendment §15-§17) ---


def test_observation_concurrency_five_source_frontier_seen_after_lock(
    migrated_engine: Engine,
) -> None:
    """AA §15: worker B waits for Finding authority on a 5-participant
    evaluation; while waiting, evidence is committed for multiple
    participants. After authority is acquired, B's observations must
    reflect the single coherent post-lock frontier."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    roles = ["A", "B", "C", "D", "E"]

    with factory() as session:
        objects: dict[str, UUID] = {}
        fields: dict[str, UUID] = {}
        for role in roles:
            obj, field = _seed_field(session, tenant_id=tenant_id, field_label=f"F-{role}")
            objects[role] = obj
            fields[role] = field
        OqiQualityRuleRepositoryImpl(session).create(
            _rule_n(condition_id=condition_id, fields=fields)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence_n(tenant_id=tenant_id, subject_id=subject_id, objects=objects)
        )
        # A, B, C agree; D and E left with zero evidence -> both missing.
        for role in ("A", "B", "C"):
            _admit_evidence(
                session, source_field_id=fields[role], source_record_reference=f"REF-{role}"
            )
        session.commit()

    lock_held = threading.Event()
    results: dict[str, tuple[str, ...]] = {}

    def _worker_a(session: Session) -> None:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        service = _service(session, clock=lambda: NOW.replace(hour=1))
        evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)
        assert evaluation is not None
        results["a"] = tuple(sorted(o.participant_role for o in evaluation.observations))
        lock_held.set()
        time.sleep(0.4)
        session.commit()

    def _worker_b(session: Session) -> None:
        assert lock_held.wait(timeout=5)
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        service = _service(session, clock=lambda: NOW.replace(hour=2))
        evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)
        assert evaluation is not None
        results["b"] = tuple(sorted(o.participant_role for o in evaluation.observations))
        session.commit()

    session_a, session_b = factory(), factory()
    thread_a = threading.Thread(target=_worker_a, args=(session_a,))
    thread_b = threading.Thread(target=_worker_b, args=(session_b,))
    thread_a.start()
    thread_b.start()

    assert lock_held.wait(timeout=5)
    with factory() as evidence_session:
        # D admitted (agreeing) while B waits; E remains missing throughout.
        _admit_evidence(
            evidence_session, source_field_id=fields["D"], source_record_reference="REF-D"
        )
        evidence_session.commit()

    thread_a.join(timeout=10)
    thread_b.join(timeout=10)
    session_a.close()
    session_b.close()

    # A: D and E both had zero evidence yet -> both missing.
    assert results["a"] == ("D", "E")
    # B: evaluating after authority, saw D's newly admitted value -> only E missing.
    assert results["b"] == ("E",)


def test_observation_idempotent_replay_no_duplicate_rows(migrated_engine: Engine) -> None:
    """AA §16: identical Evaluation replay must not duplicate observation
    rows -- the natural key (evaluation_id, observation_type,
    participant_role) makes this deterministic by construction, proven on
    real Postgres."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    with factory() as session:
        sap_object, sap_field = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-MFRPN")
        plm_object, plm_field = _seed_field(session, tenant_id=tenant_id, field_label="PART-MPN")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule(condition_id=condition_id, sap_field=sap_field, plm_field=plm_field)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        _admit_evidence(session, source_field_id=sap_field, source_record_reference="MAT-100")
        # PLM left with zero evidence -> deterministic MISSING outcome.
        session.commit()

    fixed_horizon = NOW

    with factory() as session:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        service = _service(session, clock=lambda: fixed_horizon)
        first = service.evaluate_current_state(rule=rule, correspondence=correspondence)
        assert first is not None
        session.commit()

    with factory() as session:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        service = _service(session, clock=lambda: fixed_horizon)
        second = service.evaluate_current_state(rule=rule, correspondence=correspondence)
        assert second is not None
        assert first.evaluation_id == second.evaluation_id
        session.commit()

    with factory() as session:
        rows = (
            session.execute(
                select(QualityComparisonEvaluationObservationORM).where(
                    QualityComparisonEvaluationObservationORM.evaluation_id == first.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].observation_type == "CROSS_SOURCE_PARTICIPANT_VALUE_MISSING"
        assert rows[0].participant_role == "PLM"


def test_observation_rejects_participant_role_not_in_evaluation_snapshot(
    migrated_engine: Engine,
) -> None:
    """AA §17: an observation row whose `participant_role` has no matching
    row in that evaluation's own participant snapshot must be rejected by
    the composite FK (IntegrityError)."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    with factory() as session:
        sap_object, sap_field = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-MFRPN")
        plm_object, plm_field = _seed_field(session, tenant_id=tenant_id, field_label="PART-MPN")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule(condition_id=condition_id, sap_field=sap_field, plm_field=plm_field)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.commit()

    with factory() as session:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        _admit_evidence(session, source_field_id=sap_field, source_record_reference="MAT-100")
        _admit_evidence(session, source_field_id=plm_field, source_record_reference="P-442")
        service = _service(session, clock=lambda: NOW)
        service.evaluate_current_state(rule=rule, correspondence=correspondence)
        session.commit()

    with factory() as session:
        evaluation = session.execute(select(QualityComparisonEvaluationORM)).scalars().first()
        assert evaluation is not None
        # Attack A: "Portal" has no matching participant snapshot row for
        # this evaluation at all.
        session.add(
            QualityComparisonEvaluationObservationORM(
                evaluation_id=evaluation.evaluation_id,
                observation_type="CROSS_SOURCE_VALUE_CONFLICT",
                participant_role="Portal",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_observation_rejects_role_from_a_different_evaluation(migrated_engine: Engine) -> None:
    """Attack B: a role that IS a valid participant of a different
    evaluation (E2) but not of the evaluation the observation claims (E1)
    must still be rejected -- the composite FK is scoped per-evaluation.
    E1 and E2 deliberately use disjoint role sets ("SAP"/"MES" vs.
    "SAP"/"PLM") so "PLM" is genuinely absent from E1's own snapshot."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id_1, condition_id_2 = f"cond-{uuid4()}", f"cond-{uuid4()}"
    subject_id_1, subject_id_2 = uuid4(), uuid4()
    with factory() as session:
        sap_object_1, sap_field_1 = _seed_field(session, tenant_id=tenant_id, field_label="F1")
        mes_object_1, mes_field_1 = _seed_field(session, tenant_id=tenant_id, field_label="F2")
        sap_object_2, sap_field_2 = _seed_field(session, tenant_id=tenant_id, field_label="F3")
        plm_object_2, plm_field_2 = _seed_field(session, tenant_id=tenant_id, field_label="F4")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule_n(condition_id=condition_id_1, fields={"SAP": sap_field_1, "MES": mes_field_1})
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _rule_n(condition_id=condition_id_2, fields={"SAP": sap_field_2, "PLM": plm_field_2})
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence_n(
                tenant_id=tenant_id,
                subject_id=subject_id_1,
                objects={"SAP": sap_object_1, "MES": mes_object_1},
            )
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence_n(
                tenant_id=tenant_id,
                subject_id=subject_id_2,
                objects={"SAP": sap_object_2, "PLM": plm_object_2},
            )
        )
        session.commit()

    with factory() as session:
        rule_1 = OqiQualityRuleRepositoryImpl(session).get_active(condition_id_1)
        correspondence_1 = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id_1
        )
        rule_2 = OqiQualityRuleRepositoryImpl(session).get_active(condition_id_2)
        correspondence_2 = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id_2
        )
        assert rule_1 is not None and correspondence_1 is not None
        assert rule_2 is not None and correspondence_2 is not None
        # E1: SAP has evidence, MES missing -> VIOLATED/MISSING, persisted.
        _admit_evidence(session, source_field_id=sap_field_1, source_record_reference="REF-SAP")
        # E2: SAP has evidence, PLM missing -> VIOLATED/MISSING, persisted.
        _admit_evidence(session, source_field_id=sap_field_2, source_record_reference="REF-SAP")
        service = _service(session, clock=lambda: NOW)
        evaluation_1 = service.evaluate_current_state(rule=rule_1, correspondence=correspondence_1)
        evaluation_2 = service.evaluate_current_state(rule=rule_2, correspondence=correspondence_2)
        assert evaluation_1 is not None and evaluation_2 is not None
        session.commit()
        e1_id = evaluation_1.evaluation_id

    with factory() as session:
        # "PLM" IS a genuine participant role of E2 but E1 has no PLM
        # participant snapshot row at all -- must be rejected.
        session.add(
            QualityComparisonEvaluationObservationORM(
                evaluation_id=e1_id,
                observation_type="CROSS_SOURCE_PARTICIPANT_VALUE_MISSING",
                participant_role="PLM",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_observation_valid_row_succeeds(migrated_engine: Engine) -> None:
    """Attack C: a genuinely valid observation (matching evaluation_id +
    participant_role of that evaluation's own snapshot) succeeds."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()
    with factory() as session:
        sap_object, sap_field = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-MFRPN")
        plm_object, plm_field = _seed_field(session, tenant_id=tenant_id, field_label="PART-MPN")
        OqiQualityRuleRepositoryImpl(session).create(
            _rule(condition_id=condition_id, sap_field=sap_field, plm_field=plm_field)
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            _correspondence(
                tenant_id=tenant_id,
                subject_id=subject_id,
                sap_object=sap_object,
                plm_object=plm_object,
            )
        )
        session.commit()

    with factory() as session:
        rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert rule is not None and correspondence is not None
        _admit_evidence(session, source_field_id=sap_field, source_record_reference="MAT-100")
        # PLM missing -> the service itself already inserts a valid
        # MISSING/PLM observation row; this proves it round-trips cleanly.
        service = _service(session, clock=lambda: NOW)
        evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)
        assert evaluation is not None
        session.commit()
        evaluation_id = evaluation.evaluation_id

    with factory() as session:
        rows = (
            session.execute(
                select(QualityComparisonEvaluationObservationORM).where(
                    QualityComparisonEvaluationObservationORM.evaluation_id == evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].participant_role == "PLM"
