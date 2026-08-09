"""FastAPI dependency boundary for trusted identity and application ports."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.supplier_risk.authentication import AuthenticationError, TrustedPrincipal
from app.application.supplier_risk_api import SupplierRiskApiService
from app.core.dependency_container import Container

_bearer = HTTPBearer(auto_error=False)


def container(request: Request) -> Container:
    value: Container = request.app.state.container
    return value


def correlation_id(request: Request) -> UUID:
    value = request.headers.get("X-Request-ID", "")
    try:
        return UUID(value)
    except ValueError:
        return uuid4()


def principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    value: Annotated[Container, Depends(container)],
) -> TrustedPrincipal:
    correlation = correlation_id(request)
    if credentials is None or credentials.scheme.lower() != "bearer":
        _audit_rejection(value, correlation, "AUTH_TOKEN_MISSING")
        raise HTTPException(401, detail={"code": "AUTH_TOKEN_MISSING"})
    if value.token_verifier is None:
        _audit_rejection(value, correlation, "AUTH_VERIFIER_UNAVAILABLE")
        raise HTTPException(503, detail={"code": "AUTH_VERIFIER_UNAVAILABLE"})
    try:
        return value.token_verifier.verify(credentials.credentials)
    except AuthenticationError as exc:
        _audit_rejection(value, correlation, exc.code)
        raise HTTPException(401, detail={"code": exc.code}) from exc


def api_service(value: Annotated[Container, Depends(container)]) -> SupplierRiskApiService:
    if value.supplier_risk_api is None:
        raise HTTPException(503, detail={"code": "SUPPLIER_RISK_SERVICE_UNAVAILABLE"})
    return value.supplier_risk_api


def _audit_rejection(value: Container, correlation: UUID, code: str) -> None:
    if value.security_audit is None:
        return
    value.security_audit.record(
        operation="AUTHENTICATE",
        category="AUTHENTICATION",
        outcome="REJECTED",
        code=code,
        correlation_id=correlation,
    )
