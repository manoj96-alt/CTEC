"""Repository for OQI-H2 Accuracy evaluation persistence (CDD-048 §7-§8;
Artifact Authorization row 7). Accuracy is OQI1-storage-family-shaped: it
persists into the SAME `quality_evaluations`/`quality_evaluation_evidence`/
`quality_findings` tables OQI1 already owns (unmodified schema, dimension=
ACCURACY, finding_type=REFERENCE_VALUE_UNSUPPORTED), plus one new link table,
`oqi_quality_evaluation_reference_evidence`, pinning every qualifying
`ReferenceEvidenceAssertion` version the comparison consulted.

`acquire_evaluation_authority` reuses OQI1's own advisory-lock seed (1) --
Accuracy's identity strings are computed from `rule.quality_condition_id`
in the exact same way OQI1's are, and since Accuracy `QualityRule` rows
have their own distinct `quality_condition_id`s, no collision with a
genuine Completeness/Validity lock is possible (the seed only needs to
distinguish unrelated *subsystems*, and Accuracy is not one -- it shares
OQI1's evaluation-ledger/current-state-Finding subsystem entirely).

`resolve_enterprise_entity_id` reuses `EntityResolutionStore` exactly as
`OqiOntologyImpactEvaluationRepositoryImpl.resolve_direct_impact` already
does for its own single-source-object case -- OQI-H2 introduces zero new
identity-resolution logic."""

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
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_quality_evaluation import (
    QualityEvaluationEvidenceORM,
    QualityEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_quality_rule import QualityRuleORM
from app.infrastructure.persistence.models.oqi_reference_evidence import (
    QualityEvaluationReferenceEvidenceORM,
)

#: Shared with OQI1 -- Accuracy persists into OQI1's own tables (CDD-048 §7).
OQI_ACCURACY_ADVISORY_LOCK_SEED = 1


class OqiAccuracyEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_ACCURACY_ADVISORY_LOCK_SEED},
        )

    def resolve_enterprise_entity_id(
        self, *, tenant_id: str, source_object_id: UUID
    ) -> UUID | None:
        """CDD-048 §7: the observation's real-world identity anchor for
        Reference Evidence lookup. `None` when unresolved -- this is a
        legitimate NOT_EVALUABLE cause, never a fabricated anchor."""
        store = EntityResolutionStore(self.session)
        record = store.get_current_record(
            tenant_id, EntityResolutionStore.understanding_key((source_object_id,))
        )
        if record is None:
            return None
        if record.outcome != "Resolved" or record.enterprise_entity_id is None:
            return None
        return record.enterprise_entity_id

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None:
        """Identical query shape to
        `OqiQualityEvaluationRepositoryImpl.select_latest_target_field_value`
        (CDD-039 §32) -- duplicated here rather than imported/reused because
        that file is not authorized for modification and this repository
        must not depend on its private internals."""
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

    def link_reference_evidence(self, *, evaluation_id: UUID, assertion_id: UUID) -> None:
        """CDD-048 §7: pins one qualifying `ReferenceEvidenceAssertion`
        version this evaluation consulted. Called once per backing
        assertion (a subject's single qualifying value may be corroborated
        by more than one agreeing ACTIVE form)."""
        self.session.add(
            QualityEvaluationReferenceEvidenceORM(
                evaluation_id=evaluation_id, assertion_id=assertion_id
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
        """CDD-048 §23: mirrors `OqiQualityEvaluationRepositoryImpl.has_
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
