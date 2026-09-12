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


def _verifier(
    *, oidc_scope_claim: str = "scope", oidc_tenant_claim: str = "tenant_id"
) -> tuple[OidcJwtVerifier, object]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(
        oidc_issuer="https://issuer.example/",
        oidc_audience="ctec",
        oidc_jwks_url="https://issuer.example/jwks",
        oidc_scope_claim=oidc_scope_claim,
        oidc_tenant_claim=oidc_tenant_claim,
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


# CDD-064: representative test claim key only. Real Microsoft Entra rejects
# a bare outgoing claim literally named "tenant_id" ("This claim type is
# restricted" -- it is a permanent member of Entra's JWT restricted claim
# set), so the governed Azure correction is a namespaced custom claim. This
# exact string is NOT asserted to be the real Azure-emitted claim key --
# that value is unknown until real Entra portal execution captures it
# (CDD-064 SS4/SS8); it exists here solely to prove the backend's existing,
# unmodified claim-name-driven lookup handles an arbitrary namespaced key
# identically to any other string key.
NAMESPACED_TENANT_CLAIM = "https://noetva.ai/claims/tenant_id"


def test_configured_namespaced_tenant_claim_is_accepted() -> None:
    """CDD-064: configuring oidc_tenant_claim to the governed namespaced
    key must extract the Noetva business-tenant identifier from it."""
    verifier, private = _verifier(oidc_tenant_claim=NAMESPACED_TENANT_CLAIM)
    token = _token(
        private,
        omit=("tenant_id",),
        **{NAMESPACED_TENANT_CLAIM: "noetva-dev-tenant"},
    )
    principal = verifier.verify(token)
    assert principal.tenant_id == "noetva-dev-tenant"


def test_configured_namespaced_tenant_claim_does_not_fall_back_to_bare_tenant_id() -> None:
    """CDD-064: when the namespaced claim is configured (the governed
    Azure/Entra setting), a token carrying only the bare "tenant_id" claim
    (Entra's blocked/legacy shape) must be rejected -- never a silent
    fallback to "tenant_id"."""
    verifier, private = _verifier(oidc_tenant_claim=NAMESPACED_TENANT_CLAIM)
    token = _token(private)
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(token)
    assert error.value.code == "AUTH_TENANT_MISSING_OR_AMBIGUOUS"


def test_entra_tid_never_becomes_trusted_tenant() -> None:
    """CDD-064: Microsoft Entra's own directory-tenant GUID claim, "tid", is
    never the Noetva business tenant. A token carrying "tid" but not the
    configured namespaced claim must fail closed."""
    verifier, private = _verifier(oidc_tenant_claim=NAMESPACED_TENANT_CLAIM)
    token = _token(
        private,
        omit=("tenant_id",),
        tid="8f9e2dee-5a5b-4b33-9044-4d11691899de",
    )
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(token)
    assert error.value.code == "AUTH_TENANT_MISSING_OR_AMBIGUOUS"


def test_entra_tid_is_ignored_even_when_namespaced_claim_also_present() -> None:
    """CDD-064: when both Entra's "tid" and the configured namespaced
    business-tenant claim are present (as a real Entra token would carry),
    only the configured claim's value is trusted -- "tid" is never
    consulted, even as a secondary source."""
    verifier, private = _verifier(oidc_tenant_claim=NAMESPACED_TENANT_CLAIM)
    token = _token(
        private,
        omit=("tenant_id",),
        tid="8f9e2dee-5a5b-4b33-9044-4d11691899de",
        **{NAMESPACED_TENANT_CLAIM: "noetva-dev-tenant"},
    )
    principal = verifier.verify(token)
    assert principal.tenant_id == "noetva-dev-tenant"
    assert principal.tenant_id != "8f9e2dee-5a5b-4b33-9044-4d11691899de"


def test_configured_namespaced_tenant_claim_missing_entirely_fails_closed() -> None:
    """CDD-064: if the configured namespaced claim is absent altogether
    (and no bare "tenant_id" either), authentication must fail closed."""
    verifier, private = _verifier(oidc_tenant_claim=NAMESPACED_TENANT_CLAIM)
    token = _token(private, omit=("tenant_id",))
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(token)
    assert error.value.code == "AUTH_TENANT_MISSING_OR_AMBIGUOUS"


def test_configured_namespaced_tenant_claim_list_value_fails_closed() -> None:
    """CDD-064: an ambiguous (list-valued) namespaced tenant claim must be
    rejected exactly like an ambiguous bare "tenant_id", never accepted as,
    e.g., its first element."""
    verifier, private = _verifier(oidc_tenant_claim=NAMESPACED_TENANT_CLAIM)
    token = _token(
        private,
        omit=("tenant_id",),
        **{NAMESPACED_TENANT_CLAIM: ["tenant-a", "tenant-b"]},
    )
    with pytest.raises(AuthenticationError) as error:
        verifier.verify(token)
    assert error.value.code == "AUTH_TENANT_MISSING_OR_AMBIGUOUS"
