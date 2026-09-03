"""ORM models for OQI-H5 governed Timeliness (CDD-051 §8, §28; Artifact
Authorization row 5). Exactly the three tables CDD-051 §28 names, no more:
`oqi_timeliness_policies` (tenant-owned, versioned, anchored to
`InformationElementRequirement` x `BusinessProcess`), `oqi_timeliness_
evaluations` (tenant-owned, append-only evaluation ledger), and
`oqi_timeliness_findings` (tenant-owned, current-state Finding lineage,
`STALE_SOURCE_EVIDENCE` / `INGESTION_LATENCY_EXCEEDED` only).

Every tenant-owned composite FK here is tenant-qualified (RFC-016's own
pattern, restated by CDD-050/H4-R1) -- never a plain single-column FK --
so a tenant can never reference another tenant's `BusinessProcess` or
`SourceObject`. `information_element_requirement_id` is a plain FK: its
target, `information_element_requirements`, is shared-platform with no
`tenant_id` column at all (CDD-051 §7), correct by design, mirroring
`relationship_requirement_id`'s own established plain-FK-to-shared-platform
pattern. No DELETE is ever authorized on any table here (CDD-051 §30) --
every table is either an immutable append-only ledger or a versioned,
retire-only policy envelope."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class TimelinessPolicyORM(BaseEntity):
    __tablename__ = "oqi_timeliness_policies"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "policy_id",
            "version",
            name="uq_oqi_timeliness_policies_tenant_pk",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "business_process_id", "business_process_version"],
            [
                "oqi_business_processes.tenant_id",
                "oqi_business_processes.process_id",
                "oqi_business_processes.version",
            ],
            name="fk_oqi_timeliness_policies_tenant_business_process",
        ),
        Index("idx_oqi_timeliness_policies_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_timeliness_policies_anchor",
            "tenant_id",
            "information_element_requirement_id",
            "business_process_id",
        ),
        # CDD-051 §8: exactly one ACTIVE policy per exact anchor tuple -- a
        # partial unique index, not a plain UniqueConstraint, because
        # RETIRED historical versions must coexist (identical shape to
        # uq_oqi_integrity_cardinalities_one_active, CDD-050 §7).
        Index(
            "uq_oqi_timeliness_policies_one_active_per_anchor",
            "tenant_id",
            "information_element_requirement_id",
            "business_process_id",
            "business_process_version",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_timeliness_policies_status"
        ),
        CheckConstraint(
            "freshness_window_seconds IS NULL OR freshness_window_seconds > 0",
            name="ck_oqi_timeliness_policies_freshness_positive",
        ),
        CheckConstraint(
            "ingestion_sla_seconds IS NULL OR ingestion_sla_seconds > 0",
            name="ck_oqi_timeliness_policies_ingestion_sla_positive",
        ),
        CheckConstraint(
            "freshness_window_seconds IS NOT NULL OR ingestion_sla_seconds IS NOT NULL",
            name="ck_oqi_timeliness_policies_at_least_one_threshold",
        ),
    )

    policy_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    version: Mapped[int] = mapped_column(Integer(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    information_element_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "information_element_requirements.information_element_requirement_id",
            name="fk_oqi_timeliness_policies_information_element_requirement_id",
        ),
        nullable=False,
    )
    business_process_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    business_process_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    freshness_window_seconds: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    ingestion_sla_seconds: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TimelinessEvaluationORM(BaseEntity):
    __tablename__ = "oqi_timeliness_evaluations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "policy_id", "policy_version"],
            [
                "oqi_timeliness_policies.tenant_id",
                "oqi_timeliness_policies.policy_id",
                "oqi_timeliness_policies.version",
            ],
            name="fk_oqi_timeliness_evaluations_tenant_policy",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "source_object_id"],
            ["source_objects.tenant_id", "source_objects.source_object_id"],
            name="fk_oqi_timeliness_evaluations_tenant_source_object",
        ),
        Index("idx_oqi_timeliness_evaluations_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_timeliness_evaluations_subject",
            "tenant_id",
            "source_object_id",
            "policy_id",
            "finding_type",
        ),
        CheckConstraint(
            "finding_type IN ('STALE_SOURCE_EVIDENCE', 'INGESTION_LATENCY_EXCEEDED')",
            name="ck_oqi_timeliness_evaluations_finding_type",
        ),
        CheckConstraint(
            "outcome IN ('SATISFIED', 'VIOLATED')",
            name="ck_oqi_timeliness_evaluations_outcome",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_object_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    field_value_evidence_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "field_value_evidence.field_value_evidence_id",
            name="fk_oqi_timeliness_evaluations_field_value_evidence_id",
        ),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluation_horizon: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TimelinessFindingORM(BaseEntity):
    __tablename__ = "oqi_timeliness_findings"

    __table_args__ = (
        # CDD-051 §17 anchors Finding identity to `policy_id` alone, never
        # `policy_version` -- but PostgreSQL cannot compose a FK against a
        # subset of another table's composite unique key. `policy_version`
        # is therefore carried here as a repository-managed bookkeeping
        # column only (kept current to whichever policy version produced
        # the Finding's most recent transition) -- it is NOT part of
        # `TimelinessFinding`'s domain identity/equality (CDD-051 §17) and
        # is never read by `derive_timeliness_finding_id`. This mirrors
        # `oqi_timeliness_evaluations`' own tenant-qualified composite FK
        # shape exactly, applied for structural tenant-safety, not identity.
        ForeignKeyConstraint(
            ["tenant_id", "policy_id", "policy_version"],
            [
                "oqi_timeliness_policies.tenant_id",
                "oqi_timeliness_policies.policy_id",
                "oqi_timeliness_policies.version",
            ],
            name="fk_oqi_timeliness_findings_tenant_policy",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "source_object_id"],
            ["source_objects.tenant_id", "source_objects.source_object_id"],
            name="fk_oqi_timeliness_findings_tenant_source_object",
        ),
        Index("idx_oqi_timeliness_findings_tenant_id", "tenant_id"),
        Index("idx_oqi_timeliness_findings_status", "status"),
        CheckConstraint(
            "finding_type IN ('STALE_SOURCE_EVIDENCE', 'INGESTION_LATENCY_EXCEEDED')",
            name="ck_oqi_timeliness_findings_type",
        ),
        CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="ck_oqi_timeliness_findings_status"),
    )

    finding_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_object_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_horizon: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer(), nullable=False)
