"""OQI3 `BusinessRuleFinding` -- the stable, current-state truth for one
governed business condition on one governed `SINGLE_RECORD` subject
(CDD-041 §14-§15). `status` is exactly `OPEN | RESOLVED` (reusing OQI1's
`QualityFindingStatus` directly, mirroring OQI2's own precedent of reusing
it rather than declaring a redundant identical enum) -- `resolution_basis`
is the orthogonal, OQI3-specific dimension this document adds: an explicit
`SATISFIED | NOT_APPLICABLE` column, `NULL` while `status=OPEN`, non-`NULL`
while `status=RESOLVED`.

`apply_business_rule_finding_transition` mechanically extends OQI1's exact
transition discipline (`app.domain.oqi.finding.apply_transition`) and
reproduces it here rather than reusing it directly, since the subject shape
differs (`subject_type`/`subject_identity` vs. `EvaluationSubject`) --
exactly the same non-reuse precedent OQI2's `apply_correspondence_finding_
transition` already established for this repository. Counter/timestamp
semantics are byte-identical to OQI1's own frozen discipline (CDD-039 §24-
§30, restated in `app.domain.oqi.finding`'s own module docstring):
`occurrence_count` increments only on a transition *into* OPEN (creation and
every reopen); `reopen_count` increments only on RESOLVED->VIOLATED;
`state_revision` increments on every transition that touches an existing or
newly-created Finding row, regardless of outcome; `first_seen_at` is set once
at creation and never touched again; `last_seen_at` updates only on VIOLATED
transitions (CDD-041 §14's own explicit "last_seen_at updated" annotation on
exactly those two arms, and no others). `BusinessRuleFinding` has no
`last_evaluated_horizon` column (unlike OQI1/OQI2's Finding) -- CDD-041's
Artifact Authorization schema (§5) does not define one, and §14's transition
table never mentions one; `state_revision` alone is sufficient to detect that
a Finding was touched by a given evaluation.

`BusinessRule` retirement and `NOT_EVALUABLE` never call this function at
all -- both are absolute Finding-mutation firewalls enforced entirely by the
caller (OQI3-I3's application service), never by this module."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid5

from app.domain.oqi.evaluation import _length_prefixed, canonical_form
from app.domain.oqi.finding import QualityFindingStatus
from app.domain.oqi_business_rule.evaluation import (
    SUBJECT_TYPE_SINGLE_RECORD,
    EvaluationOutcome,
)
from app.domain.oqi_business_rule.rule import OQI_BUSINESS_RULE_NAMESPACE
from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200
_MAX_CONDITION_ID_LENGTH = 200
_MAX_SUBJECT_IDENTITY_LENGTH = 1000

_FINDING_IDENTITY_ALGORITHM_VERSION = "OQI_BUSINESS_RULE_FINDING_IDENTITY_V1"


class ResolutionBasis(StrEnum):
    """CDD-041 §14: exactly these two closed values. Never conflated --
    `SATISFIED` means the governed expectation is currently met;
    `NOT_APPLICABLE` means the expectation currently does not apply. Neither
    implies the other; a dashboard/explanation layer can always distinguish
    them from persisted state alone (CDD-041 §14, §20)."""

    SATISFIED = "SATISFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def business_rule_finding_identity_material(
    *, tenant_id: str, business_condition_id: str, subject_type: str, subject_identity: str
) -> str:
    """CDD-041 §15's exact Finding-identity pre-hash material, exposed for
    reuse verbatim as the PostgreSQL advisory-lock `:identity` text input
    (CDD-041 §21, seed=3) -- mirroring OQI1/OQI2's `finding_identity_material`
    discipline exactly, so the lock's authority domain can never drift from
    the Finding identity domain it must match."""
    return (
        _length_prefixed(_FINDING_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(business_condition_id)
        + _length_prefixed(subject_type)
        + _length_prefixed(subject_identity)
    )


def derive_business_rule_finding_id(
    *, tenant_id: str, business_condition_id: str, subject_type: str, subject_identity: str
) -> UUID:
    """CDD-041 §15's exact deterministic Finding identity formula. Excludes
    rule version, evaluation horizon, evidence IDs, observations,
    resolution_basis, and current values -- this preserves condition
    continuity across executable rule versions (CDD-041 §30)."""
    material = business_rule_finding_identity_material(
        tenant_id=tenant_id,
        business_condition_id=business_condition_id,
        subject_type=subject_type,
        subject_identity=subject_identity,
    )
    return uuid5(OQI_BUSINESS_RULE_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class BusinessRuleFinding:
    finding_id: UUID
    tenant_id: str
    business_condition_id: str
    subject_type: str
    subject_identity: str
    status: QualityFindingStatus
    resolution_basis: ResolutionBasis | None
    latest_evaluation_id: UUID
    occurrence_count: int
    reopen_count: int
    state_revision: int
    first_seen_at: datetime
    last_seen_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.business_condition_id, str) or not (
            1 <= len(self.business_condition_id) <= _MAX_CONDITION_ID_LENGTH
        ):
            raise ValidationException("business_condition_id must be non-empty bounded text")
        if self.subject_type != SUBJECT_TYPE_SINGLE_RECORD:
            raise ValidationException(f"subject_type must be {SUBJECT_TYPE_SINGLE_RECORD!r}")
        if not isinstance(self.subject_identity, str) or not (
            1 <= len(self.subject_identity) <= _MAX_SUBJECT_IDENTITY_LENGTH
        ):
            raise ValidationException("subject_identity must be non-empty bounded text")
        if not isinstance(self.status, QualityFindingStatus):
            raise ValidationException("status must be a QualityFindingStatus")
        if self.status is QualityFindingStatus.OPEN and self.resolution_basis is not None:
            raise ValidationException("OPEN findings must not carry a resolution_basis")
        if self.status is QualityFindingStatus.RESOLVED and self.resolution_basis is None:
            raise ValidationException("RESOLVED findings must carry a resolution_basis")
        if self.resolution_basis is not None and not isinstance(
            self.resolution_basis, ResolutionBasis
        ):
            raise ValidationException("resolution_basis must be a ResolutionBasis or None")
        if not isinstance(self.latest_evaluation_id, UUID):
            raise ValidationException("latest_evaluation_id must be a UUID")
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
        if (
            not isinstance(self.state_revision, int)
            or isinstance(self.state_revision, bool)
            or self.state_revision < 1
        ):
            raise ValidationException("state_revision must be a positive integer")
        for label, value in (
            ("first_seen_at", self.first_seen_at),
            ("last_seen_at", self.last_seen_at),
        ):
            if value is None or value.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")

        expected_id = derive_business_rule_finding_id(
            tenant_id=self.tenant_id,
            business_condition_id=self.business_condition_id,
            subject_type=self.subject_type,
            subject_identity=self.subject_identity,
        )
        if self.finding_id != expected_id:
            raise ValidationException(
                "finding_id is inconsistent with its own governed semantic identity inputs"
            )


def apply_business_rule_finding_transition(
    *,
    existing: BusinessRuleFinding | None,
    outcome: EvaluationOutcome,
    evaluation_id: UUID,
    evaluation_horizon: datetime,
    tenant_id: str,
    business_condition_id: str,
    subject_type: str,
    subject_identity: str,
) -> BusinessRuleFinding | None:
    """CDD-041 §14's exact transition table, as a pure function. Callers
    MUST NOT invoke this for `NOT_EVALUABLE` (which has no `EvaluationOutcome`
    member at all -- CDD-041 §13) or for HISTORICAL evaluations or rule
    retirement -- those are absolute non-mutation firewalls the caller
    enforces before ever reaching this function. Returns `None` exactly for
    the "no Finding + SATISFIED/NOT_APPLICABLE -> no Finding created" cases."""
    if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")
    if not isinstance(evaluation_id, UUID):
        raise ValidationException("evaluation_id must be a UUID")

    finding_id = derive_business_rule_finding_id(
        tenant_id=tenant_id,
        business_condition_id=business_condition_id,
        subject_type=subject_type,
        subject_identity=subject_identity,
    )
    if existing is not None and existing.finding_id != finding_id:
        raise ValidationException(
            "existing Finding identity does not match the supplied identity arguments"
        )

    if existing is None:
        if outcome in (EvaluationOutcome.SATISFIED, EvaluationOutcome.NOT_APPLICABLE):
            return None
        # No Finding + VIOLATED -> create OPEN
        return BusinessRuleFinding(
            finding_id=finding_id,
            tenant_id=tenant_id,
            business_condition_id=business_condition_id,
            subject_type=subject_type,
            subject_identity=subject_identity,
            status=QualityFindingStatus.OPEN,
            resolution_basis=None,
            latest_evaluation_id=evaluation_id,
            occurrence_count=1,
            reopen_count=0,
            state_revision=1,
            first_seen_at=evaluation_horizon,
            last_seen_at=evaluation_horizon,
        )

    if existing.status is QualityFindingStatus.OPEN and outcome is EvaluationOutcome.VIOLATED:
        # OPEN + VIOLATED -> remain OPEN
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_seen_at=evaluation_horizon,
            latest_evaluation_id=evaluation_id,
        )

    if existing.status is QualityFindingStatus.OPEN and outcome is EvaluationOutcome.SATISFIED:
        # OPEN + SATISFIED -> RESOLVED, resolution_basis=SATISFIED
        return replace(
            existing,
            status=QualityFindingStatus.RESOLVED,
            resolution_basis=ResolutionBasis.SATISFIED,
            state_revision=existing.state_revision + 1,
            latest_evaluation_id=evaluation_id,
        )

    if existing.status is QualityFindingStatus.OPEN and outcome is EvaluationOutcome.NOT_APPLICABLE:
        # OPEN + NOT_APPLICABLE -> RESOLVED, resolution_basis=NOT_APPLICABLE
        return replace(
            existing,
            status=QualityFindingStatus.RESOLVED,
            resolution_basis=ResolutionBasis.NOT_APPLICABLE,
            state_revision=existing.state_revision + 1,
            latest_evaluation_id=evaluation_id,
        )

    if existing.status is QualityFindingStatus.RESOLVED and outcome is EvaluationOutcome.SATISFIED:
        # RESOLVED (any basis) + SATISFIED -> remain RESOLVED, resolution_basis=SATISFIED
        return replace(
            existing,
            resolution_basis=ResolutionBasis.SATISFIED,
            state_revision=existing.state_revision + 1,
            latest_evaluation_id=evaluation_id,
        )

    if (
        existing.status is QualityFindingStatus.RESOLVED
        and outcome is EvaluationOutcome.NOT_APPLICABLE
    ):
        # RESOLVED (any basis) + NOT_APPLICABLE -> remain RESOLVED, resolution_basis=NOT_APPLICABLE
        return replace(
            existing,
            resolution_basis=ResolutionBasis.NOT_APPLICABLE,
            state_revision=existing.state_revision + 1,
            latest_evaluation_id=evaluation_id,
        )

    # RESOLVED (any basis) + VIOLATED -> OPEN; reopen_count += 1
    return replace(
        existing,
        status=QualityFindingStatus.OPEN,
        resolution_basis=None,
        state_revision=existing.state_revision + 1,
        last_seen_at=evaluation_horizon,
        occurrence_count=existing.occurrence_count + 1,
        reopen_count=existing.reopen_count + 1,
        latest_evaluation_id=evaluation_id,
    )
