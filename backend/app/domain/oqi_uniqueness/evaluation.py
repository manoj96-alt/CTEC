"""OQI-H6 Governed EnterpriseEntity Uniqueness (CDD-084 §18-§25, §29):
evaluates, per `EnterpriseEntity`, whether its governed `canonical_name()`
blocking bucket (CDD-084 §16) contains any other same-tenant, same-
`entity_type_id` entity -- and, per canonical pair, whether a
`DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE` Finding should open, stay open,
reopen, or close (CDD-084 §25's exact four-branch transition, mirroring
`apply_timeliness_finding_transition`'s established shape).

Distinct OQI-family namespace (CDD-039 §20's own precedent, restated by
every subsequent OQI-H phase, CDD-051 §17-§18 most directly): Finding/
evaluation identity never collides with OQI1-6/H1-H5's own namespaces, even
adversarially."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.oqi_uniqueness.candidate import UniquenessAdjudicationAction
from app.domain.shared.exceptions import ValidationException

#: CDD-084 §24, refined per the established per-family dedicated-namespace
#: discipline (CDD-051 §17-§18's own `OQI_TIMELINESS_NAMESPACE` precedent,
#: CDD-050's `OQI_INTEGRITY_NAMESPACE`) -- distinct from `OQI_NAMESPACE` and
#: every other governed OQI namespace, so no cross-family identity
#: collision is possible even adversarially. CDD-084 §24's own formula
#: names the string material precisely (`"UNIQUENESS|DUPLICATE_ENTERPRISE_
#: ENTITY_CANDIDATE|..."`); this constant supplies a dedicated namespace
#: UUID to combine it with, consistent with every predecessor OQI-H phase's
#: own established practice rather than literally reusing `OQI_NAMESPACE`.
OQI_UNIQUENESS_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:uniqueness:v1")

_IDENTITY_ALGORITHM_VERSION = "OQI_UNIQUENESS_IDENTITY_V1"
_MAX_TENANT_ID_LENGTH = 200


class UniquenessOutcome(StrEnum):
    """CDD-084 §20: closed, exactly three -- reuses the Kleene-style
    SATISFIED/VIOLATED/NOT_EVALUABLE shape rather than inventing a fourth
    parallel vocabulary (CDD-046 §13's discriminator-discipline precedent,
    restated). `VIOLATED` means a governed duplicate candidate requiring
    adjudication exists -- never "duplicate proven" (CDD-084 §20)."""

    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class UniquenessNotEvaluableReason(StrEnum):
    """CDD-084 §20: closed, exactly one member in H6 v1. No ACTIVE-policy
    NOT_EVALUABLE case has no persisted row at all (§20) and therefore
    never carries this reason -- only a genuine, bounded, policy-governed
    attempt that could not honestly complete does."""

    BUCKET_EXCEEDED_CAP = "BUCKET_EXCEEDED_CAP"


class UniquenessFindingStatus(StrEnum):
    """Mirrors `TimelinessFindingStatus`'s exact closed shape."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


def _length_prefixed(value: str) -> str:
    """Self-delimiting encoding: UTF-8 byte length, never Python character
    count -- identical technique to every other OQI family's own private
    helper, redefined locally per the established per-family precedent of
    never importing another family's private symbols."""
    return f"{len(value.encode('utf-8'))}:{value}"


def uniqueness_finding_identity_material(
    *, tenant_id: str, member_a_id: UUID, member_b_id: UUID
) -> str:
    """CDD-084 §24: the exact Finding-identity material, deliberately
    excluding `policy_id`, `policy_version`, `matched_normalized_name`, and
    any adjudication timestamp -- a policy-version bump, or a steward
    decision, never creates a duplicate current Finding for the same
    semantic canonical pair. `member_a_id`/`member_b_id` must already be in
    canonical order (`member_a_id < member_b_id`, CDD-084 §12) -- this
    function does not itself canonicalize; callers use
    `app.domain.oqi_uniqueness.candidate.canonicalize_pair` first."""
    if not member_a_id < member_b_id:
        raise ValidationException(
            "member_a_id must be strictly less than member_b_id (CDD-084 §12) -- "
            "canonicalize the pair before deriving identity"
        )
    return (
        _length_prefixed(_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(tenant_id)
        + _length_prefixed("DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE")
        + _length_prefixed(str(member_a_id))
        + _length_prefixed(str(member_b_id))
    )


def derive_uniqueness_finding_id(*, tenant_id: str, member_a_id: UUID, member_b_id: UUID) -> UUID:
    return uuid5(
        OQI_UNIQUENESS_NAMESPACE,
        uniqueness_finding_identity_material(
            tenant_id=tenant_id, member_a_id=member_a_id, member_b_id=member_b_id
        ),
    )


def derive_uniqueness_evaluation_id(
    *,
    tenant_id: str,
    policy_id: UUID,
    policy_version: int,
    enterprise_entity_id: UUID,
    outcome: UniquenessOutcome,
    candidate_count: int,
    not_evaluable_reason: UniquenessNotEvaluableReason | None,
) -> UUID:
    """CDD-084 §19-§20: evaluation-row identity folds in the consulted
    policy version and the exact logical result (outcome, candidate_count,
    not_evaluable_reason) -- a repeated run producing the identical result
    converges to the same row (idempotent replay, U10); a materially
    different result (e.g. a new candidate appeared, or the bucket newly
    exceeded the cap) always produces a new row. Mirrors
    `derive_timeliness_evaluation_id`'s content-derived-identity discipline,
    adapted from a caller-supplied `evaluation_horizon` (a concept
    Uniqueness has no equivalent of -- its "as of" state is the current
    bucket contents, not a point in time) to the evaluation's own logical
    result."""
    material = (
        _length_prefixed(_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(tenant_id)
        + _length_prefixed(str(policy_id))
        + _length_prefixed(str(policy_version))
        + _length_prefixed(str(enterprise_entity_id))
        + _length_prefixed(outcome.value)
        + _length_prefixed(str(candidate_count))
        + _length_prefixed(not_evaluable_reason.value if not_evaluable_reason else "")
    )
    return uuid5(OQI_UNIQUENESS_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class UniquenessEvaluation:
    """CDD-084 §19-§20: the immutable, append-only Uniqueness evaluation
    ledger record -- one row per `(policy version, EnterpriseEntity)`
    logical result. Persisted even when `candidate_count == 0`
    (`SATISFIED`), so H1 Coverage can honestly distinguish "searched
    successfully and clean" from "never evaluated" (CDD-084 §7, §28)."""

    evaluation_id: UUID
    tenant_id: str
    policy_id: UUID
    policy_version: int
    enterprise_entity_id: UUID
    outcome: UniquenessOutcome
    not_evaluable_reason: UniquenessNotEvaluableReason | None
    candidate_count: int
    evaluated_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.policy_id, UUID):
            raise ValidationException("policy_id must be a UUID")
        if (
            not isinstance(self.policy_version, int)
            or isinstance(self.policy_version, bool)
            or self.policy_version < 1
        ):
            raise ValidationException("policy_version must be a positive integer")
        if not isinstance(self.enterprise_entity_id, UUID):
            raise ValidationException("enterprise_entity_id must be a UUID")
        if not isinstance(self.outcome, UniquenessOutcome):
            raise ValidationException("outcome must be a UniquenessOutcome")
        if self.outcome is UniquenessOutcome.NOT_EVALUABLE and self.not_evaluable_reason is None:
            raise ValidationException("NOT_EVALUABLE outcome requires not_evaluable_reason")
        if (
            self.outcome is not UniquenessOutcome.NOT_EVALUABLE
            and self.not_evaluable_reason is not None
        ):
            raise ValidationException(
                "not_evaluable_reason must be None unless outcome is NOT_EVALUABLE"
            )
        if not isinstance(self.not_evaluable_reason, (UniquenessNotEvaluableReason, type(None))):
            raise ValidationException(
                "not_evaluable_reason must be None or a UniquenessNotEvaluableReason"
            )
        if not isinstance(self.candidate_count, int) or isinstance(self.candidate_count, bool):
            raise ValidationException("candidate_count must be an integer")
        if self.candidate_count < 0:
            raise ValidationException("candidate_count must be non-negative")
        if self.outcome is UniquenessOutcome.SATISFIED and self.candidate_count != 0:
            raise ValidationException("SATISFIED requires candidate_count == 0")
        if self.outcome is UniquenessOutcome.VIOLATED and self.candidate_count < 1:
            raise ValidationException("VIOLATED requires candidate_count >= 1")
        if self.outcome is UniquenessOutcome.NOT_EVALUABLE and self.candidate_count != 0:
            raise ValidationException("NOT_EVALUABLE requires candidate_count == 0")
        if self.evaluated_on is None or self.evaluated_on.tzinfo is None:
            raise ValidationException("evaluated_on must include a timezone")

        expected_id = derive_uniqueness_evaluation_id(
            tenant_id=self.tenant_id,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            enterprise_entity_id=self.enterprise_entity_id,
            outcome=self.outcome,
            candidate_count=self.candidate_count,
            not_evaluable_reason=self.not_evaluable_reason,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


@dataclass(frozen=True, slots=True)
class UniquenessFinding:
    finding_id: UUID
    tenant_id: str
    candidate_id: UUID
    member_a_id: UUID
    member_b_id: UUID
    status: UniquenessFindingStatus
    state_revision: int
    first_seen_at: datetime
    last_seen_at: datetime
    occurrence_count: int
    reopen_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.candidate_id, UUID):
            raise ValidationException("candidate_id must be a UUID")
        if not isinstance(self.member_a_id, UUID) or not isinstance(self.member_b_id, UUID):
            raise ValidationException("member_a_id and member_b_id must be UUIDs")
        if not self.member_a_id < self.member_b_id:
            raise ValidationException("member_a_id must be strictly less than member_b_id")
        if not isinstance(self.status, UniquenessFindingStatus):
            raise ValidationException("status must be a UniquenessFindingStatus")
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

        expected_id = derive_uniqueness_finding_id(
            tenant_id=self.tenant_id, member_a_id=self.member_a_id, member_b_id=self.member_b_id
        )
        if self.finding_id != expected_id:
            raise ValidationException(
                "finding_id is inconsistent with its own governed semantic identity inputs"
            )


def apply_uniqueness_finding_transition(
    *,
    existing: UniquenessFinding | None,
    candidate_qualifies: bool,
    candidate_id: UUID,
    moment: datetime,
    tenant_id: str,
    member_a_id: UUID,
    member_b_id: UUID,
) -> UniquenessFinding | None:
    """CDD-084 §25: the evaluation-driven half of the Finding lifecycle --
    identical four-branch transition shape to
    `apply_timeliness_finding_transition` (CDD-051 §19), with
    `candidate_qualifies` (a currently-qualifying, non-rejected candidate
    exists for this pair) standing in for `EvaluationOutcome.VIOLATED`, and
    "no longer qualifies" (name diverged, or the only qualifying candidate
    was superseded) standing in for `SATISFIED`. Steward adjudication
    (`REJECT_NOT_DUPLICATE`/`CONFIRM_DUPLICATE`) is handled by the
    independent `apply_uniqueness_adjudication_transition` below -- a
    steward acts immediately, never waiting for the next evaluation
    sweep."""
    if moment is None or moment.tzinfo is None:
        raise ValidationException("moment must include a timezone")

    finding_id = derive_uniqueness_finding_id(
        tenant_id=tenant_id, member_a_id=member_a_id, member_b_id=member_b_id
    )
    if existing is not None and existing.finding_id != finding_id:
        raise ValidationException(
            "existing Finding identity does not match the supplied pair identity"
        )

    if existing is None:
        if not candidate_qualifies:
            return None
        return UniquenessFinding(
            finding_id=finding_id,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            member_a_id=member_a_id,
            member_b_id=member_b_id,
            status=UniquenessFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=moment,
            last_seen_at=moment,
            occurrence_count=1,
            reopen_count=0,
        )

    if existing.status is UniquenessFindingStatus.OPEN and candidate_qualifies:
        return replace(
            existing,
            candidate_id=candidate_id,
            state_revision=existing.state_revision + 1,
            last_seen_at=moment,
        )

    if existing.status is UniquenessFindingStatus.OPEN and not candidate_qualifies:
        return replace(
            existing,
            status=UniquenessFindingStatus.RESOLVED,
            state_revision=existing.state_revision + 1,
            last_seen_at=moment,
        )

    if existing.status is UniquenessFindingStatus.RESOLVED and not candidate_qualifies:
        return replace(existing, state_revision=existing.state_revision + 1, last_seen_at=moment)

    # RESOLVED and candidate_qualifies -- reopen.
    return replace(
        existing,
        candidate_id=candidate_id,
        status=UniquenessFindingStatus.OPEN,
        state_revision=existing.state_revision + 1,
        last_seen_at=moment,
        occurrence_count=existing.occurrence_count + 1,
        reopen_count=existing.reopen_count + 1,
    )


def apply_uniqueness_adjudication_transition(
    *,
    existing: UniquenessFinding,
    action: UniquenessAdjudicationAction,
    moment: datetime,
) -> UniquenessFinding:
    """CDD-084 §21, §25, §28: the adjudication-driven half of the Finding
    lifecycle. `REJECT_NOT_DUPLICATE` closes the Finding immediately
    (`CONFIRMED DUPLICATE ≠ RESOLVED DUPLICATE REPRESENTATION` does not
    apply here -- rejection IS a governed determination that the
    representation is not a duplicate, closing the condition honestly).
    `CONFIRM_DUPLICATE` never changes `status` -- the Finding remains OPEN
    (CDD-084 §25/§28: confirmation is governed human evidence, never
    remediation, never merge; the underlying duplicate representation still
    exists until independently corrected and re-evaluated) -- but the
    adjudication is still a real domain event, so `state_revision`/
    `last_seen_at` advance, mirroring `apply_timeliness_finding_
    transition`'s own "reaffirmed, no status change" branches exactly."""
    if moment is None or moment.tzinfo is None:
        raise ValidationException("moment must include a timezone")
    if not isinstance(action, UniquenessAdjudicationAction):
        raise ValidationException("action must be a UniquenessAdjudicationAction")

    if action is UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE:
        if existing.status is UniquenessFindingStatus.RESOLVED:
            return replace(
                existing, state_revision=existing.state_revision + 1, last_seen_at=moment
            )
        return replace(
            existing,
            status=UniquenessFindingStatus.RESOLVED,
            state_revision=existing.state_revision + 1,
            last_seen_at=moment,
        )

    # CONFIRM_DUPLICATE: status never changes here (CDD-084 §28).
    return replace(existing, state_revision=existing.state_revision + 1, last_seen_at=moment)
