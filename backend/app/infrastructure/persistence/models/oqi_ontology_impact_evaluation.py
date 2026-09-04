"""ORM models for the immutable Impact Evaluation ledger
(`ontology_impact_evaluations`, `ontology_impact_observations`,
`ontology_impact_paths`) and the mutable current-state projection
(`current_ontology_impacts`) (CDD-042 §11; Artifact Authorization §2
row 5). Tables created by migration `0023_oqi4_ontology_impact`."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class OntologyImpactEvaluationORM(BaseEntity):
    __tablename__ = "ontology_impact_evaluations"

    __table_args__ = (
        Index("idx_ontology_impact_evaluations_tenant_id", "tenant_id"),
        Index(
            "idx_ontology_impact_evaluations_finding",
            "tenant_id",
            "finding_family",
            "finding_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "finding_family",
            "finding_id",
            "finding_state_revision",
            "traversed_state_digest",
            name="uq_ontology_impact_evaluations_natural_key",
        ),
        # CDD-055 (OQI4-R1, narrow replace-FK correction): additive tenant-
        # qualified candidate key required so `current_ontology_impacts` can
        # compose a proper tenant-qualified FK against this table. Safe by
        # construction, requires no data backfill: `evaluation_id` is
        # already this table's primary key, so `(tenant_id, evaluation_id)`
        # is trivially unique as a superset of an already-unique key.
        UniqueConstraint(
            "tenant_id", "evaluation_id", name="uq_ontology_impact_evaluations_tenant_pk"
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    # CDD-050 §11, migration 0037: widened from String(8) -- "INTEGRITY" (9
    # chars) does not fit the original width.
    finding_family: Mapped[str] = mapped_column(String(16), nullable=False)
    finding_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    finding_state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    resolution_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entity_resolution_records.record_id",
            name="fk_ontology_impact_evaluations_resolution_record_id",
        ),
        nullable=True,
    )
    traversed_state_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OntologyImpactObservationORM(BaseEntity):
    __tablename__ = "ontology_impact_observations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["evaluation_id"],
            ["ontology_impact_evaluations.evaluation_id"],
            name="fk_ontology_impact_observations_evaluation_id",
        ),
        Index("idx_ontology_impact_observations_evaluation_id", "evaluation_id"),
        Index(
            "idx_ontology_impact_observations_element",
            "ontology_element_type",
            "ontology_element_id",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    ontology_element_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    impact_kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    basis: Mapped[str] = mapped_column(String(40), nullable=False)
    depth: Mapped[int] = mapped_column(Integer(), nullable=False)


class OntologyImpactPathORM(BaseEntity):
    __tablename__ = "ontology_impact_paths"

    __table_args__ = (
        ForeignKeyConstraint(
            ["evaluation_id"],
            ["ontology_impact_evaluations.evaluation_id"],
            name="fk_ontology_impact_paths_evaluation_id",
        ),
        ForeignKeyConstraint(
            ["institutional_relationship_id"],
            ["institutional_relationships.institutional_relationship_id"],
            name="fk_ontology_impact_paths_relationship_id",
        ),
        ForeignKeyConstraint(
            ["policy_id"],
            ["impact_propagation_policies.policy_id"],
            name="fk_ontology_impact_paths_policy_id",
        ),
        Index("idx_ontology_impact_paths_evaluation_id", "evaluation_id"),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    path_ordinal: Mapped[int] = mapped_column(Integer(), primary_key=True)
    institutional_relationship_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    policy_version_number: Mapped[int] = mapped_column(Integer(), nullable=False)


class CurrentOntologyImpactORM(BaseEntity):
    __tablename__ = "current_ontology_impacts"

    __table_args__ = (
        # CDD-055 (OQI4-R1, narrow replace-FK correction): this FK previously
        # targeted the plain (globally-unique) `evaluation_id` primary key,
        # proving only that the referenced evaluation exists -- not that it
        # belongs to this pointer's own tenant. Replaced with a
        # tenant-qualified composite FK against
        # `uq_ontology_impact_evaluations_tenant_pk` (added above for this
        # exact purpose).
        ForeignKeyConstraint(
            ["tenant_id", "latest_evaluation_id"],
            [
                "ontology_impact_evaluations.tenant_id",
                "ontology_impact_evaluations.evaluation_id",
            ],
            name="fk_current_ontology_impacts_tenant_evaluation",
        ),
        UniqueConstraint(
            "tenant_id",
            "finding_family",
            "finding_id",
            "ontology_element_type",
            "ontology_element_id",
            "impact_kind",
            name="uq_current_ontology_impacts_natural_key",
        ),
        Index("idx_current_ontology_impacts_tenant_id", "tenant_id"),
        Index(
            "idx_current_ontology_impacts_element",
            "ontology_element_type",
            "ontology_element_id",
        ),
    )

    current_impact_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    # CDD-050 §11, migration 0037: widened from String(8) -- "INTEGRITY" (9
    # chars) does not fit the original width.
    finding_family: Mapped[str] = mapped_column(String(16), nullable=False)
    finding_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    ontology_element_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    impact_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    latest_evaluation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
