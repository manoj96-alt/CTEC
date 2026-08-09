from app.integration.adapters.asm import AssertionAdapter
from app.integration.adapters.drm import DecisionAdapter
from app.integration.adapters.erm import EntityResolutionAdapter
from app.integration.adapters.grm import GovernanceAdapter
from app.integration.adapters.krm import KnowledgeAdapter
from app.integration.adapters.srm import SemanticResolutionAdapter
from app.integration.pipeline import supplier_risk_capability_ports
from app.integration.supplier_risk_policy import SupplierRiskPolicy
from app.tests.test_supplier_risk_pipeline import runtime_and_persistence


def test_pipeline_constructs_exact_six_production_adapter_types() -> None:
    runtime, _ = runtime_and_persistence()
    ports = runtime._orchestrator._ports
    assert tuple(type(item) for item in ports.ordered()) == (
        EntityResolutionAdapter,
        SemanticResolutionAdapter,
        AssertionAdapter,
        KnowledgeAdapter,
        DecisionAdapter,
        GovernanceAdapter,
    )


def test_factory_requires_injected_dependencies_and_policy() -> None:
    runtime, _ = runtime_and_persistence()
    dependencies = runtime._orchestrator._ports.erm._dependencies  # type: ignore[attr-defined]
    assert len(supplier_risk_capability_ports(dependencies, SupplierRiskPolicy()).ordered()) == 6
