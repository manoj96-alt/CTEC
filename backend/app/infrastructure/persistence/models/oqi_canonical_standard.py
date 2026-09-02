"""ORM models for OQI-H3 governed Canonical Standards (CDD-049 §9-§11, §15,
§17; Artifact Authorization row 2). Structural precedent: `QualityCoveragePolicyORM`
/ `ReferenceEvidenceAssertionORM` -- single-column `canonical_standard_id`
primary key, `previous_version_id` self-FK version chain, and a partial
unique index enforcing exactly one `ACTIVE` version per
`information_element_requirement_id` (CDD-049 §10). Anchored to a governed
Information Element only -- never to a `SourceField` (PO-H3-01).

`CanonicalValue`/`CanonicalAlias` are normalized children, never a JSONB
payload (CDD-049 §11). Both are scoped to their owning
`canonical_standard_id`; since at most one `CanonicalStandard` version can be
`ACTIVE` per Information Element at a time (enforced one level up), a plain
`UNIQUE(canonical_standard_id, ...)` constraint on each child table already
makes ambiguous resolution within the currently-applicable standard
structurally impossible -- no additional per-row lifecycle/status column is
required on either child table (CDD-049 §11's own explicit field list omits
one; this is the exact, faithful shape of that list, not a redesign).

`oqi_quality_evaluation_canonical_standard` mirrors
`QualityEvaluationReferenceEvidenceORM` exactly (CDD-049 §15).
`oqi_comparison_participant_canonical_projection` is the Consistency
per-participant canonical-projection provenance link (CDD-049 §17)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class CanonicalStandardORM(BaseEntity):
    __tablename__ = "oqi_canonical_standards"

    __table_args__ = (
        Index(
            "idx_oqi_canonical_standards_information_element_requirement_id",
            "information_element_requirement_id",
        ),
        # CDD-049 §10: exactly one ACTIVE version per Information Element --
        # a partial unique index, not a plain UniqueConstraint, because
        # RETIRED historical versions of the same anchor must coexist.
        Index(
            "uq_oqi_canonical_standards_one_active",
            "information_element_requirement_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_canonical_standards_status"
        ),
    )

    canonical_standard_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    information_element_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "information_element_requirements.information_element_requirement_id",
            name="fk_oqi_canonical_standards_information_element_requirement_id",
        ),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_canonical_standards.canonical_standard_id",
            name="fk_oqi_canonical_standards_previous_version_id",
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CanonicalStandardValueORM(BaseEntity):
    __tablename__ = "oqi_canonical_standard_values"

    __table_args__ = (
        Index("idx_oqi_canonical_standard_values_standard_id", "canonical_standard_id"),
        # CDD-049 §11: within one immutable standard version, one canonical
        # representation may be declared at most once.
        Index(
            "uq_oqi_canonical_standard_values_representation",
            "canonical_standard_id",
            "canonical_representation",
            unique=True,
        ),
    )

    canonical_value_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    canonical_standard_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_canonical_standards.canonical_standard_id",
            name="fk_oqi_canonical_standard_values_standard_id",
        ),
        nullable=False,
    )
    canonical_representation: Mapped[str] = mapped_column(String(4000), nullable=False)


class CanonicalStandardAliasORM(BaseEntity):
    __tablename__ = "oqi_canonical_standard_aliases"

    __table_args__ = (
        Index("idx_oqi_canonical_standard_aliases_value_id", "canonical_value_id"),
        Index("idx_oqi_canonical_standard_aliases_standard_id", "canonical_standard_id"),
        # CDD-049 §11: within one immutable standard version, one alias
        # representation may resolve to at most one canonical value --
        # structurally prevents ambiguity, never merely checked at read
        # time. canonical_standard_id is denormalized here (rather than
        # requiring a join through canonical_value_id) purely so this
        # constraint can be expressed directly on this table.
        Index(
            "uq_oqi_canonical_standard_aliases_representation",
            "canonical_standard_id",
            "alias_representation",
            unique=True,
        ),
    )

    canonical_alias_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    canonical_value_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_canonical_standard_values.canonical_value_id",
            name="fk_oqi_canonical_standard_aliases_value_id",
        ),
        nullable=False,
    )
    canonical_standard_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_canonical_standards.canonical_standard_id",
            name="fk_oqi_canonical_standard_aliases_standard_id",
        ),
        nullable=False,
    )
    alias_representation: Mapped[str] = mapped_column(String(4000), nullable=False)


class QualityEvaluationCanonicalStandardORM(BaseEntity):
    """CDD-049 §15: pins the exact `CanonicalStandard` value/version a
    Conformity `QualityEvaluation` consulted -- mirrors
    `QualityEvaluationReferenceEvidenceORM` exactly. One row per evaluation
    (Conformity compares against exactly one qualifying canonical value)."""

    __tablename__ = "oqi_quality_evaluation_canonical_standard"

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "quality_evaluations.evaluation_id",
            name="fk_oqi_qe_canonical_standard_evaluation_id",
        ),
        primary_key=True,
    )
    canonical_value_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_canonical_standard_values.canonical_value_id",
            name="fk_oqi_qe_canonical_standard_value_id",
        ),
        primary_key=True,
    )
    standard_version: Mapped[int] = mapped_column(Integer(), nullable=False)


class ComparisonParticipantCanonicalProjectionORM(BaseEntity):
    """CDD-049 §17: the Consistency per-participant canonical-projection
    provenance link -- one row per participant successfully canonicalized
    and consulted in a Case-B comparison (CDD-049 §16.1). Raw participant
    value is never duplicated here; it is reconstructable via the existing,
    unmodified `quality_comparison_evaluation_evidence` link."""

    __tablename__ = "oqi_comparison_participant_canonical_projection"

    evaluation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "quality_comparison_evaluations.evaluation_id",
            name="fk_comparison_participant_canonical_projection_evaluation_id",
        ),
        primary_key=True,
    )
    participant_role: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_value_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_canonical_standard_values.canonical_value_id",
            name="fk_comparison_participant_canonical_projection_value_id",
        ),
        nullable=False,
    )
    standard_version: Mapped[int] = mapped_column(Integer(), nullable=False)
