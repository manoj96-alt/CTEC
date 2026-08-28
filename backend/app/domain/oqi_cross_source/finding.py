"""OQI2 `QualityComparisonFinding` -- the current-state truth for one
governed cross-source quality condition on one governed comparison subject
(CDD-040 §31-§33; N-Source Finding Representation Amendment §2, §7, §14).
Mechanically reproduces OQI1's exact six-row transition table
(`app.domain.oqi.finding.apply_transition`) rather than reusing it
directly, since the subject shape differs (`comparison_subject_id` vs.
`EvaluationSubject`) -- but semantically identical counter/status
discipline throughout. Additionally threads `latest_evaluation_id` on every
transition (CDD-040 §52, §61). A cross-source Finding owns only the
continuing OPEN/RESOLVED condition-state lineage -- it does NOT own a
single failure classification; that decomposed, possibly-plural fact now
lives on the Finding's `latest_evaluation_id`'s own
`ComparisonObservation` rows (amendment §2), decoupled from Finding
lifecycle (amendment §14): observation composition may freely change
while a Finding remains OPEN."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi.finding import QualityFindingStatus
from app.domain.oqi_cross_source.evaluation import derive_comparison_finding_id
from app.domain.shared.exceptions import ValidationException

_MAX_CONDITION_ID_LENGTH = 200


@dataclass(frozen=True, slots=True)
class QualityComparisonFinding:
    finding_id: UUID
    tenant_id: str
    quality_condition_id: str
    comparison_subject_id: UUID
    status: QualityFindingStatus
    state_revision: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_evaluated_horizon: datetime
    occurrence_count: int
    reopen_count: int
    latest_evaluation_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.quality_condition_id, str) or not (
            1 <= len(self.quality_condition_id) <= _MAX_CONDITION_ID_LENGTH
        ):
            raise ValidationException("quality_condition_id must be non-empty bounded text")
        if not isinstance(self.comparison_subject_id, UUID):
            raise ValidationException("comparison_subject_id must be a UUID")
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
        if not isinstance(self.latest_evaluation_id, UUID):
            raise ValidationException("latest_evaluation_id must be a UUID")

        expected_id = derive_comparison_finding_id(
            tenant_id=self.tenant_id,
            quality_condition_id=self.quality_condition_id,
            comparison_subject_id=self.comparison_subject_id,
        )
        if self.finding_id != expected_id:
            raise ValidationException(
                "finding_id is inconsistent with its own governed semantic identity inputs"
            )


def apply_correspondence_finding_transition(
    *,
    existing: QualityComparisonFinding | None,
    outcome: EvaluationOutcome,
    evaluation_horizon: datetime,
    tenant_id: str,
    quality_condition_id: str,
    comparison_subject_id: UUID,
    evaluation_id: UUID,
) -> QualityComparisonFinding | None:
    """CDD-040 §33, N-Source Finding Representation Amendment §14:
    mechanically reproduces CDD-039 §30's exhaustive six-row transition
    table, driven by `outcome` alone -- never by which observation(s)
    caused it. Returns `None` exactly for the "no Finding + SATISFIED ->
    no Finding" case."""
    if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")

    finding_id = derive_comparison_finding_id(
        tenant_id=tenant_id,
        quality_condition_id=quality_condition_id,
        comparison_subject_id=comparison_subject_id,
    )
    if existing is not None and existing.finding_id != finding_id:
        raise ValidationException(
            "existing Finding identity does not match the supplied identity arguments"
        )

    if existing is None:
        if outcome is EvaluationOutcome.SATISFIED:
            return None
        # No Finding + VIOLATED -> create OPEN
        return QualityComparisonFinding(
            finding_id=finding_id,
            tenant_id=tenant_id,
            quality_condition_id=quality_condition_id,
            comparison_subject_id=comparison_subject_id,
            status=QualityFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=evaluation_horizon,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
            occurrence_count=1,
            reopen_count=0,
            latest_evaluation_id=evaluation_id,
        )

    if existing.status is QualityFindingStatus.OPEN and outcome is EvaluationOutcome.VIOLATED:
        # OPEN + VIOLATED -> remain OPEN; observation composition may change.
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
            latest_evaluation_id=evaluation_id,
        )

    if existing.status is QualityFindingStatus.OPEN and outcome is EvaluationOutcome.SATISFIED:
        # OPEN + SATISFIED -> RESOLVED
        return replace(
            existing,
            status=QualityFindingStatus.RESOLVED,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
            latest_evaluation_id=evaluation_id,
        )

    if existing.status is QualityFindingStatus.RESOLVED and outcome is EvaluationOutcome.SATISFIED:
        # RESOLVED + SATISFIED -> remain RESOLVED
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
            latest_evaluation_id=evaluation_id,
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
        latest_evaluation_id=evaluation_id,
    )
