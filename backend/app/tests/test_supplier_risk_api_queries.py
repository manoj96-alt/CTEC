from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.supplier_risk.schemas import ExecutionResponse
from app.infrastructure.persistence.base import Base
from app.runtime.persistence.crypto import AuthenticatedHandoffProtector
from app.runtime.persistence.repository import SqlAlchemyExecutionStore
from app.tests.test_durable_execution_store import request


def test_query_contract_exposes_references_not_protected_payloads() -> None:
    fields = ExecutionResponse.model_fields
    assert "produced_record_references" in fields
    assert "opaque_payload" not in fields
    assert "authority_context" not in fields


def test_durable_queries_are_tenant_scoped_before_disclosure() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    store = SqlAlchemyExecutionStore(
        sessionmaker(engine, expire_on_commit=False),
        AuthenticatedHandoffProtector({"test": b"t" * 32}, "test"),
    )
    execution_id = store.admit(request(), b"fingerprint").execution_identifier
    assert execution_id is not None
    assert store.list_attempts(execution_id, "tenant")
    assert store.list_attempts(execution_id, "other-tenant") == ()
    assert store.list_stages(execution_id, execution_id, "other-tenant") == ()
    assert store.get_result_for_logical(execution_id, "other-tenant") is None
