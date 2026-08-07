from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.assertion_engine import (
    AssertionEngine,
    AssertionOutcome,
    AssertionPolicy,
    AssertionRecord,
    BusinessConfidence,
    GovernedEvidence,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.repositories import REPOSITORY_TYPES


def _record(score: float) -> AssertionRecord:
    subject_id = uuid4()
    engine = AssertionEngine(AssertionPolicy("ASM-policy"))
    evidence = GovernedEvidence((uuid4(),), (uuid4(),), subject_id)
    return engine.evaluate(
        subject_entity_id=subject_id,
        predicate_relationship_type_id=uuid4(),
        object_institutional_concept_id=uuid4(),
        context_id=uuid4(),
        evidence=evidence,
        internal_score=score,
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("score", "outcome"),
    [
        (1.0, AssertionOutcome.ESTABLISHED),
        (0.75, AssertionOutcome.CANDIDATE),
        (0.2, AssertionOutcome.REJECTED),
    ],
)
def test_assertion_outcomes(score: float, outcome: AssertionOutcome) -> None:
    record = _record(score)
    assert record.outcome is outcome
    assert record.structured_reasons
    assert record.policy_version == "ASM-policy"


def test_business_confidence_is_independent_record_attribute() -> None:
    assert _record(0.75).business_confidence is BusinessConfidence.MEDIUM


def test_human_override_creates_new_record_values() -> None:
    subject_id = uuid4()
    engine = AssertionEngine(AssertionPolicy("override-policy"))
    record = engine.evaluate(
        subject_entity_id=subject_id,
        predicate_relationship_type_id=uuid4(),
        object_institutional_concept_id=uuid4(),
        context_id=uuid4(),
        evidence=GovernedEvidence((uuid4(),), (uuid4(),), subject_id),
        internal_score=0.1,
        produced_at=datetime.now(UTC),
        override_outcome=AssertionOutcome.ESTABLISHED,
        override_confidence=BusinessConfidence.HIGH,
    )
    assert record.outcome is AssertionOutcome.ESTABLISHED
    assert record.structured_reasons == ("Authorized human override",)


def test_evidence_cannot_reference_different_subject() -> None:
    with pytest.raises(ValidationException, match="Assertion Subject"):
        engine = AssertionEngine(AssertionPolicy("policy"))
        engine.evaluate(
            subject_entity_id=uuid4(),
            predicate_relationship_type_id=uuid4(),
            object_institutional_concept_id=uuid4(),
            context_id=uuid4(),
            evidence=GovernedEvidence((uuid4(),), (uuid4(),), uuid4()),
            internal_score=1,
            produced_at=datetime.now(UTC),
        )


def test_canonical_assertion_is_not_available_through_generic_unit_of_work() -> None:
    assert Assertion not in REPOSITORY_TYPES
