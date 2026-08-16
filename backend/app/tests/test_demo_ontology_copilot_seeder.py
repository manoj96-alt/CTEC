import pytest

from app.infrastructure.persistence.demo_ontology_copilot_seeder import (
    DemoOntologyCopilotSeeder,
    DemoTenantRequiredError,
)


@pytest.mark.parametrize(
    "tenant_id",
    [
        "",
        "ctec-demo-tenant ",
        " ctec-demo-tenant",
        "CTEC-DEMO-TENANT",
        "some-real-customer-tenant",
        "ctec-demo-tenant-2",
    ],
)
def test_seeder_refuses_every_non_exact_tenant_id(tenant_id: str) -> None:
    seeder = DemoOntologyCopilotSeeder(session=None)  # type: ignore[arg-type]
    with pytest.raises(DemoTenantRequiredError):
        seeder.seed(tenant_id)
