"""ORM models for OQI-H4 governed Integrity (CDD-050 §12; Artifact
Authorization row 7). Exactly the six tables CDD-050 §12 names, no more:
`oqi_integrity_relationship_cardinalities` (shared-platform, versioned,
mirrors `CanonicalStandardORM`'s exact shape), `oqi_integrity_structural_
evaluations`/`oqi_integrity_structural_evaluation_relationships`/
`oqi_integrity_structural_findings` (tenant-owned, Structural Integrity),
and `oqi_integrity_reference_evaluations`/`oqi_integrity_reference_findings`
(tenant-owned, Reference Integrity).

`enterprise_entity_id` columns use RFC-016's own tenant-qualified composite
FK pattern (identical to `institutional_relationships`' own precedent) --
never a plain single-column FK -- so a tenant can never reference another
tenant's `EnterpriseEntity`. No DELETE is ever authorized on any table here
(CDD-050 §12) -- every table is either an immutable append-only ledger or a
versioned, retire-only policy envelope."""

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
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class IntegrityRelationshipCardinalityORM(BaseEntity):
    __tablename__ = "oqi_integrity_relationship_cardinalities"

    __table_args__ = (
        Index(
            "idx_oqi_integrity_cardinalities_relationship_requirement_id",
            "relationship_requirement_id",
        ),
        # CDD-050 §7: exactly one ACTIVE cardinality definition per
        # RelationshipRequirement -- a partial unique index, not a plain
        # UniqueConstraint, because RETIRED historical versions must coexist
        # (identical shape to uq_oqi_canonical_standards_one_active,
        # CDD-049 §10).
        Index(
            "uq_oqi_integrity_cardinalities_one_active",
            "relationship_requirement_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_integrity_cardinalities_status"
        ),
        CheckConstraint("min_cardinality >= 0", name="ck_oqi_integrity_cardinalities_min_nonneg"),
        CheckConstraint(
            "max_cardinality IS NULL OR max_cardinality >= min_cardinality",
            name="ck_oqi_integrity_cardinalities_max_ge_min",
        ),
    )

    integrity_relationship_cardinality_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    relationship_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_requirements.relationship_requirement_id",
            name="fk_oqi_integrity_cardinalities_relationship_requirement_id",
        ),
        nullable=False,
    )
    min_cardinality: Mapped[int] = mapped_column(Integer(), nullable=False)
    max_cardinality: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_integrity_relationship_cardinalities.integrity_relationship_cardinality_id",
            name="fk_oqi_integrity_cardinalities_previous_version_id",
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrityStructuralEvaluationORM(BaseEntity):
    __tablename__ = "oqi_integrity_structural_evaluations"

    __table_args__ = (
        Index("idx_oqi_integrity_structural_evaluations_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_integrity_structural_evaluations_subject",
            "tenant_id",
            "enterprise_entity_id",
            "relationship_requirement_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "enterprise_entity_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_integrity_structural_evaluations_entity",
        ),
        CheckConstraint(
            "outcome IN ('SATISFIED', 'VIOLATED')",
            name="ck_oqi_integrity_structural_evaluations_outcome",
        ),
        CheckConstraint(
            "qualifying_target_count >= 0",
            name="ck_oqi_integrity_structural_evaluations_count_nonneg",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_requirements.relationship_requirement_id",
            name="fk_oqi_integrity_structural_evaluations_requirement_id",
        ),
        nullable=False,
    )
    integrity_relationship_cardinality_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_integrity_relationship_cardinalities.integrity_relationship_cardinality_id",
            name="fk_oqi_integrity_structural_evaluations_cardinality_id",
        ),
        nullable=False,
    )
    enterprise_entity_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    qualifying_target_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluation_horizon: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IntegrityStructuralEvaluationRelationshipORM(BaseEntity):
    """CDD-050 §12 table 3: pins exactly which qualifying
    `InstitutionalRelationship` rows a Structural evaluation counted --
    reconstructable distinct-target provenance, mirroring
    `QualityEvaluationEvidenceORM`/`ComparisonParticipantCanonicalProjectionORM`'s
    established link-table precedent exactly (never opaque JSON)."""

    __tablename__ = "oqi_integrity_structural_evaluation_relationships"

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_integrity_structural_evaluations.evaluation_id",
            name="fk_oqi_integrity_structural_eval_rel_evaluation_id",
        ),
        primary_key=True,
    )
    institutional_relationship_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "institutional_relationships.institutional_relationship_id",
            name="fk_oqi_integrity_structural_eval_rel_relationship_id",
        ),
        primary_key=True,
    )


class IntegrityStructuralFindingORM(BaseEntity):
    __tablename__ = "oqi_integrity_structural_findings"

    __table_args__ = (
        Index("idx_oqi_integrity_structural_findings_tenant_id", "tenant_id"),
        Index("idx_oqi_integrity_structural_findings_status", "status"),
        ForeignKeyConstraint(
            ["tenant_id", "enterprise_entity_id"],
            ["enterprise_entities.tenant_id", "enterprise_entities.enterprise_entity_id"],
            name="fk_oqi_integrity_structural_findings_entity",
        ),
        CheckConstraint(
            "finding_type IN ('MISSING_REQUIRED_RELATIONSHIP', 'RELATIONSHIP_CARDINALITY_VIOLATION')",
            name="ck_oqi_integrity_structural_findings_type",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')", name="ck_oqi_integrity_structural_findings_status"
        ),
    )

    finding_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_requirements.relationship_requirement_id",
            name="fk_oqi_integrity_structural_findings_requirement_id",
        ),
        nullable=False,
    )
    enterprise_entity_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_horizon: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer(), nullable=False)


class IntegrityReferenceEvaluationORM(BaseEntity):
    __tablename__ = "oqi_integrity_reference_evaluations"

    __table_args__ = (
        Index("idx_oqi_integrity_reference_evaluations_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_integrity_reference_evaluations_subject",
            "tenant_id",
            "source_object_id",
            "relationship_requirement_id",
        ),
        CheckConstraint(
            "resolution_outcome IN ('Resolved', 'Unresolved')",
            name="ck_oqi_integrity_reference_evaluations_resolution_outcome",
        ),
        CheckConstraint(
            "outcome IN ('SATISFIED', 'VIOLATED')",
            name="ck_oqi_integrity_reference_evaluations_outcome",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_requirements.relationship_requirement_id",
            name="fk_oqi_integrity_reference_evaluations_requirement_id",
        ),
        nullable=False,
    )
    # Plain single-column FK, mirroring QualityFindingORM.source_object_id's
    # own established precedent -- `source_objects` carries no unique
    # constraint on (tenant_id, source_object_id) to target a tenant-
    # qualified composite FK (unlike enterprise_entities/institutional_
    # relationships, RFC-016). Tenant isolation for this reference is
    # enforced at the query layer, identical to every existing OQI1-3
    # evaluation/Finding table.
    source_object_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_objects.source_object_id",
            name="fk_oqi_integrity_reference_evaluations_source_object_id",
        ),
        nullable=False,
    )
    resolution_record_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entity_resolution_records.record_id",
            name="fk_oqi_integrity_reference_evaluations_resolution_record_id",
        ),
        nullable=False,
    )
    resolution_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluation_horizon: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IntegrityReferenceFindingORM(BaseEntity):
    __tablename__ = "oqi_integrity_reference_findings"

    __table_args__ = (
        Index("idx_oqi_integrity_reference_findings_tenant_id", "tenant_id"),
        Index("idx_oqi_integrity_reference_findings_status", "status"),
        CheckConstraint(
            "finding_type = 'ORPHAN_REFERENCE'",
            name="ck_oqi_integrity_reference_findings_type",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')", name="ck_oqi_integrity_reference_findings_status"
        ),
    )

    finding_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_requirements.relationship_requirement_id",
            name="fk_oqi_integrity_reference_findings_requirement_id",
        ),
        nullable=False,
    )
    source_object_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_objects.source_object_id",
            name="fk_oqi_integrity_reference_findings_source_object_id",
        ),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_horizon: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer(), nullable=False)
