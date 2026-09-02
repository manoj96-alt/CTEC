"""OQI3 deterministic `BusinessRule` evaluation (CDD-041 §10-§13, §16-§21).
Implements the full CDD-041 §21 algorithm: `evaluate_historical` (OQI3-I2)
never acquires Finding authority (CDD-041 §23) and its evidence-frontier
coherence rests only on evidence being immutable and horizon-filtered,
exactly OQI1/OQI2's own HISTORICAL discipline. `evaluate_current_state`
(OQI3-I3) composes `select_input_frontier`/`determine_outcome` *inside*
seed-3 advisory-lock authority -- acquired before evidence selection and
held through Finding mutation and commit (CDD-041 §21 steps 1-6, 10, 17;
Atomic Multi-Field Evidence Frontier Amendment) -- which is what makes the
now-atomic evidence frontier plus this lock together provide the full
CURRENT_STATE correctness guarantee: the frontier fixes evaluator-vs-writer
snapshot coherence, the lock fixes evaluator-vs-evaluator Finding-ledger
mutual exclusion. Neither alone is sufficient; both are always exercised
together in `evaluate_current_state`.

`select_input_frontier` and `determine_outcome` remain independently callable
(as `evaluate_historical` and this module's own tests do) -- doing so makes
no CURRENT_STATE concurrency-safety claim by itself (see the OQI3-I2/I2-R3
reports' honest concurrency-scope analysis); only `evaluate_current_state`'s
full sequence provides that guarantee."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
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
from app.domain.oqi_business_rule.finding import (
    BusinessRuleFinding,
    ViolationType,
    apply_business_rule_finding_transition,
    business_rule_finding_identity_material,
    derive_business_rule_finding_id,
)
from app.domain.oqi_business_rule.rule import (
    AstNode,
    BusinessRule,
    BusinessRulePurpose,
    BusinessRuleStatus,
    ComparandKind,
    ComparatorNode,
    ExpectedType,
    Operator,
    RuleFamily,
    validate_business_rule_shape,
)
from app.domain.shared.exceptions import ValidationException


class OqiRuleNotActiveError(ValidationException):
    """Raised when CURRENT_STATE evaluation is attempted against a
    `BusinessRule` that is not the ACTIVE version for its
    `business_condition_id` (CDD-041 §21 step 2)."""


_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BOOLEAN_TRUE = "true"
_BOOLEAN_FALSE = "false"

TypedValue = str | Decimal | bool | date


class OqiBusinessRuleEvaluationRepository(Protocol):
    def select_evidence_frontier(
        self,
        *,
        source_object_id: UUID,
        source_record_reference: str,
        evaluation_horizon: datetime,
        bindings: Sequence[tuple[str, UUID]],
    ) -> tuple[bool, dict[str, UUID | None]]: ...

    def insert_evaluation_idempotent(self, evaluation: BusinessRuleEvaluation) -> bool: ...

    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_finding(self, finding_id: UUID) -> BusinessRuleFinding | None: ...

    def upsert_finding(self, finding: BusinessRuleFinding) -> None: ...


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
    """CDD-041 §21 steps 7-8 (CDD-041 Atomic Multi-Field Evidence Frontier
    Amendment, OQI3-I2-R3): select ALL bound input evidence under one
    governed horizon from one atomic PostgreSQL statement snapshot
    (`repository.select_evidence_frontier`) -- subject-known and every
    bound role's latest qualifying evidence are established together,
    closing the multi-statement evaluator-vs-evidence-writer race the
    prior sequential-SELECT algorithm could not (OQI3-I3/OQI3-R3 P1).
    Returns `None` if the subject itself is unknown to CTEC (CDD-041
    §6/§13's "absence of knowledge is not knowledge of absence") -- the
    caller must treat that as `NOT_EVALUABLE`, never manufacture a
    required-input violation for an unknown record.

    Calling this function standalone (no seed-3 lock held) fixes evidence-
    table snapshot coherence but makes no Finding-lifecycle serialization
    guarantee -- that remains OQI3-I3's advisory-lock authority (CDD-041
    Atomic Multi-Field Evidence Frontier Amendment §6)."""
    subject_known, evidence_by_role = repository.select_evidence_frontier(
        source_object_id=subject.source_object_id,
        source_record_reference=subject.source_record_reference,
        evaluation_horizon=evaluation_horizon,
        bindings=tuple(
            (binding.input_role, binding.source_field_id) for binding in rule.input_bindings
        ),
    )
    if not subject_known:
        return None

    return tuple(
        BusinessRuleEvaluationInputEntry(
            input_role=binding.input_role,
            evidence_id=evidence_by_role.get(binding.input_role),
        )
        for binding in rule.input_bindings
    )


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

    def evaluate_current_state(
        self,
        *,
        rule: BusinessRule,
        subject: SingleRecordSubject,
    ) -> BusinessRuleEvaluation | None:
        """CDD-041 §21 steps 1-18 (OQI3-I3): the full CURRENT_STATE algorithm.
        `rule` must be the caller-supplied, pre-loaded ACTIVE version -- it
        is never re-queried after lock acquisition, mirroring OQI1/OQI2
        exactly. Seed-3 authority is acquired before the trusted horizon is
        established and before any evidence is selected (steps 4-7); it is
        held through Finding mutation and commit (steps 17-18) -- the
        caller's transaction boundary (commit/rollback) governs all-or-
        nothing persistence and automatic lock release."""
        if rule.status is not BusinessRuleStatus.ACTIVE:
            raise OqiRuleNotActiveError(
                f"business_condition_id {rule.business_condition_id!r} has no ACTIVE version "
                "eligible for CURRENT_STATE evaluation"
            )

        subject_identity = canonical_single_record_subject_identity(
            source_object_id=subject.source_object_id,
            source_record_reference=subject.source_record_reference,
        )
        identity_material = business_rule_finding_identity_material(
            tenant_id=subject.tenant_id,
            business_condition_id=rule.business_condition_id,
            subject_type=SUBJECT_TYPE_SINGLE_RECORD,
            subject_identity=subject_identity,
        )
        # CDD-041 §21 step 5: authority MUST be acquired before the horizon
        # is established and before evidence selection -- this is the very
        # next line, unconditionally.
        self._repository.acquire_evaluation_authority(identity_material)

        # CDD-041 §21 step 6: defensive re-validation of whatever persisted
        # rule shape was loaded happens inside `determine_outcome` below
        # (mirrors OQI1's `validate_rule_shape` re-check precedent exactly)
        # -- no second database query for ACTIVE status is authorized or
        # needed, since `rule` is the caller's pre-loaded, never-re-queried
        # in-memory object (CDD-041 §21 step 1-2).
        horizon = self._clock()

        inputs = select_input_frontier(
            rule=rule,
            subject=subject,
            evaluation_horizon=horizon,
            repository=self._repository,
        )
        if inputs is None:
            # Subject unknown to CTEC: NOT_EVALUABLE. No Evaluation, no
            # Finding mutation. Authority releases automatically on
            # commit/rollback.
            return None

        raw_values = self._evidence_value_reader.read_values(inputs)
        result = determine_outcome(rule=rule, inputs=inputs, raw_values=raw_values)
        if result is None:
            # NOT_EVALUABLE: no Evaluation, no Finding mutation.
            return None
        outcome, observations = result

        finding_id = derive_business_rule_finding_id(
            tenant_id=subject.tenant_id,
            business_condition_id=rule.business_condition_id,
            subject_type=SUBJECT_TYPE_SINGLE_RECORD,
            subject_identity=subject_identity,
        )
        existing_finding = self._repository.get_finding(finding_id)

        digest = input_evidence_digest(inputs)
        evaluation_id = derive_business_rule_evaluation_id(
            tenant_id=subject.tenant_id,
            business_condition_id=rule.business_condition_id,
            rule_version=rule.version,
            subject_type=SUBJECT_TYPE_SINGLE_RECORD,
            subject_identity=subject_identity,
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_horizon=horizon,
            input_evidence_digest_value=digest,
        )
        next_finding = apply_business_rule_finding_transition(
            existing=existing_finding,
            outcome=outcome,
            evaluation_id=evaluation_id,
            evaluation_horizon=horizon,
            tenant_id=subject.tenant_id,
            business_condition_id=rule.business_condition_id,
            subject_type=SUBJECT_TYPE_SINGLE_RECORD,
            subject_identity=subject_identity,
            # CDD-048 §14, §20 (OQI-H2-I-R1 narrow Artifact Authorization
            # correction, disclosed in the OQI-H2-I final report): the one
            # governed finding-type-equivalent, set only for
            # dimension=REASONABLENESS rules. Zero behavior change for
            # every pre-H2 rule (dimension defaults to
            # LEGACY_UNCLASSIFIED_BUSINESS_RULE, so this stays None).
            violation_type=(
                ViolationType.CONTEXTUAL_PLAUSIBILITY_VIOLATION
                if rule.dimension is BusinessRulePurpose.REASONABLENESS
                else None
            ),
        )

        evaluation = BusinessRuleEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=subject.tenant_id,
            business_condition_id=rule.business_condition_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            subject_type=SUBJECT_TYPE_SINGLE_RECORD,
            subject_identity=subject_identity,
            source_object_id=subject.source_object_id,
            source_record_reference=subject.source_record_reference,
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_horizon=horizon,
            inputs=inputs,
            outcome=outcome,
            observations=observations,
            evaluated_at=self._clock(),
        )

        # CDD-041 §22: idempotent replay -- if this exact evaluation_id
        # already exists, the ledger insert is a no-op and the Finding
        # (already correctly mutated by the original application) MUST NOT
        # be mutated a second time.
        newly_inserted = self._repository.insert_evaluation_idempotent(evaluation)
        if newly_inserted and next_finding is not None:
            self._repository.upsert_finding(next_finding)
        return evaluation
