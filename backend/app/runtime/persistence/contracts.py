"""CDD-012 recovery and retention contracts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

RECOVERY_ROLE = "EXECUTION_RECOVERY_OPERATOR"
RECOVERY_SCOPE = "execution:replay"


class HandoffProtector(Protocol):
    """Injected platform control; implementations must encrypt before persistence."""

    def protect(self, plaintext: bytes) -> bytes: ...


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
