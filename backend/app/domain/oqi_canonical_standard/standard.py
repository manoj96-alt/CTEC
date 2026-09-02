"""OQI-H3 governed Canonical Standard (CDD-049 §7-§13): a shared-platform,
versioned, representation-level canonicalization mapping anchored to a
governed Information Element. Representation-level only -- an alias-to-
canonical STRING mapping (e.g. `"US"` -> `"USA"`), never semantic/unit
conversion, never fuzzy matching, never probabilistic resolution (CDD-049
§7).

`CanonicalStandard` is the versioned envelope, following `QualityCoveragePolicy`'s
own precedent (CDD-047 §8-§11) and `ReferenceEvidenceAssertion`'s exact
version-chain shape (CDD-048 §15): `canonical_standard_id` is a caller-supplied
identity per version, versioned via `version_number`/`previous_version_id`,
with at most one `ACTIVE` version per `information_element_requirement_id`
enforced at the database level (CDD-049 §10). `CanonicalValue`/`CanonicalAlias`
are normalized children, never an opaque JSON dictionary (CDD-049 §11).

`canonicalize()` is the pure, deterministic resolver (CDD-049 §13): given an
already-loaded `CanonicalStandard` (or `None`) and an observed representation,
it returns a `CanonicalizationResult` -- no database access, no probability,
no fuzzy matching, and -- structurally, by having no import of any kind from
`app.domain.identity_resolution` -- no dependency on Entity Resolution's own
unversioned, ungoverned matching heuristics (CDD-049 §35 STOP condition 4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

_MAX_REPRESENTATION_LENGTH = 4000
_MAX_CREATED_BY_LENGTH = 200
_MAX_REQUIREMENT_ID_LENGTH = 200


class CanonicalStandardStatus(StrEnum):
    """CDD-049 §10: closed, exactly these two. No DRAFT."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class CanonicalizationState(StrEnum):
    """CDD-049 §13: closed, exactly these five. No sixth state -- a
    canonicalization resolver may never invent a confidence-scored or
    probabilistic outcome."""

    CANONICAL = "CANONICAL"
    ALIAS_RESOLVED = "ALIAS_RESOLVED"
    NOT_MAPPED = "NOT_MAPPED"
    AMBIGUOUS = "AMBIGUOUS"
    NO_STANDARD = "NO_STANDARD"


@dataclass(frozen=True, slots=True)
class CanonicalAlias:
    """CDD-049 §11: a recognized non-canonical representation, 1:N under its
    owning `CanonicalValue`. `UNIQUE(canonical_standard_id, alias_representation)
    WHERE ACTIVE` (enforced at the database level, §11) makes it structurally
    impossible for one representation to resolve to two canonical values
    under the same applicable active standard -- this dataclass carries no
    ambiguity-detection logic of its own; ambiguity is prevented by
    construction, not computed here."""

    canonical_alias_id: UUID
    canonical_value_id: UUID
    alias_representation: str

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_alias_id, UUID):
            raise ValidationException("canonical_alias_id must be a UUID")
        if not isinstance(self.canonical_value_id, UUID):
            raise ValidationException("canonical_value_id must be a UUID")
        if not isinstance(self.alias_representation, str) or not (
            1 <= len(self.alias_representation) <= _MAX_REPRESENTATION_LENGTH
        ):
            raise ValidationException("alias_representation must be non-empty bounded text")


@dataclass(frozen=True, slots=True)
class CanonicalValue:
    """CDD-049 §11: one governed canonical representation within a
    `CanonicalStandard` (e.g. `"USA"`), 1:N under its owning standard, with
    zero or more recognized `CanonicalAlias` rows. The canonical
    representation is implicitly its own trivial alias -- an observation
    matching it exactly (after trimming) is `CANONICAL`, never requiring a
    separate alias row (§11)."""

    canonical_value_id: UUID
    canonical_standard_id: UUID
    canonical_representation: str
    aliases: tuple[CanonicalAlias, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_value_id, UUID):
            raise ValidationException("canonical_value_id must be a UUID")
        if not isinstance(self.canonical_standard_id, UUID):
            raise ValidationException("canonical_standard_id must be a UUID")
        if not isinstance(self.canonical_representation, str) or not (
            1 <= len(self.canonical_representation) <= _MAX_REPRESENTATION_LENGTH
        ):
            raise ValidationException("canonical_representation must be non-empty bounded text")
        if not isinstance(self.aliases, tuple) or not all(
            isinstance(alias, CanonicalAlias) for alias in self.aliases
        ):
            raise ValidationException("aliases must be a tuple of CanonicalAlias")
        for alias in self.aliases:
            if alias.canonical_value_id != self.canonical_value_id:
                raise ValidationException(
                    "every alias must reference its own owning canonical_value_id"
                )


@dataclass(frozen=True, slots=True)
class CanonicalStandard:
    """CDD-049 §9-§10: the shared-platform, versioned envelope. Anchored
    exclusively to a governed Information Element
    (`information_element_requirement_id`) -- never to a `SourceField`
    (PO-H3-01, CDD-049 §8). No `tenant_id` -- shared platform structure,
    identical classification to `information_element_requirements` and
    `QualityRule` itself (CDD-046 erratum)."""

    canonical_standard_id: UUID
    information_element_requirement_id: UUID
    version_number: int
    previous_version_id: UUID | None
    status: CanonicalStandardStatus
    created_by: str
    created_on: datetime
    values: tuple[CanonicalValue, ...]
    retired_on: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_standard_id, UUID):
            raise ValidationException("canonical_standard_id must be a UUID")
        if not isinstance(self.information_element_requirement_id, UUID):
            raise ValidationException("information_element_requirement_id must be a UUID")
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
        if not isinstance(self.status, CanonicalStandardStatus):
            raise ValidationException("status must be a CanonicalStandardStatus")
        if not isinstance(self.created_by, str) or not (
            1 <= len(self.created_by) <= _MAX_CREATED_BY_LENGTH
        ):
            raise ValidationException("created_by must be non-empty bounded text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")
        if self.status is CanonicalStandardStatus.ACTIVE and self.retired_on is not None:
            raise ValidationException("ACTIVE standards must not carry retired_on")
        if self.status is CanonicalStandardStatus.RETIRED and self.retired_on is None:
            raise ValidationException("RETIRED standards must carry retired_on")
        if self.retired_on is not None and self.retired_on.tzinfo is None:
            raise ValidationException("retired_on must include a timezone")
        if not isinstance(self.values, tuple) or not all(
            isinstance(value, CanonicalValue) for value in self.values
        ):
            raise ValidationException("values must be a tuple of CanonicalValue")
        for value in self.values:
            if value.canonical_standard_id != self.canonical_standard_id:
                raise ValidationException(
                    "every value must reference its own owning canonical_standard_id"
                )


def activate_new_standard_version(
    *,
    existing_active: CanonicalStandard | None,
    canonical_standard_id: UUID,
    information_element_requirement_id: UUID,
    created_by: str,
    created_on: datetime,
    values: tuple[CanonicalValue, ...],
) -> CanonicalStandard:
    """CDD-049 §10: constructs the next ACTIVE version for an Information
    Element. Retirement of `existing_active` (if any) is the caller's/
    repository's responsibility -- this function only ever returns the new
    version, never mutates `existing_active` in place (it is a frozen
    dataclass), mirroring `activate_new_assertion_version`'s exact precedent."""
    return CanonicalStandard(
        canonical_standard_id=canonical_standard_id,
        information_element_requirement_id=information_element_requirement_id,
        version_number=1 if existing_active is None else existing_active.version_number + 1,
        previous_version_id=(
            None if existing_active is None else existing_active.canonical_standard_id
        ),
        status=CanonicalStandardStatus.ACTIVE,
        created_by=created_by,
        created_on=created_on,
        values=values,
    )


@dataclass(frozen=True, slots=True)
class CanonicalizationResult:
    """CDD-049 §13: the resolver's exact, minimal, deterministic return
    shape. Sufficient provenance to reconstruct: what was observed, what it
    resolved to (if anything), whether the observed representation was
    itself already canonical, and exactly which governed standard/version
    produced the answer."""

    observed_representation: str
    resolution_state: CanonicalizationState
    resolved_canonical_value: str | None
    canonical_value_id: UUID | None
    canonical_standard_id: UUID | None
    standard_version: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.observed_representation, str):
            raise ValidationException("observed_representation must be text")
        if not isinstance(self.resolution_state, CanonicalizationState):
            raise ValidationException("resolution_state must be a CanonicalizationState")
        no_standard_states = {
            CanonicalizationState.NOT_MAPPED,
            CanonicalizationState.AMBIGUOUS,
            CanonicalizationState.NO_STANDARD,
        }
        if self.resolution_state in no_standard_states:
            if self.resolved_canonical_value is not None:
                raise ValidationException(
                    f"{self.resolution_state} must not carry a resolved_canonical_value"
                )
        elif self.resolved_canonical_value is None:
            raise ValidationException(
                f"{self.resolution_state} must carry a resolved_canonical_value"
            )
        if self.resolution_state is CanonicalizationState.NO_STANDARD:
            if self.canonical_standard_id is not None or self.standard_version is not None:
                raise ValidationException(
                    "NO_STANDARD must not carry canonical_standard_id/standard_version"
                )
        elif self.canonical_standard_id is None or self.standard_version is None:
            raise ValidationException(
                f"{self.resolution_state} must carry canonical_standard_id and standard_version"
            )
        if self.resolution_state in (
            CanonicalizationState.CANONICAL,
            CanonicalizationState.ALIAS_RESOLVED,
        ):
            if self.canonical_value_id is None:
                raise ValidationException(f"{self.resolution_state} must carry canonical_value_id")
        elif self.canonical_value_id is not None:
            raise ValidationException(f"{self.resolution_state} must not carry canonical_value_id")


def canonicalize(
    *, standard: CanonicalStandard | None, observed_representation: str
) -> CanonicalizationResult:
    """CDD-049 §13: the pure, deterministic canonicalization resolver.
    Comparison discipline is exact match, leading/trailing whitespace
    trimmed only -- no case-folding, no punctuation stripping, no fuzzy
    matching of any kind (§11) -- the narrowest possible generalization of
    `evaluate_consistency`'s own existing discipline
    (`app.domain.oqi_cross_source.evaluation.evaluate_consistency`,
    unmodified by this document). No import from
    `app.domain.identity_resolution` or any ER-internal module."""
    if standard is None or standard.status is not CanonicalStandardStatus.ACTIVE:
        return CanonicalizationResult(
            observed_representation=observed_representation,
            resolution_state=CanonicalizationState.NO_STANDARD,
            resolved_canonical_value=None,
            canonical_value_id=None,
            canonical_standard_id=None,
            standard_version=None,
        )

    trimmed = observed_representation.strip()

    canonical_matches = [
        value for value in standard.values if value.canonical_representation == trimmed
    ]
    alias_matches = [
        (value, alias)
        for value in standard.values
        for alias in value.aliases
        if alias.alias_representation == trimmed
    ]

    if len(canonical_matches) > 1 or (canonical_matches and alias_matches):
        return CanonicalizationResult(
            observed_representation=observed_representation,
            resolution_state=CanonicalizationState.AMBIGUOUS,
            resolved_canonical_value=None,
            canonical_value_id=None,
            canonical_standard_id=standard.canonical_standard_id,
            standard_version=standard.version_number,
        )
    if canonical_matches:
        matched = canonical_matches[0]
        return CanonicalizationResult(
            observed_representation=observed_representation,
            resolution_state=CanonicalizationState.CANONICAL,
            resolved_canonical_value=matched.canonical_representation,
            canonical_value_id=matched.canonical_value_id,
            canonical_standard_id=standard.canonical_standard_id,
            standard_version=standard.version_number,
        )
    if len(alias_matches) > 1:
        distinct_targets = {value.canonical_value_id for value, _alias in alias_matches}
        if len(distinct_targets) > 1:
            return CanonicalizationResult(
                observed_representation=observed_representation,
                resolution_state=CanonicalizationState.AMBIGUOUS,
                resolved_canonical_value=None,
                canonical_value_id=None,
                canonical_standard_id=standard.canonical_standard_id,
                standard_version=standard.version_number,
            )
    if alias_matches:
        matched_value, _matched_alias = alias_matches[0]
        return CanonicalizationResult(
            observed_representation=observed_representation,
            resolution_state=CanonicalizationState.ALIAS_RESOLVED,
            resolved_canonical_value=matched_value.canonical_representation,
            canonical_value_id=matched_value.canonical_value_id,
            canonical_standard_id=standard.canonical_standard_id,
            standard_version=standard.version_number,
        )
    return CanonicalizationResult(
        observed_representation=observed_representation,
        resolution_state=CanonicalizationState.NOT_MAPPED,
        resolved_canonical_value=None,
        canonical_value_id=None,
        canonical_standard_id=standard.canonical_standard_id,
        standard_version=standard.version_number,
    )
