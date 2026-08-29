"""OQI3-I2 deterministic `BusinessRule` evaluation (CDD-041 §10-§13,
§16-§21). Implements the CDD-041 §21 algorithm's *deterministic core* only
(steps 7-9, 11, 13-16): select the governed input frontier, parse each
bound input per its `expected_type`, evaluate applicability, evaluate the
predicate without short-circuit, derive observations/outcome, and persist
the immutable ledger atomically. Steps 1-6, 10, and 17 (ACTIVE-status gate,
Finding identity, advisory-lock authority seed=3, and Finding transition
mutation) belong exclusively to OQI3-I3 (CDD-041 §33) and are never
implemented here.

`evaluate_historical` is the one complete, safe, standalone entry point in
this phase -- HISTORICAL mode never needs Finding authority (CDD-041 §23),
so its evidence-frontier coherence rests only on evidence being immutable
and horizon-filtered, exactly OQI1/OQI2's own HISTORICAL discipline.

`select_input_frontier` and `determine_outcome` are the reusable building
blocks OQI3-I3 will compose *inside* its advisory-lock authority for
CURRENT_STATE evaluation -- calling them standalone, as this module's own
HISTORICAL path and this phase's tests do, makes no CURRENT_STATE
concurrency-safety claim whatsoever (see the OQI3-I2 report's honest
concurrency-scope analysis, CDD-041 §21 steps 1-6)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol
from uuid import UUID

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
from app.domain.oqi_business_rule.rule import (
    AstNode,
    BusinessRule,
    ComparandKind,
    ComparatorNode,
    ExpectedType,
    Operator,
    RuleFamily,
    validate_business_rule_shape,
)
from app.domain.shared.exceptions import ValidationException

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BOOLEAN_TRUE = "true"
_BOOLEAN_FALSE = "false"

TypedValue = str | Decimal | bool | date


class OqiBusinessRuleEvaluationRepository(Protocol):
    def select_known_lineage(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> bool: ...

    def select_latest_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None: ...

    def insert_evaluation_idempotent(self, evaluation: BusinessRuleEvaluation) -> bool: ...


def parse_typed_value(expected_type: ExpectedType, raw: str) -> TypedValue | None:
    """CDD-041 §10: closed deterministic parser per type. Returns `None` on
    parser failure -- the caller must treat that as an unavailable typed
    value (contributing to `NOT_EVALUABLE`), never as `VIOLATED`."""
    if expected_type is ExpectedType.STRING:
        return raw
    if expected_type is ExpectedType.DECIMAL:
        try:
            return Decimal(raw.strip())
        except (InvalidOperation, AttributeError):
            return None
    if expected_type is ExpectedType.BOOLEAN:
        if raw == _BOOLEAN_TRUE:
            return True
        if raw == _BOOLEAN_FALSE:
            return False
        return None
    if expected_type is ExpectedType.DATE:
        if not _DATE_PATTERN.fullmatch(raw):
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
    raise ValidationException(f"unsupported expected_type: {expected_type!r}")  # pragma: no cover


def _compare(operator: Operator, left: TypedValue, right: TypedValue) -> bool:
    if operator is Operator.EQ:
        return left == right
    if operator is Operator.NE:
        return left != right
    if operator is Operator.LT:
        return left < right  # type: ignore[operator]
    if operator is Operator.LTE:
        return left <= right  # type: ignore[operator]
    if operator is Operator.GT:
        return left > right  # type: ignore[operator]
    if operator is Operator.GTE:
        return left >= right  # type: ignore[operator]
    raise ValidationException(f"unsupported comparator: {operator!r}")  # pragma: no cover


def _evaluate_leaf(
    node: ComparatorNode,
    *,
    present_roles: frozenset[str],
    typed_values: dict[str, TypedValue],
) -> bool | None:
    """`None` means this leaf is not deterministically evaluable (CDD-041
    §13). `IS_NULL`/`IS_NOT_NULL` test evidence *presence*, never parsed
    content (CDD-041 §11) -- they are the only comparators that never
    return `None`, since presence is always knowable once the subject
    itself is known."""
    if node.operator is Operator.IS_NULL:
        return node.input_role not in present_roles
    if node.operator is Operator.IS_NOT_NULL:
        return node.input_role in present_roles

    if node.input_role not in typed_values:
        return None
    left = typed_values[node.input_role]
    if node.comparand_kind is ComparandKind.LITERAL:
        assert node.literal_type is not None and node.literal_value is not None
        right = parse_typed_value(node.literal_type, node.literal_value)
        if right is None:
            return None
    else:
        assert node.comparand_input_role is not None
        if node.comparand_input_role not in typed_values:
            return None
        right = typed_values[node.comparand_input_role]
    return _compare(node.operator, left, right)


def _evaluate_tree(
    node: AstNode, *, present_roles: frozenset[str], typed_values: dict[str, TypedValue]
) -> bool | None:
    """Strong (Kleene) three-valued evaluation: `AND`/`OR` are determinable
    to `False`/`True` respectively as soon as one child forces that result,
    even if other children are indeterminate -- otherwise `None`. This is
    an OQI3-I2 evaluator-internal decision (CDD-041 does not fix composition
    truth tables); it never fabricates a determinate result from unknown
    inputs (CDD-039's "absence of knowledge is not knowledge of absence"
    epistemic discipline, reused by structural analogy)."""
    if isinstance(node, ComparatorNode):
        return _evaluate_leaf(node, present_roles=present_roles, typed_values=typed_values)

    child_results = [
        _evaluate_tree(child, present_roles=present_roles, typed_values=typed_values)
        for child in node.children
    ]
    if node.operator is Operator.NOT:
        (only,) = child_results
        return None if only is None else not only
    if node.operator is Operator.AND:
        if any(result is False for result in child_results):
            return False
        if any(result is None for result in child_results):
            return None
        return True
    if node.operator is Operator.OR:
        if any(result is True for result in child_results):
            return True
        if any(result is None for result in child_results):
            return None
        return False
    if node.operator is Operator.IMPLIES:
        antecedent, consequent = child_results
        if antecedent is False:
            return True
        if consequent is True:
            return True
        if antecedent is True and consequent is False:
            return False
        return None
    raise ValidationException(
        f"unsupported composition operator: {node.operator!r}"
    )  # pragma: no cover


def _predicate_leaves(predicate: AstNode) -> tuple[ComparatorNode, ...]:
    """CDD-041 §4.2 (OQI3-G2/I2-R): a `CONDITIONAL_REQUIRED`/
    `CONDITIONAL_PROHIBITED`/`FIELD_COMPARISON` predicate, after
    `validate_business_rule_shape`, is exactly one `ComparatorNode` or an
    `AND`-only `CompositionNode` of `ComparatorNode` leaves -- never
    nested, never a mixed connective. This is the single point that
    depends on that closed shape to enumerate the independently
    observable consequence clauses."""
    if isinstance(predicate, ComparatorNode):
        return (predicate,)
    return tuple(child for child in predicate.children if isinstance(child, ComparatorNode))


@dataclass(frozen=True, slots=True)
class SingleRecordSubject:
    tenant_id: str
    source_object_id: UUID
    source_record_reference: str


def select_input_frontier(
    *,
    rule: BusinessRule,
    subject: SingleRecordSubject,
    evaluation_horizon: datetime,
    repository: OqiBusinessRuleEvaluationRepository,
) -> tuple[BusinessRuleEvaluationInputEntry, ...] | None:
    """CDD-041 §21 steps 7-8: select ALL bound input evidence under one
    governed horizon. Returns `None` if the subject itself is unknown to
    CTEC (CDD-041 §6/§13's "absence of knowledge is not knowledge of
    absence") -- the caller must treat that as `NOT_EVALUABLE`, never
    manufacture a required-input violation for an unknown record.

    Calling this function standalone (no lock held) makes no CURRENT_STATE
    coherent-frontier guarantee -- see the OQI3-I2 report."""
    if not repository.select_known_lineage(
        source_object_id=subject.source_object_id,
        source_record_reference=subject.source_record_reference,
        evaluation_horizon=evaluation_horizon,
    ):
        return None

    entries: list[BusinessRuleEvaluationInputEntry] = []
    for binding in rule.input_bindings:
        latest = repository.select_latest_field_value(
            source_field_id=binding.source_field_id,
            source_record_reference=subject.source_record_reference,
            evaluation_horizon=evaluation_horizon,
        )
        entries.append(
            BusinessRuleEvaluationInputEntry(
                input_role=binding.input_role,
                evidence_id=(None if latest is None else latest[0]),
            )
        )
    return tuple(entries)


def determine_outcome(
    *,
    rule: BusinessRule,
    inputs: tuple[BusinessRuleEvaluationInputEntry, ...],
    raw_values: dict[str, str],
) -> tuple[EvaluationOutcome, tuple[BusinessRuleEvaluationObservation, ...]] | None:
    """CDD-041 §21 steps 9, 11, 13-15: parse, evaluate applicability, then
    the full predicate without short-circuit, then derive observations and
    outcome. Returns `None` for `NOT_EVALUABLE` (CDD-041 §13) -- the caller
    must persist nothing at all in that case.

    `raw_values` maps `input_role -> FieldValueEvidence.observed_representation`
    for every role in `inputs` whose `evidence_id is not None` (the caller
    is responsible for fetching these; kept out of this pure function so it
    stays independently unit-testable without a database)."""
    # CDD-041 §26 point: evaluation-time defensive re-validation of
    # whatever persisted rule shape was loaded, mirroring OQI1's
    # `validate_rule_shape` re-check precedent exactly.
    validate_business_rule_shape(
        rule_family=rule.rule_family,
        applicability=rule.applicability,
        predicate=rule.predicate,
        input_bindings=rule.input_bindings,
    )

    present_roles = frozenset(entry.input_role for entry in inputs if entry.evidence_id is not None)
    bindings_by_role = {binding.input_role: binding for binding in rule.input_bindings}
    typed_values: dict[str, TypedValue] = {}
    for role, raw in raw_values.items():
        binding = bindings_by_role[role]
        parsed = parse_typed_value(binding.expected_type, raw)
        if parsed is not None:
            typed_values[role] = parsed

    if rule.applicability is None:
        applicability_result: bool | None = True
    else:
        applicability_result = _evaluate_tree(
            rule.applicability, present_roles=present_roles, typed_values=typed_values
        )

    if applicability_result is None:
        return None
    if applicability_result is False:
        return EvaluationOutcome.NOT_APPLICABLE, ()

    # CDD-041 §4.2/§4.5-§4.8 (OQI3-G2/I2-R): predicate is either a single
    # ComparatorNode (unchanged, backward compatible) or an AND-only
    # CompositionNode of ComparatorNode leaves (enforced by
    # validate_business_rule_shape above -- never nested, never
    # OR/NOT/IMPLIES). `_evaluate_tree` already implements strong Kleene
    # AND (FALSE beats UNKNOWN beats TRUE), so the top-level result is
    # correct for both shapes with no special-casing.
    predicate_result = _evaluate_tree(
        rule.predicate, present_roles=present_roles, typed_values=typed_values
    )
    if predicate_result is None:
        return None
    if predicate_result:
        return EvaluationOutcome.SATISFIED, ()

    observation_type = (
        ObservationType.REQUIRED_INPUT_MISSING
        if rule.rule_family is RuleFamily.CONDITIONAL_REQUIRED
        else ObservationType.CLAUSE_VIOLATED
    )
    # CDD-041 §4.5/§4.8: complete failure-set semantics -- collect an
    # Observation for every leaf that is deterministically FALSE, never
    # for a leaf that is TRUE (it succeeded) or UNKNOWN (absence of
    # knowledge is not knowledge of absence, applied per-clause). Strong
    # Kleene AND guarantees at least one leaf is FALSE whenever the
    # top-level result is FALSE, so this tuple is never empty.
    violated_leaves = tuple(
        leaf
        for leaf in _predicate_leaves(rule.predicate)
        if _evaluate_leaf(leaf, present_roles=present_roles, typed_values=typed_values) is False
    )
    observations = tuple(
        BusinessRuleEvaluationObservation(
            clause_id=leaf.clause_id,
            observation_type=observation_type,
            input_role=leaf.input_role,
        )
        for leaf in violated_leaves
    )
    return EvaluationOutcome.VIOLATED, observations


class EvidenceValueReader(Protocol):
    def read_values(
        self, inputs: tuple[BusinessRuleEvaluationInputEntry, ...]
    ) -> dict[str, str]: ...


class OqiBusinessRuleEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: OqiBusinessRuleEvaluationRepository,
        evidence_value_reader: EvidenceValueReader,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = evaluation_repository
        self._evidence_value_reader = evidence_value_reader
        self._clock = clock

    def evaluate_historical(
        self,
        *,
        rule: BusinessRule,
        subject: SingleRecordSubject,
        evaluation_horizon: datetime,
    ) -> BusinessRuleEvaluation | None:
        """CDD-041 §23: caller-supplied horizon; never acquires authority;
        never creates, mutates, reopens, or resolves a `BusinessRuleFinding`
        -- no Finding code is invoked or imported anywhere in this method."""
        if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")

        inputs = select_input_frontier(
            rule=rule,
            subject=subject,
            evaluation_horizon=evaluation_horizon,
            repository=self._repository,
        )
        if inputs is None:
            return None

        raw_values = self._evidence_value_reader.read_values(inputs)
        result = determine_outcome(rule=rule, inputs=inputs, raw_values=raw_values)
        if result is None:
            return None
        outcome, observations = result

        subject_identity = canonical_single_record_subject_identity(
            source_object_id=subject.source_object_id,
            source_record_reference=subject.source_record_reference,
        )
        digest = input_evidence_digest(inputs)
        evaluation = BusinessRuleEvaluation(
            evaluation_id=derive_business_rule_evaluation_id(
                tenant_id=subject.tenant_id,
                business_condition_id=rule.business_condition_id,
                rule_version=rule.version,
                subject_type=SUBJECT_TYPE_SINGLE_RECORD,
                subject_identity=subject_identity,
                evaluation_mode=EvaluationMode.HISTORICAL,
                evaluation_horizon=evaluation_horizon,
                input_evidence_digest_value=digest,
            ),
            tenant_id=subject.tenant_id,
            business_condition_id=rule.business_condition_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            subject_type=SUBJECT_TYPE_SINGLE_RECORD,
            subject_identity=subject_identity,
            source_object_id=subject.source_object_id,
            source_record_reference=subject.source_record_reference,
            evaluation_mode=EvaluationMode.HISTORICAL,
            evaluation_horizon=evaluation_horizon,
            inputs=inputs,
            outcome=outcome,
            observations=observations,
            evaluated_at=self._clock(),
        )
        self._repository.insert_evaluation_idempotent(evaluation)
        return evaluation
