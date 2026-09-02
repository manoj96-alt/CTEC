"""ORM models for `oqi_quality_coverage_policies` and
`oqi_quality_coverage_policy_dimensions` (CDD-047 §8-§11; Artifact
Authorization row 3). Structural precedent: `ImpactPropagationPolicyORM`
(CDD-042 §8) -- single-column `policy_id` primary key, `previous_version_id`
self-FK version chain, and a partial unique index enforcing exactly one
`ACTIVE` version per `(tenant_id, ontology_element_type,
ontology_element_id)` -- not `OqiBusinessDependencyORM`'s composite-PK
pattern, per CDD-047 §10's explicit precedent selection.

`required_dimensions` is deliberately normalized into its own child table
(`oqi_quality_coverage_policy_dimensions`), never a JSONB/ARRAY column
(CDD-047 §9). No `tenant_id` composite FK is applied to
`ontology_element_id` because the ontology itself carries no `tenant_id` of
its own (shared platform structure, confirmed directly against
`entity_types`/`relationship_types` and restated by the CDD-046 QualityRule
Ownership Erratum) -- the policy's own `tenant_id` is the strongest
integrity available without modifying ontology tables, mirroring
`ImpactPropagationPolicyORM`'s own identical precedent for
`relationship_type_id`."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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

#: CDD-047 §4: closed, exactly nine -- a governance-requirement vocabulary,
#: never a claim that all nine have live evaluators (see the module
#: docstring on `app.domain.oqi_quality_coverage.policy`).
_COVERAGE_DIMENSION_VALUES = (
    "COMPLETENESS",
    "VALIDITY",
    "CONSISTENCY",
    "ACCURACY",
    "UNIQUENESS",
    "TIMELINESS",
    "INTEGRITY",
    "CONFORMITY",
    "REASONABLENESS",
)
_COVERAGE_DIMENSION_CHECK_SQL = "dimension IN ({})".format(
    ", ".join(f"'{value}'" for value in _COVERAGE_DIMENSION_VALUES)
)


class QualityCoveragePolicyORM(BaseEntity):
    __tablename__ = "oqi_quality_coverage_policies"

    __table_args__ = (
        Index("idx_oqi_quality_coverage_policies_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_quality_coverage_policies_anchor",
            "tenant_id",
            "ontology_element_type",
            "ontology_element_id",
        ),
        # CDD-047 §11: exactly one ACTIVE version per (tenant, anchor) --
        # a partial unique index, not a plain UniqueConstraint, because
        # RETIRED historical versions of the same anchor must coexist.
        # Mirrors `uq_impact_propagation_policies_one_active` exactly.
        Index(
            "uq_oqi_quality_coverage_policies_one_active",
            "tenant_id",
            "ontology_element_type",
            "ontology_element_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        UniqueConstraint(
            "tenant_id", "policy_id", name="uq_oqi_quality_coverage_policies_tenant_pk"
        ),
        CheckConstraint(
            "ontology_element_type IN ('ENTITY', 'RELATIONSHIP')",
            name="ck_oqi_quality_coverage_policies_anchor_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_quality_coverage_policies_status"
        ),
    )

    policy_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    ontology_element_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_quality_coverage_policies.policy_id",
            name="fk_oqi_quality_coverage_policies_previous_version_id",
        ),
        nullable=True,
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QualityCoveragePolicyDimensionORM(BaseEntity):
    __tablename__ = "oqi_quality_coverage_policy_dimensions"

    __table_args__ = (
        Index(
            "idx_oqi_quality_coverage_policy_dimensions_policy_id",
            "policy_id",
        ),
        CheckConstraint(_COVERAGE_DIMENSION_CHECK_SQL, name="ck_oqi_qcp_dimensions_closed_vocab"),
    )

    policy_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_quality_coverage_policies.policy_id",
            name="fk_oqi_qcp_dimensions_policy_id",
        ),
        primary_key=True,
    )
    dimension: Mapped[str] = mapped_column(String(16), primary_key=True)
