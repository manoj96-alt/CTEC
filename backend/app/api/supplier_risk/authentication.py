"""Provider-neutral OIDC/JWKS bearer-token verification."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import jwt
from jwt import PyJWKClient

from app.core.config import Settings


class AuthenticationError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class TrustedPrincipal:
    principal_id: str
    tenant_id: str
    scopes: tuple[str, ...]
    roles: tuple[str, ...]
    issuer: str
    issued_at: datetime
    expires_at: datetime


class TokenVerifier(Protocol):
    def verify(self, token: str) -> TrustedPrincipal: ...


class OidcJwtVerifier:
    """Real asymmetric verifier; token contents are trusted only after validation."""

    def __init__(self, settings: Settings) -> None:
        if not settings.oidc_issuer or not settings.oidc_audience or not settings.oidc_jwks_url:
            raise ValueError("OIDC issuer, audience, and JWKS URL are required")
        if not settings.oidc_algorithms or any(
            value.lower() == "none" for value in settings.oidc_algorithms
        ):
            raise ValueError("At least one non-none signing algorithm is required")
        self._settings = settings
        self._client = PyJWKClient(
            settings.oidc_jwks_url,
            cache_jwk_set=True,
            lifespan=settings.oidc_jwks_cache_seconds,
            cache_keys=True,
            timeout=5,
        )

    def verify(self, token: str) -> TrustedPrincipal:
        if not token or token.count(".") != 2:
            raise AuthenticationError("AUTH_TOKEN_MALFORMED")
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm not in self._settings.oidc_algorithms:
                raise AuthenticationError("AUTH_ALGORITHM_FORBIDDEN")
            key = self._client.get_signing_key_from_jwt(token).key
            claims: dict[str, Any] = jwt.decode(
                token,
                key,
                algorithms=self._settings.oidc_algorithms,
                audience=self._settings.oidc_audience,
                issuer=self._settings.oidc_issuer,
                leeway=self._settings.oidc_clock_skew_seconds,
                options={"require": ["exp", "nbf", self._settings.oidc_subject_claim]},
            )
            return self._principal(claims)
        except AuthenticationError:
            raise
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("AUTH_TOKEN_EXPIRED") from exc
        except jwt.ImmatureSignatureError as exc:
            raise AuthenticationError("AUTH_TOKEN_NOT_YET_VALID") from exc
        except jwt.InvalidIssuerError as exc:
            raise AuthenticationError("AUTH_ISSUER_INVALID") from exc
        except jwt.InvalidAudienceError as exc:
            raise AuthenticationError("AUTH_AUDIENCE_INVALID") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError("AUTH_TOKEN_UNVERIFIABLE") from exc
        except Exception as exc:
            raise AuthenticationError("AUTH_KEY_SOURCE_UNAVAILABLE") from exc

    def _principal(self, claims: dict[str, Any]) -> TrustedPrincipal:
        subject = claims.get(self._settings.oidc_subject_claim)
        tenant = claims.get(self._settings.oidc_tenant_claim)
        if not isinstance(subject, str) or not subject.strip():
            raise AuthenticationError("AUTH_PRINCIPAL_MISSING")
        if not isinstance(tenant, str) or not tenant.strip():
            raise AuthenticationError("AUTH_TENANT_MISSING_OR_AMBIGUOUS")
        scopes = _claim_values(claims.get(self._settings.oidc_scope_claim))
        roles = _claim_values(claims.get(self._settings.oidc_roles_claim))
        return TrustedPrincipal(
            principal_id=subject,
            tenant_id=tenant,
            scopes=scopes,
            roles=roles,
            issuer=self._settings.oidc_issuer,
            issued_at=datetime.fromtimestamp(int(claims.get("iat", 0)), UTC),
            expires_at=datetime.fromtimestamp(int(claims["exp"]), UTC),
        )


def _claim_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(sorted(set(value.split())))
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(sorted(set(value)))
    return ()
