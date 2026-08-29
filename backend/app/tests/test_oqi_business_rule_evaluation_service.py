"""OQI3-I2 deterministic evaluation pipeline tests (CDD-041 §10-§13, §21;
Artifact Authorization §9). `determine_outcome` is a pure function -- these
tests exercise it directly against fabricated `(inputs, raw_values)`
frontiers, without a database, mirroring the family/type/applicability
matrix Artifact Authorization §9 requires."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

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


# --- OQI3-I3: CURRENT-STATE BusinessRuleFinding lifecycle + seed-3 authority
# (CDD-041 §14-§15, §21-§23, §30; Artifact Authorization §9, §14 remainder).
# A fake in-memory repository exercises the full `evaluate_current_state`
# orchestration deterministically (single-threaded) -- real-Postgres
# concurrency proofs (first-violation/resolution/reopen races, lock-before-
# frontier ordering, atomicity rollback, tenant isolation, replay idempotency
# under contention) live in test_oqi_business_rule_postgres.py.

from app.application.oqi_business_rule_evaluation_service import (
    OqiBusinessRuleEvaluationService,
    OqiRuleNotActiveError,
    SingleRecordSubject,
)
from app.domain.oqi.finding import QualityFindingStatus
from app.domain.oqi_business_rule.evaluation import BusinessRuleEvaluation
from app.domain.oqi_business_rule.finding import BusinessRuleFinding, ResolutionBasis


class _FakeCurrentStateRepo:
    """In-memory stand-in for `OqiBusinessRuleEvaluationRepository`. Field
    state is `dict[input_role, str | None]` (`None` = known subject, zero
    qualifying evidence for that role -- the frozen EMPTY sentinel);
    `subject_known=False` makes `select_evidence_frontier` report an unknown
    subject regardless of `fields`, exactly like real Postgres would for a
    record with zero evidence anywhere."""

    def __init__(self) -> None:
        self.subject_known = True
        self.fields: dict[str, str | None] = {}
        self._evaluations: dict[UUID, BusinessRuleEvaluation] = {}
        self._findings: dict[UUID, BusinessRuleFinding] = {}
        self.call_order: list[str] = []
        self._evidence_id_by_role_value: dict[tuple[str, str], UUID] = {}
        self._by_evidence_id: dict[UUID, str] = {}

    def select_evidence_frontier(
        self,
        *,
        source_object_id: UUID,
        source_record_reference: str,
        evaluation_horizon: datetime,
        bindings: Sequence[tuple[str, UUID]],
    ) -> tuple[bool, dict[str, UUID | None]]:
        self.call_order.append("select_evidence_frontier")
        if not self.subject_known:
            return False, {}
        result: dict[str, UUID | None] = {}
        for role, _field_id in bindings:
            value = self.fields.get(role)
            if value is None:
                result[role] = None
                continue
            # Stable per (role, value): unchanged raw evidence content
            # yields the same evidence_id across calls, exactly as real
            # Postgres would for an unchanged FieldValueEvidence row --
            # required for genuine replay-identity tests.
            key = (role, value)
            if key not in self._evidence_id_by_role_value:
                self._evidence_id_by_role_value[key] = uuid4()
            evidence_id = self._evidence_id_by_role_value[key]
            self._by_evidence_id[evidence_id] = value
            result[role] = evidence_id
        return True, result

    def insert_evaluation_idempotent(self, evaluation: BusinessRuleEvaluation) -> bool:
        if evaluation.evaluation_id in self._evaluations:
            return False
        self._evaluations[evaluation.evaluation_id] = evaluation
        return True

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.call_order.append("acquire_evaluation_authority")

    def get_finding(self, finding_id: UUID) -> BusinessRuleFinding | None:
        return self._findings.get(finding_id)

    def upsert_finding(self, finding: BusinessRuleFinding) -> None:
        self._findings[finding.finding_id] = finding


class _FakeReader:
    def __init__(self, repo: _FakeCurrentStateRepo) -> None:
        self._repo = repo

    def read_values(self, inputs: tuple[BusinessRuleEvaluationInputEntry, ...]) -> dict[str, str]:
        return {
            entry.input_role: self._repo._by_evidence_id[entry.evidence_id]
            for entry in inputs
            if entry.evidence_id is not None
        }


def _make_service(repo: _FakeCurrentStateRepo) -> OqiBusinessRuleEvaluationService:
    return OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: NOW,
    )


def _subject(reference: str = "REC-1") -> SingleRecordSubject:
    return SingleRecordSubject(
        tenant_id="t1", source_object_id=uuid4(), source_record_reference=reference
    )


def test_no_finding_plus_violated_creates_open() -> None:
    repo = _FakeCurrentStateRepo()
    repo.fields = {"material_type": "HAZMAT"}
    service = _make_service(repo)
    subject = _subject()
    evaluation = service.evaluate_current_state(rule=_hazmat_rule(), subject=subject)
    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.resolution_basis is None
    assert (
        finding.occurrence_count == 1 and finding.reopen_count == 0 and finding.state_revision == 1
    )
    assert finding.first_seen_at == NOW and finding.last_seen_at == NOW
    assert finding.latest_evaluation_id == evaluation.evaluation_id


def test_no_finding_plus_satisfied_creates_no_finding() -> None:
    repo = _FakeCurrentStateRepo()
    repo.fields = {"material_type": "HAZMAT", "hazmat_classification": "CLASS-3"}
    service = _make_service(repo)
    service.evaluate_current_state(rule=_hazmat_rule(), subject=_subject())
    assert repo._findings == {}


def test_no_finding_plus_not_applicable_creates_no_finding() -> None:
    repo = _FakeCurrentStateRepo()
    repo.fields = {"material_type": "STANDARD"}
    service = _make_service(repo)
    service.evaluate_current_state(rule=_hazmat_rule(), subject=_subject())
    assert repo._findings == {}


def test_open_plus_violated_remains_open_and_updates_last_seen() -> None:
    from datetime import timedelta

    repo = _FakeCurrentStateRepo()
    repo.fields = {"material_type": "HAZMAT"}
    subject = _subject()
    rule = _hazmat_rule()
    service = OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: t[0],
    )
    t = [NOW]
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=1)
    service.evaluate_current_state(rule=rule, subject=subject)
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 2
    assert finding.occurrence_count == 1 and finding.reopen_count == 0
    assert finding.last_seen_at == NOW + timedelta(days=1)
    assert finding.first_seen_at == NOW


def test_open_plus_satisfied_resolves_basis_satisfied_last_seen_unchanged() -> None:
    from datetime import timedelta

    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    t = [NOW]
    service = OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: t[0],
    )
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=1)
    repo.fields = {"material_type": "HAZMAT", "hazmat_classification": "CLASS-3"}
    service.evaluate_current_state(rule=rule, subject=subject)
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.RESOLVED
    assert finding.resolution_basis is ResolutionBasis.SATISFIED
    assert finding.state_revision == 2
    assert finding.last_seen_at == NOW  # never updated on SATISFIED


def test_open_plus_not_applicable_resolves_basis_not_applicable() -> None:
    from datetime import timedelta

    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    t = [NOW]
    service = OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: t[0],
    )
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=1)
    repo.fields = {"material_type": "STANDARD"}
    service.evaluate_current_state(rule=rule, subject=subject)
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.RESOLVED
    assert finding.resolution_basis is ResolutionBasis.NOT_APPLICABLE
    assert finding.state_revision == 2


def test_resolved_plus_satisfied_remains_resolved() -> None:
    from datetime import timedelta

    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    t = [NOW]
    service = OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: t[0],
    )
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=1)
    repo.fields = {"material_type": "HAZMAT", "hazmat_classification": "CLASS-3"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=2)
    service.evaluate_current_state(rule=rule, subject=subject)
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.RESOLVED
    assert finding.resolution_basis is ResolutionBasis.SATISFIED
    assert finding.state_revision == 3


def test_resolved_plus_not_applicable_remains_resolved() -> None:
    from datetime import timedelta

    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    t = [NOW]
    service = OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: t[0],
    )
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=1)
    repo.fields = {"material_type": "STANDARD"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=2)
    service.evaluate_current_state(rule=rule, subject=subject)
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.RESOLVED
    assert finding.resolution_basis is ResolutionBasis.NOT_APPLICABLE
    assert finding.state_revision == 3


def test_resolved_plus_violated_reopens_with_correct_counters() -> None:
    from datetime import timedelta

    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    t = [NOW]
    service = OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: t[0],
    )
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=1)
    repo.fields = {"material_type": "HAZMAT", "hazmat_classification": "CLASS-3"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=2)
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.resolution_basis is None
    assert finding.occurrence_count == 2 and finding.reopen_count == 1
    assert finding.state_revision == 3
    assert finding.last_seen_at == NOW + timedelta(days=2)
    assert finding.first_seen_at == NOW


def test_not_evaluable_leaves_existing_open_finding_completely_untouched() -> None:
    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    service = _make_service(repo)
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    (before,) = repo._findings.values()

    repo.subject_known = False
    evaluation = service.evaluate_current_state(rule=rule, subject=subject)
    assert evaluation is None
    (after,) = repo._findings.values()
    assert before == after  # frozen dataclass equality: byte-identical


def test_not_evaluable_creates_no_finding_when_none_exists() -> None:
    repo = _FakeCurrentStateRepo()
    repo.subject_known = False
    service = _make_service(repo)
    evaluation = service.evaluate_current_state(rule=_hazmat_rule(), subject=_subject())
    assert evaluation is None
    assert repo._findings == {}
    assert repo._evaluations == {}


def test_retirement_firewall_open_finding_unchanged_and_evaluation_rejected() -> None:
    from dataclasses import replace

    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    service = _make_service(repo)
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    (before,) = repo._findings.values()

    retired_rule = replace(rule, status=BusinessRuleStatus.RETIRED, retired_on=NOW)
    with pytest.raises(OqiRuleNotActiveError):
        service.evaluate_current_state(rule=retired_rule, subject=subject)
    (after,) = repo._findings.values()
    assert before == after


def test_same_evaluation_replay_does_not_double_mutate_finding() -> None:
    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    service = _make_service(repo)
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    (first,) = repo._findings.values()
    # Identical rule/subject/horizon/evidence -> identical evaluation_id ->
    # replay must be a no-op for Finding counters/state.
    service.evaluate_current_state(rule=rule, subject=subject)
    (second,) = repo._findings.values()
    assert first == second
    assert len(repo._evaluations) == 1


def test_lock_acquired_before_evidence_selection() -> None:
    repo = _FakeCurrentStateRepo()
    repo.fields = {"material_type": "HAZMAT"}
    service = _make_service(repo)
    service.evaluate_current_state(rule=_hazmat_rule(), subject=_subject())
    assert repo.call_order.index("acquire_evaluation_authority") < repo.call_order.index(
        "select_evidence_frontier"
    )


def test_not_applicable_reapplicability_reopens_finding() -> None:
    """CDD-041 §14, §30: HAZMAT -> OPEN; reclassified STANDARD -> RESOLVED/
    NOT_APPLICABLE; reclassified back to HAZMAT with classification still
    missing -> same Finding REOPENED with correct reopen_count. Mandatory
    product regression (OQI3-I3-R directive)."""
    from datetime import timedelta

    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _hazmat_rule()
    t = [NOW]
    service = OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: t[0],
    )
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    t[0] = NOW + timedelta(days=1)
    repo.fields = {"material_type": "STANDARD"}
    service.evaluate_current_state(rule=rule, subject=subject)
    (resolved,) = repo._findings.values()
    assert resolved.status is QualityFindingStatus.RESOLVED
    assert resolved.resolution_basis is ResolutionBasis.NOT_APPLICABLE

    t[0] = NOW + timedelta(days=2)
    repo.fields = {"material_type": "HAZMAT"}
    service.evaluate_current_state(rule=rule, subject=subject)
    (reopened,) = repo._findings.values()
    assert reopened.status is QualityFindingStatus.OPEN
    assert reopened.resolution_basis is None
    assert reopened.occurrence_count == 2 and reopened.reopen_count == 1
    assert reopened.finding_id == resolved.finding_id


def _compound_required_rule(condition_id: str) -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="applicable-lifecycle-active",
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
    bindings = (
        BusinessRuleInputBinding(
            input_role="lifecycle_status",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.STRING,
        ),
    ) + tuple(
        BusinessRuleInputBinding(
            input_role=role,
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.STRING,
        )
        for role in ("planning_group", "procurement_type", "base_uom")
    )
    return BusinessRule.new(
        business_condition_id=condition_id,
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


def test_compound_partial_remediation_one_finding_throughout() -> None:
    """CDD-041 §19, §21: A/B/C required; 3-missing -> 2-missing ->
    1-missing -> resolved -> reopen, one Finding throughout, old
    Observations immutable. Mandatory compound lifecycle regression."""
    from datetime import timedelta

    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _compound_required_rule(f"compound-{uuid4()}")
    t = [NOW]
    service = OqiBusinessRuleEvaluationService(
        evaluation_repository=repo,
        evidence_value_reader=_FakeReader(repo),
        clock=lambda: t[0],
    )

    repo.fields = {
        "lifecycle_status": "ACTIVE",
        "planning_group": None,
        "procurement_type": None,
        "base_uom": None,
    }
    eval1 = service.evaluate_current_state(rule=rule, subject=subject)
    assert eval1 is not None
    assert len(eval1.observations) == 3
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 1
    finding_id = finding.finding_id

    t[0] = NOW + timedelta(days=1)
    repo.fields = {
        "lifecycle_status": "ACTIVE",
        "planning_group": "PG1",
        "procurement_type": None,
        "base_uom": None,
    }
    eval2 = service.evaluate_current_state(rule=rule, subject=subject)
    assert eval2 is not None
    assert len(eval2.observations) == 2
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.OPEN and finding.state_revision == 2
    assert finding.finding_id == finding_id

    t[0] = NOW + timedelta(days=2)
    repo.fields = {
        "lifecycle_status": "ACTIVE",
        "planning_group": "PG1",
        "procurement_type": "PT1",
        "base_uom": None,
    }
    eval3 = service.evaluate_current_state(rule=rule, subject=subject)
    assert eval3 is not None
    assert len(eval3.observations) == 1
    assert eval3.observations[0].input_role == "base_uom"

    t[0] = NOW + timedelta(days=3)
    repo.fields = {
        "lifecycle_status": "ACTIVE",
        "planning_group": "PG1",
        "procurement_type": "PT1",
        "base_uom": "EA",
    }
    eval4 = service.evaluate_current_state(rule=rule, subject=subject)
    assert eval4 is not None
    assert eval4.outcome is EvaluationOutcome.SATISFIED
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.RESOLVED
    assert finding.resolution_basis is ResolutionBasis.SATISFIED
    assert finding.state_revision == 4

    # Reopen: base_uom goes missing again.
    t[0] = NOW + timedelta(days=4)
    repo.fields = {
        "lifecycle_status": "ACTIVE",
        "planning_group": "PG1",
        "procurement_type": "PT1",
        "base_uom": None,
    }
    eval5 = service.evaluate_current_state(rule=rule, subject=subject)
    assert eval5 is not None
    assert eval5.observations[0].input_role == "base_uom"
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.occurrence_count == 2 and finding.reopen_count == 1
    assert finding.finding_id == finding_id

    # Old evaluations' own observations remain immutable (never rewritten).
    assert len(eval1.observations) == 3
    assert len(eval3.observations) == 1


def _kleene_rule_two_required(condition_id: str) -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="applicable-gate",
        operator=Operator.EQ,
        input_role="gate",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="YES",
    )
    # CONDITIONAL_PROHIBITED allows any comparator as a consequence leaf
    # (unlike CONDITIONAL_REQUIRED, restricted to IS_NOT_NULL) -- needed
    # here so clause "b" can be a typed EQ comparison.
    predicate = CompositionNode(
        operator=Operator.AND,
        children=(
            ComparatorNode(
                clause_id="a-required",
                operator=Operator.IS_NOT_NULL,
                input_role="a",
                comparand_kind=ComparandKind.NONE,
            ),
            ComparatorNode(
                clause_id="b-comparison",
                operator=Operator.EQ,
                input_role="b",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.DECIMAL,
                literal_value="42",
            ),
        ),
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
            required=True,
            expected_type=ExpectedType.STRING,
        ),
        BusinessRuleInputBinding(
            input_role="b",
            source_field_id=uuid4(),
            required=True,
            expected_type=ExpectedType.DECIMAL,
        ),
    )
    return BusinessRule.new(
        business_condition_id=condition_id,
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


def test_kleene_false_and_unknown_violated_finding_stays_open_known_observation_only() -> None:
    """FALSE (a missing) AND UNKNOWN (b malformed DECIMAL) -> VIOLATED,
    exactly one observation (for 'a'), none for the unknown clause 'b'."""
    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _kleene_rule_two_required(f"kleene-fu-{uuid4()}")
    service = _make_service(repo)
    repo.fields = {"gate": "YES", "a": None, "b": "not-a-decimal"}
    evaluation = service.evaluate_current_state(rule=rule, subject=subject)
    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert len(evaluation.observations) == 1
    assert evaluation.observations[0].input_role == "a"
    (finding,) = repo._findings.values()
    assert finding.status is QualityFindingStatus.OPEN


def test_kleene_true_and_unknown_not_evaluable_finding_completely_unchanged() -> None:
    """TRUE (a present) AND UNKNOWN (b malformed) -> NOT_EVALUABLE. No
    Evaluation, no Finding created/mutated."""
    repo = _FakeCurrentStateRepo()
    subject = _subject()
    rule = _kleene_rule_two_required(f"kleene-tu-{uuid4()}")
    service = _make_service(repo)
    repo.fields = {"gate": "YES", "a": "present", "b": "not-a-decimal"}
    evaluation = service.evaluate_current_state(rule=rule, subject=subject)
    assert evaluation is None
    assert repo._findings == {}
    assert repo._evaluations == {}
