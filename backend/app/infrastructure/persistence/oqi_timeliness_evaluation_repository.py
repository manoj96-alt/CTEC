"""Repository for OQI-H5 Timeliness evaluation persistence (CDD-051 §8,
§17-§18, §33; Artifact Authorization row 7).

`select_latest_qualifying_evidence` mirrors OQI1's own established
"latest qualifying evidence" query shape exactly (`select_latest_target_
field_value`, `oqi_quality_evaluation_repository.py`): filters
`received_at <= evaluation_horizon` (CDD-051 §13's historical/as-of
discipline -- never a substitute for wall-clock `now()`), orders by
`observed_at DESC, received_at DESC`, returns the single latest row. Unlike
OQI1's Completeness-scoped query, this method does not filter on
`observed_representation != ''` -- Timeliness cares whether the latest
observation is current, not whether it is populated (that remains
Completeness's own, separate concern, CDD-051 §16). Tenant ownership is
verified transitively through `source_fields.source_object_id ->
source_objects.tenant_id` (CDD-022 §7 precedent) -- never a stored column
on `field_value_evidence` itself.

`acquire_evaluation_authority` reuses a dedicated seed (12), distinct from
the policy repository's own seed (11) and every other existing OQI seed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_timeliness.evaluation import (
    TimelinessFinding,
    TimelinessFindingStatus,
    TimelinessFindingType,
)
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_timeliness import (
    TimelinessEvaluationORM,
    TimelinessFindingORM,
)
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM

#: CDD-051 §8: next available value in the OQI advisory-lock seed registry,
#: distinct from OqiTimelinessPolicyRepositoryImpl's own seed (11) and every
#: existing OQI seed (1-10).
OQI_TIMELINESS_EVALUATION_ADVISORY_LOCK_SEED = 12


@dataclass(frozen=True, slots=True)
class QualifyingEvidence:
    """CDD-051 §33: the single latest qualifying `FieldValueEvidence` row
    for a governed `SourceField`, plus the `source_object_id` needed to
    compose the tenant-qualified FK on the Evaluation/Finding rows."""

    field_value_evidence_id: UUID
    source_object_id: UUID
    observed_at: datetime
    received_at: datetime


class OqiTimelinessEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_TIMELINESS_EVALUATION_ADVISORY_LOCK_SEED},
        )

    def select_latest_qualifying_evidence(
        self, *, tenant_id: str, source_field_id: UUID, evaluation_horizon: datetime
    ) -> QualifyingEvidence | None:
        row = self.session.execute(
            select(
                FieldValueEvidenceORM.field_value_evidence_id,
                FieldValueEvidenceORM.observed_at,
                FieldValueEvidenceORM.received_at,
                SourceFieldORM.source_object_id,
            )
            .join(
                SourceFieldORM,
                SourceFieldORM.source_field_id == FieldValueEvidenceORM.source_field_id,
            )
            .join(
                SourceObjectORM,
                SourceObjectORM.source_object_id == SourceFieldORM.source_object_id,
            )
            .where(
                FieldValueEvidenceORM.source_field_id == source_field_id,
                FieldValueEvidenceORM.received_at <= evaluation_horizon,
                SourceObjectORM.tenant_id == tenant_id,
            )
            .order_by(
                FieldValueEvidenceORM.observed_at.desc(), FieldValueEvidenceORM.received_at.desc()
            )
            .limit(1)
        ).first()
        if row is None:
            return None
        return QualifyingEvidence(
            field_value_evidence_id=row[0],
            observed_at=row[1],
            received_at=row[2],
            source_object_id=row[3],
        )

    def get_finding(self, finding_id: UUID) -> TimelinessFinding | None:
        model = self.session.get(TimelinessFindingORM, finding_id)
        return None if model is None else _finding_to_domain(model)

    def insert_evaluation_idempotent(
        self,
        *,
        evaluation_id: UUID,
        tenant_id: str,
        policy_id: UUID,
        policy_version: int,
        finding_type: str,
        source_object_id: UUID,
        field_value_evidence_id: UUID,
        outcome: str,
        evaluation_horizon: datetime,
        evaluated_on: datetime,
    ) -> bool:
        existing = self.session.get(TimelinessEvaluationORM, evaluation_id)
        if existing is not None:
            return False
        self.session.add(
            TimelinessEvaluationORM(
                evaluation_id=evaluation_id,
                tenant_id=tenant_id,
                policy_id=policy_id,
                policy_version=policy_version,
                finding_type=finding_type,
                source_object_id=source_object_id,
                field_value_evidence_id=field_value_evidence_id,
                outcome=outcome,
                evaluation_horizon=evaluation_horizon,
                evaluated_on=evaluated_on,
            )
        )
        self.session.flush()
        return True

    def upsert_finding(self, finding: TimelinessFinding, *, policy_version: int) -> None:
        """`policy_version` is repository-managed bookkeeping only (kept
        current to whichever policy version produced this transition) --
        never part of `TimelinessFinding`'s own domain identity (CDD-051
        §17), required only so the row's tenant-qualified composite FK to
        `oqi_timeliness_policies` can compose (see
        `models/oqi_timeliness.py`'s own docstring on `TimelinessFindingORM`)."""
        model = self.session.get(TimelinessFindingORM, finding.finding_id)
        if model is None:
            self.session.add(_finding_to_orm(finding, policy_version=policy_version))
            return
        model.policy_version = policy_version
        model.status = finding.status.value
        model.state_revision = finding.state_revision
        model.last_seen_at = finding.last_seen_at
        model.last_evaluated_horizon = finding.last_evaluated_horizon
        model.occurrence_count = finding.occurrence_count
        model.reopen_count = finding.reopen_count

    def has_qualifying_coverage(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...]
    ) -> bool:
        """CDD-051 §25 (I2 Coverage dispatch consumes this; created now,
        alongside the rest of this I1-authorized file, so I2 needs no
        further MODIFY to this file): existence-only, subject-scoped -- at
        least one Timeliness evaluation row (any outcome, any finding type)
        exists for one of the caller-supplied `source_object_id`s."""
        if not source_object_ids:
            return False
        return (
            self.session.execute(
                select(TimelinessEvaluationORM.evaluation_id)
                .where(
                    TimelinessEvaluationORM.tenant_id == tenant_id,
                    TimelinessEvaluationORM.source_object_id.in_(source_object_ids),
                )
                .limit(1)
            ).first()
            is not None
        )


def _finding_to_orm(finding: TimelinessFinding, *, policy_version: int) -> TimelinessFindingORM:
    return TimelinessFindingORM(
        finding_id=finding.finding_id,
        tenant_id=finding.tenant_id,
        policy_id=finding.policy_id,
        policy_version=policy_version,
        finding_type=finding.finding_type.value,
        source_object_id=finding.source_object_id,
        status=finding.status.value,
        state_revision=finding.state_revision,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
        last_evaluated_horizon=finding.last_evaluated_horizon,
        occurrence_count=finding.occurrence_count,
        reopen_count=finding.reopen_count,
    )


def _finding_to_domain(model: TimelinessFindingORM) -> TimelinessFinding:
    return TimelinessFinding(
        finding_id=model.finding_id,
        tenant_id=model.tenant_id,
        policy_id=model.policy_id,
        finding_type=TimelinessFindingType(model.finding_type),
        source_object_id=model.source_object_id,
        status=TimelinessFindingStatus(model.status),
        state_revision=model.state_revision,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
        last_evaluated_horizon=model.last_evaluated_horizon,
        occurrence_count=model.occurrence_count,
        reopen_count=model.reopen_count,
    )
