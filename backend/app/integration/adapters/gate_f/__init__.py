"""Gate F contextual-fact adapters (CDD-015 §9-§12, §33). New, separate
adapter package -- distinct from CDD-011's existing
`integration/adapters/{krm,drm,grm}.py` -- to avoid any regression risk to
the existing, implemented supplier-risk pipeline."""

from app.integration.adapters.gate_f.drm import (
    DrmUnit,
    GateFDecisionAdapter,
    GateFDecisionResult,
    GateFOutcomeReason,
)
from app.integration.adapters.gate_f.grm import (
    GateFGovernanceAdapter,
    GateFGovernanceResult,
    GateFGovernanceStanding,
)
from app.integration.adapters.gate_f.krm import (
    CandidateEvidence,
    GateFKnowledgeAdapter,
    GovernedFact,
)

__all__ = [
    "CandidateEvidence",
    "DrmUnit",
    "GateFDecisionAdapter",
    "GateFDecisionResult",
    "GateFGovernanceAdapter",
    "GateFGovernanceResult",
    "GateFGovernanceStanding",
    "GateFKnowledgeAdapter",
    "GateFOutcomeReason",
    "GovernedFact",
]
