"""Authenticated, versioned protection for opaque runtime handoffs."""

import base64
import json
import os
from dataclasses import asdict

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.runtime.persistence.contracts import (
    ProtectedPayloadIntegrityError,
    ProtectionContext,
    UnsupportedProtectionVersionError,
)


class AuthenticatedHandoffProtector:
    VERSION = "1"

    def __init__(self, keys: dict[str, bytes], active_key_id: str) -> None:
        if active_key_id not in keys or any(
            len(value) not in {16, 24, 32} for value in keys.values()
        ):
            raise ValueError("A valid active AES key is required")
        self._keys = dict(keys)
        self._active = active_key_id

    def protect(self, plaintext: bytes, context: ProtectionContext) -> bytes:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._keys[self._active]).encrypt(nonce, plaintext, _aad(context))
        return json.dumps(
            {
                "version": self.VERSION,
                "key_id": self._active,
                "nonce": base64.urlsafe_b64encode(nonce).decode(),
                "ciphertext": base64.urlsafe_b64encode(ciphertext).decode(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    def recover(self, protected: bytes, context: ProtectionContext) -> bytes:
        try:
            envelope = json.loads(protected)
            if envelope.get("version") != self.VERSION:
                raise UnsupportedProtectionVersionError("Unsupported protection version")
            key_id = envelope["key_id"]
            if key_id not in self._keys:
                raise UnsupportedProtectionVersionError("Protection key is unavailable")
            nonce = base64.urlsafe_b64decode(envelope["nonce"])
            ciphertext = base64.urlsafe_b64decode(envelope["ciphertext"])
            if len(nonce) != 12 or not ciphertext:
                raise ProtectedPayloadIntegrityError("Protected payload is malformed")
            return AESGCM(self._keys[key_id]).decrypt(nonce, ciphertext, _aad(context))
        except UnsupportedProtectionVersionError:
            raise
        except (InvalidTag, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProtectedPayloadIntegrityError("Protected payload authentication failed") from exc


def _aad(context: ProtectionContext) -> bytes:
    return json.dumps(asdict(context), default=str, sort_keys=True, separators=(",", ":")).encode()
