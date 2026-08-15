"""FastAPI dependency boundary for the Entity Resolution Steward API.
Reuses app.api.supplier_risk.dependencies's principal/container dependencies
exactly -- there is no separate authentication mechanism for this API."""

from typing import Annotated

from fastapi import Depends, HTTPException

from app.api.supplier_risk.dependencies import container
from app.application.entity_resolution_steward_api import EntityResolutionStewardApiService
from app.core.dependency_container import Container


def steward_api_service(
    value: Annotated[Container, Depends(container)],
) -> EntityResolutionStewardApiService:
    if value.entity_resolution_steward_api is None:
        raise HTTPException(503, detail={"code": "ENTITY_RESOLUTION_STEWARD_SERVICE_UNAVAILABLE"})
    return value.entity_resolution_steward_api
