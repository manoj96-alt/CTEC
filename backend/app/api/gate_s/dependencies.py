"""FastAPI dependency boundary for the Gate S Governed Human Approval API
(CDD-036 §9; Gate S Artifact Authorization §9). No `dependency_container.py`
change is authorized -- this module builds the repository and application
service per-request from `Container.ontology_sessions`, the existing,
generic `sessionmaker[Session]` already reused by
`app.api.ontology_modeling.dependencies` for an unrelated capability. No new
`Container` field is added or read here beyond that one, already-present
attribute.

`gate_s_session` is a `yield`-based dependency: FastAPI opens the session
before the endpoint runs and commits/closes it after the endpoint returns
normally (an exception propagating out of the endpoint skips the commit, so
no partial approval/note mutation is ever committed on failure).
`ApiSecurityAuditRepository` is constructed directly from the sessionmaker
(not the per-request session) because it manages its own independent,
immediately-committed transaction per audit write (CDD-013) -- the same
`Container.ontology_sessions` factory, a second, separate connection."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.supplier_risk.dependencies import container
from app.application.gate_s_approval_service import GateSApprovalService
from app.core.dependency_container import Container
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditRepository
from app.infrastructure.persistence.gate_s_approval_repository import (
    GateSApprovalRepository,
    GateSApprovalRepositoryImpl,
)


def gate_s_session(
    value: Annotated[Container, Depends(container)],
) -> Generator[Session, None, None]:
    if value.ontology_sessions is None:
        raise HTTPException(503, detail={"code": "GATE_S_SERVICE_UNAVAILABLE"})
    with value.ontology_sessions() as session:
        yield session
        session.commit()


def gate_s_approval_repository(
    session: Annotated[Session, Depends(gate_s_session)],
) -> GateSApprovalRepository:
    return GateSApprovalRepositoryImpl(session)


def gate_s_approval_service(
    session: Annotated[Session, Depends(gate_s_session)],
    dependencies: Annotated[Container, Depends(container)],
) -> GateSApprovalService:
    assert dependencies.ontology_sessions is not None
    return GateSApprovalService(
        repository=GateSApprovalRepositoryImpl(session),
        audit_repository=ApiSecurityAuditRepository(dependencies.ontology_sessions),
    )
