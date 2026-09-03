"""Repository for OQI-H4 Reference Integrity evaluation persistence
(CDD-050 §10.2, §12; Artifact Authorization row 10).

`get_latest_resolution_record_for_source_object` is the sole ER-consuming
query -- strictly read-only against `enterprise_entity_resolution_records`,
never invoking Entity Resolution matching, never inferring a target
(CDD-050 §10.2). `supporting_source_object_ids` is a pre-existing JSON array
column (not a relational reference, CDD-022-era schema), so containment is
checked in Python after a tenant-scoped fetch -- identical discipline to
`EntityResolutionStore._assert_source_objects_owned_by_tenant`'s own
established precedent, never a fragile raw JSON operator query.

`acquire_evaluation_authority` reuses a dedicated seed (10), distinct from
every other existing OQI seed."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.identity_resolution.model import ResolutionOutcome
from app.domain.oqi_integrity.reference import ReferenceIntegrityFinding
from app.domain.oqi_integrity.structural import IntegrityFindingStatus, IntegrityFindingType
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionRecordModel,
)
from app.infrastructure.persistence.models.oqi_integrity import (
    IntegrityReferenceEvaluationORM,
    IntegrityReferenceFindingORM,
)

#: CDD-050 §7: distinct from every existing OQI seed (1-9).
OQI_INTEGRITY_REFERENCE_ADVISORY_LOCK_SEED = 10


class OqiIntegrityReferenceEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_INTEGRITY_REFERENCE_ADVISORY_LOCK_SEED},
        )

    def get_latest_resolution_record_for_source_object(
        self, *, tenant_id: str, source_object_id: UUID
    ) -> tuple[UUID, ResolutionOutcome] | None:
        """Returns `(record_id, outcome)` for the most recently produced ER
        resolution record whose `supporting_source_object_ids` includes
        `source_object_id`, or `None` if Entity Resolution has never
        evaluated this source object at all -- the exact `NOT_EVALUABLE`
        trigger (CDD-050 §10.2)."""
        rows = self.session.execute(
            select(
                EnterpriseEntityResolutionRecordModel.record_id,
                EnterpriseEntityResolutionRecordModel.supporting_source_object_ids,
                EnterpriseEntityResolutionRecordModel.outcome,
                EnterpriseEntityResolutionRecordModel.produced_at,
            )
            .where(EnterpriseEntityResolutionRecordModel.tenant_id == tenant_id)
            .order_by(EnterpriseEntityResolutionRecordModel.produced_at.desc())
        ).all()
        target = str(source_object_id)
        for record_id, supporting_ids, outcome, _produced_at in rows:
            if target in supporting_ids:
                return record_id, ResolutionOutcome(outcome)
        return None

    def get_finding(self, finding_id: UUID) -> ReferenceIntegrityFinding | None:
        model = self.session.get(IntegrityReferenceFindingORM, finding_id)
        return None if model is None else _finding_to_domain(model)

    def insert_evaluation_idempotent(
        self,
        *,
        evaluation_id: UUID,
        tenant_id: str,
        relationship_requirement_id: UUID,
        source_object_id: UUID,
        resolution_record_id: UUID,
        resolution_outcome: str,
        outcome: str,
        evaluation_horizon: datetime,
        evaluated_on: datetime,
    ) -> bool:
        existing = self.session.get(IntegrityReferenceEvaluationORM, evaluation_id)
        if existing is not None:
            return False
        self.session.add(
            IntegrityReferenceEvaluationORM(
                evaluation_id=evaluation_id,
                tenant_id=tenant_id,
                relationship_requirement_id=relationship_requirement_id,
                source_object_id=source_object_id,
                resolution_record_id=resolution_record_id,
                resolution_outcome=resolution_outcome,
                outcome=outcome,
                evaluation_horizon=evaluation_horizon,
                evaluated_on=evaluated_on,
            )
        )
        self.session.flush()
        return True

    def upsert_finding(self, finding: ReferenceIntegrityFinding) -> None:
        model = self.session.get(IntegrityReferenceFindingORM, finding.finding_id)
        if model is None:
            self.session.add(_finding_to_orm(finding))
            return
        model.status = finding.status.value
        model.state_revision = finding.state_revision
        model.last_seen_at = finding.last_seen_at
        model.last_evaluated_horizon = finding.last_evaluated_horizon
        model.occurrence_count = finding.occurrence_count
        model.reopen_count = finding.reopen_count

    def has_qualifying_coverage(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...]
    ) -> bool:
        """CDD-050 §24 (H1 coverage): existence-only, subject-scoped -- at
        least one Reference Integrity evaluation row (any outcome) exists
        for one of the caller-supplied source objects."""
        if not source_object_ids:
            return False
        return (
            self.session.execute(
                select(IntegrityReferenceEvaluationORM.evaluation_id)
                .where(
                    IntegrityReferenceEvaluationORM.tenant_id == tenant_id,
                    IntegrityReferenceEvaluationORM.source_object_id.in_(source_object_ids),
                )
                .limit(1)
            ).first()
            is not None
        )


def _finding_to_orm(finding: ReferenceIntegrityFinding) -> IntegrityReferenceFindingORM:
    return IntegrityReferenceFindingORM(
        finding_id=finding.finding_id,
        tenant_id=finding.tenant_id,
        relationship_requirement_id=finding.relationship_requirement_id,
        source_object_id=finding.source_object_id,
        finding_type=finding.finding_type.value,
        status=finding.status.value,
        state_revision=finding.state_revision,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
        last_evaluated_horizon=finding.last_evaluated_horizon,
        occurrence_count=finding.occurrence_count,
        reopen_count=finding.reopen_count,
    )


def _finding_to_domain(model: IntegrityReferenceFindingORM) -> ReferenceIntegrityFinding:
    return ReferenceIntegrityFinding(
        finding_id=model.finding_id,
        tenant_id=model.tenant_id,
        relationship_requirement_id=model.relationship_requirement_id,
        source_object_id=model.source_object_id,
        finding_type=IntegrityFindingType(model.finding_type),
        status=IntegrityFindingStatus(model.status),
        state_revision=model.state_revision,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
        last_evaluated_horizon=model.last_evaluated_horizon,
        occurrence_count=model.occurrence_count,
        reopen_count=model.reopen_count,
    )
