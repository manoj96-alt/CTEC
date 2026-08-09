from dataclasses import replace
from uuid import uuid4

import pytest

from app.runtime.persistence.contracts import (
    ProtectedPayloadIntegrityError,
    ProtectionContext,
    UnsupportedProtectionVersionError,
)
from app.runtime.persistence.crypto import AuthenticatedHandoffProtector


def context() -> ProtectionContext:
    return ProtectionContext("tenant", uuid4(), uuid4(), "ERM", "OUTPUT", "CIM-001-v1.1")


def test_authenticated_payload_round_trip_and_context_binding() -> None:
    protector = AuthenticatedHandoffProtector({"current": b"a" * 32}, "current")
    binding = context()
    protected = protector.protect(b"opaque", binding)
    assert protector.recover(protected, binding) == b"opaque"
    with pytest.raises(ProtectedPayloadIntegrityError):
        protector.recover(protected, replace(binding, tenant_id="other"))


def test_key_rotation_reads_old_key_and_unknown_key_fails_closed() -> None:
    binding = context()
    old = AuthenticatedHandoffProtector({"old": b"o" * 32}, "old")
    protected = old.protect(b"opaque", binding)
    rotated = AuthenticatedHandoffProtector({"old": b"o" * 32, "new": b"n" * 32}, "new")
    assert rotated.recover(protected, binding) == b"opaque"
    with pytest.raises(UnsupportedProtectionVersionError):
        AuthenticatedHandoffProtector({"new": b"n" * 32}, "new").recover(protected, binding)


def test_malformed_payload_uses_safe_integrity_error() -> None:
    protector = AuthenticatedHandoffProtector({"current": b"a" * 32}, "current")
    with pytest.raises(ProtectedPayloadIntegrityError, match="authentication failed"):
        protector.recover(b"not-an-envelope", context())
