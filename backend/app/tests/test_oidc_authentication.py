from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.api.supplier_risk.authentication import AuthenticationError, OidcJwtVerifier
from app.core.config import Settings


class _Key:
    def __init__(self, key: object) -> None:
        self.key = key


class _Client:
    def __init__(self, key: object) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str) -> _Key:
        del token
        return _Key(self.key)


def _verifier() -> tuple[OidcJwtVerifier, object]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(
        oidc_issuer="https://issuer.example/",
        oidc_audience="ctec",
        oidc_jwks_url="https://issuer.example/jwks",
    )
    verifier = OidcJwtVerifier(settings)
    verifier._client = _Client(private.public_key())  # type: ignore[assignment]
    return verifier, private


def _token(key: Any, **changes: object) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": "principal",
        "tenant_id": "tenant-a",
        "scope": "supplier-risk:submit supplier-risk:read",
        "roles": ["analyst"],
        "iss": "https://issuer.example/",
        "aud": "ctec",
        "iat": int(now.timestamp()),
        "nbf": int((now - timedelta(seconds=1)).timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(changes)
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "key-1"})


def test_valid_signed_token_derives_minimum_trusted_principal() -> None:
    verifier, private = _verifier()
    principal = verifier.verify(_token(private))
    assert principal.principal_id == "principal"
    assert principal.tenant_id == "tenant-a"
    assert "supplier-risk:submit" in principal.scopes


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"iss": "https://attacker/"}, "AUTH_ISSUER_INVALID"),
        ({"aud": "other"}, "AUTH_AUDIENCE_INVALID"),
        ({"exp": 1}, "AUTH_TOKEN_EXPIRED"),
        ({"tenant_id": ["a", "b"]}, "AUTH_TENANT_MISSING_OR_AMBIGUOUS"),
    ],
)
def test_rejects_invalid_or_ambiguous_claims(change: dict[str, object], code: str) -> None:
    verifier, private = _verifier()
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(_token(private, **change))
    assert error.value.code == code


def test_rejects_unsigned_and_algorithm_substitution() -> None:
    verifier, _ = _verifier()
    unsigned = jwt.encode({"sub": "x"}, key="", algorithm="none")
    with pytest.raises(AuthenticationError, match="AUTH_ALGORITHM_FORBIDDEN"):
        verifier.verify(unsigned)
