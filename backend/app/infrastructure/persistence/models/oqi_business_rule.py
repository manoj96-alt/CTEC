"""ORM models for `business_rules` and `business_rule_input_bindings`
(CDD-041 §24, Artifact Authorization §5). `rule_id` is deterministically
application-supplied -- see
`app.domain.oqi_business_rule.rule.derive_business_rule_id`. The partial
unique index enforces "exactly one ACTIVE version per
(tenant_id, business_condition_id)" at the database level, mirroring
`QualityRuleORM`'s own `uq_quality_rules_one_active_per_condition` /
`ComparisonSubjectCorrespondenceORM`'s own
`uq_comparison_subject_correspondences_one_active` pattern exactly."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class BusinessRuleORM(BaseEntity):
    __tablename__ = "business_rules"

    __table_args__ = (
        UniqueConstraint(
            "business_condition_id", "version", name="uq_business_rules_condition_version"
        ),
        Index("idx_business_rules_tenant_id", "tenant_id"),
        Index(
            "uq_business_rules_one_active_per_condition",
            "tenant_id",
            "business_condition_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    rule_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    business_condition_id: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_family: Mapped[str] = mapped_column(String(32), nullable=False)
    applicability: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    predicate: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BusinessRuleInputBindingORM(BaseEntity):
    __tablename__ = "business_rule_input_bindings"

    rule_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("business_rules.rule_id", name="fk_business_rule_input_bindings_rule_id"),
        primary_key=True,
    )
    input_role: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_fields.source_field_id",
            name="fk_business_rule_input_bindings_source_field_id",
        ),
        nullable=False,
    )
    required: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    expected_type: Mapped[str] = mapped_column(String(16), nullable=False)
