"""Fast, database-free proof that DemoEntityResolutionSeeder refuses any
tenant other than the labeled demo tenant before touching the session at
all -- the refusal is the very first statement in seed(), ahead of any
query or write, so it can be proven without a real database."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.demo_entity_resolution_seeder import (
    DemoEntityResolutionSeeder,
    DemoTenantRequiredError,
)


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_seeder_refuses_a_non_demo_tenant_by_default_argument() -> None:
    with _session() as session:
        seeder = DemoEntityResolutionSeeder(session)
        with pytest.raises(DemoTenantRequiredError):
            seeder.seed(tenant_id="not-the-demo-tenant")


@pytest.mark.parametrize(
    "tenant_id",
    [
        "",
        "ctec-demo-tenant ",  # trailing space -- not an exact match
        "CTEC-DEMO-TENANT",  # case mismatch -- not an exact match
        "tenant-a",
        BOOTSTRAP_DEMO_TENANT_ID + "-impersonator",
    ],
)
def test_seeder_refuses_every_non_exact_tenant_id(tenant_id: str) -> None:
    with _session() as session:
        seeder = DemoEntityResolutionSeeder(session)
        with pytest.raises(DemoTenantRequiredError):
            seeder.seed(tenant_id=tenant_id)
