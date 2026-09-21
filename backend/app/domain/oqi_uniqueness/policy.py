"""OQI-H6 governed EnterpriseEntity Uniqueness policy (CDD-084 §15-§17): a
tenant-owned, versioned governed object anchored to `entity_type_id` -- a
shared-platform, non-tenant-owned ontology vocabulary member (CDD-084 §15,
mirroring `TimelinessPolicy`'s `information_element_requirement_id` plain-FK
anchor exactly). At most one `ACTIVE` version may exist per exact
`(tenant_id, entity_type_id)` anchor -- enforced at the database level
(CDD-084 §15's partial unique index), never recomputed here.

`bucket_max_size` is the single governed knob controlling H6 v1's bounded
candidate-generation search (CDD-084 §17) -- there is deliberately no
`blocking_strategy` column: H6 v1's blocking key is fixed, not
policy-configurable, to `canonical_name(enterprise_entity_name)` equality
(CDD-084 §16)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200
_MAX_CREATED_BY_LENGTH = 200


class UniquenessPolicyStatus(StrEnum):
    """CDD-084 §15: closed, exactly these two. No DRAFT, mirroring
    `TimelinessPolicyStatus` exactly."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class UniquenessPolicy:
    """One immutable version row. `policy_id` is the stable cross-version
    identity (Finding identity never depends on `version` at all -- CDD-084
    §24); `version` is a positive, monotonically increasing integer starting
    at 1 for a given `policy_id`."""

    policy_id: UUID
    version: int
    tenant_id: str
    entity_type_id: UUID
    bucket_max_size: int
    status: UniquenessPolicyStatus
    created_by: str
    created_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, UUID):
            raise ValidationException("policy_id must be a UUID")
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValidationException("version must be a positive integer")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.entity_type_id, UUID):
            raise ValidationException("entity_type_id must be a UUID")
        if (
            not isinstance(self.bucket_max_size, int)
            or isinstance(self.bucket_max_size, bool)
            or self.bucket_max_size <= 0
        ):
            raise ValidationException("bucket_max_size must be a positive integer")
        if not isinstance(self.status, UniquenessPolicyStatus):
            raise ValidationException("status must be a UniquenessPolicyStatus")
        if not isinstance(self.created_by, str) or not (
            1 <= len(self.created_by) <= _MAX_CREATED_BY_LENGTH
        ):
            raise ValidationException("created_by must be non-empty bounded text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


def new_uniqueness_policy(
    *,
    policy_id: UUID,
    tenant_id: str,
    entity_type_id: UUID,
    bucket_max_size: int,
    created_by: str,
    created_on: datetime,
) -> UniquenessPolicy:
    """First governed version (version 1, ACTIVE) of a new UniquenessPolicy."""
    return UniquenessPolicy(
        policy_id=policy_id,
        version=1,
        tenant_id=tenant_id,
        entity_type_id=entity_type_id,
        bucket_max_size=bucket_max_size,
        status=UniquenessPolicyStatus.ACTIVE,
        created_by=created_by,
        created_on=created_on,
    )


def new_uniqueness_policy_version(
    prior: UniquenessPolicy,
    *,
    bucket_max_size: int | None = None,
    status: UniquenessPolicyStatus | None = None,
    created_by: str,
    created_on: datetime,
) -> UniquenessPolicy:
    """CDD-084 §15: a new governed version, never a silent overwrite of the
    prior row. `prior` remains byte-unchanged in the caller's persistence
    layer -- this returns a new object with the same `policy_id` and
    `version + 1`. `entity_type_id` never changes across versions of the
    same policy -- a different anchor is a different `policy_id` entirely."""
    return UniquenessPolicy(
        policy_id=prior.policy_id,
        version=prior.version + 1,
        tenant_id=prior.tenant_id,
        entity_type_id=prior.entity_type_id,
        bucket_max_size=(prior.bucket_max_size if bucket_max_size is None else bucket_max_size),
        status=prior.status if status is None else status,
        created_by=created_by,
        created_on=created_on,
    )
