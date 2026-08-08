# Generated from ECOM Physical Data Model v1.3. Do not edit manually.
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class InstitutionalRelationshipAssertions(BaseEntity):
    __tablename__ = "institutional_relationship_assertions"

    institutional_relationship_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("institutional_relationships.institutional_relationship_id"),
        nullable=False,
        primary_key=True,
    )
    assertion_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("assertions.assertion_id"), nullable=False, primary_key=True
    )
