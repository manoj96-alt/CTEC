from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.domain.identity_resolution import (
    BusinessConfidence,
    EntityResolutionEngine,
    ResolutionOutcome,
    ResolutionPolicy,
)


def test_exact_candidate_resolves_with_explanation_and_policy_traceability() -> None:
    entity_id = uuid4()
    source_id = uuid4()
    engine = EntityResolutionEngine(ResolutionPolicy(version="policy-1"))
    candidates = engine.discover_candidates(
        ("Acme, Inc.",), ((entity_id, "ACME INC"), (uuid4(), "Different Company"))
    )

    record = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=(source_id,),
        candidates=candidates,
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert record.tenant_id == "tenant-a"
    assert record.enterprise_entity_id == entity_id
    assert record.outcome is ResolutionOutcome.RESOLVED
    assert record.business_confidence is BusinessConfidence.HIGH
    assert record.policy_version == "policy-1"
    assert "Normalized name exact match" in record.narrative_explanation


def test_possible_resolution_is_preserved_as_valid_understanding() -> None:
    entity_id = uuid4()
    engine = EntityResolutionEngine(
        ResolutionPolicy(version="policy-2", resolved_threshold=0.99, possible_threshold=0.5)
    )
    candidates = engine.discover_candidates(("Acme Holding",), ((entity_id, "Acme Holdings"),))
    record = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        candidates=candidates,
        produced_at=datetime.now(UTC),
    )
    assert record.outcome is ResolutionOutcome.POSSIBLE


def test_unresolved_can_have_low_business_confidence() -> None:
    engine = EntityResolutionEngine(ResolutionPolicy(version="policy-3"))
    record = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=(uuid4(),),
        candidates=(),
        produced_at=datetime.now(UTC),
    )
    assert record.outcome is ResolutionOutcome.UNRESOLVED
    assert record.business_confidence is BusinessConfidence.LOW
    assert record.enterprise_entity_id is None


def test_human_override_creates_new_immutable_record() -> None:
    engine = EntityResolutionEngine(ResolutionPolicy(version="policy-4"))
    source_ids = (uuid4(), uuid4())
    first = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=source_ids,
        candidates=(),
        produced_at=datetime.now(UTC),
    )
    override_entity_id = uuid4()
    overridden = engine.resolve(
        tenant_id="tenant-a",
        supporting_source_object_ids=source_ids,
        candidates=(),
        produced_at=datetime.now(UTC),
        override_entity_id=override_entity_id,
    )
    assert first.record_id != overridden.record_id
    assert overridden.enterprise_entity_id == override_entity_id
    assert overridden.structured_reasons == ("Authorized human override",)


def test_policy_validation_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValueError):
        ResolutionPolicy(version="invalid", resolved_threshold=0.5, possible_threshold=0.8)


def test_resolution_configuration_is_externalized() -> None:
    settings = Settings(
        resolution_policy_version="policy-configured",
        resolution_resolved_threshold=0.88,
        resolution_possible_threshold=0.61,
    )
    policy = ResolutionPolicy(
        version=settings.resolution_policy_version,
        resolved_threshold=settings.resolution_resolved_threshold,
        possible_threshold=settings.resolution_possible_threshold,
        high_confidence_threshold=settings.resolution_high_confidence_threshold,
        medium_confidence_threshold=settings.resolution_medium_confidence_threshold,
    )
    assert policy.version == "policy-configured"
    assert policy.resolved_threshold == 0.88
