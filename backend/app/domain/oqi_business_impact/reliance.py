"""CDD-044 §8-§11, §18-§19, §36, §42, §58: `RelianceEvaluation` -- a
per-ontology-subject (deliberately independent of any `BusinessDependency`,
CDD-044 §19), deterministic, categorical, evidence-bounded conclusion.
`derive_reliance_state` is the sole place OQI6 decides a Reliance State --
its inputs are three booleans derived entirely from OQI1/2/3's own
Finding/evaluation state and OQI4's own `CurrentOntologyImpact` state; no
majority, authority, agent, or model input may ever reach it."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.oqi_ontology_impact.evaluation import FindingFamily, OntologyElementType
from app.domain.shared.exceptions import ValidationException

#: Distinct from every predecessor OQI namespace and from OQI6's own
#: business-impact namespace.
OQI_RELIANCE_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:reliance:v1")

_MAX_TENANT_ID_LENGTH = 200


def _length_prefixed(value: str) -> str:
    return f"{len(value.encode('utf-8'))}:{value}"


class RelianceState(StrEnum):
    """CDD-044 §8: closed, exactly three values. Never a numeric score."""

    RELIANCE_SUPPORTED = "RELIANCE_SUPPORTED"
    RELIANCE_AT_RISK = "RELIANCE_AT_RISK"
    RELIANCE_UNKNOWN = "RELIANCE_UNKNOWN"


class ReasonCode(StrEnum):
    """CDD-044 §36: closed, deterministic, non-prose vocabulary."""

    OPEN_QUALITY_CONDITION = "OPEN_QUALITY_CONDITION"
    INSUFFICIENT_QUALITY_COVERAGE = "INSUFFICIENT_QUALITY_COVERAGE"
    ONTOLOGY_IMPACT_UNKNOWN = "ONTOLOGY_IMPACT_UNKNOWN"
    BUSINESS_DEPENDENCY_UNKNOWN = "BUSINESS_DEPENDENCY_UNKNOWN"
    CRITICALITY_UNKNOWN = "CRITICALITY_UNKNOWN"
    REMEDIATION_PENDING = "REMEDIATION_PENDING"


def derive_reliance_state(
    *,
    any_open_finding: bool,
    any_evaluation_ever_run: bool,
    any_active_impact_unknown: bool,
) -> tuple[RelianceState, tuple[ReasonCode, ...]]:
    """CDD-044 §58's exact decision table."""
    if any_open_finding:
        return RelianceState.RELIANCE_AT_RISK, (ReasonCode.OPEN_QUALITY_CONDITION,)
    if not any_evaluation_ever_run:
        return RelianceState.RELIANCE_UNKNOWN, (ReasonCode.INSUFFICIENT_QUALITY_COVERAGE,)
    if any_active_impact_unknown:
        return RelianceState.RELIANCE_UNKNOWN, (ReasonCode.ONTOLOGY_IMPACT_UNKNOWN,)
    return RelianceState.RELIANCE_SUPPORTED, ()


def compute_reliance_contributing_state_digest(
    *,
    open_finding_refs: tuple[tuple[FindingFamily, UUID, int], ...],
    any_evaluation_ever_run: bool,
    any_active_impact_unknown: bool,
) -> str:
    """CDD-044 §42: canonical, sorted, content-addressed digest over
    exactly the contributing state -- row-return order never affects the
    digest, mirroring OQI4's own `compute_traversed_state_digest`."""
    sorted_refs = sorted(open_finding_refs, key=lambda ref: (ref[0].value, str(ref[1]), ref[2]))
    material = (
        _length_prefixed(str(len(sorted_refs)))
        + "".join(
            _length_prefixed(family.value)
            + _length_prefixed(str(finding_id))
            + _length_prefixed(str(revision))
            for family, finding_id, revision in sorted_refs
        )
        + _length_prefixed(str(any_evaluation_ever_run))
        + _length_prefixed(str(any_active_impact_unknown))
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def derive_reliance_evaluation_id(
    *,
    tenant_id: str,
    ontology_element_type: OntologyElementType,
    ontology_element_id: UUID,
    contributing_state_digest: str,
) -> UUID:
    """CDD-044 §42's exact deterministic identity. Never a random UUID --
    identical replay input converges to the identical evaluation row."""
    material = (
        _length_prefixed(tenant_id)
        + _length_prefixed(ontology_element_type.value)
        + _length_prefixed(str(ontology_element_id))
        + _length_prefixed(contributing_state_digest)
    )
    return uuid5(OQI_RELIANCE_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class RelianceEvaluation:
    """CDD-044 §38: immutable once created."""

    evaluation_id: UUID
    tenant_id: str
    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    state: RelianceState
    reason_codes: tuple[ReasonCode, ...]
    contributing_state_digest: str
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if not isinstance(self.state, RelianceState):
            raise ValidationException("state must be a RelianceState")
        if not isinstance(self.reason_codes, tuple) or not all(
            isinstance(code, ReasonCode) for code in self.reason_codes
        ):
            raise ValidationException("reason_codes must be a tuple of ReasonCode")
        if (
            not isinstance(self.contributing_state_digest, str)
            or not self.contributing_state_digest
        ):
            raise ValidationException("contributing_state_digest must be non-empty text")
        if self.evaluated_at.tzinfo is None:
            raise ValidationException("evaluated_at must include a timezone")

        expected_id = derive_reliance_evaluation_id(
            tenant_id=self.tenant_id,
            ontology_element_type=self.ontology_element_type,
            ontology_element_id=self.ontology_element_id,
            contributing_state_digest=self.contributing_state_digest,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


@dataclass(frozen=True, slots=True)
class CurrentReliance:
    """CDD-044 §39: mutable current-projection pointer, one row per
    `(tenant_id, ontology_element_type, ontology_element_id)`."""

    tenant_id: str
    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    latest_evaluation_id: UUID
    first_seen_at: datetime
    last_seen_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if not isinstance(self.latest_evaluation_id, UUID):
            raise ValidationException("latest_evaluation_id must be a UUID")
        for label, value in (
            ("first_seen_at", self.first_seen_at),
            ("last_seen_at", self.last_seen_at),
        ):
            if value.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")
