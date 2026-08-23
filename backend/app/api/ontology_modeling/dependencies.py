"""FastAPI dependency boundary for the Gate M Ontology Modeling API (CDD-028;
Gate M Artifact Authorization v1.1 §4.5). No `dependency_container.py`
change is authorized (AA v1.1 §3) -- this module builds the repository and
application service per-request from `Container.ontology_sessions`, the
existing `sessionmaker[Session]` already used by
`app.api.ontology.router._ontology_session_factory`. No new `Container`
field is added or read here beyond that one, already-present attribute.

`ontology_modeling_session` is a `yield`-based dependency: FastAPI opens the
session before the endpoint runs and commits/closes it after the endpoint
returns normally (an exception propagating out of the endpoint skips the
commit, so no partial canonical mutation is ever committed on failure --
AA v1.1 §13, §18)."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.supplier_risk.dependencies import container
from app.application.ontology_modeling_proposal_governance import (
    OntologyModelingProposalGovernanceApplicationService,
)
from app.core.dependency_container import Container
from app.infrastructure.persistence.ontology_change_proposal_repository import (
    OntologyChangeProposalRepository,
    OntologyChangeProposalRepositoryImpl,
)


def ontology_modeling_session(
    value: Annotated[Container, Depends(container)],
) -> Generator[Session, None, None]:
    if value.ontology_sessions is None:
        raise HTTPException(503, detail={"code": "ONTOLOGY_MODELING_SERVICE_UNAVAILABLE"})
    with value.ontology_sessions() as session:
        yield session
        session.commit()


def ontology_modeling_proposal_repository(
    session: Annotated[Session, Depends(ontology_modeling_session)],
) -> OntologyChangeProposalRepository:
    return OntologyChangeProposalRepositoryImpl(session)


def ontology_modeling_service(
    session: Annotated[Session, Depends(ontology_modeling_session)],
) -> OntologyModelingProposalGovernanceApplicationService:
    return OntologyModelingProposalGovernanceApplicationService(
        session=session,
        proposal_repository=OntologyChangeProposalRepositoryImpl(session),
    )
