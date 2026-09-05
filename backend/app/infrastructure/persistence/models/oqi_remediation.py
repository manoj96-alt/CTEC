"""ORM models for OQI5-I1 -- Deterministic Remediation Foundation
(CDD-043 Sec11-Sec14; Artifact Authorization Sec2 row 5). Four tables:
`oqi_remediation_cases`, `oqi_remediation_candidates`,
`oqi_remediation_instructions`, `oqi_remediation_authorizations`. No
existing OQI1/2/3/4, Gate S, or Gate V table is altered."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
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


class OqiRemediationCaseORM(BaseEntity):
    __tablename__ = "oqi_remediation_cases"

    __table_args__ = (
        Index("idx_oqi_remediation_cases_tenant_id", "tenant_id"),
        Index("idx_oqi_remediation_cases_status", "status"),
        Index(
            "idx_oqi_remediation_cases_finding",
            "tenant_id",
            "finding_family",
            "finding_id",
            unique=True,
        ),
        UniqueConstraint("tenant_id", "case_id", name="uq_oqi_remediation_cases_tenant_pk"),
    )

    case_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    finding_family: Mapped[str] = mapped_column(String(16), nullable=False)
    finding_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    external_execution_claimed: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("false")
    )
    external_execution_claimed_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OqiRemediationCandidateORM(BaseEntity):
    __tablename__ = "oqi_remediation_candidates"

    __table_args__ = (Index("idx_oqi_remediation_candidates_case_id", "case_id"),)

    candidate_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, primary_key=True)
    case_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("oqi_remediation_cases.case_id", name="fk_oqi_remediation_candidates_case_id"),
        nullable=False,
    )
    target_source_object_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    target_source_field_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    proposed_value: Mapped[str] = mapped_column(String(4000), nullable=False)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(
        JSON(), nullable=False, server_default=text("'[]'")
    )
    conflicting_evidence_ids: Mapped[list[str]] = mapped_column(
        JSON(), nullable=False, server_default=text("'[]'")
    )
    missing_participant_roles: Mapped[list[str]] = mapped_column(
        JSON(), nullable=False, server_default=text("'[]'")
    )
    authority_participant_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    basis: Mapped[str] = mapped_column(String(32), nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OqiRemediationInstructionORM(BaseEntity):
    __tablename__ = "oqi_remediation_instructions"

    __table_args__ = (
        Index("idx_oqi_remediation_instructions_case_id", "case_id"),
        UniqueConstraint(
            "tenant_id",
            "instruction_id",
            name="uq_oqi_remediation_instructions_tenant_pk",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "case_id"],
            ["oqi_remediation_cases.tenant_id", "oqi_remediation_cases.case_id"],
            name="fk_oqi_remediation_instructions_tenant_case",
        ),
    )

    instruction_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    finding_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    finding_state_revision: Mapped[int] = mapped_column(Integer(), nullable=False)
    case_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "oqi_remediation_candidates.candidate_id",
            name="fk_oqi_remediation_instructions_candidate_id",
        ),
        nullable=False,
    )
    target_source_object_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    target_source_field_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_recommendation_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OqiRemediationAuthorizationORM(BaseEntity):
    __tablename__ = "oqi_remediation_authorizations"

    __table_args__ = (
        Index("idx_oqi_remediation_authorizations_tenant_id", "tenant_id"),
        Index("idx_oqi_remediation_authorizations_status", "status"),
        Index("idx_oqi_remediation_authorizations_instruction_id", "instruction_id"),
        ForeignKeyConstraint(
            ["tenant_id", "instruction_id"],
            [
                "oqi_remediation_instructions.tenant_id",
                "oqi_remediation_instructions.instruction_id",
            ],
            name="fk_oqi_remediation_authorizations_tenant_instruction",
        ),
    )

    authorization_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(String(200), nullable=False)
    instruction_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decided_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    consumed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_execution_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
