"""ORM model for `impact_propagation_policies` (CDD-042 §8; Artifact
Authorization §2 row 4). Tenant-qualified composite FK to
`relationship_types` is not applied here because `relationship_types` (an
ECOM-generated registry table) carries no `tenant_id` column of its own --
the policy's own `tenant_id` plus the plain FK to `relationship_type_id` is
the strongest integrity available without modifying that table (which this
Artifact Authorization explicitly forbids). Table created by migration
`0023_oqi4_ontology_impact`."""

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class ImpactPropagationPolicyORM(BaseEntity):
    __tablename__ = "impact_propagation_policies"

    __table_args__ = (
        Index("idx_impact_propagation_policies_tenant_id", "tenant_id"),
        Index(
            "idx_impact_propagation_policies_relationship_type_id",
            "relationship_type_id",
        ),
        # CDD-042 §8: only one ACTIVE version per
        # (tenant, relationship_type, direction) at a time. A partial
        # unique index (not a plain UniqueConstraint) is required because
        # RETIRED/Draft versions of the same triple must coexist.
        Index(
            "uq_impact_propagation_policies_one_active",
            "tenant_id",
            "relationship_type_id",
            "direction",
            unique=True,
            postgresql_where=text("governance_status = 'Active'"),
        ),
        UniqueConstraint("tenant_id", "policy_id", name="uq_impact_propagation_policies_tenant_pk"),
        CheckConstraint("max_depth >= 1 AND max_depth <= 10", name="ck_ipp_max_depth_bounded"),
    )

    policy_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_types.relationship_type_id",
            name="fk_impact_propagation_policies_relationship_type_id",
        ),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    max_depth: Mapped[int] = mapped_column(Integer(), nullable=False)
    governance_status: Mapped[str] = mapped_column(String(16), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "impact_propagation_policies.policy_id",
            name="fk_impact_propagation_policies_previous_version_id",
        ),
        nullable=True,
    )
