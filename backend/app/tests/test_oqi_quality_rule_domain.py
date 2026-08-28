"""Pure domain unit tests for `app.domain.oqi.quality_rule` (CDD-039 §9-§10,
§16-§18, §31, §33-§34; OQI1 Artifact Authorization §4)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.oqi.quality_rule import (
    OqiMalformedRuleError,
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
    ValidityPrimitive,
    derive_quality_rule_id,
    validate_rule_shape,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime.now(UTC)


def _make_rule(
    *,
    quality_condition_id: str = "cond-1",
    version: int = 1,
    dimension: QualityDimension = QualityDimension.COMPLETENESS,
    finding_type: QualityFindingType = QualityFindingType.MISSING_VALUE,
    validity_primitive: ValidityPrimitive | None = None,
    rule_parameters: dict[str, object] | None = None,
    status: QualityRuleStatus = QualityRuleStatus.ACTIVE,
    retired_on: datetime | None = None,
) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=quality_condition_id,
        version=version,
        dimension=dimension,
        finding_type=finding_type,
        validity_primitive=validity_primitive,
        information_element_requirement_id="req-1",
        rule_parameters={} if rule_parameters is None else rule_parameters,
        status=status,
        created_by="steward",
        created_on=NOW,
        retired_on=retired_on,
    )


# --- rule identity determinism ---


def test_rule_id_is_deterministic() -> None:
    a = derive_quality_rule_id(quality_condition_id="cond-1", version=1)
    b = derive_quality_rule_id(quality_condition_id="cond-1", version=1)
    assert a == b


def test_rule_id_differs_by_version() -> None:
    a = derive_quality_rule_id(quality_condition_id="cond-1", version=1)
    b = derive_quality_rule_id(quality_condition_id="cond-1", version=2)
    assert a != b


def test_rule_id_differs_by_condition() -> None:
    a = derive_quality_rule_id(quality_condition_id="cond-1", version=1)
    b = derive_quality_rule_id(quality_condition_id="cond-2", version=1)
    assert a != b


def test_new_rule_has_consistent_id() -> None:
    rule = _make_rule()
    assert rule.rule_id == derive_quality_rule_id(quality_condition_id="cond-1", version=1)


def test_rehydrated_rule_with_wrong_id_is_rejected() -> None:
    with pytest.raises(ValidationException):
        QualityRule(
            rule_id=derive_quality_rule_id(quality_condition_id="cond-1", version=2),
            quality_condition_id="cond-1",
            version=1,
            dimension=QualityDimension.COMPLETENESS,
            finding_type=QualityFindingType.MISSING_VALUE,
            validity_primitive=None,
            information_element_requirement_id="req-1",
            rule_parameters={},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )


# --- dimension/finding-type/primitive coupling ---


def test_completeness_missing_value_none_primitive_is_valid() -> None:
    validate_rule_shape(
        dimension=QualityDimension.COMPLETENESS,
        finding_type=QualityFindingType.MISSING_VALUE,
        validity_primitive=None,
        rule_parameters={},
    )


@pytest.mark.parametrize(
    ("finding_type", "primitive"),
    [
        (QualityFindingType.ENUM_VIOLATION, ValidityPrimitive.ENUM_MEMBERSHIP),
        (QualityFindingType.FORMAT_VIOLATION, ValidityPrimitive.FORMAT_VIOLATION),
        (QualityFindingType.RANGE_VIOLATION, ValidityPrimitive.RANGE_VIOLATION),
    ],
)
def test_validity_couplings_are_valid(
    finding_type: QualityFindingType, primitive: ValidityPrimitive
) -> None:
    parameters_by_primitive: dict[ValidityPrimitive, dict[str, object]] = {
        ValidityPrimitive.ENUM_MEMBERSHIP: {"allowed_values": ["A"]},
        ValidityPrimitive.FORMAT_VIOLATION: {"pattern": ".*"},
        ValidityPrimitive.RANGE_VIOLATION: {"min": 0, "max": 1},
    }
    parameters = parameters_by_primitive[primitive]
    validate_rule_shape(
        dimension=QualityDimension.VALIDITY,
        finding_type=finding_type,
        validity_primitive=primitive,
        rule_parameters=parameters,
    )


def test_invalid_combination_completeness_with_primitive_is_rejected() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.COMPLETENESS,
            finding_type=QualityFindingType.MISSING_VALUE,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            rule_parameters={},
        )


def test_invalid_combination_validity_missing_value_is_rejected() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.MISSING_VALUE,
            validity_primitive=None,
            rule_parameters={},
        )


def test_mismatched_finding_type_and_primitive_is_rejected() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.RANGE_VIOLATION,
            rule_parameters={"min": 0, "max": 1},
        )


# --- rule_parameters shape validation, per primitive ---


def test_completeness_rejects_non_empty_parameters() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.COMPLETENESS,
            finding_type=QualityFindingType.MISSING_VALUE,
            validity_primitive=None,
            rule_parameters={"unexpected": 1},
        )


def test_enum_membership_requires_non_empty_allowed_values() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            rule_parameters={"allowed_values": []},
        )


def test_enum_membership_rejects_non_string_members() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            rule_parameters={"allowed_values": ["A", 1]},
        )


def test_enum_membership_rejects_duplicates() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            rule_parameters={"allowed_values": ["A", "A"]},
        )


def test_enum_membership_rejects_extra_keys() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            rule_parameters={"allowed_values": ["A"], "extra": 1},
        )


def test_format_requires_pattern_key_only() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.FORMAT_VIOLATION,
            validity_primitive=ValidityPrimitive.FORMAT_VIOLATION,
            rule_parameters={},
        )


def test_format_rejects_invalid_regex() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.FORMAT_VIOLATION,
            validity_primitive=ValidityPrimitive.FORMAT_VIOLATION,
            rule_parameters={"pattern": "("},
        )


def test_range_requires_at_least_one_bound() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.RANGE_VIOLATION,
            validity_primitive=ValidityPrimitive.RANGE_VIOLATION,
            rule_parameters={"min": None, "max": None},
        )


def test_range_requires_min_lte_max() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.RANGE_VIOLATION,
            validity_primitive=ValidityPrimitive.RANGE_VIOLATION,
            rule_parameters={"min": 10, "max": 1},
        )


def test_range_rejects_boolean_bounds() -> None:
    with pytest.raises(OqiMalformedRuleError):
        validate_rule_shape(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.RANGE_VIOLATION,
            validity_primitive=ValidityPrimitive.RANGE_VIOLATION,
            rule_parameters={"min": True, "max": 10},
        )


def test_range_accepts_single_bound() -> None:
    validate_rule_shape(
        dimension=QualityDimension.VALIDITY,
        finding_type=QualityFindingType.RANGE_VIOLATION,
        validity_primitive=ValidityPrimitive.RANGE_VIOLATION,
        rule_parameters={"min": 0, "max": None},
    )


# --- construction-time enforcement (CDD-039 §33 point 1) ---


def test_construction_rejects_malformed_rule_shape() -> None:
    with pytest.raises(OqiMalformedRuleError):
        _make_rule(
            dimension=QualityDimension.VALIDITY,
            finding_type=QualityFindingType.ENUM_VIOLATION,
            validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
            rule_parameters={"allowed_values": []},
        )


# --- lifecycle invariants ---


def test_active_rule_must_not_carry_retired_on() -> None:
    with pytest.raises(ValidationException):
        _make_rule(status=QualityRuleStatus.ACTIVE, retired_on=NOW)


def test_retired_rule_must_carry_retired_on() -> None:
    with pytest.raises(ValidationException):
        _make_rule(status=QualityRuleStatus.RETIRED, retired_on=None)


def test_retired_rule_with_retired_on_is_valid() -> None:
    rule = _make_rule(status=QualityRuleStatus.RETIRED, retired_on=NOW)
    assert rule.status is QualityRuleStatus.RETIRED
    assert rule.retired_on == NOW


def test_version_must_be_positive() -> None:
    with pytest.raises(ValidationException):
        _make_rule(version=0)
