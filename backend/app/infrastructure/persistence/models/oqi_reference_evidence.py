"""ORM models for OQI-H2 governed Reference Evidence (CDD-048 §15-§16;
Artifact Authorization row 3). Structural precedent:
`QualityCoveragePolicyORM` (CDD-047 §8-§11) -- single-column `assertion_id`
primary key, `previous_version_id` self-FK version chain, and a partial
unique index enforcing exactly one `ACTIVE` version per
`(tenant_id, ontology_element_type, ontology_element_id, source_field_id,
form)` -- multiple forms may each hold their own ACTIVE assertion for the
same subject simultaneously (CDD-048 §15).

Each form's specific provenance lives on its own normalized 1:1 child table
(`oqi_governed_reference_dataset_entries`/`oqi_human_verified_evidence_
entries`/`oqi_business_rule_derived_reference_entries`), never a generic
JSONB payload -- mirroring `QualityCoveragePolicyDimensionORM`'s own
normalized-child precedent.

`oqi_reference_evidence_conflicts` (CDD-048 §16) is a separate, mutable
current-state table -- explicitly not a Quality Finding table, carries no
`FindingStorageFamily`/`QualityDimension` columns of any kind. Its member
assertion ids are normalized into `oqi_reference_evidence_conflict_members`,
never a JSONB/ARRAY column, mirroring `QualityCoveragePolicyDimensionORM`'s
own normalized-child discipline (CDD-047 §9) applied consistently here."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity

_REFERENCE_EVIDENCE_FORM_VALUES = (
    "GOVERNED_REFERENCE_DATASET",
    "HUMAN_VERIFIED_EVIDENCE",
    "BUSINESS_RULE_DERIVED_VALUE",
)
_REFERENCE_EVIDENCE_FORM_CHECK_SQL = "form IN ({})".format(
    ", ".join(f"'{value}'" for value in _REFERENCE_EVIDENCE_FORM_VALUES)
)


class ReferenceEvidenceAssertionORM(BaseEntity):
    __tablename__ = "oqi_reference_evidence_assertions"

    __table_args__ = (
        Index("idx_oqi_reference_evidence_assertions_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_reference_evidence_assertions_anchor",
            "tenant_id",
            "ontology_element_type",
            "ontology_element_id",
            "source_field_id",
        ),
        # CDD-048 §15: exactly one ACTIVE version per (tenant, subject,
        # form) -- a partial unique index, not a plain UniqueConstraint,
        # because RETIRED historical versions of the same (subject, form)
        # must coexist, and distinct forms may each be ACTIVE simultaneously.
        Index(
            "uq_oqi_reference_evidence_assertions_one_active",
            "tenant_id",
            "ontology_element_type",
            "ontology_element_id",
            "source_field_id",
            "form",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint(
            "ontology_element_type IN ('ENTITY', 'RELATIONSHIP')",
            name="ck_oqi_reference_evidence_assertions_anchor_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_reference_evidence_assertions_status"
        ),
        CheckConstraint(
            _REFERENCE_EVIDENCE_FORM_CHECK_SQL, name="ck_oqi_reference_evidence_assertions_form"
        ),
    )

    assertion_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    ontology_element_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_fields.source_field_id",
            name="fk_oqi_reference_evidence_assertions_source_field_id",
        ),
        nullable=False,
    )
    form: Mapped[str] = mapped_column(String(32), nullable=False)
    asserted_value: Mapped[str] = mapped_column(String(4000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_reference_evidence_assertions.assertion_id",
            name="fk_oqi_reference_evidence_assertions_previous_version_id",
        ),
        nullable=True,
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GovernedReferenceDatasetEntryORM(BaseEntity):
    __tablename__ = "oqi_governed_reference_dataset_entries"

    assertion_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_reference_evidence_assertions.assertion_id",
            name="fk_oqi_governed_reference_dataset_entries_assertion_id",
        ),
        primary_key=True,
    )
    dataset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_key: Mapped[str] = mapped_column(String(1000), nullable=False)


class HumanVerifiedEvidenceEntryORM(BaseEntity):
    __tablename__ = "oqi_human_verified_evidence_entries"

    assertion_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_reference_evidence_assertions.assertion_id",
            name="fk_oqi_human_verified_evidence_entries_assertion_id",
        ),
        primary_key=True,
    )
    verifying_actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    verification_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verification_rationale: Mapped[str] = mapped_column(String(4000), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BusinessRuleDerivedReferenceEntryORM(BaseEntity):
    __tablename__ = "oqi_business_rule_derived_reference_entries"

    assertion_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_reference_evidence_assertions.assertion_id",
            name="fk_oqi_business_rule_derived_reference_entries_assertion_id",
        ),
        primary_key=True,
    )
    deriving_business_rule_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "business_rules.rule_id",
            name="fk_oqi_business_rule_derived_reference_entries_rule_id",
        ),
        nullable=False,
    )
    deriving_rule_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    deriving_evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "business_rule_evaluations.evaluation_id",
            name="fk_oqi_business_rule_derived_reference_entries_evaluation_id",
        ),
        nullable=False,
    )


class OqiReferenceEvidenceConflictORM(BaseEntity):
    """CDD-048 §16: mutable current-state governance condition. Explicitly
    NOT a Quality Finding table -- no `finding_family`/`dimension`/
    `finding_type` column of any kind."""

    __tablename__ = "oqi_reference_evidence_conflicts"

    __table_args__ = (
        Index("idx_oqi_reference_evidence_conflicts_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_reference_evidence_conflicts_anchor",
            "tenant_id",
            "ontology_element_type",
            "ontology_element_id",
            "source_field_id",
        ),
        CheckConstraint(
            "ontology_element_type IN ('ENTITY', 'RELATIONSHIP')",
            name="ck_oqi_reference_evidence_conflicts_anchor_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'RESOLVED')", name="ck_oqi_reference_evidence_conflicts_status"
        ),
    )

    conflict_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    ontology_element_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    source_field_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "source_fields.source_field_id",
            name="fk_oqi_reference_evidence_conflicts_source_field_id",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OqiReferenceEvidenceConflictMemberORM(BaseEntity):
    """CDD-048 §16: normalized child recording exactly which
    `ReferenceEvidenceAssertion` rows are in disagreement for one conflict."""

    __tablename__ = "oqi_reference_evidence_conflict_members"

    conflict_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_reference_evidence_conflicts.conflict_id",
            name="fk_oqi_reference_evidence_conflict_members_conflict_id",
        ),
        primary_key=True,
    )
    assertion_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_reference_evidence_assertions.assertion_id",
            name="fk_oqi_reference_evidence_conflict_members_assertion_id",
        ),
        primary_key=True,
    )


class QualityEvaluationReferenceEvidenceORM(BaseEntity):
    """CDD-048 §7: pins the exact `ReferenceEvidenceAssertion` version an
    Accuracy `QualityEvaluation` consulted -- mirrors `QualityEvaluationEvidenceORM`'s
    own association-table pattern exactly. One row per evaluation (Accuracy
    compares against exactly one qualifying value, CDD-048 §8)."""

    __tablename__ = "oqi_quality_evaluation_reference_evidence"

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "quality_evaluations.evaluation_id",
            name="fk_oqi_qe_reference_evidence_evaluation_id",
        ),
        primary_key=True,
    )
    assertion_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_reference_evidence_assertions.assertion_id",
            name="fk_oqi_qe_reference_evidence_assertion_id",
        ),
        primary_key=True,
    )
