from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.identity_resolution.policy import (
    ResolutionPolicyDefinition,
    balanced_preset,
    conservative_preset,
    exploratory_preset,
)
from app.infrastructure.persistence.models.resolution_policy import ResolutionPolicyModel

BUILT_IN_PRESETS: tuple[ResolutionPolicyDefinition, ...] = (
    conservative_preset(),
    balanced_preset(),
    exploratory_preset(),
)


class ResolutionPolicyStore:
    """Tenant-owned, immutable policy persistence. Conservative/Balanced/
    Exploratory are in-code templates (app.domain.identity_resolution.policy)
    materialized as real, tenant-owned rows on first use -- never a shared
    cross-tenant row. A policy row is never mutated in place: once
    referenced by a resolution record, its (tenant_id, policy_name,
    policy_version) identity and definition are immutable forever; a
    changed policy is a new version, which is a new row.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self, tenant_id: str, policy_name: str, policy_version: str
    ) -> ResolutionPolicyModel | None:
        return self.session.scalar(
            select(ResolutionPolicyModel).where(
                ResolutionPolicyModel.tenant_id == tenant_id,
                ResolutionPolicyModel.policy_name == policy_name,
                ResolutionPolicyModel.policy_version == policy_version,
            )
        )

    def get_by_id(self, tenant_id: str, policy_id: UUID) -> ResolutionPolicyModel | None:
        model = self.session.get(ResolutionPolicyModel, policy_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        return model

    def list_for_tenant(self, tenant_id: str) -> list[ResolutionPolicyModel]:
        return list(
            self.session.scalars(
                select(ResolutionPolicyModel)
                .where(ResolutionPolicyModel.tenant_id == tenant_id)
                .order_by(ResolutionPolicyModel.policy_name, ResolutionPolicyModel.policy_version)
            )
        )

    def materialize(
        self, tenant_id: str, definition: ResolutionPolicyDefinition, *, preset_kind: str
    ) -> ResolutionPolicyModel:
        """Idempotent get-or-create: repeated calls with the same
        (tenant_id, policy_name, policy_version) never create a duplicate
        row or mutate the existing one."""
        existing = self.get(tenant_id, definition.policy_name, definition.policy_version)
        if existing is not None:
            return existing
        model = ResolutionPolicyModel(
            policy_id=uuid4(),
            tenant_id=tenant_id,
            policy_name=definition.policy_name,
            policy_version=definition.policy_version,
            preset_kind=preset_kind,
            definition=definition.to_definition_dict(),
            status="Active",
            created_on=datetime.now(UTC),
        )
        self.session.add(model)
        self.session.flush()
        return model

    def materialize_built_in_presets(self, tenant_id: str) -> list[ResolutionPolicyModel]:
        return [
            self.materialize(tenant_id, definition, preset_kind=definition.policy_name)
            for definition in BUILT_IN_PRESETS
        ]

    def as_definition(self, model: ResolutionPolicyModel) -> ResolutionPolicyDefinition:
        return ResolutionPolicyDefinition.from_definition_dict(model.definition)
