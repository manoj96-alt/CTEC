# Generated from ECOM Physical Data Model v1.3. Do not edit manually.
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class Enterprise(BaseEntity):
    __tablename__ = "enterprises"

    __table_args__ = (
        Index("idx_enterprises_enterprise_name", "enterprise_name"),
        Index("idx_enterprises_enterprise_type_id", "enterprise_type_id"),
        Index("idx_enterprises_country_id", "country_id"),
        Index("idx_enterprises_lifecycle_state", "lifecycle_state"),
        Index("idx_enterprises_effective_from", "effective_from"),
        Index("idx_enterprises_effective_to", "effective_to"),
        Index("idx_enterprises_governance_status", "governance_status"),
        Index("idx_enterprises_created_by", "created_by"),
        Index("idx_enterprises_created_on", "created_on"),
        Index("idx_enterprises_modified_by", "modified_by"),
        Index("idx_enterprises_modified_on", "modified_on"),
        Index("idx_enterprises_version_number", "version_number"),
        Index("idx_enterprises_previous_version_id", "previous_version_id"),
    )

    enterprise_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    enterprise_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    legal_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    enterprise_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_types.enterprise_type_id",
            name="fk_enterprises_enterprise_type_id",
        ),
        nullable=False,
    )
    country_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("countries.country_id", name="fk_enterprises_country_id"),
        nullable=False,
    )
    lifecycle_state: Mapped[str] = mapped_column(
        Enum("Draft", "Active", "Suspended", "Archived", name="lifecyclestate_t"),
        nullable=False,
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    governance_status: Mapped[str] = mapped_column(
        Enum("Proposed", "Approved", "Retired", "Archived", name="governancestatus_t"),
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("enterprise_entities.enterprise_entity_id", name="fk_enterprises_created_by"),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_enterprises_modified_by",
        ),
        nullable=True,
    )
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("1"))
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("enterprises.enterprise_id", name="fk_enterprises_previous_version_id"),
        nullable=True,
    )
