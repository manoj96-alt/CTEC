"""OQI3-I2 deterministic evaluation pipeline tests (CDD-041 §10-§13, §21;
Artifact Authorization §9). `determine_outcome` is a pure function -- these
tests exercise it directly against fabricated `(inputs, raw_values)`
frontiers, without a database, mirroring the family/type/applicability
matrix Artifact Authorization §9 requires."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

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
    CompositionNode,
    ExpectedType,
    Operator,
    OqiMalformedBusinessRuleError,
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


# --- Scenario D: compound AND-composed consequences (CDD-041 §4.2/§4.5-
# §4.8, OQI3-G2/I2-R). Product example: `IF lifecycle_status = ACTIVE THEN
# planning_group MUST EXIST AND procurement_type MUST EXIST AND base_uom
# MUST EXIST` -- one governed policy, multiple independently observable
# consequence clauses, never fragmented into three separate BusinessRules.


def _multi_required_rule() -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="applicable-active",
        operator=Operator.EQ,
        input_role="lifecycle_status",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="ACTIVE",
    )
    predicate = CompositionNode(
        operator=Operator.AND,
        children=(
            ComparatorNode(
                clause_id="planning-group-required",
                operator=Operator.IS_NOT_NULL,
                input_role="planning_group",
                comparand_kind=ComparandKind.NONE,
            ),
            ComparatorNode(
                clause_id="procurement-type-required",
                operator=Operator.IS_NOT_NULL,
                input_role="procurement_type",
                comparand_kind=ComparandKind.NONE,
            ),
            ComparatorNode(
                clause_id="base-uom-required",
                operator=Operator.IS_NOT_NULL,
                input_role="base_uom",
                comparand_kind=ComparandKind.NONE,
            ),
        ),
    )
    bindings = tuple(
        BusinessRuleInputBinding(
            input_role=role,
            source_field_id=uuid4(),
            required=required,
            expected_type=ExpectedType.STRING,
        )
        for role, required in (
            ("lifecycle_status", True),
            ("planning_group", False),
            ("procurement_type", False),
            ("base_uom", False),
        )
    )
    return BusinessRule.new(
        business_condition_id="active-requires-planning-attributes",
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


def test_multi_required_not_applicable_when_not_active() -> None:
    rule = _multi_required_rule()
    inputs = (
        _entry("lifecycle_status", True),
        _entry("planning_group", False),
        _entry("procurement_type", False),
        _entry("base_uom", False),
    )
    result = determine_outcome(
        rule=rule, inputs=inputs, raw_values={"lifecycle_status": "STANDARD"}
    )
    assert result == (EvaluationOutcome.NOT_APPLICABLE, ())


def test_multi_required_all_present_satisfied_zero_observations() -> None:
    rule = _multi_required_rule()
    inputs = (
        _entry("lifecycle_status", True),
        _entry("planning_group", True),
        _entry("procurement_type", True),
        _entry("base_uom", True),
    )
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={
            "lifecycle_status": "ACTIVE",
            "planning_group": "PG1",
            "procurement_type": "PT1",
            "base_uom": "EA",
        },
    )
    assert result == (EvaluationOutcome.SATISFIED, ())


def test_multi_required_all_missing_produces_three_observations() -> None:
    """The AA's own mandatory >=3-simultaneous-clause-failure regression,
    finally implementable after OQI3-G2/I2-R (CDD-041 §4.2 compound
    authorization)."""
    rule = _multi_required_rule()
    inputs = (
        _entry("lifecycle_status", True),
        _entry("planning_group", False),
        _entry("procurement_type", False),
        _entry("base_uom", False),
    )
    result = determine_outcome(rule=rule, inputs=inputs, raw_values={"lifecycle_status": "ACTIVE"})
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert len(observations) == 3
    assert {o.clause_id for o in observations} == {
        "planning-group-required",
        "procurement-type-required",
        "base-uom-required",
    }
    assert {o.input_role for o in observations} == {
        "planning_group",
        "procurement_type",
        "base_uom",
    }
    assert all(o.observation_type is ObservationType.REQUIRED_INPUT_MISSING for o in observations)


def test_multi_required_partial_missing_produces_two_observations() -> None:
    rule = _multi_required_rule()
    inputs = (
        _entry("lifecycle_status", True),
        _entry("planning_group", True),
        _entry("procurement_type", False),
        _entry("base_uom", False),
    )
    result = determine_outcome(
        rule=rule,
        inputs=inputs,
        raw_values={"lifecycle_status": "ACTIVE", "planning_group": "PG1"},
    )
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert len(observations) == 2
    assert {o.input_role for o in observations} == {"procurement_type", "base_uom"}


def test_clause_order_permutation_is_deterministic() -> None:
    """Reordering AND children changes neither the outcome nor the
    Observation set (CDD-041 §4.4: no schema/identity change; observation
    identity/set semantics must not depend on traversal order)."""
    rule = _multi_required_rule()
    reordered_predicate = CompositionNode(
        operator=Operator.AND,
        children=tuple(reversed(rule.predicate.children)),  # type: ignore[union-attr]
    )
    import dataclasses

    reordered_rule = dataclasses.replace(rule, predicate=reordered_predicate)
    inputs = (
        _entry("lifecycle_status", True),
        _entry("planning_group", False),
        _entry("procurement_type", False),
        _entry("base_uom", False),
    )
    raw_values = {"lifecycle_status": "ACTIVE"}
    forward = determine_outcome(rule=rule, inputs=inputs, raw_values=raw_values)
    reversed_result = determine_outcome(rule=reordered_rule, inputs=inputs, raw_values=raw_values)
    assert forward is not None and reversed_result is not None
    assert forward[0] == reversed_result[0]
    forward_keys = {(o.clause_id, o.observation_type, o.input_role) for o in forward[1]}
    reversed_keys = {(o.clause_id, o.observation_type, o.input_role) for o in reversed_result[1]}
    assert forward_keys == reversed_keys


# --- Kleene three-valued compound consequence (CDD-041 §4.6-§4.9) ---


def _kleene_prohibited_rule(clause_count: int = 3) -> BusinessRule:
    """AND-composed CONDITIONAL_PROHIBITED with `clause_count` independent
    NE clauses -- unlike CONDITIONAL_REQUIRED's IS_NOT_NULL-only leaves
    (which can never be UNKNOWN, since presence is always knowable),
    arbitrary comparators can be UNKNOWN when their bound input has no
    admitted raw value, which is exactly what these tests need to exercise
    strong Kleene AND (CDD-041 §4.6)."""
    roles = [f"role_{i}" for i in range(clause_count)]
    applicability = ComparatorNode(
        clause_id="applicable-gate",
        operator=Operator.EQ,
        input_role="gate",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="YES",
    )
    predicate = CompositionNode(
        operator=Operator.AND,
        children=tuple(
            ComparatorNode(
                clause_id=f"prohibited-{role}",
                operator=Operator.NE,
                input_role=role,
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value=f"BAD_{role}",
            )
            for role in roles
        ),
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="gate",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.STRING,
        ),
        *(
            BusinessRuleInputBinding(
                input_role=role,
                source_field_id=uuid4(),
                required=False,
                expected_type=ExpectedType.STRING,
            )
            for role in roles
        ),
    )
    return BusinessRule.new(
        business_condition_id=f"kleene-prohibited-{uuid4()}",
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


def test_compound_prohibited_all_violated_three_observations() -> None:
    rule = _kleene_prohibited_rule(3)
    inputs = tuple(_entry(f"role_{i}", True) for i in range(3)) + (_entry("gate", True),)
    raw_values = {"gate": "YES", **{f"role_{i}": f"BAD_role_{i}" for i in range(3)}}
    result = determine_outcome(rule=rule, inputs=inputs, raw_values=raw_values)
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert len(observations) == 3


def test_compound_prohibited_mixed_only_failing_clause_observed() -> None:
    """A=TRUE (satisfied, NE holds), B=FALSE (violated), C=TRUE -- exactly
    one observation, for B only (CDD-041 §4.5's complete-but-not-
    over-complete failure-set semantics)."""
    rule = _kleene_prohibited_rule(3)
    inputs = tuple(_entry(f"role_{i}", True) for i in range(3)) + (_entry("gate", True),)
    raw_values = {
        "gate": "YES",
        "role_0": "OK",  # NE True: not the disallowed value -> satisfied
        "role_1": "BAD_role_1",  # NE False: the disallowed value -> violated
        "role_2": "OK",  # NE True: satisfied
    }
    result = determine_outcome(rule=rule, inputs=inputs, raw_values=raw_values)
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert len(observations) == 1
    assert observations[0].input_role == "role_1"


def test_compound_crown_false_false_unknown_is_violated_with_two_observations() -> None:
    """The crown regression (CDD-041 §4.8): A=FALSE, B=FALSE, C=UNKNOWN
    under strong Kleene AND -> overall FALSE (not UNKNOWN) -> VIOLATED,
    with observations for A and B only -- none for C, since its failure is
    never deterministically established."""
    rule = _kleene_prohibited_rule(3)
    inputs = tuple(_entry(f"role_{i}", True) for i in range(2)) + (
        _entry("role_2", False),  # C: no evidence at all -> UNKNOWN
        _entry("gate", True),
    )
    raw_values = {
        "gate": "YES",
        "role_0": "BAD_role_0",  # A: violated (NE False)
        "role_1": "BAD_role_1",  # B: violated (NE False)
        # role_2 (C) deliberately has no raw value -> UNKNOWN
    }
    result = determine_outcome(rule=rule, inputs=inputs, raw_values=raw_values)
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert len(observations) == 2
    assert {o.input_role for o in observations} == {"role_0", "role_1"}


def test_compound_false_and_unknown_violated_one_observation() -> None:
    """FALSE AND UNKNOWN = FALSE -> VIOLATED with an observation for the
    known-failing clause only, none for the UNKNOWN clause."""
    rule = _kleene_prohibited_rule(2)
    inputs = (_entry("role_0", True), _entry("role_1", False), _entry("gate", True))
    raw_values = {"gate": "YES", "role_0": "BAD_role_0"}  # role_1: UNKNOWN
    result = determine_outcome(rule=rule, inputs=inputs, raw_values=raw_values)
    assert result is not None
    outcome, observations = result
    assert outcome is EvaluationOutcome.VIOLATED
    assert len(observations) == 1
    assert observations[0].input_role == "role_0"


def test_compound_true_and_unknown_is_not_evaluable_with_zero_ledger() -> None:
    """TRUE AND UNKNOWN = UNKNOWN -> whole-Evaluation NOT_EVALUABLE
    (CDD-041 §4.7, §4.9): `determine_outcome` returns `None`, meaning the
    caller persists nothing at all -- zero Evaluation, zero Observations,
    zero Finding mutation."""
    rule = _kleene_prohibited_rule(2)
    inputs = (_entry("role_0", True), _entry("role_1", False), _entry("gate", True))
    raw_values = {"gate": "YES", "role_0": "OK"}  # role_0: TRUE (NE holds); role_1: UNKNOWN
    result = determine_outcome(rule=rule, inputs=inputs, raw_values=raw_values)
    assert result is None


# --- OR/NOT/nested-IMPLIES/FIELD_COMPARISON compound-consequence firewalls
# (CDD-041 §4.2/§4.10: only AND is authorized for consequence composition)


def _lone_comparator(
    clause_id: str, role: str, *, operator: Operator = Operator.IS_NOT_NULL
) -> ComparatorNode:
    return ComparatorNode(
        clause_id=clause_id,
        operator=operator,
        input_role=role,
        comparand_kind=ComparandKind.NONE,
    )


def _new_compound_rule(rule_family: RuleFamily, predicate: object) -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="applicable-gate",
        operator=Operator.IS_NOT_NULL,
        input_role="gate",
        comparand_kind=ComparandKind.NONE,
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="gate",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.STRING,
        ),
        BusinessRuleInputBinding(
            input_role="a",
            source_field_id=uuid4(),
            required=False,
            expected_type=ExpectedType.STRING,
        ),
        BusinessRuleInputBinding(
            input_role="b",
            source_field_id=uuid4(),
            required=False,
            expected_type=ExpectedType.STRING,
        ),
    )
    return BusinessRule.new(
        business_condition_id=f"firewall-{uuid4()}",
        version=1,
        tenant_id="t1",
        rule_family=rule_family,
        applicability=applicability,
        predicate=predicate,  # type: ignore[arg-type]
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )


def test_compound_or_consequence_rejected_for_conditional_required() -> None:
    predicate = CompositionNode(
        operator=Operator.OR,
        children=(_lone_comparator("c1", "a"), _lone_comparator("c2", "b")),
    )
    with pytest.raises(OqiMalformedBusinessRuleError):
        _new_compound_rule(RuleFamily.CONDITIONAL_REQUIRED, predicate)


def test_compound_not_consequence_rejected_for_conditional_prohibited() -> None:
    predicate = CompositionNode(operator=Operator.NOT, children=(_lone_comparator("c1", "a"),))
    with pytest.raises(OqiMalformedBusinessRuleError):
        _new_compound_rule(RuleFamily.CONDITIONAL_PROHIBITED, predicate)


def test_nested_and_inside_and_rejected() -> None:
    """No nesting: an AND child that is itself a CompositionNode (not a
    bare ComparatorNode) is rejected (CDD-041 §4.2: 'no nesting')."""
    inner = CompositionNode(
        operator=Operator.AND, children=(_lone_comparator("c1", "a"), _lone_comparator("c2", "b"))
    )
    predicate = CompositionNode(
        operator=Operator.AND, children=(inner, _lone_comparator("c3", "a"))
    )
    with pytest.raises(OqiMalformedBusinessRuleError):
        _new_compound_rule(RuleFamily.CONDITIONAL_REQUIRED, predicate)


def test_conditional_required_and_child_must_be_is_not_null() -> None:
    """An AND child that is a comparator other than IS_NOT_NULL is
    rejected for CONDITIONAL_REQUIRED (CDD-041 §4.2: 'all IS_NOT_NULL for
    CONDITIONAL_REQUIRED')."""
    predicate = CompositionNode(
        operator=Operator.AND,
        children=(
            _lone_comparator("c1", "a"),
            ComparatorNode(
                clause_id="c2",
                operator=Operator.EQ,
                input_role="b",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value="X",
            ),
        ),
    )
    with pytest.raises(OqiMalformedBusinessRuleError):
        _new_compound_rule(RuleFamily.CONDITIONAL_REQUIRED, predicate)


def test_field_comparison_compound_predicate_rejected() -> None:
    """CDD-041 §4.2: FIELD_COMPARISON remains strictly atomic -- a
    CompositionNode predicate must still be rejected, proving compound
    authorization was not accidentally broadened beyond the two
    conditional families."""
    predicate = CompositionNode(
        operator=Operator.AND,
        children=(
            ComparatorNode(
                clause_id="c1",
                operator=Operator.LTE,
                input_role="a",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="b",
            ),
            ComparatorNode(
                clause_id="c2",
                operator=Operator.GTE,
                input_role="a",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="b",
            ),
        ),
    )
    bindings = (
        BusinessRuleInputBinding(
            input_role="a", source_field_id=uuid4(), required=True, expected_type=ExpectedType.DATE
        ),
        BusinessRuleInputBinding(
            input_role="b", source_field_id=uuid4(), required=True, expected_type=ExpectedType.DATE
        ),
    )
    with pytest.raises(OqiMalformedBusinessRuleError):
        BusinessRule.new(
            business_condition_id=f"field-comparison-compound-firewall-{uuid4()}",
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
