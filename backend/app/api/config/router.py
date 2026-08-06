from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class PublicConfigResponse(BaseModel):
    environment: str
    api_version: str


@router.get("/config", response_model=PublicConfigResponse)
async def public_config(request: Request) -> PublicConfigResponse:
    container = request.app.state.container
    return PublicConfigResponse(environment=container.settings.environment, api_version="v1")
