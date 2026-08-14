from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class ResolutionPolicyModel(BaseEntity):
    """Versioned, immutable Entity Resolution policy instances.

    tenant_id is always a real tenant id, never a shared "platform" row:
    Conservative/Balanced/Exploratory exist as in-code templates
    (app.domain.identity_resolution.policy) and are materialized as
    tenant-owned rows on first use, so a resolution record's composite
    foreign key (tenant_id, policy_id) can only ever reference a policy
    version owned by its own tenant. A tenant never mutates a policy row in
    place: a new version is a new row.
    """

    __tablename__ = "resolution_policies"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "policy_name", "policy_version", name="uq_resolution_policies_identity"
        ),
        # Composite-unique FK target for enterprise_entity_resolution_records
        # (tenant_id, policy_id).
        UniqueConstraint("tenant_id", "policy_id", name="uq_resolution_policies_tenant_pk"),
    )

    policy_id: Mapped[UUID] = mapped_column(
        Uuid(), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    preset_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
