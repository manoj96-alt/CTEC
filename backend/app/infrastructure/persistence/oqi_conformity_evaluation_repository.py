"""Repository for OQI-H3 Conformity evaluation persistence (CDD-049 §14-§15,
§21; Artifact Authorization row 4). Conformity is OQI1-storage-family-shaped:
it persists into the SAME `quality_evaluations`/`quality_evaluation_evidence`/
`quality_findings` tables OQI1 and Accuracy already own (unmodified schema,
dimension=CONFORMITY, finding_type=NON_CANONICAL_REPRESENTATION), plus one
new link table, `oqi_quality_evaluation_canonical_standard`, pinning the
exact `CanonicalStandard` value/version the comparison consulted.

`acquire_evaluation_authority` reuses OQI1's own advisory-lock seed (1) --
identical reasoning to `OqiAccuracyEvaluationRepositoryImpl` (CDD-048's own
precedent): Conformity shares OQI1's evaluation-ledger/current-state-Finding
subsystem entirely, and its `quality_condition_id`s are distinct from
Completeness/Validity/Accuracy's own.

Unlike Accuracy, Conformity requires NO entity-resolution step -- its
`CanonicalStandard` is resolved directly from the evaluating rule's own
`information_element_requirement_id` (CDD-049 §8), never from a resolved
real-world entity identity."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi.evaluation import (
    EvaluationSubject,
    QualityEvaluation,
    SourceRecordLineageIdentity,
    evidence_set_digest,
)
from app.domain.oqi.finding import QualityFinding, QualityFindingStatus
from app.domain.oqi.quality_rule import QualityFindingType
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_canonical_standard import (
    QualityEvaluationCanonicalStandardORM,
)
from app.infrastructure.persistence.models.oqi_quality_evaluation import (
    QualityEvaluationEvidenceORM,
    QualityEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_quality_rule import QualityRuleORM

#: Shared with OQI1/Accuracy -- Conformity persists into OQI1's own tables
#: (CDD-049 §14).
OQI_CONFORMITY_ADVISORY_LOCK_SEED = 1


class OqiConformityEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_CONFORMITY_ADVISORY_LOCK_SEED},
        )

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None:
        """Identical query shape to
        `OqiAccuracyEvaluationRepositoryImpl.select_latest_target_field_value`
        -- duplicated here rather than imported/reused because that file is
        not authorized for modification and this repository must not depend
        on its private internals."""
        row = self.session.execute(
            select(
                FieldValueEvidenceORM.field_value_evidence_id,
                FieldValueEvidenceORM.observed_representation,
            )
            .where(
                FieldValueEvidenceORM.source_field_id == source_field_id,
                FieldValueEvidenceORM.source_record_reference == source_record_reference,
                FieldValueEvidenceORM.observed_representation != "",
                FieldValueEvidenceORM.received_at <= evaluation_horizon,
            )
            .order_by(
                FieldValueEvidenceORM.observed_at.desc(), FieldValueEvidenceORM.received_at.desc()
            )
            .limit(1)
        ).first()
        return None if row is None else (row[0], row[1])

    def get_finding(self, finding_id: UUID) -> QualityFinding | None:
        model = self.session.get(QualityFindingORM, finding_id)
        return None if model is None else _finding_to_domain(model)

    def insert_evaluation_idempotent(self, evaluation: QualityEvaluation) -> bool:
        existing = self.session.get(QualityEvaluationORM, evaluation.evaluation_id)
        if existing is not None:
            return False
        self.session.add(
            QualityEvaluationORM(
                evaluation_id=evaluation.evaluation_id,
                tenant_id=evaluation.tenant_id,
                quality_condition_id=evaluation.quality_condition_id,
                rule_id=evaluation.rule_id,
                rule_version=evaluation.rule_version,
                subject_type=evaluation.subject.subject_type,
                source_object_id=evaluation.subject.lineage.source_object_id,
                source_record_reference=evaluation.subject.lineage.source_record_reference,
                source_field_id=evaluation.subject.source_field_id,
                evaluation_mode=evaluation.evaluation_mode.value,
                evaluation_origin=evaluation.evaluation_origin.value,
                evaluation_horizon=evaluation.evaluation_horizon,
                evidence_set_digest=evidence_set_digest(evaluation.evidence_ids),
                outcome=evaluation.outcome.value,
                applied_current_state_authority=evaluation.applied_current_state_authority,
                state_revision_applied=evaluation.state_revision_applied,
                evaluated_on=evaluation.evaluated_on,
            )
        )
        self.session.flush()
        for sequence_index, evidence_id in enumerate(evaluation.evidence_ids):
            self.session.add(
                QualityEvaluationEvidenceORM(
                    evaluation_id=evaluation.evaluation_id,
                    field_value_evidence_id=evidence_id,
                    sequence_index=sequence_index,
                )
            )
        return True

    def link_canonical_standard(
        self, *, evaluation_id: UUID, canonical_value_id: UUID, standard_version: int
    ) -> None:
        """CDD-049 §15: pins the exact `CanonicalValue`/version this
        evaluation consulted."""
        self.session.add(
            QualityEvaluationCanonicalStandardORM(
                evaluation_id=evaluation_id,
                canonical_value_id=canonical_value_id,
                standard_version=standard_version,
            )
        )

    def upsert_finding(self, finding: QualityFinding) -> None:
        model = self.session.get(QualityFindingORM, finding.finding_id)
        if model is None:
            self.session.add(_finding_to_orm(finding))
            return
        model.status = finding.status.value
        model.state_revision = finding.state_revision
        model.last_seen_at = finding.last_seen_at
        model.last_evaluated_horizon = finding.last_evaluated_horizon
        model.occurrence_count = finding.occurrence_count
        model.reopen_count = finding.reopen_count

    def has_qualifying_coverage_for_dimension(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...], dimension: str
    ) -> bool:
        """CDD-049 §21: mirrors `OqiAccuracyEvaluationRepositoryImpl.has_
        qualifying_coverage_for_dimension`'s exact shape -- existence-only,
        regardless of outcome, joined through `quality_rules.dimension`."""
        if not source_object_ids:
            return False
        return (
            self.session.execute(
                select(QualityEvaluationORM.evaluation_id)
                .join(QualityRuleORM, QualityRuleORM.rule_id == QualityEvaluationORM.rule_id)
                .where(
                    QualityEvaluationORM.tenant_id == tenant_id,
                    QualityEvaluationORM.source_object_id.in_(source_object_ids),
                    QualityRuleORM.dimension == dimension,
                )
                .limit(1)
            ).first()
            is not None
        )


def _finding_to_orm(finding: QualityFinding) -> QualityFindingORM:
    return QualityFindingORM(
        finding_id=finding.finding_id,
        tenant_id=finding.tenant_id,
        quality_condition_id=finding.quality_condition_id,
        subject_type=finding.subject.subject_type,
        source_object_id=finding.subject.lineage.source_object_id,
        source_record_reference=finding.subject.lineage.source_record_reference,
        source_field_id=finding.subject.source_field_id,
        finding_type=finding.finding_type.value,
        status=finding.status.value,
        state_revision=finding.state_revision,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
        last_evaluated_horizon=finding.last_evaluated_horizon,
        occurrence_count=finding.occurrence_count,
        reopen_count=finding.reopen_count,
    )


def _finding_to_domain(model: QualityFindingORM) -> QualityFinding:
    lineage = SourceRecordLineageIdentity(
        tenant_id=model.tenant_id,
        source_object_id=model.source_object_id,
        source_record_reference=model.source_record_reference,
    )
    subject = EvaluationSubject(lineage=lineage, source_field_id=model.source_field_id)
    return QualityFinding(
        finding_id=model.finding_id,
        tenant_id=model.tenant_id,
        quality_condition_id=model.quality_condition_id,
        subject=subject,
        finding_type=QualityFindingType(model.finding_type),
        status=QualityFindingStatus(model.status),
        state_revision=model.state_revision,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
        last_evaluated_horizon=model.last_evaluated_horizon,
        occurrence_count=model.occurrence_count,
        reopen_count=model.reopen_count,
    )
