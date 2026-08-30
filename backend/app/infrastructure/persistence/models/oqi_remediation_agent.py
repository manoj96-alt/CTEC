"""ORM models for OQI5-I2 -- Governed Real Agent Reasoning (CDD-043
§18-§22; Artifact Authorization §3 row 6). Four tables:
`oqi_remediation_agent_roles`, `oqi_remediation_agent_runs`,
`oqi_remediation_agent_assessments`, `oqi_remediation_agent_recommendations`.
No existing OQI1/2/3/4, OQI5-I1, Gate S, or Gate V table is altered."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class AgentRoleORM(BaseEntity):
    __tablename__ = "oqi_remediation_agent_roles"

    __table_args__ = (
        Index(
            "idx_oqi_remediation_agent_roles_role_version",
            "role_id",
            "version",
            unique=True,
        ),
    )

    role_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer(), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    instructions: Mapped[str] = mapped_column(Text(), nullable=False)
    allowed_recommendation_types: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentRunORM(BaseEntity):
    __tablename__ = "oqi_remediation_agent_runs"

    __table_args__ = (
        Index("idx_oqi_remediation_agent_runs_tenant_id", "tenant_id"),
        Index("idx_oqi_remediation_agent_runs_case_id", "case_id"),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    case_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("oqi_remediation_cases.case_id", name="fk_oqi_remediation_agent_runs_case_id"),
        nullable=False,
    )
    role_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_packet_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_output: Mapped[str | None] = mapped_column(Text(), nullable=True)
    result_state: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentAssessmentORM(BaseEntity):
    __tablename__ = "oqi_remediation_agent_assessments"

    __table_args__ = (Index("idx_oqi_remediation_agent_assessments_run_id", "run_id"),)

    run_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_remediation_agent_runs.run_id",
            name="fk_oqi_remediation_agent_assessments_run_id",
        ),
        nullable=False,
        primary_key=True,
    )
    role_id: Mapped[str] = mapped_column(String(64), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    conflicting_evidence_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    impact_evaluation_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    rationale: Mapped[str] = mapped_column(String(2000), nullable=False)


class AgentRecommendationORM(BaseEntity):
    __tablename__ = "oqi_remediation_agent_recommendations"

    __table_args__ = (
        Index("idx_oqi_remediation_agent_recommendations_case_id", "case_id"),
        Index("idx_oqi_remediation_agent_recommendations_run_id", "run_id"),
    )

    recommendation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_remediation_agent_runs.run_id",
            name="fk_oqi_remediation_agent_recommendations_run_id",
        ),
        nullable=False,
    )
    case_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_remediation_cases.case_id",
            name="fk_oqi_remediation_agent_recommendations_case_id",
        ),
        nullable=False,
    )
    recommendation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    conflicting_evidence_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False)
    rationale: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
