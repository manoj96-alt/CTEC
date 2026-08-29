"""ORM model for `business_rule_findings` -- the mutable current-state
projection for one governed business condition on one governed
`SINGLE_RECORD` subject (CDD-041 §14-§15, §24; Artifact Authorization §5).
Created by the `0022_oqi3_business_rule` migration (OQI3-I1); this file adds
the ORM mapping OQI3-I3 needs to read/write it -- schema-only until this
phase, per CDD-041 §33's decomposition."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class BusinessRuleFindingORM(BaseEntity):
    __tablename__ = "business_rule_findings"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "business_condition_id",
            "subject_type",
            "subject_identity",
            name="uq_business_rule_findings_subject",
        ),
        CheckConstraint(
            "(status = 'OPEN' AND resolution_basis IS NULL) OR "
            "(status = 'RESOLVED' AND resolution_basis IS NOT NULL)",
            name="ck_business_rule_findings_resolution_basis",
        ),
        Index("idx_business_rule_findings_tenant_id", "tenant_id"),
        Index("idx_business_rule_findings_status", "status"),
    )

    finding_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    business_condition_id: Mapped[str] = mapped_column(String(200), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_identity: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    resolution_basis: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latest_evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "business_rule_evaluations.evaluation_id",
            name="fk_business_rule_findings_latest_evaluation_id",
        ),
        nullable=False,
    )
    occurrence_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
