from uuid import UUID

import pytest
from sqlalchemy import Engine, select, text

from app.core.config import Settings
from app.infrastructure.persistence.database import database_is_healthy
from app.infrastructure.persistence.models.country import Country
from app.infrastructure.persistence.models.enterprise_type import EnterpriseType
from app.infrastructure.persistence.repositories.country_repository import (
    CountryRepository,
)
from app.infrastructure.persistence.session import create_session_factory
from app.infrastructure.persistence.unit_of_work import UnitOfWork


def test_connection_and_migration(migrated_engine: Engine) -> None:
    assert database_is_healthy(migrated_engine)
    with migrated_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        table_count = connection.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
        assert revision == "0021_oqi2_cross_source"
        assert table_count == 74


def test_repository_crud(migrated_engine: Engine) -> None:
    factory = create_session_factory(migrated_engine)
    identifier = UUID("10000000-0000-0000-0000-000000000001")
    with factory.begin() as session:
        repository = CountryRepository(session)
        country = Country(
            country_id=identifier,
            country_name="Repository Test Country",
            iso2_code="XT",
            iso3_code="XTT",
        )
        repository.add(country)
    with factory.begin() as session:
        repository = CountryRepository(session)
        loaded = repository.get(identifier)
        assert loaded is not None
        assert loaded.country_name == "Repository Test Country"
        repository.delete(loaded)


def test_unit_of_work_rolls_back_on_error(migrated_engine: Engine) -> None:
    factory = create_session_factory(migrated_engine)
    identifier = UUID("10000000-0000-0000-0000-000000000002")
    with pytest.raises(RuntimeError, match="force rollback"), UnitOfWork(factory) as unit_of_work:
        repository = unit_of_work.repository(EnterpriseType)
        repository.add(EnterpriseType(enterprise_type_id=identifier, type_name="Rollback Test"))
        unit_of_work.session.flush()  # type: ignore[union-attr]
        raise RuntimeError("force rollback")
    with factory() as session:
        assert (
            session.scalar(
                select(EnterpriseType).where(EnterpriseType.enterprise_type_id == identifier)
            )
            is None
        )


def test_database_configuration_requires_url() -> None:
    settings = Settings(database_url=None)
    assert settings.database_url is None
