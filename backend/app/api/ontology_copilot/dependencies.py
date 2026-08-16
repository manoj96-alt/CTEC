"""FastAPI dependency boundary for the Ask CTEC API. Reuses
app.api.supplier_risk.dependencies's principal/container dependencies
exactly -- there is no separate authentication mechanism for this API."""

from typing import Annotated

from fastapi import Depends, HTTPException

from app.api.supplier_risk.dependencies import container
from app.application.ontology_copilot_api import OntologyCopilotApiService
from app.core.dependency_container import Container


def ontology_copilot_api_service(
    value: Annotated[Container, Depends(container)],
) -> OntologyCopilotApiService:
    if value.ontology_copilot_api is None:
        raise HTTPException(503, detail={"code": "ONTOLOGY_COPILOT_SERVICE_UNAVAILABLE"})
    return value.ontology_copilot_api
