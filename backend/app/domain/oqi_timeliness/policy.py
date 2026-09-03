"""OQI-H5 governed Timeliness policy (CDD-051 §7-§10): a tenant-owned,
versioned governed object anchored to `(information_element_requirement_id,
business_process_id, business_process_version)` -- CDD-051 §7 resolves
CDD-046 §43 DD-06 to `InformationElementRequirement` only (never
`SourceField` directly, which carries no `tenant_id` of its own and cannot
compose a tenant-qualified FK). Mirrors `BusinessProcess`'s own
`(process_id, version)` stable-identity-plus-incrementing-version shape
(CDD-044 §15) exactly, since `TimelinessPolicy` references `BusinessProcess`
anyway -- never `IntegrityRelationshipCardinality`'s
`previous_version_id`-chain shape.

At most one `ACTIVE` version may exist per exact anchor tuple -- enforced at
the database level (CDD-051 §8's partial unique index), never recomputed
here. `freshness_window_seconds`/`ingestion_sla_seconds` govern the two
Timeliness Finding types (CDD-051 §4); at least one must be populated, since
a policy governing neither reason path is meaningless."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200
_MAX_CREATED_BY_LENGTH = 200


class TimelinessPolicyStatus(StrEnum):
    """CDD-051 §8: closed, exactly these two. No DRAFT."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class TimelinessPolicy:
    """One immutable version row. `policy_id` is the stable cross-version
    identity (Finding identity anchors to this, never to `version` --
    CDD-051 §17); `version` is a positive, monotonically increasing integer
    starting at 1 for a given `policy_id`."""

    policy_id: UUID
    version: int
    tenant_id: str
    information_element_requirement_id: UUID
    business_process_id: UUID
    business_process_version: int
    freshness_window_seconds: int | None
    ingestion_sla_seconds: int | None
    status: TimelinessPolicyStatus
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
        if not isinstance(self.information_element_requirement_id, UUID):
            raise ValidationException("information_element_requirement_id must be a UUID")
        if not isinstance(self.business_process_id, UUID):
            raise ValidationException("business_process_id must be a UUID")
        if (
            not isinstance(self.business_process_version, int)
            or isinstance(self.business_process_version, bool)
            or self.business_process_version < 1
        ):
            raise ValidationException("business_process_version must be a positive integer")
        for label, value in (
            ("freshness_window_seconds", self.freshness_window_seconds),
            ("ingestion_sla_seconds", self.ingestion_sla_seconds),
        ):
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value <= 0
            ):
                raise ValidationException(f"{label} must be None or a positive integer")
        if self.freshness_window_seconds is None and self.ingestion_sla_seconds is None:
            raise ValidationException(
                "TimelinessPolicy must govern at least one of freshness_window_seconds or "
                "ingestion_sla_seconds -- a policy governing neither reason path is meaningless "
                "(CDD-051 §8)"
            )
        if not isinstance(self.status, TimelinessPolicyStatus):
            raise ValidationException("status must be a TimelinessPolicyStatus")
        if not isinstance(self.created_by, str) or not (
            1 <= len(self.created_by) <= _MAX_CREATED_BY_LENGTH
        ):
            raise ValidationException("created_by must be non-empty bounded text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


def new_timeliness_policy(
    *,
    policy_id: UUID,
    tenant_id: str,
    information_element_requirement_id: UUID,
    business_process_id: UUID,
    business_process_version: int,
    freshness_window_seconds: int | None,
    ingestion_sla_seconds: int | None,
    created_by: str,
    created_on: datetime,
) -> TimelinessPolicy:
    """First governed version (version 1, ACTIVE) of a new TimelinessPolicy."""
    return TimelinessPolicy(
        policy_id=policy_id,
        version=1,
        tenant_id=tenant_id,
        information_element_requirement_id=information_element_requirement_id,
        business_process_id=business_process_id,
        business_process_version=business_process_version,
        freshness_window_seconds=freshness_window_seconds,
        ingestion_sla_seconds=ingestion_sla_seconds,
        status=TimelinessPolicyStatus.ACTIVE,
        created_by=created_by,
        created_on=created_on,
    )


def new_timeliness_policy_version(
    prior: TimelinessPolicy,
    *,
    freshness_window_seconds: int | None = None,
    ingestion_sla_seconds: int | None = None,
    status: TimelinessPolicyStatus | None = None,
    created_by: str,
    created_on: datetime,
) -> TimelinessPolicy:
    """CDD-051 §8: a new governed version, never a silent overwrite of the
    prior row. `prior` remains byte-unchanged in the caller's persistence
    layer -- this returns a new object with the same `policy_id` and
    `version + 1`. The anchor tuple (`information_element_requirement_id`,
    `business_process_id`, `business_process_version`) never changes across
    versions of the same policy -- a different anchor is a different
    `policy_id` entirely."""
    return TimelinessPolicy(
        policy_id=prior.policy_id,
        version=prior.version + 1,
        tenant_id=prior.tenant_id,
        information_element_requirement_id=prior.information_element_requirement_id,
        business_process_id=prior.business_process_id,
        business_process_version=prior.business_process_version,
        freshness_window_seconds=(
            prior.freshness_window_seconds
            if freshness_window_seconds is None
            else freshness_window_seconds
        ),
        ingestion_sla_seconds=(
            prior.ingestion_sla_seconds if ingestion_sla_seconds is None else ingestion_sla_seconds
        ),
        status=prior.status if status is None else status,
        created_by=created_by,
        created_on=created_on,
    )
