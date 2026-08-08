from sqlalchemy import Engine, create_engine

from app.core.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    if not settings.database_url:
        raise ValueError("CTEC_DATABASE_URL is required for persistence operations")
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
    )


def database_is_healthy(engine: Engine) -> bool:
    from sqlalchemy import text

    with engine.connect() as connection:
        result: bool = connection.execute(text("SELECT 1")).scalar_one() == 1
        return result
