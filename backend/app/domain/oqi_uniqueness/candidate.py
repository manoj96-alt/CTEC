"""OQI-H6 governed Uniqueness candidate + steward adjudication (CDD-084
§12-§13, §18, §21, §23). A `UniquenessCandidate` is an immutable, persisted
fact: this canonical `EnterpriseEntity` pair qualified under this policy
version's blocking rule (CDD-084 §18 -- exact `canonical_name()` equality
within the same tenant/entity_type, bounded bucket). Existence alone is
evidence, never itself a duplicate fact (`DUPLICATE CANDIDATE ≠ DUPLICATE
FACT`).

Pair canonicalization (CDD-084 §12) is enforced HERE, at construction --
`member_a_id < member_b_id` under Python's own UUID ordering (identical
total order to PostgreSQL's native `uuid` comparison operator, CDD-084 §12)
-- so no caller can ever construct a `UniquenessCandidate` in the wrong
orientation. The database's own `CHECK (member_a_id < member_b_id)`
constraint (AA §7.3) is the second, independent, structural enforcement
layer -- Python canonicalizes, PostgreSQL enforces (CDD-084 §12, restated)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200
_MAX_ACTOR_ID_LENGTH = 200
_MAX_RATIONALE_LENGTH = 2000
_MAX_NORMALIZED_NAME_LENGTH = 200


def canonicalize_pair(entity_a_id: UUID, entity_b_id: UUID) -> tuple[UUID, UUID]:
    """CDD-084 §12: the single, shared canonicalization function every
    candidate-generation call site must use -- never ad hoc sorting at the
    call site. Raises on a self-pair; a self-pair is never a legitimate
    candidate (CDD-084 §12's `A,A` prohibition)."""
    if entity_a_id == entity_b_id:
        raise ValidationException("a candidate pair cannot compare an EnterpriseEntity to itself")
    return (entity_a_id, entity_b_id) if entity_a_id < entity_b_id else (entity_b_id, entity_a_id)


@dataclass(frozen=True, slots=True)
class UniquenessCandidate:
    """CDD-084 §18, §23: one qualifying candidate pair under one policy
    version. `matched_normalized_name` is the exact evidentiary basis
    (CDD-084 §18) -- the shared `canonical_name(enterprise_entity_name)`
    value both members share, never an unexplained score (`MATCH SCORE ≠
    DUPLICATE FACT`)."""

    candidate_id: UUID
    tenant_id: str
    member_a_id: UUID
    member_b_id: UUID
    policy_id: UUID
    policy_version: int
    matched_normalized_name: str
    created_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, UUID):
            raise ValidationException("candidate_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.member_a_id, UUID) or not isinstance(self.member_b_id, UUID):
            raise ValidationException("member_a_id and member_b_id must be UUIDs")
        if not self.member_a_id < self.member_b_id:
            raise ValidationException(
                "member_a_id must be strictly less than member_b_id (CDD-084 §12 canonical "
                "pair ordering) -- use canonicalize_pair() to construct a candidate"
            )
        if not isinstance(self.policy_id, UUID):
            raise ValidationException("policy_id must be a UUID")
        if (
            not isinstance(self.policy_version, int)
            or isinstance(self.policy_version, bool)
            or self.policy_version < 1
        ):
            raise ValidationException("policy_version must be a positive integer")
        if not isinstance(self.matched_normalized_name, str) or not (
            1 <= len(self.matched_normalized_name) <= _MAX_NORMALIZED_NAME_LENGTH
        ):
            raise ValidationException("matched_normalized_name must be non-empty bounded text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


class UniquenessAdjudicationAction(StrEnum):
    """CDD-084 §21 (PO-2, binding): closed, exactly these two. No MERGE, no
    DEACTIVATE -- H6 detects and routes to steward adjudication; it never
    mutates EnterpriseEntity identity by any action defined here."""

    REJECT_NOT_DUPLICATE = "REJECT_NOT_DUPLICATE"
    CONFIRM_DUPLICATE = "CONFIRM_DUPLICATE"


@dataclass(frozen=True, slots=True)
class UniquenessAdjudication:
    """CDD-084 §21: one append-only steward decision on one candidate.
    Never updated, never deleted -- the current disposition of a candidate
    is always derived from the latest adjudication row for it (CDD-084
    §21), mirroring Entity Resolution's own append-only
    `EnterpriseEntityResolutionRecord` discipline."""

    adjudication_id: UUID
    tenant_id: str
    candidate_id: UUID
    action: UniquenessAdjudicationAction
    actor_id: str
    rationale: str
    decided_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.adjudication_id, UUID):
            raise ValidationException("adjudication_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.candidate_id, UUID):
            raise ValidationException("candidate_id must be a UUID")
        if not isinstance(self.action, UniquenessAdjudicationAction):
            raise ValidationException("action must be a UniquenessAdjudicationAction")
        if not isinstance(self.actor_id, str) or not (
            1 <= len(self.actor_id) <= _MAX_ACTOR_ID_LENGTH
        ):
            raise ValidationException("actor_id must be non-empty bounded text")
        if not isinstance(self.rationale, str) or not (
            1 <= len(self.rationale) <= _MAX_RATIONALE_LENGTH
        ):
            raise ValidationException("rationale must be non-empty bounded text")
        if self.decided_on is None or self.decided_on.tzinfo is None:
            raise ValidationException("decided_on must include a timezone")
