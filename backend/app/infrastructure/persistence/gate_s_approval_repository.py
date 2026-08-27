"""Repository for Gate S's governed human approval (CDD-036 §19-§22; Gate S
Artifact Authorization §4). `get_for_update` performs a `SELECT ... FOR
UPDATE` on the target approval row -- the row-level lock underpinning
CDD-036 §20's concurrency guarantee -- exactly mirroring
`OntologyChangeProposalRepository.update_status`'s own technique. Lookups
are not tenant-filtered at the SQL layer: `GateSApprovalService` performs
the tenant comparison explicitly, after fetch, so that a cross-tenant
attempt is reported as the CDD-036 §23 `APPROVAL_TENANT_MISMATCH` code
distinct from `APPROVAL_REQUEST_NOT_FOUND` -- a deliberate, frozen
governance choice, not an oversight. `insert_governed_note_and_consume` is
the sole method in this entire module (and, per CDD-036 §22, in the entire
codebase) that ever writes a `GateSGovernedNoteORM` row; it always also
marks the approval consumed, in the same call, so a note can never exist
without a durably-consumed approval behind it."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.gate_s.approval import ApprovalStatus, GateSApprovalRequest
from app.infrastructure.persistence.models.gate_s_approval import (
    GateSApprovalRequestORM,
    GateSGovernedNoteORM,
)


class GateSApprovalRepository(Protocol):
    def create(self, request: GateSApprovalRequest) -> None: ...

    def get_by_id(self, approval_id: UUID) -> GateSApprovalRequest | None: ...

    def get_for_update(self, approval_id: UUID) -> GateSApprovalRequest | None: ...

    def update_decision(self, request: GateSApprovalRequest) -> None: ...

    def insert_governed_note_and_consume(
        self,
        *,
        request: GateSApprovalRequest,
        governed_note_id: UUID,
        execution_id: UUID,
        created_by: str,
        now: datetime,
    ) -> None: ...


class GateSApprovalRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, request: GateSApprovalRequest) -> None:
        self.session.add(_to_orm(request))

    def get_by_id(self, approval_id: UUID) -> GateSApprovalRequest | None:
        model = self.session.get(GateSApprovalRequestORM, approval_id)
        if model is None:
            return None
        return _to_domain(model)

    def get_for_update(self, approval_id: UUID) -> GateSApprovalRequest | None:
        model = self.session.execute(
            select(GateSApprovalRequestORM)
            .where(GateSApprovalRequestORM.approval_id == approval_id)
            .with_for_update()
        ).scalar_one_or_none()
        if model is None:
            return None
        return _to_domain(model)

    def update_decision(self, request: GateSApprovalRequest) -> None:
        model = self.session.get(GateSApprovalRequestORM, request.approval_id)
        assert model is not None
        model.status = request.status.value
        model.decided_by = request.decided_by
        model.decided_on = request.decided_on
        model.rejection_reason = request.rejection_reason

    def insert_governed_note_and_consume(
        self,
        *,
        request: GateSApprovalRequest,
        governed_note_id: UUID,
        execution_id: UUID,
        created_by: str,
        now: datetime,
    ) -> None:
        self.session.add(
            GateSGovernedNoteORM(
                governed_note_id=governed_note_id,
                tenant_id=request.tenant_id,
                approval_id=request.approval_id,
                note_text=request.note_text,
                created_by=created_by,
                created_at=now,
            )
        )
        model = self.session.get(GateSApprovalRequestORM, request.approval_id)
        assert model is not None
        model.consumed_on = now
        model.consumed_execution_id = execution_id


def _to_orm(request: GateSApprovalRequest) -> GateSApprovalRequestORM:
    return GateSApprovalRequestORM(
        approval_id=request.approval_id,
        tenant_id=request.tenant_id,
        action_id=request.action_id,
        note_text=request.note_text,
        action_input_digest=request.action_input_digest,
        requested_by=request.requested_by,
        requested_on=request.requested_on,
        status=request.status.value,
        decided_by=request.decided_by,
        decided_on=request.decided_on,
        rejection_reason=request.rejection_reason,
        consumed_on=request.consumed_on,
        consumed_execution_id=request.consumed_execution_id,
    )


def _to_domain(model: GateSApprovalRequestORM) -> GateSApprovalRequest:
    return GateSApprovalRequest(
        approval_id=model.approval_id,
        tenant_id=model.tenant_id,
        action_id=model.action_id,
        note_text=model.note_text,
        action_input_digest=model.action_input_digest,
        requested_by=model.requested_by,
        requested_on=model.requested_on,
        status=ApprovalStatus(model.status),
        decided_by=model.decided_by,
        decided_on=model.decided_on,
        rejection_reason=model.rejection_reason,
        consumed_on=model.consumed_on,
        consumed_execution_id=model.consumed_execution_id,
    )
