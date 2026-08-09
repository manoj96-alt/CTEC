from app.runtime.persistence.repository import SqlAlchemyExecutionStore


def test_api_service_uses_the_existing_durable_store_type() -> None:
    assert SqlAlchemyExecutionStore.__module__ == "app.runtime.persistence.repository"
