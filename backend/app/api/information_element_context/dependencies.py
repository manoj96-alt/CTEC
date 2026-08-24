"""FastAPI dependency boundary for the Gate O Information-Element Context
API (CDD-029; Gate O Artifact Authorization v1.0 §5). No
`dependency_container.py` change is authorized -- this module builds the
application service per-request from `Container.ontology_sessions`, the
existing `sessionmaker[Session]` already used by
`app.api.ontology_modeling.dependencies.ontology_modeling_session`. No new
`Container` field is added or read here beyond that one, already-present
attribute.

`information_element_context_session` is a `yield`-based dependency. Unlike
`ontology_modeling_session`, it never calls `session.commit()` -- Gate O is
read-only and introduces no write-transaction semantics of any kind
(CDD-029 §17)."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.supplier_risk.dependencies import container
from app.application.information_element_context_resolution import (
    InformationElementContextResolutionApplicationService,
)
from app.core.dependency_container import Container


def information_element_context_session(
    value: Annotated[Container, Depends(container)],
) -> Generator[Session, None, None]:
    if value.ontology_sessions is None:
        raise HTTPException(503, detail={"code": "INFORMATION_ELEMENT_CONTEXT_SERVICE_UNAVAILABLE"})
    with value.ontology_sessions() as session:
        yield session


def information_element_context_service(
    session: Annotated[Session, Depends(information_element_context_session)],
) -> InformationElementContextResolutionApplicationService:
    return InformationElementContextResolutionApplicationService(session=session)
