import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.api_versions.router import router as api_versions_router
from app.api.config.router import router as config_router
from app.api.entity_resolution.router import router as entity_resolution_router
from app.api.gate_s.router import router as gate_s_router
from app.api.gate_v.router import router as gate_v_router
from app.api.health.router import router as health_router
from app.api.information_element_context.router import router as information_element_context_router
from app.api.information_element_evidence_fitness.router import (
    router as information_element_evidence_fitness_router,
)
from app.api.ontology.router import router as ontology_router
from app.api.ontology_copilot.router import router as ontology_copilot_router
from app.api.ontology_modeling.router import router as ontology_modeling_router
from app.api.supplier_risk.router import router as supplier_risk_router
from app.api.supply_chain_impact.router import router as supply_chain_impact_router
from app.api.version.router import router as version_router
from app.core.constants import API_PREFIX, APP_NAME, APP_VERSION, REQUEST_ID_HEADER
from app.core.dependency_container import build_container
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, request_id_context

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = build_container()
    app.state.container = container
    configure_logging(container.settings.log_level)
    logger.info("application_started", extra={"environment": container.settings.environment})
    yield
    logger.info("application_stopped")


def create_app() -> FastAPI:
    settings = build_container().settings
    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Paths using the flat, stable {"code", "message", "correlation_id",
    # "retryable"} error contract instead of FastAPI's default nested
    # {"detail": ...} body. Additive only: every other existing path
    # (ontology, config, version, health) keeps the default shape
    # byte-for-byte.
    _STABLE_ERROR_CONTRACT_PATHS = (
        "/api/v1/supplier-risk",
        "/api/v1/entity-resolution",
        "/api/v1/ontology-copilot",
    )

    @app.exception_handler(HTTPException)
    async def supplier_risk_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        if not request.url.path.startswith(_STABLE_ERROR_CONTRACT_PATHS):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        detail: dict[str, object] = exc.detail if isinstance(exc.detail, dict) else {}
        code = str(detail.get("code", "REQUEST_REJECTED"))
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": code,
                "message": "Request could not be completed",
                "correlation_id": _safe_request_id(request),
                "retryable": exc.status_code in {429, 500, 503},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def supplier_risk_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        if not request.url.path.startswith(_STABLE_ERROR_CONTRACT_PATHS):
            return JSONResponse(status_code=422, content={"detail": exc.errors()})
        return JSONResponse(
            status_code=422,
            content={
                "code": "REQUEST_VALIDATION_FAILED",
                "message": "Request could not be completed",
                "correlation_id": _safe_request_id(request),
                "retryable": False,
            },
        )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed", extra={"path": request.url.path})
            request_id_context.reset(token)
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        request_id_context.reset(token)
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(config_router, prefix=API_PREFIX)
    app.include_router(version_router, prefix=API_PREFIX)
    app.include_router(api_versions_router, prefix=API_PREFIX)
    app.include_router(supplier_risk_router)
    app.include_router(ontology_router)
    app.include_router(entity_resolution_router)
    app.include_router(ontology_copilot_router)
    app.include_router(ontology_modeling_router)
    app.include_router(supply_chain_impact_router)
    app.include_router(information_element_context_router)
    app.include_router(information_element_evidence_fitness_router)
    app.include_router(gate_s_router)
    app.include_router(gate_v_router)
    return app


def _safe_request_id(request: Request) -> str:
    value = request.headers.get(REQUEST_ID_HEADER, "")
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return str(uuid.uuid4())


app = create_app()
