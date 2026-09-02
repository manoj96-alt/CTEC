"""OQI-H2 generalized Finding-origin value object (CDD-048 §12). Resolves
the G0 architectural prerequisite: `FindingFamily` has always meant "which
physical table stores this Finding" (WHERE), never "which quality dimension
produced it" (WHAT) -- the two happened, prior to this document, to always
coincide. `QualityFindingOrigin` makes both axes explicit and independently
readable.

`FindingStorageFamily` is `FindingFamily` (`app.domain.oqi_ontology_impact.
evaluation.FindingFamily`) renamed in code identity only -- its three
persisted string values (`"OQI1"`, `"OQI2"`, `"OQI3"`) are byte-identical
and unchanged (CDD-048 §12.2, §13). It gains zero new members in H2: Accuracy
reuses OQI1's physical storage (`quality_findings`); Reasonableness reuses
OQI3's (`business_rule_findings`).

`QualityFindingOrigin` is deliberately NEVER persisted as its own table
(CDD-048 §12.2) -- `quality_dimension` is derived at read time, safely and
immutably, from data that already exists: the static `finding_type ->
quality_dimension` mapping for OQI1-shaped Findings (including Accuracy),
`BusinessRule.dimension`/purpose for OQI3-shaped Findings (including
Reasonableness), or the `CONSISTENCY` constant for OQI2-shaped Findings.

`LEGACY_UNCLASSIFIED_BUSINESS_RULE` is the frozen, honest, non-fabricated
treatment for pre-H2 `BusinessRule` rows that carry no real semantic-
dimension information (CDD-048 §13) -- never retroactively claimed to be
REASONABLENESS. It is deliberately NOT a member of `QualityDimension` itself
(which remains exactly the five real, implemented dimensions) -- it is a
distinct governance sentinel, valid only as a `QualityFindingOrigin.
quality_dimension` value."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.oqi.quality_rule import QualityDimension, QualityFindingType
from app.domain.oqi_ontology_impact.evaluation import FindingFamily
from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200

#: CDD-048 §13: the frozen, honest default for a legacy OQI3 BusinessRule
#: Finding whose rule was created before dimension/purpose tagging existed.
#: Deliberately not a QualityDimension member -- see module docstring.
LEGACY_UNCLASSIFIED_BUSINESS_RULE = "LEGACY_UNCLASSIFIED_BUSINESS_RULE"

#: CDD-048 §12.2: every value a QualityFindingOrigin.quality_dimension may
#: legitimately carry -- the five real QualityDimension members plus the one
#: legacy sentinel above. Closed; never silently widened.
_VALID_QUALITY_DIMENSION_VALUES: frozenset[str] = frozenset(
    {member.value for member in QualityDimension} | {LEGACY_UNCLASSIFIED_BUSINESS_RULE}
)


class FindingStorageFamily(StrEnum):
    """CDD-048 §12.2: `FindingFamily` renamed in code identity only. Closed,
    exactly these three -- zero new members in H2. Answers WHERE a Finding
    is physically stored, never WHAT quality dimension it represents."""

    OQI1 = "OQI1"
    OQI2 = "OQI2"
    OQI3 = "OQI3"


def storage_family_from_finding_family(finding_family: FindingFamily) -> FindingStorageFamily:
    """Pure, value-preserving conversion -- both enums share identical
    string values by construction (CDD-048 §12.2)."""
    return FindingStorageFamily(finding_family.value)


def finding_family_from_storage_family(storage_family: FindingStorageFamily) -> FindingFamily:
    """The inverse of `storage_family_from_finding_family`, for call sites
    (e.g. OQI4/OQI5's existing dispatch) that still expect the original
    `FindingFamily` type -- unchanged, unmodified by this document."""
    return FindingFamily(storage_family.value)


#: CDD-048 §12.2: the static, deterministic `finding_type ->
#: quality_dimension` mapping for OQI1-storage-family Findings (including
#: Accuracy, which reuses OQI1's physical tables). This mapping was already
#: implicit in `QualityFindingType`'s own member grouping before this
#: document (CDD-039/CDD-040); `REFERENCE_VALUE_UNSUPPORTED -> ACCURACY` is
#: the one new entry this document adds.
_OQI1_FINDING_TYPE_TO_DIMENSION: dict[QualityFindingType, QualityDimension] = {
    QualityFindingType.MISSING_VALUE: QualityDimension.COMPLETENESS,
    QualityFindingType.ENUM_VIOLATION: QualityDimension.VALIDITY,
    QualityFindingType.FORMAT_VIOLATION: QualityDimension.VALIDITY,
    QualityFindingType.RANGE_VIOLATION: QualityDimension.VALIDITY,
    QualityFindingType.REFERENCE_VALUE_UNSUPPORTED: QualityDimension.ACCURACY,
}


def quality_dimension_for_oqi1_finding_type(finding_type: QualityFindingType) -> QualityDimension:
    """CDD-048 §12.2: derives the semantic quality dimension for an
    OQI1-storage-family Finding from its own `finding_type` -- requires no
    new column on `quality_findings`/`quality_evaluations`. Deliberately
    excludes `CROSS_SOURCE_VALUE_CONFLICT`/
    `CROSS_SOURCE_PARTICIPANT_VALUE_MISSING` -- those are OQI2-storage-family
    finding types (always `CONSISTENCY`, handled separately, never routed
    through this OQI1-only mapping)."""
    try:
        return _OQI1_FINDING_TYPE_TO_DIMENSION[finding_type]
    except KeyError as exc:
        raise ValidationException(
            f"no governed OQI1-storage-family quality_dimension mapping exists for "
            f"finding_type {finding_type!r}"
        ) from exc


@dataclass(frozen=True, slots=True)
class QualityFindingOrigin:
    """CDD-048 §12: the generalized Finding-origin value object. NEVER
    persisted as its own table (CDD-048 §12.2) -- constructed on demand by
    the storage-family-specific adapter (`OqiOntologyImpactEvaluationRepositoryImpl
    .resolve_finding_origin`) from data already safely, immutably derivable.

    `quality_dimension` is `None` only when no governed dimension could be
    resolved at all (this should never occur for a Finding that legitimately
    exists -- every OQI1/OQI2/OQI3(-legacy) Finding has a resolvable value,
    the legacy case included, via `LEGACY_UNCLASSIFIED_BUSINESS_RULE`); the
    type permits it defensively rather than fabricating a value."""

    tenant_id: str
    finding_storage_family: FindingStorageFamily
    quality_dimension: str | None
    finding_id: UUID
    finding_state_revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.finding_storage_family, FindingStorageFamily):
            raise ValidationException("finding_storage_family must be a FindingStorageFamily")
        if self.quality_dimension is not None and (
            not isinstance(self.quality_dimension, str)
            or self.quality_dimension not in _VALID_QUALITY_DIMENSION_VALUES
        ):
            raise ValidationException(
                "quality_dimension must be None or one of the governed QualityDimension "
                f"values / {LEGACY_UNCLASSIFIED_BUSINESS_RULE!r}"
            )
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if (
            not isinstance(self.finding_state_revision, int)
            or isinstance(self.finding_state_revision, bool)
            or self.finding_state_revision < 1
        ):
            raise ValidationException("finding_state_revision must be a positive integer")
