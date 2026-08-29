"""Pure domain unit tests for `app.domain.oqi_business_rule.rule` (CDD-041
§3-§12, §19, §22, §26). OQI3-I1 scope only: BusinessRule/binding/AST
construction, publication-shape validation, immutability, and versioning
invariants. No evaluation runtime, no Finding lifecycle -- those are
OQI3-I2/I3 and are exercised in their own future test files."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.oqi_business_rule.rule import (
    MAX_AST_DEPTH,
    MAX_AST_NODES,
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
    ast_from_json,
    ast_to_json,
    derive_business_rule_id,
    validate_ast_bounds,
    validate_business_rule_shape,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _binding(
    *, role: str, expected_type: ExpectedType = ExpectedType.STRING, required: bool = True
) -> BusinessRuleInputBinding:
    return BusinessRuleInputBinding(
        input_role=role,
        source_field_id=uuid4(),
        required=required,
        expected_type=expected_type,
    )


def _conditional_required_rule(
    *,
    business_condition_id: str = "hazmat-classification-required",
    version: int = 1,
    tenant_id: str = "tenant-a",
    status: BusinessRuleStatus = BusinessRuleStatus.ACTIVE,
    retired_on: datetime | None = None,
) -> BusinessRule:
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
        _binding(role="material_type"),
        _binding(role="hazmat_classification", required=True),
    )
    return BusinessRule.new(
        business_condition_id=business_condition_id,
        version=version,
        tenant_id=tenant_id,
        rule_family=RuleFamily.CONDITIONAL_REQUIRED,
        applicability=applicability,
        predicate=predicate,
        input_bindings=bindings,
        status=status,
        created_by="tester",
        created_on=NOW,
        retired_on=retired_on,
    )


def _conditional_prohibited_rule() -> BusinessRule:
    applicability = ComparatorNode(
        clause_id="applicable-discontinued",
        operator=Operator.EQ,
        input_role="lifecycle_status",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="DISCONTINUED",
    )
    predicate = ComparatorNode(
        clause_id="prohibited-active-planning",
        operator=Operator.EQ,
        input_role="planning_status",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="ACTIVE",
    )
    bindings = (_binding(role="lifecycle_status"), _binding(role="planning_status"))
    return BusinessRule.new(
        business_condition_id="discontinued-must-not-plan-active",
        version=1,
        tenant_id="tenant-a",
        rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
        applicability=applicability,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )


def _field_comparison_rule(*, applicability: ComparatorNode | None = None) -> BusinessRule:
    predicate = ComparatorNode(
        clause_id="start-before-end",
        operator=Operator.LTE,
        input_role="effective_start",
        comparand_kind=ComparandKind.INPUT_ROLE,
        comparand_input_role="effective_end",
    )
    bindings = (
        _binding(role="effective_start", expected_type=ExpectedType.DATE),
        _binding(role="effective_end", expected_type=ExpectedType.DATE),
    )
    return BusinessRule.new(
        business_condition_id="effective-start-before-end",
        version=1,
        tenant_id="tenant-a",
        rule_family=RuleFamily.FIELD_COMPARISON,
        applicability=applicability,
        predicate=predicate,
        input_bindings=bindings,
        status=BusinessRuleStatus.ACTIVE,
        created_by="tester",
        created_on=NOW,
    )


# --- valid construction, one per family ---


def test_conditional_required_rule_constructs() -> None:
    rule = _conditional_required_rule()
    assert rule.rule_family is RuleFamily.CONDITIONAL_REQUIRED
    assert rule.rule_id == derive_business_rule_id(
        business_condition_id=rule.business_condition_id, version=rule.version
    )


def test_conditional_prohibited_rule_constructs() -> None:
    rule = _conditional_prohibited_rule()
    assert rule.rule_family is RuleFamily.CONDITIONAL_PROHIBITED


def test_field_comparison_rule_constructs_without_applicability() -> None:
    rule = _field_comparison_rule()
    assert rule.rule_family is RuleFamily.FIELD_COMPARISON
    assert rule.applicability is None


def test_field_comparison_rule_constructs_with_applicability() -> None:
    applicability = ComparatorNode(
        clause_id="applicable-active",
        operator=Operator.EQ,
        input_role="effective_start",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.DATE,
        literal_value="2026-01-01",
    )
    rule = _field_comparison_rule(applicability=applicability)
    assert rule.applicability == applicability


# --- unsupported family rejected ---


def test_unsupported_rule_family_string_is_unrepresentable() -> None:
    with pytest.raises(ValueError):
        RuleFamily("CUSTOM_SCRIPT")


def test_validate_business_rule_shape_rejects_non_rule_family_value() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family="CONDITIONAL_REQUIRED",  # type: ignore[arg-type]
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.IS_NOT_NULL,
                input_role="x",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(_binding(role="x"),),
        )


# --- ACTIVE/RETIRED lifecycle ---


def test_active_rule_rejects_retired_on() -> None:
    with pytest.raises(ValidationException):
        _conditional_required_rule(status=BusinessRuleStatus.ACTIVE, retired_on=NOW)


def test_retired_rule_requires_retired_on() -> None:
    with pytest.raises(ValidationException):
        _conditional_required_rule(status=BusinessRuleStatus.RETIRED)


def test_retired_rule_with_retired_on_constructs() -> None:
    rule = _conditional_required_rule(status=BusinessRuleStatus.RETIRED, retired_on=NOW)
    assert rule.status is BusinessRuleStatus.RETIRED


# --- condition/version identity ---


def test_rule_id_is_deterministic_given_condition_and_version() -> None:
    rule_a = _conditional_required_rule(business_condition_id="cond-x", version=1)
    rule_b = _conditional_required_rule(business_condition_id="cond-x", version=1)
    assert rule_a.rule_id == rule_b.rule_id


def test_rule_id_changes_with_version() -> None:
    rule_v1 = _conditional_required_rule(business_condition_id="cond-x", version=1)
    rule_v2 = _conditional_required_rule(business_condition_id="cond-x", version=2)
    assert rule_v1.rule_id != rule_v2.rule_id


def test_rule_id_mismatch_is_rejected() -> None:
    with pytest.raises(ValidationException):
        BusinessRule(
            rule_id=uuid4(),
            business_condition_id="cond-x",
            version=1,
            tenant_id="tenant-a",
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.EQ,
                input_role="a",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="b",
            ),
            input_bindings=(_binding(role="a"), _binding(role="b")),
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )


# --- immutable executable meaning ---


def test_business_rule_is_frozen() -> None:
    rule = _conditional_required_rule()
    with pytest.raises(dataclasses.FrozenInstanceError):
        rule.version = 2  # type: ignore[misc]


def test_input_binding_is_frozen() -> None:
    binding = _binding(role="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        binding.required = False  # type: ignore[misc]


def test_comparator_node_is_frozen() -> None:
    node = ComparatorNode(
        clause_id="c1",
        operator=Operator.IS_NOT_NULL,
        input_role="x",
        comparand_kind=ComparandKind.NONE,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        node.clause_id = "c2"  # type: ignore[misc]


# --- input binding tests ---


def test_duplicate_input_role_is_rejected() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.EQ,
                input_role="a",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="a",
            ),
            input_bindings=(_binding(role="a"), _binding(role="a")),
        )


def test_expected_type_closed_set() -> None:
    with pytest.raises(ValueError):
        ExpectedType("FLOAT")


def test_at_least_one_input_binding_is_required() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.IS_NOT_NULL,
                input_role="a",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(),
        )


# --- AST tests ---


def test_ast_round_trips_through_json() -> None:
    rule = _conditional_required_rule()
    assert rule.applicability is not None
    applicability_json = ast_to_json(rule.applicability)
    predicate_json = ast_to_json(rule.predicate)
    assert ast_from_json(applicability_json) == rule.applicability
    assert ast_from_json(predicate_json) == rule.predicate


def test_ast_from_json_rejects_unknown_node_type() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        ast_from_json({"node_type": "PYTHON_EVAL", "code": "eval('1+1')"})


def test_ast_from_json_rejects_unknown_operator() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        ast_from_json(
            {
                "node_type": "COMPARATOR",
                "clause_id": "c1",
                "operator": "EXEC",
                "input_role": "x",
                "comparand_kind": "NONE",
                "literal_type": None,
                "literal_value": None,
                "comparand_input_role": None,
            }
        )


def test_ast_from_json_rejects_unsupported_field() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        ast_from_json(
            {
                "node_type": "COMPARATOR",
                "clause_id": "c1",
                "operator": "IS_NOT_NULL",
                "input_role": "x",
                "comparand_kind": "NONE",
                "literal_type": None,
                "literal_value": None,
                "comparand_input_role": None,
                "dynamic_import": "os",
            }
        )


def test_literal_value_shaped_like_code_is_stored_as_inert_text() -> None:
    """Proves the AST never executes a literal -- a payload shaped like
    executable code round-trips as an exact, unexecuted string."""
    payload = "__import__('os').system('rm -rf /')"
    node = ComparatorNode(
        clause_id="c1",
        operator=Operator.EQ,
        input_role="x",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value=payload,
    )
    round_tripped = ast_from_json(ast_to_json(node))
    assert isinstance(round_tripped, ComparatorNode)
    assert round_tripped.literal_value == payload


def test_composition_node_rejects_malformed_child_count() -> None:
    leaf = ComparatorNode(
        clause_id="c1",
        operator=Operator.IS_NOT_NULL,
        input_role="x",
        comparand_kind=ComparandKind.NONE,
    )
    with pytest.raises(OqiMalformedBusinessRuleError):
        CompositionNode(operator=Operator.NOT, children=(leaf, leaf))
    with pytest.raises(OqiMalformedBusinessRuleError):
        CompositionNode(operator=Operator.IMPLIES, children=(leaf,))
    with pytest.raises(OqiMalformedBusinessRuleError):
        CompositionNode(operator=Operator.AND, children=(leaf,))


def test_duplicate_clause_id_is_rejected() -> None:
    predicate = ComparatorNode(
        clause_id="dup",
        operator=Operator.IS_NOT_NULL,
        input_role="a",
        comparand_kind=ComparandKind.NONE,
    )
    applicability = ComparatorNode(
        clause_id="dup",
        operator=Operator.EQ,
        input_role="b",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="X",
    )
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=applicability,
            predicate=predicate,
            input_bindings=(_binding(role="a"), _binding(role="b")),
        )


def _nested_and(depth: int) -> ComparatorNode | CompositionNode:
    """Builds an AND-tree of exactly the given depth (2*depth-1 nodes),
    using distinct clause_ids/input_roles at each level."""
    node: ComparatorNode | CompositionNode = ComparatorNode(
        clause_id="leaf-0",
        operator=Operator.IS_NOT_NULL,
        input_role="role-0",
        comparand_kind=ComparandKind.NONE,
    )
    for level in range(1, depth):
        leaf = ComparatorNode(
            clause_id=f"leaf-{level}",
            operator=Operator.IS_NOT_NULL,
            input_role=f"role-{level}",
            comparand_kind=ComparandKind.NONE,
        )
        node = CompositionNode(operator=Operator.AND, children=(leaf, node))
    return node


def _wide_and(count: int) -> ComparatorNode | CompositionNode:
    """Builds a single AND node with `count` leaf children -- depth stays 2
    regardless of `count`, isolating the node-count bound from the depth
    bound."""
    leaves = tuple(
        ComparatorNode(
            clause_id=f"wide-{i}",
            operator=Operator.IS_NOT_NULL,
            input_role=f"wide-role-{i}",
            comparand_kind=ComparandKind.NONE,
        )
        for i in range(count)
    )
    return CompositionNode(operator=Operator.AND, children=leaves)


def test_ast_depth_boundary_is_accepted() -> None:
    validate_ast_bounds(_nested_and(MAX_AST_DEPTH))


def test_ast_depth_boundary_plus_one_is_rejected() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_ast_bounds(_nested_and(MAX_AST_DEPTH + 1))


def test_ast_node_count_boundary_is_accepted() -> None:
    # (MAX_AST_NODES - 1) leaves + 1 AND node == MAX_AST_NODES total.
    validate_ast_bounds(_wide_and(MAX_AST_NODES - 1))


def test_ast_node_count_boundary_plus_one_is_rejected() -> None:
    # MAX_AST_NODES leaves + 1 AND node == MAX_AST_NODES + 1 total.
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_ast_bounds(_wide_and(MAX_AST_NODES))


# --- operator/type compatibility (CDD-041 §11) ---


def test_decimal_ordering_comparator_valid_at_publication() -> None:
    validate_business_rule_shape(
        rule_family=RuleFamily.FIELD_COMPARISON,
        applicability=None,
        predicate=ComparatorNode(
            clause_id="c1",
            operator=Operator.LT,
            input_role="a",
            comparand_kind=ComparandKind.INPUT_ROLE,
            comparand_input_role="b",
        ),
        input_bindings=(
            _binding(role="a", expected_type=ExpectedType.DECIMAL),
            _binding(role="b", expected_type=ExpectedType.DECIMAL),
        ),
    )


def test_date_ordering_comparator_valid_at_publication() -> None:
    validate_business_rule_shape(
        rule_family=RuleFamily.FIELD_COMPARISON,
        applicability=None,
        predicate=ComparatorNode(
            clause_id="c1",
            operator=Operator.LTE,
            input_role="a",
            comparand_kind=ComparandKind.INPUT_ROLE,
            comparand_input_role="b",
        ),
        input_bindings=(
            _binding(role="a", expected_type=ExpectedType.DATE),
            _binding(role="b", expected_type=ExpectedType.DATE),
        ),
    )


def test_string_equality_valid_at_publication() -> None:
    validate_business_rule_shape(
        rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
        applicability=ComparatorNode(
            clause_id="app",
            operator=Operator.IS_NOT_NULL,
            input_role="a",
            comparand_kind=ComparandKind.NONE,
        ),
        predicate=ComparatorNode(
            clause_id="c1",
            operator=Operator.EQ,
            input_role="a",
            comparand_kind=ComparandKind.LITERAL,
            literal_type=ExpectedType.STRING,
            literal_value="X",
        ),
        input_bindings=(_binding(role="a", expected_type=ExpectedType.STRING),),
    )


def test_boolean_equality_valid_at_publication() -> None:
    validate_business_rule_shape(
        rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
        applicability=ComparatorNode(
            clause_id="app",
            operator=Operator.IS_NOT_NULL,
            input_role="a",
            comparand_kind=ComparandKind.NONE,
        ),
        predicate=ComparatorNode(
            clause_id="c1",
            operator=Operator.EQ,
            input_role="a",
            comparand_kind=ComparandKind.LITERAL,
            literal_type=ExpectedType.BOOLEAN,
            literal_value="true",
        ),
        input_bindings=(_binding(role="a", expected_type=ExpectedType.BOOLEAN),),
    )


def test_string_ordering_comparator_is_rejected_at_publication() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.LT,
                input_role="a",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="b",
            ),
            input_bindings=(
                _binding(role="a", expected_type=ExpectedType.STRING),
                _binding(role="b", expected_type=ExpectedType.STRING),
            ),
        )


def test_boolean_ordering_comparator_is_rejected_at_publication() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.GT,
                input_role="a",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="b",
            ),
            input_bindings=(
                _binding(role="a", expected_type=ExpectedType.BOOLEAN),
                _binding(role="b", expected_type=ExpectedType.BOOLEAN),
            ),
        )


def test_cross_type_comparison_between_input_roles_is_rejected() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.EQ,
                input_role="a",
                comparand_kind=ComparandKind.INPUT_ROLE,
                comparand_input_role="b",
            ),
            input_bindings=(
                _binding(role="a", expected_type=ExpectedType.STRING),
                _binding(role="b", expected_type=ExpectedType.DECIMAL),
            ),
        )


def test_literal_type_mismatch_is_rejected_no_implicit_coercion() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
            applicability=ComparatorNode(
                clause_id="app",
                operator=Operator.IS_NOT_NULL,
                input_role="a",
                comparand_kind=ComparandKind.NONE,
            ),
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.EQ,
                input_role="a",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.DECIMAL,
                literal_value="10",
            ),
            input_bindings=(_binding(role="a", expected_type=ExpectedType.STRING),),
        )


# --- per-family closed structural contract (CDD-041 §22) ---


def test_conditional_required_predicate_must_be_is_not_null() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="app",
                operator=Operator.IS_NOT_NULL,
                input_role="a",
                comparand_kind=ComparandKind.NONE,
            ),
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.EQ,
                input_role="b",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value="X",
            ),
            input_bindings=(_binding(role="a"), _binding(role="b")),
        )


def test_conditional_required_requires_applicability() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.IS_NOT_NULL,
                input_role="a",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(_binding(role="a"),),
        )


def test_conditional_required_rejects_reference_to_unknown_input_role() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=ComparatorNode(
                clause_id="app",
                operator=Operator.EQ,
                input_role="unknown",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value="X",
            ),
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.IS_NOT_NULL,
                input_role="a",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(_binding(role="a"),),
        )


def test_conditional_prohibited_predicate_must_be_single_comparator() -> None:
    leaf = ComparatorNode(
        clause_id="c1",
        operator=Operator.EQ,
        input_role="a",
        comparand_kind=ComparandKind.LITERAL,
        literal_type=ExpectedType.STRING,
        literal_value="X",
    )
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.CONDITIONAL_PROHIBITED,
            applicability=ComparatorNode(
                clause_id="app",
                operator=Operator.IS_NOT_NULL,
                input_role="a",
                comparand_kind=ComparandKind.NONE,
            ),
            predicate=CompositionNode(operator=Operator.NOT, children=(leaf,)),
            input_bindings=(_binding(role="a"),),
        )


def test_field_comparison_predicate_must_compare_two_input_roles() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.EQ,
                input_role="a",
                comparand_kind=ComparandKind.LITERAL,
                literal_type=ExpectedType.STRING,
                literal_value="X",
            ),
            input_bindings=(_binding(role="a"),),
        )


def test_field_comparison_predicate_must_be_single_comparator() -> None:
    with pytest.raises(OqiMalformedBusinessRuleError):
        validate_business_rule_shape(
            rule_family=RuleFamily.FIELD_COMPARISON,
            applicability=None,
            predicate=CompositionNode(
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
                        operator=Operator.IS_NOT_NULL,
                        input_role="a",
                        comparand_kind=ComparandKind.NONE,
                    ),
                ),
            ),
            input_bindings=(
                _binding(role="a", expected_type=ExpectedType.DATE),
                _binding(role="b", expected_type=ExpectedType.DATE),
            ),
        )


# --- publication validation as a security boundary (CDD-041 §26) ---


def test_malformed_rule_never_becomes_constructible() -> None:
    """Publication validation runs at construction time itself
    (`BusinessRule.__post_init__`), so a malformed rule can never reach
    ACTIVE status -- it cannot even be constructed, let alone persisted."""
    with pytest.raises(OqiMalformedBusinessRuleError):
        BusinessRule.new(
            business_condition_id="malformed",
            version=1,
            tenant_id="tenant-a",
            rule_family=RuleFamily.CONDITIONAL_REQUIRED,
            applicability=None,  # missing required applicability
            predicate=ComparatorNode(
                clause_id="c1",
                operator=Operator.IS_NOT_NULL,
                input_role="a",
                comparand_kind=ComparandKind.NONE,
            ),
            input_bindings=(_binding(role="a"),),
            status=BusinessRuleStatus.ACTIVE,
            created_by="tester",
            created_on=NOW,
        )
