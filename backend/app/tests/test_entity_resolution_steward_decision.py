from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from app.domain.identity_resolution.evidence import SourceRepresentation, build_evidence_profile
from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EvidenceProfile,
    EvidenceType,
    ResolutionOutcome,
    StewardDecisionAction,
)
from app.domain.identity_resolution.policy import (
    ResolutionPolicyDefinition,
    balanced_preset,
    conservative_preset,
)
from app.domain.identity_resolution.service import (
    EvidenceResolutionEngine,
    OverrideNotPermittedError,
)
from app.domain.shared.exceptions import ValidationException

CANDIDATE_NAME = "Taiwan Semiconductor Manufacturing Company Limited"
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _tsmc_representations(**overrides: Any) -> tuple[SourceRepresentation, ...]:
    lei_a = overrides.pop("lei_a", None)
    lei_b = overrides.pop("lei_b", None)
    return (
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="CRM",
            display_name="TSMC",
            acronym="TSMC",
            website_domain="tsmc.com",
            country="Taiwan",
            strong_identifiers=(((EvidenceType.STRONG_IDENTIFIER_LEI, lei_a),) if lei_a else ()),
        ),
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="Registry",
            display_name=CANDIDATE_NAME,
            website_domain="tsmc.com",
            country="Taiwan",
            strong_identifiers=(((EvidenceType.STRONG_IDENTIFIER_LEI, lei_b),) if lei_b else ()),
        ),
    )


def _profile_no_veto(policy: ResolutionPolicyDefinition) -> EvidenceProfile:
    reps = _tsmc_representations(lei_a="5493001KJTIIGC8Y1R12", lei_b="5493001KJTIIGC8Y1R12")
    return build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )


def _profile_with_veto(policy: ResolutionPolicyDefinition) -> EvidenceProfile:
    reps = _tsmc_representations(lei_a="AAAAAAAAAAAAAAAAAAAA", lei_b="BBBBBBBBBBBBBBBBBBBB")
    return build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )


def _profile_possible_no_strong_id(policy: ResolutionPolicyDefinition) -> EvidenceProfile:
    reps = _tsmc_representations()
    return build_evidence_profile(
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
        candidate_parent_entity_name=None,
        policy=policy,
    )


def _engine(policy: ResolutionPolicyDefinition) -> EvidenceResolutionEngine:
    return EvidenceResolutionEngine(policy, policy_id=uuid4())


# ---------------------------------------------------------------------------
# confirm_match
# ---------------------------------------------------------------------------


def test_confirm_match_resolves_when_no_veto_is_present() -> None:
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_no_veto(policy)
    entity_id = uuid4()

    record = engine.decide_steward_action(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        evidence_profile=profile,
        current_enterprise_entity_id=entity_id,
        action=StewardDecisionAction.CONFIRM_MATCH,
        actor_id="steward-jane",
        decision_rationale="Verified via phone call with supplier compliance contact.",
        produced_at=NOW,
    )

    assert record.outcome is ResolutionOutcome.RESOLVED
    assert record.business_confidence is BusinessConfidence.HIGH
    assert record.enterprise_entity_id == entity_id
    assert record.actor_id == "steward-jane"
    assert record.evidence_profile == profile


def test_confirm_match_cannot_bypass_a_strong_identifier_veto_conflict() -> None:
    """Regression test for Gate C requirement: a human override must never
    turn BLOCKED_CONFLICT into RESOLVED."""
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_with_veto(policy)
    entity_id = uuid4()

    with pytest.raises(OverrideNotPermittedError):
        engine.decide_steward_action(
            tenant_id="tenant-a",
            supporting_source_object_ids=(uuid4(),),
            evidence_profile=profile,
            current_enterprise_entity_id=entity_id,
            action=StewardDecisionAction.CONFIRM_MATCH,
            actor_id="steward-jane",
            decision_rationale="Trying to force a resolution despite the conflict.",
            produced_at=NOW,
        )


def test_confirm_match_requires_a_candidate_entity_reference() -> None:
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_no_veto(policy)

    with pytest.raises(ValidationException):
        engine.decide_steward_action(
            tenant_id="tenant-a",
            supporting_source_object_ids=(uuid4(),),
            evidence_profile=profile,
            current_enterprise_entity_id=None,
            action=StewardDecisionAction.CONFIRM_MATCH,
            actor_id="steward-jane",
            decision_rationale="No candidate on this case yet.",
            produced_at=NOW,
        )


@pytest.mark.parametrize("actor_id,rationale", [("", "valid rationale"), ("steward-jane", "  ")])
def test_decision_requires_non_blank_actor_and_rationale(actor_id: str, rationale: str) -> None:
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_no_veto(policy)

    with pytest.raises(ValidationException):
        engine.decide_steward_action(
            tenant_id="tenant-a",
            supporting_source_object_ids=(uuid4(),),
            evidence_profile=profile,
            current_enterprise_entity_id=uuid4(),
            action=StewardDecisionAction.CONFIRM_MATCH,
            actor_id=actor_id,
            decision_rationale=rationale,
            produced_at=NOW,
        )


# ---------------------------------------------------------------------------
# reject_match
# ---------------------------------------------------------------------------


def test_reject_match_clears_the_candidate_and_yields_possible_or_unresolved() -> None:
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_possible_no_strong_id(policy)

    record = engine.decide_steward_action(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        evidence_profile=profile,
        current_enterprise_entity_id=uuid4(),
        action=StewardDecisionAction.REJECT_MATCH,
        actor_id="steward-jane",
        decision_rationale="Candidate is a different subsidiary entirely.",
        produced_at=NOW,
    )

    assert record.enterprise_entity_id is None
    assert record.outcome in (ResolutionOutcome.POSSIBLE, ResolutionOutcome.UNRESOLVED)


def test_reject_match_cannot_clear_an_existing_veto_conflict() -> None:
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_with_veto(policy)

    record = engine.decide_steward_action(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        evidence_profile=profile,
        current_enterprise_entity_id=None,
        action=StewardDecisionAction.REJECT_MATCH,
        actor_id="steward-jane",
        decision_rationale="Rejecting, but the evidence still conflicts.",
        produced_at=NOW,
    )

    assert record.outcome is ResolutionOutcome.BLOCKED_CONFLICT
    assert record.enterprise_entity_id is None


def test_reject_match_never_produces_resolved() -> None:
    policy = balanced_preset()
    engine = _engine(policy)
    reps = (
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="CRM",
            display_name=CANDIDATE_NAME,
            website_domain="tsmc.com",
            country="Taiwan",
            registered_address="No. 8 Li-Hsin Road 6",
            postal_code="30078",
        ),
        SourceRepresentation(
            source_object_id=uuid4(),
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

    record = engine.decide_steward_action(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        evidence_profile=profile,
        current_enterprise_entity_id=uuid4(),
        action=StewardDecisionAction.REJECT_MATCH,
        actor_id="steward-jane",
        decision_rationale="Steward disagrees despite the high score.",
        produced_at=NOW,
    )

    assert record.outcome is not ResolutionOutcome.RESOLVED
    assert record.enterprise_entity_id is None


# ---------------------------------------------------------------------------
# mark_unresolved
# ---------------------------------------------------------------------------


def test_mark_unresolved_always_clears_the_candidate_and_is_unresolved() -> None:
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_no_veto(policy)  # even a strong, resolvable case

    record = engine.decide_steward_action(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        evidence_profile=profile,
        current_enterprise_entity_id=uuid4(),
        action=StewardDecisionAction.MARK_UNRESOLVED,
        actor_id="steward-jane",
        decision_rationale="Deferring this case for further investigation.",
        produced_at=NOW,
    )

    assert record.outcome is ResolutionOutcome.UNRESOLVED
    assert record.enterprise_entity_id is None
    assert record.business_confidence is BusinessConfidence.LOW


# ---------------------------------------------------------------------------
# block_conflict
# ---------------------------------------------------------------------------


def test_block_conflict_succeeds_when_evidence_contains_a_veto() -> None:
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_with_veto(policy)

    record = engine.decide_steward_action(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        evidence_profile=profile,
        current_enterprise_entity_id=None,
        action=StewardDecisionAction.BLOCK_CONFLICT,
        actor_id="steward-jane",
        decision_rationale="Confirmed conflicting LEI values with the source systems.",
        produced_at=NOW,
    )

    assert record.outcome is ResolutionOutcome.BLOCKED_CONFLICT
    assert record.enterprise_entity_id is None
    assert record.structured_reasons


def test_block_conflict_is_rejected_without_an_applicable_veto() -> None:
    """A steward cannot manually declare a conflict the evidence doesn't
    support -- this keeps the audit trail evidentiary."""
    policy = conservative_preset()
    engine = _engine(policy)
    profile = _profile_no_veto(policy)

    with pytest.raises(ValidationException):
        engine.decide_steward_action(
            tenant_id="tenant-a",
            supporting_source_object_ids=(uuid4(),),
            evidence_profile=profile,
            current_enterprise_entity_id=uuid4(),
            action=StewardDecisionAction.BLOCK_CONFLICT,
            actor_id="steward-jane",
            decision_rationale="Trying to block a case with no real conflict.",
            produced_at=NOW,
        )


# ---------------------------------------------------------------------------
# Cross-cutting
# ---------------------------------------------------------------------------


def test_every_decision_carries_actor_rationale_policy_and_the_same_evidence_profile() -> None:
    policy = conservative_preset()
    policy_id = uuid4()
    engine = EvidenceResolutionEngine(policy, policy_id=policy_id)
    profile = _profile_no_veto(policy)

    record = engine.decide_steward_action(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        evidence_profile=profile,
        current_enterprise_entity_id=uuid4(),
        action=StewardDecisionAction.MARK_UNRESOLVED,
        actor_id="steward-jane",
        decision_rationale="Deferred pending more information.",
        produced_at=NOW,
    )

    assert record.actor_id == "steward-jane"
    assert record.decision_rationale == "Deferred pending more information."
    assert record.policy_id == policy_id
    assert record.policy_version == policy.policy_version
    assert record.evidence_profile == profile
    assert record.produced_at == NOW


def test_resolve_override_also_refuses_to_bypass_a_veto_conflict() -> None:
    """Regression test on the pre-existing raw-representations override path
    (EvidenceResolutionEngine.resolve(override_entity_id=...)), not just the
    new steward-action path: both must enforce the same invariant."""
    policy = conservative_preset()
    engine = _engine(policy)
    reps = _tsmc_representations(lei_a="AAAAAAAAAAAAAAAAAAAA", lei_b="BBBBBBBBBBBBBBBBBBBB")

    with pytest.raises(OverrideNotPermittedError):
        engine.resolve(
            tenant_id="tenant-a",
            supporting_source_object_ids=tuple(r.source_object_id for r in reps),
            representations=reps,
            candidate_name=CANDIDATE_NAME,
            candidate_enterprise_entity_id=None,
            produced_at=NOW,
            candidate_country="Taiwan",
            override_entity_id=uuid4(),
            override_actor_id="steward-jane",
            override_rationale="Attempting to force resolve.",
        )


# ---------------------------------------------------------------------------
# EvidenceProfile.as_record() / from_record() round trip
# ---------------------------------------------------------------------------


def test_evidence_profile_round_trips_through_the_persisted_record_shape() -> None:
    profile = _profile_with_veto(conservative_preset())
    restored = EvidenceProfile.from_record(profile.as_record())
    assert restored == profile


def test_evidence_profile_from_record_rejects_malformed_data() -> None:
    with pytest.raises(ValidationException):
        EvidenceProfile.from_record({"items": [{"evidence_type": "not-a-real-type"}]})
    with pytest.raises(ValidationException):
        EvidenceProfile.from_record({"not_items": []})
    with pytest.raises(ValidationException):
        EvidenceProfile.from_record([])  # type: ignore[arg-type]
