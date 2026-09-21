"""ORM models for OQI-H6 governed EnterpriseEntity Uniqueness (CDD-084 §7,
§11-§29; Artifact Authorization §7). Exactly the five tables CDD-084/AA §7
name, no more: `oqi_uniqueness_policies` (tenant-owned, versioned, anchored
to `entity_type_id`), `oqi_uniqueness_evaluations` (tenant-owned, append-
only per-entity evaluation ledger), `oqi_uniqueness_candidates` (tenant-
owned, immutable, canonical-pair candidate ledger), `oqi_uniqueness_
adjudications` (tenant-owned, append-only steward decision ledger), and
`oqi_uniqueness_findings` (tenant-owned, current-state Finding lineage,
`DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE` only).

Every tenant-owned composite FK here is tenant-qualified (RFC-016's own
pattern, restated by CDD-050/H4-R1, CDD-084 §13) -- never a plain
single-column FK -- so a tenant can never reference another tenant's
`EnterpriseEntity` or `UniquenessPolicy`. `entity_type_id` is a plain FK:
its target, `entity_types`, is shared-platform with no `tenant_id` column at
all, correct by design, mirroring `information_element_requirement_id`'s
own established plain-FK-to-shared-platform pattern
(`TimelinessPolicyORM`). No DELETE is ever authorized on any table here
(CDD-084 §21/§25) -- every table is either an immutable append-only ledger
or a versioned, retire-only policy envelope."""

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


class UniquenessPolicyORM(BaseEntity):
    __tablename__ = "oqi_uniqueness_policies"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "policy_id",
            "version",
            name="uq_oqi_uniqueness_policies_tenant_pk",
        ),
        Index("idx_oqi_uniqueness_policies_tenant_id", "tenant_id"),
        # CDD-084 §15: exactly one ACTIVE policy per exact
        # (tenant_id, entity_type_id) anchor -- a partial unique index, not
        # a plain UniqueConstraint, because RETIRED historical versions must
        # coexist (identical shape to
        # uq_oqi_timeliness_policies_one_active_per_anchor, CDD-051 §8).
        Index(
            "uq_oqi_uniqueness_policies_one_active_per_type",
            "tenant_id",
            "entity_type_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_uniqueness_policies_status"
        ),
        CheckConstraint(
            "bucket_max_size > 0", name="ck_oqi_uniqueness_policies_bucket_max_size_positive"
        ),
    )

    policy_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    version: Mapped[int] = mapped_column(Integer(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("entity_types.entity_type_id", name="fk_oqi_uniqueness_policies_entity_type_id"),
        nullable=False,
    )
    bucket_max_size: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UniquenessEvaluationORM(BaseEntity):
    __tablename__ = "oqi_uniqueness_evaluations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "policy_id", "policy_version"],
            [
                "oqi_uniqueness_policies.tenant_id",
                "oqi_uniqueness_policies.policy_id",
                "oqi_uniqueness_policies.version",
            ],
            name="fk_oqi_uniqueness_evaluations_tenant_policy",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "enterprise_entity_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_evaluations_tenant_entity",
        ),
        Index("idx_oqi_uniqueness_evaluations_subject", "tenant_id", "enterprise_entity_id"),
        Index("idx_oqi_uniqueness_evaluations_policy", "tenant_id", "policy_id"),
        CheckConstraint(
            "outcome IN ('SATISFIED', 'VIOLATED', 'NOT_EVALUABLE')",
            name="ck_oqi_uniqueness_evaluations_outcome",
        ),
        CheckConstraint(
            "(outcome = 'NOT_EVALUABLE' AND not_evaluable_reason = 'BUCKET_EXCEEDED_CAP') "
            "OR (outcome != 'NOT_EVALUABLE' AND not_evaluable_reason IS NULL)",
            name="ck_oqi_uniqueness_evaluations_not_evaluable_reason",
        ),
        CheckConstraint(
            "candidate_count >= 0", name="ck_oqi_uniqueness_evaluations_candidate_count_nonneg"
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    enterprise_entity_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    not_evaluable_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    candidate_count: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default=text("0")
    )
    evaluated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UniquenessCandidateORM(BaseEntity):
    __tablename__ = "oqi_uniqueness_candidates"

    __table_args__ = (
        CheckConstraint(
            "member_a_id < member_b_id", name="ck_oqi_uniqueness_candidates_canonical_pair"
        ),
        UniqueConstraint(
            "tenant_id",
            "member_a_id",
            "member_b_id",
            "policy_id",
            "policy_version",
            name="uq_oqi_uniqueness_candidates_idempotent",
        ),
        UniqueConstraint(
            "tenant_id", "candidate_id", name="uq_oqi_uniqueness_candidates_tenant_pk"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "member_a_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_candidates_tenant_member_a",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "member_b_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_candidates_tenant_member_b",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "policy_id", "policy_version"],
            [
                "oqi_uniqueness_policies.tenant_id",
                "oqi_uniqueness_policies.policy_id",
                "oqi_uniqueness_policies.version",
            ],
            name="fk_oqi_uniqueness_candidates_tenant_policy",
        ),
        Index("idx_oqi_uniqueness_candidates_tenant_id", "tenant_id"),
        Index("idx_oqi_uniqueness_candidates_pair", "tenant_id", "member_a_id", "member_b_id"),
    )

    candidate_id: Mapped[UUID] = mapped_column(
        Uuid(), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    member_a_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    member_b_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    policy_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    matched_normalized_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UniquenessAdjudicationORM(BaseEntity):
    __tablename__ = "oqi_uniqueness_adjudications"

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "candidate_id"],
            [
                "oqi_uniqueness_candidates.tenant_id",
                "oqi_uniqueness_candidates.candidate_id",
            ],
            name="fk_oqi_uniqueness_adjudications_tenant_candidate",
        ),
        Index(
            "idx_oqi_uniqueness_adjudications_candidate",
            "tenant_id",
            "candidate_id",
            "decided_on",
        ),
        CheckConstraint(
            "action IN ('REJECT_NOT_DUPLICATE', 'CONFIRM_DUPLICATE')",
            name="ck_oqi_uniqueness_adjudications_action",
        ),
    )

    adjudication_id: Mapped[UUID] = mapped_column(
        Uuid(), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    rationale: Mapped[str] = mapped_column(String(2000), nullable=False)
    decided_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UniquenessFindingORM(BaseEntity):
    __tablename__ = "oqi_uniqueness_findings"

    __table_args__ = (
        CheckConstraint(
            "member_a_id < member_b_id", name="ck_oqi_uniqueness_findings_canonical_pair"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "candidate_id"],
            [
                "oqi_uniqueness_candidates.tenant_id",
                "oqi_uniqueness_candidates.candidate_id",
            ],
            name="fk_oqi_uniqueness_findings_tenant_candidate",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "member_a_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_findings_tenant_member_a",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "member_b_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_uniqueness_findings_tenant_member_b",
        ),
        Index("idx_oqi_uniqueness_findings_tenant_id", "tenant_id"),
        Index("idx_oqi_uniqueness_findings_status", "status"),
        Index("idx_oqi_uniqueness_findings_pair", "tenant_id", "member_a_id", "member_b_id"),
        CheckConstraint(
            "finding_type = 'DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE'",
            name="ck_oqi_uniqueness_findings_type",
        ),
        CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="ck_oqi_uniqueness_findings_status"),
    )

    finding_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    member_a_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    member_b_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer(), nullable=False)
