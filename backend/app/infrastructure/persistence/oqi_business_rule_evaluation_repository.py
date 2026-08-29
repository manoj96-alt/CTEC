"""OQI3-I2 evaluation-ledger persistence: evidence selection (reusing OQI1's
proven "latest qualifying evidence" query exactly, CDD-039 §32) and atomic,
idempotent insertion of a `BusinessRuleEvaluation` together with its input
snapshot rows and observations (CDD-041 §16-§19, §21 steps 7-9, 13-16).

Deliberately does NOT expose `acquire_evaluation_authority`, `get_finding`,
or `upsert_finding` -- Finding-authority advisory locking (seed=3, CDD-041
§21 steps 1-6, 10, 17) and Finding lifecycle mutation belong exclusively to
OQI3-I3 (CDD-041 §33 decomposition). This repository's persistence methods
are safe building blocks for I3 to compose *inside* its lock; calling
`insert_evaluation_idempotent` on its own (as this module's own HISTORICAL
path and tests do) never claims CURRENT_STATE concurrency safety -- see the
OQI3-I2 report's honest concurrency-scope analysis."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.domain.oqi.evaluation import EvaluationMode
from app.domain.oqi_business_rule.evaluation import (
    BusinessRuleEvaluation,
    BusinessRuleEvaluationInputEntry,
    BusinessRuleEvaluationObservation,
    EvaluationOutcome,
    ObservationType,
    canonical_single_record_subject_identity,
    input_evidence_digest,
)
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_business_rule import BusinessRuleORM
from app.infrastructure.persistence.models.oqi_business_rule_evaluation import (
    BusinessRuleEvaluationInputORM,
    BusinessRuleEvaluationObservationORM,
    BusinessRuleEvaluationORM,
)
from app.infrastructure.persistence.models.source_field import SourceFieldORM


class OqiBusinessRuleEvaluationRepository(Protocol):
    def select_known_lineage(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> bool: ...

    def select_latest_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None: ...

    def insert_evaluation_idempotent(self, evaluation: BusinessRuleEvaluation) -> bool: ...

    def get_evaluation(self, evaluation_id: UUID) -> BusinessRuleEvaluation | None: ...


class OqiBusinessRuleEvidenceValueReader:
    """CDD-041 §10, §20: reads `FieldValueEvidence.observed_representation`
    (raw, unparsed) for exactly the evidence rows an already-selected input
    frontier references -- the only place OQI3-I2 touches evidence content,
    and it never mutates or reinterprets it (CDD-022 raw-evidence
    immutability, CDD-041 §27 OQI1/OQI2 firewalls)."""

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


class OqiBusinessRuleEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def select_known_lineage(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> bool:
        """CDD-041 §12/§6: is the single-record subject known to CTEC at
        all under the evaluation horizon -- at least one admitted,
        non-empty `FieldValueEvidence` observation for *any* `SourceField`
        belonging to `source_object_id`, carrying `source_record_reference`?
        Mirrors OQI1's `select_known_lineage_evidence_id` exactly (CDD-039
        §12), generalized to a boolean since OQI3 has no single target
        field."""
        return (
            self.session.execute(
                select(FieldValueEvidenceORM.field_value_evidence_id)
                .join(
                    SourceFieldORM,
                    SourceFieldORM.source_field_id == FieldValueEvidenceORM.source_field_id,
                )
                .where(
                    SourceFieldORM.source_object_id == source_object_id,
                    FieldValueEvidenceORM.source_record_reference == source_record_reference,
                    FieldValueEvidenceORM.observed_representation != "",
                    FieldValueEvidenceORM.received_at <= evaluation_horizon,
                )
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )

    def select_latest_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None:
        """CDD-041 §16: the single latest qualifying evidence row for one
        bound input -- greatest `observed_at`, ties broken by greatest
        `received_at`. Byte-identical selection rule to OQI1's
        `select_latest_target_field_value` (CDD-039 §32) -- OQI3 does not
        invent a different "current value" rule."""
        row = self.session.execute(
            select(
                FieldValueEvidenceORM.field_value_evidence_id,
                FieldValueEvidenceORM.observed_representation,
            )
            .where(
                FieldValueEvidenceORM.source_field_id == source_field_id,
                FieldValueEvidenceORM.source_record_reference == source_record_reference,
                FieldValueEvidenceORM.observed_representation != "",
                FieldValueEvidenceORM.received_at <= evaluation_horizon,
            )
            .order_by(
                FieldValueEvidenceORM.observed_at.desc(), FieldValueEvidenceORM.received_at.desc()
            )
            .limit(1)
        ).first()
        return None if row is None else (row[0], row[1])

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
