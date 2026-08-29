"""Domain-level tests for OQI3-I2's `BusinessRuleEvaluation`/
`BusinessRuleEvaluationObservation`/input-evidence digest (CDD-041 §16-§19;
Artifact Authorization §5, §9). Proves identity determinism, digest
role-sensitivity/order-invariance, and that observation content never
enters Evaluation identity -- the direct OQI2 lesson, reused."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.oqi.evaluation import EvaluationMode
from app.domain.oqi_business_rule.evaluation import (
    SUBJECT_TYPE_SINGLE_RECORD,
    BusinessRuleEvaluation,
    BusinessRuleEvaluationInputEntry,
    BusinessRuleEvaluationObservation,
    EvaluationOutcome,
    ObservationType,
    canonical_single_record_subject_identity,
    derive_business_rule_evaluation_id,
    input_evidence_digest,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime(2026, 1, 1, tzinfo=UTC)


_FIXED_SOURCE_OBJECT_ID = uuid4()


def _make_evaluation(
    *,
    inputs: tuple[BusinessRuleEvaluationInputEntry, ...],
    outcome: EvaluationOutcome,
    observations: tuple[BusinessRuleEvaluationObservation, ...] = (),
    business_condition_id: str = "cond-1",
) -> BusinessRuleEvaluation:
    subject_identity = canonical_single_record_subject_identity(
        source_object_id=_FIXED_SOURCE_OBJECT_ID, source_record_reference="MAT-100"
    )
    digest = input_evidence_digest(inputs)
    evaluation_id = derive_business_rule_evaluation_id(
        tenant_id="t1",
        business_condition_id=business_condition_id,
        rule_version=1,
        subject_type=SUBJECT_TYPE_SINGLE_RECORD,
        subject_identity=subject_identity,
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_horizon=NOW,
        input_evidence_digest_value=digest,
    )
    return BusinessRuleEvaluation(
        evaluation_id=evaluation_id,
        tenant_id="t1",
        business_condition_id=business_condition_id,
        rule_id=uuid4(),
        rule_version=1,
        subject_type=SUBJECT_TYPE_SINGLE_RECORD,
        subject_identity=subject_identity,
        source_object_id=_FIXED_SOURCE_OBJECT_ID,
        source_record_reference="MAT-100",
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_horizon=NOW,
        inputs=inputs,
        outcome=outcome,
        observations=observations,
        evaluated_at=NOW,
    )


def test_evaluation_constructs_with_consistent_identity() -> None:
    inputs = (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    evaluation = _make_evaluation(inputs=inputs, outcome=EvaluationOutcome.SATISFIED)
    assert evaluation.outcome is EvaluationOutcome.SATISFIED


def test_evaluation_id_is_role_order_invariant() -> None:
    e1, e2, e3 = uuid4(), uuid4(), uuid4()
    inputs_forward = (
        BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=e1),
        BusinessRuleEvaluationInputEntry(input_role="b", evidence_id=e2),
        BusinessRuleEvaluationInputEntry(input_role="c", evidence_id=e3),
    )
    inputs_reversed = tuple(reversed(inputs_forward))
    assert input_evidence_digest(inputs_forward) == input_evidence_digest(inputs_reversed)

    forward = _make_evaluation(inputs=inputs_forward, outcome=EvaluationOutcome.SATISFIED)
    reversed_eval = _make_evaluation(inputs=inputs_reversed, outcome=EvaluationOutcome.SATISFIED)
    assert forward.evaluation_id == reversed_eval.evaluation_id


def test_digest_is_role_sensitive() -> None:
    shared_evidence = uuid4()
    d1 = input_evidence_digest(
        (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=shared_evidence),)
    )
    d2 = input_evidence_digest(
        (BusinessRuleEvaluationInputEntry(input_role="b", evidence_id=shared_evidence),)
    )
    assert d1 != d2


def test_digest_is_evidence_sensitive() -> None:
    d1 = input_evidence_digest(
        (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    )
    d2 = input_evidence_digest(
        (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    )
    assert d1 != d2


def test_digest_distinguishes_zero_evidence_from_a_different_role_set() -> None:
    empty = input_evidence_digest(
        (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=None),)
    )
    other_empty = input_evidence_digest(
        (BusinessRuleEvaluationInputEntry(input_role="b", evidence_id=None),)
    )
    assert empty != other_empty


def test_evaluation_id_excludes_observation_content() -> None:
    """CDD-041 §16: observation content is excluded from Evaluation
    identity -- observations are deterministic derivatives of the frozen
    inputs, proven not assumed, exactly the OQI2 lesson."""
    inputs = (BusinessRuleEvaluationInputEntry(input_role="required_field", evidence_id=None),)
    no_observations = _make_evaluation(inputs=inputs, outcome=EvaluationOutcome.SATISFIED)
    with_observations = dataclasses.replace(
        no_observations,
        outcome=EvaluationOutcome.VIOLATED,
        observations=(
            BusinessRuleEvaluationObservation(
                clause_id="c1",
                observation_type=ObservationType.REQUIRED_INPUT_MISSING,
                input_role="required_field",
            ),
        ),
    )
    assert no_observations.evaluation_id == with_observations.evaluation_id


def test_evaluation_id_changes_when_evidence_digest_changes() -> None:
    inputs_a = (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    inputs_b = (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    eval_a = _make_evaluation(inputs=inputs_a, outcome=EvaluationOutcome.SATISFIED)
    eval_b = _make_evaluation(inputs=inputs_b, outcome=EvaluationOutcome.SATISFIED)
    assert eval_a.evaluation_id != eval_b.evaluation_id


def test_evaluation_id_changes_when_horizon_changes() -> None:
    inputs = (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    subject_identity = canonical_single_record_subject_identity(
        source_object_id=uuid4(), source_record_reference="MAT-100"
    )
    digest = input_evidence_digest(inputs)
    id_1 = derive_business_rule_evaluation_id(
        tenant_id="t1",
        business_condition_id="cond-1",
        rule_version=1,
        subject_type=SUBJECT_TYPE_SINGLE_RECORD,
        subject_identity=subject_identity,
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_horizon=NOW,
        input_evidence_digest_value=digest,
    )
    id_2 = derive_business_rule_evaluation_id(
        tenant_id="t1",
        business_condition_id="cond-1",
        rule_version=1,
        subject_type=SUBJECT_TYPE_SINGLE_RECORD,
        subject_identity=subject_identity,
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_horizon=datetime(2026, 6, 1, tzinfo=UTC),
        input_evidence_digest_value=digest,
    )
    assert id_1 != id_2


def test_evaluation_id_changes_when_rule_version_changes() -> None:
    inputs = (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    eval_v1 = _make_evaluation(inputs=inputs, outcome=EvaluationOutcome.SATISFIED)
    subject_identity = eval_v1.subject_identity
    digest = input_evidence_digest(inputs)
    id_v2 = derive_business_rule_evaluation_id(
        tenant_id="t1",
        business_condition_id="cond-1",
        rule_version=2,
        subject_type=SUBJECT_TYPE_SINGLE_RECORD,
        subject_identity=subject_identity,
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_horizon=NOW,
        input_evidence_digest_value=digest,
    )
    assert eval_v1.evaluation_id != id_v2


def test_satisfied_evaluation_must_not_carry_observations() -> None:
    inputs = (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    with pytest.raises(ValidationException):
        _make_evaluation(
            inputs=inputs,
            outcome=EvaluationOutcome.SATISFIED,
            observations=(
                BusinessRuleEvaluationObservation(
                    clause_id="c1", observation_type=ObservationType.CLAUSE_VIOLATED, input_role="a"
                ),
            ),
        )


def test_violated_evaluation_requires_at_least_one_observation() -> None:
    inputs = (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    with pytest.raises(ValidationException):
        _make_evaluation(inputs=inputs, outcome=EvaluationOutcome.VIOLATED, observations=())


def test_observation_input_role_must_belong_to_evaluation_inputs() -> None:
    inputs = (BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=uuid4()),)
    with pytest.raises(ValidationException):
        _make_evaluation(
            inputs=inputs,
            outcome=EvaluationOutcome.VIOLATED,
            observations=(
                BusinessRuleEvaluationObservation(
                    clause_id="c1",
                    observation_type=ObservationType.CLAUSE_VIOLATED,
                    input_role="not-a-bound-input",
                ),
            ),
        )


def test_evaluation_supports_multiple_simultaneous_observations() -> None:
    """The persistence/identity layer itself imposes no cap on observation
    count -- proven here at the domain level even though I1's current
    single-comparator-predicate family shapes (CDD-041 §5, `rule.py`
    `validate_business_rule_shape`) mean no *executable* rule can yet
    produce more than one observation per Evaluation (see the OQI3-I2
    report's flagged architecture-scope finding)."""
    inputs = (
        BusinessRuleEvaluationInputEntry(input_role="a", evidence_id=None),
        BusinessRuleEvaluationInputEntry(input_role="b", evidence_id=None),
    )
    evaluation = _make_evaluation(
        inputs=inputs,
        outcome=EvaluationOutcome.VIOLATED,
        observations=(
            BusinessRuleEvaluationObservation(
                clause_id="c1",
                observation_type=ObservationType.REQUIRED_INPUT_MISSING,
                input_role="a",
            ),
            BusinessRuleEvaluationObservation(
                clause_id="c2",
                observation_type=ObservationType.REQUIRED_INPUT_MISSING,
                input_role="b",
            ),
        ),
    )
    assert len(evaluation.observations) == 2
