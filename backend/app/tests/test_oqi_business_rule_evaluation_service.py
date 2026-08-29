"""OQI3-I2 deterministic evaluation pipeline tests (CDD-041 §10-§13, §21;
Artifact Authorization §9). `determine_outcome` is a pure function -- these
tests exercise it directly against fabricated `(inputs, raw_values)`
frontiers, without a database, mirroring the family/type/applicability
matrix Artifact Authorization §9 requires."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.application.oqi_business_rule_evaluation_service import (
    determine_outcome,
    parse_typed_value,
)
from app.domain.oqi_business_rule.evaluation import (
    BusinessRuleEvaluationInputEntry,
    EvaluationOutcome,
    ObservationType,
)
from app.domain.oqi_business_rule.rule import (
    BusinessRule,
    BusinessRuleInputBinding,
    BusinessRuleStatus,
    ComparandKind,
    ComparatorNode,
    ExpectedType,
    Operator,
    RuleFamily,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _entry(role: str, has_evidence: bool) -> BusinessRuleEvaluationInputEntry:
    return BusinessRuleEvaluationInputEntry(
        input_role=role, evidence_id=uuid4() if has_evidence else None
    )


def _hazmat_rule() -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="applicable-hazmat",
        operator=Operator.EQ,
        input_role="material_type",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="HAZMAT",
    )
    predicate = ComparatorNode(
        clause_id="classification-required",
        operator=Operator.IS_NOT_NULL,
        input_role="hazmat_classification",
        comparand_kind=ComparandKind.NONE,
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="material_type",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.STRING,
        ),
        BusinessRuleInputBinding(
            input_role="hazmat_classification",
            source_field_id=uuid4(),
            required=False,
            expected_type=ExpectedType.STRING,
        ),
    )
    return BusinessRule.new(
        business_condition_id="hazmat-classification-required",
        version=1,
        tenant_id="t1",
        rule_family=RuleFamily.CONDITIONAL_REQUIRED,
        applicability=applicability,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )


# --- Scenario A: HAZMAT CONDITIONAL_REQUIRED (CDD-041 §5, AA §9) ---


def test_hazmat_not_applicable_when_material_is_standard() -> None:
    rule = _hazmat_rule()
    inputs = (_entry("material_type", True), _entry("hazmat_classification", False))
    result = determine_outcome(rule=rule, inputs=inputs, raw_values={"material_type": "STANDARD"})
    assert result == (EvaluationOutcome.NOT_APPLICABLE, ())


def test_hazmat_satisfied_when_classification_exists() -> None:
    rule = _hazmat_rule()
    inputs = (_entry("material_type", True), _entry("hazmat_classification", True))
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={"material_type": "HAZMAT", "hazmat_classification": "CLASS-3"},
    )
    assert result == (EvaluationOutcome.SATISFIED, ())


def test_hazmat_violated_when_classification_missing() -> None:
    rule = _hazmat_rule()
    inputs = (_entry("material_type", True), _entry("hazmat_classification", False))
    result = determine_outcome(rule=rule, inputs=inputs, raw_values={"material_type": "HAZMAT"})
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert len(observations) == 1
    assert observations[0].observation_type is ObservationType.REQUIRED_INPUT_MISSING
    assert observations[0].input_role == "hazmat_classification"
    assert observations[0].clause_id == "classification-required"


def test_hazmat_not_evaluable_when_subject_material_type_unknown() -> None:
    rule = _hazmat_rule()
    inputs = (_entry("material_type", False), _entry("hazmat_classification", False))
    assert determine_outcome(rule=rule, inputs=inputs, raw_values={}) is None


# --- Scenario B: FIELD_COMPARISON effective dates (CDD-041 §5, AA §9) ---


def _effective_dates_rule() -> BusinessRule:
    predicate = ComparatorNode(
        clause_id="start-before-end",
        operator=Operator.LTE,
        input_role="effective_start",
        comparand_kind=ComparandKind.INPUT_ROLE,
        comparand_input_role="effective_end",
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="effective_start",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.DATE,
        ),
        BusinessRuleInputBinding(
            input_role="effective_end",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.DATE,
        ),
    )
    return BusinessRule.new(
        business_condition_id="effective-dates-ordered",
        version=1,
        tenant_id="t1",
        rule_family=RuleFamily.FIELD_COMPARISON,
        applicability=None,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )


def test_effective_dates_satisfied_when_ordered() -> None:
    rule = _effective_dates_rule()
    inputs = (_entry("effective_start", True), _entry("effective_end", True))
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={"effective_start": "2026-01-01", "effective_end": "2026-12-31"},
    )
    assert result == (EvaluationOutcome.SATISFIED, ())


def test_effective_dates_violated_when_reversed() -> None:
    rule = _effective_dates_rule()
    inputs = (_entry("effective_start", True), _entry("effective_end", True))
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={"effective_start": "2026-12-31", "effective_end": "2026-01-01"},
    )
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert observations[0].observation_type is ObservationType.CLAUSE_VIOLATED


def test_effective_dates_not_evaluable_for_invalid_date() -> None:
    rule = _effective_dates_rule()
    inputs = (_entry("effective_start", True), _entry("effective_end", True))
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={"effective_start": "ABC", "effective_end": "2026-12-31"},
    )
    assert result is None


def test_effective_dates_not_evaluable_when_input_missing() -> None:
    rule = _effective_dates_rule()
    inputs = (_entry("effective_start", False), _entry("effective_end", True))
    result = determine_outcome(rule=rule, inputs=inputs, raw_values={"effective_end": "2026-12-31"})
    assert result is None


def test_decimal_comparison_is_numeric_not_lexical() -> None:
    """`"10" < "2"` lexically -- proves DECIMAL comparison uses real
    numeric ordering, never string ordering (CDD-041 §10, AA §9)."""
    predicate = ComparatorNode(
        clause_id="a-lt-b",
        operator=Operator.LT,
        input_role="a",
        comparand_kind=ComparandKind.INPUT_ROLE,
        comparand_input_role="b",
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="a",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.DECIMAL,
        ),
        BusinessRuleInputBinding(
            input_role="b",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.DECIMAL,
        ),
    )
    rule = BusinessRule.new(
        business_condition_id="decimal-ordering",
        version=1,
        tenant_id="t1",
        rule_family=RuleFamily.FIELD_COMPARISON,
        applicability=None,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )
    inputs = (_entry("a", True), _entry("b", True))
    result = determine_outcome(rule=rule, inputs=inputs, raw_values={"a": "2", "b": "10"})
    assert result == (EvaluationOutcome.SATISFIED, ())  # 2 < 10 numerically


# --- Scenario C: CONDITIONAL_PROHIBITED discontinued planning ---


def _discontinued_planning_rule() -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="applicable-discontinued",
        operator=Operator.EQ,
        input_role="lifecycle_status",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="DISCONTINUED",
    )
    predicate = ComparatorNode(
        clause_id="planning-not-active",
        operator=Operator.NE,
        input_role="planning_status",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="ACTIVE",
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="lifecycle_status",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.STRING,
        ),
        BusinessRuleInputBinding(
            input_role="planning_status",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.STRING,
        ),
    )
    return BusinessRule.new(
        business_condition_id="discontinued-planning-prohibited",
        version=1,
        tenant_id="t1",
        rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
        applicability=applicability,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )


def test_discontinued_planning_not_applicable_when_not_discontinued() -> None:
    rule = _discontinued_planning_rule()
    inputs = (_entry("lifecycle_status", True), _entry("planning_status", True))
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={"lifecycle_status": "ACTIVE", "planning_status": "ACTIVE"},
    )
    assert result == (EvaluationOutcome.NOT_APPLICABLE, ())


def test_discontinued_planning_satisfied_when_inactive() -> None:
    rule = _discontinued_planning_rule()
    inputs = (_entry("lifecycle_status", True), _entry("planning_status", True))
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={"lifecycle_status": "DISCONTINUED", "planning_status": "CLOSED"},
    )
    assert result == (EvaluationOutcome.SATISFIED, ())


def test_discontinued_planning_violated_when_still_active() -> None:
    rule = _discontinued_planning_rule()
    inputs = (_entry("lifecycle_status", True), _entry("planning_status", True))
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={"lifecycle_status": "DISCONTINUED", "planning_status": "ACTIVE"},
    )
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert observations[0].observation_type is ObservationType.CLAUSE_VIOLATED
    assert observations[0].input_role == "planning_status"


# --- typed parsers, in isolation (CDD-041 §10, AA §9) ---


def test_parse_decimal_uses_exact_decimal_not_binary_float() -> None:
    from decimal import Decimal

    assert parse_typed_value(ExpectedType.DECIMAL, "10.10") == Decimal("10.10")


def test_parse_decimal_rejects_garbage() -> None:
    assert parse_typed_value(ExpectedType.DECIMAL, "not-a-number") is None


def test_parse_boolean_accepts_only_closed_lowercase_tokens() -> None:
    assert parse_typed_value(ExpectedType.BOOLEAN, "true") is True
    assert parse_typed_value(ExpectedType.BOOLEAN, "false") is False
    assert parse_typed_value(ExpectedType.BOOLEAN, "True") is None
    assert parse_typed_value(ExpectedType.BOOLEAN, "1") is None
    assert parse_typed_value(ExpectedType.BOOLEAN, "yes") is None


def test_parse_date_rejects_non_iso_formats() -> None:
    from datetime import date

    assert parse_typed_value(ExpectedType.DATE, "2026-08-28") == date(2026, 8, 28)
    assert parse_typed_value(ExpectedType.DATE, "2026-8-28") is None  # not zero-padded
    assert parse_typed_value(ExpectedType.DATE, "08/28/2026") is None
    assert parse_typed_value(ExpectedType.DATE, "2026-13-01") is None  # invalid month


def test_parse_string_is_never_coerced() -> None:
    assert parse_typed_value(ExpectedType.STRING, "10") == "10"
