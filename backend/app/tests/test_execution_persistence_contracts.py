from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.runtime.persistence.contracts import ReplayAuthorization


def test_replay_authority_requires_bounded_role_scope_and_tenant() -> None:
    auth = ReplayAuthorization(
        "operator",
        "tenant",
        ("EXECUTION_RECOVERY_OPERATOR",),
        ("execution:replay",),
        "decision",
        "recover",
        uuid4(),
        datetime.now(UTC),
    )
    auth.validate("tenant")
    with pytest.raises(PermissionError):
        auth.validate("another")
    with pytest.raises(PermissionError):
        ReplayAuthorization(
            "operator", "tenant", (), (), "decision", "recover", uuid4(), datetime.now(UTC)
        ).validate("tenant")
