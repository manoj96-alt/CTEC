from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.semantic_resolution import (
    BusinessConfidence,
    ResolutionOutcome,
    SemanticResolutionEngine,
    SemanticResolutionPolicy,
    SemanticResolutionRecord,
)


def _resolve(
    term: str, concept_name: str, *, resolved: float = 0.9
) -> tuple[SemanticResolutionRecord, UUID]:
    engine = SemanticResolutionEngine(
        SemanticResolutionPolicy("policy-1", resolved_threshold=resolved, possible_threshold=0.4)
    )
    concept_id = uuid4()
    candidates = engine.discover_candidates((term,), ((concept_id, concept_name),))
    record = engine.resolve(
        enterprise_entity_id=uuid4(),
        context_id=uuid4(),
        supporting_entity_resolution_record_ids=(uuid4(),),
        supporting_source_object_ids=(uuid4(),),
        candidates=candidates,
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return record, concept_id


def test_resolved_references_exactly_one_governed_concept() -> None:
    record, concept_id = _resolve("Critical Component", "Critical Component")
    assert record.outcome is ResolutionOutcome.RESOLVED
    assert record.semantic_interpretation_id == concept_id
    assert record.business_confidence is BusinessConfidence.HIGH


def test_possible_contains_explainable_candidate_interpretations() -> None:
    record, _ = _resolve("Strategic Supplier", "Strategic Supply", resolved=0.99)
    assert record.outcome is ResolutionOutcome.POSSIBLE
    assert record.candidate_interpretations
    assert record.candidate_interpretations[0].structured_reasons


def test_unresolved_contains_no_interpretation() -> None:
    engine = SemanticResolutionEngine(SemanticResolutionPolicy("policy-2"))
    record = engine.resolve(
        enterprise_entity_id=uuid4(),
        context_id=uuid4(),
        supporting_entity_resolution_record_ids=(uuid4(),),
        supporting_source_object_ids=(uuid4(),),
        candidates=(),
        produced_at=datetime.now(UTC),
    )
    assert record.outcome is ResolutionOutcome.UNRESOLVED
    assert record.semantic_interpretation_id is None
    assert not record.candidate_interpretations


def test_override_creates_resolved_record() -> None:
    concept_id = uuid4()
    engine = SemanticResolutionEngine(SemanticResolutionPolicy("policy-3"))
    record = engine.resolve(
        enterprise_entity_id=uuid4(),
        context_id=uuid4(),
        supporting_entity_resolution_record_ids=(uuid4(),),
        supporting_source_object_ids=(uuid4(),),
        candidates=(),
        produced_at=datetime.now(UTC),
        override_concept_id=concept_id,
    )
    assert record.semantic_interpretation_id == concept_id
    assert record.structured_reasons == ("Authorized human override",)


def test_policy_validation() -> None:
    with pytest.raises(ValueError):
        SemanticResolutionPolicy("bad", resolved_threshold=0.4, possible_threshold=0.8)
