"""Gate F pipeline factory (CDD-015 §7, §33): constructs the Gate F adapter
set, mirroring `integration/pipeline.py`'s existing CDD-011 factory pattern.

Returns an in-process dependency bundle scoped to one session/transaction,
following `SqlAlchemyCapabilityPersistence`'s existing capability-local
transaction pattern (§33) -- distinct in shape from `CapabilityStepPorts`
(`runtime/orchestration.py`) because Gate F's adapters are plain, directly
callable classes, not `CapabilityStepPort` implementations: CDD-015 §33
authorizes no change to `runtime/orchestration.py`, `runtime/recovery.py`,
or any admission entrypoint (`api/supplier_risk/router.py`) that would be
needed to actually invoke `RuntimeOrchestrator` for Gate F. Compatibility
with the existing six-port CDD-010/CDD-012 durable-execution and replay
model (CDD-015 §20) is a forward architectural guarantee -- no seventh
stage, no orchestration-contract change -- not a requirement that F-I2
itself run Gate F's adapters through it before an admission entrypoint for
Gate F exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.integration.adapters.gate_f.drm import GateFDecisionAdapter
from app.integration.adapters.gate_f.grm import GateFGovernanceAdapter
from app.integration.adapters.gate_f.krm import GateFKnowledgeAdapter


@dataclass(frozen=True, slots=True)
class GateFCapabilityAdapters:
    krm: GateFKnowledgeAdapter
    drm: GateFDecisionAdapter
    grm: GateFGovernanceAdapter


def gate_f_capability_adapters(session: Session) -> GateFCapabilityAdapters:
    """Construct the one governed Gate F KRM -> DRM -> GRM adapter set,
    sharing one session/transaction: the caller owns the transaction
    boundary and each adapter's writes participate in it."""
    return GateFCapabilityAdapters(
        krm=GateFKnowledgeAdapter(session),
        drm=GateFDecisionAdapter(session),
        grm=GateFGovernanceAdapter(session),
    )
