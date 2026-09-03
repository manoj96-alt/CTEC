"""OQI-H4 governed relationship-cardinality extension (CDD-050 §7): a
shared-platform, versioned policy anchored to the existing, unmodified
`RelationshipRequirement` (CDD-017) -- never a duplicate of its own
source-concept/relationship-type/target-type/obligation fields. Mirrors
`CanonicalStandard`'s exact versioning shape (CDD-049 §10): a caller-supplied
identity per version, `version_number`/`previous_version_id` chain, at most
one `ACTIVE` version per `relationship_requirement_id` enforced at the
database level (CDD-050 §7) -- never recomputed here.

`min_cardinality`/`max_cardinality` (`NULL` = unbounded) are the sole new
governed fact this module adds; `RelationshipRequirement.obligation` remains
the sole governor of *whether* a cardinality definition may legitimately mark
`min_cardinality >= 1` (CDD-050 §8) -- that consistency is an
implementation-time validation, not re-expressed as a domain invariant here,
since this dataclass has no dependency on `RelationshipRequirement`'s own
domain shape (CDD-017, unmodified, unimported)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

_MAX_CREATED_BY_LENGTH = 200


class IntegrityRelationshipCardinalityStatus(StrEnum):
    """CDD-050 §7: closed, exactly these two. No DRAFT."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class IntegrityRelationshipCardinality:
    """CDD-050 §7: the versioned governed cardinality envelope. Anchored
    exclusively to a governed `RelationshipRequirement`
    (`relationship_requirement_id`) -- never to a raw relationship-type
    string. No `tenant_id` -- shared platform structure, identical
    classification to `RelationshipRequirement` itself (CDD-017 §9,
    CDD-050 §7)."""

    integrity_relationship_cardinality_id: UUID
    relationship_requirement_id: UUID
    min_cardinality: int
    max_cardinality: int | None
    version_number: int
    previous_version_id: UUID | None
    status: IntegrityRelationshipCardinalityStatus
    created_by: str
    created_on: datetime
    retired_on: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.integrity_relationship_cardinality_id, UUID):
            raise ValidationException("integrity_relationship_cardinality_id must be a UUID")
        if not isinstance(self.relationship_requirement_id, UUID):
            raise ValidationException("relationship_requirement_id must be a UUID")
        if (
            not isinstance(self.min_cardinality, int)
            or isinstance(self.min_cardinality, bool)
            or self.min_cardinality < 0
        ):
            raise ValidationException("min_cardinality must be a non-negative integer")
        if self.max_cardinality is not None and (
            not isinstance(self.max_cardinality, int)
            or isinstance(self.max_cardinality, bool)
            or self.max_cardinality < self.min_cardinality
        ):
            raise ValidationException(
                "max_cardinality must be None (unbounded) or an integer >= min_cardinality"
            )
        if (
            not isinstance(self.version_number, int)
            or isinstance(self.version_number, bool)
            or self.version_number < 1
        ):
            raise ValidationException("version_number must be a positive integer")
        if self.previous_version_id is not None and not isinstance(self.previous_version_id, UUID):
            raise ValidationException("previous_version_id must be a UUID or None")
        if self.version_number == 1 and self.previous_version_id is not None:
            raise ValidationException("version_number=1 must not carry previous_version_id")
        if self.version_number > 1 and self.previous_version_id is None:
            raise ValidationException("version_number > 1 requires previous_version_id")
        if not isinstance(self.status, IntegrityRelationshipCardinalityStatus):
            raise ValidationException("status must be an IntegrityRelationshipCardinalityStatus")
        if not isinstance(self.created_by, str) or not (
            1 <= len(self.created_by) <= _MAX_CREATED_BY_LENGTH
        ):
            raise ValidationException("created_by must be non-empty bounded text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")
        if (
            self.status is IntegrityRelationshipCardinalityStatus.ACTIVE
            and self.retired_on is not None
        ):
            raise ValidationException("ACTIVE cardinality definitions must not carry retired_on")
        if (
            self.status is IntegrityRelationshipCardinalityStatus.RETIRED
            and self.retired_on is None
        ):
            raise ValidationException("RETIRED cardinality definitions must carry retired_on")
        if self.retired_on is not None and self.retired_on.tzinfo is None:
            raise ValidationException("retired_on must include a timezone")


def activate_new_cardinality_version(
    *,
    existing_active: IntegrityRelationshipCardinality | None,
    integrity_relationship_cardinality_id: UUID,
    relationship_requirement_id: UUID,
    min_cardinality: int,
    max_cardinality: int | None,
    created_by: str,
    created_on: datetime,
) -> IntegrityRelationshipCardinality:
    """CDD-050 §7: constructs the next ACTIVE version for a
    `RelationshipRequirement`. Retirement of `existing_active` (if any) is
    the caller's/repository's responsibility -- this function only ever
    returns the new version, mirroring
    `activate_new_standard_version`'s exact precedent (CDD-049 §10)."""
    return IntegrityRelationshipCardinality(
        integrity_relationship_cardinality_id=integrity_relationship_cardinality_id,
        relationship_requirement_id=relationship_requirement_id,
        min_cardinality=min_cardinality,
        max_cardinality=max_cardinality,
        version_number=1 if existing_active is None else existing_active.version_number + 1,
        previous_version_id=(
            None
            if existing_active is None
            else existing_active.integrity_relationship_cardinality_id
        ),
        status=IntegrityRelationshipCardinalityStatus.ACTIVE,
        created_by=created_by,
        created_on=created_on,
    )
