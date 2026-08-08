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


class ReasonGraph(BaseEntity):
    __tablename__ = "reason_graphs"

    __table_args__ = (
        Index("idx_reason_graphs_reason_graph_name", "reason_graph_name"),
        Index("idx_reason_graphs_lifecycle_state", "lifecycle_state"),
        Index("idx_reason_graphs_effective_from", "effective_from"),
        Index("idx_reason_graphs_effective_to", "effective_to"),
        Index("idx_reason_graphs_governance_status", "governance_status"),
        Index("idx_reason_graphs_created_by", "created_by"),
        Index("idx_reason_graphs_created_on", "created_on"),
        Index("idx_reason_graphs_modified_by", "modified_by"),
        Index("idx_reason_graphs_modified_on", "modified_on"),
        Index("idx_reason_graphs_version_number", "version_number"),
        Index("idx_reason_graphs_previous_version_id", "previous_version_id"),
    )

    reason_graph_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    reason_graph_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
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
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_reason_graphs_created_by",
        ),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "enterprise_entities.enterprise_entity_id",
            name="fk_reason_graphs_modified_by",
        ),
        nullable=True,
    )
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("1"))
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("reason_graphs.reason_graph_id", name="fk_reason_graphs_previous_version_id"),
        nullable=True,
    )
