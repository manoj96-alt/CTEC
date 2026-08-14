from typing import Any
from uuid import uuid4

import pytest

from app.domain.identity_resolution.evidence import (
    SourceRepresentation,
    build_evidence_profile,
    decide,
)
from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EvidenceClassification,
    EvidenceType,
    ResolutionOutcome,
)
from app.domain.identity_resolution.policy import (
    balanced_preset,
    conservative_preset,
    exploratory_preset,
)
from app.domain.shared.exceptions import ValidationException


def _rep(**overrides: Any) -> SourceRepresentation:
    defaults: dict[str, Any] = {
        "source_object_id": uuid4(),
        "source_system_name": overrides.pop("source_system_name", f"system-{uuid4()}"),
        "display_name": "Acme Widgets",
    }
    defaults.update(overrides)
    return SourceRepresentation(**defaults)


def _tsmc_representations() -> tuple[SourceRepresentation, ...]:
    return (
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="CRM",
            display_name="TSMC",
            acronym="TSMC",
            website_domain="tsmc.com",
            country="Taiwan",
        ),
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="ERP",
            display_name="TSMC Inc.",
            acronym="TSMC",
            country="Taiwan",
        ),
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="Registry",
            display_name="Taiwan Semiconductor Manufacturing Company Limited",
            website_domain="tsmc.com",
            country="Taiwan",
        ),
    )


CANDIDATE_NAME = "Taiwan Semiconductor Manufacturing Company Limited"


# ---------------------------------------------------------------------------
# TSMC demonstration case
# ---------------------------------------------------------------------------


def test_tsmc_case_under_conservative_is_steward_review_medium_confidence() -> None:
    policy = conservative_preset()
    profile = build_evidence_profile(
        representations=_tsmc_representations(),
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)

    assert decision.outcome is ResolutionOutcome.POSSIBLE
    assert decision.business_confidence is BusinessConfidence.MEDIUM
    # No strong identifier evidence at all -- explicitly missing, not merely absent.
    tax_item = next(
        i
        for i in profile.items
        if i.evidence_type is EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION
    )
    assert tax_item.classification is EvidenceClassification.MISSING
    lei_item = next(
        i for i in profile.items if i.evidence_type is EvidenceType.STRONG_IDENTIFIER_LEI
    )
    assert lei_item.classification is EvidenceClassification.MISSING

    acronym_item = next(i for i in profile.items if i.evidence_type is EvidenceType.ACRONYM_MATCH)
    assert acronym_item.classification is EvidenceClassification.POSITIVE
    assert acronym_item.normalized_values == ("TSMC",)

    suffix_item = next(
        i for i in profile.items if i.evidence_type is EvidenceType.LEGAL_SUFFIX_NORMALIZED
    )
    assert suffix_item.classification is EvidenceClassification.POSITIVE

    domain_item = next(i for i in profile.items if i.evidence_type is EvidenceType.DOMAIN_VERIFIED)
    assert domain_item.classification is EvidenceClassification.POSITIVE
    assert domain_item.normalized_values == ("tsmc.com",)

    country_item = next(i for i in profile.items if i.evidence_type is EvidenceType.COUNTRY_MATCH)
    assert country_item.classification is EvidenceClassification.POSITIVE

    # Every agreement and every missing identifier is explained.
    for item in profile.items:
        assert item.explanation.strip()
        assert item.provenance.strip()


def test_tsmc_case_with_matching_strong_identifier_resolves() -> None:
    policy = conservative_preset()
    reps = tuple(
        SourceRepresentation(
            source_object_id=r.source_object_id,
            source_system_name=r.source_system_name,
            display_name=r.display_name,
            acronym=r.acronym,
            website_domain=r.website_domain,
            country=r.country,
            strong_identifiers=(
                (EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION, "GOV-REG-24894001"),
            ),
        )
        for r in _tsmc_representations()
    )
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)

    assert decision.outcome is ResolutionOutcome.RESOLVED
    assert decision.business_confidence is BusinessConfidence.HIGH
    tax_item = next(
        i
        for i in profile.items
        if i.evidence_type is EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION
    )
    assert tax_item.classification is EvidenceClassification.POSITIVE
    # The raw registration number must never appear in the evidence item.
    assert "GOV-REG-24894001" not in tax_item.normalized_values[0]
    assert tax_item.normalized_values[0].startswith("fp:")


def test_tsmc_case_with_conflicting_strong_identifiers_is_blocked_regardless_of_score() -> None:
    policy = conservative_preset()
    base_reps = _tsmc_representations()
    reps = (
        SourceRepresentation(
            source_object_id=base_reps[0].source_object_id,
            source_system_name=base_reps[0].source_system_name,
            display_name=base_reps[0].display_name,
            acronym=base_reps[0].acronym,
            website_domain=base_reps[0].website_domain,
            country=base_reps[0].country,
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION, "GOV-REG-AAA"),),
        ),
        SourceRepresentation(
            source_object_id=base_reps[1].source_object_id,
            source_system_name=base_reps[1].source_system_name,
            display_name=base_reps[1].display_name,
            acronym=base_reps[1].acronym,
            country=base_reps[1].country,
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION, "GOV-REG-BBB"),),
        ),
        base_reps[2],
    )
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)

    assert decision.outcome is ResolutionOutcome.BLOCKED_CONFLICT
    assert decision.triggered_veto_rules
    tax_item = next(
        i
        for i in profile.items
        if i.evidence_type is EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION
    )
    assert tax_item.classification is EvidenceClassification.VETO
    assert "GOV-REG-AAA" not in " ".join(tax_item.normalized_values)
    assert "GOV-REG-BBB" not in " ".join(tax_item.normalized_values)


# ---------------------------------------------------------------------------
# Safety rules
# ---------------------------------------------------------------------------


def test_name_only_evidence_never_auto_resolves() -> None:
    policy = exploratory_preset()  # lowest bar of the three presets
    reps = (_rep(display_name=CANDIDATE_NAME),)
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country=None,
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)
    assert decision.outcome is not ResolutionOutcome.RESOLVED


def test_acronym_only_evidence_never_auto_resolves() -> None:
    policy = exploratory_preset()
    reps = (_rep(display_name="Something Else Entirely", acronym="TSMC"),)
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country=None,
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)
    assert decision.outcome is not ResolutionOutcome.RESOLVED


def test_name_plus_acronym_alone_never_auto_resolves() -> None:
    policy = exploratory_preset()
    reps = (_rep(display_name=CANDIDATE_NAME, acronym="TSMC"),)
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country=None,
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)
    assert decision.outcome is not ResolutionOutcome.RESOLVED


def test_strong_identifier_match_can_auto_resolve_under_conservative() -> None:
    policy = conservative_preset()
    reps = (
        _rep(
            display_name=CANDIDATE_NAME,
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "5493001KJTIIGC8Y1R12"),),
        ),
    )
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country=None,
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)
    assert decision.outcome is ResolutionOutcome.RESOLVED


def test_conflicting_strong_identifier_vetoes_even_with_high_score() -> None:
    policy = conservative_preset()
    reps = (
        _rep(
            display_name=CANDIDATE_NAME,
            country="Taiwan",
            website_domain="tsmc.com",
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "AAAAAAAAAAAAAAAAAAAA"),),
        ),
        _rep(
            display_name=CANDIDATE_NAME,
            country="Taiwan",
            website_domain="tsmc.com",
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "BBBBBBBBBBBBBBBBBBBB"),),
        ),
    )
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)
    assert decision.outcome is ResolutionOutcome.BLOCKED_CONFLICT


def test_multiple_corroborating_non_name_attributes_can_resolve_under_balanced() -> None:
    policy = balanced_preset()  # no mandatory strong identifier
    reps = (
        _rep(
            source_system_name="CRM",
            display_name=CANDIDATE_NAME,
            website_domain="tsmc.com",
            country="Taiwan",
            registered_address="No. 8 Li-Hsin Road 6",
            postal_code="30078",
        ),
        _rep(
            source_system_name="ERP",
            display_name=CANDIDATE_NAME,
            website_domain="tsmc.com",
            country="Taiwan",
            registered_address="No. 8 Li-Hsin Road 6",
            postal_code="30078",
        ),
    )
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)
    assert decision.outcome is ResolutionOutcome.RESOLVED


def test_known_parent_subsidiary_difference_blocks_automatic_resolution() -> None:
    policy = conservative_preset()
    reps = (
        _rep(
            display_name=CANDIDATE_NAME,
            country="Taiwan",
            website_domain="tsmc.com",
            parent_entity_name="A Totally Different Holding Company",
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "5493001KJTIIGC8Y1R12"),),
        ),
    )
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name="Taiwan Semiconductor Manufacturing Company Limited",
        policy=policy,
    )
    decision = decide(profile, policy)
    # Conservative treats parent/subsidiary conflicts as a veto.
    assert decision.outcome is ResolutionOutcome.BLOCKED_CONFLICT


def test_country_conflict_is_visible_and_policy_governed() -> None:
    reps = (_rep(display_name=CANDIDATE_NAME, country="Taiwan"),)

    conservative = conservative_preset()
    profile_conservative = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Singapore",
        candidate_parent_entity_name=None,
        policy=conservative,
    )
    country_item = next(
        i for i in profile_conservative.items if i.evidence_type is EvidenceType.COUNTRY_MATCH
    )
    assert country_item.classification is EvidenceClassification.VETO
    assert decide(profile_conservative, conservative).outcome is ResolutionOutcome.BLOCKED_CONFLICT

    balanced = balanced_preset()
    profile_balanced = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Singapore",
        candidate_parent_entity_name=None,
        policy=balanced,
    )
    country_item_balanced = next(
        i for i in profile_balanced.items if i.evidence_type is EvidenceType.COUNTRY_MATCH
    )
    assert country_item_balanced.classification is EvidenceClassification.NEGATIVE
    assert decide(profile_balanced, balanced).outcome is not ResolutionOutcome.RESOLVED


def test_missing_evidence_on_both_sides_is_reported_as_missing() -> None:
    policy = conservative_preset()
    reps = (_rep(display_name=CANDIDATE_NAME),)  # no country provided anywhere
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country=None,
        candidate_parent_entity_name=None,
        policy=policy,
    )
    country_item = next(i for i in profile.items if i.evidence_type is EvidenceType.COUNTRY_MATCH)
    assert country_item.classification is EvidenceClassification.MISSING
    assert country_item.contribution == 0.0
    decision = decide(profile, policy)
    assert decision.outcome is not ResolutionOutcome.BLOCKED_CONFLICT


def test_missing_evidence_never_manufactures_a_veto() -> None:
    """A gap in the evidence (candidate declares a country, no representation
    does) must never be conflated with an actual contradiction: it must not
    block or veto resolution on its own."""
    policy = conservative_preset()
    reps = (_rep(display_name=CANDIDATE_NAME),)  # no country provided by the representation
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    country_item = next(i for i in profile.items if i.evidence_type is EvidenceType.COUNTRY_MATCH)
    assert country_item.classification is not EvidenceClassification.VETO
    assert country_item.classification is not EvidenceClassification.NEGATIVE
    decision = decide(profile, policy)
    assert decision.outcome is not ResolutionOutcome.BLOCKED_CONFLICT


def test_veto_overrides_a_high_aggregate_score() -> None:
    policy = conservative_preset()
    reps = (
        _rep(
            display_name=CANDIDATE_NAME,
            website_domain="tsmc.com",
            country="Taiwan",
            registered_address="No. 8 Li-Hsin Road 6",
            postal_code="30078",
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "AAAAAAAAAAAAAAAAAAAA"),),
        ),
        _rep(
            display_name=CANDIDATE_NAME,
            website_domain="tsmc.com",
            country="Taiwan",
            registered_address="No. 8 Li-Hsin Road 6",
            postal_code="30078",
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "ZZZZZZZZZZZZZZZZZZZZ"),),
        ),
    )
    profile = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    decision = decide(profile, policy)
    assert decision.outcome is ResolutionOutcome.BLOCKED_CONFLICT
    assert decision.score == 0.0


def test_original_source_representations_are_never_mutated_by_evaluation() -> None:
    reps = _tsmc_representations()
    snapshot = tuple(reps)
    policy = conservative_preset()
    build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    assert reps == snapshot


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_evaluation_is_identical_regardless_of_representation_order() -> None:
    policy = conservative_preset()
    reps = _tsmc_representations()
    reversed_reps = tuple(reversed(reps))

    profile_forward = build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    profile_reversed = build_evidence_profile(
        representations=reversed_reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )
    assert profile_forward == profile_reversed
    assert decide(profile_forward, policy) == decide(profile_reversed, policy)


def test_evaluation_is_identical_across_repeated_runs() -> None:
    policy = conservative_preset()
    reps = _tsmc_representations()
    results = [
        decide(
            build_evidence_profile(
                representations=reps,
                candidate_name=CANDIDATE_NAME,
                candidate_country="Taiwan",
                candidate_parent_entity_name=None,
                policy=policy,
            ),
            policy,
        )
        for _ in range(3)
    ]
    assert results[0] == results[1] == results[2]


def test_no_representations_is_rejected() -> None:
    with pytest.raises(ValidationException):
        build_evidence_profile(
            representations=(),
            candidate_name=CANDIDATE_NAME,
            candidate_country=None,
            candidate_parent_entity_name=None,
            policy=conservative_preset(),
        )


def test_strong_identifier_type_on_source_representation_is_validated() -> None:
    with pytest.raises(ValidationException):
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="CRM",
            display_name="Acme",
            strong_identifiers=((EvidenceType.COUNTRY_MATCH, "not-a-strong-identifier-type"),),
        )
