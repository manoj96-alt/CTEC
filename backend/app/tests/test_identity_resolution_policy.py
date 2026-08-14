from collections.abc import Callable
from typing import Any

import pytest

from app.domain.identity_resolution.model import EvidenceType
from app.domain.identity_resolution.policy import (
    PRESET_FACTORIES,
    ResolutionPolicyDefinition,
    balanced_preset,
    conservative_preset,
    exploratory_preset,
)
from app.domain.shared.exceptions import ValidationException


def _minimal_kwargs(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = dict(
        policy_name="Test Policy",
        policy_version="v1.0",
        resolved_threshold=0.9,
        possible_threshold=0.5,
        high_confidence_threshold=0.9,
        medium_confidence_threshold=0.5,
        min_corroborating_attributes=1,
        participating_evidence_types=(EvidenceType.LEGAL_NAME_MATCH, EvidenceType.DOMAIN_VERIFIED),
        mandatory_auto_resolution_evidence=(),
        evidence_weights={EvidenceType.LEGAL_NAME_MATCH: 0.1, EvidenceType.DOMAIN_VERIFIED: 0.3},
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Built-in presets are constructible and materially different
# ---------------------------------------------------------------------------


def test_all_three_presets_are_constructible() -> None:
    assert conservative_preset().policy_name == "Conservative"
    assert balanced_preset().policy_name == "Balanced"
    assert exploratory_preset().policy_name == "Exploratory"


def test_preset_factories_registry_matches_the_three_named_presets() -> None:
    assert set(PRESET_FACTORIES) == {"Conservative", "Balanced", "Exploratory"}
    assert PRESET_FACTORIES["Conservative"]().policy_name == "Conservative"


def test_conservative_requires_a_strong_identifier_for_auto_resolution() -> None:
    policy = conservative_preset()
    assert policy.mandatory_auto_resolution_evidence
    assert policy.country_conflict_severity == "veto"
    assert policy.parent_subsidiary_conflict_severity == "veto"


def test_balanced_has_no_mandatory_strong_identifier_but_still_gates_on_corroboration() -> None:
    policy = balanced_preset()
    assert policy.mandatory_auto_resolution_evidence == ()
    assert policy.min_corroborating_attributes >= 2
    assert policy.country_conflict_severity == "review"


def test_exploratory_has_the_lowest_thresholds_of_the_three() -> None:
    conservative = conservative_preset()
    balanced = balanced_preset()
    exploratory = exploratory_preset()
    assert (
        exploratory.resolved_threshold
        < balanced.resolved_threshold
        < conservative.resolved_threshold
    )
    assert (
        exploratory.possible_threshold
        < balanced.possible_threshold
        < conservative.possible_threshold
    )
    assert exploratory.min_corroborating_attributes <= balanced.min_corroborating_attributes


def test_sensitive_value_masking_is_true_on_every_preset() -> None:
    for factory in PRESET_FACTORIES.values():
        assert factory().sensitive_value_masking is True


# ---------------------------------------------------------------------------
# Round trip through the persisted JSON representation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", [conservative_preset, balanced_preset, exploratory_preset])
def test_definition_round_trips_through_dict_form(
    factory: Callable[[], ResolutionPolicyDefinition],
) -> None:
    original = factory()
    restored = ResolutionPolicyDefinition.from_definition_dict(original.to_definition_dict())
    assert restored == original


def test_from_definition_dict_rejects_unknown_keys() -> None:
    raw = conservative_preset().to_definition_dict()
    raw["not_a_real_field"] = True
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition.from_definition_dict(raw)


def test_from_definition_dict_rejects_missing_keys() -> None:
    raw = conservative_preset().to_definition_dict()
    del raw["resolved_threshold"]
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition.from_definition_dict(raw)


def test_from_definition_dict_rejects_non_dict_input() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition.from_definition_dict(["not", "a", "dict"])  # type: ignore[arg-type]


def test_from_definition_dict_rejects_unknown_evidence_type_value() -> None:
    raw = conservative_preset().to_definition_dict()
    raw["participating_evidence_types"] = ["Not A Real Evidence Type"]
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition.from_definition_dict(raw)


# ---------------------------------------------------------------------------
# Validation / invalid policy rejection
# ---------------------------------------------------------------------------


def test_blank_policy_name_is_rejected() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(policy_name="   "))


def test_blank_policy_version_is_rejected() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(policy_version=""))


@pytest.mark.parametrize(
    "field_name",
    [
        "resolved_threshold",
        "possible_threshold",
        "high_confidence_threshold",
        "medium_confidence_threshold",
    ],
)
def test_thresholds_outside_zero_to_one_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(**{field_name: 1.5}))
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(**{field_name: -0.1}))


def test_resolved_threshold_must_exceed_possible_threshold() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(
            **_minimal_kwargs(resolved_threshold=0.5, possible_threshold=0.5)
        )
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(
            **_minimal_kwargs(resolved_threshold=0.4, possible_threshold=0.5)
        )


def test_high_confidence_threshold_must_be_at_least_medium() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(
            **_minimal_kwargs(high_confidence_threshold=0.3, medium_confidence_threshold=0.5)
        )


def test_min_corroborating_attributes_must_be_at_least_one() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(min_corroborating_attributes=0))


def test_participating_evidence_types_must_not_be_empty() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(participating_evidence_types=()))


def test_mandatory_evidence_must_be_a_governed_strong_identifier_type() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(
            **_minimal_kwargs(
                participating_evidence_types=(EvidenceType.LEGAL_NAME_MATCH,),
                mandatory_auto_resolution_evidence=(EvidenceType.LEGAL_NAME_MATCH,),
            )
        )


def test_mandatory_evidence_must_be_a_subset_of_participating_types() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(
            **_minimal_kwargs(
                participating_evidence_types=(EvidenceType.LEGAL_NAME_MATCH,),
                mandatory_auto_resolution_evidence=(EvidenceType.STRONG_IDENTIFIER_LEI,),
            )
        )


def test_evidence_weights_must_reference_participating_types_only() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(
            **_minimal_kwargs(
                participating_evidence_types=(EvidenceType.LEGAL_NAME_MATCH,),
                evidence_weights={EvidenceType.DOMAIN_VERIFIED: 0.5},
            )
        )


@pytest.mark.parametrize("bad_weight", [0.0, -0.1, 1.1])
def test_evidence_weights_must_be_strictly_between_zero_and_one(bad_weight: float) -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(
            **_minimal_kwargs(
                evidence_weights={EvidenceType.LEGAL_NAME_MATCH: bad_weight},
                participating_evidence_types=(EvidenceType.LEGAL_NAME_MATCH,),
            )
        )


def test_source_system_trust_weights_reject_blank_keys() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(source_system_trust_weights={"  ": 1.0}))


@pytest.mark.parametrize("bad_weight", [0.0, -0.5, 2.1])
def test_source_system_trust_weights_must_be_between_zero_and_two(bad_weight: float) -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(
            **_minimal_kwargs(source_system_trust_weights={"CRM": bad_weight})
        )


def test_country_conflict_severity_must_be_veto_or_review() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(country_conflict_severity="ignore"))


def test_parent_subsidiary_conflict_severity_must_be_veto_or_review() -> None:
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(parent_subsidiary_conflict_severity="ignore"))


def test_sensitive_value_masking_cannot_be_disabled_by_policy() -> None:
    """A hard security invariant: no customer-configurable knob may turn off
    sensitive-value fingerprinting."""
    with pytest.raises(ValidationException):
        ResolutionPolicyDefinition(**_minimal_kwargs(sensitive_value_masking=False))


def test_valid_minimal_policy_constructs_successfully() -> None:
    policy = ResolutionPolicyDefinition(**_minimal_kwargs())
    assert policy.policy_name == "Test Policy"
