"""ORM models for Gate S's governed human approval (CDD-036 §19). Two
tables: `gate_s_approval_requests` (the approval workflow record) and
`gate_s_governed_notes` (the append-only consequential-action ledger,
written exclusively by `GateSApprovalService.execute()` -- CDD-036 §21-§22).
`requested_by`/`decided_by`/`created_by` are plain strings with no FK,
following `OntologyChangeProposalORM`'s own provenance-field convention."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class GateSApprovalRequestORM(BaseEntity):
    __tablename__ = "gate_s_approval_requests"

    __table_args__ = (
        Index("idx_gate_s_approval_requests_tenant_id", "tenant_id"),
        Index("idx_gate_s_approval_requests_status", "status"),
        Index("idx_gate_s_approval_requests_requested_by", "requested_by"),
    )

    approval_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    action_id: Mapped[str] = mapped_column(String(200), nullable=False)
    note_text: Mapped[str] = mapped_column(String(500), nullable=False)
    action_input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decided_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    consumed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_execution_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class GateSGovernedNoteORM(BaseEntity):
    __tablename__ = "gate_s_governed_notes"

    __table_args__ = (Index("idx_gate_s_governed_notes_tenant_id", "tenant_id"),)

    governed_note_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    approval_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "gate_s_approval_requests.approval_id",
            name="fk_gate_s_governed_notes_approval_id",
        ),
        nullable=False,
    )
    note_text: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
