from app.integration.adapters.asm import AssertionAdapter
from app.integration.adapters.drm import DecisionAdapter
from app.integration.adapters.erm import EntityResolutionAdapter
from app.integration.adapters.grm import GovernanceAdapter
from app.integration.adapters.krm import KnowledgeAdapter
from app.integration.adapters.srm import SemanticResolutionAdapter
from app.integration.dependencies import IntegrationDependencies
from app.integration.supplier_risk_policy import SupplierRiskPolicy
from app.runtime.orchestration import CapabilityStepPorts


def supplier_risk_capability_ports(
    dependencies: IntegrationDependencies, policy: SupplierRiskPolicy
) -> CapabilityStepPorts:
    """Construct the one governed ERM→SRM→ASM→KRM→DRM→GRM adapter chain."""
    return CapabilityStepPorts(
        erm=EntityResolutionAdapter(dependencies),
        srm=SemanticResolutionAdapter(dependencies),
        asm=AssertionAdapter(dependencies),
        krm=KnowledgeAdapter(dependencies),
        drm=DecisionAdapter(dependencies, policy),
        grm=GovernanceAdapter(dependencies, policy),
    )
