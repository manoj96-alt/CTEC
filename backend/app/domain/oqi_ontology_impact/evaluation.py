"""CDD-042 §5-§7, §10-§11: the closed epistemic vocabulary, the
Finding-family adapter reference (a plain composite value, never a
polymorphic FK -- CDD-042 §10), and the immutable
`OntologyImpactEvaluation`/`OntologyImpactObservation`/`OntologyImpactPath`
ledger plus the mutable `CurrentOntologyImpact` projection, re-derived from
(not copied from) the Evaluation/Finding split this codebase has now proven
correct three times (OQI1/OQI2/OQI3)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.shared.exceptions import ValidationException

#: Distinct namespace from OQI1 ("...oqi:v1"), OQI2 ("...cross-source:v1"),
#: and OQI3 ("...business-rule:v1") -- OQI4 identities can never
#: coincidentally collide with a predecessor family's.
OQI_ONTOLOGY_IMPACT_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:ontology-impact:v1")

_MAX_TENANT_ID_LENGTH = 200


def _length_prefixed(value: str) -> str:
    """Self-delimiting encoding: UTF-8 byte length, never Python character
    count -- identical technique to every prior OQI digest/identity
    formula in this codebase."""
    return f"{len(value.encode('utf-8'))}:{value}"


def canonical_form(value: UUID | str | int) -> str:
    return str(value)


class FindingFamily(StrEnum):
    """CDD-042 §10: closed, exactly the three predecessor capability
    layers. OQI4 never introduces a fourth."""

    OQI1 = "OQI1"
    OQI2 = "OQI2"
    OQI3 = "OQI3"


@dataclass(frozen=True, slots=True)
class FindingReference:
    """CDD-042 §10: the Finding-family adapter's composite reference.
    Never a DB-level polymorphic FK (Postgres cannot natively express one FK
    spanning three separate tables without a shared parent) -- referential
    correctness is enforced at the application boundary by the per-family
    adapter lookup, the same precedent already accepted in this codebase
    for `EnterpriseEntityResolutionRecordModel.supporting_source_object_ids`."""

    finding_family: FindingFamily
    finding_id: UUID
    finding_state_revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.finding_family, FindingFamily):
            raise ValidationException("finding_family must be a FindingFamily")
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if (
            not isinstance(self.finding_state_revision, int)
            or isinstance(self.finding_state_revision, bool)
            or self.finding_state_revision < 1
        ):
            raise ValidationException("finding_state_revision must be a positive integer")


class ImpactOutcome(StrEnum):
    """CDD-042 §5: closed, 3-value, semantically distinct. `NO_IMPACT` is a
    positive fact requiring governed proof, never a zero-row-join default.
    `IMPACT_UNKNOWN` is a first-class, permanent, legitimate outcome."""

    IMPACTED = "IMPACTED"
    NO_IMPACT = "NO_IMPACT"
    IMPACT_UNKNOWN = "IMPACT_UNKNOWN"


class OntologyElementType(StrEnum):
    """CDD-042 §7: closed. No ASSERTION element type in this scope (§4.7 --
    Assertions carry no live evidence-linked graph data today)."""

    ENTITY = "ENTITY"
    RELATIONSHIP = "RELATIONSHIP"


class ImpactClass(StrEnum):
    """CDD-042 §7: closed. No CRITICAL/HIGH/MEDIUM/LOW -- that is OQI6's
    territory."""

    DIRECT = "DIRECT"
    PROPAGATED = "PROPAGATED"


class ImpactBasis(StrEnum):
    """CDD-042 §6-§7: closed, every positive impact row must carry exactly
    one of these."""

    DIRECT_ENTITY_IDENTITY_LINEAGE = "DIRECT_ENTITY_IDENTITY_LINEAGE"
    GOVERNED_RELATIONSHIP_PROPAGATION = "GOVERNED_RELATIONSHIP_PROPAGATION"


@dataclass(frozen=True, slots=True)
class OntologyImpactObservation:
    """CDD-042 §11.2: one immutable deterministic impact fact. Persisted
    keyed by `(evaluation_id, ontology_element_type, ontology_element_id,
    impact_kind)` -- `evaluation_id` is supplied by the owning
    `OntologyImpactEvaluation` at persistence time, not carried here,
    mirroring OQI3's own Observation dataclass shape."""

    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    impact_kind: ImpactClass
    basis: ImpactBasis
    depth: int

    def __post_init__(self) -> None:
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if not isinstance(self.impact_kind, ImpactClass):
            raise ValidationException("impact_kind must be an ImpactClass")
        if not isinstance(self.basis, ImpactBasis):
            raise ValidationException("basis must be an ImpactBasis")
        if not isinstance(self.depth, int) or isinstance(self.depth, bool) or self.depth < 0:
            raise ValidationException("depth must be a non-negative integer")
        if self.impact_kind is ImpactClass.DIRECT and (
            self.depth != 0 or self.basis is not ImpactBasis.DIRECT_ENTITY_IDENTITY_LINEAGE
        ):
            raise ValidationException("DIRECT observations must have depth 0 and the direct basis")
        if self.impact_kind is ImpactClass.PROPAGATED and (
            self.depth < 1 or self.basis is not ImpactBasis.GOVERNED_RELATIONSHIP_PROPAGATION
        ):
            raise ValidationException(
                "PROPAGATED observations must have depth >= 1 and the propagation basis"
            )


@dataclass(frozen=True, slots=True)
class OntologyImpactPath:
    """CDD-042 §11.3: one immutable hop of a retained path proof. Persisted
    keyed by `(evaluation_id, ontology_element_id, path_ordinal)`;
    `evaluation_id` supplied by the owning Evaluation at persistence time.
    `path_ordinal` orders the hops of one distinct path from a directly-
    impacted element to `ontology_element_id`; multiple distinct paths to
    the same element share `ontology_element_id` but are distinguished by a
    `path_index` prefix folded into `path_ordinal`'s caller-side numbering
    (see the repository's canonical path-ordinal scheme)."""

    ontology_element_id: UUID
    path_ordinal: int
    institutional_relationship_id: UUID
    direction: str
    policy_id: UUID
    policy_version_number: int

    def __post_init__(self) -> None:
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if (
            not isinstance(self.path_ordinal, int)
            or isinstance(self.path_ordinal, bool)
            or self.path_ordinal < 0
        ):
            raise ValidationException("path_ordinal must be a non-negative integer")
        if not isinstance(self.institutional_relationship_id, UUID):
            raise ValidationException("institutional_relationship_id must be a UUID")
        if not isinstance(self.direction, str) or not self.direction:
            raise ValidationException("direction must be non-empty text")
        if not isinstance(self.policy_id, UUID):
            raise ValidationException("policy_id must be a UUID")
        if (
            not isinstance(self.policy_version_number, int)
            or isinstance(self.policy_version_number, bool)
            or self.policy_version_number < 1
        ):
            raise ValidationException("policy_version_number must be a positive integer")


def compute_traversed_state_digest(
    *,
    resolution_record_id: UUID | None,
    resolution_outcome: str | None,
    traversed_relationships: tuple[tuple[UUID, int], ...],
    applied_policies: tuple[tuple[UUID, int], ...],
) -> str:
    """CDD-042 §11.4: canonical, sorted, content-addressed digest over
    exactly which versioned rows were actually traversed -- deliberately
    excludes any invented global "ontology version" (CDD-042 explicitly
    forbids fabricating one). Row-return order never affects the digest."""
    sorted_relationships = sorted(traversed_relationships, key=lambda pair: canonical_form(pair[0]))
    sorted_policies = sorted(applied_policies, key=lambda pair: canonical_form(pair[0]))
    material = (
        _length_prefixed(
            "" if resolution_record_id is None else canonical_form(resolution_record_id)
        )
        + _length_prefixed("" if resolution_outcome is None else resolution_outcome)
        + _length_prefixed(str(len(sorted_relationships)))
        + "".join(
            _length_prefixed(canonical_form(rel_id)) + _length_prefixed(str(version))
            for rel_id, version in sorted_relationships
        )
        + _length_prefixed(str(len(sorted_policies)))
        + "".join(
            _length_prefixed(canonical_form(policy_id)) + _length_prefixed(str(version))
            for policy_id, version in sorted_policies
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def derive_ontology_impact_evaluation_id(
    *,
    tenant_id: str,
    finding_family: FindingFamily,
    finding_id: UUID,
    finding_state_revision: int,
    traversed_state_digest: str,
) -> UUID:
    """CDD-042 §11.1's exact deterministic Evaluation identity formula.
    Deliberately excludes observation/path content -- those are
    deterministic derivatives of these frozen inputs, exactly as OQI2/OQI3
    proved for their own Observation models."""
    material = (
        _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(finding_family.value)
        + _length_prefixed(canonical_form(finding_id))
        + _length_prefixed(str(finding_state_revision))
        + _length_prefixed(traversed_state_digest)
    )
    return uuid5(OQI_ONTOLOGY_IMPACT_NAMESPACE, material)


def derive_current_ontology_impact_id(
    *,
    tenant_id: str,
    finding_family: FindingFamily,
    finding_id: UUID,
    ontology_element_type: OntologyElementType,
    ontology_element_id: UUID,
    impact_kind: ImpactClass,
) -> UUID:
    """CDD-042 §11.5's exact deterministic current-impact identity formula.
    Deliberately excludes `evaluation_id`, `traversed_state_digest`, policy
    version, and path (CDD-042 §11.5 / the governing prompt's §55) -- it is
    condition-level, one row per (Finding, element, kind) triple."""
    material = (
        _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(finding_family.value)
        + _length_prefixed(canonical_form(finding_id))
        + _length_prefixed(ontology_element_type.value)
        + _length_prefixed(canonical_form(ontology_element_id))
        + _length_prefixed(impact_kind.value)
    )
    return uuid5(OQI_ONTOLOGY_IMPACT_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class OntologyImpactEvaluation:
    """CDD-042 §11.1: the immutable, append-only Impact Evaluation ledger
    record -- one deterministic execution of OQI4 against one Finding
    state, at one moment, against one coherent ontology snapshot."""

    evaluation_id: UUID
    tenant_id: str
    finding_family: FindingFamily
    finding_id: UUID
    finding_state_revision: int
    outcome: ImpactOutcome
    resolution_record_id: UUID | None
    traversed_state_digest: str
    evaluated_at: datetime
    observations: tuple[OntologyImpactObservation, ...]
    paths: tuple[OntologyImpactPath, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.finding_family, FindingFamily):
            raise ValidationException("finding_family must be a FindingFamily")
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if (
            not isinstance(self.finding_state_revision, int)
            or isinstance(self.finding_state_revision, bool)
            or self.finding_state_revision < 1
        ):
            raise ValidationException("finding_state_revision must be a positive integer")
        if not isinstance(self.outcome, ImpactOutcome):
            raise ValidationException("outcome must be an ImpactOutcome")
        if self.resolution_record_id is not None and not isinstance(
            self.resolution_record_id, UUID
        ):
            raise ValidationException("resolution_record_id must be a UUID or None")
        if not isinstance(self.traversed_state_digest, str) or not self.traversed_state_digest:
            raise ValidationException("traversed_state_digest must be non-empty text")
        if self.evaluated_at.tzinfo is None:
            raise ValidationException("evaluated_at must include a timezone")
        if not isinstance(self.observations, tuple) or not isinstance(self.paths, tuple):
            raise ValidationException("observations and paths must be tuples")
        if self.outcome is not ImpactOutcome.IMPACTED and self.observations:
            raise ValidationException(
                "only IMPACTED evaluations may carry observations -- "
                "NO_IMPACT/IMPACT_UNKNOWN must have zero"
            )
        if self.outcome is ImpactOutcome.IMPACTED and not self.observations:
            raise ValidationException("IMPACTED evaluations must carry at least one observation")
        observation_keys = {
            (obs.ontology_element_type, obs.ontology_element_id, obs.impact_kind)
            for obs in self.observations
        }
        if len(observation_keys) != len(self.observations):
            raise ValidationException(
                "observation natural keys must be unique within one evaluation"
            )
        propagated_element_ids = {
            obs.ontology_element_id
            for obs in self.observations
            if obs.impact_kind is ImpactClass.PROPAGATED
        }
        path_element_ids = {path.ontology_element_id for path in self.paths}
        if not path_element_ids <= propagated_element_ids:
            raise ValidationException(
                "every path must belong to a PROPAGATED observation in this same evaluation"
            )

        expected_id = derive_ontology_impact_evaluation_id(
            tenant_id=self.tenant_id,
            finding_family=self.finding_family,
            finding_id=self.finding_id,
            finding_state_revision=self.finding_state_revision,
            traversed_state_digest=self.traversed_state_digest,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


class CurrentImpactStatus(StrEnum):
    """CDD-042 §11.5/§12: mutable current-projection status. No counters
    (occurrence_count/reopen_count/state_revision) are duplicated here --
    those already belong to the Finding itself."""

    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True, slots=True)
class CurrentOntologyImpact:
    """CDD-042 §11.5: the mutable current-state projection of the latest
    relevant Impact Evaluation for one (Finding, ontology element, impact
    kind) triple. Never historical evidence in itself -- only a fast,
    indexed pointer to the latest immutable Evaluation that justifies it."""

    current_impact_id: UUID
    tenant_id: str
    finding_family: FindingFamily
    finding_id: UUID
    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    impact_kind: ImpactClass
    status: CurrentImpactStatus
    latest_evaluation_id: UUID
    first_seen_at: datetime
    last_seen_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.current_impact_id, UUID):
            raise ValidationException("current_impact_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.finding_family, FindingFamily):
            raise ValidationException("finding_family must be a FindingFamily")
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if not isinstance(self.impact_kind, ImpactClass):
            raise ValidationException("impact_kind must be an ImpactClass")
        if not isinstance(self.status, CurrentImpactStatus):
            raise ValidationException("status must be a CurrentImpactStatus")
        if not isinstance(self.latest_evaluation_id, UUID):
            raise ValidationException("latest_evaluation_id must be a UUID")
        for label, value in (
            ("first_seen_at", self.first_seen_at),
            ("last_seen_at", self.last_seen_at),
        ):
            if value.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")

        expected_id = derive_current_ontology_impact_id(
            tenant_id=self.tenant_id,
            finding_family=self.finding_family,
            finding_id=self.finding_id,
            ontology_element_type=self.ontology_element_type,
            ontology_element_id=self.ontology_element_id,
            impact_kind=self.impact_kind,
        )
        if self.current_impact_id != expected_id:
            raise ValidationException(
                "current_impact_id is inconsistent with its own governed semantic identity inputs"
            )


def utc_now_placeholder() -> datetime:
    """Not used for CURRENT_STATE horizon fabrication -- the application
    service always supplies its own trusted clock. Kept only as a
    documented, explicit import point for tests constructing fixture
    timestamps consistently in UTC."""
    return datetime.now(UTC)
