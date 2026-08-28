"""Gate W -- Governed API Version Declaration (CDD-038 SS9-SS10, SS14, SS17;
Gate W Artifact Authorization SS4). `SUPPORTED_API_VERSIONS` is a fixed,
code-level constant -- not durable state, not runtime-mutable -- exactly
mirroring `app.api.config.router`/`app.api.version.router`'s own
no-persistence, no-authentication, single-file convention. Adding a second
entry requires its own, separate, future governance cycle (CDD-038 SS9)."""

from enum import StrEnum

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class ApiVersionState(StrEnum):
    SUPPORTED = "SUPPORTED"


class SupportedApiVersion(BaseModel):
    version: str
    state: ApiVersionState


SUPPORTED_API_VERSIONS: tuple[SupportedApiVersion, ...] = (
    SupportedApiVersion(version="v1", state=ApiVersionState.SUPPORTED),
)


class ApiVersionsResponse(BaseModel):
    versions: tuple[SupportedApiVersion, ...]


@router.get("/versions", response_model=ApiVersionsResponse)
async def api_versions() -> ApiVersionsResponse:
    return ApiVersionsResponse(versions=SUPPORTED_API_VERSIONS)
