"""OQI `QualityFinding` -- the universal, dimension-neutral current-state
truth for one governed quality condition on one governed subject (CDD-039
§27-§30). Truth state is exactly OPEN/RESOLVED (§27); `apply_transition`
implements CDD-039 §30's exhaustive six-row transition table as a pure
function over immutable `QualityFinding` values -- it never mutates a
Finding in place, it returns the next state.

Counter semantics not given an exact algorithm by CDD-039 itself are frozen
here, consistently, as: `occurrence_count` increments on every transition
into OPEN (first violation *and* every reopen -- i.e. every time the
condition is newly registered as violated), never on remaining OPEN or on
any SATISFIED outcome; `last_seen_at` updates only on VIOLATED evaluations
(the timestamp the problem was last observed present); `last_evaluated_horizon`
updates on every authoritative evaluation regardless of outcome (the
timestamp the Finding was last evaluated at all). `state_revision`
increments on every authoritative evaluation that touches an existing or
newly-created Finding row -- including OPEN->OPEN and RESOLVED->RESOLVED --
per CDD-039 §24/§26's "every successful authoritative CURRENT_STATE
evaluation applied to that Finding lineage"."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.oqi.evaluation import (
    EvaluationOutcome,
    EvaluationSubject,
    canonical_subject_identity,
    derive_quality_finding_id,
)
from app.domain.oqi.quality_rule import QualityFindingType
from app.domain.shared.exceptions import ValidationException

_MAX_CONDITION_ID_LENGTH = 200


class QualityFindingStatus(StrEnum):
    """CDD-039 §27: exactly these two, closed. No RECURRING, SUPERSEDED,
    ACKNOWLEDGED, or REMEDIATING."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True, slots=True)
class QualityFinding:
    finding_id: UUID
    tenant_id: str
    quality_condition_id: str
    subject: EvaluationSubject
    finding_type: QualityFindingType
    status: QualityFindingStatus
    state_revision: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_evaluated_horizon: datetime
    occurrence_count: int
    reopen_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.quality_condition_id, str) or not (
            1 <= len(self.quality_condition_id) <= _MAX_CONDITION_ID_LENGTH
        ):
            raise ValidationException("quality_condition_id must be non-empty bounded text")
        if not isinstance(self.subject, EvaluationSubject):
            raise ValidationException("subject must be an EvaluationSubject")
        if not isinstance(self.finding_type, QualityFindingType):
            raise ValidationException("finding_type must be a QualityFindingType")
        if not isinstance(self.status, QualityFindingStatus):
            raise ValidationException("status must be a QualityFindingStatus")
        if (
            not isinstance(self.state_revision, int)
            or isinstance(self.state_revision, bool)
            or self.state_revision < 1
        ):
            raise ValidationException("state_revision must be a positive integer")
        for label, value in (
            ("first_seen_at", self.first_seen_at),
            ("last_seen_at", self.last_seen_at),
            ("last_evaluated_horizon", self.last_evaluated_horizon),
        ):
            if value is None or value.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")
        if (
            not isinstance(self.occurrence_count, int)
            or isinstance(self.occurrence_count, bool)
            or self.occurrence_count < 1
        ):
            raise ValidationException("occurrence_count must be a positive integer")
        if (
            not isinstance(self.reopen_count, int)
            or isinstance(self.reopen_count, bool)
            or self.reopen_count < 0
        ):
            raise ValidationException("reopen_count must be a non-negative integer")
        if self.reopen_count + 1 > self.occurrence_count:
            raise ValidationException("reopen_count cannot exceed occurrence_count - 1")

        expected_id = derive_quality_finding_id(
            tenant_id=self.tenant_id,
            quality_condition_id=self.quality_condition_id,
            subject_type=self.subject.subject_type,
            subject_identity=canonical_subject_identity(self.subject),
        )
        if self.finding_id != expected_id:
            raise ValidationException(
                "finding_id is inconsistent with its own governed semantic identity inputs"
            )


def apply_transition(
    *,
    existing: QualityFinding | None,
    outcome: EvaluationOutcome,
    evaluation_horizon: datetime,
    tenant_id: str,
    quality_condition_id: str,
    subject: EvaluationSubject,
    finding_type: QualityFindingType,
) -> QualityFinding | None:
    """CDD-039 §30's exhaustive transition table, as a pure function.
    Returns `None` exactly for the "No Finding + SATISFIED -> no Finding"
    case; every other case returns the next immutable `QualityFinding`
    value. If `existing` is provided, its identity fields must match the
    caller-supplied identity arguments (defensive consistency check)."""
    if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")

    finding_id = derive_quality_finding_id(
        tenant_id=tenant_id,
        quality_condition_id=quality_condition_id,
        subject_type=subject.subject_type,
        subject_identity=canonical_subject_identity(subject),
    )
    if existing is not None and existing.finding_id != finding_id:
        raise ValidationException(
            "existing Finding identity does not match the supplied identity arguments"
        )

    if existing is None:
        if outcome is EvaluationOutcome.SATISFIED:
            return None
        # No Finding + VIOLATED -> create OPEN
        return QualityFinding(
            finding_id=finding_id,
            tenant_id=tenant_id,
            quality_condition_id=quality_condition_id,
            subject=subject,
            finding_type=finding_type,
            status=QualityFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=evaluation_horizon,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
            occurrence_count=1,
            reopen_count=0,
        )

    if existing.status is QualityFindingStatus.OPEN and outcome is EvaluationOutcome.VIOLATED:
        # OPEN + VIOLATED -> remain OPEN
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
        )

    if existing.status is QualityFindingStatus.OPEN and outcome is EvaluationOutcome.SATISFIED:
        # OPEN + SATISFIED -> RESOLVED
        return replace(
            existing,
            status=QualityFindingStatus.RESOLVED,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
        )

    if existing.status is QualityFindingStatus.RESOLVED and outcome is EvaluationOutcome.SATISFIED:
        # RESOLVED + SATISFIED -> remain RESOLVED
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
        )

    # RESOLVED + VIOLATED -> OPEN; reopen_count += 1
    return replace(
        existing,
        status=QualityFindingStatus.OPEN,
        state_revision=existing.state_revision + 1,
        last_seen_at=evaluation_horizon,
        last_evaluated_horizon=evaluation_horizon,
        occurrence_count=existing.occurrence_count + 1,
        reopen_count=existing.reopen_count + 1,
    )
