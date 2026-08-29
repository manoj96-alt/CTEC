"""CDD-042 §8: `ImpactPropagationPolicy` CRUD + ACTIVE-version lookup.
Administrative/governance-authoring surface -- OQI4 evaluation itself never
calls this module's `create`/`retire`; the recursive traversal statement
(`oqi_ontology_impact_evaluation_repository.py`) reads
`impact_propagation_policies` directly, in the same statement as the graph
traversal (CDD-042 §9), never through this repository."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.oqi_ontology_impact.policy import (
    ImpactPropagationPolicy,
    PolicyGovernanceStatus,
    PropagationDirection,
)
from app.infrastructure.persistence.models.oqi_ontology_impact_policy import (
    ImpactPropagationPolicyORM,
)


class OqiOntologyImpactPolicyRepository(Protocol):
    def create(self, policy: ImpactPropagationPolicy) -> None: ...

    def get_by_id(self, tenant_id: str, policy_id: UUID) -> ImpactPropagationPolicy | None: ...

    def get_active(
        self, tenant_id: str, relationship_type_id: UUID, direction: PropagationDirection
    ) -> ImpactPropagationPolicy | None: ...


def _to_orm(policy: ImpactPropagationPolicy) -> ImpactPropagationPolicyORM:
    return ImpactPropagationPolicyORM(
        policy_id=policy.policy_id,
        tenant_id=policy.tenant_id,
        relationship_type_id=policy.relationship_type_id,
        direction=policy.direction.value,
        max_depth=policy.max_depth,
        governance_status=policy.governance_status.value,
        version_number=policy.version_number,
        previous_version_id=policy.previous_version_id,
    )


def _to_domain(model: ImpactPropagationPolicyORM) -> ImpactPropagationPolicy:
    return ImpactPropagationPolicy(
        policy_id=model.policy_id,
        tenant_id=model.tenant_id,
        relationship_type_id=model.relationship_type_id,
        direction=PropagationDirection(model.direction),
        max_depth=model.max_depth,
        governance_status=PolicyGovernanceStatus(model.governance_status),
        version_number=model.version_number,
        previous_version_id=model.previous_version_id,
    )


class OqiOntologyImpactPolicyRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, policy: ImpactPropagationPolicy) -> None:
        self.session.add(_to_orm(policy))

    def get_by_id(self, tenant_id: str, policy_id: UUID) -> ImpactPropagationPolicy | None:
        model = self.session.get(ImpactPropagationPolicyORM, policy_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        return _to_domain(model)

    def get_active(
        self, tenant_id: str, relationship_type_id: UUID, direction: PropagationDirection
    ) -> ImpactPropagationPolicy | None:
        model = self.session.scalar(
            select(ImpactPropagationPolicyORM).where(
                ImpactPropagationPolicyORM.tenant_id == tenant_id,
                ImpactPropagationPolicyORM.relationship_type_id == relationship_type_id,
                ImpactPropagationPolicyORM.direction == direction.value,
                ImpactPropagationPolicyORM.governance_status == PolicyGovernanceStatus.ACTIVE.value,
            )
        )
        return None if model is None else _to_domain(model)
