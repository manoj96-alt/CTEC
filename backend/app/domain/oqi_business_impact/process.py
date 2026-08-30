"""CDD-044 §15, §15.1, §17: `BusinessProcess` -- a governed, versioned,
tenant-scoped named unit of business activity, carrying no execution/
workflow semantics of its own (no BPMN, no process instances, no task
management, no SLA engine, no process mining). `process_id` is a stable
identity shared across every version row (mirroring `AgentRole`'s own
`role_id` + `version` composite-identity shape, CDD-043 §18) -- a change to
name/description/category/status never overwrites history; it produces a
new version row with the same `process_id` and `version + 1`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200
_MAX_NAME_LENGTH = 200
_MAX_DESCRIPTION_LENGTH = 2000


class BusinessProcessStatus(StrEnum):
    """CDD-044 §15, §43: closed, exactly two values. Retirement changes
    only future/current computation eligibility -- it never deletes or
    rewrites a historical version row."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class BusinessImpactCategory(StrEnum):
    """CDD-044 §17: minimal governed seed vocabulary. A categorical
    descriptive tag only -- never computed or inferred, never a gateway to
    monetary quantification. Extending this set is a future governance
    (CDD-044 amendment) action, never an implementation-time or
    reference-pack-time decision."""

    OPERATIONAL = "OPERATIONAL"
    FINANCIAL = "FINANCIAL"
    COMPLIANCE = "COMPLIANCE"
    CUSTOMER = "CUSTOMER"
    ANALYTICS = "ANALYTICS"


@dataclass(frozen=True, slots=True)
class BusinessProcess:
    """One immutable version row. `process_id` is the stable cross-version
    identity; `version` is a positive, monotonically increasing integer
    starting at 1 for a given `process_id`."""

    process_id: UUID
    tenant_id: str
    version: int
    name: str
    description: str | None
    status: BusinessProcessStatus
    category: BusinessImpactCategory | None
    created_by: str
    created_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.process_id, UUID):
            raise ValidationException("process_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValidationException("version must be a positive integer")
        if not isinstance(self.name, str) or not (1 <= len(self.name) <= _MAX_NAME_LENGTH):
            raise ValidationException("name must be non-empty bounded text")
        if self.description is not None and (
            not isinstance(self.description, str) or len(self.description) > _MAX_DESCRIPTION_LENGTH
        ):
            raise ValidationException("description must be None or bounded text")
        if not isinstance(self.status, BusinessProcessStatus):
            raise ValidationException("status must be a BusinessProcessStatus")
        if self.category is not None and not isinstance(self.category, BusinessImpactCategory):
            raise ValidationException("category must be None or a BusinessImpactCategory")
        if not isinstance(self.created_by, str) or not self.created_by:
            raise ValidationException("created_by must be non-empty text")
        if self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


def create_business_process(
    *,
    process_id: UUID,
    tenant_id: str,
    name: str,
    description: str | None,
    category: BusinessImpactCategory | None,
    created_by: str,
    created_on: datetime,
) -> BusinessProcess:
    """First governed version (version 1, ACTIVE) of a new BusinessProcess."""
    return BusinessProcess(
        process_id=process_id,
        tenant_id=tenant_id,
        version=1,
        name=name,
        description=description,
        status=BusinessProcessStatus.ACTIVE,
        category=category,
        created_by=created_by,
        created_on=created_on,
    )


def new_business_process_version(
    prior: BusinessProcess,
    *,
    name: str | None = None,
    description: str | None = None,
    category: BusinessImpactCategory | None = None,
    status: BusinessProcessStatus | None = None,
    created_by: str,
    created_on: datetime,
) -> BusinessProcess:
    """CDD-044 §15: a new governed version, never a silent overwrite of the
    prior row. `prior` remains byte-unchanged in the caller's persistence
    layer -- this returns a new object with the same `process_id`."""
    return BusinessProcess(
        process_id=prior.process_id,
        tenant_id=prior.tenant_id,
        version=prior.version + 1,
        name=prior.name if name is None else name,
        description=prior.description if description is None else description,
        status=prior.status if status is None else status,
        category=prior.category if category is None else category,
        created_by=created_by,
        created_on=created_on,
    )
