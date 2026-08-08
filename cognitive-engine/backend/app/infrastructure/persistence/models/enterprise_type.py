# Generated from ECOM Physical Data Model v1.3. Do not edit manually.
from uuid import UUID

from sqlalchemy import (
    Index,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class EnterpriseType(BaseEntity):
    __tablename__ = "enterprise_types"

    __table_args__ = (Index("idx_enterprise_types_type_name", "type_name"),)

    enterprise_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    type_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
