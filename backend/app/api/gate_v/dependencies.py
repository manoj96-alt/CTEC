"""FastAPI dependency boundary for the Gate V Governed Agent Resolution API
(CDD-037 §9; Gate V Artifact Authorization §9). No `dependency_container.py`
change is authorized -- this module builds the repository and application
service per-request from `Container.ontology_sessions`, exactly mirroring
`app.api.gate_s.dependencies`. No new `Container` field is added or read
here beyond that one, already-present attribute.

`gate_v_session` is a `yield`-based dependency: FastAPI opens the session
before the endpoint runs and commits/closes it after the endpoint returns
normally (an exception propagating out of the endpoint skips the commit, so
no partial resolution/approval-request write is ever committed on
failure). The Gate S approval-request write (when `PROPOSED`) and the Gate V
resolution write share this one session/transaction: both commit together
or neither does. `ApiSecurityAuditRepository` is constructed directly from
the sessionmaker (not the per-request session) because it manages its own
independent, immediately-committed transaction per audit write (CDD-013) --
the same `Container.ontology_sessions` factory, a second, separate
connection."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.supplier_risk.dependencies import container
from app.application.gate_s_approval_service import GateSApprovalService
from app.application.gate_v_agent_service import GateVApplicationService
from app.core.dependency_container import Container
from app.infrastructure.persistence.api_security_audit_repository import ApiSecurityAuditRepository
from app.infrastructure.persistence.gate_s_approval_repository import GateSApprovalRepositoryImpl
from app.infrastructure.persistence.gate_v_agent_resolution_repository import (
    GateVAgentResolutionRepository,
    GateVAgentResolutionRepositoryImpl,
)


def gate_v_session(
    value: Annotated[Container, Depends(container)],
) -> Generator[Session, None, None]:
    if value.ontology_sessions is None:
        raise HTTPException(503, detail={"code": "GATE_V_SERVICE_UNAVAILABLE"})
    with value.ontology_sessions() as session:
        yield session
        session.commit()


def gate_v_agent_resolution_repository(
    session: Annotated[Session, Depends(gate_v_session)],
) -> GateVAgentResolutionRepository:
    return GateVAgentResolutionRepositoryImpl(session)


def gate_v_agent_service(
    session: Annotated[Session, Depends(gate_v_session)],
    dependencies: Annotated[Container, Depends(container)],
) -> GateVApplicationService:
    assert dependencies.ontology_sessions is not None
    gate_s_service = GateSApprovalService(
        repository=GateSApprovalRepositoryImpl(session),
        audit_repository=ApiSecurityAuditRepository(dependencies.ontology_sessions),
    )
    return GateVApplicationService(
        repository=GateVAgentResolutionRepositoryImpl(session),
        gate_s_service=gate_s_service,
        audit_repository=ApiSecurityAuditRepository(dependencies.ontology_sessions),
    )
