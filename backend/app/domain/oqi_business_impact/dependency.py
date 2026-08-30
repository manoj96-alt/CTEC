"""CDD-044 §12-§14, §16, §22-§23: `BusinessDependency` -- the governed
statement that a named `BusinessProcess` (at a specific version) depends on
a specific ontology subject, carrying `Criticality` as one of its own
fields (never a field of the ontology subject, an entity type, a `Finding`,
or an `AgentRecommendation`, CDD-044 §12). Reuses CDD-042's own closed
`OntologyElementType` vocabulary unmodified -- no attribute/assertion-level
subject exists, for the identical reason OQI4 itself excludes one."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200


class Criticality(StrEnum):
    """CDD-044 §13: closed, four values. An ordering exists for
    deterministic sorting/filtering only (`_CRITICALITY_SORT_ORDER`) --
    it carries no quantitative, monetary, or probabilistic meaning and is
    never used as a numeric weight in any aggregation."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


_CRITICALITY_SORT_ORDER: dict[Criticality, int] = {
    Criticality.LOW: 0,
    Criticality.MEDIUM: 1,
    Criticality.HIGH: 2,
    Criticality.CRITICAL: 3,
}


def criticality_sort_key(criticality: Criticality) -> int:
    """Deterministic sort/filter ordering only -- CDD-044 §13 explicitly
    forbids attaching quantitative/risk/monetary meaning to this order."""
    return _CRITICALITY_SORT_ORDER[criticality]


class BusinessDependencyStatus(StrEnum):
    """CDD-044 §16, §43: closed. Retirement changes only future/current
    computation eligibility -- historical `BusinessImpactEvaluation` rows
    that already referenced this dependency version are never rewritten."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class BusinessDependency:
    """One immutable version row. `dependency_id` is the stable
    cross-version identity; `version` is a positive, monotonically
    increasing integer starting at 1. `criticality=None` is the explicit,
    first-class `CRITICALITY_UNKNOWN` result (CDD-044 §14) -- never a
    fabricated placeholder value."""

    dependency_id: UUID
    tenant_id: str
    version: int
    business_process_id: UUID
    business_process_version: int
    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    criticality: Criticality | None
    status: BusinessDependencyStatus
    created_by: str
    created_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.dependency_id, UUID):
            raise ValidationException("dependency_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValidationException("version must be a positive integer")
        if not isinstance(self.business_process_id, UUID):
            raise ValidationException("business_process_id must be a UUID")
        if (
            not isinstance(self.business_process_version, int)
            or isinstance(self.business_process_version, bool)
            or self.business_process_version < 1
        ):
            raise ValidationException("business_process_version must be a positive integer")
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if self.criticality is not None and not isinstance(self.criticality, Criticality):
            raise ValidationException("criticality must be None or a Criticality")
        if not isinstance(self.status, BusinessDependencyStatus):
            raise ValidationException("status must be a BusinessDependencyStatus")
        if not isinstance(self.created_by, str) or not self.created_by:
            raise ValidationException("created_by must be non-empty text")
        if self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


def create_business_dependency(
    *,
    dependency_id: UUID,
    tenant_id: str,
    business_process_id: UUID,
    business_process_version: int,
    ontology_element_type: OntologyElementType,
    ontology_element_id: UUID,
    criticality: Criticality | None,
    created_by: str,
    created_on: datetime,
) -> BusinessDependency:
    return BusinessDependency(
        dependency_id=dependency_id,
        tenant_id=tenant_id,
        version=1,
        business_process_id=business_process_id,
        business_process_version=business_process_version,
        ontology_element_type=ontology_element_type,
        ontology_element_id=ontology_element_id,
        criticality=criticality,
        status=BusinessDependencyStatus.ACTIVE,
        created_by=created_by,
        created_on=created_on,
    )


class _Unset:
    """Sentinel type distinct from `None` -- `None` is itself a legitimate
    target `criticality` value (CRITICALITY_UNKNOWN), so "leave unchanged"
    needs its own, differently-typed marker."""


_UNSET = _Unset()


def new_business_dependency_version(
    prior: BusinessDependency,
    *,
    criticality: Criticality | None | _Unset = _UNSET,
    status: BusinessDependencyStatus | None = None,
    created_by: str,
    created_on: datetime,
) -> BusinessDependency:
    """CDD-044 §22-§23: a criticality/status change is a new governed
    version, never an in-place mutation."""
    new_criticality = prior.criticality if isinstance(criticality, _Unset) else criticality
    return BusinessDependency(
        dependency_id=prior.dependency_id,
        tenant_id=prior.tenant_id,
        version=prior.version + 1,
        business_process_id=prior.business_process_id,
        business_process_version=prior.business_process_version,
        ontology_element_type=prior.ontology_element_type,
        ontology_element_id=prior.ontology_element_id,
        criticality=new_criticality,
        status=prior.status if status is None else status,
        created_by=created_by,
        created_on=created_on,
    )
