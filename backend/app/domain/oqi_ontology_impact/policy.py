"""CDD-042 §8: `ImpactPropagationPolicy` -- the sole authority by which a
relationship type may carry ontology quality impact. `relationship_types`
itself carries no propagation semantics (verified by direct read during
OQI4-G) -- deny-by-default is therefore a data-governed fact on this table,
never a code branch: a relationship type with no ACTIVE policy enrollment
for the traversed direction/tenant never propagates impact."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

#: CDD-042 §9's separate, secondary global safety ceiling. A policy's own
#: `max_depth` may never exceed this; it exists so a single malformed/
#: overly-broad policy cannot make traversal unbounded even if depth
#: validation elsewhere were ever bypassed.
GLOBAL_MAX_DEPTH_CEILING = 10

_MAX_TENANT_ID_LENGTH = 200


class PropagationDirection(StrEnum):
    """CDD-042 §8: the direction, relative to `institutional_relationships.
    from_entity_id -> to_entity_id`, in which this policy permits impact to
    traverse the enrolled relationship type."""

    FORWARD = "FORWARD"
    REVERSE = "REVERSE"
    BOTH = "BOTH"


class PolicyGovernanceStatus(StrEnum):
    """CDD-042 §8: reuses the existing ECOM lifecycle-enum casing
    (Draft/Active/Retired) rather than inventing new naming."""

    DRAFT = "Draft"
    ACTIVE = "Active"
    RETIRED = "Retired"


@dataclass(frozen=True, slots=True)
class ImpactPropagationPolicy:
    """CDD-042 §8. Immutable per version -- the same ACTIVE/RETIRED-plus-
    `previous_version_id` discipline already used for `QualityRule`/
    `BusinessRule`. Only one ACTIVE version may exist per
    `(tenant_id, relationship_type_id, direction)` at a time; that
    uniqueness is enforced at the database layer (migration 0023)."""

    policy_id: UUID
    tenant_id: str
    relationship_type_id: UUID
    direction: PropagationDirection
    max_depth: int
    governance_status: PolicyGovernanceStatus
    version_number: int
    previous_version_id: UUID | None

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, UUID):
            raise ValidationException("policy_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.relationship_type_id, UUID):
            raise ValidationException("relationship_type_id must be a UUID")
        if not isinstance(self.direction, PropagationDirection):
            raise ValidationException("direction must be a PropagationDirection")
        if (
            not isinstance(self.max_depth, int)
            or isinstance(self.max_depth, bool)
            or not (1 <= self.max_depth <= GLOBAL_MAX_DEPTH_CEILING)
        ):
            raise ValidationException(
                f"max_depth must be an integer in [1, {GLOBAL_MAX_DEPTH_CEILING}]"
            )
        if not isinstance(self.governance_status, PolicyGovernanceStatus):
            raise ValidationException("governance_status must be a PolicyGovernanceStatus")
        if (
            not isinstance(self.version_number, int)
            or isinstance(self.version_number, bool)
            or self.version_number < 1
        ):
            raise ValidationException("version_number must be a positive integer")
        if self.previous_version_id is not None and not isinstance(self.previous_version_id, UUID):
            raise ValidationException("previous_version_id must be a UUID or None")
        if self.version_number == 1 and self.previous_version_id is not None:
            raise ValidationException("version 1 must not carry a previous_version_id")
        if self.version_number > 1 and self.previous_version_id is None:
            raise ValidationException("version > 1 must carry a previous_version_id")
