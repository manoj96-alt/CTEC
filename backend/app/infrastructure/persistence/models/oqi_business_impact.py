"""ORM models for OQI6-I -- Criticality, Business Impact & Explainable
Reliance (CDD-044; Artifact Authorization §2.1 row 6). Six tables:
`oqi_business_processes`, `oqi_business_dependencies`,
`oqi_business_impact_evaluations`, `current_business_impacts`,
`oqi_reliance_evaluations`, `current_reliance`. No existing OQI1-5, Gate S,
Gate V, or Gate F table is altered."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class OqiBusinessProcessORM(BaseEntity):
    __tablename__ = "oqi_business_processes"

    __table_args__ = (
        Index("idx_oqi_business_processes_tenant_id", "tenant_id"),
        Index("idx_oqi_business_processes_process_id", "process_id"),
    )

    process_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    version: Mapped[int] = mapped_column(Integer(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OqiBusinessDependencyORM(BaseEntity):
    __tablename__ = "oqi_business_dependencies"

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_process_id", "business_process_version"],
            ["oqi_business_processes.process_id", "oqi_business_processes.version"],
            name="fk_oqi_business_dependencies_process",
        ),
        Index("idx_oqi_business_dependencies_tenant_id", "tenant_id"),
        Index("idx_oqi_business_dependencies_dependency_id", "dependency_id"),
        Index(
            "idx_oqi_business_dependencies_subject",
            "tenant_id",
            "ontology_element_type",
            "ontology_element_id",
        ),
    )

    dependency_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    version: Mapped[int] = mapped_column(Integer(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    business_process_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    business_process_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    ontology_element_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    criticality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OqiBusinessImpactEvaluationORM(BaseEntity):
    __tablename__ = "oqi_business_impact_evaluations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_dependency_id", "business_dependency_version"],
            ["oqi_business_dependencies.dependency_id", "oqi_business_dependencies.version"],
            name="fk_oqi_business_impact_evaluations_dependency",
        ),
        ForeignKeyConstraint(
            ["considered_current_impact_id"],
            ["current_ontology_impacts.current_impact_id"],
            name="fk_oqi_business_impact_evaluations_current_impact",
        ),
        Index("idx_oqi_business_impact_evaluations_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_business_impact_evaluations_dependency",
            "business_dependency_id",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    business_dependency_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    business_dependency_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    ontology_element_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    considered_current_impact_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CurrentBusinessImpactORM(BaseEntity):
    __tablename__ = "current_business_impacts"

    __table_args__ = (
        ForeignKeyConstraint(
            ["latest_evaluation_id"],
            ["oqi_business_impact_evaluations.evaluation_id"],
            name="fk_current_business_impacts_latest_evaluation_id",
        ),
        Index("idx_current_business_impacts_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    business_dependency_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    latest_evaluation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OqiRelianceEvaluationORM(BaseEntity):
    __tablename__ = "oqi_reliance_evaluations"

    __table_args__ = (
        Index("idx_oqi_reliance_evaluations_tenant_id", "tenant_id"),
        Index(
            "idx_oqi_reliance_evaluations_subject",
            "tenant_id",
            "ontology_element_type",
            "ontology_element_id",
        ),
    )

    evaluation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    ontology_element_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    contributing_state_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CurrentRelianceORM(BaseEntity):
    __tablename__ = "current_reliance"

    __table_args__ = (
        ForeignKeyConstraint(
            ["latest_evaluation_id"],
            ["oqi_reliance_evaluations.evaluation_id"],
            name="fk_current_reliance_latest_evaluation_id",
        ),
        Index("idx_current_reliance_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    ontology_element_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    ontology_element_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    latest_evaluation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
