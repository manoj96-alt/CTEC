"""FastAPI dependency boundary for the Gate F Supply Chain Impact API.
Reuses app.api.supplier_risk.dependencies's principal/container
dependencies exactly -- there is no separate authentication mechanism for
this API (PAD-003 §11, unchanged from Gate E)."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.dependencies import container
from app.application.supply_chain_impact_api import SupplyChainImpactApiService
from app.core.dependency_container import Container


def supply_chain_impact_api_service(
    value: Annotated[Container, Depends(container)],
) -> SupplyChainImpactApiService:
    if value.supply_chain_impact_api is None:
        raise HTTPException(503, detail={"code": "SUPPLY_CHAIN_IMPACT_SERVICE_UNAVAILABLE"})
    return value.supply_chain_impact_api


def supply_chain_impact_sessions(
    value: Annotated[Container, Depends(container)],
) -> "sessionmaker[Session]":
    """The same tenant-scoped session factory ontology/entity-resolution
    reads already use (`container.ontology_sessions`) -- the read
    operation needs a session to call the existing public
    DecisionEvaluationRepositoryImpl/GovernanceEvaluationRepositoryImpl
    read contracts directly; it does not go through
    SupplyChainImpactApiService, which implements only the evaluate
    operation (CDD-015 §33)."""
    if value.ontology_sessions is None:
        raise HTTPException(503, detail={"code": "SUPPLY_CHAIN_IMPACT_SERVICE_UNAVAILABLE"})
    return value.ontology_sessions
