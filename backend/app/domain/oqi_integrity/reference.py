"""OQI-H4 Reference Integrity (CDD-050 §10.2, §14-§16, PO-H4-04): evaluates
one source reference observation (identified by `tenant_id + source_object_id
+ relationship_requirement_id`) against a persisted, governed Entity
Resolution `ResolutionOutcome` -- read-only, never invoking ER matching
itself (CDD-050 §10.2). Detects `ORPHAN_REFERENCE` only when the consulted
outcome is a genuine `ResolutionOutcome.UNRESOLVED` -- `POSSIBLE` and "no
outcome at all" are both `NOT_EVALUABLE`, never orphan (PO-H4-04).
`ResolutionOutcome.RESOLVED` is `SATISFIED` here -- it proves nothing about
whether the corresponding ontology relationship was ever materialized
(`RESOLVED REFERENCE != MATERIALIZED RELATIONSHIP`, CDD-050 crown invariant
11); Structural Integrity independently answers that question."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid5

from app.domain.identity_resolution.model import ResolutionOutcome
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi_integrity.structural import (
    OQI_INTEGRITY_NAMESPACE,
    IntegrityFindingStatus,
    IntegrityFindingType,
    _length_prefixed,
)
from app.domain.shared.exceptions import ValidationException

_IDENTITY_ALGORITHM_VERSION = "OQI_INTEGRITY_REFERENCE_IDENTITY_V1"
_MAX_TENANT_ID_LENGTH = 200

#: CDD-050 §10.2, PO-H4-04: the only two `ResolutionOutcome` values a
#: Reference Integrity evaluation row may ever persist. `POSSIBLE` and "no
#: outcome" both short-circuit to zero row before construction is attempted.
_PERSISTABLE_OUTCOMES = frozenset({ResolutionOutcome.RESOLVED, ResolutionOutcome.UNRESOLVED})


def reference_finding_identity_material(
    *, tenant_id: str, relationship_requirement_id: UUID, source_object_id: UUID
) -> str:
    """CDD-050 §15: excludes the consulted `ResolutionOutcome` record id,
    evaluation horizon, and outcome -- a fresh ER re-resolution never creates
    a duplicate current Finding for the same source-reference/requirement
    pair."""
    return (
        _length_prefixed(_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(tenant_id)
        + _length_prefixed(str(relationship_requirement_id))
        + _length_prefixed(str(source_object_id))
    )


def derive_reference_finding_id(
    *, tenant_id: str, relationship_requirement_id: UUID, source_object_id: UUID
) -> UUID:
    return uuid5(
        OQI_INTEGRITY_NAMESPACE,
        reference_finding_identity_material(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
        ),
    )


def derive_reference_evaluation_id(
    *,
    tenant_id: str,
    relationship_requirement_id: UUID,
    source_object_id: UUID,
    resolution_record_id: UUID,
    evaluation_horizon: datetime,
) -> UUID:
    if evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")
    material = (
        reference_finding_identity_material(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
        )
        + _length_prefixed(str(resolution_record_id))
        + _length_prefixed(evaluation_horizon.astimezone(UTC).isoformat())
    )
    return uuid5(OQI_INTEGRITY_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class ReferenceIntegrityEvaluation:
    """CDD-050 §12 table 5: the immutable, append-only Reference evaluation
    ledger record."""

    evaluation_id: UUID
    tenant_id: str
    relationship_requirement_id: UUID
    source_object_id: UUID
    resolution_record_id: UUID
    resolution_outcome: ResolutionOutcome
    outcome: EvaluationOutcome
    evaluation_horizon: datetime
    evaluated_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.relationship_requirement_id, UUID):
            raise ValidationException("relationship_requirement_id must be a UUID")
        if not isinstance(self.source_object_id, UUID):
            raise ValidationException("source_object_id must be a UUID")
        if not isinstance(self.resolution_record_id, UUID):
            raise ValidationException("resolution_record_id must be a UUID")
        if self.resolution_outcome not in _PERSISTABLE_OUTCOMES:
            raise ValidationException(
                "resolution_outcome must be RESOLVED or UNRESOLVED -- POSSIBLE and any other "
                "value are NOT_EVALUABLE and must never reach persistence (PO-H4-04)"
            )
        if not isinstance(self.outcome, EvaluationOutcome):
            raise ValidationException("outcome must be an EvaluationOutcome")
        if (self.resolution_outcome is ResolutionOutcome.RESOLVED) != (
            self.outcome is EvaluationOutcome.SATISFIED
        ):
            raise ValidationException(
                "outcome must be SATISFIED iff resolution_outcome is RESOLVED, VIOLATED iff "
                "UNRESOLVED"
            )
        if self.evaluation_horizon is None or self.evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")
        if self.evaluated_on is None or self.evaluated_on.tzinfo is None:
            raise ValidationException("evaluated_on must include a timezone")

        expected_id = derive_reference_evaluation_id(
            tenant_id=self.tenant_id,
            relationship_requirement_id=self.relationship_requirement_id,
            source_object_id=self.source_object_id,
            resolution_record_id=self.resolution_record_id,
            evaluation_horizon=self.evaluation_horizon,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


@dataclass(frozen=True, slots=True)
class ReferenceIntegrityFinding:
    finding_id: UUID
    tenant_id: str
    relationship_requirement_id: UUID
    source_object_id: UUID
    finding_type: IntegrityFindingType
    status: IntegrityFindingStatus
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
        if not isinstance(self.relationship_requirement_id, UUID):
            raise ValidationException("relationship_requirement_id must be a UUID")
        if not isinstance(self.source_object_id, UUID):
            raise ValidationException("source_object_id must be a UUID")
        if self.finding_type is not IntegrityFindingType.ORPHAN_REFERENCE:
            raise ValidationException(
                "ReferenceIntegrityFinding.finding_type must be ORPHAN_REFERENCE"
            )
        if not isinstance(self.status, IntegrityFindingStatus):
            raise ValidationException("status must be an IntegrityFindingStatus")
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

        expected_id = derive_reference_finding_id(
            tenant_id=self.tenant_id,
            relationship_requirement_id=self.relationship_requirement_id,
            source_object_id=self.source_object_id,
        )
        if self.finding_id != expected_id:
            raise ValidationException(
                "finding_id is inconsistent with its own governed semantic identity inputs"
            )


def apply_reference_finding_transition(
    *,
    existing: ReferenceIntegrityFinding | None,
    outcome: EvaluationOutcome,
    evaluation_horizon: datetime,
    tenant_id: str,
    relationship_requirement_id: UUID,
    source_object_id: UUID,
) -> ReferenceIntegrityFinding | None:
    """CDD-050 §16: identical transition-table shape to
    `apply_structural_finding_transition`/`apply_transition`. `NOT_EVALUABLE`
    (POSSIBLE, no outcome) never reaches this function."""
    if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")

    finding_id = derive_reference_finding_id(
        tenant_id=tenant_id,
        relationship_requirement_id=relationship_requirement_id,
        source_object_id=source_object_id,
    )
    if existing is not None and existing.finding_id != finding_id:
        raise ValidationException(
            "existing Finding identity does not match the supplied identity arguments"
        )

    if existing is None:
        if outcome is EvaluationOutcome.SATISFIED:
            return None
        return ReferenceIntegrityFinding(
            finding_id=finding_id,
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
            finding_type=IntegrityFindingType.ORPHAN_REFERENCE,
            status=IntegrityFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=evaluation_horizon,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
            occurrence_count=1,
            reopen_count=0,
        )

    if existing.status is IntegrityFindingStatus.OPEN and outcome is EvaluationOutcome.VIOLATED:
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
        )

    if existing.status is IntegrityFindingStatus.OPEN and outcome is EvaluationOutcome.SATISFIED:
        return replace(
            existing,
            status=IntegrityFindingStatus.RESOLVED,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
        )

    if (
        existing.status is IntegrityFindingStatus.RESOLVED
        and outcome is EvaluationOutcome.SATISFIED
    ):
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
        )

    return replace(
        existing,
        status=IntegrityFindingStatus.OPEN,
        state_revision=existing.state_revision + 1,
        last_seen_at=evaluation_horizon,
        last_evaluated_horizon=evaluation_horizon,
        occurrence_count=existing.occurrence_count + 1,
        reopen_count=existing.reopen_count + 1,
    )
