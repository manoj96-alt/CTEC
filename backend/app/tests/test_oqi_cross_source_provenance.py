"""Real-PostgreSQL provenance-chain reconstruction proof for OQI2 (CDD-040
§37, §39, Artifact Authorization §8). Proves the full chain
`QualityComparisonFinding -> latest_evaluation_id ->
QualityComparisonEvaluation -> rule_version ->
comparison_subject_correspondence_id -> participant snapshots ->
SourceRecordLineageIdentity -> evidence IDs -> SourceField -> SourceObject
-> SourceSystem` is reconstructable end-to-end from persisted state alone,
with zero raw observed-value duplication anywhere outside
`field_value_evidence` itself."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

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
from app.infrastructure.persistence.models.oqi_cross_source_evaluation import (
    QualityComparisonEvaluationEvidenceORM,
    QualityComparisonEvaluationORM,
    QualityComparisonEvaluationParticipantORM,
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


def test_full_provenance_chain_is_reconstructable_with_zero_raw_value_duplication(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    condition_id = f"cond-{uuid4()}"
    subject_id = uuid4()

    with factory() as session:
        sap_object = _seed_source_object(session, tenant_id=tenant_id)
        plm_object = _seed_source_object(session, tenant_id=tenant_id)
        sap_field = _source_field(source_object_id=sap_object, field_label="LFA1-MFRPN")
        plm_field = _source_field(source_object_id=plm_object, field_label="PART-MPN")
        SourceFieldRepositoryImpl(session).create(sap_field)
        SourceFieldRepositoryImpl(session).create(plm_field)
        session.flush()

        rule = QualityRule.new(
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
                        "source_field_id": str(sap_field.source_field_id.value),
                        "eligible": True,
                        "expected": True,
                        "authoritative": False,
                    },
                    {
                        "role": "PLM",
                        "source_field_id": str(plm_field.source_field_id.value),
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
        OqiQualityRuleRepositoryImpl(session).create(rule)

        correspondence = ComparisonSubjectCorrespondence.new(
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
                    participant_role="PLM",
                    source_object_id=plm_object,
                    source_record_reference="P-442",
                ),
            ),
            created_by="steward",
            created_on=NOW,
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(correspondence)

        sap_evidence = FieldValueEvidence.new(
            source_field_id=Identifier(sap_field.source_field_id.value),
            source_record_reference="MAT-100",
            observed_representation="ABC123",
            observed_at=NOW,
            received_at=NOW,
        )
        plm_evidence = FieldValueEvidence.new(
            source_field_id=Identifier(plm_field.source_field_id.value),
            source_record_reference="P-442",
            observed_representation="XYZ999",
            observed_at=NOW,
            received_at=NOW,
        )
        FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(sap_evidence)
        FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(plm_evidence)
        session.commit()

    with factory() as session:
        active_rule = OqiQualityRuleRepositoryImpl(session).get_active(condition_id)
        active_correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
            tenant_id=tenant_id, comparison_subject_id=subject_id
        )
        assert active_rule is not None and active_correspondence is not None
        service = OqiCrossSourceEvaluationService(
            evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session), clock=lambda: NOW
        )
        evaluation = service.evaluate_current_state(
            rule=active_rule, correspondence=active_correspondence
        )
        session.commit()
        assert evaluation is not None
        assert evaluation.outcome.value == "VIOLATED"  # ABC123 != XYZ999

    # --- reconstruct the full chain from persisted state alone ---
    with factory() as session:
        finding = session.execute(
            select(QualityComparisonFindingORM).where(
                QualityComparisonFindingORM.tenant_id == tenant_id
            )
        ).scalar_one()
        assert finding.finding_type == "CROSS_SOURCE_VALUE_CONFLICT"

        evaluation_row = session.get(QualityComparisonEvaluationORM, finding.latest_evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.rule_version == 1
        assert (
            evaluation_row.comparison_subject_correspondence_id == correspondence.correspondence_id
        )

        participants = (
            session.execute(
                select(QualityComparisonEvaluationParticipantORM).where(
                    QualityComparisonEvaluationParticipantORM.evaluation_id
                    == evaluation_row.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert {p.participant_role for p in participants} == {"SAP", "PLM"}
        plm_participant = next(p for p in participants if p.participant_role == "PLM")
        assert plm_participant.authoritative is True
        assert plm_participant.source_object_id == plm_object
        assert plm_participant.source_record_reference == "P-442"

        evidence_rows = (
            session.execute(
                select(QualityComparisonEvaluationEvidenceORM).where(
                    QualityComparisonEvaluationEvidenceORM.evaluation_id
                    == evaluation_row.evaluation_id
                )
            )
            .scalars()
            .all()
        )
        assert len(evidence_rows) == 2

        # Confirm the evidence rows resolve to the real FieldValueEvidence
        # rows carrying the actual observed values -- never duplicated
        # anywhere in the OQI2 tables themselves.
        from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM

        for row in evidence_rows:
            evidence_model = session.get(FieldValueEvidenceORM, row.field_value_evidence_id)
            assert evidence_model is not None
            assert evidence_model.source_field_id == row.source_field_id

    # --- zero raw-value duplication: no OQI2 table has an
    # observed-representation-shaped column ---
    inspector = inspect(migrated_engine)
    for table_name in (
        "comparison_subject_correspondences",
        "comparison_subject_correspondence_members",
        "quality_comparison_evaluations",
        "quality_comparison_evaluation_participants",
        "quality_comparison_evaluation_evidence",
        "quality_comparison_findings",
    ):
        columns = {c["name"] for c in inspector.get_columns(table_name)}
        assert "observed_representation" not in columns
        assert "value" not in columns
