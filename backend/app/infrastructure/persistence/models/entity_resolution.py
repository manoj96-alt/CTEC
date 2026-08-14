from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKeyConstraint, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class EnterpriseEntityResolutionRecordModel(BaseEntity):
    __tablename__ = "enterprise_entity_resolution_records"
    __table_args__ = (
        Index("idx_eer_records_produced_at", "produced_at"),
        # Composite-unique FK target for
        # enterprise_entity_resolution_history(tenant_id, active_record_id).
        UniqueConstraint("tenant_id", "record_id", name="uq_eer_records_tenant_pk"),
        # Tenant-qualified composite FKs: a resolution record can only
        # reference a canonical entity or policy owned by its own tenant.
        # enterprise_entity_id/policy_id are nullable (Unresolved/Blocked
        # Conflict records, or automated-engine records with no policy row);
        # PostgreSQL's default MATCH SIMPLE skips the check when either
        # referencing column is NULL.
        ForeignKeyConstraint(
            ["tenant_id", "enterprise_entity_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_eer_records_tenant_enterprise_entity",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "policy_id"],
            ["resolution_policies.tenant_id", "resolution_policies.policy_id"],
            name="fk_eer_records_tenant_policy",
        ),
    )

    record_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    enterprise_entity_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    # Pre-existing JSON array (0002), not a relational column: PostgreSQL
    # cannot express a foreign key against elements of a JSON array. Tenant
    # consistency for these references is enforced at the application
    # boundary (EntityResolutionStore validates each id belongs to the
    # record's own tenant before insert) and proven by test.
    supporting_source_object_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    business_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    structured_reasons: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    narrative_explanation: Mapped[str] = mapped_column(String(2000), nullable=False)
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    # Multi-attribute evidence profile (see app.domain.identity_resolution.model
    # .EvidenceProfile). Nullable: pre-existing name-only records have none.
    evidence_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    policy_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    # Principal ID of the steward who authored this record, when it resulted
    # from a human decision rather than the automated engine.
    actor_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class EnterpriseEntityResolutionHistoryModel(BaseEntity):
    """Externally maintained RFC-011 projection; not an ERM business artifact.

    The mapped database column names are retained for migration compatibility only.
    Records never transition between active and archived business states.
    """

    __tablename__ = "enterprise_entity_resolution_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "active_record_id"],
            [
                "enterprise_entity_resolution_records.tenant_id",
                "enterprise_entity_resolution_records.record_id",
            ],
            name="fk_eer_history_tenant_active_record",
        ),
    )

    understanding_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    current_record_identifier: Mapped[UUID] = mapped_column(
        "active_record_id",
        Uuid(),
        nullable=False,
    )
    # Pre-existing JSON array (0002): entirely derived and managed by
    # EntityResolutionStore.append() within a single tenant's history chain,
    # never externally supplied, so it carries no independent tenant-leak
    # surface beyond what the composite FK on active_record_id already
    # guards.
    historical_record_references: Mapped[list[str]] = mapped_column(
        "archived_record_ids", JSON(), nullable=False, default=list
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
