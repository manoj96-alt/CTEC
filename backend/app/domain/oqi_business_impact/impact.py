"""CDD-044 §20-§26, §37-§39, §42, §59: deterministic, per-`BusinessDependency`
Business Impact derivation. `BusinessImpactEvaluation` is the immutable
ledger record; `CurrentBusinessImpact` is the mutable current-projection
pointer (CDD-044 §39, mirroring OQI4's own
`OntologyImpactEvaluation`/`CurrentOntologyImpact` pairing). No LLM,
majority, or authority input may ever reach `derive_business_impact_outcome`
-- its only inputs are OQI4's own governed `CurrentOntologyImpact` facts and
whether an `ACTIVE` `BusinessDependency` exists."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.oqi_ontology_impact.evaluation import CurrentImpactStatus, OntologyElementType
from app.domain.shared.exceptions import ValidationException

#: Distinct from OQI1-5's own namespaces -- OQI6 identities can never
#: coincidentally collide with a predecessor family's.
OQI_BUSINESS_IMPACT_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:business-impact:v1")

_MAX_TENANT_ID_LENGTH = 200


def _length_prefixed(value: str) -> str:
    """Self-delimiting encoding: UTF-8 byte length, never Python character
    count -- identical technique to every prior OQI digest/identity
    formula in this codebase."""
    return f"{len(value.encode('utf-8'))}:{value}"


class BusinessImpactOutcome(StrEnum):
    """CDD-044 §21: closed, exact frozen wording. `BUSINESS_IMPACT_IDENTIFIED`
    is a positive, proven consequence; `NO_KNOWN_BUSINESS_IMPACT` never means
    "no consequence exists anywhere" (§22); `BUSINESS_IMPACT_UNKNOWN` covers
    every insufficient-knowledge case (§23)."""

    BUSINESS_IMPACT_IDENTIFIED = "BUSINESS_IMPACT_IDENTIFIED"
    NO_KNOWN_BUSINESS_IMPACT = "NO_KNOWN_BUSINESS_IMPACT"
    BUSINESS_IMPACT_UNKNOWN = "BUSINESS_IMPACT_UNKNOWN"


def derive_business_impact_outcome(
    *,
    active_dependency_exists: bool,
    impact_status: CurrentImpactStatus | None,
) -> BusinessImpactOutcome:
    """CDD-044 §59's exact decision table -- the sole place OQI6 decides a
    Business Impact outcome. `impact_status` is `None` when no relevant
    `CurrentOntologyImpact` row exists yet.

    Implementation-time finding (disclosed, safe direction, does not
    require a governance amendment): direct inspection of OQI4's own
    evaluation service shows `CurrentOntologyImpact` rows are written only
    for `IMPACTED` (status `ACTIVE`) or a subsequently-resolved former
    impact (status `RESOLVED`, CDD-042's own "absence of knowledge is not
    knowledge of absence" comment) -- an `IMPACT_UNKNOWN` outcome leaves
    the current projection completely untouched and therefore produces no
    row of its own, indistinguishable at the row level from "never
    evaluated". Treating that absence as `NO_KNOWN_BUSINESS_IMPACT` (a
    literal reading of CDD-044 §59's "no relevant row yet" branch) would
    violate CDD-044 §23-§24's own, more heavily emphasized firewall that
    `IMPACT_UNKNOWN` may never be silently converted to
    `NO_KNOWN_BUSINESS_IMPACT`. This function therefore maps "no relevant
    row exists" to `BUSINESS_IMPACT_UNKNOWN` -- the safe, firewall-
    consistent answer -- rather than `NO_KNOWN_BUSINESS_IMPACT`.
    `NO_KNOWN_BUSINESS_IMPACT` is reachable only via an explicit `RESOLVED`
    row (a previously-proven impact that OQI4 itself later retracted)."""
    if not active_dependency_exists:
        return BusinessImpactOutcome.BUSINESS_IMPACT_UNKNOWN
    if impact_status is CurrentImpactStatus.ACTIVE:
        return BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED
    if impact_status is CurrentImpactStatus.RESOLVED:
        return BusinessImpactOutcome.NO_KNOWN_BUSINESS_IMPACT
    # impact_status is None: no CurrentOntologyImpact row has ever existed.
    return BusinessImpactOutcome.BUSINESS_IMPACT_UNKNOWN


def derive_business_impact_evaluation_id(
    *,
    tenant_id: str,
    business_dependency_id: UUID,
    business_dependency_version: int,
    considered_current_impact_id: UUID | None,
    outcome: BusinessImpactOutcome,
) -> UUID:
    """CDD-044 §42's exact deterministic identity: tenant + dependency
    (id + version) + the exact `CurrentOntologyImpact` row considered (or
    none) + the resulting outcome. Never a random UUID -- identical replay
    input converges to the identical evaluation row."""
    material = (
        _length_prefixed(tenant_id)
        + _length_prefixed(str(business_dependency_id))
        + _length_prefixed(str(business_dependency_version))
        + _length_prefixed(
            "" if considered_current_impact_id is None else str(considered_current_impact_id)
        )
        + _length_prefixed(outcome.value)
    )
    return uuid5(OQI_BUSINESS_IMPACT_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class BusinessImpactEvaluation:
    """CDD-044 §38: immutable once created. A later change to Finding
    state, `BusinessDependency`/criticality, OQI4 impact, or coverage never
    rewrites this row -- it produces a new one."""

    evaluation_id: UUID
    tenant_id: str
    business_dependency_id: UUID
    business_dependency_version: int
    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    outcome: BusinessImpactOutcome
    considered_current_impact_id: UUID | None
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.business_dependency_id, UUID):
            raise ValidationException("business_dependency_id must be a UUID")
        if (
            not isinstance(self.business_dependency_version, int)
            or isinstance(self.business_dependency_version, bool)
            or self.business_dependency_version < 1
        ):
            raise ValidationException("business_dependency_version must be a positive integer")
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if not isinstance(self.outcome, BusinessImpactOutcome):
            raise ValidationException("outcome must be a BusinessImpactOutcome")
        if self.considered_current_impact_id is not None and not isinstance(
            self.considered_current_impact_id, UUID
        ):
            raise ValidationException("considered_current_impact_id must be a UUID or None")
        if self.evaluated_at.tzinfo is None:
            raise ValidationException("evaluated_at must include a timezone")

        expected_id = derive_business_impact_evaluation_id(
            tenant_id=self.tenant_id,
            business_dependency_id=self.business_dependency_id,
            business_dependency_version=self.business_dependency_version,
            considered_current_impact_id=self.considered_current_impact_id,
            outcome=self.outcome,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


@dataclass(frozen=True, slots=True)
class CurrentBusinessImpact:
    """CDD-044 §39: mutable current-projection pointer, one row per
    `(tenant_id, business_dependency_id)`. Carries no independent truth --
    only an indexed pointer to the latest immutable evaluation."""

    tenant_id: str
    business_dependency_id: UUID
    latest_evaluation_id: UUID
    first_seen_at: datetime
    last_seen_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.business_dependency_id, UUID):
            raise ValidationException("business_dependency_id must be a UUID")
        if not isinstance(self.latest_evaluation_id, UUID):
            raise ValidationException("latest_evaluation_id must be a UUID")
        for label, value in (
            ("first_seen_at", self.first_seen_at),
            ("last_seen_at", self.last_seen_at),
        ):
            if value.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")
