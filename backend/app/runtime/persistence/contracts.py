"""CDD-012 recovery and retention contracts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

RECOVERY_ROLE = "EXECUTION_RECOVERY_OPERATOR"
RECOVERY_SCOPE = "execution:replay"
RETRY_SCOPE = "supplier-risk:retry"


@dataclass(frozen=True, slots=True)
class ProtectionContext:
    tenant_id: str
    logical_execution_id: UUID
    attempt_id: UUID
    stage_name: str
    direction: str
    contract_version: str


class ProtectedPayloadMissingError(LookupError):
    """A required protected payload is absent."""


class ProtectedPayloadIntegrityError(ValueError):
    """A protected payload failed authentication or binding validation."""


class UnsupportedProtectionVersionError(ValueError):
    """A protected payload uses an unavailable protection version or key."""


class HandoffProtector(Protocol):
    """Authenticated protection with context-bound, versioned recovery."""

    def protect(self, plaintext: bytes, context: ProtectionContext) -> bytes: ...
    def recover(self, protected: bytes, context: ProtectionContext) -> bytes: ...


@dataclass(frozen=True, slots=True)
class ReplayAuthorization:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    scopes: tuple[str, ...]
    authorization_reference: str
    reason: str
    correlation_id: UUID
    authorized_at: datetime

    def validate(self, original_tenant: str) -> None:
        if self.tenant_id != original_tenant:
            raise PermissionError("Replay tenant mismatch")
        if RECOVERY_ROLE not in self.roles or RECOVERY_SCOPE not in self.scopes:
            raise PermissionError("Replay authority is insufficient")
        if not self.authorization_reference or not self.reason.strip():
            raise PermissionError("Replay authority evidence is incomplete")
        if self.authorized_at.tzinfo is None:
            raise ValueError("Replay authorization timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RetryAuthorization:
    principal_id: str
    tenant_id: str
    scopes: tuple[str, ...]
    authorization_reference: str
    reason: str
    correlation_id: UUID
    authorized_at: datetime

    def validate(self, original_tenant: str) -> None:
        if self.tenant_id != original_tenant:
            raise PermissionError("Retry tenant mismatch")
        if RETRY_SCOPE not in self.scopes:
            raise PermissionError("Retry authority is insufficient")
        if not self.authorization_reference or not self.reason.strip():
            raise PermissionError("Retry authority evidence is incomplete")
        if self.authorized_at.tzinfo is None:
            raise ValueError("Retry authorization timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class AttemptProjection:
    execution_id: UUID
    logical_execution_id: UUID
    state: str
    admitted_at: datetime
    terminal_at: datetime | None
    revision: int


@dataclass(frozen=True, slots=True)
class StageProjection:
    stage_id: UUID
    stage_name: str
    stage_ordinal: int
    status: str
    started_at: datetime
    completed_at: datetime | None
    safe_failure_code: str | None
    produced_record_references: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ResultProjection:
    execution_id: UUID
    result_code: str | None
    result_value: str | None
    actionable: bool
    completed_at: datetime
    produced_record_references: tuple[UUID, ...]
