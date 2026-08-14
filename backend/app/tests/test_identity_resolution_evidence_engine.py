from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.identity_resolution.evidence import SourceRepresentation
from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EvidenceType,
    ResolutionOutcome,
)
from app.domain.identity_resolution.policy import conservative_preset, exploratory_preset
from app.domain.identity_resolution.service import EvidenceResolutionEngine
from app.domain.shared.exceptions import ValidationException

CANDIDATE_NAME = "Taiwan Semiconductor Manufacturing Company Limited"


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
            source_system_name="Registry",
            display_name=CANDIDATE_NAME,
            website_domain="tsmc.com",
            country="Taiwan",
        ),
    )


def test_evaluate_returns_the_same_decision_as_the_domain_functions_directly() -> None:
    policy = conservative_preset()
    engine = EvidenceResolutionEngine(policy, policy_id=uuid4())
    decision = engine.evaluate(
        representations=_tsmc_representations(),
        candidate_name=CANDIDATE_NAME,
        candidate_country="Taiwan",
    )
    assert decision.outcome is ResolutionOutcome.POSSIBLE
    assert decision.business_confidence is BusinessConfidence.MEDIUM


def test_resolve_with_override_produces_resolved_high_confidence_and_attaches_evidence() -> None:
    policy = conservative_preset()
    policy_id = uuid4()
    engine = EvidenceResolutionEngine(policy, policy_id=policy_id)
    reps = _tsmc_representations()
    source_object_ids = tuple(r.source_object_id for r in reps)
    override_entity_id = uuid4()

    record = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=source_object_ids,
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_enterprise_entity_id=None,
        produced_at=datetime.now(UTC),
        candidate_country="Taiwan",
        override_entity_id=override_entity_id,
        override_actor_id="steward-jane",
        override_rationale="Confirmed via phone call with supplier compliance contact.",
    )

    assert record.outcome is ResolutionOutcome.RESOLVED
    assert record.business_confidence is BusinessConfidence.HIGH
    assert record.enterprise_entity_id == override_entity_id
    assert record.actor_id == "steward-jane"
    assert record.decision_rationale == "Confirmed via phone call with supplier compliance contact."
    assert record.policy_id == policy_id
    assert record.evidence_profile is not None
    assert record.structured_reasons == ("Authorized human override",)


def test_resolve_without_override_attaches_the_computed_evidence_profile() -> None:
    policy = conservative_preset()
    policy_id = uuid4()
    engine = EvidenceResolutionEngine(policy, policy_id=policy_id)
    reps = tuple(
        SourceRepresentation(
            source_object_id=r.source_object_id,
            source_system_name=r.source_system_name,
            display_name=r.display_name,
            acronym=r.acronym,
            website_domain=r.website_domain,
            country=r.country,
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "5493001KJTIIGC8Y1R12"),),
        )
        for r in _tsmc_representations()
    )
    source_object_ids = tuple(r.source_object_id for r in reps)
    entity_id = uuid4()

    record = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=source_object_ids,
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_enterprise_entity_id=entity_id,
        produced_at=datetime.now(UTC),
        candidate_country="Taiwan",
    )

    assert record.outcome is ResolutionOutcome.RESOLVED
    assert record.enterprise_entity_id == entity_id
    assert record.policy_id == policy_id
    assert record.evidence_profile is not None
    assert record.evidence_profile.items
    assert record.actor_id is None
    assert record.decision_rationale is None


def test_resolve_raises_when_a_resolvable_outcome_has_no_candidate_entity_reference() -> None:
    policy = exploratory_preset()
    engine = EvidenceResolutionEngine(policy, policy_id=uuid4())
    reps = _tsmc_representations()

    with pytest.raises(ValidationException):
        engine.resolve(
            tenant_id="tenant-a",
            supporting_source_object_ids=tuple(r.source_object_id for r in reps),
            representations=reps,
            candidate_name=CANDIDATE_NAME,
            candidate_enterprise_entity_id=None,
            produced_at=datetime.now(UTC),
            candidate_country="Taiwan",
        )


def test_resolve_allows_no_entity_reference_when_outcome_is_unresolved() -> None:
    policy = conservative_preset()
    engine = EvidenceResolutionEngine(policy, policy_id=uuid4())
    rep = SourceRepresentation(
        source_object_id=uuid4(), source_system_name="CRM", display_name="Totally Unrelated Corp"
    )

    record = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=(rep.source_object_id,),
        representations=(rep,),
        candidate_name=CANDIDATE_NAME,
        candidate_enterprise_entity_id=None,
        produced_at=datetime.now(UTC),
    )
    assert record.outcome is ResolutionOutcome.UNRESOLVED
    assert record.enterprise_entity_id is None


def test_resolve_allows_no_entity_reference_when_outcome_is_blocked_conflict() -> None:
    policy = conservative_preset()
    engine = EvidenceResolutionEngine(policy, policy_id=uuid4())
    reps = (
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="CRM",
            display_name=CANDIDATE_NAME,
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "AAAAAAAAAAAAAAAAAAAA"),),
        ),
        SourceRepresentation(
            source_object_id=uuid4(),
            source_system_name="ERP",
            display_name=CANDIDATE_NAME,
            strong_identifiers=((EvidenceType.STRONG_IDENTIFIER_LEI, "BBBBBBBBBBBBBBBBBBBB"),),
        ),
    )

    record = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=tuple(r.source_object_id for r in reps),
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_enterprise_entity_id=None,
        produced_at=datetime.now(UTC),
    )
    assert record.outcome is ResolutionOutcome.BLOCKED_CONFLICT
    assert record.enterprise_entity_id is None
