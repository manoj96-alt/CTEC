# isort: skip_file
import os
from collections.abc import Generator

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine


@pytest.fixture(scope="session")
def test_database_url() -> str:
    value = os.getenv("CTEC_TEST_DATABASE_URL")
    if not value:
        pytest.skip("CTEC_TEST_DATABASE_URL is required for PostgreSQL integration tests")
    return value


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: str) -> Generator[Engine, None, None]:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", test_database_url)
    previous = os.environ.get("CTEC_DATABASE_URL")
    os.environ["CTEC_DATABASE_URL"] = test_database_url
    alembic.command.downgrade(config, "base")
    alembic.command.upgrade(config, "head")
    engine = create_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()
        alembic.command.downgrade(config, "base")
        if previous is None:
            os.environ.pop("CTEC_DATABASE_URL", None)
        else:
            os.environ["CTEC_DATABASE_URL"] = previous
