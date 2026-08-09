from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.base import Base
from app.runtime.persistence.contracts import RECOVERY_ROLE, RECOVERY_SCOPE, ReplayAuthorization
from app.runtime.persistence.repository import SqlAlchemyExecutionStore
from app.tests.test_durable_execution_store import FakeHandoffProtector, request


def test_replay_preserves_explicit_authorization_evidence() -> None:
    value = ReplayAuthorization(
        "operator",
        "tenant",
        (RECOVERY_ROLE,),
        (RECOVERY_SCOPE,),
        "authorization-1",
        "database restart",
        uuid4(),
        datetime.now(UTC),
    )
    value.validate("tenant")
    assert value.authorization_reference == "authorization-1" and value.reason == "database restart"


def test_recovery_attempt_requires_authority_and_links_attempts() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    durable = SqlAlchemyExecutionStore(
        sessionmaker(engine, expire_on_commit=False), FakeHandoffProtector()
    )
    original = durable.admit(request(), b"original").execution_identifier
    replay = durable.admit(request(), b"replay").execution_identifier
    assert original is not None and replay is not None
    authorization = ReplayAuthorization(
        "operator",
        "tenant",
        (RECOVERY_ROLE,),
        (RECOVERY_SCOPE,),
        "authorization-2",
        "recover from verified checkpoint",
        uuid4(),
        datetime.now(UTC),
    )
    assert durable.authorize_recovery(original, replay, authorization)
