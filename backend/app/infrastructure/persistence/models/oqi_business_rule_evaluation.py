"""ORM models for `business_rule_evaluations` (the immutable Evaluation
ledger), `business_rule_evaluation_inputs` (the immutable per-evaluation
input snapshot), and `business_rule_evaluation_observations` (the immutable
per-evaluation deterministic quality facts) (CDD-041 §16-§19, §24; Artifact
Authorization §5). `evaluation_id` is deterministically application-supplied
-- see
`app.domain.oqi_business_rule.evaluation.derive_business_rule_evaluation_id`.

`business_rule_evaluation_observations` declares a chained composite foreign
key back to its own evaluation's input snapshot row (CDD-040 §49's chained-
FK provenance-integrity pattern, reused): this makes it structurally
impossible at the database level for an observation to claim an `input_role`
that was not genuinely part of that evaluation's own input frontier -- no
trigger required. Both tables and their constraints are created by the
`0022_oqi3_business_rule` migration (OQI3-I1); this file only adds the ORM
mapping OQI3-I2 needs to read/write them."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class BusinessRuleEvaluationORM(BaseEntity):
    __tablename__ = "business_rule_evaluations"

    __table_args__ = (Index("idx_business_rule_evaluations_tenant_id_orm", "tenant_id"),)

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    business_condition_id: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("business_rules.rule_id", name="fk_business_rule_evaluations_rule_id"),
        nullable=False,
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_object_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_objects.source_object_id",
            name="fk_business_rule_evaluations_source_object_id",
        ),
        nullable=False,
    )
    source_record_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    evaluation_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluation_horizon: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BusinessRuleEvaluationInputORM(BaseEntity):
    __tablename__ = "business_rule_evaluation_inputs"

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "business_rule_evaluations.evaluation_id",
            name="fk_business_rule_evaluation_inputs_evaluation_id",
        ),
        primary_key=True,
    )
    input_role: Mapped[str] = mapped_column(String(64), primary_key=True)
    field_value_evidence_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "field_value_evidence.field_value_evidence_id",
            name="fk_business_rule_evaluation_inputs_evidence_id",
        ),
        nullable=True,
    )


class BusinessRuleEvaluationObservationORM(BaseEntity):
    __tablename__ = "business_rule_evaluation_observations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["evaluation_id", "input_role"],
            [
                "business_rule_evaluation_inputs.evaluation_id",
                "business_rule_evaluation_inputs.input_role",
            ],
            name="fk_business_rule_evaluation_observations_input",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "business_rule_evaluations.evaluation_id",
            name="fk_business_rule_evaluation_observations_evaluation_id",
        ),
        primary_key=True,
    )
    clause_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    observation_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    input_role: Mapped[str] = mapped_column(String(64), primary_key=True)
