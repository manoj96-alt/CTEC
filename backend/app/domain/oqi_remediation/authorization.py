"""OQI5-I1 `RemediationInstruction` + `RemediationAuthorization` (CDD-043
Sec13-Sec15). `RemediationAuthorization` is OQI5's own governed
human-approval object -- structurally independent from Gate S's
`GateSApprovalRequest` (CDD-036 Sec14/Sec37/Sec38 close that domain class
to a second `action_id`; this is the separate, explicit Product Owner
architecture decision CDD-036 itself anticipated -- CDD-043 Sec9). It
reuses Gate S's exact digest/TOCTOU/one-time-consumption *pattern*
verbatim (`compute_payload_digest` mirrors `compute_action_digest`'s
canonical-JSON-then-SHA-256 technique exactly), never its class or table.

`compute_payload_digest` deliberately excludes `proposed_value` as its own
digest input: the value is already implied by `candidate_id`, so the
digest cannot be satisfied by a model or caller substituting a different
string for the same candidate reference (CDD-043 Sec13's stated
rationale) -- there is no field in this payload a model's free text could
ever flow into."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200
_MAX_REJECTION_REASON_LENGTH = 1000


class RemediationActionType(StrEnum):
    """CDD-043 Sec13: closed to exactly one v1 value. CREATE/DELETE and
    multi-field atomic actions are explicitly excluded (OQI5-DR Sec136-138)."""

    UPDATE_FIELD = "UPDATE_FIELD"


class RemediationAuthorizationStatus(StrEnum):
    """CDD-043 Sec14: closed, exactly these three, mirroring CDD-036
    Sec15's `ApprovalStatus` shape exactly (max 8 chars, `String(16)` safe)."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def compute_payload_digest(
    *,
    tenant_id: str,
    finding_id: UUID,
    finding_state_revision: int,
    case_id: UUID,
    candidate_id: UUID,
    target_source_object_id: UUID,
    target_source_field_id: UUID,
    action_type: RemediationActionType,
) -> str:
    """CDD-043 Sec13: a deterministic SHA-256 digest over the canonical
    JSON representation of the exact remediation payload, including
    `finding_state_revision` -- the single field that makes the staleness
    contract (Sec15) work with zero new machinery: any Finding-revision
    change before execution changes this digest and fails closed at
    recomputation, exactly as Gate S's `compute_action_digest` already
    does for its own action shape."""
    canonical = json.dumps(
        {
            "tenant_id": tenant_id,
            "finding_id": str(finding_id),
            "finding_state_revision": finding_state_revision,
            "case_id": str(case_id),
            "candidate_id": str(candidate_id),
            "target_source_object_id": str(target_source_object_id),
            "target_source_field_id": str(target_source_field_id),
            "action_type": action_type.value,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RemediationInstruction:
    instruction_id: UUID
    tenant_id: str
    finding_id: UUID
    finding_state_revision: int
    case_id: UUID
    candidate_id: UUID
    target_source_object_id: UUID
    target_source_field_id: UUID
    action_type: RemediationActionType
    payload_digest: str
    agent_recommendation_id: UUID | None
    created_by: str
    created_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.instruction_id, UUID):
            raise ValidationException("instruction_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id.strip()) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-blank bounded text")
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if (
            not isinstance(self.finding_state_revision, int)
            or isinstance(self.finding_state_revision, bool)
            or self.finding_state_revision < 1
        ):
            raise ValidationException("finding_state_revision must be a positive integer")
        if not isinstance(self.case_id, UUID):
            raise ValidationException("case_id must be a UUID")
        if not isinstance(self.candidate_id, UUID):
            raise ValidationException("candidate_id must be a UUID")
        if not isinstance(self.target_source_object_id, UUID):
            raise ValidationException("target_source_object_id must be a UUID")
        if not isinstance(self.target_source_field_id, UUID):
            raise ValidationException("target_source_field_id must be a UUID")
        if not isinstance(self.action_type, RemediationActionType):
            raise ValidationException("action_type must be a RemediationActionType")
        expected_digest = compute_payload_digest(
            tenant_id=self.tenant_id,
            finding_id=self.finding_id,
            finding_state_revision=self.finding_state_revision,
            case_id=self.case_id,
            candidate_id=self.candidate_id,
            target_source_object_id=self.target_source_object_id,
            target_source_field_id=self.target_source_field_id,
            action_type=self.action_type,
        )
        if self.payload_digest != expected_digest:
            raise ValidationException(
                "payload_digest does not match the instruction's own payload fields"
            )
        if self.agent_recommendation_id is not None and not isinstance(
            self.agent_recommendation_id, UUID
        ):
            raise ValidationException("agent_recommendation_id must be None or a UUID")
        if not isinstance(self.created_by, str) or not self.created_by.strip():
            raise ValidationException("created_by must be non-blank text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


@dataclass(frozen=True, slots=True)
class RemediationAuthorization:
    authorization_id: UUID
    tenant_id: str
    instruction_id: UUID
    payload_digest: str
    requested_by: str
    requested_on: datetime
    status: RemediationAuthorizationStatus
    decided_by: str | None = None
    decided_on: datetime | None = None
    rejection_reason: str | None = None
    consumed_on: datetime | None = None
    consumed_execution_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.authorization_id, UUID):
            raise ValidationException("authorization_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.instruction_id, UUID):
            raise ValidationException("instruction_id must be a UUID")
        if not isinstance(self.payload_digest, str) or len(self.payload_digest) != 64:
            raise ValidationException("payload_digest must be a 64-character SHA-256 hex digest")
        if not isinstance(self.status, RemediationAuthorizationStatus):
            raise ValidationException("status must be a RemediationAuthorizationStatus")
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
        if self.rejection_reason is not None:
            if not isinstance(self.rejection_reason, str):
                raise ValidationException("rejection_reason must be a string")
            if len(self.rejection_reason) > _MAX_REJECTION_REASON_LENGTH:
                raise ValidationException(
                    f"rejection_reason must not exceed {_MAX_REJECTION_REASON_LENGTH} characters"
                )
        for label, timestamp in (
            ("requested_on", self.requested_on),
            ("decided_on", self.decided_on),
            ("consumed_on", self.consumed_on),
        ):
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")
        if self.requested_on is None:
            raise ValidationException("requested_on is required")
