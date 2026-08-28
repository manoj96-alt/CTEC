"""OQI governed quality-condition/rule identity and lifecycle (CDD-039
§9-§10, §16-§18, §31, §33-§34). `quality_condition_id` is the stable
governed semantic identity of one quality expectation (§16); no separate
persisted `QualityCondition` table exists -- it is carried directly on each
`QualityRule` version row. `dimension`/`finding_type`/`validity_primitive`
form a closed, exhaustive 4-row coupling (§10); `rule_parameters` shape is a
closed schema per Validity primitive (§31). `validate_rule_shape` is the
single, shared validation function CDD-039 §33 requires to be invoked
identically at construction, persistence/activation, and evaluation-time
defensive re-validation -- invalid governed rule definitions must never
become ACTIVE, and evaluation must fail closed on any residual malformed
state rather than fabricate an outcome."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.shared.exceptions import DomainException, ValidationException

# CDD-039 §20: "OQI_NAMESPACE = uuid5(NAMESPACE_URL, 'urn:ctec:oqi:v1') --
# fixed, frozen forever once implemented." Deliberately distinct from
# `app.core.bootstrap.BOOTSTRAP_SEED_NAMESPACE` (CDD-022's own namespace) so
# no OQI identity can ever collide with a FieldValueEvidence identity even
# under adversarially-chosen inputs.
OQI_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:v1")


class OqiMalformedRuleError(DomainException):
    """CDD-039 §33: raised whenever a governed rule definition's shape is
    invalid -- at construction, at persistence/activation, or (defensively)
    at evaluation time. Never caught to silently fabricate SATISFIED or
    VIOLATED."""


class QualityDimension(StrEnum):
    """CDD-039 §9: exactly these two, closed."""

    COMPLETENESS = "COMPLETENESS"
    VALIDITY = "VALIDITY"


class QualityFindingType(StrEnum):
    """CDD-039 §10: exactly these four, closed."""

    MISSING_VALUE = "MISSING_VALUE"
    ENUM_VIOLATION = "ENUM_VIOLATION"
    FORMAT_VIOLATION = "FORMAT_VIOLATION"
    RANGE_VIOLATION = "RANGE_VIOLATION"


class ValidityPrimitive(StrEnum):
    """CDD-039 §10: exactly these three, closed. `FORMAT_VIOLATION`/
    `RANGE_VIOLATION` deliberately share their literal names with the
    corresponding `QualityFindingType` members -- CDD-039 §10 states this is
    intentional and binding, not a naming defect to silently disambiguate."""

    ENUM_MEMBERSHIP = "ENUM_MEMBERSHIP"
    FORMAT_VIOLATION = "FORMAT_VIOLATION"
    RANGE_VIOLATION = "RANGE_VIOLATION"


class QualityRuleStatus(StrEnum):
    """CDD-039 §18: exactly these two, closed. No DRAFT, no DELETED."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


# CDD-039 §10's closed, exhaustive 4-row coupling table:
#   COMPLETENESS -> MISSING_VALUE   -> validity_primitive = None
#   VALIDITY     -> ENUM_VIOLATION  -> validity_primitive = ENUM_MEMBERSHIP
#   VALIDITY     -> FORMAT_VIOLATION -> validity_primitive = FORMAT_VIOLATION
#   VALIDITY     -> RANGE_VIOLATION  -> validity_primitive = RANGE_VIOLATION
_ALLOWED_COMBINATIONS: frozenset[
    tuple[QualityDimension, QualityFindingType, ValidityPrimitive | None]
] = frozenset(
    {
        (QualityDimension.COMPLETENESS, QualityFindingType.MISSING_VALUE, None),
        (
            QualityDimension.VALIDITY,
            QualityFindingType.ENUM_VIOLATION,
            ValidityPrimitive.ENUM_MEMBERSHIP,
        ),
        (
            QualityDimension.VALIDITY,
            QualityFindingType.FORMAT_VIOLATION,
            ValidityPrimitive.FORMAT_VIOLATION,
        ),
        (
            QualityDimension.VALIDITY,
            QualityFindingType.RANGE_VIOLATION,
            ValidityPrimitive.RANGE_VIOLATION,
        ),
    }
)

_MAX_CONDITION_ID_LENGTH = 200
_MAX_REQUIREMENT_ID_LENGTH = 200


def _require_numeric(value: Any, *, label: str) -> float:
    """Rejects bool explicitly -- `isinstance(True, int)` is `True` in
    Python, and a boolean range bound would silently coerce to 0/1."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise OqiMalformedRuleError(f"{label} must be a number, not {value!r}")
    return float(value)


def validate_rule_shape(
    *,
    dimension: QualityDimension,
    finding_type: QualityFindingType,
    validity_primitive: ValidityPrimitive | None,
    rule_parameters: Mapping[str, Any],
) -> None:
    """CDD-039 §33: the single, shared validation function reused at
    construction, persistence/activation, and evaluation-time defensive
    re-validation. Raises `OqiMalformedRuleError` on any shape violation."""
    combination = (dimension, finding_type, validity_primitive)
    if combination not in _ALLOWED_COMBINATIONS:
        raise OqiMalformedRuleError(
            f"Invalid dimension/finding_type/validity_primitive combination: {combination!r}"
        )
    if not isinstance(rule_parameters, Mapping):
        raise OqiMalformedRuleError("rule_parameters must be a mapping")

    if dimension is QualityDimension.COMPLETENESS:
        if dict(rule_parameters) != {}:
            raise OqiMalformedRuleError("COMPLETENESS rule_parameters must be empty")
        return

    if validity_primitive is ValidityPrimitive.ENUM_MEMBERSHIP:
        allowed_keys = {"allowed_values"}
        if set(rule_parameters.keys()) != allowed_keys:
            raise OqiMalformedRuleError(
                f"ENUM_MEMBERSHIP rule_parameters must contain exactly {allowed_keys}"
            )
        allowed_values = rule_parameters["allowed_values"]
        if not isinstance(allowed_values, list) or not allowed_values:
            raise OqiMalformedRuleError("allowed_values must be a non-empty list")
        if not all(isinstance(item, str) for item in allowed_values):
            raise OqiMalformedRuleError("allowed_values must contain only strings")
        if len(set(allowed_values)) != len(allowed_values):
            raise OqiMalformedRuleError("allowed_values must not contain duplicates")
        return

    if validity_primitive is ValidityPrimitive.FORMAT_VIOLATION:
        allowed_keys = {"pattern"}
        if set(rule_parameters.keys()) != allowed_keys:
            raise OqiMalformedRuleError(
                f"FORMAT_VIOLATION rule_parameters must contain exactly {allowed_keys}"
            )
        pattern = rule_parameters["pattern"]
        if not isinstance(pattern, str) or not pattern:
            raise OqiMalformedRuleError("pattern must be a non-empty string")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise OqiMalformedRuleError(
                f"pattern is not a valid regular expression: {exc}"
            ) from exc
        return

    if validity_primitive is ValidityPrimitive.RANGE_VIOLATION:
        allowed_keys = {"min", "max"}
        if set(rule_parameters.keys()) != allowed_keys:
            raise OqiMalformedRuleError(
                f"RANGE_VIOLATION rule_parameters must contain exactly {allowed_keys}"
            )
        minimum = rule_parameters["min"]
        maximum = rule_parameters["max"]
        if minimum is None and maximum is None:
            raise OqiMalformedRuleError("RANGE_VIOLATION requires at least one of min/max")
        parsed_min = None if minimum is None else _require_numeric(minimum, label="min")
        parsed_max = None if maximum is None else _require_numeric(maximum, label="max")
        if parsed_min is not None and parsed_max is not None and parsed_min > parsed_max:
            raise OqiMalformedRuleError("RANGE_VIOLATION requires min <= max")
        return

    raise OqiMalformedRuleError(f"Unhandled validity_primitive: {validity_primitive!r}")


def derive_quality_rule_id(*, quality_condition_id: str, version: int) -> UUID:
    """CDD-039 Persistence model (§39): `rule_id` is deterministic, not
    server-generated, so re-running a seed/activation is naturally
    idempotent."""
    return uuid5(OQI_NAMESPACE, f"quality_rule:{quality_condition_id}:{version}")


@dataclass(frozen=True, slots=True)
class QualityRule:
    rule_id: UUID
    quality_condition_id: str
    version: int
    dimension: QualityDimension
    finding_type: QualityFindingType
    validity_primitive: ValidityPrimitive | None
    information_element_requirement_id: str
    rule_parameters: Mapping[str, Any]
    status: QualityRuleStatus
    created_by: str
    created_on: datetime
    retired_on: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, UUID):
            raise ValidationException("rule_id must be a UUID")
        if not isinstance(self.quality_condition_id, str) or not (
            1 <= len(self.quality_condition_id) <= _MAX_CONDITION_ID_LENGTH
        ):
            raise ValidationException(
                f"quality_condition_id must be non-empty text of length <= "
                f"{_MAX_CONDITION_ID_LENGTH}"
            )
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValidationException("version must be a positive integer")
        if not isinstance(self.dimension, QualityDimension):
            raise ValidationException("dimension must be a QualityDimension")
        if not isinstance(self.finding_type, QualityFindingType):
            raise ValidationException("finding_type must be a QualityFindingType")
        if self.validity_primitive is not None and not isinstance(
            self.validity_primitive, ValidityPrimitive
        ):
            raise ValidationException("validity_primitive must be a ValidityPrimitive or None")
        if not isinstance(self.information_element_requirement_id, str) or not (
            1 <= len(self.information_element_requirement_id) <= _MAX_REQUIREMENT_ID_LENGTH
        ):
            raise ValidationException(
                "information_element_requirement_id must be non-empty text of length <= "
                f"{_MAX_REQUIREMENT_ID_LENGTH}"
            )
        if not isinstance(self.status, QualityRuleStatus):
            raise ValidationException("status must be a QualityRuleStatus")
        if not isinstance(self.created_by, str) or not self.created_by.strip():
            raise ValidationException("created_by must be non-blank text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")
        if self.status is QualityRuleStatus.ACTIVE and self.retired_on is not None:
            raise ValidationException("ACTIVE rules must not carry retired_on")
        if self.status is QualityRuleStatus.RETIRED and self.retired_on is None:
            raise ValidationException("RETIRED rules must carry retired_on")
        if self.retired_on is not None and self.retired_on.tzinfo is None:
            raise ValidationException("retired_on must include a timezone")

        # CDD-039 §33 point 1: construction-time enforcement.
        validate_rule_shape(
            dimension=self.dimension,
            finding_type=self.finding_type,
            validity_primitive=self.validity_primitive,
            rule_parameters=self.rule_parameters,
        )

        expected_id = derive_quality_rule_id(
            quality_condition_id=self.quality_condition_id, version=self.version
        )
        if self.rule_id != expected_id:
            raise ValidationException(
                "rule_id is inconsistent with its own governed semantic identity inputs"
            )

    @classmethod
    def new(
        cls,
        *,
        quality_condition_id: str,
        version: int,
        dimension: QualityDimension,
        finding_type: QualityFindingType,
        validity_primitive: ValidityPrimitive | None,
        information_element_requirement_id: str,
        rule_parameters: Mapping[str, Any],
        status: QualityRuleStatus,
        created_by: str,
        created_on: datetime,
        retired_on: datetime | None = None,
    ) -> QualityRule:
        rule_id = derive_quality_rule_id(quality_condition_id=quality_condition_id, version=version)
        return cls(
            rule_id=rule_id,
            quality_condition_id=quality_condition_id,
            version=version,
            dimension=dimension,
            finding_type=finding_type,
            validity_primitive=validity_primitive,
            information_element_requirement_id=information_element_requirement_id,
            rule_parameters=rule_parameters,
            status=status,
            created_by=created_by,
            created_on=created_on,
            retired_on=retired_on,
        )
