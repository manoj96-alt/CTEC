"""OQI-H1 `QualityCoveragePolicy` (CDD-047 §8-§11): a tenant-owned,
versioned declaration that a set of governed quality dimensions must have
qualifying evaluation coverage for a specific ontology subject before that
subject's Reliance may become RELIANCE_SUPPORTED.

`CoverageDimension` (CDD-047 §4) is deliberately a separate closed
vocabulary from `QualityDimension` (`app.domain.oqi.quality_rule`) --
membership in `CoverageDimension` expresses governance requirement, never
evaluator capability. `QualityDimension` remains exactly three members
(COMPLETENESS, VALIDITY, CONSISTENCY) and is untouched by this module.

Identity follows `ImpactPropagationPolicy`'s precedent (CDD-042 §8), not
`BusinessDependency`'s (CDD-044 §16): `policy_id` is a caller-supplied,
non-deterministic identity per version -- a human-authored governance
configuration act, not a machine-computed replay-safe evaluation output --
linked across versions via `previous_version_id`, never a `uuid5` digest
of contributing state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200
_MAX_CREATED_BY_LENGTH = 200


class CoverageDimension(StrEnum):
    """CDD-047 §4: closed, exactly nine. Governance requirement vocabulary
    -- membership here never implies a live evaluator exists. Only
    COMPLETENESS, VALIDITY, and CONSISTENCY currently have one (see
    `app.domain.oqi.quality_rule.QualityDimension`, which remains exactly
    those three and is never expanded by this module)."""

    COMPLETENESS = "COMPLETENESS"
    VALIDITY = "VALIDITY"
    CONSISTENCY = "CONSISTENCY"
    ACCURACY = "ACCURACY"
    UNIQUENESS = "UNIQUENESS"
    TIMELINESS = "TIMELINESS"
    INTEGRITY = "INTEGRITY"
    CONFORMITY = "CONFORMITY"
    REASONABLENESS = "REASONABLENESS"


class QualityCoveragePolicyStatus(StrEnum):
    """CDD-047 §8: closed, exactly two. No DRAFT in H1."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class QualityCoveragePolicy:
    """CDD-047 §8. Immutable once constructed -- a requirement-set or
    status change is always a new version (a new `policy_id`, an
    incremented `version_number`, `previous_version_id` pointing at the
    prior row), never an in-place mutation of a persisted version."""

    policy_id: UUID
    tenant_id: str
    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    status: QualityCoveragePolicyStatus
    version_number: int
    previous_version_id: UUID | None
    required_dimensions: frozenset[CoverageDimension]
    created_by: str
    created_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, UUID):
            raise ValidationException("policy_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if not isinstance(self.status, QualityCoveragePolicyStatus):
            raise ValidationException("status must be a QualityCoveragePolicyStatus")
        if not isinstance(self.version_number, int) or self.version_number < 1:
            raise ValidationException("version_number must be a positive integer")
        if self.previous_version_id is not None and not isinstance(self.previous_version_id, UUID):
            raise ValidationException("previous_version_id must be a UUID or None")
        if self.version_number == 1 and self.previous_version_id is not None:
            raise ValidationException("version 1 must not declare a previous_version_id")
        if self.version_number > 1 and self.previous_version_id is None:
            raise ValidationException("version_number > 1 requires an explicit previous_version_id")
        if not isinstance(self.required_dimensions, frozenset) or not all(
            isinstance(dimension, CoverageDimension) for dimension in self.required_dimensions
        ):
            raise ValidationException(
                "required_dimensions must be a frozenset of CoverageDimension"
            )
        if not self.required_dimensions:
            # CDD-047 §8, §12, §16 (H1-G adversarial review Q16): no empty
            # policy may ever exist, ACTIVE or RETIRED -- a policy's entire
            # purpose is its required-dimension set.
            raise ValidationException("required_dimensions must be non-empty")
        if not isinstance(self.created_by, str) or not (
            1 <= len(self.created_by) <= _MAX_CREATED_BY_LENGTH
        ):
            raise ValidationException("created_by must be non-empty bounded text")
        if self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


def create_quality_coverage_policy(
    *,
    policy_id: UUID,
    tenant_id: str,
    ontology_element_type: OntologyElementType,
    ontology_element_id: UUID,
    required_dimensions: frozenset[CoverageDimension],
    created_by: str,
    created_on: datetime,
) -> QualityCoveragePolicy:
    """CDD-047 §8: the first version of a logical policy. Always
    `status=ACTIVE`, `version_number=1`, `previous_version_id=None` --
    activating a brand-new policy is definitionally an ACTIVE act; a
    caller wishing to author a policy without immediately activating it
    is not authorized by H1 (no DRAFT status exists, CDD-047 §8)."""
    return QualityCoveragePolicy(
        policy_id=policy_id,
        tenant_id=tenant_id,
        ontology_element_type=ontology_element_type,
        ontology_element_id=ontology_element_id,
        status=QualityCoveragePolicyStatus.ACTIVE,
        version_number=1,
        previous_version_id=None,
        required_dimensions=required_dimensions,
        created_by=created_by,
        created_on=created_on,
    )


def new_quality_coverage_policy_version(
    prior: QualityCoveragePolicy,
    *,
    new_policy_id: UUID,
    status: QualityCoveragePolicyStatus,
    required_dimensions: frozenset[CoverageDimension] | None = None,
    created_by: str,
    created_on: datetime,
) -> QualityCoveragePolicy:
    """CDD-047 §8, §10: a new, immutable version superseding `prior` --
    never a mutation of `prior` itself. Retiring a policy is exactly this
    call with `status=RETIRED` and `required_dimensions` unchanged
    (retirement does not redefine what was required, it only ends
    whether the requirement currently governs)."""
    return QualityCoveragePolicy(
        policy_id=new_policy_id,
        tenant_id=prior.tenant_id,
        ontology_element_type=prior.ontology_element_type,
        ontology_element_id=prior.ontology_element_id,
        status=status,
        version_number=prior.version_number + 1,
        previous_version_id=prior.policy_id,
        required_dimensions=(
            prior.required_dimensions if required_dimensions is None else required_dimensions
        ),
        created_by=created_by,
        created_on=created_on,
    )
