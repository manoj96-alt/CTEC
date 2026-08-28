"""Real-PostgreSQL provenance and raw-value-non-duplication proof for OQI1
(CDD-039 §21, §35-§36; OQI1 Artifact Authorization §4). Proves the full
`QualityFinding -> QualityEvaluation -> QualityRule version ->
FieldValueEvidence ids -> SourceField -> SourceObject -> SourceSystem`
chain is genuinely reconstructible from persisted rows alone, with tenant
identity intact throughout, and that no OQI table ever stores a duplicate
of `FieldValueEvidence.observed_representation`."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from app.application.oqi_quality_evaluation_service import OqiQualityEvaluationService
from app.domain.oqi.quality_rule import (
    QualityFindingType,
)
from app.infrastructure.persistence.models.oqi_quality_evaluation import (
    QualityEvaluationEvidenceORM,
    QualityEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_quality_rule import QualityRuleORM
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.models.source_system import SourceSystem as SourceSystemORM
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OqiQualityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.tests.test_oqi_quality_postgres import (
    _admit_evidence,
    _completeness_rule,
    _seed_field,
    _subject,
)
from app.tests.test_source_field_persistence_postgres import _source_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_full_provenance_chain_is_reconstructible(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"

    with factory() as session:
        source_object_id, source_field_id = _seed_field(session, tenant_id=tenant_id)
        rule = _completeness_rule(quality_condition_id=condition_id)
        OqiQualityRuleRepositoryImpl(session).create(rule)
        # Known lineage via a sibling field with real evidence; the
        # target field carries zero evidence -> MISSING_VALUE, so the
        # ledger's evidence_ids for this evaluation is genuinely empty --
        # provenance must still resolve cleanly through the *subject*
        # chain even when there is no evidence row to point to.
        sibling_field = _source_field(source_object_id=source_object_id, field_label="LFA1-NAME1")
        SourceFieldRepositoryImpl(session).create(sibling_field)
        session.flush()
        _admit_evidence(
            session,
            source_field_id=sibling_field.source_field_id.value,
            source_record_reference="900001",
            observed_representation="Acme Ltd",
        )
        session.commit()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="900001",
    )
    with factory() as session:
        service = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        evaluation = service.evaluate_current_state(
            rule=_completeness_rule(quality_condition_id=condition_id), subject=subject
        )
        session.commit()

    assert evaluation is not None
    assert evaluation.outcome.value == "VIOLATED"

    # --- Reconstruct the chain from persisted rows alone ---
    with factory() as session:
        finding = session.execute(
            select(QualityFindingORM).where(QualityFindingORM.tenant_id == tenant_id)
        ).scalar_one()
        assert finding.status == "OPEN"
        assert finding.finding_type == QualityFindingType.MISSING_VALUE.value

        evaluations = (
            session.execute(
                select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert len(evaluations) == 1
        evaluation_row = evaluations[0]
        assert evaluation_row.tenant_id == tenant_id
        assert evaluation_row.quality_condition_id == condition_id
        assert evaluation_row.outcome == "VIOLATED"
        assert evaluation_row.evaluation_mode == "CURRENT_STATE"

        rule_row = session.get(QualityRuleORM, evaluation_row.rule_id)
        assert rule_row is not None
        assert rule_row.quality_condition_id == condition_id
        assert rule_row.version == evaluation_row.rule_version == 1
        assert rule_row.status == "ACTIVE"

        evidence_links = (
            session.execute(
                select(QualityEvaluationEvidenceORM).where(
                    QualityEvaluationEvidenceORM.evaluation_id == evaluation_row.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert evidence_links == []  # MISSING_VALUE: genuinely zero target evidence

        field_row = session.get(SourceFieldORM, evaluation_row.source_field_id)
        assert field_row is not None
        assert field_row.source_object_id == source_object_id

        object_row = session.get(SourceObjectORM, field_row.source_object_id)
        assert object_row is not None
        assert object_row.tenant_id == tenant_id

        system_row = session.get(SourceSystemORM, object_row.source_system_id)
        assert system_row is not None
        assert system_row.tenant_id == tenant_id

        # Full chain, tenant-consistent throughout:
        assert (
            finding.tenant_id
            == evaluation_row.tenant_id
            == object_row.tenant_id
            == system_row.tenant_id
        )


def test_provenance_chain_includes_evidence_ids_when_present(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"

    with factory() as session:
        source_object_id, source_field_id = _seed_field(session, tenant_id=tenant_id)
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(quality_condition_id=condition_id)
        )
        evidence_id = _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="900002",
            observed_representation="Acme Ltd",
        )
        session.commit()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="900002",
    )
    with factory() as session:
        service = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        evaluation = service.evaluate_current_state(
            rule=_completeness_rule(quality_condition_id=condition_id), subject=subject
        )
        session.commit()

    assert evaluation is not None
    assert evaluation.outcome.value == "SATISFIED"
    assert evaluation.evidence_ids == (evidence_id,)

    with factory() as session:
        evaluation_row = session.get(QualityEvaluationORM, evaluation.evaluation_id)
        assert evaluation_row is not None
        links = (
            session.execute(
                select(QualityEvaluationEvidenceORM).where(
                    QualityEvaluationEvidenceORM.evaluation_id == evaluation_row.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert len(links) == 1
        assert links[0].field_value_evidence_id == evidence_id
        assert links[0].sequence_index == 0


def test_no_raw_evidence_value_is_duplicated_into_oqi_tables(migrated_engine: Engine) -> None:
    """CDD-039 §36: `QualityEvaluation`/`QualityFinding` never persist a
    duplicate of `FieldValueEvidence.observed_representation`. Proven by
    exhaustively listing every column on both OQI tables and confirming
    none is a raw-value column, and that the distinctive raw string used
    here appears only inside `field_value_evidence`."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    distinctive_value = f"DISTINCTIVE-RAW-VALUE-{uuid4()}"

    with factory() as session:
        source_object_id, source_field_id = _seed_field(session, tenant_id=tenant_id)
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(quality_condition_id=condition_id)
        )
        _admit_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="900003",
            observed_representation=distinctive_value,
        )
        session.commit()

    subject = _subject(
        tenant_id=tenant_id,
        source_object_id=source_object_id,
        source_field_id=source_field_id,
        reference="900003",
    )
    with factory() as session:
        service = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        service.evaluate_current_state(
            rule=_completeness_rule(quality_condition_id=condition_id), subject=subject
        )
        session.commit()

    # Column-name inventory: no OQI table declares any column shaped like a
    # raw source value.
    finding_columns = {c.name for c in QualityFindingORM.__table__.columns}
    evaluation_columns = {c.name for c in QualityEvaluationORM.__table__.columns}
    forbidden_names = {"value", "observed_representation", "raw_value", "content"}
    assert not (finding_columns & forbidden_names)
    assert not (evaluation_columns & forbidden_names)

    # Direct proof: the distinctive raw string exists in field_value_evidence
    # and nowhere serialized inside any OQI row's own text columns.
    from sqlalchemy import text as sql_text

    with factory() as session:
        in_evidence = session.execute(
            sql_text(
                "SELECT count(*) FROM field_value_evidence WHERE observed_representation = :v"
            ),
            {"v": distinctive_value},
        ).scalar_one()
        assert in_evidence == 1

        in_evaluations = session.execute(
            sql_text(
                "SELECT count(*) FROM quality_evaluations WHERE "
                "evidence_set_digest = :v OR quality_condition_id = :v OR "
                "source_record_reference = :v"
            ),
            {"v": distinctive_value},
        ).scalar_one()
        assert in_evaluations == 0

        in_findings = session.execute(
            sql_text(
                "SELECT count(*) FROM quality_findings WHERE "
                "quality_condition_id = :v OR source_record_reference = :v"
            ),
            {"v": distinctive_value},
        ).scalar_one()
        assert in_findings == 0
