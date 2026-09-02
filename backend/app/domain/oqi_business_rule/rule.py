"""OQI3 governed `BusinessRule`/`BusinessRuleInputBinding`/declarative-AST
identity, closed shape, and publication-time validation (CDD-041 §3-§12,
§19, §22, §26). `BusinessRule` is a first-class sibling of OQI1's
`QualityRule` (CDD-039) -- never a subtype, extension row, or shared-table
discriminator; `QualityRule`, its `_ALLOWED_COMBINATIONS` coupling table, and
`validate_rule_shape` are never imported, referenced, or modified here.

The declarative AST is closed to exactly two node kinds -- `ComparatorNode`
(one of the 8 authorized comparators, CDD-041 §12) and `CompositionNode`
(AND/OR/NOT/IMPLIES) -- never an arbitrary expression string, callable
reference, or executable code (CDD-041 §12, §25). A comparator's right-hand
side is either a typed literal (`comparand_kind=LITERAL`, raw representation
parsed only at OQI3-I2 evaluation time, never here) or another bound input
role (`comparand_kind=INPUT_ROLE`, for `FIELD_COMPARISON`); a presence check
(`IS_NULL`/`IS_NOT_NULL`) takes no comparand at all. `validate_business_rule_
shape` is the single, shared validator this document requires to run at
construction, publication/activation, and (by OQI3-I2/I3) evaluation-time
defensive re-validation -- a malformed rule must never become `ACTIVE`."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.shared.exceptions import DomainException, ValidationException

# CDD-041 §4: fixed, frozen forever once implemented. Deliberately distinct
# from OQI1's OQI_NAMESPACE ("urn:ctec:oqi:v1") and OQI2's
# OQI_CROSS_SOURCE_NAMESPACE ("urn:ctec:oqi:cross-source:v1"), so no OQI3
# identity can ever collide with an OQI1/OQI2/evidence identity under any
# adversarially-chosen input.
OQI_BUSINESS_RULE_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:business-rule:v1")

_MAX_CONDITION_ID_LENGTH = 200
_MAX_TENANT_ID_LENGTH = 200
_MAX_INPUT_ROLE_LENGTH = 64
_MAX_CLAUSE_ID_LENGTH = 64
_MAX_LITERAL_VALUE_LENGTH = 1000

# CDD-041 §12: publication-time AST bounds. Conservative constants, since
# CDD-041 delegates exact numeric bounds to implementation while requiring
# them to exist and be enforced (never unbounded recursive expressions).
MAX_AST_DEPTH = 8
MAX_AST_NODES = 64


class OqiMalformedBusinessRuleError(DomainException):
    """CDD-041 §26: raised whenever a governed `BusinessRule`'s shape --
    family, AST, bindings, or operator/type compatibility -- is invalid, at
    construction or at publication/activation. Never caught to silently
    fabricate SATISFIED/VIOLATED, and never repaired automatically."""


class RuleFamily(StrEnum):
    """CDD-041 §5: exactly these three, closed. No fourth family, no
    CUSTOM/EXPRESSION/SCRIPT escape hatch, without a new governance
    amendment."""

    CONDITIONAL_REQUIRED = "CONDITIONAL_REQUIRED"
    CONDITIONAL_PROHIBITED = "CONDITIONAL_PROHIBITED"
    FIELD_COMPARISON = "FIELD_COMPARISON"


class ExpectedType(StrEnum):
    """CDD-041 §9: exactly these four, closed. No INTEGER (merged into
    DECIMAL), DATETIME, TIME, BINARY, JSON, or business-semantic type."""

    STRING = "STRING"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"


class BusinessRuleStatus(StrEnum):
    """CDD-041 §4: exactly these two, closed. No DRAFT."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class BusinessRulePurpose(StrEnum):
    """CDD-048 §14, §19: closed, exactly these three -- the governed
    dimension/purpose tag distinguishing a legacy (pre-H2) OQI3 business
    rule from an H2 REASONABLENESS rule from an H2 ACCURACY_REFERENCE_
    DERIVATION rule. A single `BusinessRule` version carries exactly one
    purpose, never two simultaneously (CDD-048 §19's circular-proof
    prevention: a rule may never be both a Reasonableness plausibility
    check and an Accuracy reference-deriving rule). `LEGACY_UNCLASSIFIED_
    BUSINESS_RULE` is the frozen, honest default for every rule created
    before this document -- never retroactively reclassified as
    REASONABLENESS (CDD-048 §13)."""

    LEGACY_UNCLASSIFIED_BUSINESS_RULE = "LEGACY_UNCLASSIFIED_BUSINESS_RULE"
    REASONABLENESS = "REASONABLENESS"
    ACCURACY_REFERENCE_DERIVATION = "ACCURACY_REFERENCE_DERIVATION"


class Operator(StrEnum):
    """CDD-041 §12: exactly these twelve node operators, closed. The first
    eight are comparators (leaves); the last four are composition
    (branches). No other operator is authorized without a new governance
    amendment."""

    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    IS_NULL = "IS_NULL"
    IS_NOT_NULL = "IS_NOT_NULL"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    IMPLIES = "IMPLIES"


class ComparandKind(StrEnum):
    """Closed discriminator for a comparator node's right-hand side. `NONE`
    for the two presence operators (which take no comparand); `LITERAL` for
    a typed constant (raw representation only -- parsing is an OQI3-I2
    evaluation-time concern, CDD-041 §10); `INPUT_ROLE` for comparing two
    bound inputs on the same subject (`FIELD_COMPARISON`, CDD-041 §5)."""

    NONE = "NONE"
    LITERAL = "LITERAL"
    INPUT_ROLE = "INPUT_ROLE"


_COMPARATOR_OPERATORS: frozenset[Operator] = frozenset(
    {
        Operator.EQ,
        Operator.NE,
        Operator.LT,
        Operator.LTE,
        Operator.GT,
        Operator.GTE,
        Operator.IS_NULL,
        Operator.IS_NOT_NULL,
    }
)
_COMPOSITION_OPERATORS: frozenset[Operator] = frozenset(
    {Operator.AND, Operator.OR, Operator.NOT, Operator.IMPLIES}
)
_UNARY_COMPARATORS: frozenset[Operator] = frozenset({Operator.IS_NULL, Operator.IS_NOT_NULL})
_ORDERING_OPERATORS: frozenset[Operator] = frozenset(
    {Operator.LT, Operator.LTE, Operator.GT, Operator.GTE}
)
_EQUALITY_OPERATORS: frozenset[Operator] = frozenset({Operator.EQ, Operator.NE})


@dataclass(frozen=True, slots=True)
class ComparatorNode:
    """CDD-041 §12: one leaf predicate clause. `clause_id` is this clause's
    stable identity (CDD-041 §19), unique within its owning rule version."""

    clause_id: str
    operator: Operator
    input_role: str
    comparand_kind: ComparandKind
    literal_type: ExpectedType | None = None
    literal_value: str | None = None
    comparand_input_role: str | None = None

    def __post_init__(self) -> None:
        if self.operator not in _COMPARATOR_OPERATORS:
            raise OqiMalformedBusinessRuleError(
                f"ComparatorNode operator must be one of {_COMPARATOR_OPERATORS}, "
                f"got {self.operator!r}"
            )
        if not isinstance(self.clause_id, str) or not (
            1 <= len(self.clause_id) <= _MAX_CLAUSE_ID_LENGTH
        ):
            raise OqiMalformedBusinessRuleError(
                f"clause_id must be non-empty text of length <= {_MAX_CLAUSE_ID_LENGTH}"
            )
        if not isinstance(self.input_role, str) or not (
            1 <= len(self.input_role) <= _MAX_INPUT_ROLE_LENGTH
        ):
            raise OqiMalformedBusinessRuleError(
                f"input_role must be non-empty text of length <= {_MAX_INPUT_ROLE_LENGTH}"
            )

        if self.operator in _UNARY_COMPARATORS:
            if self.comparand_kind is not ComparandKind.NONE:
                raise OqiMalformedBusinessRuleError(
                    f"{self.operator} takes no comparand -- comparand_kind must be NONE"
                )
            if (
                self.literal_type is not None
                or self.literal_value is not None
                or self.comparand_input_role is not None
            ):
                raise OqiMalformedBusinessRuleError(
                    f"{self.operator} must not carry literal_type/literal_value/"
                    "comparand_input_role"
                )
            return

        # Binary comparators: EQ/NE/LT/LTE/GT/GTE.
        if self.comparand_kind is ComparandKind.LITERAL:
            if self.comparand_input_role is not None:
                raise OqiMalformedBusinessRuleError(
                    "comparand_kind=LITERAL must not carry comparand_input_role"
                )
            if not isinstance(self.literal_type, ExpectedType):
                raise OqiMalformedBusinessRuleError(
                    "comparand_kind=LITERAL requires a governed literal_type"
                )
            if not isinstance(self.literal_value, str) or not (
                0 <= len(self.literal_value) <= _MAX_LITERAL_VALUE_LENGTH
            ):
                raise OqiMalformedBusinessRuleError(
                    f"literal_value must be text of length <= {_MAX_LITERAL_VALUE_LENGTH}"
                )
        elif self.comparand_kind is ComparandKind.INPUT_ROLE:
            if self.literal_type is not None or self.literal_value is not None:
                raise OqiMalformedBusinessRuleError(
                    "comparand_kind=INPUT_ROLE must not carry literal_type/literal_value"
                )
            if not isinstance(self.comparand_input_role, str) or not (
                1 <= len(self.comparand_input_role) <= _MAX_INPUT_ROLE_LENGTH
            ):
                raise OqiMalformedBusinessRuleError(
                    "comparand_kind=INPUT_ROLE requires a governed comparand_input_role"
                )
            if self.comparand_input_role == self.input_role:
                raise OqiMalformedBusinessRuleError(
                    "a comparator must not compare an input_role against itself"
                )
        else:
            raise OqiMalformedBusinessRuleError(
                f"{self.operator} requires comparand_kind of LITERAL or INPUT_ROLE, "
                f"got {self.comparand_kind!r}"
            )


@dataclass(frozen=True, slots=True)
class CompositionNode:
    """CDD-041 §12: AND/OR (>=2 children), NOT (exactly 1 child), IMPLIES
    (exactly 2 children: antecedent, consequent)."""

    operator: Operator
    children: tuple[AstNode, ...]

    def __post_init__(self) -> None:
        if self.operator not in _COMPOSITION_OPERATORS:
            raise OqiMalformedBusinessRuleError(
                f"CompositionNode operator must be one of {_COMPOSITION_OPERATORS}, "
                f"got {self.operator!r}"
            )
        if not isinstance(self.children, tuple) or not all(
            isinstance(child, ComparatorNode | CompositionNode) for child in self.children
        ):
            raise OqiMalformedBusinessRuleError(
                "children must be a tuple of ComparatorNode/CompositionNode instances"
            )
        if self.operator is Operator.NOT and len(self.children) != 1:
            raise OqiMalformedBusinessRuleError("NOT requires exactly 1 child")
        if self.operator is Operator.IMPLIES and len(self.children) != 2:
            raise OqiMalformedBusinessRuleError("IMPLIES requires exactly 2 children")
        if self.operator in (Operator.AND, Operator.OR) and len(self.children) < 2:
            raise OqiMalformedBusinessRuleError(f"{self.operator} requires at least 2 children")


AstNode = ComparatorNode | CompositionNode


def _ast_depth(node: AstNode) -> int:
    if isinstance(node, ComparatorNode):
        return 1
    return 1 + max((_ast_depth(child) for child in node.children), default=0)


def _ast_node_count(node: AstNode) -> int:
    if isinstance(node, ComparatorNode):
        return 1
    return 1 + sum(_ast_node_count(child) for child in node.children)


def _collect_comparator_nodes(node: AstNode) -> list[ComparatorNode]:
    if isinstance(node, ComparatorNode):
        return [node]
    collected: list[ComparatorNode] = []
    for child in node.children:
        collected.extend(_collect_comparator_nodes(child))
    return collected


def validate_ast_bounds(
    node: AstNode, *, max_depth: int = MAX_AST_DEPTH, max_nodes: int = MAX_AST_NODES
) -> None:
    """CDD-041 §12, §25: enforced at publication time. Unbounded recursive
    expressions are prohibited absolutely."""
    depth = _ast_depth(node)
    if depth > max_depth:
        raise OqiMalformedBusinessRuleError(f"AST depth {depth} exceeds maximum {max_depth}")
    node_count = _ast_node_count(node)
    if node_count > max_nodes:
        raise OqiMalformedBusinessRuleError(
            f"AST node count {node_count} exceeds maximum {max_nodes}"
        )


def ast_to_json(node: AstNode) -> dict[str, Any]:
    """Canonical JSON serialization for `business_rules.applicability`/
    `predicate` (JSON columns, mirroring `QualityRule.rule_parameters`'s own
    JSON-persistence precedent). Never persists an arbitrary expression
    string -- always this closed, tagged node shape."""
    if isinstance(node, ComparatorNode):
        return {
            "node_type": "COMPARATOR",
            "clause_id": node.clause_id,
            "operator": node.operator.value,
            "input_role": node.input_role,
            "comparand_kind": node.comparand_kind.value,
            "literal_type": node.literal_type.value if node.literal_type is not None else None,
            "literal_value": node.literal_value,
            "comparand_input_role": node.comparand_input_role,
        }
    if isinstance(node, CompositionNode):
        return {
            "node_type": "COMPOSITION",
            "operator": node.operator.value,
            "children": [ast_to_json(child) for child in node.children],
        }
    raise OqiMalformedBusinessRuleError(f"unsupported AST node instance: {node!r}")


_COMPARATOR_KEYS = frozenset(
    {
        "node_type",
        "clause_id",
        "operator",
        "input_role",
        "comparand_kind",
        "literal_type",
        "literal_value",
        "comparand_input_role",
    }
)
_COMPOSITION_KEYS = frozenset({"node_type", "operator", "children"})


def _require_str(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise OqiMalformedBusinessRuleError(f"{label} must be a string, got {value!r}")
    return value


def ast_from_json(data: Any) -> AstNode:
    """Strict, closed deserialization. Any unsupported `node_type`, unknown
    field, or non-enum operator/type/kind value is rejected here -- this is
    the boundary that guarantees no arbitrary-code-shaped payload (e.g. a
    forged node_type or an executable-looking operator) can ever become a
    constructible AST node (CDD-041 §12, §25)."""
    if not isinstance(data, Mapping):
        raise OqiMalformedBusinessRuleError("AST node must be a mapping")
    node_type = data.get("node_type")
    if node_type == "COMPARATOR":
        if not set(data.keys()) <= _COMPARATOR_KEYS:
            raise OqiMalformedBusinessRuleError(
                f"unsupported field(s) in comparator node: {set(data.keys()) - _COMPARATOR_KEYS}"
            )
        try:
            operator = Operator(_require_str(data.get("operator"), label="operator"))
        except ValueError as exc:
            raise OqiMalformedBusinessRuleError(
                f"invalid comparator operator: {data.get('operator')!r}"
            ) from exc
        try:
            comparand_kind = ComparandKind(
                _require_str(data.get("comparand_kind"), label="comparand_kind")
            )
        except ValueError as exc:
            raise OqiMalformedBusinessRuleError(
                f"invalid comparand_kind: {data.get('comparand_kind')!r}"
            ) from exc
        literal_type_raw = data.get("literal_type")
        literal_type: ExpectedType | None = None
        if literal_type_raw is not None:
            try:
                literal_type = ExpectedType(literal_type_raw)
            except ValueError as exc:
                raise OqiMalformedBusinessRuleError(
                    f"invalid literal_type: {literal_type_raw!r}"
                ) from exc
        literal_value = data.get("literal_value")
        comparand_input_role = data.get("comparand_input_role")
        return ComparatorNode(
            clause_id=_require_str(data.get("clause_id"), label="clause_id"),
            operator=operator,
            input_role=_require_str(data.get("input_role"), label="input_role"),
            comparand_kind=comparand_kind,
            literal_type=literal_type,
            literal_value=(
                None
                if literal_value is None
                else _require_str(literal_value, label="literal_value")
            ),
            comparand_input_role=(
                None
                if comparand_input_role is None
                else _require_str(comparand_input_role, label="comparand_input_role")
            ),
        )
    if node_type == "COMPOSITION":
        if not set(data.keys()) <= _COMPOSITION_KEYS:
            raise OqiMalformedBusinessRuleError(
                f"unsupported field(s) in composition node: {set(data.keys()) - _COMPOSITION_KEYS}"
            )
        try:
            operator = Operator(_require_str(data.get("operator"), label="operator"))
        except ValueError as exc:
            raise OqiMalformedBusinessRuleError(
                f"invalid composition operator: {data.get('operator')!r}"
            ) from exc
        children_raw = data.get("children")
        if not isinstance(children_raw, list):
            raise OqiMalformedBusinessRuleError("children must be a list")
        children = tuple(ast_from_json(child) for child in children_raw)
        return CompositionNode(operator=operator, children=children)
    raise OqiMalformedBusinessRuleError(f"unsupported AST node_type: {node_type!r}")


@dataclass(frozen=True, slots=True)
class BusinessRuleInputBinding:
    """CDD-041 §7-§9: one immutable, semantically-named input binding.
    `expected_type` is OQI3's own governed canonical-type ownership point
    (CDD-041 §8) -- `SourceField` is never modified and carries no type
    metadata of any kind."""

    input_role: str
    source_field_id: UUID
    required: bool
    expected_type: ExpectedType

    def __post_init__(self) -> None:
        if not isinstance(self.input_role, str) or not (
            1 <= len(self.input_role) <= _MAX_INPUT_ROLE_LENGTH
        ):
            raise ValidationException(
                f"input_role must be non-empty text of length <= {_MAX_INPUT_ROLE_LENGTH}"
            )
        if not isinstance(self.source_field_id, UUID):
            raise ValidationException("source_field_id must be a UUID")
        if not isinstance(self.required, bool):
            raise ValidationException("required must be an explicit boolean")
        if not isinstance(self.expected_type, ExpectedType):
            raise ValidationException("expected_type must be an ExpectedType")


def _validate_operator_type_compatibility(operator: Operator, expected_type: ExpectedType) -> None:
    """CDD-041 §11's closed publication-time matrix. Never discovered at
    runtime -- a malformed combination must never reach ACTIVE status."""
    if operator in _UNARY_COMPARATORS:
        return  # IS_NULL/IS_NOT_NULL: valid for all four types.
    if operator in _ORDERING_OPERATORS and expected_type not in (
        ExpectedType.DECIMAL,
        ExpectedType.DATE,
    ):
        raise OqiMalformedBusinessRuleError(
            f"{operator} is not authorized for type {expected_type} "
            "(LT/LTE/GT/GTE are valid only for DECIMAL, DATE)"
        )
    # EQ/NE: valid for all four types -- nothing further to check.


def _validate_comparator_against_bindings(
    node: ComparatorNode, *, bindings_by_role: Mapping[str, BusinessRuleInputBinding]
) -> None:
    binding = bindings_by_role.get(node.input_role)
    if binding is None:
        raise OqiMalformedBusinessRuleError(
            f"comparator references unknown input_role: {node.input_role!r}"
        )
    _validate_operator_type_compatibility(node.operator, binding.expected_type)

    if node.comparand_kind is ComparandKind.LITERAL:
        if node.literal_type is not binding.expected_type:
            raise OqiMalformedBusinessRuleError(
                f"literal_type {node.literal_type} does not match input_role "
                f"{node.input_role!r}'s expected_type {binding.expected_type} -- "
                "implicit coercion is prohibited"
            )
    elif node.comparand_kind is ComparandKind.INPUT_ROLE:
        assert node.comparand_input_role is not None  # enforced by ComparatorNode.__post_init__
        comparand_binding = bindings_by_role.get(node.comparand_input_role)
        if comparand_binding is None:
            raise OqiMalformedBusinessRuleError(
                f"comparator references unknown comparand_input_role: "
                f"{node.comparand_input_role!r}"
            )
        if comparand_binding.expected_type is not binding.expected_type:
            raise OqiMalformedBusinessRuleError(
                f"comparator compares incompatible types: {node.input_role!r} is "
                f"{binding.expected_type} but {node.comparand_input_role!r} is "
                f"{comparand_binding.expected_type} -- implicit coercion is prohibited"
            )


def _validate_and_only_conditional_consequence(
    predicate: AstNode,
    *,
    leaf_check: Any,
    family_label: str,
    leaf_shape_description: str,
) -> None:
    """CDD-041 §4.2 (OQI3-I2-R): a `CONDITIONAL_REQUIRED`/`CONDITIONAL_
    PROHIBITED` predicate is either a single `ComparatorNode` (the original
    singular shape, unchanged, fully backward compatible) or an `AND`-only
    `CompositionNode` whose direct children are each a single, family-
    appropriate `ComparatorNode` -- no nesting, no mixed connective. `OR`,
    `NOT`, and nested `IMPLIES` are never authorized as compound consequence
    composition (CDD-041 §4.2/§4.10) regardless of leaf shape."""
    if isinstance(predicate, ComparatorNode):
        if not leaf_check(predicate):
            raise OqiMalformedBusinessRuleError(
                f"{family_label}'s predicate must be exactly one {leaf_shape_description}, "
                "or an AND-only compound of such comparators"
            )
        return
    if isinstance(predicate, CompositionNode) and predicate.operator is Operator.AND:
        for child in predicate.children:
            if not isinstance(child, ComparatorNode) or not leaf_check(child):
                raise OqiMalformedBusinessRuleError(
                    f"{family_label}'s AND-compound predicate children must each be "
                    f"{leaf_shape_description} -- no nesting, no mixed connective"
                )
        return
    raise OqiMalformedBusinessRuleError(
        f"{family_label}'s predicate must be exactly one {leaf_shape_description}, "
        "or an AND-only compound of such comparators (OR/NOT/IMPLIES are not "
        "authorized as compound consequence composition, CDD-041 §4.2/§4.10)"
    )


def validate_business_rule_shape(
    *,
    rule_family: RuleFamily,
    applicability: AstNode | None,
    predicate: AstNode,
    input_bindings: tuple[BusinessRuleInputBinding, ...],
) -> None:
    """CDD-041 §22, §26: the single, shared validation function reused at
    construction, publication/activation, and (by OQI3-I2/I3) evaluation-time
    defensive re-validation. Enforces the closed structural contract for
    each of the three initial rule families -- a `CONDITIONAL_REQUIRED` rule
    may not masquerade as an arbitrary AST that merely happens to produce a
    boolean."""
    if not isinstance(rule_family, RuleFamily):
        raise OqiMalformedBusinessRuleError("rule_family must be a RuleFamily")
    if not isinstance(input_bindings, tuple) or not all(
        isinstance(binding, BusinessRuleInputBinding) for binding in input_bindings
    ):
        raise OqiMalformedBusinessRuleError(
            "input_bindings must be a tuple of BusinessRuleInputBinding instances"
        )
    if not input_bindings:
        raise OqiMalformedBusinessRuleError("a BusinessRule requires at least one input binding")
    roles = [binding.input_role for binding in input_bindings]
    if len(set(roles)) != len(roles):
        raise OqiMalformedBusinessRuleError("input_role must be unique within a rule version")
    bindings_by_role = {binding.input_role: binding for binding in input_bindings}

    if applicability is not None and not isinstance(
        applicability, ComparatorNode | CompositionNode
    ):
        raise OqiMalformedBusinessRuleError("applicability must be an AstNode or None")
    if not isinstance(predicate, ComparatorNode | CompositionNode):
        raise OqiMalformedBusinessRuleError("predicate must be an AstNode")

    trees = [predicate] + ([applicability] if applicability is not None else [])
    for tree in trees:
        validate_ast_bounds(tree)

    clause_ids: list[str] = []
    for tree in trees:
        for comparator in _collect_comparator_nodes(tree):
            _validate_comparator_against_bindings(comparator, bindings_by_role=bindings_by_role)
            clause_ids.append(comparator.clause_id)
    if len(set(clause_ids)) != len(clause_ids):
        raise OqiMalformedBusinessRuleError("clause_id must be unique within a rule version")

    if rule_family is RuleFamily.CONDITIONAL_REQUIRED:
        if applicability is None:
            raise OqiMalformedBusinessRuleError(
                "CONDITIONAL_REQUIRED requires an explicit applicability predicate"
            )
        _validate_and_only_conditional_consequence(
            predicate,
            leaf_check=lambda leaf: leaf.operator is Operator.IS_NOT_NULL,
            family_label="CONDITIONAL_REQUIRED",
            leaf_shape_description="IS_NOT_NULL comparator naming the required input_role",
        )
    elif rule_family is RuleFamily.CONDITIONAL_PROHIBITED:
        if applicability is None:
            raise OqiMalformedBusinessRuleError(
                "CONDITIONAL_PROHIBITED requires an explicit applicability predicate"
            )
        _validate_and_only_conditional_consequence(
            predicate,
            leaf_check=lambda _leaf: True,
            family_label="CONDITIONAL_PROHIBITED",
            leaf_shape_description="comparator naming the prohibited state",
        )
    elif rule_family is RuleFamily.FIELD_COMPARISON:
        if not (
            isinstance(predicate, ComparatorNode)
            and predicate.operator in (_ORDERING_OPERATORS | _EQUALITY_OPERATORS)
            and predicate.comparand_kind is ComparandKind.INPUT_ROLE
        ):
            raise OqiMalformedBusinessRuleError(
                "FIELD_COMPARISON's predicate must be exactly one relational comparator "
                "(EQ/NE/LT/LTE/GT/GTE) between two input roles"
            )
    else:  # pragma: no cover -- RuleFamily is exhaustively closed above.
        raise OqiMalformedBusinessRuleError(f"unhandled rule_family: {rule_family!r}")


def derive_business_rule_id(*, business_condition_id: str, version: int) -> UUID:
    """CDD-041 §4's exact deterministic identity formula."""
    return uuid5(OQI_BUSINESS_RULE_NAMESPACE, f"business_rule:{business_condition_id}:{version}")


@dataclass(frozen=True, slots=True)
class BusinessRule:
    rule_id: UUID
    business_condition_id: str
    version: int
    tenant_id: str
    rule_family: RuleFamily
    applicability: AstNode | None
    predicate: AstNode
    input_bindings: tuple[BusinessRuleInputBinding, ...]
    status: BusinessRuleStatus
    created_by: str
    created_on: datetime
    retired_on: datetime | None = None
    dimension: BusinessRulePurpose = BusinessRulePurpose.LEGACY_UNCLASSIFIED_BUSINESS_RULE

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, UUID):
            raise ValidationException("rule_id must be a UUID")
        if not isinstance(self.business_condition_id, str) or not (
            1 <= len(self.business_condition_id) <= _MAX_CONDITION_ID_LENGTH
        ):
            raise ValidationException(
                f"business_condition_id must be non-empty text of length <= "
                f"{_MAX_CONDITION_ID_LENGTH}"
            )
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValidationException("version must be a positive integer")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException(
                f"tenant_id must be non-empty text of length <= {_MAX_TENANT_ID_LENGTH}"
            )
        if not isinstance(self.status, BusinessRuleStatus):
            raise ValidationException("status must be a BusinessRuleStatus")
        if not isinstance(self.created_by, str) or not self.created_by.strip():
            raise ValidationException("created_by must be non-blank text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")
        if self.status is BusinessRuleStatus.ACTIVE and self.retired_on is not None:
            raise ValidationException("ACTIVE rules must not carry retired_on")
        if self.status is BusinessRuleStatus.RETIRED and self.retired_on is None:
            raise ValidationException("RETIRED rules must carry retired_on")
        if self.retired_on is not None and self.retired_on.tzinfo is None:
            raise ValidationException("retired_on must include a timezone")
        if not isinstance(self.dimension, BusinessRulePurpose):
            raise ValidationException("dimension must be a BusinessRulePurpose")

        # CDD-041 §26 point 1: construction-time enforcement.
        validate_business_rule_shape(
            rule_family=self.rule_family,
            applicability=self.applicability,
            predicate=self.predicate,
            input_bindings=self.input_bindings,
        )

        expected_id = derive_business_rule_id(
            business_condition_id=self.business_condition_id, version=self.version
        )
        if self.rule_id != expected_id:
            raise ValidationException(
                "rule_id is inconsistent with its own governed semantic identity inputs"
            )

    @classmethod
    def new(
        cls,
        *,
        business_condition_id: str,
        version: int,
        tenant_id: str,
        rule_family: RuleFamily,
        applicability: AstNode | None,
        predicate: AstNode,
        input_bindings: tuple[BusinessRuleInputBinding, ...],
        status: BusinessRuleStatus,
        created_by: str,
        created_on: datetime,
        retired_on: datetime | None = None,
        dimension: BusinessRulePurpose = BusinessRulePurpose.LEGACY_UNCLASSIFIED_BUSINESS_RULE,
    ) -> BusinessRule:
        rule_id = derive_business_rule_id(
            business_condition_id=business_condition_id, version=version
        )
        return cls(
            rule_id=rule_id,
            business_condition_id=business_condition_id,
            version=version,
            tenant_id=tenant_id,
            rule_family=rule_family,
            applicability=applicability,
            predicate=predicate,
            input_bindings=input_bindings,
            status=status,
            created_by=created_by,
            created_on=created_on,
            retired_on=retired_on,
            dimension=dimension,
        )
