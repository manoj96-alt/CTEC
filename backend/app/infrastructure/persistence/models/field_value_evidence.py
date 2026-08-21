"""ORM model for `field_value_evidence` (CDD-022 §6, §15; Field-Value
Evidence Artifact Authorization). Global identity, deterministically
application-supplied (CDD-022 §6, §25) -- no `tenant_id`, no
`source_object_id`, no `source_system_id` column; tenant is resolved
transitively through `source_field_id` -> `source_objects.tenant_id`
(CDD-022 §7). No lifecycle/governance-status column -- this is an
immutable, append-only fact, not a governed-vocabulary entity."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class FieldValueEvidenceORM(BaseEntity):
    __tablename__ = "field_value_evidence"

    __table_args__ = (
        Index("idx_field_value_evidence_source_field_id", "source_field_id"),
        Index("idx_field_value_evidence_observed_at", "observed_at"),
        Index("idx_field_value_evidence_received_at", "received_at"),
    )

    field_value_evidence_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("source_fields.source_field_id", name="fk_field_value_evidence_source_field_id"),
        nullable=False,
    )
    source_record_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    observed_representation: Mapped[str] = mapped_column(String(1000), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
