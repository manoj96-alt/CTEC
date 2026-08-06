import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.config.router import router as config_router
from app.api.health.router import router as health_router
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
                "user": request.headers.get("X-User", "anonymous"),
            },
        )
        request_id_context.reset(token)
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(config_router, prefix=API_PREFIX)
    app.include_router(version_router, prefix=API_PREFIX)
    return app


app = create_app()
