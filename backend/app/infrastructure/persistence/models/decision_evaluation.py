from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class DecisionEvaluationGroupORM(BaseEntity):
    """`decision_evaluations` -- Gate F F-I1 / CDD-015 §16 item 1.

    The stable identity of one governed decision evaluation whose result may
    require multiple persisted `DecisionEvaluationORM` records. Noncanonical
    runtime persistence, authorized directly by CDD-015 §16-17/§33 (not by
    RFC), on the same governance tier as `decision_evaluation_records`/
    `governance_evaluation_records` themselves. Carries its own direct
    `tenant_id` (unlike this table's children, which resolve tenant only
    indirectly). `logical_execution_id` is a plain, non-FK audit-trail
    reference -- see the migration docstring and CDD-015 §20 for why it is
    deliberately not a foreign key to `runtime_executions`.
    """

    __tablename__ = "decision_evaluations"
    __table_args__ = (Index("idx_decision_evaluations_tenant_id", "tenant_id"),)

    decision_evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    logical_execution_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DecisionEvaluationORM(BaseEntity):
    __tablename__ = "decision_evaluation_records"
    __table_args__ = (
        Index(
            "idx_decision_evaluation_currentness",
            "decision_identity_key",
            "effective_from",
            "produced_timestamp",
            "record_identifier",
        ),
        Index(
            "idx_decision_evaluation_policy_traceability",
            "governing_policy_reference",
            "policy_version",
        ),
        Index(
            "idx_decision_evaluation_records_decision_evaluation_id",
            "decision_evaluation_id",
        ),
    )

    record_identifier: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    knowledge_references: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    decision_recommendation: Mapped[str] = mapped_column(String(1000), nullable=False)
    evaluation_outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    decision_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    structured_reasons: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    narrative_explanation: Mapped[str] = mapped_column(String(4000), nullable=False)
    governing_policy_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    produced_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision_identity_key: Mapped[str] = mapped_column(String(64), nullable=False)
    business_context_reference: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    enterprise_constraint_references: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    policy_satisfied: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    decision_evaluation_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("decision_evaluations.decision_evaluation_id"), nullable=True
    )
