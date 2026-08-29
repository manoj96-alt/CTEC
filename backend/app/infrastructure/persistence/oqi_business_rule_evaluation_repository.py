"""OQI3-I2 evaluation-ledger persistence: evidence selection and atomic,
idempotent insertion of a `BusinessRuleEvaluation` together with its input
snapshot rows and observations (CDD-041 §16-§19, §21 steps 7-9, 13-16).

CDD-041 Atomic Multi-Field Evidence Frontier Amendment (OQI3-I2-R3):
`select_evidence_frontier` replaces the prior `select_known_lineage` +
N-sequential-`select_latest_field_value` algorithm with exactly one
PostgreSQL statement establishing every mutable evidence-state fact
(subject-known, and the latest qualifying evidence for every bound role)
from one READ COMMITTED statement snapshot -- closing the evaluator-vs-
evidence-writer coherence gap discovered by OQI3-I3/OQI3-R3. This changes
snapshot-acquisition mechanics only: the OQI1-derived latest-evidence
ordering/filter predicates, `EMPTY` semantics, and `NOT_EVALUABLE`/
unknown-subject semantics are all reproduced verbatim.

CDD-041 §21 steps 1-6, 10, 17 (OQI3-I3): `acquire_evaluation_authority` reuses
OQI1/OQI2's exact mechanism -- `SELECT pg_advisory_xact_lock(hashtextextended
(:identity, :seed))` -- with `OQI_BUSINESS_RULE_ADVISORY_LOCK_SEED = 3`,
distinct from `_lock_replay_identity`'s seed 0, OQI1's seed 1, and OQI2's
seed 2 (CDD-041 §21). `get_finding`/`upsert_finding` are the Finding-lifecycle
read/write primitives the application service composes *inside* that lock.
Calling `insert_evaluation_idempotent` standalone (as this module's own
HISTORICAL path and tests do) never claims CURRENT_STATE Finding-lifecycle
safety by itself -- see the OQI3-I2/I2-R3 reports' honest concurrency-scope
analysis; only the full CDD-041 §21 sequence (lock before evidence selection,
held through Finding mutation and commit) provides that guarantee."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import (
    String,
    Uuid,
    and_,
    column,
    func,
    literal_column,
    or_,
    select,
    text,
    true,
    values,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.domain.oqi.evaluation import EvaluationMode
from app.domain.oqi.finding import QualityFindingStatus
from app.domain.oqi_business_rule.evaluation import (
    BusinessRuleEvaluation,
    BusinessRuleEvaluationInputEntry,
    BusinessRuleEvaluationObservation,
    EvaluationOutcome,
    ObservationType,
    canonical_single_record_subject_identity,
    input_evidence_digest,
)
from app.domain.oqi_business_rule.finding import BusinessRuleFinding, ResolutionBasis
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_business_rule import BusinessRuleORM
from app.infrastructure.persistence.models.oqi_business_rule_evaluation import (
    BusinessRuleEvaluationInputORM,
    BusinessRuleEvaluationObservationORM,
    BusinessRuleEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.source_field import SourceFieldORM

#: CDD-041 §21: distinct from `_lock_replay_identity`'s seed 0, OQI1's own
#: seed 1, and OQI2's own seed 2, so the four otherwise-unrelated subsystems
#: can never coincidentally serialize against each other.
OQI_BUSINESS_RULE_ADVISORY_LOCK_SEED = 3


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

    def get_evaluation(self, evaluation_id: UUID) -> BusinessRuleEvaluation | None: ...

    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_finding(self, finding_id: UUID) -> BusinessRuleFinding | None: ...

    def upsert_finding(self, finding: BusinessRuleFinding) -> None: ...


class OqiBusinessRuleEvidenceValueReader:
    """CDD-041 §10, §20: reads `FieldValueEvidence.observed_representation`
    (raw, unparsed) for exactly the evidence rows an already-selected input
    frontier references -- the only place OQI3-I2 touches evidence content,
    and it never mutates or reinterprets it (CDD-022 raw-evidence
    immutability, CDD-041 §27 OQI1/OQI2 firewalls). Reading it in a separate
    statement after the atomic frontier is safe (not a lazy-load leak)
    because `field_value_evidence` is insert-only -- a row's content
    cannot change between the coherent-snapshot statement and this read
    (CDD-041 Atomic Multi-Field Evidence Frontier Amendment §4.3)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def read_values(self, inputs: tuple[BusinessRuleEvaluationInputEntry, ...]) -> dict[str, str]:
        evidence_ids = {
            entry.evidence_id: entry.input_role for entry in inputs if entry.evidence_id
        }
        if not evidence_ids:
            return {}
        rows = self.session.execute(
            select(
                FieldValueEvidenceORM.field_value_evidence_id,
                FieldValueEvidenceORM.observed_representation,
            ).where(FieldValueEvidenceORM.field_value_evidence_id.in_(evidence_ids.keys()))
        ).all()
        return {evidence_ids[row[0]]: row[1] for row in rows}


def _build_evidence_frontier_statement(
    *,
    source_object_id: UUID,
    source_record_reference: str,
    evaluation_horizon: datetime,
    bindings: Sequence[tuple[str, UUID]],
    _test_only_delay_seconds: float | None = None,
) -> Select[Any]:
    """CDD-041 Atomic Multi-Field Evidence Frontier Amendment §4 (exact,
    binding query shape): one top-level PostgreSQL statement returning
    `(subject_known, input_role, field_value_evidence_id_or_NULL)` for
    every bound role. The `subject_known` correlated `EXISTS` and the
    per-role `ranked` window-function CTE are evaluated by PostgreSQL as
    one query tree and therefore share one statement snapshot -- this is
    what closes both the known-lineage race and the per-field race
    simultaneously (Amendment §4, §11).

    Preserves verbatim: the non-empty-representation filter, the
    `received_at <= evaluation_horizon` boundary, and the
    `observed_at DESC, received_at DESC` latest-evidence ordering --
    byte-identical to OQI1's own `select_latest_target_field_value`
    predicates (CDD-039 §32). No third tiebreaker is introduced for
    exact-timestamp ties -- that inherited ambiguity is OQI-P3-006
    (Amendment §5), not fixed here.

    `_test_only_delay_seconds`, when set, adds a `pg_sleep`-gated CTE to
    the statement's FROM clause so a test can force the statement to
    remain in-flight for a controlled window while a concurrent writer
    commits -- proving the one-statement-one-snapshot property against
    real PostgreSQL rather than asserting it. It has zero effect on
    production behavior; no production caller ever passes it."""
    fve = FieldValueEvidenceORM.__table__
    sf = SourceFieldORM.__table__

    bound_roles = values(
        column("input_role", String),
        column("source_field_id", Uuid()),
        name="bound_roles",
    ).data(list(bindings))

    ranked = (
        select(
            bound_roles.c.input_role,
            fve.c.field_value_evidence_id,
            func.row_number()
            .over(
                partition_by=bound_roles.c.input_role,
                order_by=(fve.c.observed_at.desc(), fve.c.received_at.desc()),
            )
            .label("rn"),
        )
        .select_from(
            bound_roles.outerjoin(
                fve,
                and_(
                    fve.c.source_field_id == bound_roles.c.source_field_id,
                    fve.c.source_record_reference == source_record_reference,
                    fve.c.observed_representation != "",
                    fve.c.received_at <= evaluation_horizon,
                ),
            )
        )
        .cte("ranked")
    )

    subject_known_expr = (
        select(literal_column("1"))
        .select_from(fve.join(sf, sf.c.source_field_id == fve.c.source_field_id))
        .where(
            sf.c.source_object_id == source_object_id,
            fve.c.source_record_reference == source_record_reference,
            fve.c.observed_representation != "",
            fve.c.received_at <= evaluation_horizon,
        )
        .exists()
    )

    from_clause = bound_roles.outerjoin(
        ranked,
        and_(
            ranked.c.input_role == bound_roles.c.input_role,
            or_(ranked.c.rn == 1, ranked.c.rn.is_(None)),
        ),
    )
    if _test_only_delay_seconds is not None:
        delay_gate = select(func.pg_sleep(_test_only_delay_seconds).label("_ignore")).cte(
            "delay_gate"
        )
        from_clause = from_clause.join(delay_gate, true())

    return select(
        subject_known_expr.label("subject_known"),
        bound_roles.c.input_role,
        ranked.c.field_value_evidence_id,
    ).select_from(from_clause)


class OqiBusinessRuleEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        """CDD-041 §21 step 5: transaction-scoped -- releases automatically
        on COMMIT, ROLLBACK, or connection loss. Never `pg_advisory_lock`
        (session-scoped)."""
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_BUSINESS_RULE_ADVISORY_LOCK_SEED},
        )

    def get_finding(self, finding_id: UUID) -> BusinessRuleFinding | None:
        model = self.session.get(BusinessRuleFindingORM, finding_id)
        return None if model is None else _finding_to_domain(model)

    def upsert_finding(self, finding: BusinessRuleFinding) -> None:
        model = self.session.get(BusinessRuleFindingORM, finding.finding_id)
        if model is None:
            self.session.add(_finding_to_orm(finding))
            return
        model.status = finding.status.value
        model.resolution_basis = (
            None if finding.resolution_basis is None else finding.resolution_basis.value
        )
        model.latest_evaluation_id = finding.latest_evaluation_id
        model.occurrence_count = finding.occurrence_count
        model.reopen_count = finding.reopen_count
        model.state_revision = finding.state_revision
        model.first_seen_at = finding.first_seen_at
        model.last_seen_at = finding.last_seen_at

    def select_evidence_frontier(
        self,
        *,
        source_object_id: UUID,
        source_record_reference: str,
        evaluation_horizon: datetime,
        bindings: Sequence[tuple[str, UUID]],
    ) -> tuple[bool, dict[str, UUID | None]]:
        """CDD-041 Atomic Multi-Field Evidence Frontier Amendment §4/§9
        (OQI3-I2-R3). Returns `(subject_known, {input_role: evidence_id})`
        -- every bound role is present in the mapping (value `None` is the
        frozen `EMPTY` sentinel) whenever `subject_known` is True. When
        `subject_known` is False the mapping is empty and the caller MUST
        treat this as `NOT_EVALUABLE` (CDD-041 §6/§13) -- never manufacture
        `EMPTY` entries for an unknown subject."""
        stmt = _build_evidence_frontier_statement(
            source_object_id=source_object_id,
            source_record_reference=source_record_reference,
            evaluation_horizon=evaluation_horizon,
            bindings=bindings,
        )
        rows = self.session.execute(stmt).all()
        if not rows or not bool(rows[0][0]):
            return False, {}
        return True, {row[1]: row[2] for row in rows}

    def insert_evaluation_idempotent(self, evaluation: BusinessRuleEvaluation) -> bool:
        """CDD-041 §5.2 (OQI3-I2-R), §16, §22: returns True if a new
        immutable ledger row (and its input snapshot + observation rows)
        were inserted; False if `evaluation.evaluation_id` already
        existed -- a byte-identical logical replay is a genuine no-op,
        never a duplicate row and never an error.

        Parent-gated conflict ownership (CDD-041 §5.2, OQI3-G2): the parent
        `business_rule_evaluations` row is inserted via `ON CONFLICT
        (evaluation_id) DO NOTHING RETURNING evaluation_id`, atomically at
        the database level -- a plain check-then-insert (`session.get` then
        `session.add`) cannot close this race, since two concurrent
        transactions under READ COMMITTED can both observe "no existing
        row" before either commits. Only the transaction that receives a
        returned `evaluation_id` (this transaction won the race, or no
        prior row existed) proceeds to insert children. A transaction that
        loses the conflict (`RETURNING` yields no row) returns `False`
        immediately and MUST NOT attempt to insert any child row -- doing
        so would either violate the children's own natural-key constraints
        or silently duplicate an already-complete child set. This is the
        exact reason `ON CONFLICT DO NOTHING` is applied ONLY to the parent
        table, never independently to each child table (CDD-041 §5.2
        explicitly rejects that unconditional variant as unsafe): gating
        ownership at the single authoritative natural-key check, before any
        child table is touched, is what makes the pattern safe across all
        four tables without per-child conflict handling.

        `parent_row` is constructed via the ORM class exactly as before
        (the single authorized construction site, `test_runtime_
        architecture.py`'s firewall assertion) purely as a typed value
        holder -- its mapped columns are read back to build the Core
        `INSERT ... ON CONFLICT` statement, since `Session.add()` cannot
        express `ON CONFLICT DO NOTHING RETURNING`."""
        parent_row = BusinessRuleEvaluationORM(
            evaluation_id=evaluation.evaluation_id,
            tenant_id=evaluation.tenant_id,
            business_condition_id=evaluation.business_condition_id,
            rule_id=evaluation.rule_id,
            subject_type=evaluation.subject_type,
            source_object_id=evaluation.source_object_id,
            source_record_reference=evaluation.source_record_reference,
            evaluation_mode=evaluation.evaluation_mode.value,
            evaluation_horizon=evaluation.evaluation_horizon,
            input_evidence_digest=_input_evidence_digest_of(evaluation),
            outcome=evaluation.outcome.value,
            evaluated_at=evaluation.evaluated_at,
        )
        parent_values = {
            column.name: getattr(parent_row, column.name)
            for column in BusinessRuleEvaluationORM.__table__.columns
        }
        insert_stmt = (
            pg_insert(BusinessRuleEvaluationORM)
            .values(**parent_values)
            .on_conflict_do_nothing(index_elements=["evaluation_id"])
            .returning(BusinessRuleEvaluationORM.evaluation_id)
        )
        won_ownership = self.session.execute(insert_stmt).first() is not None
        if not won_ownership:
            return False

        # Staged flushes, not one combined flush: without an ORM
        # `relationship()` between these mapped classes (deliberately --
        # this repository is a thin, explicit persistence layer, mirroring
        # OQI1/OQI2's own style), a single `flush()` covering all three
        # tables does not reliably order the parent INSERT ahead of its
        # FK-dependent children, tripping the FK constraint. Each stage's
        # rows are only ever added after their FK target is already
        # durable within this same transaction -- still one atomic
        # transaction end-to-end (CDD-041 §21 step 16): the caller's
        # `commit()`/absence of one governs all-or-nothing persistence.
        self.session.flush()
        for entry in evaluation.inputs:
            self.session.add(
                BusinessRuleEvaluationInputORM(
                    evaluation_id=evaluation.evaluation_id,
                    input_role=entry.input_role,
                    field_value_evidence_id=entry.evidence_id,
                )
            )
        self.session.flush()
        for observation in evaluation.observations:
            self.session.add(
                BusinessRuleEvaluationObservationORM(
                    evaluation_id=evaluation.evaluation_id,
                    clause_id=observation.clause_id,
                    observation_type=observation.observation_type.value,
                    input_role=observation.input_role,
                )
            )
        self.session.flush()
        return True

    def get_evaluation(self, evaluation_id: UUID) -> BusinessRuleEvaluation | None:
        model = self.session.get(BusinessRuleEvaluationORM, evaluation_id)
        if model is None:
            return None
        input_rows = (
            self.session.execute(
                select(BusinessRuleEvaluationInputORM).where(
                    BusinessRuleEvaluationInputORM.evaluation_id == evaluation_id
                )
            )
            .scalars()
            .all()
        )
        observation_rows = (
            self.session.execute(
                select(BusinessRuleEvaluationObservationORM).where(
                    BusinessRuleEvaluationObservationORM.evaluation_id == evaluation_id
                )
            )
            .scalars()
            .all()
        )
        rule_model = self.session.get(BusinessRuleORM, model.rule_id)
        assert rule_model is not None  # FK-enforced; a rule is never deleted once referenced
        return _to_domain(model, rule_model.version, input_rows, observation_rows)


def _finding_to_orm(finding: BusinessRuleFinding) -> BusinessRuleFindingORM:
    return BusinessRuleFindingORM(
        finding_id=finding.finding_id,
        tenant_id=finding.tenant_id,
        business_condition_id=finding.business_condition_id,
        subject_type=finding.subject_type,
        subject_identity=finding.subject_identity,
        status=finding.status.value,
        resolution_basis=(
            None if finding.resolution_basis is None else finding.resolution_basis.value
        ),
        latest_evaluation_id=finding.latest_evaluation_id,
        occurrence_count=finding.occurrence_count,
        reopen_count=finding.reopen_count,
        state_revision=finding.state_revision,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
    )


def _finding_to_domain(model: BusinessRuleFindingORM) -> BusinessRuleFinding:
    return BusinessRuleFinding(
        finding_id=model.finding_id,
        tenant_id=model.tenant_id,
        business_condition_id=model.business_condition_id,
        subject_type=model.subject_type,
        subject_identity=model.subject_identity,
        status=QualityFindingStatus(model.status),
        resolution_basis=(
            None if model.resolution_basis is None else ResolutionBasis(model.resolution_basis)
        ),
        latest_evaluation_id=model.latest_evaluation_id,
        occurrence_count=model.occurrence_count,
        reopen_count=model.reopen_count,
        state_revision=model.state_revision,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
    )


def _input_evidence_digest_of(evaluation: BusinessRuleEvaluation) -> str:
    return input_evidence_digest(evaluation.inputs)


def _to_domain(
    model: BusinessRuleEvaluationORM,
    rule_version: int,
    input_rows: Sequence[BusinessRuleEvaluationInputORM],
    observation_rows: Sequence[BusinessRuleEvaluationObservationORM],
) -> BusinessRuleEvaluation:
    """Reconstructs a read-side `BusinessRuleEvaluation` via the normal,
    fully-validating constructor (CDD-041 §3.1/§3.2, OQI3-I2-R): with
    `source_object_id` now persisted directly on `business_rule_evaluations`
    (the OQI3-G2/I2-R provenance correction), the true canonical
    `subject_identity` is recomputed from `source_object_id` +
    `source_record_reference` exactly as at write time, and
    `evaluation_id`/`subject_identity` are both re-derived and verified by
    `__post_init__` -- no bypass, no placeholder, no dependency on
    non-empty evidence-link presence or on mutable current `SourceField`
    state (subject provenance comes entirely from this row's own
    `source_object_id`/`source_record_reference` columns)."""
    return BusinessRuleEvaluation(
        evaluation_id=model.evaluation_id,
        tenant_id=model.tenant_id,
        business_condition_id=model.business_condition_id,
        rule_id=model.rule_id,
        rule_version=rule_version,
        subject_type=model.subject_type,
        subject_identity=canonical_single_record_subject_identity(
            source_object_id=model.source_object_id,
            source_record_reference=model.source_record_reference,
        ),
        source_object_id=model.source_object_id,
        source_record_reference=model.source_record_reference,
        evaluation_mode=EvaluationMode(model.evaluation_mode),
        evaluation_horizon=model.evaluation_horizon,
        inputs=tuple(
            BusinessRuleEvaluationInputEntry(
                input_role=row.input_role, evidence_id=row.field_value_evidence_id
            )
            for row in input_rows
        ),
        outcome=EvaluationOutcome(model.outcome),
        observations=tuple(
            BusinessRuleEvaluationObservation(
                clause_id=row.clause_id,
                observation_type=ObservationType(row.observation_type),
                input_role=row.input_role,
            )
            for row in observation_rows
        ),
        evaluated_at=model.evaluated_at,
    )
