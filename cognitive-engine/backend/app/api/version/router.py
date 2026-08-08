from fastapi import APIRouter
from pydantic import BaseModel

from app.core.constants import APP_NAME, APP_VERSION

router = APIRouter(tags=["system"])


class VersionResponse(BaseModel):
    name: str
    version: str


@router.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    return VersionResponse(name=APP_NAME, version=APP_VERSION)
