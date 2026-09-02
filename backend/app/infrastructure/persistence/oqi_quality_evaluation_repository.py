"""Repository coordinating OQI's evaluation-authority lock, evidence
selection, immutable evaluation-ledger persistence, and QualityFinding
current-state mutation -- all inside one transaction (CDD-039 §19-§26,
§39; OQI1 Artifact Authorization §4; Concurrency Hardening Amendment §11).

`acquire_evaluation_authority` is the exact GR-selected mechanism:
`SELECT pg_advisory_xact_lock(hashtextextended(:identity, 1))`, reusing
verbatim the shape of `backend/app/runtime/persistence/repository.py`'s
`_lock_replay_identity` -- PostgreSQL computes the hash from the identity
*text*; no UUID byte-splitting, XOR-folding, or manual signed-integer
conversion occurs anywhere in this file. `:identity` must be
`app.domain.oqi.evaluation.finding_identity_material(...)`'s own output --
the exact same string that also feeds `derive_quality_finding_id`'s
`uuid5` call -- so the lock's authority domain can never drift from the
Finding identity domain it must match (Concurrency Hardening Amendment
§11). The advisory-lock hash is pure synchronization infrastructure: it
never appears in any identity, query filter, or return value below every
read/write here is keyed by the real tenant_id/quality_condition_id/
finding_id/evaluation_id columns.

`select_known_lineage_evidence_ids`/`select_target_field_evidence_ids`
implement CDD-039 §12's "known lineage" query and §31-§32's "qualifying
target evidence" query directly against the existing, unmodified
`field_value_evidence`/`source_fields` tables (read-only; CDD-039 §7).
Both filter on `received_at <= evaluation_horizon` -- CTEC's own trusted
admission clock, not the source-supplied `observed_at` -- so a HISTORICAL
evaluation's caller-supplied horizon has genuine "as of that point in
CTEC's own knowledge" semantics (CDD-039 §22), while a CURRENT_STATE
evaluation's "now" horizon is effectively unfiltered."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi.evaluation import (
    EvaluationSubject,
    QualityEvaluation,
    SourceRecordLineageIdentity,
)
from app.domain.oqi.finding import QualityFinding, QualityFindingStatus
from app.domain.oqi.quality_rule import QualityFindingType
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_quality_evaluation import (
    QualityEvaluationEvidenceORM,
    QualityEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_quality_rule import QualityRuleORM
from app.infrastructure.persistence.models.source_field import SourceFieldORM

#: Concurrency Hardening Amendment §11: a fixed seed distinguishing OQI1's
#: `hashtextextended` hash outputs from `_lock_replay_identity`'s own use of
#: seed 0 for the identical `pg_advisory_xact_lock(bigint)` form, so the two
#: otherwise-unrelated subsystems can never coincidentally serialize against
#: each other.
OQI_ADVISORY_LOCK_SEED = 1


class OqiQualityEvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_finding(self, finding_id: UUID) -> QualityFinding | None: ...

    def insert_evaluation_idempotent(self, evaluation: QualityEvaluation) -> bool: ...

    def upsert_finding(self, finding: QualityFinding) -> None: ...

    def select_known_lineage_evidence_id(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> UUID | None: ...

    def select_target_field_evidence_ids(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, ...]: ...

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None: ...

    # `has_any_evaluation_for_source_objects` (CDD-044 §49.1) is
    # intentionally NOT declared on this Protocol -- OQI6 always consumes
    # the concrete `OqiQualityEvaluationRepositoryImpl` directly, so
    # adding it here would force every existing fake/test double already
    # structurally typed against this Protocol to implement a method they
    # have no use for. The method exists only on the concrete class below.


class OqiQualityEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        """Transaction-scoped: releases automatically on COMMIT, ROLLBACK,
        or connection loss. Never `pg_advisory_lock` (session-scoped)."""
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_ADVISORY_LOCK_SEED},
        )

    def get_finding(self, finding_id: UUID) -> QualityFinding | None:
        model = self.session.get(QualityFindingORM, finding_id)
        return None if model is None else _finding_to_domain(model)

    def insert_evaluation_idempotent(self, evaluation: QualityEvaluation) -> bool:
        """Returns True if a new ledger row (and its evidence associations)
        were inserted; False if `evaluation.evaluation_id` already existed
        -- a byte-identical logical replay is then a genuine no-op, never a
        duplicate row and never an error (CDD-039 §20)."""
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
                evidence_set_digest=_evidence_digest_of(evaluation),
                outcome=evaluation.outcome.value,
                applied_current_state_authority=evaluation.applied_current_state_authority,
                state_revision_applied=evaluation.state_revision_applied,
                evaluated_on=evaluation.evaluated_on,
            )
        )
        # Explicit flush before the child rows: guarantees the parent
        # ledger row is genuinely written first, matching
        # OqiQualityRuleRepositoryImpl.activate_new_version's identical
        # discipline for the same class of ordering guarantee.
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

    def select_known_lineage_evidence_id(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> UUID | None:
        """CDD-039 §12: does at least one admitted, non-empty
        `FieldValueEvidence` observation exist for *any* `SourceField`
        belonging to `source_object_id`, carrying `source_record_reference`,
        within the evaluation's admitted-evidence frontier?"""
        return self.session.execute(
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

    def select_target_field_evidence_ids(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, ...]:
        """CDD-039 §12: qualifying evidence for the *target* SourceField
        only -- used by Completeness."""
        rows = (
            self.session.execute(
                select(FieldValueEvidenceORM.field_value_evidence_id).where(
                    FieldValueEvidenceORM.source_field_id == source_field_id,
                    FieldValueEvidenceORM.source_record_reference == source_record_reference,
                    FieldValueEvidenceORM.observed_representation != "",
                    FieldValueEvidenceORM.received_at <= evaluation_horizon,
                )
            )
            .scalars()
            .all()
        )
        return tuple(rows)

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None:
        """CDD-039 §32: the single latest qualifying evidence row for
        Validity -- greatest `observed_at`, ties broken by greatest
        `received_at` (CDD-031's own comparable-evidence selection
        precedent)."""
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

    def has_any_evaluation_for_source_objects(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...]
    ) -> bool:
        """CDD-044 §49.1 (OQI6 Artifact Authorization §2.2 row 12): narrow,
        additive, read-only. Reports whether at least one OQI1
        `QualityEvaluation` row -- regardless of outcome -- has ever been
        persisted whose resolved evidence is one of the given
        `source_object_ids` (already resolved by the caller). Coverage is
        a boolean existence predicate over real persisted rows, never a
        percentage. No other method's behavior changes; no write path."""
        if not source_object_ids:
            return False
        return (
            self.session.execute(
                select(QualityEvaluationORM.evaluation_id)
                .where(
                    QualityEvaluationORM.tenant_id == tenant_id,
                    QualityEvaluationORM.source_object_id.in_(source_object_ids),
                )
                .limit(1)
            ).first()
            is not None
        )

    def has_qualifying_coverage_for_dimension(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...], dimension: str
    ) -> bool:
        """CDD-047 §14, Artifact Authorization row 10: narrow, additive,
        read-only. Reports whether at least one OQI1 `QualityEvaluation`
        row -- regardless of outcome -- has ever been persisted, whose
        resolved evidence is one of the given `source_object_ids`, AND
        whose governing `QualityRule.dimension` matches the requested
        dimension. No `dimension` column exists directly on
        `quality_evaluations` (verified directly against its schema) --
        this is why the join to `quality_rules` is required and was not
        already expressible via `has_any_evaluation_for_source_objects`,
        which is family-level, not dimension-level, and remains completely
        unmodified by this addition. `dimension` is passed as the plain
        `CoverageDimension` string value (`"COMPLETENESS"`/`"VALIDITY"`) --
        this method has no dependency on `CoverageDimension` itself, only
        on the identical literal `QualityDimension` values it shares."""
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


def _evidence_digest_of(evaluation: QualityEvaluation) -> str:
    from app.domain.oqi.evaluation import evidence_set_digest

    return evidence_set_digest(evaluation.evidence_ids)


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
