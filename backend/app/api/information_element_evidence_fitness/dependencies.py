"""FastAPI dependency boundary for the Governed Evidence Fitness Exposure
API (CDD-034; CDD-034 Artifact Authorization v1.0 §6). No
`dependency_container.py` change is authorized -- this module builds the
application service per-request from `Container.ontology_sessions`, the
existing `sessionmaker[Session]` already reused by
`app.api.information_element_context.dependencies
.information_element_context_session`. No new `Container` field is added or
read here beyond that one, already-present attribute.

`information_element_evidence_fitness_session` is a `yield`-based
dependency. It never calls `session.commit()` -- this capability is
read-only and introduces no write-transaction semantics of any kind
(CDD-034 §19)."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.supplier_risk.dependencies import container
from app.application.information_element_evidence_fitness_resolution import (
    InformationElementEvidenceFitnessResolutionApplicationService,
)
from app.core.dependency_container import Container


def information_element_evidence_fitness_session(
    value: Annotated[Container, Depends(container)],
) -> Generator[Session, None, None]:
    if value.ontology_sessions is None:
        raise HTTPException(
            503, detail={"code": "INFORMATION_ELEMENT_EVIDENCE_FITNESS_SERVICE_UNAVAILABLE"}
        )
    with value.ontology_sessions() as session:
        yield session


def information_element_evidence_fitness_service(
    session: Annotated[Session, Depends(information_element_evidence_fitness_session)],
) -> InformationElementEvidenceFitnessResolutionApplicationService:
    return InformationElementEvidenceFitnessResolutionApplicationService(session=session)
