"""Repository coordinating OQI2's cross-source evaluation-authority lock,
per-participant evidence selection, immutable evaluation-ledger persistence
(with its participant snapshot and participant-scoped evidence
association), and `QualityComparisonFinding` current-state mutation -- all
inside one transaction (CDD-040 §37, §46-§52).

`acquire_evaluation_authority` reuses OQI1's exact mechanism --
`SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))` -- with
`OQI_CROSS_SOURCE_ADVISORY_LOCK_SEED = 2`, distinct from both
`_lock_replay_identity`'s seed 0 and OQI1's own seed 1 (CDD-040 §46). No
UUID byte-splitting, XOR-folding, or manual signed-integer conversion
occurs anywhere in this file. `:identity` must be
`app.domain.oqi_cross_source.evaluation.finding_identity_material(...)`'s
own output -- the exact same string that also feeds
`derive_comparison_finding_id`'s `uuid5` call."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi.finding import QualityFindingStatus
from app.domain.oqi.quality_rule import QualityFindingType
from app.domain.oqi_cross_source.evaluation import (
    QualityComparisonEvaluation,
    participant_evidence_digest,
)
from app.domain.oqi_cross_source.finding import QualityComparisonFinding
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_cross_source_evaluation import (
    QualityComparisonEvaluationEvidenceORM,
    QualityComparisonEvaluationORM,
    QualityComparisonEvaluationParticipantORM,
)
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.source_field import SourceFieldORM

#: CDD-040 §46: distinct from `_lock_replay_identity`'s seed 0 and OQI1's
#: own `OQI_ADVISORY_LOCK_SEED = 1`, so the three otherwise-unrelated
#: subsystems can never coincidentally serialize against each other.
OQI_CROSS_SOURCE_ADVISORY_LOCK_SEED = 2


class OqiCrossSourceEvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_finding(self, finding_id: UUID) -> QualityComparisonFinding | None: ...

    def insert_evaluation_idempotent(self, evaluation: QualityComparisonEvaluation) -> bool: ...

    def upsert_finding(self, finding: QualityComparisonFinding) -> None: ...

    def select_known_lineage(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> bool: ...

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None: ...


class OqiCrossSourceEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        """Transaction-scoped: releases automatically on COMMIT, ROLLBACK,
        or connection loss."""
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_CROSS_SOURCE_ADVISORY_LOCK_SEED},
        )

    def get_finding(self, finding_id: UUID) -> QualityComparisonFinding | None:
        model = self.session.get(QualityComparisonFindingORM, finding_id)
        return None if model is None else _finding_to_domain(model)

    def insert_evaluation_idempotent(self, evaluation: QualityComparisonEvaluation) -> bool:
        """Returns True if a new ledger row (and its participant/evidence
        associations) were inserted; False if `evaluation.evaluation_id`
        already existed -- a byte-identical logical replay is then a
        genuine no-op (CDD-040 §43)."""
        existing = self.session.get(QualityComparisonEvaluationORM, evaluation.evaluation_id)
        if existing is not None:
            return False
        self.session.add(
            QualityComparisonEvaluationORM(
                evaluation_id=evaluation.evaluation_id,
                tenant_id=evaluation.tenant_id,
                quality_condition_id=evaluation.quality_condition_id,
                rule_id=evaluation.rule_id,
                rule_version=evaluation.rule_version,
                subject_type="CROSS_SOURCE_COMPARISON",
                comparison_subject_id=evaluation.comparison_subject_id,
                comparison_subject_correspondence_id=evaluation.comparison_subject_correspondence_id,
                evaluation_mode=evaluation.evaluation_mode.value,
                evaluation_origin=evaluation.evaluation_origin.value,
                evaluation_horizon=evaluation.evaluation_horizon,
                participant_evidence_digest=participant_evidence_digest(evaluation.participants),
                outcome=evaluation.outcome.value,
                applied_current_state_authority=evaluation.applied_current_state_authority,
                state_revision_applied=evaluation.state_revision_applied,
                evaluated_on=evaluation.evaluated_on,
            )
        )
        # Explicit flush before the child rows, matching
        # OqiQualityEvaluationRepositoryImpl's identical discipline.
        self.session.flush()
        for entry in evaluation.participants:
            self.session.add(
                QualityComparisonEvaluationParticipantORM(
                    evaluation_id=evaluation.evaluation_id,
                    participant_role=entry.role,
                    source_field_id=entry.source_field_id,
                    source_object_id=entry.lineage.source_object_id,
                    source_record_reference=entry.lineage.source_record_reference,
                    expected=entry.expected,
                    authoritative=entry.authoritative,
                )
            )
        self.session.flush()
        for entry in evaluation.participants:
            for sequence_index, evidence_id in enumerate(entry.evidence_ids):
                self.session.add(
                    QualityComparisonEvaluationEvidenceORM(
                        evaluation_id=evaluation.evaluation_id,
                        participant_role=entry.role,
                        source_field_id=entry.source_field_id,
                        field_value_evidence_id=evidence_id,
                        sequence_index=sequence_index,
                    )
                )
        return True

    def upsert_finding(self, finding: QualityComparisonFinding) -> None:
        model = self.session.get(QualityComparisonFindingORM, finding.finding_id)
        if model is None:
            self.session.add(_finding_to_orm(finding))
            return
        model.finding_type = finding.finding_type.value
        model.status = finding.status.value
        model.state_revision = finding.state_revision
        model.last_seen_at = finding.last_seen_at
        model.last_evaluated_horizon = finding.last_evaluated_horizon
        model.occurrence_count = finding.occurrence_count
        model.reopen_count = finding.reopen_count
        model.latest_evaluation_id = finding.latest_evaluation_id

    def select_known_lineage(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> bool:
        """CDD-040 §28 (reused from CDD-039 §12 unchanged): does at least
        one admitted, non-empty `FieldValueEvidence` observation exist for
        *any* SourceField belonging to `source_object_id`, carrying
        `source_record_reference`, within the evaluation's admitted-
        evidence frontier?"""
        found = self.session.execute(
            select(FieldValueEvidenceORM.field_value_evidence_id)
            .join(
                SourceFieldORM,
                SourceFieldORM.source_field_id == FieldValueEvidenceORM.source_field_id,
            )
            .where(
                SourceFieldORM.source_object_id == source_object_id,
                FieldValueEvidenceORM.source_record_reference == source_record_reference,
                FieldValueEvidenceORM.observed_representation != "",
                FieldValueEvidenceORM.received_at <= evaluation_horizon,
            )
            .limit(1)
        ).scalar_one_or_none()
        return found is not None

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None:
        """CDD-040 §48: the single latest qualifying evidence row for one
        participant's target SourceField -- greatest `observed_at`, ties
        broken by greatest `received_at`, reusing OQI1's exact ordering."""
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


def _finding_to_orm(finding: QualityComparisonFinding) -> QualityComparisonFindingORM:
    return QualityComparisonFindingORM(
        finding_id=finding.finding_id,
        tenant_id=finding.tenant_id,
        quality_condition_id=finding.quality_condition_id,
        subject_type="CROSS_SOURCE_COMPARISON",
        comparison_subject_id=finding.comparison_subject_id,
        finding_type=finding.finding_type.value,
        status=finding.status.value,
        state_revision=finding.state_revision,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
        last_evaluated_horizon=finding.last_evaluated_horizon,
        occurrence_count=finding.occurrence_count,
        reopen_count=finding.reopen_count,
        latest_evaluation_id=finding.latest_evaluation_id,
    )


def _finding_to_domain(model: QualityComparisonFindingORM) -> QualityComparisonFinding:
    return QualityComparisonFinding(
        finding_id=model.finding_id,
        tenant_id=model.tenant_id,
        quality_condition_id=model.quality_condition_id,
        comparison_subject_id=model.comparison_subject_id,
        finding_type=QualityFindingType(model.finding_type),
        status=QualityFindingStatus(model.status),
        state_revision=model.state_revision,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
        last_evaluated_horizon=model.last_evaluated_horizon,
        occurrence_count=model.occurrence_count,
        reopen_count=model.reopen_count,
        latest_evaluation_id=model.latest_evaluation_id,
    )
