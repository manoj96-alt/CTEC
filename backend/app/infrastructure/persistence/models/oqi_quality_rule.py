"""ORM model for `quality_rules` (CDD-039 §18, §39; OQI1 Artifact
Authorization §4). `rule_id` is deterministically application-supplied
(never server-generated) -- see
`app.domain.oqi.quality_rule.derive_quality_rule_id`. The partial unique
index enforces "exactly one ACTIVE version per quality_condition_id" at the
database level (CDD-039 §18, §21)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class QualityRuleORM(BaseEntity):
    __tablename__ = "quality_rules"

    __table_args__ = (
        UniqueConstraint(
            "quality_condition_id", "version", name="uq_quality_rules_condition_version"
        ),
        Index(
            "uq_quality_rules_one_active_per_condition",
            "quality_condition_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    rule_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    quality_condition_id: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    dimension: Mapped[str] = mapped_column(String(16), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    validity_primitive: Mapped[str | None] = mapped_column(String(32), nullable=True)
    information_element_requirement_id: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_parameters: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
