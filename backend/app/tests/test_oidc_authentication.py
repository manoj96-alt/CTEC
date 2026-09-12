from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

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


def _verifier(*, oidc_scope_claim: str = "scope") -> tuple[OidcJwtVerifier, object]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(
        oidc_issuer="https://issuer.example/",
        oidc_audience="ctec",
        oidc_jwks_url="https://issuer.example/jwks",
        oidc_scope_claim=oidc_scope_claim,
    )
    verifier = OidcJwtVerifier(settings)
    verifier._client = _Client(private.public_key())  # type: ignore[assignment]
    return verifier, private


def _token(key: Any, *, omit: tuple[str, ...] = (), **changes: object) -> str:
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
    for key_name in omit:
        claims.pop(key_name, None)
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "key-1"})


def test_valid_signed_token_derives_minimum_trusted_principal() -> None:
    verifier, private = _verifier()
    principal = verifier.verify(_token(private))
    assert principal.principal_id == "principal"
    assert principal.tenant_id == "tenant-a"
    assert "supplier-risk:submit" in principal.scopes


def test_valid_token_without_nbf_is_accepted() -> None:
    """ "nbf" is optional (e.g. Keycloak's default access token omits it
    entirely): its absence must not make an otherwise-valid token
    unverifiable."""
    verifier, private = _verifier()
    principal = verifier.verify(_token(private, omit=("nbf",)))
    assert principal.principal_id == "principal"


def test_token_with_future_nbf_is_rejected() -> None:
    """When "nbf" IS present, it must still be enforced normally."""
    verifier, private = _verifier()
    future_nbf = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(_token(private, nbf=future_nbf))
    assert error.value.code == "AUTH_TOKEN_NOT_YET_VALID"


def test_token_missing_exp_is_rejected() -> None:
    verifier, private = _verifier()
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(_token(private, omit=("exp",)))
    assert error.value.code == "AUTH_TOKEN_UNVERIFIABLE"


def test_token_missing_subject_claim_is_rejected() -> None:
    verifier, private = _verifier()
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(_token(private, omit=("sub",)))
    assert error.value.code == "AUTH_TOKEN_UNVERIFIABLE"


class _ClaimOverride(TypedDict, total=False):
    iss: str
    aud: str
    exp: int
    tenant_id: list[str]


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"iss": "https://attacker/"}, "AUTH_ISSUER_INVALID"),
        ({"aud": "other"}, "AUTH_AUDIENCE_INVALID"),
        ({"exp": 1}, "AUTH_TOKEN_EXPIRED"),
        ({"tenant_id": ["a", "b"]}, "AUTH_TENANT_MISSING_OR_AMBIGUOUS"),
    ],
)
def test_rejects_invalid_or_ambiguous_claims(change: _ClaimOverride, code: str) -> None:
    verifier, private = _verifier()
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(_token(private, **change))
    assert error.value.code == code


def test_rejects_unsigned_and_algorithm_substitution() -> None:
    verifier, _ = _verifier()
    unsigned = jwt.encode({"sub": "x"}, key="", algorithm="none")
    with pytest.raises(AuthenticationError, match="AUTH_ALGORITHM_FORBIDDEN"):
        verifier.verify(unsigned)


def test_configured_scp_claim_is_extracted_in_entra_delegated_shape() -> None:
    """CDD-063: Microsoft Entra External ID exposes delegated permissions
    through the "scp" claim as a space-delimited string -- the same shape
    Keycloak already uses for "scope". Configuring oidc_scope_claim="scp"
    must extract scopes from "scp" via the existing, unmodified parser."""
    verifier, private = _verifier(oidc_scope_claim="scp")
    token = _token(
        private,
        omit=("scope",),
        scp="supplier-risk:read entity-resolution:read",
    )
    principal = verifier.verify(token)
    assert principal.scopes == ("entity-resolution:read", "supplier-risk:read")


def test_configured_scp_claim_does_not_fall_back_to_scope() -> None:
    """CDD-063: when oidc_scope_claim="scp" is configured (the governed
    Azure/Entra setting), a token carrying only "scope" (no "scp" at all)
    must yield zero scopes -- never a silent fallback to "scope"."""
    verifier, private = _verifier(oidc_scope_claim="scp")
    token = _token(private)
    principal = verifier.verify(token)
    assert principal.scopes == ()
