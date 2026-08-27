"""Domain model for Gate S's governed human approval (CDD-036 §4, §14-§18).
`GateSApprovalRequest` is a frozen, immutable-transition domain object,
following `OntologyChangeProposal`'s own shape (plain-string actor
provenance fields, never FK -- CDD-036 §8) but adding the invariants Gate M
never needed: tenant binding, an immutable action digest, and one-time
consumption tracking. `compute_action_digest` is the sole mechanism
preventing "approve A, mutate to B, execute B" (CDD-036 §16-§17)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

ACTION_ID = "gate-s-governed-note-write"
_MAX_NOTE_TEXT_LENGTH = 500
_MAX_REJECTION_REASON_LENGTH = 1000


class ApprovalStatus(StrEnum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


def compute_action_digest(*, action_id: str, note_text: str) -> str:
    """CDD-036 §16: a deterministic SHA-256 digest over the canonical JSON
    representation of the exact action being proposed. Recomputed at
    execute() and compared to the stored digest (§17) -- a mismatch means
    the action changed after approval and must fail closed."""
    canonical = json.dumps(
        {"action_id": action_id, "note_text": note_text}, sort_keys=True, separators=(",", ":")
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class GateSApprovalRequest:
    approval_id: UUID
    tenant_id: str
    action_id: str
    note_text: str
    action_input_digest: str
    requested_by: str
    requested_on: datetime
    status: ApprovalStatus
    decided_by: str | None = None
    decided_on: datetime | None = None
    rejection_reason: str | None = None
    consumed_on: datetime | None = None
    consumed_execution_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ApprovalStatus):
            raise ValidationException("Status must be an ApprovalStatus")
        if self.action_id != ACTION_ID:
            raise ValidationException(f"Unknown action_id: {self.action_id!r}")
        if not isinstance(self.note_text, str) or not (
            1 <= len(self.note_text) <= _MAX_NOTE_TEXT_LENGTH
        ):
            raise ValidationException(
                f"note_text must be a string of length 1..{_MAX_NOTE_TEXT_LENGTH}"
            )
        if self.action_input_digest != compute_action_digest(
            action_id=self.action_id, note_text=self.note_text
        ):
            raise ValidationException("action_input_digest does not match note_text/action_id")

        for field_name, actor_value in (
            ("requested_by", self.requested_by),
            ("decided_by", self.decided_by),
        ):
            if actor_value is not None and not isinstance(actor_value, str):
                raise ValidationException(f"{field_name} must be a plain string")
            if isinstance(actor_value, str) and not actor_value.strip():
                raise ValidationException(f"{field_name} must not be blank")
        if not self.requested_by:
            raise ValidationException("requested_by is required")

        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id is required")

        if self.rejection_reason is not None:
            if not isinstance(self.rejection_reason, str):
                raise ValidationException("rejection_reason must be a string")
            if len(self.rejection_reason) > _MAX_REJECTION_REASON_LENGTH:
                raise ValidationException(
                    f"rejection_reason must not exceed {_MAX_REJECTION_REASON_LENGTH} characters"
                )

        for field_name, timestamp in (
            ("requested_on", self.requested_on),
            ("decided_on", self.decided_on),
            ("consumed_on", self.consumed_on),
        ):
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValidationException(f"{field_name} must include a timezone")
        if self.requested_on is None:
            raise ValidationException("requested_on is required")
